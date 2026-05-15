import os
import json
import dataclasses
from flask import Flask, request, jsonify, render_template, session, Response, stream_with_context
from flask_session import Session
from werkzeug.utils import secure_filename

from config import config
from core.contracts import PipelineRequest, CompletionRequest
from ingestion.parser import DocumentParser
from ingestion.chunker import Chunker
from indexing.indexer import Indexer
from retrieval.retriever import Retriever
from reasoning.llm_caller import LLMCaller
from reasoning.prompt_builder import PromptBuilder
from extraction.schema_registry import SchemaRegistry
from extraction.validator import Validator
from extraction.extractor import MetadataExtractor
from orchestration.session_manager import SessionManager
from orchestration.orchestrator import Orchestrator

app = Flask(__name__)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = os.urandom(24)
Session(app)

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

# Initialize singletons
schema_registry = SchemaRegistry()
schema_registry.load()

llm_provider = config.get_llm_provider()
vector_store = config.get_vector_store()

llm_caller = LLMCaller(llm_provider)
parser = DocumentParser()
chunker = Chunker()
indexer = Indexer(vector_store)
reranker = config.get_reranker()
retriever = Retriever(vector_store, reranker)
validator = Validator(schema_registry)
extractor = MetadataExtractor(schema_registry, validator, llm_caller)
session_manager = SessionManager(vector_store)
orchestrator = Orchestrator(session_manager, retriever, extractor, llm_caller, schema_registry)

# Initialize schema vector index on startup
try:
    schema_registry.build_index(indexer)
except Exception as e:
    print(f"Warning: Failed to build schema index on startup: {e}")

@app.errorhandler(Exception)
def handle_exception(e):
    # Handle 404 errors specifically to avoid noisy tracebacks in debug mode
    from werkzeug.exceptions import HTTPException, NotFound
    
    if isinstance(e, NotFound):
        if request.path.startswith('/api/'):
            return jsonify({"error": "Endpoint not found"}), 404
        return render_template("index.html"), 200 # Fallback to index for SPA-like behavior or just let it 404

    if request.path.startswith('/api/'):
        return jsonify({"error": str(e)}), 500
        
    # For non-API routes, re-raise the exception to use default handlers
    raise e

@app.route("/favicon.ico")
def favicon():
    return "", 204




@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/schema", methods=["GET"])
def get_schema():
    return jsonify(schema_registry.get_schema_for_ui())


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
        
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
        
    filename = secure_filename(file.filename)
    filepath = os.path.join(config.UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # Ensure session is created before headers are sent
    if "session_id" in session:
        session_manager.clear_document(session)
    else:
        session_manager.create(session)
        
    def generate():
        try:
            # --- Lock UI: block chat/edits during processing ---
            yield f"data: {json.dumps({'stage': 'lock_ui', 'message': 'Processing — please wait…'})}\n\n"

            yield f"data: {json.dumps({'stage': 'processing', 'message': 'Processing document…'})}\n\n"
            text, error = parser.parse(filepath, filename)
            if error:
                yield f"data: {json.dumps({'stage': 'unlock_ui'})}\n\n"
                yield f"data: {json.dumps({'error': error})}\n\n"
                return
                
            yield f"data: {json.dumps({'stage': 'analyzing', 'message': 'Analyzing content…'})}\n\n"
            chunks = chunker.chunk(text, filename)
            session["chunk_count"] = len(chunks)
            session["document_filename"] = filename
            
            yield f"data: {json.dumps({'stage': 'indexing', 'message': f'Building knowledge base ({len(chunks)} chunks)…'})}\n\n"
            
            def on_progress(current, total):
                pass # Optional: can send progress here if needed
                
            indexer.index(session["session_id"], chunks, on_progress=on_progress)
            
            # --- Phase 1: Single-pass structured extraction (fast) ---
            yield f"data: {json.dumps({'stage': 'extracting', 'message': 'Extracting metadata (single-pass)…'})}\n\n"
            
            result = extractor.extract_single_pass(retriever, session["session_id"])
            
            # Convert to serializable dict and emit all fields at once
            all_fields = {}
            for group_name, group_data in result.fields.items():
                group_dict = {}
                for k, v in group_data.items():
                    if dataclasses.is_dataclass(v):
                        group_dict[k] = dataclasses.asdict(v)
                    elif isinstance(v, dict):
                        group_dict[k] = v
                all_fields[group_name] = group_dict
            
            yield f"data: {json.dumps({'stage': 'metadata', 'metadata': all_fields})}\n\n"

            # --- Phase 2: Async refinement for null/low-confidence fields ---
            null_count = sum(
                1 for g in result.fields.values()
                for f in g.values() if f.value is None
            )
            
            if null_count > 0:
                yield f"data: {json.dumps({'stage': 'refining', 'message': f'Refining {null_count} missing fields…'})}\n\n"
                
                result = extractor.refine_missing_fields(result, retriever, session["session_id"])
                
                # Re-serialize and emit updated fields
                all_fields = {}
                for group_name, group_data in result.fields.items():
                    group_dict = {}
                    for k, v in group_data.items():
                        if dataclasses.is_dataclass(v):
                            group_dict[k] = dataclasses.asdict(v)
                        elif isinstance(v, dict):
                            group_dict[k] = v
                    all_fields[group_name] = group_dict

                yield f"data: {json.dumps({'stage': 'metadata', 'metadata': all_fields})}\n\n"

            session["extracted_metadata"] = all_fields

            # --- Unlock UI: re-enable chat/edits ---
            yield f"data: {json.dumps({'stage': 'unlock_ui'})}\n\n"
            yield f"data: {json.dumps({'stage': 'complete', 'message': 'Ready — metadata extracted', 'filename': filename})}\n\n"
            
        except Exception as e:
            # Revert session state if indexing fails
            session_manager.clear_document(session)
            yield f"data: {json.dumps({'stage': 'unlock_ui'})}\n\n"
            yield f"data: {json.dumps({'error': 'Indexing/Extraction failed: ' + str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/chat", methods=["POST"])
def chat():
    if "session_id" not in session:
        return jsonify({"error": "No active session. Please upload a document first."}), 400
        
    data = request.json or {}
    user_message = data.get("message", "")
    
    pipeline_request = PipelineRequest(
        session_id=session["session_id"],
        user_message=user_message,
        mode="interaction",
        schema_data=schema_registry.get_schema_for_ui(),
        extracted_metadata=session.get("extracted_metadata", {})
    )
    
    def generate():
        try:
            for event in orchestrator.execute(pipeline_request):
                if not event.startswith("data: ") and not event.startswith("\n\n"):
                    # basic chat chunk
                    yield f"data: {json.dumps({'content': event})}\n\n"
                else:
                    yield event
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/suggest", methods=["POST"])
def suggest_field():
    if "session_id" not in session:
        return jsonify({"error": "No active session."}), 400
        
    data = request.json or {}
    field_name = data.get("field_name")
    group_name = data.get("group_name")
    user_context = data.get("user_context")
    
    if not field_name or not group_name:
        return jsonify({"error": "Missing field_name or group_name"}), 400
        
    completion_req = CompletionRequest(
        session_id=session["session_id"],
        field_name=field_name,
        group_name=group_name,
        user_context=user_context
    )
    
    def generate():
        try:
            for event in orchestrator.execute_completion(completion_req):
                yield event
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/api/metadata/update", methods=["POST"])
def update_metadata():
    if "session_id" not in session:
        return jsonify({"error": "No active session."}), 400
        
    data = request.json or {}
    group_name = data.get("group_name")
    field_name = data.get("field_name")
    value = data.get("value")
    source = data.get("source", "user-provided")
    
    if not group_name or not field_name:
        return jsonify({"error": "Missing group_name or field_name"}), 400
        
    extracted = session.get("extracted_metadata", {})
    if group_name not in extracted:
        extracted[group_name] = {}
        
    if field_name not in extracted[group_name]:
        extracted[group_name][field_name] = {
            "field_name": field_name,
            "group_name": group_name,
            "confidence": "high",
            "evidence": None,
            "inference_type": "reported",
            "section": None
        }
        
    extracted[group_name][field_name]["value"] = value
    extracted[group_name][field_name]["source"] = source
    session["extracted_metadata"] = extracted
    
    return jsonify({"success": True, "updated_field": extracted[group_name][field_name]})

@app.route("/api/metadata", methods=["GET"])
def get_metadata():
    if "session_id" not in session:
        return jsonify({"error": "No active session."}), 400
    return jsonify(session.get("extracted_metadata", {}))

@app.route("/api/session", methods=["DELETE"])
def clear_session():
    if "session_id" in session:
        session_manager.clear_document(session)
    session.clear()
    return jsonify({"message": "Session cleared"})

if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)

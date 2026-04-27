"""
app.py — Flask backend for the Crop Development Research Assistant (Tri-Modal System).
"""

import os
import sys
import json
import uuid
import re
import difflib

# Ensure venv site-packages are on the path
VENV_SITE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "lib", "python3.12", "site-packages"
)
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

from flask import Flask, render_template, request, jsonify, Response, session
from flask_session import Session
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from openai import OpenAI

from manuscript_parser import extract_text
from retrieval_engine import chunk_text, embed_chunks, query_chunks, clear_session, build_schema_index, score_field_relevance, retrieve_evidence

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"))

app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flask_session")
os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
Session(app)

# Initialize LLM client
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "glm-4.7" if LLM_PROVIDER == "cerit" else "gpt-4o")

if LLM_PROVIDER == "cerit":
    client = OpenAI(
        api_key=os.getenv("CERIT_API_KEY"),
        base_url=os.getenv("CERIT_BASE_URL", "https://llm.ai.e-infra.cz/v1/")
    )
else:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Setup paths for upload and metadata
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

METADATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metadata")
SCHEMA_PATH = os.path.join(METADATA_DIR, "sample_metadata.json")
SKILL_PATH = os.path.join(METADATA_DIR, "extraction_skill.md")

# Load schema and skill once at startup
try:
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        SCHEMA_DATA = json.load(f)
    with open(SKILL_PATH, 'r', encoding='utf-8') as f:
        EXTRACTION_SKILL = f.read()
except Exception as e:
    print(f"Error loading metadata files: {e}")
    SCHEMA_DATA = {}
    EXTRACTION_SKILL = ""

def build_schema_maps(raw_schema):
    schema_for_llm = {}
    schema_for_ui = {}
    for group in raw_schema.get("field_groups", []):
        gname = group["group_name"]
        fields_llm = {}
        fields_ui = {}
        for field in group.get("fields", []):
            fname = field["name"]
            fields_llm[fname] = {
                "field_type": field.get("field_type"),
                "text_values": field.get("text_values")
            }
            fields_ui[fname] = {
                "field_type": field.get("field_type"),
                "text_values": field.get("text_values")
            }
        schema_for_llm[gname] = fields_llm
        schema_for_ui[gname] = {
            "restriction_type": group.get("restriction_type"),
            "fields": fields_ui
        }
    return schema_for_llm, schema_for_ui

SCHEMA_FOR_LLM, SCHEMA_FOR_UI = build_schema_maps(SCHEMA_DATA)

try:
    build_schema_index(SCHEMA_DATA, EXTRACTION_SKILL)
except Exception as e:
    print(f"Error building schema index: {e}")

def fuzzy_match_vocab(value, vocab):
    if not value or not vocab: return value, False
    matches = difflib.get_close_matches(str(value).lower(), [str(v).lower() for v in vocab], n=1, cutoff=0.8)
    if matches:
        for v in vocab:
            if str(v).lower() == matches[0]:
                return v, True
    return value, False

def validate_extraction(raw_json_str, schema_for_llm):
    try:
        data = json.loads(raw_json_str)
    except json.JSONDecodeError as e:
        return None, {"error": f"JSON parse failed: {e}"}
    
    validated = {}
    diagnostics = {"extracted": 0, "null": 0, "total": 0, "warnings": []}
    
    for group_name, fields_spec in schema_for_llm.items():
        group_data = data.get(group_name, {})
        if not isinstance(group_data, dict):
            diagnostics["warnings"].append(f"Group '{group_name}' is not a dict")
            group_data = {}
        
        validated_group = {}
        for field_name in fields_spec:
            diagnostics["total"] += 1
            field_val = group_data.get(field_name)
            
            if field_val is None:
                validated_group[field_name] = {"value": None, "evidence": None, "confidence": None}
                diagnostics["null"] += 1
            elif isinstance(field_val, dict) and "value" in field_val:
                validated_group[field_name] = field_val
                if field_val["value"] is not None:
                    diagnostics["extracted"] += 1
                else:
                    diagnostics["null"] += 1
            else:
                validated_group[field_name] = {"value": field_val, "evidence": None, "confidence": "medium"}
                diagnostics["extracted"] += 1
                diagnostics["warnings"].append(f"Field '{field_name}' had bare value, wrapped")
        
        validated[group_name] = validated_group
    
    return validated, diagnostics

@app.route("/")
def index():
    """Serve the main extraction interface."""
    return render_template("index.html")


@app.route("/api/schema")
def get_schema():
    """Return the schema field groups so the UI knows what to render."""
    return jsonify(SCHEMA_FOR_UI)


@app.route("/api/upload", methods=["POST"])
def upload():
    """
    Handle file upload, extract text, chunk, embed, and store in session.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(file.filename)
    ext = filename.lower().split('.')[-1]
    
    if ext not in ['pdf', 'txt', 'docx']:
        return jsonify({"error": f"Unsupported format: .{ext}. Only PDF, TXT, DOCX allowed."}), 400

    # Ensure a session ID exists
    if not session.get("session_id"):
        session["session_id"] = str(uuid.uuid4())
        session["chat_history"] = []
    
    # If a previous file was uploaded, clear its vector store
    if session.get("document_filename"):
        clear_session(session["session_id"])
        
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Extract text from document
    text, error = extract_text(file_path, filename)
    if error:
        return jsonify({"error": error}), 500
    if not text or not text.strip():
        return jsonify({"error": "Extracted text is empty or unreadable."}), 500

    session["document_text"] = text
    session["document_filename"] = filename
    session["extracted_metadata"] = None
    
    # Chunk and embed
    chunks = chunk_text(text, filename)
    embed_chunks(session["session_id"], chunks)

    return jsonify({"filename": filename, "chunk_count": len(chunks), "status": "success"})


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Handle chat messages and route to Extraction, Interaction, or Hybrid mode.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400
        
    user_message = data.get("message", "").strip()
    is_extraction_trigger = data.get("trigger_extraction", False)
    
    if not session.get("session_id"):
        session["session_id"] = str(uuid.uuid4())
        session["chat_history"] = []
        
    document_text = session.get("document_text")
    if not document_text:
        return jsonify({"error": "Please upload a document first."}), 400
        
    # Append to chat history
    if user_message:
        chat_history = session.get("chat_history", [])
        chat_history.append({"role": "user", "content": user_message})
        if len(chat_history) > 20:
            chat_history = chat_history[-20:]
        session["chat_history"] = chat_history

    # Determine mode
    mode = "interaction"
    if is_extraction_trigger or user_message.lower() in ["extract", "extract metadata", "extract data"]:
        mode = "extraction"
    elif user_message and session.get("extracted_metadata"):
        # Simple heuristic for hybrid mode: check if schema fields are mentioned
        schema_keys = str(SCHEMA_DATA).lower()
        words = set(re.findall(r'\w+', user_message.lower()))
        if any(w in schema_keys and len(w) > 4 for w in words):
             mode = "hybrid"

    # Route based on mode
    if mode == "extraction":
        return stream_extraction(session["session_id"], document_text)
    elif mode == "hybrid":
        return stream_hybrid(session["session_id"], user_message, session.get("extracted_metadata"))
    else:
        return stream_interaction(session["session_id"], user_message)


def stream_extraction(session_id, document_text):
    def generate():
        try:
            # Stage 1: Field Relevance Scoring
            yield f"data: {json.dumps({'status': 'extracting', 'mode': 'extraction', 'message': 'Finding relevant fields...'})}\n\n"
            relevant_groups = score_field_relevance(session_id, SCHEMA_DATA)
            
            all_results = {}
            for group_name, fields_llm in SCHEMA_FOR_LLM.items():
                if group_name not in relevant_groups:
                    all_results[group_name] = {
                        fname: {"value": None, "evidence": None, "confidence": None}
                        for fname in fields_llm
                    }
                    continue
                    
                field_names = list(fields_llm.keys())
                yield f"data: {json.dumps({'status': 'extracting', 'mode': 'extraction', 'message': f'Extracting {group_name}...'})}\n\n"
                
                # Stage 2: Evidence Retrieval
                evidence_chunks = retrieve_evidence(session_id, field_names, top_k=5)
                context = "\n\n".join(evidence_chunks)
                
                if not context.strip():
                    all_results[group_name] = {
                        fname: {"value": None, "evidence": None, "confidence": None}
                        for fname in fields_llm
                    }
                    continue
                    
                # Stage 3: Focused Extraction
                prompt = f"""Extract values for these fields from the text below.
For each field, return JSON: {{"field_name": {{"value": "...", "evidence": "verbatim quote", "confidence": "high|medium|low"}}}}
If a field cannot be found, set value to null.
Return JSON only.

Fields: {', '.join(field_names)}

Text:
{context}"""
                
                create_kwargs = {
                    "model": LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are a metadata extraction engine. Return JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.0
                }
                if LLM_PROVIDER == "openai":
                    create_kwargs["response_format"] = {"type": "json_object"}
                    
                response = client.chat.completions.create(**create_kwargs)
                raw_json = response.choices[0].message.content.strip()
                raw_json = re.sub(r'```(?:json)?\s*\n?(.*?)\n?```', r'\1', raw_json, flags=re.DOTALL).strip()
                
                try:
                    group_data = json.loads(raw_json)
                except Exception:
                    group_data = {}
                    
                # Post-processing & Validation
                validated_group = {}
                for fname in field_names:
                    fval = group_data.get(fname)
                    
                    if fval is None:
                        validated_group[fname] = {"value": None, "evidence": None, "confidence": None}
                    elif isinstance(fval, dict) and "value" in fval:
                        val = fval.get("value")
                        if val and fields_llm[fname].get("field_type") == "TEXT_CHOICE_FIELD":
                            matched_val, is_matched = fuzzy_match_vocab(val, fields_llm[fname].get("text_values", []))
                            if is_matched:
                                fval["value"] = matched_val
                        validated_group[fname] = fval
                    else:
                        val = fval
                        if val and fields_llm[fname].get("field_type") == "TEXT_CHOICE_FIELD":
                            matched_val, is_matched = fuzzy_match_vocab(val, fields_llm[fname].get("text_values", []))
                            if is_matched:
                                val = matched_val
                        validated_group[fname] = {"value": val, "evidence": None, "confidence": "medium"}
                        
                all_results[group_name] = validated_group
                
            validated_json, diag = validate_extraction(json.dumps(all_results), SCHEMA_FOR_LLM)
            if validated_json is None:
                yield f"data: {json.dumps({'error': diag['error']})}\n\n"
                return
                
            session["extracted_metadata"] = validated_json
            yield f"data: {json.dumps({'content': json.dumps(validated_json), 'mode': 'extraction'})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


def stream_interaction(session_id, user_message):
    chunks = query_chunks(session_id, user_message, top_k=5)
    context_text = "\n\n---\n\n".join([f"Chunk from {c['metadata']['source_file']}:\n{c['text']}" for c in chunks])
    
    system_prompt = """You are a helpful, document-grounded research assistant. 
Answer the user's question using ONLY the provided document context.
Do not hallucinate. If the answer is not in the context, explicitly state that you cannot find it in the uploaded document.
Always cite your evidence based on the context."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context chunks:\n\n{context_text}\n\nUser Question: {user_message}"}
    ]

    def generate():
        try:
            stream = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                stream=True,
                temperature=0.2
            )
            full_response = ""
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_response += delta.content
                    yield f"data: {json.dumps({'content': delta.content, 'mode': 'interaction'})}\n\n"
            
            # Update history
            chat_history = session.get("chat_history", [])
            chat_history.append({"role": "assistant", "content": full_response})
            session["chat_history"] = chat_history
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


def stream_hybrid(session_id, user_message, extracted_metadata):
    chunks = query_chunks(session_id, user_message, top_k=5)
    context_text = "\n\n---\n\n".join([f"Chunk from {c['metadata']['source_file']}:\n{c['text']}" for c in chunks])
    
    system_prompt = """You are a helpful, document-grounded research assistant. 
You have access to both retrieved text chunks from the document AND previously extracted structured metadata.
Answer the user's question by combining information from both sources. 
Reference the extracted metadata explicitly if it answers the question.
Do not hallucinate."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Extracted Metadata:\n{extracted_metadata}\n\nContext chunks:\n\n{context_text}\n\nUser Question: {user_message}"}
    ]

    def generate():
        try:
            stream = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                stream=True,
                temperature=0.2
            )
            full_response = ""
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_response += delta.content
                    yield f"data: {json.dumps({'content': delta.content, 'mode': 'hybrid'})}\n\n"
            
            chat_history = session.get("chat_history", [])
            chat_history.append({"role": "assistant", "content": full_response})
            session["chat_history"] = chat_history
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/session", methods=["DELETE"])
def clear_session_route():
    """Clear session data and delete vector store collection."""
    if session.get("session_id"):
        clear_session(session["session_id"])
    session.clear()
    return jsonify({"status": "success"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)

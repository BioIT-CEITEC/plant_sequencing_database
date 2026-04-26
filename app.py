"""
app.py — Flask backend for the Crop Development Research Assistant (Tri-Modal System).
"""

import os
import sys
import json
import uuid
import re

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
from retrieval_engine import chunk_text, embed_chunks, query_chunks, clear_session

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

# Initialize OpenAI client
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


@app.route("/")
def index():
    """Serve the main extraction interface."""
    return render_template("index.html")


@app.route("/api/schema")
def get_schema():
    """Return the schema field groups so the UI knows what to render."""
    return jsonify(SCHEMA_DATA)


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
        return stream_extraction(document_text)
    elif mode == "hybrid":
        return stream_hybrid(session["session_id"], user_message, session.get("extracted_metadata"))
    else:
        return stream_interaction(session["session_id"], user_message)


def stream_extraction(document_text):
    system_prompt = f"""You are an information extraction engine specialized in scientific text mining.
Your function is deterministic: extract structured metadata fields from unstructured scientific manuscripts using a predefined schema and extraction rules.
Return structured JSON only. Do not wrap the JSON in Markdown code blocks. Just output raw JSON.
Missing fields must be explicitly marked as null.
Follow the rich output format described in the extraction skill rules (value, evidence, confidence, section, inference_type).

# Rules & Schema
{EXTRACTION_SKILL}

# Target Schema Reference (Fields to extract)
{json.dumps(SCHEMA_DATA, indent=2)}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Extract metadata from the following manuscript text:\n\n{document_text[:100000]}"}
    ]

    def generate():
        try:
            stream = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                stream=True,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            full_json = ""
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_json += delta.content
                    yield f"data: {json.dumps({'content': delta.content, 'mode': 'extraction'})}\n\n"
            
            # Cache extracted metadata
            session["extracted_metadata"] = full_json
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
                model="gpt-4o",
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
                model="gpt-4o",
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

"""
app.py — Flask backend for the Crop Development Research Assistant.

Serves a split-screen web UI with:
- Left panel: GPT-4o chat interface
- Right panel: Dynamic form derived from crop_development_factors.docx

Routes:
    GET  /              → Serve the split-screen HTML
    GET  /api/form-data → Return document-derived form structure as JSON
    POST /api/chat      → Accept {message, form_context}, query subgraph, call GPT-4o
"""

import os
import sys
import json

# Ensure venv site-packages are on the path
VENV_SITE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "lib", "python3.12", "site-packages"
)
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

from flask import Flask, render_template, request, jsonify, Response
from dotenv import load_dotenv
from openai import OpenAI

from doc_parser import parse_crop_document, get_environment_sections
from knowledge_graph import build_knowledge_graph, export_graph, query_subgraph, GRAPH_PATH

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"))

# Initialize OpenAI client — API key from .env, never hardcoded
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load form data once at startup
FORM_DATA = get_environment_sections(parse_crop_document())

# Build knowledge graph at startup if it doesn't exist
if not os.path.exists(GRAPH_PATH):
    print("Building knowledge graph...")
    G = build_knowledge_graph()
    export_graph(G)
    print("Knowledge graph ready.")


SYSTEM_PROMPT = """You are an expert crop development research assistant specialized in European field conditions.
You help researchers understand and optimize environmental factors for crop growth in both laboratory and field settings.

Your expertise covers:
- Lab environment: controlled parameters (light, temperature, humidity, CO₂, pH, nutrients, VPD)
- Field environment: uncontrollable variables, partially controllable factors, EU-specific regulations
- General cultivation: genetics, operational variables, economic constraints
- EU agricultural regulations (CAP, pesticide, organic, nitrate directives)

Guidelines:
- Be precise and data-driven. Include specific ranges, values, and EU regulatory references when relevant.
- When comparing lab vs field environments, highlight the key trade-offs.
- If form context is provided, focus your response on those specific factors.
- Use the knowledge graph context to ground your answers in the document's factor relationships.
- Always consider European conditions (climate zones 4-9, EU regulatory framework).
"""


@app.route("/")
def index():
    """Serve the main split-screen interface."""
    return render_template("index.html")


@app.route("/api/form-data")
def get_form_data():
    """Return the document-derived form structure as JSON."""
    return jsonify(FORM_DATA)


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Handle chat requests with GPT-4o.

    Accepts JSON: {message: str, form_context: dict}
    - message: user's question
    - form_context: {environment: str, selected_factors: [str]}

    Queries the knowledge graph for relevant subgraph, combines with
    form context, and streams the GPT-4o response.
    """
    data = request.get_json()
    user_message = data.get("message", "").strip()
    form_context = data.get("form_context", {})

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Build context from knowledge graph subgraph
    try:
        graph_context = query_subgraph(user_message)
    except Exception:
        graph_context = ""

    # Build form context string
    form_context_str = ""
    if form_context:
        env = form_context.get("environment", "")
        factors = form_context.get("selected_factors", [])
        if env:
            form_context_str += f"\n\nUser is currently viewing: {env}\n"
        if factors:
            form_context_str += "Selected factors of interest:\n"
            form_context_str += "\n".join(f"- {f}" for f in factors)

    # Assemble messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    # Inject graph + form context as a system-level grounding message
    if graph_context or form_context_str:
        context_block = ""
        if graph_context:
            context_block += f"\n{graph_context}\n"
        if form_context_str:
            context_block += f"\n{form_context_str}\n"
        messages.append({
            "role": "system",
            "content": f"[Document Context]{context_block}"
        })

    messages.append({"role": "user", "content": user_message})

    # Stream response from GPT-4o
    def generate():
        """Generator that streams GPT-4o response chunks as SSE events."""
        try:
            stream = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=1500
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield f"data: {json.dumps({'content': delta.content})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True, port=5000)

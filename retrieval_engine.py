"""
retrieval_engine.py
Responsible for text chunking, embedding, vector storage, and retrieval.
Uses ChromaDB and OpenAI text-embedding-3-small.
"""
import os
import re
import json
import tiktoken
import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name="text-embedding-3-small"
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vector_store")
chroma_client = chromadb.PersistentClient(path=DB_PATH, settings=Settings(anonymized_telemetry=False))

def chunk_text(text: str, filename: str, chunk_size=512, overlap=50) -> list[dict]:
    """
    Structure-aware recursive splitter.
    Splits by double newline, then by sentence if chunks are too large.
    Uses tiktoken cl100k_base to count tokens.
    """
    enc = tiktoken.get_encoding("cl100k_base")
    
    # Pre-split into paragraphs
    paragraphs = re.split(r'\n\n+', text)
    
    chunks = []
    current_chunk_text = ""
    current_chunk_tokens = []
    
    for para in paragraphs:
        if not para.strip():
            continue
            
        para_tokens = enc.encode(para)
        
        # If the paragraph itself is larger than chunk size, we need to split it by sentence
        if len(para_tokens) > chunk_size:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
                sentence_tokens = enc.encode(sentence)
                if len(current_chunk_tokens) + len(sentence_tokens) > chunk_size and current_chunk_text:
                    chunks.append({
                        "text": current_chunk_text.strip(),
                        "source_file": filename,
                        "token_count": len(current_chunk_tokens)
                    })
                    overlap_tokens = current_chunk_tokens[-overlap:] if overlap > 0 else []
                    current_chunk_text = enc.decode(overlap_tokens) + " " + sentence
                    current_chunk_tokens = overlap_tokens + sentence_tokens
                else:
                    current_chunk_text += (" " + sentence if current_chunk_text else sentence)
                    current_chunk_tokens.extend(sentence_tokens)
                    
        else:
            if len(current_chunk_tokens) + len(para_tokens) > chunk_size and current_chunk_text:
                chunks.append({
                    "text": current_chunk_text.strip(),
                    "source_file": filename,
                    "token_count": len(current_chunk_tokens)
                })
                overlap_tokens = current_chunk_tokens[-overlap:] if overlap > 0 else []
                current_chunk_text = enc.decode(overlap_tokens) + "\n\n" + para
                current_chunk_tokens = overlap_tokens + para_tokens
            else:
                current_chunk_text += ("\n\n" + para if current_chunk_text else para)
                current_chunk_tokens.extend(para_tokens)
                
    if current_chunk_text:
        chunks.append({
            "text": current_chunk_text.strip(),
            "source_file": filename,
            "token_count": len(current_chunk_tokens)
        })
        
    for i, chunk in enumerate(chunks):
        chunk["chunk_index"] = i
        
    return chunks

def embed_chunks(session_id: str, chunks: list[dict]):
    """
    Store chunks in ChromaDB. Collection name is tied to session_id.
    """
    collection = chroma_client.get_or_create_collection(
        name=f"session_{session_id}",
        embedding_function=openai_ef
    )
    
    ids = []
    documents = []
    metadatas = []
    
    for chunk in chunks:
        ids.append(f"chunk_{chunk['chunk_index']}")
        documents.append(chunk["text"])
        metadatas.append({
            "source_file": chunk["source_file"],
            "chunk_index": chunk["chunk_index"]
        })
        
    if documents:
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

def query_chunks(session_id: str, question: str, top_k: int = 5) -> list[dict]:
    """
    Retrieve top_k chunks for the given session_id.
    """
    try:
        collection = chroma_client.get_collection(
            name=f"session_{session_id}",
            embedding_function=openai_ef
        )
    except Exception:
        return []
        
    results = collection.query(
        query_texts=[question],
        n_results=top_k
    )
    
    if not results['documents'] or not results['documents'][0]:
        return []
        
    retrieved = []
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        retrieved.append({
            "text": doc,
            "metadata": meta
        })
        
    return retrieved

def clear_session(session_id: str):
    """
    Delete the ChromaDB collection for the session.
    """
    try:
        chroma_client.delete_collection(name=f"session_{session_id}")
    except Exception:
        pass

def build_schema_index(schema_data, skill_text):
    """
    Build a semantic index of schema field groups to determine relevance.
    """
    collection = chroma_client.get_or_create_collection(
        name="schema_fields",
        embedding_function=openai_ef
    )
    
    # Simple check if already built (in prod, use hash checking)
    if collection.count() > 0:
        return
        
    lines = skill_text.split('\n')
    guidance_map = {}
    for line in lines:
        if line.startswith('| `'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 5:
                fname = parts[1].replace("`", "").strip()
                guidance = parts[4]
                guidance_map[fname] = guidance
                
    documents = []
    metadatas = []
    ids = []
    
    for i, group in enumerate(schema_data.get("field_groups", [])):
        group_name = group["group_name"]
        
        for field in group.get("fields", []):
            fname = field["name"]
            ftype = field.get("field_type")
            guidance = guidance_map.get(fname, "")
            
            # Create a rich description for embedding
            text_repr = f"Group: {group_name} | Field: {fname} | Type: {ftype} | Guidance: {guidance}"
            if "text_values" in field and field["text_values"]:
                text_repr += f" | Values: {', '.join(field['text_values'][:10])}"
                
            documents.append(text_repr)
            metadatas.append({"group_name": group_name, "field_name": fname})
            ids.append(f"schema_{fname}")
            
    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)

def score_field_relevance(session_id: str, schema_data) -> list[str]:
    """
    Query the document chunks against the schema index to find relevant field groups.
    Returns a list of relevant group names.
    """
    try:
        doc_collection = chroma_client.get_collection(
            name=f"session_{session_id}",
            embedding_function=openai_ef
        )
        schema_collection = chroma_client.get_collection(
            name="schema_fields",
            embedding_function=openai_ef
        )
    except Exception:
        return [g["group_name"] for g in schema_data.get("field_groups", [])]

    # Get a sample of document chunks (up to 20) to find what it's about
    docs = doc_collection.get(limit=20)
    if not docs or not docs['documents']:
        return [g["group_name"] for g in schema_data.get("field_groups", [])]

    # Combine document chunks into a single large query (or a few)
    query_text = " ".join(docs['documents'])[:8000] # truncate to avoid token limits
    
    # Ask schema collection which fields match this document
    results = schema_collection.query(
        query_texts=[query_text],
        n_results=15  # Get top 15 most relevant fields
    )
    
    if not results['metadatas'] or not results['metadatas'][0]:
        return [g["group_name"] for g in schema_data.get("field_groups", [])]
        
    relevant_groups = set()
    for meta in results['metadatas'][0]:
        relevant_groups.add(meta['group_name'])
        
    return list(relevant_groups)

def retrieve_evidence(session_id: str, field_names: list[str], top_k: int = 5) -> list[str]:
    """
    Retrieve top_k chunks for a specific group of fields.
    """
    query = ", ".join(field_names)
    chunks = query_chunks(session_id, query, top_k)
    return [c["text"] for c in chunks]


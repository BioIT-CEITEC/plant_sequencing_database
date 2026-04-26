"""
retrieval_engine.py
Responsible for text chunking, embedding, vector storage, and retrieval.
Uses ChromaDB and OpenAI text-embedding-3-small.
"""
import os
import re
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

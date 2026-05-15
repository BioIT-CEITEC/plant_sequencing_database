from core.vector_store import VectorStore
from core.contracts import Chunk
from typing import List

class Indexer:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def index(self, session_id: str, chunks: List[Chunk], batch_size: int = 15, on_progress=None) -> None:
        """
        Embeds chunks and stores them in the vector store under the session_id collection in batches.
        """
        if not chunks:
            return

        self.vector_store.create_collection(name=session_id)
        
        total = len(chunks)
        for i in range(0, total, batch_size):
            batch_chunks = chunks[i:i + batch_size]
            documents = []
            metadatas = []
            ids = []
            
            for j, chunk in enumerate(batch_chunks):
                documents.append(chunk.text)
                
                meta = chunk.metadata.copy() if chunk.metadata else {}
                meta.update({
                    "source_file": chunk.source_file,
                    "section": chunk.section,
                    "chunk_index": chunk.chunk_index,
                    "token_count": chunk.token_count
                })
                metadatas.append(meta)
                
                ids.append(f"chunk_{i+j}")
                
            self.vector_store.add(
                collection=session_id,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            if on_progress:
                on_progress(min(i + batch_size, total), total)

    def delete(self, session_id: str) -> None:
        """
        Deletes the entire collection for a given session.
        """
        self.vector_store.delete_collection(name=session_id)

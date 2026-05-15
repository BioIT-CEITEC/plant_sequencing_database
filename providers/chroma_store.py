import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
from core.vector_store import VectorStore
from core.contracts import RetrievalResult
from core.embedding_provider import EmbeddingProvider
from chromadb.utils import embedding_functions

class CustomEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __init__(self, provider: EmbeddingProvider):
        self.provider = provider
        
    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        return self.provider.embed(input)

class ChromaVectorStore(VectorStore):
    def __init__(self, db_path: str, embedding_provider: EmbeddingProvider):
        self.client = chromadb.PersistentClient(path=db_path, settings=Settings(anonymized_telemetry=False))
        self.embedding_function = CustomEmbeddingFunction(embedding_provider)

    def create_collection(self, name: str) -> None:
        self.client.get_or_create_collection(
            name=name,
            embedding_function=self.embedding_function
        )

    def add(self, collection: str, documents: List[str],
            metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        col = self.client.get_or_create_collection(
            name=collection,
            embedding_function=self.embedding_function
        )
        if documents:
            col.add(documents=documents, metadatas=metadatas, ids=ids)

    def query(self, collection: str, query_texts: List[str],
              n_results: int) -> List[List[RetrievalResult]]:
        try:
            col = self.client.get_collection(
                name=collection,
                embedding_function=self.embedding_function
            )
        except Exception:
            return [[] for _ in query_texts]

        results = col.query(
            query_texts=query_texts,
            n_results=n_results
        )
        
        if not results['documents']:
            return [[] for _ in query_texts]
            
        all_retrieval_results = []
        for i in range(len(query_texts)):
            query_results = []
            if i < len(results['documents']) and results['documents'][i]:
                distances = results['distances'][i] if results.get('distances') else [0.0]*len(results['documents'][i])
                for doc, meta, distance in zip(
                    results['documents'][i], 
                    results['metadatas'][i],
                    distances
                ):
                    score = 1.0 / (1.0 + distance) if distance is not None else 1.0
                    query_results.append(RetrievalResult(
                        text=doc,
                        section=meta.get("section", "Document") if meta else "Document",
                        score=score,
                        source="semantic",
                        metadata=meta or {}
                    ))
            all_retrieval_results.append(query_results)
            
        return all_retrieval_results

    def delete_collection(self, name: str) -> None:
        try:
            self.client.delete_collection(name=name)
        except Exception:
            pass

    def count(self, collection: str) -> int:
        try:
            col = self.client.get_collection(name=collection)
            return col.count()
        except Exception:
            return 0

    def get(self, collection: str, limit: int = None) -> Dict[str, Any]:
        try:
            col = self.client.get_collection(name=collection)
            return col.get(limit=limit) if limit else col.get()
        except Exception:
            return {"documents": [], "metadatas": [], "ids": []}

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from .contracts import RetrievalResult

class VectorStore(ABC):
    @abstractmethod
    def create_collection(self, name: str) -> None:
        """Ensure a collection exists."""
        pass

    @abstractmethod
    def add(self, collection: str, documents: List[str],
            metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        """Add documents to a collection."""
        pass

    @abstractmethod
    def query(self, collection: str, query_texts: List[str],
              n_results: int) -> List[List[RetrievalResult]]:
        """Query a collection, returning lists of results for each query."""
        pass

    @abstractmethod
    def delete_collection(self, name: str) -> None:
        """Delete a collection entirely."""
        pass

    @abstractmethod
    def count(self, collection: str) -> int:
        """Get number of items in collection."""
        pass

    @abstractmethod
    def get(self, collection: str, limit: int = None) -> Dict[str, Any]:
        """Get items from collection, typically returning documents and metadatas."""
        pass

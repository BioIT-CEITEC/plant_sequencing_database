from typing import List
from chromadb.utils import embedding_functions
from core.embedding_provider import EmbeddingProvider

class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model_name: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model_name = model_name
        self.ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.api_key,
            model_name=self.model_name
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.ef(texts)

    @property
    def dimension(self) -> int:
        return 1536

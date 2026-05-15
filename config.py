import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

class Config:
    def __init__(self):
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "cerit")
        self.LLM_MODEL = os.getenv("LLM_MODEL", "glm-5.1" if self.LLM_PROVIDER == "cerit" else "gpt-4o")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.CERIT_API_KEY = os.getenv("CERIT_API_KEY")
        self.CERIT_BASE_URL = os.getenv("CERIT_BASE_URL", "https://llm.ai.e-infra.cz/v1/")
        
        # Embedding configuration — defaults to CERIT
        self.EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "cerit")
        self.EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "qwen3-embedding-4b")
        self.RERANKER_MODEL = os.getenv("RERANKER_MODEL", "qwen3-reranker-4b")
        
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.UPLOAD_FOLDER = os.path.join(self.BASE_DIR, "documents")
        self.METADATA_DIR = os.path.join(self.BASE_DIR, "metadata")
        self.SCHEMA_PATH = os.path.join(self.METADATA_DIR, "sample_metadata_2.json")
        self.SKILL_PATH = os.path.join(self.METADATA_DIR, "extraction_skill.md")
        self.VECTOR_STORE_DIR = os.path.join(self.BASE_DIR, "vector_store")
        
    def get_llm_provider(self):
        """Factory for LLM providers (chat/completion)."""
        if self.LLM_PROVIDER == "cerit":
            from providers.cerit_llm import CeritLLMProvider
            return CeritLLMProvider(self.CERIT_API_KEY, self.CERIT_BASE_URL, self.LLM_MODEL)
        else:
            from providers.openai_llm import OpenAILLMProvider
            return OpenAILLMProvider(self.OPENAI_API_KEY, self.LLM_MODEL)
            
    def get_embedding_provider(self):
        """Factory for embedding providers. Defaults to CERIT."""
        if self.EMBEDDING_PROVIDER == "cerit":
            from providers.cerit_embeddings import CeritEmbeddingProvider
            return CeritEmbeddingProvider(
                api_key=self.CERIT_API_KEY,
                base_url=self.CERIT_BASE_URL,
                model_name=self.EMBEDDING_MODEL
            )
        else:
            from providers.openai_embeddings import OpenAIEmbeddingProvider
            return OpenAIEmbeddingProvider(self.OPENAI_API_KEY)
            
    def get_reranker(self):
        """Factory for reranker."""
        from retrieval.reranker import CeritReranker
        return CeritReranker(
            api_key=self.CERIT_API_KEY,
            base_url=self.CERIT_BASE_URL,
            model_name=self.RERANKER_MODEL
        )
        
    def get_vector_store(self):
        """Factory for vector stores."""
        from providers.chroma_store import ChromaVectorStore
        return ChromaVectorStore(self.VECTOR_STORE_DIR, self.get_embedding_provider())

# Global config instance
config = Config()

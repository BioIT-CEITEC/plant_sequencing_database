"""
CERIT embedding provider with rate limiting, caching, and exponential backoff.
Supports Qwen3-Embedding-4B and other CERIT-hosted embedding models.
"""
import hashlib
import random
import time
from collections import OrderedDict
from typing import List

from openai import OpenAI
from core.embedding_provider import EmbeddingProvider
from core.rate_limiter import EmbeddingRateLimiter


class CeritEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using CERIT's OpenAI-compatible API.
    
    Supports multiple models: multilingual-e5-large-instruct, mxbai-embed-large,
    nomic-embed-text-v1.5, nomic-embed-text-v2-moe, qwen3-embedding-4b.
    """
    
    # Known dimensions per model to avoid discovery overhead
    KNOWN_DIMENSIONS = {
        "multilingual-e5-large-instruct": 1024,
        "mxbai-embed-large:latest": 1024,
        "nomic-embed-text-v1.5": 768,
        "nomic-embed-text-v2-moe": 768,
        "qwen3-embedding-4b": 2560,
    }

    MAX_CACHE_SIZE = 500
    MAX_RETRIES = 3

    def __init__(self, api_key: str, base_url: str, model_name: str = "multilingual-e5-large-instruct"):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self._dimension = self.KNOWN_DIMENSIONS.get(model_name)
        self._cache = OrderedDict()           # md5(text) → embedding vector
        self._rate_limiter = EmbeddingRateLimiter(max_concurrent=3, min_interval=0.1)
        self._cache_hits = 0
        self._cache_misses = 0

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings with cache-first lookup and rate-limited API calls."""
        try:
            results = [None] * len(texts)
            uncached_indices = []
            uncached_texts = []

            # Phase 1: Check cache
            for i, text in enumerate(texts):
                key = hashlib.md5(text.encode()).hexdigest()
                if key in self._cache:
                    results[i] = self._cache[key]
                    self._cache.move_to_end(key)    # LRU refresh
                    self._cache_hits += 1
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(text)
                    self._cache_misses += 1

            # Phase 2: Call API only for cache misses
            if uncached_texts:
                self._rate_limiter.acquire()
                try:
                    embeddings = self._call_api_with_backoff(uncached_texts)
                    for idx, emb in zip(uncached_indices, embeddings):
                        key = hashlib.md5(texts[idx].encode()).hexdigest()
                        self._cache[key] = emb
                        results[idx] = emb

                    # LRU eviction
                    while len(self._cache) > self.MAX_CACHE_SIZE:
                        self._cache.popitem(last=False)
                finally:
                    self._rate_limiter.release()

            # Cache dimension from first successful response
            if self._dimension is None and results and results[0]:
                self._dimension = len(results[0])

            total = self._cache_hits + self._cache_misses
            if total > 0 and total % 50 == 0:
                print(f"[EmbeddingCache] hits={self._cache_hits} misses={self._cache_misses} "
                      f"rate={self._cache_hits/total:.0%} size={len(self._cache)}")

            return results
        except Exception as e:
            raise RuntimeError(f"CERIT embedding failed for model '{self.model_name}': {e}") from e

    def _call_api_with_backoff(self, texts: List[str]) -> List[List[float]]:
        """Call embedding API with exponential backoff + jitter on 429 errors."""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=texts
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                error_str = str(e)
                if '429' in error_str and attempt < self.MAX_RETRIES:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    print(f"[EmbeddingProvider] 429 rate-limited (attempt {attempt+1}/{self.MAX_RETRIES}). "
                          f"Retrying in {wait:.1f}s...")
                    time.sleep(wait)
                else:
                    raise

    @property
    def dimension(self) -> int:
        """Return the dimension of the embeddings."""
        if self._dimension is not None:
            return self._dimension
        # Discovery fallback: embed a probe text to determine dimension
        try:
            probe = self.embed(["dimension probe"])
            self._dimension = len(probe[0])
            return self._dimension
        except Exception:
            return 1024  # Safe fallback for e5-large

from typing import List
from core.contracts import RetrievalResult
from openai import OpenAI

class CeritReranker:
    def __init__(self, api_key: str, base_url: str, model_name: str = "qwen3-reranker-4b"):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=30.0)

    def rerank(self, query: str, results: List[RetrievalResult], top_k: int = 5) -> List[RetrievalResult]:
        if not results:
            return []

        # The API expects a list of text strings for 'documents'
        documents = [res.text for res in results]

        try:
            # We hit the /rerank endpoint (without /v1) as discovered in testing
            # However, the OpenAI client's base_url already has /v1/, so we can use post('/rerank') 
            # Or construct the URL manually if OpenAI client appends /v1/ to everything.
            # Actually, standard OpenAI client with base_url="https://llm.ai.e-infra.cz/v1/"
            # `client.post('/rerank', ...)` hit `https://llm.ai.e-infra.cz/v1/rerank`.
            response = self.client.post(
                "/rerank", 
                cast_to=object, 
                body={
                    "model": self.model_name,
                    "query": query,
                    "documents": documents
                }
            )
            
            # response format: {'results': [{'index': 0, 'relevance_score': 0.82}]}
            reranked_results = []
            
            # Create a sorted list based on relevance_score
            for item in response.get("results", []):
                idx = item.get("index")
                score = item.get("relevance_score", 0.0)
                
                original_result = results[idx]
                # Update the score (replace or combine)
                original_result.score = score
                reranked_results.append(original_result)

            # Sort descending by score
            reranked_results.sort(key=lambda x: x.score, reverse=True)
            
            return reranked_results[:top_k]

        except Exception as e:
            print(f"Reranker failed: {e}. Falling back to original ranking.")
            return results[:top_k]

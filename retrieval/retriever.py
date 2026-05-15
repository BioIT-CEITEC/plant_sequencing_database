import math
from typing import List, Dict, Any, Optional
from core.vector_store import VectorStore
from core.contracts import RetrievalResult
from retrieval.reranker import CeritReranker

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

class Retriever:
    def __init__(self, vector_store: VectorStore, reranker: Optional[CeritReranker] = None):
        self.vector_store = vector_store
        self.reranker = reranker
        self._bm25_cache = {}

    def semantic_search(self, session_id: str, query: str, top_k: int) -> List[RetrievalResult]:
        """Perform semantic search using VectorStore."""
        results_lists = self.vector_store.query(
            collection=session_id,
            query_texts=[query],
            n_results=top_k
        )
        if not results_lists:
            return []
        
        return results_lists[0]

    def keyword_search(self, session_id: str, query: str, top_k: int) -> List[RetrievalResult]:
        """Perform BM25 keyword search over all chunks in session collection."""
        if not BM25Okapi:
            return []

        if session_id in self._bm25_cache:
            bm25, docs, metas = self._bm25_cache[session_id]
        else:
            data = self.vector_store.get(collection=session_id)
            docs = data.get("documents", [])
            metas = data.get("metadatas", [])
            
            if not docs:
                return []

            tokenized_corpus = [doc.lower().split() for doc in docs]
            bm25 = BM25Okapi(tokenized_corpus)
            self._bm25_cache[session_id] = (bm25, docs, metas)
        
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for i in top_indices:
            if scores[i] <= 0:
                continue
            meta = metas[i] if i < len(metas) and metas[i] else {}
            score = min(1.0, scores[i] / 10.0) 
            results.append(RetrievalResult(
                text=docs[i],
                section=meta.get("section", "Document"),
                score=score,
                source="keyword",
                metadata=meta
            ))
        return results

    def _validate_chunk_relevance(self, chunk_text: str, field: dict, min_keyword_hits: int = 1) -> bool:
        """Check if chunk contains at least min_keyword_hits from field's vocabulary or name."""
        text_lower = chunk_text.lower()
        
        # Build keyword list from field name
        field_name_words = field["name"].replace("_", " ").lower().split()
        keywords = set(field_name_words)
        
        # Add vocabulary values
        if "text_values" in field:
            for val in field["text_values"]:
                # split values into words or keep as whole phrase
                keywords.add(val.lower())
                
        # Count hits
        hits = sum(1 for kw in keywords if kw in text_lower)
        return hits >= min_keyword_hits

    def per_field_retrieval(self, session_id: str, field: dict, schema_registry, top_k: int = 5) -> List[RetrievalResult]:
        """Retrieve chunks relevant to a SINGLE field using expanded queries."""
        queries = schema_registry.get_field_queries(field)
        all_results = []
        
        for q in queries:
            results = self.hybrid_query(session_id, q, top_k=top_k*2)
            all_results.extend(results)
            
        # Deduplicate by chunk_index
        seen = set()
        unique_results = []
        for res in all_results:
            chunk_idx = res.metadata.get("chunk_index", res.text)
            if chunk_idx not in seen:
                seen.add(chunk_idx)
                unique_results.append(res)
                
        # Validate relevance
        validated_results = [res for res in unique_results if self._validate_chunk_relevance(res.text, field)]
        
        # Sort by score descending and return top_k
        validated_results.sort(key=lambda x: x.score, reverse=True)
        return validated_results[:top_k]

    def hybrid_query(self, session_id: str, query: str, top_k: int, use_reranker: bool = True) -> List[RetrievalResult]:
        """Combines semantic and keyword search using RRF, then reranks."""
        fetch_k = top_k * 2
        
        semantic_results = self.semantic_search(session_id, query, fetch_k)
        keyword_results = self.keyword_search(session_id, query, fetch_k)
        
        fused = self._reciprocal_rank_fusion([semantic_results, keyword_results])
        
        if use_reranker and self.reranker and fused:
            fused = self.reranker.rerank(query, fused)
            
        return fused[:top_k]

    def _reciprocal_rank_fusion(self, result_lists: List[List[RetrievalResult]], k: int = 60) -> List[RetrievalResult]:
        """Fuses multiple ranked lists using Reciprocal Rank Fusion."""
        rrf_scores = {}
        result_map = {}
        
        for result_list in result_lists:
            for rank, result in enumerate(result_list):
                chunk_index = result.metadata.get("chunk_index", hash(result.text))
                key = f"{chunk_index}"
                
                if key not in rrf_scores:
                    rrf_scores[key] = 0.0
                    result_map[key] = result
                    
                rrf_scores[key] += 1.0 / (k + rank + 1)
                
        sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        fused_results = []
        for key in sorted_keys:
            res = result_map[key]
            res.score = rrf_scores[key]
            res.source = "hybrid"
            fused_results.append(res)
            
        return fused_results

    def score_field_relevance(self, session_id: str, schema_registry) -> List[str]:
        # Using schema index from VectorStore. Assuming SchemaRegistry provides a way to query.
        # Or just directly query schema_index collection
        results = self.vector_store.query(
            collection="schema_index",
            query_texts=["identify relevant fields for document"],
            n_results=10
        )
        if not results or not results[0]:
            return []
            
        groups = set()
        for res in results[0]:
            if "group_name" in res.metadata:
                groups.add(res.metadata["group_name"])
        return list(groups)

    def retrieve_evidence(self, session_id: str, field_names: List[str], top_k: int = 8) -> List[RetrievalResult]:
        """Dedicated retrieve method for extraction evidence."""
        return self.field_aware_search(session_id, field_names, top_k)

    def compute_top_k(self, document_token_count: int, max_context_tokens: int = 3000, chunk_size: int = 512) -> int:
        """Dynamic top_k based on document length and limits."""
        if document_token_count <= 0:
            return 5
        ideal_k = math.ceil(max_context_tokens / chunk_size)
        doc_chunks = math.ceil(document_token_count / chunk_size)
        return min(ideal_k, doc_chunks)

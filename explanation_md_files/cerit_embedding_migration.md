# Implementation Plan: Migrate to CERIT Embedding Models

## Problem
OpenAI API quota is exhausted. The embedding provider (`text-embedding-3-small`) is hardcoded as the only option, blocking document upload/indexing/retrieval.

## Discovery Results

**Available CERIT Embedding Models** (tested 2026-05-05):

| Model | Dimension | Latency (3 texts) | Status |
|---|---|---|---|
| `multilingual-e5-large-instruct` | 1024 | 0.04s | OK |
| `mxbai-embed-large:latest` | 1024 | 0.04s | OK |
| `nomic-embed-text-v1.5` | 768 | 0.04s | OK |
| `nomic-embed-text-v2-moe` | 768 | 0.04s | OK |
| `qwen3-embedding-4b` | 2560 | 0.37s | OK |

> [!TIP]
> Also available: `qwen3-reranker-4b` (reranker, not embedding — 404 on embeddings endpoint, likely needs a different API pattern).

### Recommended Default: `multilingual-e5-large-instruct`

| Criteria | Why e5-large-instruct |
|---|---|
| **Multilingual** | Handles Czech + English scientific text natively |
| **Dimension** | 1024 — good balance of quality vs. storage |
| **Latency** | 0.04s — 10x faster than qwen3-embedding-4b |
| **Proven quality** | Microsoft's E5 family is MTEB-benchmarked, top-tier for retrieval |
| **Instruction-tuned** | Supports query/passage instruction prefixes for better retrieval |

---

## Tasks

### Task 1 — Create CERIT Embedding Provider
- **File:** `providers/cerit_embeddings.py`
- **What:** New `CeritEmbeddingProvider(EmbeddingProvider)` using `openai.OpenAI` client pointed at CERIT base URL
- **Key detail:** Must dynamically detect dimension from first response (varies per model)

### Task 2 — Add Embedding Config to Config + .env
- **File:** `config.py`, `.env`
- **What:** Add `EMBEDDING_PROVIDER` and `EMBEDDING_MODEL` env vars; update `get_embedding_provider()` factory
- **Default:** `EMBEDDING_PROVIDER=cerit`, `EMBEDDING_MODEL=multilingual-e5-large-instruct`

### Task 3 — Fix ChromaDB Integration
- **File:** `providers/chroma_store.py`
- **What:** Remove the OpenAI-specific shortcut (`if hasattr(embedding_provider, 'ef')`) — always use the generic `CustomEmbeddingFunction` wrapper for provider-agnostic behavior

### Task 4 — Clear Stale Vector Store
- **Action:** Delete existing `vector_store/` directory (it was created with OpenAI 1536-dim embeddings, incompatible with new 1024-dim)

### Task 5 — Validate End-to-End
- **Test:** Run `test_upload.py` to verify parse → chunk → embed → index pipeline works with CERIT embeddings

# 🧠 Codebase Memory — Document Research Assistant

> Operational reference for working on this codebase. Complements `CODEBASE_WORKING_TREE.md` (full structural detail) with decision context, patterns, gotchas, and call chains.
>
> **Reflects the current modular architecture after the major refactor.** Legacy monolithic files (`manuscript_parser.py`, `retrieval_engine.py`, `extract_fields.py`, `assess_field_derivability.py`) have been deleted.

**Last updated:** May 2026

---

## 1. What This System Does (30 seconds)

Flask app → user uploads a scientific manuscript (PDF/DOCX/TXT) → system:
1. Parses to raw text
2. Chunks section-aware (~600 tokens each)
3. Embeds + indexes in ChromaDB
4. **Phase 1:** Single-pass extraction (1 LLM call → all fields)
5. **Phase 2:** Parallel async refinement for null/low-confidence fields
6. Serves a chat UI for Q&A over the document + interactive field editing with AI hints

Domain: plant-genomics / soil-microbiome. Schema: environmental sample metadata (ERC000022).

---

## 2. Architectural Patterns

### Provider Pattern (Dependency Injection via `config.py`)

```
core/ ABCs                    providers/ implementations         config.py wires at startup
─────────────                  ──────────────────────────          ────────────────────────
EmbeddingProvider  ◄───────  CeritEmbeddingProvider               config.get_embedding_provider()
                  ◄───────  OpenAIEmbeddingProvider               ↳ injected into ChromaVectorStore

LLMProvider        ◄───────  CeritLLMProvider                     config.get_llm_provider()
                  ◄───────  OpenAILLMProvider                     ↳ injected into LLMCaller

VectorStore        ◄───────  ChromaVectorStore                    config.get_vector_store()
                                                                  ↳ receives EmbeddingProvider via DI
```

**Key point:** `ChromaVectorStore` never imports a concrete embedding provider. It receives an `EmbeddingProvider` instance through `CustomEmbeddingFunction`, which wraps any implementation. Swapping CERIT ↔ OpenAI embeddings requires only changing `.env` — zero code changes.

### Pipeline Pattern (Strategy via `orchestration/pipelines.py`)

```
Orchestrator.detect_mode() → selects one of 4 pipelines:
  "interaction"  → QAPipeline          (retrieve → prompt → stream)
  "extraction"   → ExtractionPipeline  (sequential group-by-group extraction)
  "hybrid"       → HybridPipeline      (Q&A + metadata, post-response extraction)
  "completion"   → CompletionPipeline   (single-field AI suggestion)
```

All pipelines implement `BasePipeline.run(request) → Generator[str]`. Output is always SSE-formatted strings.

---

## 3. Three Extraction Strategies — When and Why

| | 🟢 Batch (`extract_single_pass`) | 🟡 Async Refinement (`refine_missing_fields`) | 🔵 Sequential (`extract_all`) |
|---|---|---|---|
| **LLM calls** | 1 (all groups in one prompt) | N (1 per null/low field, parallel) | N (1 per group, sequential) |
| **Retrieval** | 3 broad domain queries → top 15 chunks | Per-field targeted retrieval (top_k=3) | Per-field retrieval (top_k=5) |
| **Prompt** | `build_full_extraction()` | `build_extraction()` (single-field) | `build_extraction()` (per-group, with field_contexts) |
| **Parallelism** | None (single call) | `ThreadPoolExecutor(max_workers=3)` | None (sequential) |
| **Quality** | Broad coverage, may miss niche fields | Targeted — better for specific gaps | Most thorough per-field, but very slow |
| **Speed** | Fastest (~5 API calls total) | Moderate (parallel, rate-limited) | Slowest (~N round-trips) |
| **Called by** | `app.py` `/api/upload` Phase 1 | `app.py` `/api/upload` Phase 2 (if nulls exist) | `ExtractionPipeline` (chat-triggered fallback) |
| **Trigger** | Automatic after indexing | Automatic if any fields are null/low | User types "extract", "metadata", etc. in chat |
| **Status label** | `"Extracting metadata (single-pass)…"` | `"Refining N missing fields…"` | Chat SSE with extracting_evidence status |

A fourth method, `extract_from_response()`, is called by `HybridPipeline` after every hybrid chat response to opportunistically discover fields mentioned in the AI's answer.

**`source` field provenance across strategies:**
- `"auto-extracted"` — Phase 1 single-pass
- `"auto-refined"` — Phase 2 async refinement (new)
- `"ai-suggested"` — ✨ Ask AI button (CompletionPipeline)
- `"user-provided"` — Manual edit via /api/metadata/update

---

## 4. Call Chain Quick Reference

### Upload → Two-Phase Extraction
```
/api/upload (POST, SSE streaming)
  │
  ├─ lock_ui SSE event              ← frontend disables chat/edits
  │
  ├─ DocumentParser.parse()           [ingestion/parser.py]
  ├─ Chunker.chunk()                   [ingestion/chunker.py]         → List[Chunk]
  ├─ Indexer.index()                   [indexing/indexer.py]          → ChromaDB collection
  │
  ├─ Phase 1: extract_single_pass()   [extraction/extractor.py]
  │   ├─ 3 broad hybrid_queries → top 15 chunks (deduplicated)
  │   ├─ PromptBuilder.build_full_extraction()
  │   ├─ llm_caller.complete(json_mode=True)
  │   ├─ validator.validate() per group
  │   └─ SSE: {stage: "metadata", metadata: all_fields}
  │
  ├─ Phase 2 (if nulls > 0): refine_missing_fields()
  │   ├─ Collect null/low-confidence fields
  │   ├─ ThreadPoolExecutor(max_workers=3)
  │   │   └─ per field: retriever.per_field_retrieval(top_k=3)
  │   │   └─ build_extraction() → llm_caller.complete()
  │   └─ SSE: {stage: "metadata", metadata: updated_all_fields}
  │
  ├─ unlock_ui SSE event             ← frontend re-enables chat/edits
  └─ SSE: {stage: "complete", filename: "..."}
```

### Chat Q&A
```
/api/chat (POST)
  → Orchestrator.execute()
    → detect_mode() → "interaction"
    → QAPipeline.run()
      → Retriever.hybrid_query()
        → semantic_search()           [ChromaDB vector search]
        → keyword_search()            [BM25Okapi, cached per session]
        → _reciprocal_rank_fusion()   [k=60]
        → CeritReranker.rerank()      [POST /rerank, graceful fallback]
      → PromptBuilder.build_qa()      [context + last 4 history msgs]
      → LLMCaller.stream()           [SSE chunks]
```

### Chat-Triggered Extraction (Legacy Fallback)
```
/api/chat (POST, mode="extraction")
  → Orchestrator.execute()
    → detect_mode() → "extraction"
    → ExtractionPipeline.run()
      → MetadataExtractor.extract_all()  ← SEQUENTIAL strategy (legacy)
        → For each group:
          → retriever.per_field_retrieval(field_info, top_k=5)
          → PromptBuilder.build_extraction(field_contexts=...)
          → llm_caller.complete(json_mode=True)
          → validator.validate()
```

### Field Hints (✨ Ask AI)
```
/api/suggest (POST)
  → Orchestrator.execute_completion()
    → CompletionPipeline.run()
      → Lookup field_info from schema_registry.group_map
      → retriever.retrieve_evidence([field_name], top_k=5)
      → PromptBuilder.build_field_completion()  [includes controlled vocab]
      → llm_caller.complete(json_mode=True)
      → Parse → FieldSuggestion → SSE yield
```

**⚠️ Mismatch note:** Backend yields `{field_suggestion: {...}}` but frontend parses `{field_hints: {hints: [...]}}`. See gotcha #5.

### User Edit (Inline Dropdown/Input)
```
/api/metadata/update (POST)
  → Direct session dict update (no LLM call)
  → source: "user-provided"
  → Frontend: input.classList.add('user-modified')
  → Frontend: userModifiedFields.add(`${groupName}.${fieldKey}`)
```

---

## 5. Data Contracts Cheat Sheet

| Contract | Created By | Consumed By | Key Fields |
|---|---|---|---|
| `Chunk` | Chunker.chunk() | Indexer, PromptBuilder | text, section, chunk_index, token_count |
| `RetrievalResult` | ChromaVectorStore.query(), BM25 | Retriever, Reranker | text, section, score, source ("semantic"/"keyword"/"hybrid") |
| `FieldExtraction` | Validator.validate() | Extractor, stored in session | value, evidence, confidence, inference_type, source |
| `FieldSuggestion` | CompletionPipeline | Frontend (/api/suggest) | suggested_value, confidence, evidence, alternatives |
| `ExtractionResult` | Extractor | Pipelines, /api/upload | fields (group→field→FieldExtraction), diagnostics |
| `PipelineRequest` | app.py /api/chat | Orchestrator | session_id, user_message, mode, extracted_metadata |
| `CompletionRequest` | app.py /api/suggest | Orchestrator | session_id, field_name, group_name, user_context |
| `DocumentSession` | SessionManager.create() | (defined but not persisted — Flask dicts used instead) | session_id, filename, chat_history, extracted_metadata |

**`source` field on FieldExtraction** — all current values:
- `"auto-extracted"` — Phase 1 single-pass
- `"auto-refined"` — Phase 2 async refinement
- `"ai-suggested"` — ✨ Ask AI button
- `"user-provided"` — Manual edit

---

## 6. Configuration & Environment

| Variable | Default | Effect |
|---|---|---|
| `LLM_PROVIDER` | `"cerit"` | `"cerit"` → glm-5.1; `"openai"` → gpt-4o |
| `EMBEDDING_PROVIDER` | `"cerit"` | `"cerit"` → qwen3-embedding-4b (2560-dim); `"openai"` → text-embedding-3-small (1536-dim) |
| `EMBEDDING_MODEL` | `"qwen3-embedding-4b"` | Any model in `CeritEmbeddingProvider.KNOWN_DIMENSIONS` |
| `RERANKER_MODEL` | `"qwen3-reranker-4b"` | Must support /rerank endpoint |
| `CERIT_BASE_URL` | `"https://llm.ai.e-infra.cz/v1/"` | CERIT OpenAI-compatible API |
| `SCHEMA_PATH` | `metadata/sample_metadata_2.json` | Active schema (6 groups). Switch to `sample_metadata.json` for all 24 groups |
| `SKILL_PATH` | `metadata/extraction_skill.md` | LLM skill instructions injected into extraction prompts |

**⚠️ Dimension mismatch is fatal:** If you change `EMBEDDING_MODEL` to one with a different dimension, you MUST delete the `vector_store/` directory. ChromaDB collections are dimension-locked — mixing 1024-dim and 2560-dim embeddings in the same collection causes runtime errors.

---

## 7. External Services

| Service | Endpoint | Auth | Notes |
|---|---|---|---|
| CERIT Chat | `POST /v1/chat/completions` | `CERIT_API_KEY` | OpenAI-compatible. Does NOT support `response_format` for JSON mode |
| CERIT Embeddings | `POST /v1/embeddings` | `CERIT_API_KEY` | Supports multiple models (see KNOWN_DIMENSIONS) |
| CERIT Reranker | `POST /v1/rerank` | `CERIT_API_KEY` | Non-standard endpoint. Uses `client.post("/rerank")` — not part of OpenAI SDK spec |
| OpenAI Chat | `POST /v1/chat/completions` | `OPENAI_API_KEY` | Full `response_format` support for JSON mode |
| OpenAI Embeddings | `POST /v1/embeddings` | `OPENAI_API_KEY` | `text-embedding-3-small` (1536-dim) |

---

## 8. Score Mathematics

**ChromaDB → RetrievalResult score:** `score = 1.0 / (1.0 + distance)`
- ChromaDB returns cosine *distance* (0 = identical, 2 = opposite)
- Mapping: distance 0 → 1.0, distance 1 → 0.5, distance 2 → 0.33

**BM25 → RetrievalResult score:** `score = min(1.0, raw_bm25_score / 10.0)`
- Raw BM25 scores are unbounded; capped at 1.0 for comparability

**Reciprocal Rank Fusion (RRF):** `rrf_score = Σ 1/(k + rank + 1)` across lists, k=60
- Deduplicates by `chunk_index` from metadata
- After RRF, reranker replaces scores with `relevance_score` from cross-encoder

---

## 9. Chunking Strategy Details

- **Tokenizer:** `tiktoken` cl100k_base (class-level cached)
- **Split:** `\n\n+` (double newlines = paragraph boundaries)
- **Heading detection:** 17 regex patterns + numbered subsection fallback
- **Section boundary:** forces chunk flush (no cross-section chunks)
- **Target:** 600 tokens (soft), 4000 tokens (hard ceiling)
- **No overlap** between chunks (section-aligned chunks are self-contained)
- **Fallback:** sentence-level splitting only when a single paragraph exceeds `max_chunk_size`
- **Metadata preserved:** `section` name on every Chunk

---

## 10. Validation Logic

**Fuzzy vocabulary matching** (`validator.py`):
- For `TEXT_CHOICE_FIELD` values: `SequenceMatcher` ratio ≥ 0.8 → normalize to canonical form
- No match → keep value but downgrade `confidence` to `"low"`
- Nullification: strings `"not mentioned"`, `"null"`, `"none"` (case-insensitive) → `None`

**Evidence checking** (currently defined but not enforced in extract flow):
- `fuzzy_evidence_match()`: substring match OR SequenceMatcher ratio > 0.6

---

## 11. Schema Structure

**Active schema** (`sample_metadata_2.json`) — 6 groups, ~10 fields:
```
field_groups: [
  { group_name: "Organism characteristics: ecosystem",
    fields: [
      { name: "trophic_level", field_type: "TEXT_CHOICE_FIELD", text_values: [...] },
      { name: "observed_biotic_relationship", ... },
      { name: "relationship_to_oxygen", ... }
    ]},
  { group_name: "local environment conditions: soil",
    fields: [{ name: "soil_type", text_values: [32 FAO types] }]},
  { group_name: "non-sample terms",
    fields: [{ name: "sequence_quality_check", text_values: [manual/none/software] }]},
  { group_name: "Organism characteristics",
    fields: [{ name: "geographic_location_country_andor_sea", text_values: [country list] }]},
  { group_name: "local environment conditions",
    fields: [soil_horizon, drainage_classification, profile_position]},
  { group_name: "local environment history",
    fields: [{ name: "historytillage", text_values: [9 tillage types] }]}
]
```

**Parsed into two maps** by `SchemaRegistry.build_maps()`:
- `flat_schema`: `{field_name → field_def}` — used for field lookups, prompt building
- `group_map`: `{group_name → [field_defs]}` — used for iteration, validation grouping

**Schema index:** `SchemaRegistry.build_index()` creates a `schema_index` ChromaDB collection at startup, enabling semantic search over group/field descriptions for relevance scoring.

---

## 12. Prompt Templates Summary

| Template | Method | Mode | Temperature | JSON Mode | Output Format |
|---|---|---|---|---|---|
| QA | `build_qa()` | interaction | 0.3 (stream) | No | Free text (markdown) |
| Hybrid | `build_hybrid()` | hybrid | 0.3 (stream) | No | Free text + background extraction |
| Per-Group Extraction | `build_extraction()` | extraction / refinement | 0.0 | Yes | Flat `{field: {value, evidence, confidence}}` — now supports `field_contexts` param |
| Full Extraction | `build_full_extraction()` | upload Phase 1 | 0.0 | Yes | Nested `{group: {field: {...}}}` |
| Post-Response | `build_post_response()` | hybrid (bg) | 0.0 | Yes | `{field: value}` (only new fields) |
| Field Completion | `build_field_completion()` | completion | 0.0 | Yes | `{field_name, suggested_value, confidence, evidence, inference_type, alternatives}` |

---

## 13. Session State

**Flask server-side filesystem sessions** hold a dict with:
```
session = {
  "session_id":         str (UUID),
  "document_filename":  str | None,
  "chunk_count":        int,
  "extracted_metadata": Dict[group_name, Dict[field_name, FieldExtraction_dict]],
  "chat_history":       List[Dict]  (populated but NOT currently passed to build_qa correctly — see gotchas)
}
```

**`DocumentSession` dataclass** exists in `core/contracts.py` but is NOT actually used for persistence — `SessionManager.create()` operates on plain dicts. The dataclass is dead code.

**BM25 cache** lives in `Retriever._bm25_cache`: `{session_id: (bm25_model, docs_list, metas_list)}` — in-memory only, survives for process lifetime, never invalidated on re-upload.

---

## 14. Frontend ↔ Backend Protocol

All async responses use **Server-Sent Events (SSE)** (`text/event-stream`).

**Upload SSE stages (current — two-phase extraction):**
```
data: {"stage": "lock_ui", "message": "Processing — please wait…"}     ← UI lock
data: {"stage": "processing", "message": "Processing document…"}      → 15%
data: {"stage": "analyzing", "message": "Analyzing content…"}       → 30%
data: {"stage": "indexing", "message": "Building knowledge base…"}  → 50%
data: {"stage": "extracting", "message": "Extracting metadata (single-pass)…"}  → 70%
data: {"stage": "metadata", "metadata": {...}}                      → 90%  ← Phase 1 payload
data: {"stage": "refining", "message": "Refining N missing fields…"}  → 85%  ← Phase 2 start
data: {"stage": "metadata", "metadata": {...}}                      → 90%  ← Phase 2 updated payload
data: {"stage": "unlock_ui"}                                         ← UI unlock
data: {"stage": "complete", "message": "Ready", "filename": "..."}  → 100%
data: {"error": "..."}                                              → on any failure (also sends unlock_ui)
```

**Chat SSE events:**
```
data: {"content": "..."}                            → streaming text chunk
data: {"status": "extracting_evidence"}             → extraction in progress
data: {"metadata": {...}}                           → extraction result
data: {"metadata_update": {...}}                    → post-response discovery (hybrid mode)
data: {"response_metadata": {...}}                  → alternative key (hybrid mode)
data: {"field_suggestion": {...}}                   → completion result (backend)
data: {"field_hints": {hints: [...]}}               ← what frontend expects (MISMATCH — see gotcha #5)
data: {"error": "..."}                              → on any failure
```

---

## 15. Frontend Architecture

### Key UI Components
- **Searchable Dropdown** (`createSearchableDropdown()`): For TEXT_CHOICE_FIELD — uses a "portal" pattern (appends dropdown list to `document.body`) to escape `overflow:hidden` containers. Repositions on scroll.
- **Inline Edit Input**: For TEXT_FIELD — standard `<input>` with change listener
- **Stop Button** (`stopBtn`): Uses `AbortController` to cancel streaming requests
- **Progress Bar** (`uploadProgress`): Maps SSE stages to CSS width percentages
- **UI Lock** (`setExtractionLock(locked)`): Disables chat input, send, attach, all dropdowns/inputs, hides ✨ Ask AI buttons during extraction
- **User-Modified Tracking** (`userModifiedFields` Set): Prevents auto-extracted values from overwriting user edits during `renderMetadata()`

### Rendering Flow
1. `init()` → fetch schema → `renderEmptySchema()` builds skeleton with dropdowns/inputs
2. Upload → SSE metadata → `renderMetadata()` updates values **in-place** (doesn't rebuild DOM)
3. User edit → `saveField()` → POST `/api/metadata/update` → re-fetch `/api/metadata` → `renderMetadata()`
4. ✨ Ask AI → `suggestField()` → POST `/api/suggest` → shows hints popover or "no hints found"

---

## 16. Known Gotchas & Technical Debt

| # | Issue | Impact | Where |
|---|---|---|---|
| 1 | **CeritLLMProvider ignores `json_mode`** | Extraction relies on prompt-only JSON instruction; no API enforcement | `providers/cerit_llm.py:complete()` |
| 2 | **`DocumentSession` is dead code** | SessionManager uses plain dicts, not the dataclass | `orchestration/session_manager.py` vs `core/contracts.py` |
| 3 | **BM25 cache never invalidated** | Re-uploading without clearing session keeps stale BM25 index | `retrieval/retriever.py:_bm25_cache` |
| 4 | **Chat history not wired to LLM** | `build_qa()` accepts `chat_history` but `QAPipeline` passes `None` | `orchestration/pipelines.py:QAPipeline.run()` |
| 5 | **⚡ Frontend/backend SSE key mismatch** | Backend `CompletionPipeline` yields `{field_suggestion: {...}}`; frontend `suggestField()` parses `{field_hints: {hints: [...]}}`. **Suggestions will silently fail to render.** | `orchestration/pipelines.py` vs `templates/index.html:suggestField()` |
| 6 | **`statNull` is a mock object** | `const statNull = { textContent: '0' }` — not a real DOM element. Null count never displays correctly. | `templates/index.html` |
| 7 | **`SchemaRegistry.parse_xml()` stub** | XML parsing not implemented | `extraction/schema_registry.py` |
| 8 | **Partial upload now has rollback** | ✅ FIXED — `app.py` catches exceptions and calls `session_manager.clear_document(session)` | `app.py:upload_file()` |
| 9 | **Reranker uses non-standard `client.post()`** | May break on OpenAI SDK updates | `retrieval/reranker.py` |
| 10 | **Dimension change requires manual cleanup** | Switching embedding model without deleting `vector_store/` causes dimension mismatch crash | `config.py` ↔ `providers/chroma_store.py` |
| 11 | **Refinement race condition potential** | `refine_missing_fields()` uses ThreadPoolExecutor but mutates `result.fields` dict concurrently — safe only because each thread writes a different key | `extraction/extractor.py:refine_missing_fields()` |
| 12 | **`SECRET_KEY` regenerated every restart** | `os.urandom(24)` means all Flask sessions are invalidated on server restart | `app.py` |

**Previously listed gotchas now resolved:**
- ~~Frontend undefined JS references~~ → ✅ `togglePanelBtn`, `closePanelBtn`, `statExtracted`, `statTotal` now exist in HTML
- ~~`renderEmptySchema()` key mismatch~~ → ✅ Now handles both `field_groups` and `groups` keys
- ~~Partial upload no rollback~~ → ✅ Now has exception handler with `clear_document()`

---

## 17. Deleted Files (from refactor)

These legacy monolithic files have been removed and their functionality distributed across the modular architecture:

| Deleted File | Functionality moved to |
|---|---|
| `manuscript_parser.py` | `ingestion/parser.py` (DocumentParser class) |
| `retrieval_engine.py` | `ingestion/chunker.py`, `indexing/indexer.py`, `retrieval/retriever.py` |
| `extract_fields.py` | `extraction/schema_registry.py` (XML→JSON conversion) |
| `assess_field_derivability.py` | `metadata/field_derivability_assessment.json` (pre-computed output) |
| `test_parser.py` | Removed (no replacement) |
| `code_graph.json` | Regenerated on demand by `code_knowledge.py` |

---

## 18. Quick File Locator

| I need to... | File |
|---|---|
| Change the chunking logic | `ingestion/chunker.py` |
| Add a new LLM provider | New file in `providers/` + update `config.py` factory |
| Change the extraction prompt | `reasoning/prompt_builder.py` |
| Add a new pipeline mode | `orchestration/pipelines.py` + `orchestration/orchestrator.py` |
| Add a new API endpoint | `app.py` |
| Change the schema (add/remove groups) | `metadata/sample_metadata_2.json` |
| Fix the validation/fuzzy matching | `extraction/validator.py` |
| Change the retrieval strategy | `retrieval/retriever.py` |
| Switch embedding/LLM provider | `.env` file (no code changes needed) |
| Fix the frontend metadata panel | `templates/index.html` — `renderMetadata()` function |
| Fix the searchable dropdown | `templates/index.html` — `createSearchableDropdown()` |
| Fix the ✨ Ask AI flow | `templates/index.html:suggestField()` + `orchestration/pipelines.py:CompletionPipeline` |
| Add a new data contract | `core/contracts.py` |
| Change the extraction skill instructions | `metadata/extraction_skill.md` |
| Debug SSE stream format | Check `app.py` route → pipeline `.run()` → yield format |
| Change the refinement parallelism | `extraction/extractor.py:refine_missing_fields(max_workers=3)` |
| Change the broad queries for single-pass | `extraction/extractor.py:extract_single_pass()` → `broad_queries` list |

---

## 19. Dependency Versions (Critical Ones)

| Package | Version | Why It Matters |
|---|---|---|
| `chromadb` | 1.5.8 | Vector store engine. API may change across majors |
| `openai` | 2.31.0 | SDK for both CERIT + OpenAI. `client.post()` is non-standard |
| `tiktoken` | 0.12.0 | Tokenizer for chunking. cl100k_base encoding |
| `PyMuPDF` | 1.27.2.2 | PDF parsing. `fitz.open()` API |
| `rank_bm25` | (via pip) | BM25Okapi for keyword search. Optional import — gracefully disabled if missing |
| `tree-sitter` | 0.25.2 | Code knowledge graph only. NOT in runtime pipeline |
| `flask` | 3.1.3 | Web framework. `stream_with_context()` required for SSE |
| `flask-session` | 0.8.0 | Server-side filesystem sessions |
| `concurrent.futures` | (stdlib) | Used by `refine_missing_fields()` for parallel extraction |
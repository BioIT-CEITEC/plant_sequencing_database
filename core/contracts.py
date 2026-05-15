from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
from datetime import datetime

@dataclass
class Chunk:
    text: str
    chunk_index: int
    source_file: str
    section: str
    token_count: int
    overlap_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RetrievalResult:
    text: str
    section: str
    score: float
    source: str           # "semantic" | "keyword" | "field_aware"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FieldExtraction:
    field_name: str
    group_name: str
    value: Optional[str]
    evidence: Optional[str]
    confidence: Optional[str]  # "high" | "medium" | "low"
    inference_type: Optional[str]  # "reported" | "inferred"
    section: Optional[str]
    source: Optional[str] = "auto-extracted"  # "auto-extracted" | "ai-suggested" | "user-provided"

@dataclass
class FieldSuggestion:
    field_name: str
    group_name: str
    suggested_value: Optional[str]
    confidence: str
    evidence: Optional[str]
    inference_type: str
    alternatives: List[str]

@dataclass
class CompletionRequest:
    session_id: str
    field_name: str
    group_name: str
    user_context: Optional[str] = None

@dataclass
class ExtractionDiagnostics:
    total_fields: int
    extracted_count: int
    null_count: int
    warnings: List[str]
    relevant_groups: List[str]

@dataclass
class ExtractionResult:
    fields: Dict[str, Dict[str, FieldExtraction]]  # group -> field -> extraction
    diagnostics: ExtractionDiagnostics

@dataclass
class PipelineRequest:
    session_id: str
    user_message: str
    mode: str                # "interaction" | "extraction" | "hybrid"
    schema_data: Optional[Dict]
    extracted_metadata: Optional[Dict]

@dataclass
class PipelineResponse:
    content: str
    mode: str
    metadata: Optional[ExtractionResult]
    streaming: bool = True

@dataclass
class DocumentSession:
    session_id: str
    document_filename: Optional[str]
    document_text: Optional[str]
    chat_history: List[Dict]
    extracted_metadata: Optional[Dict]
    chunk_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

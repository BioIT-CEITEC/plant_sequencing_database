"""
Orchestrator — Routes user requests to the appropriate pipeline
based on query classification (conversational vs document-grounded).
"""
import re
from typing import Generator
from core.contracts import PipelineRequest, CompletionRequest
from orchestration.pipelines import QAPipeline, ExtractionPipeline, HybridPipeline, CompletionPipeline, ConversationalPipeline

# Patterns that indicate a simple conversational message (no RAG needed)
CONVERSATIONAL_PATTERNS = [
    r'^(hi|hey|hello|greetings|good\s+(morning|afternoon|evening))\b',
    r'^(thanks|thank\s+you|thx|cheers)\b',
    r'^(ok|okay|sure|yes|no|yep|nope|alright)\b',
    r'^(bye|goodbye|see\s+you)\b',
    r'^(what\s+can\s+you\s+do|who\s+are\s+you|help)\b',
    r'^(how\s+are\s+you)',
]


class Orchestrator:
    def __init__(self, session_mgr, retriever, extractor, reasoner, schema_registry):
        self.pipelines = {
            "interaction": QAPipeline(retriever, reasoner),
            "extraction": ExtractionPipeline(retriever, extractor, schema_registry),
            "hybrid": HybridPipeline(retriever, reasoner, extractor),
            "completion": CompletionPipeline(retriever, reasoner, schema_registry),
            "conversational": ConversationalPipeline(reasoner),
        }

    def detect_mode(self, request: PipelineRequest) -> str:
        """Classify query to avoid unnecessary embedding generation.
        
        Routes greetings/casual chat to a lightweight LLM path that
        skips retrieval entirely, eliminating embedding API calls for
        messages like 'Hey' that previously triggered 429 errors.
        """
        msg = request.user_message.strip().lower()
        word_count = len(msg.split())

        # Short messages matching conversational patterns → no RAG
        if word_count <= 6:
            for pattern in CONVERSATIONAL_PATTERNS:
                if re.match(pattern, msg):
                    return "conversational"

        # No document uploaded → conversational fallback
        if not request.extracted_metadata:
            # Still check if user has a session with a document
            # If no metadata at all, they haven't uploaded anything
            if word_count <= 4:
                return "conversational"

        # Mentions metadata group names → hybrid (metadata-aware)
        if request.extracted_metadata:
            if any(k.lower() in msg for k in request.extracted_metadata.keys()):
                return "hybrid"

        return "interaction"

    def execute(self, request: PipelineRequest) -> Generator[str, None, None]:
        mode = self.detect_mode(request)
        pipeline = self.pipelines[mode]
        yield from pipeline.run(request)
        
    def execute_completion(self, request: CompletionRequest) -> Generator[str, None, None]:
        yield from self.pipelines["completion"].run(request)

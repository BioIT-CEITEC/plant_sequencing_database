import json
import dataclasses
from abc import ABC, abstractmethod
from typing import Generator
from core.contracts import PipelineRequest, CompletionRequest, FieldSuggestion
from reasoning.llm_caller import LLMCaller
from reasoning.prompt_builder import PromptBuilder
from retrieval.retriever import Retriever
from extraction.extractor import MetadataExtractor
from extraction.schema_registry import SchemaRegistry

class BasePipeline(ABC):
    @abstractmethod
    def run(self, request: PipelineRequest) -> Generator[str, None, None]:
        pass

class QAPipeline(BasePipeline):
    def __init__(self, retriever: Retriever, llm_caller: LLMCaller):
        self.retriever = retriever
        self.llm_caller = llm_caller

    def run(self, request: PipelineRequest) -> Generator[str, None, None]:
        top_k = self.retriever.compute_top_k(3000)
        chunks = self.retriever.hybrid_query(request.session_id, request.user_message, top_k=top_k)
        
        prompt = PromptBuilder.build_qa(chunks, request.user_message, chat_history=None)
        
        yield from self.llm_caller.stream(prompt)


class ConversationalPipeline(BasePipeline):
    """Lightweight chat — no embeddings, no retrieval, no reranking.
    Used for greetings, casual messages, and queries without a document loaded.
    """
    def __init__(self, llm_caller: LLMCaller):
        self.llm_caller = llm_caller

    def run(self, request: PipelineRequest) -> Generator[str, None, None]:
        messages = [
            {"role": "system", "content": (
                "You are a helpful scientific research assistant for the Document Research Assistant application. "
                "Answer conversationally. If the user asks about document content, analysis, or metadata, "
                "tell them to upload a document first using the attachment button (📎)."
            )},
            {"role": "user", "content": request.user_message}
        ]
        yield from self.llm_caller.stream(messages)

class ExtractionPipeline(BasePipeline):
    def __init__(self, retriever: Retriever, extractor: MetadataExtractor, schema_registry: SchemaRegistry):
        self.retriever = retriever
        self.extractor = extractor
        self.schema_registry = schema_registry

    def run(self, request: PipelineRequest) -> Generator[str, None, None]:
        yield "data: {\"status\": \"extracting_evidence\"}\n\n"
        
        relevant_groups = list(self.schema_registry.group_map.keys())
        
        result = self.extractor.extract_all(relevant_groups, self.retriever, request.session_id)
        
        fields_dict = {
            g: {f: dataclasses.asdict(ext) for f, ext in fields.items()}
            for g, fields in result.fields.items()
        }
        
        yield f"data: {json.dumps({'metadata': fields_dict})}\n\n"

class CompletionPipeline(BasePipeline):
    """Returns contextual hints for a field, NOT direct answers.
    Helps user discover/infer the correct value from document evidence.
    """
    def __init__(self, retriever: Retriever, llm_caller: LLMCaller, schema_registry: SchemaRegistry):
        self.retriever = retriever
        self.llm_caller = llm_caller
        self.schema_registry = schema_registry

    def run(self, request: CompletionRequest) -> Generator[str, None, None]:
        # 1. Lookup field info from schema
        field_info = None
        for f in self.schema_registry.group_map.get(request.group_name, []):
            if f["name"] == request.field_name:
                field_info = f
                break
                
        if not field_info:
            yield f"data: {json.dumps({'error': 'Field not found'})}\n\n"
            return
            
        # 2. Retrieve relevant chunks for this specific field
        chunks = self.retriever.per_field_retrieval(
            request.session_id, field_info, self.schema_registry, top_k=5
        )
        
        # 3. Build contextual hints prompt (NOT direct answer)
        prompt = PromptBuilder.build_field_hints(
            field_info=field_info,
            group_name=request.group_name,
            context_chunks=chunks
        )
        
        # 4. Call LLM for hints
        try:
            raw_response = self.llm_caller.complete(prompt, temperature=0.2, json_mode=True)
            import re
            clean_json = re.sub(r'```json\n?|\n?```', '', raw_response).strip()
            raw_json = json.loads(clean_json)
            
            hints = raw_json.get("hints", [])
            if not hints:
                hints = ["No relevant information found in the document for this field."]
            
            yield f"data: {json.dumps({'field_hints': {'field_name': request.field_name, 'group_name': request.group_name, 'hints': hints}})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': 'Failed to generate hints: ' + str(e)})}\n\n"

class HybridPipeline(BasePipeline):
    def __init__(self, retriever: Retriever, llm_caller: LLMCaller, extractor: MetadataExtractor):
        self.retriever = retriever
        self.llm_caller = llm_caller
        self.extractor = extractor

    def run(self, request: PipelineRequest) -> Generator[str, None, None]:
        top_k = self.retriever.compute_top_k(3000)
        chunks = self.retriever.hybrid_query(request.session_id, request.user_message, top_k=top_k)
        
        prompt = PromptBuilder.build_hybrid(chunks, request.user_message, request.extracted_metadata)
        
        full_response = ""
        for chunk in self.llm_caller.stream(prompt):
            full_response += chunk
            yield chunk
            
        new_metadata = self.extractor.extract_from_response(full_response)
        if new_metadata:
            yield f"\n\ndata: {json.dumps({'metadata_update': new_metadata})}\n\n"

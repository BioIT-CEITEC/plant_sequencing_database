"""
Metadata extractor with single-pass and async refinement strategies.

Primary strategy: Single-pass structured extraction (1 retrieval + 1 LLM call → all fields).
Secondary strategy: Targeted async refinement for null/low-confidence fields only.
"""
import json
import re
import concurrent.futures
from typing import Dict, Any, List
from core.contracts import ExtractionResult, ExtractionDiagnostics, FieldExtraction
from reasoning.llm_caller import LLMCaller
from reasoning.prompt_builder import PromptBuilder


class MetadataExtractor:
    def __init__(self, schema_registry, validator, llm_caller: LLMCaller):
        self.schema_registry = schema_registry
        self.validator = validator
        self.llm_caller = llm_caller

    def extract_single_pass(self, retriever, session_id: str) -> ExtractionResult:
        """Single-pass: 3 broad queries + 1 LLM call → all fields at once.
        
        Replaces the previous per-field sequential extraction that caused
        ~84 API roundtrips with just ~5 calls total.
        """
        all_fields = {}
        total_fields = 0
        extracted_count = 0
        warnings = []

        # Phase 1: Retrieve top chunks using broad domain queries (3 embedding calls)
        broad_queries = [
            "experimental methods organism species taxonomy classification",
            "results findings data measurements conditions environment",
            "materials growth medium culture isolation characteristics"
        ]

        all_chunks = []
        seen_chunks = set()
        for q in broad_queries:
            try:
                results = retriever.hybrid_query(session_id, q, top_k=8, use_reranker=True)
                for r in results:
                    chunk_id = r.metadata.get("chunk_index", hash(r.text))
                    if chunk_id not in seen_chunks:
                        seen_chunks.add(chunk_id)
                        all_chunks.append(r)
            except Exception as e:
                warnings.append(f"Broad query failed: {e}")

        # Sort by relevance score, take top 15 for context window
        all_chunks.sort(key=lambda x: x.score, reverse=True)
        context = "\n\n".join([r.text for r in all_chunks[:15]])

        if not context.strip():
            warnings.append("No document context retrieved — extraction may be empty")

        # Phase 2: Single LLM call with full schema
        prompt = PromptBuilder.build_full_extraction(
            self.schema_registry.group_map, context, self.schema_registry.skill_text
        )

        try:
            raw_response = self.llm_caller.complete(prompt, temperature=0.0, json_mode=True)
            clean_json = re.sub(r'```json\n?|\n?```', '', raw_response).strip()
            raw_json = json.loads(clean_json)
        except Exception as e:
            warnings.append(f"Failed to generate valid JSON from LLM: {str(e)}")
            raw_json = {}

        # Phase 3: Validate per-group
        for group_name, fields in self.schema_registry.group_map.items():
            total_fields += len(fields)
            group_json = raw_json.get(group_name, {})

            try:
                validated_group = self.validator.validate(group_name, group_json)
                all_fields[group_name] = validated_group

                for f in validated_group.values():
                    if f.value is not None:
                        extracted_count += 1
            except Exception as e:
                warnings.append(f"Failed to validate group {group_name}: {str(e)}")
                all_fields[group_name] = {
                    f["name"]: FieldExtraction(f["name"], group_name, None, None, "low", None, None)
                    for f in fields
                }

        diagnostics = ExtractionDiagnostics(
            total_fields=total_fields,
            extracted_count=extracted_count,
            null_count=total_fields - extracted_count,
            warnings=warnings,
            relevant_groups=list(self.schema_registry.group_map.keys())
        )

        return ExtractionResult(fields=all_fields, diagnostics=diagnostics)

    def refine_missing_fields(self, result: ExtractionResult, retriever, session_id: str,
                               max_workers: int = 3) -> ExtractionResult:
        """Parallel async refinement for null/low-confidence fields only.
        
        Only invoked after single-pass extraction to fill in gaps.
        Uses ThreadPoolExecutor capped at max_workers to respect rate limits.
        """
        missing_fields = []
        for group_name, fields in result.fields.items():
            for field_name, extraction in fields.items():
                if extraction.value is None or extraction.confidence == "low":
                    field_info = self.schema_registry.flat_schema.get(field_name)
                    if field_info:
                        missing_fields.append((group_name, field_name, field_info))

        if not missing_fields:
            return result

        print(f"[Extractor] Refining {len(missing_fields)} missing/low-confidence fields...")

        def refine_one(group_name: str, field_name: str, field_info: dict) -> FieldExtraction:
            """Targeted retrieval + single-field LLM extraction for one field."""
            try:
                chunks = retriever.per_field_retrieval(
                    session_id, field_info, self.schema_registry, top_k=3
                )
                if not chunks:
                    return None

                context = "\n\n".join([r.text for r in chunks])
                prompt = PromptBuilder.build_extraction(
                    group_name, [field_info], context, self.schema_registry.skill_text
                )

                raw_response = self.llm_caller.complete(prompt, temperature=0.0, json_mode=True)
                clean_json = re.sub(r'```json\n?|\n?```', '', raw_response).strip()
                raw_json = json.loads(clean_json)

                # Extract the single field from response
                field_data = raw_json.get(field_name, {})
                if field_data and field_data.get("value") is not None:
                    return FieldExtraction(
                        field_name=field_name,
                        group_name=group_name,
                        value=field_data.get("value"),
                        evidence=field_data.get("evidence"),
                        confidence=field_data.get("confidence", "medium"),
                        inference_type=field_data.get("inference_type", "inferred"),
                        section=field_data.get("section"),
                        source="auto-refined"
                    )
            except Exception as e:
                print(f"[Extractor] Refinement failed for {field_name}: {e}")
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(refine_one, gn, fn, fi): (gn, fn)
                for gn, fn, fi in missing_fields
            }
            for future in concurrent.futures.as_completed(futures):
                group_name, field_name = futures[future]
                try:
                    refined = future.result()
                    if refined and refined.value is not None:
                        result.fields[group_name][field_name] = refined
                        result.diagnostics.extracted_count += 1
                        result.diagnostics.null_count -= 1
                except Exception as e:
                    print(f"[Extractor] Refinement error for {field_name}: {e}")

        return result

    def extract_all(self, relevant_groups: List[str], retriever, session_id: str) -> ExtractionResult:
        """Legacy per-group extraction — kept as fallback.
        
        Iterates groups sequentially with per-field retrieval.
        Significantly slower than extract_single_pass but more thorough per-field.
        """
        all_fields = {}
        total_fields = 0
        extracted_count = 0
        warnings = []
        
        for group_name in relevant_groups:
            fields = self.schema_registry.group_map.get(group_name, [])
            total_fields += len(fields)
            
            field_contexts = {}
            for field in fields:
                results = retriever.per_field_retrieval(session_id, field, self.schema_registry, top_k=5)
                if results:
                    field_contexts[field["name"]] = "\n\n".join([r.text for r in results])
                else:
                    field_contexts[field["name"]] = ""
                    
            prompt = PromptBuilder.build_extraction(
                group_name, fields, "", self.schema_registry.skill_text, field_contexts=field_contexts
            )
            
            try:
                raw_response = self.llm_caller.complete(prompt, temperature=0.0, json_mode=True)
                clean_json = re.sub(r'```json\n?|\n?```', '', raw_response).strip()
                raw_json = json.loads(clean_json)
                
                validated_group = self.validator.validate(group_name, raw_json)
                all_fields[group_name] = validated_group
                
                for f in validated_group.values():
                    if f.value is not None:
                        extracted_count += 1
                        
            except Exception as e:
                warnings.append(f"Failed to extract group {group_name}: {str(e)}")
                all_fields[group_name] = {
                    f["name"]: FieldExtraction(f["name"], group_name, None, None, "low", None, None)
                    for f in fields
                }
                
        diagnostics = ExtractionDiagnostics(
            total_fields=total_fields,
            extracted_count=extracted_count,
            null_count=total_fields - extracted_count,
            warnings=warnings,
            relevant_groups=relevant_groups
        )
        
        return ExtractionResult(fields=all_fields, diagnostics=diagnostics)

    def extract_from_response(self, response_text: str) -> Dict[str, Any]:
        """Post-response extraction of fields."""
        schema_fields = list(self.schema_registry.flat_schema.keys())
        prompt = PromptBuilder.build_post_response(response_text, schema_fields)
        try:
            raw = self.llm_caller.complete(prompt, temperature=0.0, json_mode=True)
            clean_json = re.sub(r'```json\n?|\n?```', '', raw).strip()
            return json.loads(clean_json)
        except Exception:
            return {}

import re
from typing import Dict, Any, List
from difflib import SequenceMatcher
from core.contracts import FieldExtraction

class Validator:
    def __init__(self, schema_registry):
        self.schema_registry = schema_registry

    def fuzzy_match_vocab(self, value: str, expected_vocab: List[str], threshold: float = 0.8) -> str | None:
        if not value:
            return None
        value_lower = str(value).lower()
        for expected in expected_vocab:
            if expected.lower() == value_lower:
                return expected
            ratio = SequenceMatcher(None, value_lower, expected.lower()).ratio()
            if ratio >= threshold:
                return expected
        return None

    def fuzzy_evidence_match(self, evidence: str, context: str) -> bool:
        if not evidence or not context:
            return False
        if evidence.lower() in context.lower():
            return True
        return SequenceMatcher(None, evidence.lower(), context.lower()[:len(evidence)*2]).ratio() > 0.6

    def validate(self, group_name: str, raw_json: Dict[str, Any]) -> Dict[str, FieldExtraction]:
        validated = {}
        expected_fields = self.schema_registry.group_map.get(group_name, [])
        
        for field in expected_fields:
            field_name = field["name"]
            raw_field = raw_json.get(field_name, {})
            
            if isinstance(raw_field, str):
                raw_field = {"value": raw_field, "evidence": None, "confidence": "medium"}
                
            val = raw_field.get("value")
            
            if val and "text_values" in field:
                vocab = field["text_values"]
                matched = self.fuzzy_match_vocab(val, vocab)
                if matched:
                    val = matched
                else:
                    raw_field["confidence"] = "low"
            
            validated[field_name] = FieldExtraction(
                field_name=field_name,
                group_name=group_name,
                value=val if val and str(val).lower() not in ['not mentioned', 'null', 'none'] else None,
                evidence=raw_field.get("evidence"),
                confidence=raw_field.get("confidence", "low"),
                inference_type=raw_field.get("inference_type", "reported"),
                section=None
            )
        return validated

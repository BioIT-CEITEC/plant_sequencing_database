import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from config import config

class SchemaRegistry:
    def __init__(self):
        self.schema_data = {}
        self.skill_text = ""
        self.flat_schema = {}
        self.group_map = {}
        
    def load(self):
        """Load schema and skill from configured paths."""
        try:
            with open(config.SCHEMA_PATH, 'r', encoding='utf-8') as f:
                self.schema_data = json.load(f)
            with open(config.SKILL_PATH, 'r', encoding='utf-8') as f:
                self.skill_text = f.read()
            self.build_maps()
        except Exception as e:
            print(f"Error loading schema: {e}")

    def build_maps(self):
        # Handle new format (field_groups) or fallback to old (checklist.groups)
        groups = self.schema_data.get("field_groups", [])
        if not groups:
            groups = self.schema_data.get("checklist", {}).get("groups", [])
            
        for group in groups:
            group_name = group.get("group_name", group.get("name", "Unknown Group"))
            self.group_map[group_name] = []
            for field in group.get("fields", []):
                self.flat_schema[field["name"]] = field
                self.group_map[group_name].append(field)

    def build_index(self, indexer):
        """Builds vector index for schema fields if not exists.
        Delegated to indexing layer, but called here to ensure schema is indexed.
        """
        from core.contracts import Chunk
        chunks = []
        for i, (group_name, fields) in enumerate(self.group_map.items()):
            field_desc = ", ".join([f"{f['name']}: {f.get('description', f.get('field_type', ''))}" for f in fields])
            text = f"Group: {group_name}\nFields: {field_desc}"
            chunks.append(Chunk(
                text=text,
                chunk_index=i,
                source_file="schema.json",
                section="Schema",
                token_count=len(text.split()),
                metadata={"group_name": group_name}
            ))
        indexer.index("schema_index", chunks)

    def get_schema_for_llm(self) -> Dict:
        return self.schema_data

    def get_schema_for_ui(self) -> Dict:
        return self.schema_data

    def get_field_queries(self, field: dict) -> list[str]:
        field_name_human = field["name"].replace("_", " ")
        queries = [field_name_human]
        
        if "text_values" in field:
            # Add up to 10 vocabulary terms to the query for semantic richness
            terms = field["text_values"][:10]
            if terms:
                queries.append(f"{field_name_human} {' '.join(terms)}")
                
        return queries

    def parse_xml(self, xml_path: str) -> Dict:
        """Utility migrated from extract_fields.py"""
        pass

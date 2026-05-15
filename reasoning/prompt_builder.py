from typing import List, Dict, Any
from core.contracts import Chunk

EXTRACTION_RULES = """
Rules:
1. Extract ONLY values explicitly stated or clearly implied in the text.
2. For TEXT_CHOICE_FIELD fields, ONLY use values from the provided options list.
3. Set value to null if the information is not found — never guess.
4. Evidence MUST be a verbatim quote from the source text.
5. Confidence: "high" = explicitly stated, "medium" = clearly implied, "low" = weakly inferred.
"""

class PromptBuilder:
    @staticmethod
    def build_qa(chunks: List[Chunk], message: str, chat_history: List[Dict] = None) -> List[Dict[str, str]]:
        context_text = "\n\n".join(
            [f"--- Section: {c.section} ---\n{c.text}" for c in chunks]
        )
        system_prompt = (
            "You are a scientific research assistant. Answer the user's question based ONLY "
            "on the provided context from the uploaded document.\n\n"
            f"Context:\n{context_text}"
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            messages.extend(chat_history[-4:]) # Include last 4 messages
        messages.append({"role": "user", "content": message})
        
        return messages

    @staticmethod
    def build_hybrid(chunks: List[Chunk], message: str, extracted_metadata: Dict[str, Any] = None) -> List[Dict[str, str]]:
        context_text = "\n\n".join(
            [f"--- Section: {c.section} ---\n{c.text}" for c in chunks]
        )
        metadata_text = str(extracted_metadata) if extracted_metadata else "None"
        
        system_prompt = (
            "You are a specialized hybrid research assistant. You have access to both "
            "the document text and structured extracted metadata. Use both to answer "
            "the user's query.\n\n"
            f"Extracted Metadata:\n{metadata_text}\n\n"
            f"Context:\n{context_text}"
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": message})
        
        return messages

    @staticmethod
    def build_extraction(group_name: str, fields: List[Dict[str, Any]], context: str, skill: str, field_contexts: dict[str, str] = None) -> List[Dict[str, str]]:
        def get_desc(f):
            desc = f.get('field_type', '')
            if f.get('text_values'):
                values = f['text_values']
                if len(values) > 20:
                    desc += f" (Controlled vocabulary with {len(values)} values — select from controlled list)"
                else:
                    desc += f" (Options: {', '.join(values)})"
            return desc

        fields_instruction = "\n".join([
            f"- {f['name']} ({f.get('field_type', 'TEXT_FIELD')}): {get_desc(f)}" for f in fields
        ])
        
        system_prompt = (
            "You are a scientific metadata extraction engine. Your task is to extract "
            "specific fields for the group provided. Return valid JSON only.\n\n"
            f"{EXTRACTION_RULES}\n\n"
            "Output Format must be JSON:\n"
            "{\n"
            '  "field_name": {"value": "extracted_value", "evidence": "exact quote from text", "confidence": "high/medium/low"}\n'
            "}\n"
        )
        
        if field_contexts:
            context_blocks = []
            for fname, fctx in field_contexts.items():
                if fctx:
                    context_blocks.append(f"--- Context for field '{fname}' ---\n{fctx}")
            context_section = "\n\n".join(context_blocks)
            if not context_section:
                context_section = "No relevant context found."
        else:
            context_section = f"Context:\n{context}"
        
        user_prompt = (
            f"Extract fields for group: {group_name}\n\n"
            f"Fields to extract:\n{fields_instruction}\n\n"
            f"{context_section}"
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    @staticmethod
    def build_full_extraction(group_map: Dict[str, List[Dict]], context: str, skill: str) -> List[Dict[str, str]]:
        """Build a single prompt for ALL groups and fields at once.
        Used by extract_single_pass for the 1-retrieval + 1-LLM approach.
        """
        def get_desc(f):
            desc = f.get('field_type', '')
            if f.get('text_values'):
                values = f['text_values']
                if len(values) > 20:
                    desc += f" (Controlled vocabulary — {len(values)} values)"
                else:
                    desc += f" (Options: {', '.join(values[:15])})"
            return desc

        groups_instruction = ""
        for group_name, fields in group_map.items():
            groups_instruction += f"\n## Group: {group_name}\n"
            for f in fields:
                groups_instruction += f"  - {f['name']} ({f.get('field_type', 'TEXT_FIELD')}): {get_desc(f)}\n"

        system_prompt = (
            "You are a scientific metadata extraction engine. Your task is to extract ALL fields "
            "from ALL groups listed below in a single pass. Return valid JSON only.\n\n"
            f"{EXTRACTION_RULES}\n\n"
            "Output Format:\n"
            "{\n"
            '  "Group_Name": {\n'
            '    "field_name": {"value": "extracted_value", "evidence": "exact quote", "confidence": "high/medium/low"},\n'
            '    ...\n'
            "  },\n"
            "  ...\n"
            "}\n"
        )

        user_prompt = (
            f"Extract ALL metadata fields from the following document context.\n\n"
            f"Schema:\n{groups_instruction}\n\n"
            f"Document Context:\n{context}"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]




    @staticmethod
    def build_post_response(response_text: str, schema_fields: List[str]) -> List[Dict[str, str]]:
        system_prompt = (
            "You are a background extraction service. Review the AI's response to the user "
            "and determine if any metadata fields were implicitly confirmed or discovered.\n"
            "Return valid JSON containing ONLY the newly discovered fields and their values."
        )
        
        user_prompt = (
            f"Allowed schema fields: {', '.join(schema_fields)}\n\n"
            f"AI Response:\n{response_text}"
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    @staticmethod
    def build_field_completion(field_info: Dict[str, Any], group_name: str, context_chunks: List[Any], user_context: str = None) -> List[Dict[str, str]]:
        context_text = "\n\n".join(
            [f"--- Section: {getattr(c, 'section', 'Document')} ---\n{getattr(c, 'text', '')}" for c in context_chunks]
        )
        
        field_name = field_info['name']
        field_type = field_info.get('field_type', 'TEXT_FIELD')
        
        options_text = ""
        if field_info.get('text_values'):
            options_text = f"\nControlled Vocabulary (prefer these if applicable):\n" + "\n".join([f"- {v}" for v in field_info['text_values']])
            
        system_prompt = (
            "You are an interactive metadata completion assistant. "
            f"Your task is to suggest a value for the field '{field_name}' in the group '{group_name}'.\n\n"
            "CRITICAL RULES:\n"
            "1. ONLY suggest a value if it is supported by the provided document passages.\n"
            "2. If there is NO evidence in the text, you MUST respond with value: null and explain why.\n"
            "3. DO NOT hallucinate or guess based on general knowledge.\n"
            f"{options_text}\n\n"
            "Return valid JSON ONLY in this format:\n"
            "{\n"
            '  "field_name": "the field name",\n'
            '  "suggested_value": "the extracted value or null",\n'
            '  "confidence": "high|medium|low",\n'
            '  "evidence": "the EXACT sentence from the text proving the value",\n'
            '  "inference_type": "reported|inferred",\n'
            '  "alternatives": ["alternative1", "alternative2"]\n'
            "}"
        )
        
        user_hint = f"\n\nUser Hint: {user_context}" if user_context else ""
        
        user_prompt = (
            f"Please suggest a value for '{field_name}'.\n\n"
            f"Document Context:\n{context_text}"
            f"{user_hint}"
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    @staticmethod
    def build_field_hints(field_info: Dict[str, Any], group_name: str, context_chunks: List[Any]) -> List[Dict[str, str]]:
        """Build prompt for contextual hints — guides user toward the answer
        without directly stating it. Returns 3-4 hint sentences referencing
        document passages to help user discover, remember, or infer the value.
        """
        context_text = "\n\n".join(
            [f"--- Section: {getattr(c, 'section', 'Document')} ---\n{getattr(c, 'text', '')}" for c in context_chunks]
        )

        field_name = field_info['name']
        options_text = ""
        if field_info.get('text_values'):
            options_text = f"\nPossible values for this field include:\n" + "\n".join([f"- {v}" for v in field_info['text_values'][:15]])

        system_prompt = (
            "You are a metadata research assistant helping a scientist fill in a structured form. "
            f"The user needs help deciding a value for the field '{field_name}' in group '{group_name}'.\n\n"
            "YOUR TASK:\n"
            "1. Read the provided document passages carefully.\n"
            "2. Generate 3-4 contextual HINT sentences that help the user discover, "
            "   remember, infer, or validate the correct value.\n"
            "3. DO NOT directly state the answer — guide the user toward it.\n"
            "4. Reference specific observations or passages from the document.\n"
            "5. If the document contains NO relevant information, say so clearly.\n"
            f"{options_text}\n\n"
            "Return valid JSON ONLY:\n"
            '{"hints": ["hint sentence 1", "hint sentence 2", "hint sentence 3"]}'
        )

        user_prompt = (
            f"Help me figure out the value for '{field_name}'.\n\n"
            f"Document Context:\n{context_text}"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]


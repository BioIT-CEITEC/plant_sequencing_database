import re
import tiktoken
from core.contracts import Chunk
from typing import List

class Chunker:
    SECTION_PATTERNS = [
        r'^(?:\d+\.?\s+)?(Abstract)\b',
        r'^(?:\d+\.?\s+)?(Introduction)\b',
        r'^(?:\d+\.?\s+)?(Background)\b',
        r'^(?:\d+\.?\s+)?(Literature\s+Review)\b',
        r'^(?:\d+\.?\s+)?(Materials?\s+and\s+Methods?)\b',
        r'^(?:\d+\.?\s+)?(Methods?)\b',
        r'^(?:\d+\.?\s+)?(Experimental\s+(?:Design|Setup|Procedure))\b',
        r'^(?:\d+\.?\s+)?(Results?)\b',
        r'^(?:\d+\.?\s+)?(Results?\s+and\s+Discussion)\b',
        r'^(?:\d+\.?\s+)?(Discussion)\b',
        r'^(?:\d+\.?\s+)?(Conclusion)\b',
        r'^(?:\d+\.?\s+)?(Conclusions?)\b',
        r'^(?:\d+\.?\s+)?(Acknowledg(?:e)?ments?)\b',
        r'^(?:\d+\.?\s+)?(References?)\b',
        r'^(?:\d+\.?\s+)?(Bibliography)\b',
        r'^(?:\d+\.?\s+)?(Supplementary\s+(?:Materials?|Data|Information))\b',
        r'^(?:\d+\.?\d*\.?\s+)(.+)$',  # Fallback: numbered subsections like "2.1 Sample Collection"
    ]

    def _detect_section_heading(self, paragraph_text: str) -> str | None:
        first_line = paragraph_text.strip().split('\n')[0].strip()
        if len(first_line) > 80 or first_line.endswith('.'):
            return None
        for pattern in self.SECTION_PATTERNS[:-1]:
            match = re.match(pattern, first_line, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        fallback = re.match(r'^(\d+\.[\d.]*)\s+(.+)$', first_line)
        if fallback and len(first_line) < 60:
            return fallback.group(2).strip()
        return None

    _encoder = None

    @classmethod
    def _get_encoder(cls):
        if cls._encoder is None:
            cls._encoder = tiktoken.get_encoding("cl100k_base")
        return cls._encoder

    def __init__(self, min_chunk_tokens=100, max_chunk_tokens=1200, overlap_tokens=50):
        self.min_chunk_tokens = min_chunk_tokens
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, text: str, filename: str) -> List[Chunk]:
        enc = self._get_encoder()
        paragraphs = re.split(r'\n\n+', text)
        
        chunks = []
        current_chunk_text = ""
        current_chunk_tokens = []
        current_section = "Document"
        
        def flush_chunk():
            nonlocal current_chunk_text, current_chunk_tokens
            
            if not current_chunk_text.strip():
                return
                
            chunks.append(Chunk(
                text=current_chunk_text.strip(),
                source_file=filename,
                section=current_section,
                token_count=len(current_chunk_tokens),
                chunk_index=len(chunks),
                overlap_tokens=self.overlap_tokens if len(chunks) > 0 else 0
            ))
            
            # Retain overlap tokens
            if len(current_chunk_tokens) > self.overlap_tokens:
                overlap_toks = current_chunk_tokens[-self.overlap_tokens:]
                current_chunk_text = enc.decode(overlap_toks)
                current_chunk_tokens = overlap_toks
            else:
                current_chunk_text = ""
                current_chunk_tokens = []

        for para in paragraphs:
            if not para.strip():
                continue
                
            heading = self._detect_section_heading(para)
            if heading:
                # Flush the previous chunk on new section boundary
                flush_chunk()
                current_section = heading
                
            para_tokens = enc.encode(para)
            
            # If a single paragraph is too large, split by sentences
            if len(para_tokens) > self.max_chunk_tokens:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sentence in sentences:
                    sentence_tokens = enc.encode(sentence)
                    if len(current_chunk_tokens) + len(sentence_tokens) > self.max_chunk_tokens and current_chunk_text:
                        flush_chunk()
                    current_chunk_text += (" " + sentence if current_chunk_text else sentence)
                    current_chunk_tokens.extend(sentence_tokens)
            else:
                # Normal paragraph grouping
                if len(current_chunk_tokens) + len(para_tokens) > self.max_chunk_tokens and current_chunk_text:
                    flush_chunk()
                    
                current_chunk_text += ("\n\n" + para if current_chunk_text else para)
                current_chunk_tokens.extend(para_tokens)
                    
        flush_chunk()
        
        return self._merge_small_chunks(chunks)

    def _merge_small_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        if not chunks:
            return []
            
        merged = []
        current_merge = chunks[0]
        
        for next_chunk in chunks[1:]:
            if current_merge.token_count < self.min_chunk_tokens:
                # Merge current_merge into next_chunk
                combined_text = current_merge.text + "\n\n" + next_chunk.text
                enc = self._get_encoder()
                combined_tokens = enc.encode(combined_text)
                current_merge = Chunk(
                    text=combined_text,
                    source_file=current_merge.source_file,
                    section=current_merge.section,  # keep section of first
                    token_count=len(combined_tokens),
                    chunk_index=current_merge.chunk_index,
                    overlap_tokens=current_merge.overlap_tokens
                )
            else:
                merged.append(current_merge)
                current_merge = next_chunk
                current_merge.chunk_index = len(merged)
                
        # Append the last one
        current_merge.chunk_index = len(merged)
        merged.append(current_merge)
        
        return merged

import os
import fitz  # PyMuPDF
from docx import Document
import chardet

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

def extract_text(file_path: str, filename: str) -> tuple[str | None, str | None]:
    """
    Extract plain text from a scientific manuscript (PDF, TXT, DOCX).
    Returns (text, error_message).
    """
    try:
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE_BYTES:
            return None, f"File exceeds {MAX_FILE_SIZE_MB}MB limit."

        ext = filename.lower().split('.')[-1]
        
        if ext == 'pdf':
            return _extract_from_pdf(file_path)
        elif ext == 'docx':
            return _extract_from_docx(file_path)
        elif ext == 'txt':
            return _extract_from_txt(file_path)
        else:
            return None, f"Unsupported file type: .{ext}"

    except Exception as e:
        return None, f"Error processing file: {str(e)}"


def _extract_from_pdf(file_path: str) -> tuple[str | None, str | None]:
    try:
        text = []
        with fitz.open(file_path) as doc:
            for page in doc:
                text.append(page.get_text())
        if not text:
            return None, "No text could be extracted from the PDF (it might be scanned images)."
        return "\n".join(text), None
    except Exception as e:
        return None, f"PDF extraction failed: {str(e)}"


def _extract_from_docx(file_path: str) -> tuple[str | None, str | None]:
    try:
        doc = Document(file_path)
        text = [para.text for para in doc.paragraphs]
        if not text:
            return None, "No text found in the DOCX file."
        return "\n".join(text), None
    except Exception as e:
        return None, f"DOCX extraction failed: {str(e)}"


def _extract_from_txt(file_path: str) -> tuple[str | None, str | None]:
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            
        result = chardet.detect(raw_data)
        encoding = result['encoding'] or 'utf-8'
        
        return raw_data.decode(encoding), None
    except Exception as e:
        return None, f"TXT extraction failed: {str(e)}"

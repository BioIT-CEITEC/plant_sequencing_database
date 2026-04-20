"""
doc_parser.py — Parse crop_development_factors.docx into structured form data.

Extracts the hierarchical document structure (Heading 2 → Heading 3 → List items)
and returns a nested dict suitable for dynamic form rendering.
"""

import os
import sys
import json

# Ensure venv site-packages are on the path
VENV_SITE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "lib", "python3.12", "site-packages"
)
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

from docx import Document


DOC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "documents", "crop_development_factors.docx")


def parse_crop_document(doc_path: str = DOC_PATH) -> dict:
    """
    Parse the crop development factors .docx file into a nested dictionary.

    Returns a structure like:
    {
        "1. LAB ENVIRONMENT FACTORS": {
            "Controllable Parameters:": [
                "Light spectrum (PAR, R:FR ratio, UV-A/B exposure)",
                ...
            ],
            "Equipment Constraints:": [...]
        },
        "2. FIELD ENVIRONMENT FACTORS": { ... },
        "3. GENERAL CULTIVATION CONSIDERATIONS": { ... }
    }

    Each top-level key is a Heading 2 section.
    Each sub-key is a Heading 3 sub-section.
    Each value is a list of factor strings (from List Paragraph items).
    """
    try:
        doc = Document(doc_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Document not found: {doc_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to read document: {e}")

    result = {}
    current_section = None     # Heading 2
    current_subsection = None  # Heading 3

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        style = para.style.name

        if style == "Heading 2":
            current_section = text
            result[current_section] = {}
            current_subsection = None

        elif style == "Heading 3" and current_section is not None:
            current_subsection = text
            result[current_section][current_subsection] = []

        elif style == "List Paragraph" and current_subsection is not None:
            result[current_section][current_subsection].append(text)

    return result


def get_environment_sections(data: dict) -> dict:
    """
    Split parsed data into Lab and Field environment groups,
    plus the General Cultivation section.

    Returns:
    {
        "Lab Environment": { subsection: [factors] },
        "Field Environment": { subsection: [factors] },
        "General Cultivation": { subsection: [factors] }
    }
    """
    env_map = {}
    for section_title, subsections in data.items():
        # Derive a clean label from the Heading 2 text
        clean = section_title.lower()
        if "lab" in clean:
            label = "Lab Environment"
        elif "field" in clean:
            label = "Field Environment"
        elif "general" in clean or "cultivation" in clean:
            label = "General Cultivation"
        else:
            label = section_title
        env_map[label] = subsections
    return env_map


def get_all_factors_flat(data: dict) -> list[str]:
    """
    Return a flat list of every factor string in the document.
    Useful for keyword matching against user queries.
    """
    factors = []
    for subsections in data.values():
        for items in subsections.values():
            factors.extend(items)
    return factors


if __name__ == "__main__":
    # Standalone test: parse and print the document structure
    data = parse_crop_document()
    env_sections = get_environment_sections(data)
    print(json.dumps(env_sections, indent=2, ensure_ascii=False))
    print(f"\n--- Total factors: {len(get_all_factors_flat(data))} ---")

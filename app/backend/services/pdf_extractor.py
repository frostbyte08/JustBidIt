
import pdfplumber
import re
from typing import Dict, List, Tuple


SECTION_KEYWORDS = [
    "eligibility criteria",
    "eligibility requirement",
    "technical qualification",
    "scope of work",
    "terms and conditions",
    "general conditions",
    "special conditions",
    "documents required",
    "document checklist",
    "bid submission",
    "evaluation criteria",
    "financial requirement",
    "pre-qualification",
    "technical specifications",
    "instructions to bidders",
]


def extract_text_from_pdf(file_path: str) -> Dict:
    """
    Main extraction function.

    Returns a dict:
    {
        "success": True/False,
        "full_text": "...",
        "page_count": 5,
        "sections": { "eligibility criteria": "...", ... },
        "is_image_based": False,
        "error": None or "error message"
    }
    """
    result = {
        "success": False,
        "full_text": "",
        "page_count": 0,
        "sections": {},
        "is_image_based": False,
        "error": None
    }

    try:
        with pdfplumber.open(file_path) as pdf:
            result["page_count"] = len(pdf.pages)
            pages_text = []

            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()

                if text:
                    text = _clean_page_text(text)
                    pages_text.append(text)
                else:
                    pages_text.append(f"[Page {page_num + 1}: No extractable text — may be scanned]")

            full_text = "\n\n".join(pages_text)
            result["full_text"] = full_text

            extractable_pages = sum(1 for t in pages_text if not t.startswith("[Page"))
            if extractable_pages == 0:
                result["is_image_based"] = True
                result["error"] = (
                    "This PDF appears to be entirely scanned (image-based). "
                    "pdfplumber cannot extract text from image PDFs. "
                    "Please use a PDF with a proper text layer."
                )
                return result

            result["sections"] = _extract_sections(full_text)
            result["success"] = True

    except Exception as e:
        result["error"] = f"PDF extraction failed: {str(e)}"

    return result


def _clean_page_text(text: str) -> str:
    """
    Remove common PDF noise:
      - Multiple consecutive blank lines
      - Page numbers like 'Page 1 of 20'
      - Repeated header/footer patterns
    """
    text = re.sub(r'\n{3,}', '\n\n', text)

    text = re.sub(r'\nPage\s+\d+\s+of\s+\d+\n', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)

    text = re.sub(r'[ \t]{3,}', '  ', text)

    return text.strip()


def _extract_sections(full_text: str) -> Dict[str, str]:
    """
    Detect and extract named sections from the tender text.
    Returns a dict mapping section names to their content.

    This helps us send targeted section text to Gemini rather than
    dumping the full document (token efficient + more accurate).
    """
    sections = {}
    text_lower = full_text.lower()

    for keyword in SECTION_KEYWORDS:
        pos = text_lower.find(keyword)
        if pos == -1:
            continue

        end_pos = len(full_text)
        for other_keyword in SECTION_KEYWORDS:
            if other_keyword == keyword:
                continue
            next_pos = text_lower.find(other_keyword, pos + len(keyword))
            if next_pos != -1 and next_pos < end_pos:
                end_pos = next_pos

        section_content = full_text[pos:min(end_pos, pos + 3000)]
        sections[keyword] = section_content.strip()

    return sections


def get_eligibility_section(sections: Dict[str, str], full_text: str) -> str:
    """
    Return the best available eligibility text.
    Priority: dedicated section > first 4000 chars of full text.

    This is what gets sent to Gemini for structured extraction.
    """
    for key in ["eligibility criteria", "eligibility requirement", "pre-qualification",
                "technical qualification", "financial requirement"]:
        if key in sections and len(sections[key]) > 100:
            return sections[key]

    return full_text[:4000]


def get_documents_section(sections: Dict[str, str], full_text: str) -> str:
    """Return the best available documents-required text."""
    for key in ["documents required", "document checklist", "bid submission"]:
        if key in sections and len(sections[key]) > 100:
            return sections[key]
    return full_text[:3000]


def truncate_for_gemini(text: str, max_chars: int = 8000) -> str:
    """
    Safely truncate text to fit within Gemini's context window.
    Tries to cut at a paragraph boundary.
    """
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    last_newline = truncated.rfind('\n')
    if last_newline > max_chars * 0.8:
        truncated = truncated[:last_newline]

    return truncated + "\n\n[... document truncated for processing ...]"

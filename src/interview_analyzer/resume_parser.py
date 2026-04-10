import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


def extract_resume_text(resume_path: Path) -> str:
    """Extract plain text from a PDF resume."""
    logger.info("Extracting text from resume: %s", resume_path)
    pages_text: list[str] = []

    with pdfplumber.open(resume_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)

    full_text = "\n\n".join(pages_text)
    logger.info("Extracted %d characters from resume", len(full_text))
    return full_text

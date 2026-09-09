"""Text extraction for uploaded evidence documents.

Supports PDF, DOCX, and TXT today. Each format has its own small extractor
function; `parse_document` dispatches on a normalized extension. Adding a
new format (or OCR for images) later means adding one more extractor and
one more dispatch entry - the call site in `app.services.evidence` doesn't
need to change.

This module only extracts readable text and light structural metadata
(page count where available). It never attempts summarization, semantic
analysis, or anything AI-related - that belongs to a later step.
"""

import io
from dataclasses import dataclass

from docx import Document
from pypdf import PdfReader

from app.core.errors import UnsupportedMediaTypeError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Extensions this module knows how to parse today. Kept separate from the
# *upload* allow-list in Settings so the two concerns (what a user is
# allowed to upload vs. what this module can currently read) don't have to
# stay manually in sync as either list grows - e.g. image formats could be
# added to the upload allow-list ahead of OCR support landing here.
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


@dataclass(frozen=True)
class ParsedDocument:
    """Extracted text plus the structural metadata available for the format."""

    text: str
    page_count: int | None = None


def parse_document(content: bytes, extension: str) -> ParsedDocument:
    """Extract text and available metadata from a file's raw bytes.

    `extension` must be lowercase and dot-prefixed (e.g. ".pdf"), matching
    the normalization already applied during upload validation.
    """
    if extension == ".pdf":
        return _parse_pdf(content)
    if extension == ".docx":
        return _parse_docx(content)
    if extension == ".txt":
        return _parse_txt(content)

    # Reachable only if a caller bypasses upload validation - upload
    # validation should always reject this before parsing is attempted.
    raise UnsupportedMediaTypeError(detail=f"No parser available for '{extension}' files.")


def _parse_pdf(content: bytes) -> ParsedDocument:
    reader = PdfReader(io.BytesIO(content))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return ParsedDocument(text="\n\n".join(pages_text).strip(), page_count=len(reader.pages))


def _parse_docx(content: bytes) -> ParsedDocument:
    document = Document(io.BytesIO(content))
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
    return ParsedDocument(text="\n".join(paragraphs).strip(), page_count=None)


def _parse_txt(content: bytes) -> ParsedDocument:
    # "utf-8-sig" transparently strips a leading UTF-8 BOM if present (common
    # in text files saved by Windows tools) and behaves exactly like "utf-8"
    # otherwise.
    text = content.decode("utf-8-sig", errors="replace")
    return ParsedDocument(text=text.strip(), page_count=None)

"""Business logic for evidence upload, retrieval, and deletion.

Route handlers stay thin and delegate here. This step only extracts text
and stores metadata - no semantic analysis, embeddings, or AI happens on
the extracted content.
"""

from pathlib import PurePosixPath
from uuid import UUID

from app.core.config import get_settings
from app.core.errors import NotFoundError, PayloadTooLargeError, UnsupportedMediaTypeError
from app.core.logging import get_logger
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.decision_resources import Evidence, SourceType
from app.services.document_parser import SUPPORTED_EXTENSIONS, parse_document
from app.services.storage import StorageBackend

logger = get_logger(__name__)

# Bound on how much extracted text is kept in the evidence record. This is a
# metadata store, not a document store - the full text stays retrievable
# from the original file via the storage backend if ever needed.
MAX_CONTENT_REFERENCE_CHARS = 20_000

# Magic-byte signatures used to sanity-check that a file's content actually
# matches its claimed extension, rather than trusting the client-supplied
# filename/MIME type alone.
_PDF_SIGNATURE = b"%PDF-"
_ZIP_SIGNATURE = b"PK\x03\x04"  # DOCX is a zip archive under the hood.


class EvidenceService:
    """Coordinates evidence upload validation, parsing, storage, and retrieval."""

    def __init__(self, repository: EvidenceRepository, storage: StorageBackend) -> None:
        self._repository = repository
        self._storage = storage

    def upload_evidence(
        self,
        decision_id: UUID,
        filename: str,
        content: bytes,
        title: str | None = None,
    ) -> Evidence:
        settings = get_settings()
        extension = self._validate_extension(filename)
        self._validate_size(content, settings.max_upload_size_bytes)
        self._validate_content_matches_extension(content, extension)

        parsed = parse_document(content, extension)
        content_reference = parsed.text[:MAX_CONTENT_REFERENCE_CHARS]
        content_truncated = len(parsed.text) > MAX_CONTENT_REFERENCE_CHARS

        storage_key = self._storage.save(content, extension)

        evidence = self._repository.create(
            decision_id=decision_id,
            title=title or _safe_display_name(filename),
            source_type=SourceType.DOCUMENT,
            storage_key=storage_key,
            filename=_safe_display_name(filename),
            file_type=extension.lstrip("."),
            size_bytes=len(content),
            page_count=parsed.page_count,
            content_reference=content_reference,
            content_truncated=content_truncated,
        )
        logger.info(
            "Evidence uploaded id=%s decision_id=%s file_type=%s size_bytes=%d",
            evidence.id,
            decision_id,
            extension,
            len(content),
        )
        return evidence

    def list_evidence(self, decision_id: UUID) -> list[Evidence]:
        return self._repository.list_for_decision(decision_id)

    def get_evidence(self, evidence_id: UUID) -> Evidence:
        evidence = self._repository.get_by_id(evidence_id)
        if evidence is None:
            raise NotFoundError(detail=f"Evidence {evidence_id} not found.")
        return evidence

    def delete_evidence(self, evidence_id: UUID) -> None:
        evidence = self.get_evidence(evidence_id)
        if evidence.storage_key:
            self._storage.delete(evidence.storage_key)
        self._repository.delete(evidence.decision_id, evidence_id)
        logger.info("Evidence deleted id=%s decision_id=%s", evidence_id, evidence.decision_id)

    @staticmethod
    def _validate_extension(filename: str) -> str:
        # Used purely to isolate the extension, never to build a path.
        extension = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
        settings = get_settings()

        if extension not in settings.allowed_extensions:
            raise UnsupportedMediaTypeError(
                detail=f"File type '{extension or 'unknown'}' is not supported."
            )
        if extension not in SUPPORTED_EXTENSIONS:
            # Allowed for upload by config but no parser exists yet (e.g. a
            # future image type pending OCR support).
            raise UnsupportedMediaTypeError(
                detail=f"File type '{extension}' cannot be processed yet."
            )
        return extension

    @staticmethod
    def _validate_size(content: bytes, max_bytes: int) -> None:
        if len(content) == 0:
            raise UnsupportedMediaTypeError(detail="Uploaded file is empty.")
        if len(content) > max_bytes:
            raise PayloadTooLargeError(
                detail=f"File exceeds the maximum allowed size of {max_bytes} bytes."
            )

    @staticmethod
    def _validate_content_matches_extension(content: bytes, extension: str) -> None:
        """Sanity-check file content against its claimed extension.

        Not a full antivirus/format validator - just enough to catch the
        common case of a file renamed to look like a supported type. TXT
        has no reliable signature, so it isn't checked here; the parser
        will surface a decode issue if the bytes aren't text-like.
        """
        if extension == ".pdf" and not content.startswith(_PDF_SIGNATURE):
            raise UnsupportedMediaTypeError(detail="File does not look like a valid PDF.")
        if extension == ".docx" and not content.startswith(_ZIP_SIGNATURE):
            raise UnsupportedMediaTypeError(detail="File does not look like a valid DOCX.")


def _safe_display_name(filename: str) -> str:
    """Return just the filename component, stripped of any directory parts.

    Splits on both `/` and `\\` since a client filename could carry either
    separator (e.g. a Windows browser sending `C:\\docs\\report.pdf`). Used
    only for display (the `filename`/`title` fields) - never to construct a
    filesystem path. The actual stored file always gets a server-generated
    name (see `app.services.storage`).
    """
    normalized = filename.replace("\\", "/")
    name = PurePosixPath(normalized).name
    return name or "untitled"

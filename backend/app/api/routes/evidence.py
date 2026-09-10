"""Evidence routes.

Two route groups, both thin:

- Nested under a decision (`/decisions/{decision_id}/evidence`) for
  uploading and listing - these first confirm the decision exists and is
  owned by the caller via `DecisionServiceDep`, reusing the same
  ownership-check logic the decision routes already use.
- Top-level (`/evidence/{evidence_id}`) for fetching or deleting a single
  piece of evidence once its id is known, independent of its parent
  decision.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, UploadFile, status

from app.core.config import get_settings
from app.core.errors import NotFoundError, PayloadTooLargeError
from app.dependencies.decisions import CurrentUserIdDep, DecisionServiceDep
from app.dependencies.evidence import EvidenceServiceDep
from app.schemas.decision_resources import Evidence
from app.services.decisions import DecisionService

decision_evidence_router = APIRouter(prefix="/decisions", tags=["evidence"])
evidence_router = APIRouter(prefix="/evidence", tags=["evidence"])


@decision_evidence_router.post(
    "/{decision_id}/evidence", response_model=Evidence, status_code=status.HTTP_201_CREATED
)
async def upload_evidence(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    evidence_service: EvidenceServiceDep,
    user_id: CurrentUserIdDep,
    file: Annotated[UploadFile, File(...)],
) -> Evidence:
    """Upload a document as evidence for a decision.

    Supports PDF, DOCX, and TXT. The decision must exist and belong to the
    caller. No AI or semantic analysis runs on the extracted text yet -
    this only stores it.
    """
    decision_service.get_decision(user_id, decision_id)  # existence + ownership, raises 404
    content = await _read_bounded(file)
    return evidence_service.upload_evidence(
        decision_id=decision_id,
        filename=file.filename or "untitled",
        content=content,
    )


@decision_evidence_router.get("/{decision_id}/evidence", response_model=list[Evidence])
async def list_evidence(
    decision_id: UUID,
    decision_service: DecisionServiceDep,
    evidence_service: EvidenceServiceDep,
    user_id: CurrentUserIdDep,
) -> list[Evidence]:
    """List evidence metadata for a decision.

    Returns metadata and a bounded text extract for each item, not full raw
    document content.
    """
    decision_service.get_decision(user_id, decision_id)
    return evidence_service.list_evidence(decision_id)


@evidence_router.get("/{evidence_id}", response_model=Evidence)
async def get_evidence(
    evidence_id: UUID,
    evidence_service: EvidenceServiceDep,
    decision_service: DecisionServiceDep,
    user_id: CurrentUserIdDep,
) -> Evidence:
    """Fetch a single piece of evidence by id.

    Ownership is enforced via the evidence's parent decision - a missing
    evidence id and one belonging to a decision the caller doesn't own both
    surface as the same 404.
    """
    evidence = evidence_service.get_evidence(evidence_id)
    _ensure_owns_parent_decision(decision_service, user_id, evidence)
    return evidence


@evidence_router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: UUID,
    evidence_service: EvidenceServiceDep,
    decision_service: DecisionServiceDep,
    user_id: CurrentUserIdDep,
) -> None:
    """Delete a piece of evidence and its underlying stored file."""
    evidence = evidence_service.get_evidence(evidence_id)
    _ensure_owns_parent_decision(decision_service, user_id, evidence)
    evidence_service.delete_evidence(evidence_id)


async def _read_bounded(file: UploadFile) -> bytes:
    """Read an uploaded file's body, rejecting it once it exceeds the
    configured size limit rather than after buffering the whole thing.

    `EvidenceService.upload_evidence` also re-checks the final size (a
    defense-in-depth check on whatever bytes it's handed), but reading in
    bounded chunks here means an oversized upload is rejected as soon as
    it crosses the limit instead of first being fully read into memory -
    an oversized-upload DoS shouldn't be able to exhaust memory before
    validation ever runs.
    """
    max_bytes = get_settings().max_upload_size_bytes
    chunk_size = 1024 * 1024  # 1 MB
    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise PayloadTooLargeError(
                detail=f"File exceeds the maximum allowed size of {max_bytes} bytes."
            )
        chunks.append(chunk)

    return b"".join(chunks)


def _ensure_owns_parent_decision(
    decision_service: DecisionService, user_id: str, evidence: Evidence
) -> None:
    try:
        decision_service.get_decision(user_id, evidence.decision_id)
    except NotFoundError as exc:
        # Re-raised as evidence-not-found rather than decision-not-found,
        # since the caller asked about the evidence id, not the decision.
        raise NotFoundError(detail=f"Evidence {evidence.id} not found.") from exc

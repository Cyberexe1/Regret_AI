"""The `ResearchProvider` abstraction and shared URL safety validation.

Nothing outside this package (and `app.research.service`, which wraps a
provider with budget limits) should ever import a concrete provider class
directly - callers depend only on this Protocol, so the underlying search
implementation can be swapped (a different HTTP API, a different vendor,
a test stub) without touching `app.agents.research_agent` or the
orchestrator at all.
"""

from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlparse

from app.core.errors import ValidationError

if TYPE_CHECKING:
    from app.research.schemas import ResearchResult

# Only plain http/https are ever accepted. Every other scheme -
# `javascript:`, `data:`, `file:`, `ftp:`, etc. - is treated as unsafe and
# rejected outright; a `ResearchResult`/`ExternalEvidence` URL is never
# "executed" anywhere, but rejecting unsafe schemes at the boundary means
# nothing downstream (a future frontend link, a re-fetch) can be tricked
# into treating one as safe to open.
_ALLOWED_SCHEMES = {"http", "https"}

# Generous but bounded - a URL this long is almost certainly malformed or
# an attempt to smuggle something unexpected through a "url" field.
_MAX_URL_LENGTH = 2048


def validate_external_url(url: str) -> str:
    """Validate that `url` is a safe, well-formed http(s) URL.

    Raises `ValidationError` (a 400-class `AppError`, never leaking parser
    internals) if the URL is empty, oversized, missing a scheme/host, or
    uses any scheme other than http/https. This is the single choke point
    every externally-sourced URL passes through before being allowed into
    a `ResearchResult` or `ExternalEvidence` record - see
    `app.research.schemas.ResearchResult`'s validator and
    `app.agents.schemas.ExternalEvidence`.
    """
    if not url or not url.strip():
        raise ValidationError(detail="Source URL must not be empty.")
    candidate = url.strip()
    if len(candidate) > _MAX_URL_LENGTH:
        raise ValidationError(detail="Source URL exceeds the maximum allowed length.")

    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValidationError(
            detail=f"Source URL scheme '{parsed.scheme or 'none'}' is not allowed; only "
            "http/https URLs are accepted."
        )
    if not parsed.netloc:
        raise ValidationError(detail="Source URL must include a valid host.")

    return candidate


class ResearchProvider(Protocol):
    """A pluggable external search backend.

    Implementations translate a plain-text query into real
    `ResearchResult`s from an actual external source - never fabricated
    results. See `app.research.providers` for concrete implementations and
    `app.research.service.ResearchService` for the budget-limited,
    failure-tolerant wrapper every caller actually uses.
    """

    async def search(self, query: str, *, max_results: int = 5) -> list["ResearchResult"]:
        """Return up to `max_results` real results for `query`.

        Implementations must never return a fabricated result - if the
        underlying API returns nothing, an empty list is the correct
        response, never an invented placeholder result.
        """
        ...

"""File storage abstraction for evidence uploads.

`StorageBackend` is the interface every route/service depends on. Only
`LocalStorageBackend` exists today - it writes to a directory on disk and
needs no AWS credentials at all, which keeps local development independent
of any cloud account. An S3-backed implementation can be added later behind
the same interface without touching callers; selecting `storage_backend =
"s3"` today raises `NotImplementedError` rather than silently misbehaving.

Security notes:
- Filenames are never taken verbatim from client input. Every stored file
  gets a server-generated name (`<uuid>.<safe-extension>`), which is the
  primary defense against path traversal and filename-injection issues.
- The resolved storage path is always verified to stay inside the storage
  root before any write/read/delete, as a second, independent guard.
"""

import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import RepositoryError
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageBackend(ABC):
    """Persists and retrieves raw file bytes by an opaque storage key."""

    @abstractmethod
    def save(self, content: bytes, extension: str) -> str:
        """Persist `content` and return a storage key that can later locate it."""

    @abstractmethod
    def read(self, storage_key: str) -> bytes:
        """Return the raw bytes previously saved under `storage_key`."""

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Remove the file stored under `storage_key`, if it exists."""


class LocalStorageBackend(StorageBackend):
    """Stores files on the local filesystem under a configured directory."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = (root or Path(get_settings().local_storage_dir)).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, content: bytes, extension: str) -> str:
        storage_key = f"{uuid.uuid4()}{extension}"
        path = self._resolve(storage_key)
        path.write_bytes(content)
        return storage_key

    def read(self, storage_key: str) -> bytes:
        path = self._resolve(storage_key)
        if not path.is_file():
            raise RepositoryError(detail="Stored evidence file could not be found.")
        return path.read_bytes()

    def delete(self, storage_key: str) -> None:
        path = self._resolve(storage_key)
        path.unlink(missing_ok=True)

    def _resolve(self, storage_key: str) -> Path:
        """Resolve `storage_key` to a path guaranteed to be inside the storage root.

        `storage_key` is always a server-generated `<uuid>.<ext>` (never raw
        client input), but this check is kept as a defense-in-depth guard
        against path traversal regardless of how the key was produced.
        """
        candidate = (self._root / storage_key).resolve()
        if self._root not in candidate.parents and candidate != self._root:
            logger.error("Rejected storage key resolving outside storage root: %s", storage_key)
            raise RepositoryError(detail="Invalid storage reference.")
        return candidate


def get_storage_backend() -> StorageBackend:
    """Return the configured storage backend.

    FastAPI dependency accessor - constructs a fresh backend per call today
    (cheap: just a directory handle), matching the pattern used for other
    repositories in this codebase.
    """
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalStorageBackend()
    raise NotImplementedError(
        f"Storage backend '{settings.storage_backend}' is not implemented yet. "
        "Only 'local' is available in this step."
    )

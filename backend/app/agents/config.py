"""Amazon Bedrock model provider configuration for Strands agents.

Centralized so every agent constructs its model the same way, from the
same environment-driven settings - no agent should build a `BedrockModel`
directly.
"""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import TypeVar

from botocore.exceptions import EventStreamError
from strands.models import BedrockModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Observed in production: Bedrock occasionally raises a transient
# `modelStreamErrorException` mid-stream ("Model produced invalid sequence
# as part of ToolUse") for reasons unrelated to the prompt itself - a
# retry with the exact same request routinely succeeds. This is narrowly
# scoped to that one transient failure mode; it never retries a genuine
# validation/timeout/programming error, and it never changes what's sent
# to the model.
_MAX_INVOKE_ATTEMPTS = 3
_RETRY_BASE_DELAY_SECONDS = 1.5


@lru_cache
def get_bedrock_model() -> BedrockModel:
    """Return a process-wide Bedrock model provider.

    No AWS credentials are constructed here - `BedrockModel` resolves them
    itself through boto3's standard credential provider chain (environment
    variables, shared credentials file, an assumed role, or an instance
    profile), exactly like the DynamoDB layer does.
    """
    settings = get_settings()
    return BedrockModel(
        model_id=settings.bedrock_model_id,
        region_name=settings.aws_region,
    )


def reset_bedrock_model_cache() -> None:
    """Clear the cached model provider. Used by tests that mock the model."""
    get_bedrock_model.cache_clear()


async def invoke_with_retry(call: Callable[[], Awaitable[T]], *, agent_name: str) -> T:
    """Run one Bedrock-backed agent call, retrying only on a transient
    mid-stream provider error.

    `call` is re-invoked, at most `_MAX_INVOKE_ATTEMPTS` times total, only
    when it raises `botocore.exceptions.EventStreamError` (the exception
    class for a `modelStreamErrorException`/similar mid-stream failure
    surfaced by `converse_stream`). Every other exception - a genuine
    validation error, `TimeoutError` from the caller's own
    `asyncio.wait_for`, throttling, access-denied, etc. - propagates on
    the first attempt, unchanged, exactly as before this helper existed.
    The prompt/request is never altered between attempts; this only
    guards against the model provider's own transient hiccups, never
    papers over a real failure.
    """
    last_error: EventStreamError | None = None
    for attempt in range(1, _MAX_INVOKE_ATTEMPTS + 1):
        try:
            return await call()
        except EventStreamError as exc:
            last_error = exc
            if attempt == _MAX_INVOKE_ATTEMPTS:
                break
            delay = _RETRY_BASE_DELAY_SECONDS * attempt + random.uniform(0, 0.5)
            logger.warning(
                "Transient Bedrock stream error for %s (attempt %d/%d), retrying in %.1fs: %s",
                agent_name,
                attempt,
                _MAX_INVOKE_ATTEMPTS,
                delay,
                str(exc)[:200],
            )
            await asyncio.sleep(delay)

    assert last_error is not None  # loop only exits this way after setting it
    raise last_error

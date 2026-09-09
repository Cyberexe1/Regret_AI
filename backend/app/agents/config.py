"""Amazon Bedrock model provider configuration for Strands agents.

Centralized so every agent constructs its model the same way, from the
same environment-driven settings - no agent should build a `BedrockModel`
directly.
"""

from functools import lru_cache

from strands.models import BedrockModel

from app.core.config import get_settings


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

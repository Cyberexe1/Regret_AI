"""Application configuration.

All runtime configuration is loaded from environment variables (via a local
.env file in development). Nothing here should ever contain a real secret -
see .env.example for the documented variable list.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, populated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "REGRET ENGINE"
    app_env: str = "development"
    debug: bool = True

    api_v1_prefix: str = "/api/v1"

    # Comma-separated list of allowed CORS origins. Defaults to the standard
    # local Vite dev server origin so the existing frontend can talk to the
    # API out of the box in development.
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    log_level: str = "INFO"

    # --- DynamoDB -----------------------------------------------------------
    # No AWS keys live here or anywhere else in source: boto3 resolves
    # credentials itself via the standard provider chain (environment,
    # shared config/credentials files, an assumed role, an EC2/ECS/Lambda
    # instance profile, etc).
    aws_region: str = "ap-south-1"
    dynamodb_table_name: str = "regret-engine"
    # Optional. Only set this for local development against a
    # DynamoDB-compatible endpoint (e.g. DynamoDB Local or moto's server
    # mode). Leave unset to use real AWS DynamoDB.
    aws_endpoint_url: str | None = None

    # Placeholder identity used until real authentication exists. Every
    # decision is currently attributed to this user id so the data model and
    # access patterns are already user-scoped and ready for real auth later.
    default_user_id: str = "local-dev-user"

    @property
    def cors_origins(self) -> list[str]:
        """Parsed list of allowed CORS origins."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so the environment is only parsed once."""
    return Settings()

"""Response schemas for the health/readiness endpoints."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Simple liveness payload confirming the API is reachable.

    Deliberately never checks external dependencies (DynamoDB, Bedrock, an
    optional research provider) - a liveness check exists to answer "is
    the process up at all", and must not fail just because an optional
    dependency (research) is unavailable, or flap because of a transient
    AWS blip. See `ReadinessResponse` for dependency-aware status.
    """

    status: str = Field(default="ok", description="Health status of the service.")
    service: str = Field(default="regret-engine-api", description="Service identifier.")


class DependencyStatus(BaseModel):
    """Whether one external dependency looks reachable right now."""

    name: str
    status: str = Field(description="'ok', 'unavailable', or 'not_configured'.")
    required: bool = Field(
        description="Whether this dependency being unavailable should be considered "
        "degraded readiness. Research is never required; DynamoDB always is."
    )


class ReadinessResponse(BaseModel):
    """Dependency-aware readiness payload.

    Distinct from `HealthResponse`: this endpoint actually probes
    DynamoDB (a required dependency - the API can't serve real requests
    without it) and reports the configured research provider's status
    (optional - its absence never affects overall readiness). `status` is
    "ready" only if every *required* dependency is reachable.
    """

    status: str = Field(description="'ready' or 'degraded'.")
    dependencies: list[DependencyStatus]

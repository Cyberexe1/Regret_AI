"""Response schema for the health check endpoint."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Simple liveness payload confirming the API is reachable."""

    status: str = Field(default="ok", description="Health status of the service.")
    service: str = Field(default="regret-engine-api", description="Service identifier.")

"""Health and readiness check routes."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.repositories.dynamodb import check_table_reachable
from app.research.service import get_research_provider
from app.schemas.health import DependencyStatus, HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Confirm the API process is up and responding.

    Never checks external dependencies - see `HealthResponse`'s
    docstring. Use `GET /api/v1/ready` to also check DynamoDB
    reachability.
    """
    return HealthResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def get_readiness() -> ReadinessResponse:
    """Report whether the API's required dependencies are reachable.

    DynamoDB is required - a failure there marks the service `degraded`.
    The external research provider is optional and never affects overall
    readiness (research being unavailable is an expected, handled state -
    see `AgentRunStatus.UNAVAILABLE`); its status is reported purely for
    visibility.
    """
    settings = get_settings()
    dependencies: list[DependencyStatus] = []

    dynamodb_status = "ok" if check_table_reachable() else "unavailable"
    dependencies.append(DependencyStatus(name="dynamodb", status=dynamodb_status, required=True))

    research_provider = get_research_provider(settings)
    research_status = "ok" if research_provider is not None else "not_configured"
    dependencies.append(
        DependencyStatus(name="research_provider", status=research_status, required=False)
    )

    overall_status = "ready" if dynamodb_status == "ok" else "degraded"
    return ReadinessResponse(status=overall_status, dependencies=dependencies)

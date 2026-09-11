"""REGRET ENGINE API entrypoint.

Wires together the full decision-intelligence pipeline (Decision Analyzer
through Experiment Planner/Re-evaluation), request-id propagation,
structured logging, and standardized error handling. See README.md for
the current scope and architecture.
"""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    adaptive,
    analysis,
    decision_analysis_resources,
    decisions,
    evidence,
    evolution,
    experiments,
    health,
    historical_context,
    learning,
    memory,
    research,
    value_of_information,
)
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.request_context import (
    generate_request_id,
    is_valid_client_request_id,
    set_request_id,
)

_REQUEST_ID_HEADER = "X-Request-ID"

settings = get_settings()
configure_logging()
logger = get_logger(__name__)

# Fail fast, before the app even starts serving, if production is missing
# configuration it needs - see `Settings.validate_for_production`.
settings.validate_for_production()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "%s starting up | env=%s | debug=%s | cors_origins=%s",
        settings.app_name,
        settings.app_env,
        settings.debug,
        settings.cors_origins,
    )
    yield
    logger.info("%s shutting down", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "REGRET ENGINE decision-intelligence API: Decision Analyzer, "
        "Assumption Hunter, Blindspot Hunter, external Research Agent, "
        "Evidence Agent, Devil's Advocate, Regret Simulator, Threshold "
        "Engine, Experiment Planner, and the experiment result / "
        "re-evaluation loop."
    ),
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach a request id to every request, and log its outcome.

    If the client supplies a well-formed `X-Request-ID` header, it's
    preserved (so a caller can correlate their own logs with ours);
    otherwise one is generated. Always echoed back on the response so the
    caller can capture it even if they didn't send one themselves.
    """
    client_request_id = request.headers.get(_REQUEST_ID_HEADER)
    request_id = (
        client_request_id
        if is_valid_client_request_id(client_request_id)
        else generate_request_id()
    )
    set_request_id(request_id)
    request.state.request_id = request_id

    started = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - started) * 1000

    response.headers[_REQUEST_ID_HEADER] = request_id
    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# Origins are environment-configured. Development defaults to the local Vite
# dev server only - never falls back to "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(decisions.router, prefix=settings.api_v1_prefix)
app.include_router(evidence.decision_evidence_router, prefix=settings.api_v1_prefix)
app.include_router(evidence.evidence_router, prefix=settings.api_v1_prefix)
app.include_router(analysis.router, prefix=settings.api_v1_prefix)
app.include_router(experiments.decision_experiments_router, prefix=settings.api_v1_prefix)
app.include_router(experiments.experiments_router, prefix=settings.api_v1_prefix)
app.include_router(research.router, prefix=settings.api_v1_prefix)
app.include_router(decision_analysis_resources.router, prefix=settings.api_v1_prefix)
app.include_router(memory.decision_memory_router, prefix=settings.api_v1_prefix)
app.include_router(memory.memory_router, prefix=settings.api_v1_prefix)
app.include_router(historical_context.router, prefix=settings.api_v1_prefix)
app.include_router(value_of_information.router, prefix=settings.api_v1_prefix)
app.include_router(adaptive.router, prefix=settings.api_v1_prefix)
app.include_router(evolution.router, prefix=settings.api_v1_prefix)
app.include_router(learning.router, prefix=settings.api_v1_prefix)

"""REGRET ENGINE API entrypoint.

Step 1 foundation: health check + decision placeholder endpoints only.
No AI agents, no Bedrock, no Strands, no database - see README.md for the
current scope and planned architecture.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, decisions, evidence, health
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


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
        "REGRET ENGINE decision-intelligence API. This build exposes only the "
        "health check and decision intake endpoints; the analysis pipeline "
        "(assumptions, blindspots, evidence, stress-testing, regret "
        "simulation, thresholds, experiments) is not implemented yet."
    ),
    lifespan=lifespan,
)

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

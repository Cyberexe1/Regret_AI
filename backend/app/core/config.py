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

    # --- Amazon Bedrock (AI agents) --------------------------------------------
    # No API keys live here: the Strands Agents SDK's BedrockModel resolves AWS
    # credentials through boto3's standard provider chain, same as DynamoDB
    # above. `bedrock_model_id` defaults to the Strands SDK's own current
    # default model - override via env if your account/region needs a
    # different one.
    bedrock_model_id: str = "apac.amazon.nova-pro-v1:0"
    # Wall-clock budget for a single agent model call. Guards against a hung
    # Bedrock request blocking an API request indefinitely.
    bedrock_invoke_timeout_seconds: float = 60.0
    # Wall-clock budget for one entire analysis run (all ~9 sequential
    # agent stages combined). A second, independent safety net on top of
    # each stage's own `bedrock_invoke_timeout_seconds` - guards against
    # the run as a whole ever staying `running` indefinitely, even if a
    # future stage were added without its own per-call timeout. Generous
    # by default since stages run sequentially, never in parallel (see the
    # pipeline's dependency-order requirement).
    analysis_max_duration_seconds: float = 600.0
    # How much older than `analysis_max_duration_seconds` an "active"
    # analysis lock must be before a new `/analyze` call is allowed to
    # treat it as abandoned (e.g. the process crashed mid-run) and
    # re-acquire it, rather than treating the decision as still busy.
    analysis_lock_grace_seconds: float = 120.0

    # --- External research (optional) ------------------------------------------
    # Research is OFF by default - `research_provider` must be explicitly set
    # to a recognized value ("http" for the built-in httpx-based provider,
    # "none"/unset to disable) before the Research Agent's stage ever runs.
    # No API key lives here unencrypted in any committed file; like every
    # other credential in this project, it's read from the environment only.
    research_provider: str = "none"
    research_api_key: str | None = None
    # Conservative defaults, per the "prevent runaway research" requirement -
    # a single analysis should never fan out into dozens of searches.
    research_max_queries: int = 3
    research_max_results_per_query: int = 5
    research_max_total_sources: int = 10
    research_timeout_seconds: float = 15.0
    research_max_retries: int = 2
    # Upper bound on how much raw snippet text from one external result is
    # ever kept - mirrors `MAX_CONTENT_REFERENCE_CHARS` in
    # app.services.evidence, applied here to untrusted external content.
    research_max_snippet_chars: int = 1000

    # --- Abuse protection ---------------------------------------------------
    # Bounds how many analysis pipelines (each making up to ~10 sequential
    # Bedrock calls) can run concurrently in this process - a cheap guard
    # against one client's burst of `/analyze` calls (for different
    # decisions - the same decision is already deduplicated via
    # `AnalysisRepository.get_active_run`) exhausting Bedrock capacity or
    # this process's own resources. Not a distributed rate limiter - see
    # module-level "reasonable protection for a hackathon production demo,
    # not a full API gateway" guidance.
    max_concurrent_analyses: int = 5

    # --- Decision Similarity & Historical Insight Engine (REGRET ENGINE 2.0) ---
    # No vector DB, no embeddings - similarity is deterministic, multi-feature
    # scoring over a user's own past decisions (see app.memory.similarity).
    # These three bounds keep it a cheap, in-process computation even for a
    # user with a long decision history, mirroring the "prevent runaway
    # research" bounding pattern used for `research_max_*` above.
    #
    # How many of the user's own most recent past decisions are even
    # considered as similarity candidates (via the existing GSI1 user
    # index) before scoring - never a full, unbounded scan of history.
    historical_search_limit: int = 20
    # Of those candidates, how many of the highest-scoring ones are kept
    # as "relevant decisions" after scoring.
    historical_top_k: int = 5
    # Upper bound on how many individual `HistoricalInsight` records are
    # ever surfaced in one `HistoricalContext`, across all relevant
    # decisions combined.
    historical_insight_limit: int = 10

    # --- Adaptive Experiment Loop (REGRET ENGINE 2.0, Step 21) -----------------
    # Hard ceiling on how many adaptive cycles (experiment -> result ->
    # re-evaluation -> next experiment) a single decision can go through.
    # Guards against an infinite loop - see app.adaptive.service. A cycle
    # that would exceed this limit is marked `blocked` with an explicit
    # stopping reason rather than silently continuing forever.
    max_adaptive_cycles: int = 8

    # --- Decision Evolution & Causal Timeline (REGRET ENGINE 2.0, Step 22) ----
    # Upper bound on how many events one `GET /decisions/{id}/evolution`
    # response ever returns. When a decision's real history exceeds this,
    # the OLDEST events are dropped first (never the most recent ones), so
    # "what changed most recently" always stays visible - see
    # app.evolution.service.DecisionEvolutionService.get_evolution.
    evolution_max_events: int = 200

    # --- Cross-Decision Learning Engine (REGRET ENGINE 2.0, Step 23) ----------
    # No LLM call, no vector DB, no embeddings - deterministic pattern
    # detection over a user's own past decisions only (see
    # app.learning.pattern_detector). Bounds how many of the user's own
    # most recent decisions one `refresh_patterns()` call considers -
    # mirrors `historical_search_limit`'s own bounding pattern so a user
    # with a long decision history never triggers an unbounded scan.
    learning_max_decisions_scanned: int = 50

    # --- Decision Intelligence Quality & Calibration Engine (REGRET ENGINE 2.0, Step 24) ---
    # No LLM call, no vector DB - deterministic rule checks over a
    # decision's own already-persisted records (see app.quality.rules)
    # and deterministic calibration aggregation over a user's own
    # completed experiments (see app.quality.calibration). Reuses
    # `learning_max_decisions_scanned` above as the calibration bound
    # rather than inventing a second, separate limit for the same kind
    # of "how much of a user's history to scan" bounding concern.

    # --- Adaptive Decision Interview Agent (REGRET ENGINE 2.0, Step 27) -------
    # Hard ceiling on how many user turns one interview can go through -
    # spec section 12's "MUST NOT continue indefinitely." Question
    # SELECTION is deterministic (see app.interview.question_selector);
    # only the per-turn extraction/phrasing call actually reaches
    # Bedrock, reusing `bedrock_invoke_timeout_seconds` above rather than
    # inventing a second per-call timeout for the same kind of call.
    interview_max_turns: int = 7

    @property
    def research_enabled(self) -> bool:
        return self.research_provider.strip().lower() not in {"", "none"}

    # --- Evidence storage -----------------------------------------------------
    # "local" is the only implemented backend. The interface
    # (app.services.storage.StorageBackend) is shaped so "s3" can be added
    # later without changing any calling code; selecting it today raises a
    # clear NotImplementedError rather than silently doing the wrong thing.
    storage_backend: str = "local"
    # Directory evidence files are written to. Relative paths are resolved
    # against the backend/ working directory. Never requires AWS credentials.
    local_storage_dir: str = "./data/evidence"
    # Reserved for the future S3-backed StorageBackend implementation (see
    # app.services.storage). Selecting `storage_backend=s3` today still
    # raises NotImplementedError - this setting exists now so production
    # config validation can require it once that backend lands, without
    # a config schema change at that point.
    s3_bucket_name: str = ""
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    # Comma-separated list of allowed upload extensions, dot-prefixed.
    allowed_evidence_extensions: str = ".pdf,.docx,.txt"

    @property
    def allowed_extensions(self) -> set[str]:
        return {
            ext.strip().lower()
            for ext in self.allowed_evidence_extensions.split(",")
            if ext.strip()
        }

    @property
    def cors_origins(self) -> list[str]:
        """Parsed list of allowed CORS origins."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    def validate_for_production(self) -> None:
        """Fail fast at startup if `APP_ENV=production` is missing configuration
        it needs to run safely.

        Deliberately does nothing when `app_env` isn't `production` -
        local/development mode never requires any of these to be set
        explicitly, since sensible defaults exist for that case. Raises
        `RuntimeError` (crashing startup, which is the intended behavior -
        an under-configured production process should never silently
        start serving traffic) rather than logging a warning and
        continuing.
        """
        if not self.is_production:
            return

        problems: list[str] = []

        if not self.aws_region.strip():
            problems.append("AWS_REGION must be set in production.")
        if not self.dynamodb_table_name.strip():
            problems.append("DYNAMODB_TABLE_NAME must be set in production.")
        if not self.bedrock_model_id.strip():
            problems.append("BEDROCK_MODEL_ID must be set in production.")
        if not self.cors_origins:
            problems.append("CORS_ALLOWED_ORIGINS must be set in production.")
        if "*" in self.cors_origins:
            problems.append(
                "CORS_ALLOWED_ORIGINS must not be '*' in production; list explicit origins."
            )
        if self.storage_backend not in {"local", "s3"}:
            problems.append(f"Unknown STORAGE_BACKEND '{self.storage_backend}' in production.")
        if self.storage_backend == "s3" and not self.s3_bucket_name.strip():
            problems.append("S3_BUCKET_NAME must be set in production when STORAGE_BACKEND=s3.")

        if problems:
            raise RuntimeError(
                "Invalid production configuration:\n" + "\n".join(f"  - {p}" for p in problems)
            )


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so the environment is only parsed once."""
    return Settings()

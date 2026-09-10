"""Budget-limited, failure-tolerant wrapper around a `ResearchProvider`.

`app.agents.research_agent` (and anything else that needs external
research) calls `ResearchService`, never a concrete provider directly.
This is the single place that:

- selects the active provider from `Settings.research_provider`
- enforces the configured research budget (max queries, max results per
  query, max total sources across an entire analysis run, timeout, retry
  count) so one analysis can never fan out into runaway searching
- retries a transient provider failure a bounded number of times
- turns any provider failure (timeout, HTTP error, malformed response)
  into a clean `ResearchUnavailable` signal rather than letting it
  propagate and break the rest of the analysis pipeline
"""

import asyncio
from dataclasses import dataclass, field

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.research.provider import ResearchProvider
from app.research.providers.duckduckgo import DuckDuckGoProvider
from app.research.schemas import ResearchResult

logger = get_logger(__name__)


class ResearchUnavailable(Exception):
    """Raised when the configured research provider could not be reached
    after retries, or when research is not enabled at all.

    Callers (the Research Agent / orchestrator) MUST catch this and
    continue the analysis using whatever evidence already exists - see the
    module-level "research failure must not break the entire analysis"
    requirement. This exception is never allowed to fabricate a fallback
    research result.
    """


def get_research_provider(settings: Settings | None = None) -> ResearchProvider | None:
    """Return the configured provider instance, or `None` if research is disabled.

    This is the only place a concrete provider class is ever instantiated -
    everything else depends on the `ResearchProvider` Protocol.
    """
    settings = settings or get_settings()
    provider_name = settings.research_provider.strip().lower()
    if provider_name in {"", "none"}:
        return None
    if provider_name in {"http", "duckduckgo"}:
        return DuckDuckGoProvider(timeout_seconds=settings.research_timeout_seconds)
    logger.warning("Unrecognized research_provider=%s; research disabled.", provider_name)
    return None


@dataclass
class ResearchBudget:
    """Tracks how much of the configured research budget has been spent
    across one analysis run's worth of queries.

    A fresh `ResearchBudget` must be created per analysis run - it is
    never shared or reused across decisions, so one decision's research
    never counts against another's limits.
    """

    max_queries: int
    max_results_per_query: int
    max_total_sources: int
    queries_used: int = 0
    sources_returned: int = 0
    exhausted_reason: str | None = field(default=None)

    def remaining_queries(self) -> int:
        return max(0, self.max_queries - self.queries_used)

    def remaining_sources(self) -> int:
        return max(0, self.max_total_sources - self.sources_returned)

    def can_query(self) -> bool:
        if self.queries_used >= self.max_queries:
            self.exhausted_reason = f"Reached the maximum of {self.max_queries} queries."
            return False
        if self.sources_returned >= self.max_total_sources:
            self.exhausted_reason = f"Reached the maximum of {self.max_total_sources} sources."
            return False
        return True


class ResearchService:
    """Runs a bounded set of research queries against the configured provider."""

    def __init__(
        self, settings: Settings | None = None, provider: ResearchProvider | None = None
    ) -> None:
        self._settings = settings or get_settings()
        self._provider = (
            provider if provider is not None else get_research_provider(self._settings)
        )

    @property
    def enabled(self) -> bool:
        return self._provider is not None

    def new_budget(self) -> ResearchBudget:
        return ResearchBudget(
            max_queries=self._settings.research_max_queries,
            max_results_per_query=self._settings.research_max_results_per_query,
            max_total_sources=self._settings.research_max_total_sources,
        )

    async def run_queries(
        self, queries: list[str], budget: ResearchBudget | None = None
    ) -> tuple[dict[str, list[ResearchResult]], ResearchBudget]:
        """Run each query in `queries` (bounded by budget) and return the
        per-query results plus the budget as spent.

        Raises `ResearchUnavailable` if research isn't enabled at all, or
        if the provider fails on every retry for every query attempted -
        callers must catch this and continue without external evidence.
        A provider failure on some (but not all) queries does not raise -
        the failed query's slot is simply skipped, logged, and budget is
        still consumed for the attempt, so a single flaky query can't be
        retried indefinitely by the caller re-invoking this method.
        """
        if not self.enabled:
            raise ResearchUnavailable("No research provider is configured.")

        budget = budget or self.new_budget()
        results_by_query: dict[str, list[ResearchResult]] = {}
        any_success = False
        any_attempt = False

        for query in queries[: budget.max_queries]:
            if not budget.can_query():
                break
            any_attempt = True
            budget.queries_used += 1

            max_results = min(
                self._settings.research_max_results_per_query, budget.remaining_sources()
            )
            if max_results <= 0:
                break

            try:
                query_results = await self._search_with_retries(query, max_results)
            except Exception as exc:  # noqa: BLE001 - any provider failure lands here, never crashes the caller
                logger.warning(
                    "Research query failed after retries query=%r error=%s", query, str(exc)[:200]
                )
                results_by_query[query] = []
                continue

            any_success = True
            results_by_query[query] = query_results
            budget.sources_returned += len(query_results)

        if any_attempt and not any_success:
            raise ResearchUnavailable(
                "The research provider failed on every attempted query for this analysis."
            )

        return results_by_query, budget

    async def _search_with_retries(self, query: str, max_results: int) -> list[ResearchResult]:
        last_exception: Exception | None = None
        attempts = self._settings.research_max_retries + 1
        for attempt in range(attempts):
            try:
                return await asyncio.wait_for(
                    self._provider.search(query, max_results=max_results),
                    timeout=self._settings.research_timeout_seconds,
                )
            except (TimeoutError, httpx.HTTPError, httpx.TimeoutException) as exc:
                last_exception = exc
                if attempt < attempts - 1:
                    logger.info(
                        "Retrying research query attempt=%d/%d query=%r",
                        attempt + 1,
                        attempts,
                        query,
                    )
                    continue
            except Exception as exc:  # noqa: BLE001 - non-network provider errors still bound the retry loop
                last_exception = exc
                break
        assert last_exception is not None
        raise last_exception

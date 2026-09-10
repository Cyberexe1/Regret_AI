"""Tests for `ResearchService`, `ResearchBudget`, and URL validation.

Uses an in-memory stub `ResearchProvider` throughout - no real HTTP call
happens anywhere in this file, and no real Bedrock/Strands call is
involved (this module has nothing to do with the LLM-facing agent).
"""

from datetime import UTC, datetime

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import ValidationError
from app.research.provider import validate_external_url
from app.research.schemas import ResearchResult
from app.research.service import ResearchService, ResearchUnavailable


class _StubProvider:
    """An in-memory `ResearchProvider` whose behavior is fully scripted by
    the test - never touches the network."""

    def __init__(
        self,
        *,
        results: list[ResearchResult] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._results = results if results is not None else []
        self._error = error
        self.calls: list[tuple[str, int]] = []

    async def search(self, query: str, *, max_results: int = 5) -> list[ResearchResult]:
        self.calls.append((query, max_results))
        if self._error is not None:
            raise self._error
        return self._results[:max_results]


class _FlakyProvider:
    """Fails a configured number of times, then succeeds - used to verify retry behavior."""

    def __init__(self, fail_times: int, results: list[ResearchResult]) -> None:
        self._fail_times = fail_times
        self._results = results
        self.attempts = 0

    async def search(self, query: str, *, max_results: int = 5) -> list[ResearchResult]:
        self.attempts += 1
        if self.attempts <= self._fail_times:
            raise httpx.ConnectTimeout("simulated timeout")
        return self._results[:max_results]


def _result(query: str = "q", url: str = "https://example.com/a") -> ResearchResult:
    return ResearchResult(
        title="Example title",
        url=url,
        source_name="example.com",
        snippet="Example snippet.",
        retrieved_at=datetime.now(UTC),
        query=query,
    )


def _settings(**overrides) -> Settings:
    defaults = dict(
        research_provider="stub",
        research_max_queries=3,
        research_max_results_per_query=5,
        research_max_total_sources=10,
        research_timeout_seconds=1.0,
        research_max_retries=2,
    )
    defaults.update(overrides)
    return Settings(**defaults)


# --- Provider: successful search ---------------------------------------------


@pytest.mark.asyncio
async def test_successful_search_returns_real_results() -> None:
    provider = _StubProvider(results=[_result(), _result(url="https://example.com/b")])
    service = ResearchService(settings=_settings(), provider=provider)

    results_by_query, budget = await service.run_queries(["query one"])

    assert len(results_by_query["query one"]) == 2
    assert budget.sources_returned == 2
    assert budget.queries_used == 1


# --- Provider: empty result ---------------------------------------------------


@pytest.mark.asyncio
async def test_empty_result_is_a_valid_outcome_not_an_error() -> None:
    provider = _StubProvider(results=[])
    service = ResearchService(settings=_settings(), provider=provider)

    results_by_query, budget = await service.run_queries(["obscure query"])

    assert results_by_query["obscure query"] == []
    assert budget.sources_returned == 0


# --- Provider: timeout ---------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_timeout_on_every_query_raises_research_unavailable() -> None:
    provider = _StubProvider(error=httpx.ConnectTimeout("simulated timeout"))
    service = ResearchService(settings=_settings(research_max_retries=0), provider=provider)

    with pytest.raises(ResearchUnavailable):
        await service.run_queries(["query one"])


# --- Provider: error ------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_http_error_on_every_query_raises_research_unavailable() -> None:
    provider = _StubProvider(
        error=httpx.HTTPStatusError(
            "server error", request=httpx.Request("POST", "https://x"), response=httpx.Response(500)
        )
    )
    service = ResearchService(settings=_settings(research_max_retries=0), provider=provider)

    with pytest.raises(ResearchUnavailable):
        await service.run_queries(["query one"])


# --- Provider: invalid response (malformed result) ------------------------------


def test_invalid_result_url_is_rejected_at_construction() -> None:
    """A provider trying to construct a ResearchResult with an unsafe URL
    must fail immediately - the Pydantic validator is the safety net."""
    with pytest.raises(ValidationError):
        ResearchResult(
            title="x",
            url="javascript:alert(1)",
            source_name="x",
            snippet="x",
            retrieved_at=datetime.now(UTC),
            query="x",
        )


# --- Provider: retry behavior ---------------------------------------------------


@pytest.mark.asyncio
async def test_retry_behavior_succeeds_after_transient_failures() -> None:
    flaky = _FlakyProvider(fail_times=2, results=[_result()])
    service = ResearchService(settings=_settings(research_max_retries=2), provider=flaky)

    results_by_query, _budget = await service.run_queries(["query one"])

    assert flaky.attempts == 3  # 2 failures + 1 success
    assert len(results_by_query["query one"]) == 1


@pytest.mark.asyncio
async def test_retry_exhausted_raises_research_unavailable() -> None:
    flaky = _FlakyProvider(fail_times=5, results=[_result()])
    service = ResearchService(settings=_settings(research_max_retries=1), provider=flaky)

    with pytest.raises(ResearchUnavailable):
        await service.run_queries(["query one"])

    assert flaky.attempts == 2  # 1 initial attempt + 1 retry, then gives up


# --- Research budget ------------------------------------------------------------


@pytest.mark.asyncio
async def test_budget_caps_number_of_queries_run() -> None:
    provider = _StubProvider(results=[_result()])
    service = ResearchService(settings=_settings(research_max_queries=2), provider=provider)

    await service.run_queries(["a", "b", "c", "d"])

    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_budget_caps_total_sources_across_queries() -> None:
    provider = _StubProvider(results=[_result(), _result(), _result()])
    service = ResearchService(
        settings=_settings(research_max_queries=3, research_max_total_sources=4), provider=provider
    )

    results_by_query, budget = await service.run_queries(["a", "b", "c"])

    total_sources = sum(len(results) for results in results_by_query.values())
    assert total_sources <= 4
    assert budget.sources_returned <= 4


def test_disabled_research_service_has_enabled_false() -> None:
    service = ResearchService(settings=_settings(research_provider="none"))

    assert service.enabled is False


@pytest.mark.asyncio
async def test_disabled_research_service_raises_unavailable_immediately() -> None:
    service = ResearchService(settings=_settings(research_provider="none"))

    with pytest.raises(ResearchUnavailable):
        await service.run_queries(["query one"])


# --- URL validation --------------------------------------------------------------


def test_validate_external_url_accepts_https() -> None:
    assert validate_external_url("https://example.com/page") == "https://example.com/page"


def test_validate_external_url_accepts_http() -> None:
    assert validate_external_url("http://example.com/page") == "http://example.com/page"


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "ftp://example.com/file",
    ],
)
def test_validate_external_url_rejects_unsafe_schemes(unsafe_url: str) -> None:
    with pytest.raises(ValidationError):
        validate_external_url(unsafe_url)


def test_validate_external_url_rejects_empty_string() -> None:
    with pytest.raises(ValidationError):
        validate_external_url("")


def test_validate_external_url_rejects_oversized_url() -> None:
    with pytest.raises(ValidationError):
        validate_external_url("https://example.com/" + "a" * 3000)


def test_validate_external_url_rejects_missing_host() -> None:
    with pytest.raises(ValidationError):
        validate_external_url("https:///no-host")

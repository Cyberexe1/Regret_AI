"""HTTP-based `ResearchProvider` backed by DuckDuckGo's HTML search endpoint.

Chosen as the default concrete provider because it requires no API key
(nothing to configure, nothing to leak) and uses `httpx`, a dependency
Strands itself already pulls in - see `app.research.__init__`'s note that
no Strands-native search tool exists in the installed SDK version.

This provider treats the fetched HTML strictly as DATA to parse for
title/url/snippet triples - it never executes, evaluates, or otherwise
treats page content as instructions (there is no LLM call anywhere in
this file). The prompt-injection defense that matters for LLM-facing text
lives in `app.agents.research_agent`, which is the first place any of this
provider's output ever reaches a model.
"""

from datetime import UTC, datetime
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from lxml import html as lxml_html

from app.core.logging import get_logger
from app.research.provider import validate_external_url
from app.research.schemas import ResearchResult, SourceType

logger = get_logger(__name__)

_SEARCH_URL = "https://html.duckduckgo.com/html/"
_USER_AGENT = "RegretEngineResearchAgent/1.0 (+https://github.com/regret-engine)"


class DuckDuckGoProvider:
    """Real HTTP search against DuckDuckGo's HTML (JS-free) results page."""

    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self._timeout_seconds = timeout_seconds

    async def search(self, query: str, *, max_results: int = 5) -> list[ResearchResult]:
        """Return up to `max_results` real results for `query`.

        Returns an empty list (never raises, never fabricates a result) if
        the response can't be parsed or contains nothing usable - callers
        (`app.research.service.ResearchService`) are responsible for
        surfacing provider-level failures (timeouts, HTTP errors)
        separately; this method's own contract is "zero or more real
        results, nothing invented."
        """
        retrieved_at = datetime.now(UTC)
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                _SEARCH_URL,
                data={"q": query},
                headers={"User-Agent": _USER_AGENT},
            )
            response.raise_for_status()

        return self._parse_results(response.text, query, retrieved_at, max_results)

    @staticmethod
    def _parse_results(
        raw_html: str, query: str, retrieved_at: datetime, max_results: int
    ) -> list[ResearchResult]:
        results: list[ResearchResult] = []
        try:
            document = lxml_html.fromstring(raw_html)
        except Exception:  # noqa: BLE001 - malformed/unexpected HTML must never crash the pipeline
            logger.warning("DuckDuckGo response could not be parsed as HTML.")
            return results

        # XPath rather than CSS selectors - `cssselect` is not a project
        # dependency, and lxml's native XPath support requires nothing
        # extra.
        for node in document.xpath("//div[contains(@class, 'result')]"):
            if len(results) >= max_results:
                break

            link_node = node.xpath(".//a[contains(@class, 'result__a')]")
            if not link_node:
                continue
            title = (link_node[0].text_content() or "").strip()
            raw_href = link_node[0].get("href") or ""
            resolved_url = _resolve_redirect_url(raw_href)
            if not title or not resolved_url:
                continue

            snippet_node = node.xpath(".//*[contains(@class, 'result__snippet')]")
            snippet = (snippet_node[0].text_content() or "").strip() if snippet_node else ""

            try:
                safe_url = validate_external_url(resolved_url)
            except Exception:  # noqa: BLE001 - an unsafe/malformed URL is dropped, never surfaced
                logger.warning("Dropping DuckDuckGo result with unsafe/malformed URL.")
                continue

            source_name = urlparse(safe_url).netloc or "unknown source"
            results.append(
                ResearchResult(
                    title=title,
                    url=safe_url,
                    source_name=source_name,
                    snippet=snippet[:2000],
                    published_at=None,  # DuckDuckGo's HTML results never report a publish date
                    retrieved_at=retrieved_at,
                    source_type=SourceType.OTHER,
                    query=query,
                )
            )

        return results


def _resolve_redirect_url(href: str) -> str | None:
    """DuckDuckGo's HTML result links point through its own redirect
    (`//duckduckgo.com/l/?uddg=<real-url>&...`) - unwrap that to the real
    destination URL. Returns `None` (never a guess) if `href` doesn't carry
    a decodable destination.
    """
    if not href:
        return None
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    query_params = parse_qs(parsed.query)
    if "uddg" in query_params and query_params["uddg"]:
        return unquote(query_params["uddg"][0])
    # Already a direct URL (no redirect wrapper detected).
    if parsed.scheme and parsed.netloc:
        return href
    return None

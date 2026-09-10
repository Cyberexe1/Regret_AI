"""External research abstraction.

This package isolates "how we search the internet" from the rest of the
application. Nothing outside `app.research` should know whether search is
powered by a specific provider, an HTTP API, or a stub - every caller goes
through `ResearchProvider.search(...)` (see `provider.py`) via
`ResearchService` (see `service.py`), never a concrete provider directly.

No Strands-native web-search tool exists in the installed SDK (strands-agents
1.50.2 - inspected via its `vended_tools` package, which offers only
`http_request`, `bash`, `file_editor`, and `sleep`), so this package builds
its own small HTTP-based provider on top of `httpx` (already a Strands
dependency) rather than inventing a nonexistent Strands tool API.
"""

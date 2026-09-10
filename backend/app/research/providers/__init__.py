"""Concrete `ResearchProvider` implementations.

Nothing outside this subpackage should be imported directly by callers -
go through `app.research.service.get_research_provider()` (selected by
`Settings.research_provider`) instead, so the active provider stays
swappable without touching call sites.
"""

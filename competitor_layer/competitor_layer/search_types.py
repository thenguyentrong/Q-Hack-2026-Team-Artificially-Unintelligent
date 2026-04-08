"""Intermediate data types for raw search results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class RawSearchResult:
    """A single result from a search engine."""

    url: str
    title: str
    snippet: str
    query: str
    source_engine: str  # "google", "mock"


@dataclass
class SearchResultSet:
    """Aggregated results from all queries for one ingredient."""

    ingredient_id: str
    queries_used: List[str]
    results: List[RawSearchResult]
    total_results: int
    errors: List[str] = field(default_factory=list)

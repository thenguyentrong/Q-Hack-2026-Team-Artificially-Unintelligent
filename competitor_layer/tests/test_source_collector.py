"""Tests for source collector."""

from __future__ import annotations

from typing import List, Optional

from competitor_layer.config import CompetitorConfig
from competitor_layer.schemas import IngredientRef, SearchContext
from competitor_layer.search_adapter import MockSearchAdapter, SearchAdapter
from competitor_layer.search_types import RawSearchResult
from competitor_layer.source_collector import collect_sources


def _config() -> CompetitorConfig:
    return CompetitorConfig(
        gemini_api_key=None,
        gemini_model="gemini-2.5-pro",
        max_candidates=10,
        ranking_enabled=True,
        google_api_key=None,
        google_cse_id=None,
        search_engine="mock",
        search_results_per_query=10,
        search_delay=0.0,  # no delay in tests
    )


def _ascorbic_acid() -> IngredientRef:
    return IngredientRef(
        ingredient_id="ING-ASCORBIC-ACID",
        canonical_name="Ascorbic Acid",
        aliases=["Vitamin C", "L-Ascorbic Acid"],
    )


class TestCollectSources:
    def test_end_to_end_with_mock(self):
        result = collect_sources(
            _ascorbic_acid(), None, _config(), adapter=MockSearchAdapter()
        )
        assert result.ingredient_id == "ING-ASCORBIC-ACID"
        assert len(result.queries_used) > 0
        assert len(result.results) > 0
        assert result.total_results > 0
        assert len(result.errors) == 0

    def test_results_are_deduplicated(self):
        result = collect_sources(
            _ascorbic_acid(), None, _config(), adapter=MockSearchAdapter()
        )
        urls = [r.url for r in result.results]
        assert len(urls) == len(set(urls))

    def test_queries_match_planner_output(self):
        from competitor_layer.query_planner import plan_queries

        expected_queries = plan_queries(_ascorbic_acid())
        result = collect_sources(
            _ascorbic_acid(), None, _config(), adapter=MockSearchAdapter()
        )
        assert result.queries_used == expected_queries

    def test_region_passed_through(self):
        ctx = SearchContext(region="EU")
        result = collect_sources(
            _ascorbic_acid(), ctx, _config(), adapter=MockSearchAdapter()
        )
        assert any("EU" in q for q in result.queries_used)


class FailingAdapter(SearchAdapter):
    def search(
        self,
        query: str,
        max_results: int = 10,
        region: Optional[str] = None,
    ) -> List[RawSearchResult]:
        raise ConnectionError("Network unavailable")


class TestErrorResilience:
    def test_failing_adapter_captures_errors(self):
        result = collect_sources(
            _ascorbic_acid(), None, _config(), adapter=FailingAdapter()
        )
        assert len(result.results) == 0
        assert len(result.errors) > 0
        assert all("Network unavailable" in e for e in result.errors)

    def test_failing_adapter_still_returns_valid_set(self):
        result = collect_sources(
            _ascorbic_acid(), None, _config(), adapter=FailingAdapter()
        )
        assert result.ingredient_id == "ING-ASCORBIC-ACID"
        assert result.total_results == 0

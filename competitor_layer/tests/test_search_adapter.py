"""Tests for search adapters."""

from __future__ import annotations

import pytest

from competitor_layer.config import CompetitorConfig
from competitor_layer.search_adapter import (
    DuckDuckGoAdapter,
    GoogleSearchAdapter,
    MockSearchAdapter,
    create_search_adapter,
)


def _mock_config(**overrides) -> CompetitorConfig:
    defaults = dict(
        gemini_api_key=None,
        gemini_model="gemini-2.5-pro",
        max_candidates=10,
        ranking_enabled=True,
        google_api_key=None,
        google_cse_id=None,
        search_engine="mock",
        search_results_per_query=10,
        search_delay=0.0,
    )
    defaults.update(overrides)
    return CompetitorConfig(**defaults)


class TestMockSearchAdapter:
    def test_returns_results(self):
        adapter = MockSearchAdapter()
        results = adapter.search("ascorbic acid supplier")
        assert len(results) > 0

    def test_result_fields_populated(self):
        adapter = MockSearchAdapter()
        results = adapter.search("test query")
        for r in results:
            assert r.url.startswith("http")
            assert len(r.title) > 0
            assert len(r.snippet) > 0
            assert r.query == "test query"
            assert r.source_engine == "mock"

    def test_max_results_respected(self):
        adapter = MockSearchAdapter()
        results = adapter.search("test", max_results=1)
        assert len(results) == 1


class TestCreateSearchAdapter:
    def test_mock_engine(self):
        config = _mock_config(search_engine="mock")
        adapter = create_search_adapter(config)
        assert isinstance(adapter, MockSearchAdapter)

    def test_auto_without_keys_falls_back_to_duckduckgo_or_mock(self):
        config = _mock_config(search_engine="auto")
        adapter = create_search_adapter(config)
        assert isinstance(adapter, (DuckDuckGoAdapter, MockSearchAdapter))

    def test_auto_with_keys_creates_google(self):
        config = _mock_config(
            search_engine="auto",
            google_api_key="test-key",
            google_cse_id="test-cse",
        )
        adapter = create_search_adapter(config)
        assert isinstance(adapter, GoogleSearchAdapter)

    def test_google_without_keys_raises(self):
        config = _mock_config(search_engine="google")
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            create_search_adapter(config)

    def test_unknown_engine_raises(self):
        config = _mock_config(search_engine="bing")
        with pytest.raises(ValueError, match="Unknown"):
            create_search_adapter(config)


@pytest.mark.integration
class TestGoogleSearchAdapterLive:
    """Live integration tests — require GOOGLE_API_KEY and GOOGLE_CSE_ID."""

    def test_live_search(self):
        import os

        api_key = os.environ.get("GOOGLE_API_KEY")
        cse_id = os.environ.get("GOOGLE_CSE_ID")
        if not api_key or not cse_id:
            pytest.skip("GOOGLE_API_KEY and GOOGLE_CSE_ID not set")

        adapter = GoogleSearchAdapter(api_key, cse_id)
        results = adapter.search("ascorbic acid food grade supplier", max_results=5)
        assert len(results) > 0
        for r in results:
            assert r.url.startswith("http")
            assert r.source_engine == "google"

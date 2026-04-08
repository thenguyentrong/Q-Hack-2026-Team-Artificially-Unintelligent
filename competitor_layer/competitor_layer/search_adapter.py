"""Pluggable search adapters for supplier discovery."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx

from competitor_layer.config import CompetitorConfig
from competitor_layer.search_types import RawSearchResult

GOOGLE_CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


class SearchAdapter(ABC):
    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 10,
        region: Optional[str] = None,
    ) -> List[RawSearchResult]:
        ...


class GoogleSearchAdapter(SearchAdapter):
    """Google Custom Search JSON API adapter."""

    def __init__(self, api_key: str, cse_id: str) -> None:
        self.api_key = api_key
        self.cse_id = cse_id

    def search(
        self,
        query: str,
        max_results: int = 10,
        region: Optional[str] = None,
    ) -> List[RawSearchResult]:
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": min(max_results, 10),  # API max is 10 per request
        }
        if region:
            # Google CSE uses gl parameter for geolocation
            params["gl"] = _normalize_region(region)

        resp = httpx.get(GOOGLE_CSE_ENDPOINT, params=params, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()

        results: List[RawSearchResult] = []
        for item in data.get("items", []):
            results.append(
                RawSearchResult(
                    url=item.get("link", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    query=query,
                    source_engine="google",
                )
            )
        return results


class DuckDuckGoAdapter(SearchAdapter):
    """DuckDuckGo search adapter. No API key needed."""

    def search(
        self,
        query: str,
        max_results: int = 10,
        region: Optional[str] = None,
    ) -> List[RawSearchResult]:
        from ddgs import DDGS

        ddg_region = _normalize_ddg_region(region) if region else None
        kwargs = {"max_results": max_results}
        if ddg_region:
            kwargs["region"] = ddg_region

        results: List[RawSearchResult] = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, **kwargs):
                results.append(
                    RawSearchResult(
                        url=item.get("href", ""),
                        title=item.get("title", ""),
                        snippet=item.get("body", ""),
                        query=query,
                        source_engine="duckduckgo",
                    )
                )
        return results


class MockSearchAdapter(SearchAdapter):
    """Returns hardcoded results for testing and offline use."""

    def search(
        self,
        query: str,
        max_results: int = 10,
        region: Optional[str] = None,
    ) -> List[RawSearchResult]:
        mock_results = [
            RawSearchResult(
                url="https://www.dsm-firmenich.com/ingredients/ascorbic-acid",
                title="Ascorbic Acid - DSM-Firmenich",
                snippet="DSM-Firmenich offers high-quality ascorbic acid for food and beverage applications.",
                query=query,
                source_engine="mock",
            ),
            RawSearchResult(
                url="https://www.cspc.com.hk/product/vitamin-c",
                title="Vitamin C - CSPC Pharmaceutical",
                snippet="CSPC is one of the world's largest vitamin C manufacturers.",
                query=query,
                source_engine="mock",
            ),
            RawSearchResult(
                url="https://www.prinovaglobal.com/ingredients/vitamins",
                title="Vitamins - Prinova Global",
                snippet="Prinova distributes ascorbic acid and other vitamin ingredients.",
                query=query,
                source_engine="mock",
            ),
        ]
        return mock_results[:max_results]


def create_search_adapter(config: CompetitorConfig) -> SearchAdapter:
    """Create the appropriate search adapter based on config."""
    engine = config.search_engine

    if engine == "mock":
        return MockSearchAdapter()

    if engine == "duckduckgo":
        return DuckDuckGoAdapter()

    if engine in ("google", "auto"):
        if config.google_api_key and config.google_cse_id:
            return GoogleSearchAdapter(config.google_api_key, config.google_cse_id)
        if engine == "google":
            raise ValueError(
                "Google search requested but GOOGLE_API_KEY or GOOGLE_CSE_ID not set"
            )
        # auto mode: try duckduckgo, then mock
        try:
            from ddgs import DDGS
            return DuckDuckGoAdapter()
        except ImportError:
            return MockSearchAdapter()

    raise ValueError(f"Unknown search engine: {engine}")


def _normalize_region(region: str) -> str:
    """Normalize region string to Google gl parameter format."""
    mapping = {
        "EU": "de",
        "US": "us",
        "UK": "gb",
        "DE": "de",
        "FR": "fr",
        "NL": "nl",
        "CN": "cn",
        "JP": "jp",
    }
    return mapping.get(region.upper(), region.lower())


def _normalize_ddg_region(region: str) -> str:
    """Normalize region string to DuckDuckGo region format."""
    mapping = {
        "EU": "de-de",
        "US": "us-en",
        "UK": "uk-en",
        "DE": "de-de",
        "FR": "fr-fr",
        "NL": "nl-nl",
        "CN": "cn-zh",
        "JP": "jp-jp",
    }
    return mapping.get(region.upper(), "wt-wt")

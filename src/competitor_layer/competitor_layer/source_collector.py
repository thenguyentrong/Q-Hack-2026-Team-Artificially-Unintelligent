"""Orchestrates query planning and search execution."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, List, Optional

logger = logging.getLogger(__name__)

from competitor_layer.config import CompetitorConfig
from competitor_layer.query_planner import plan_queries, plan_queries_with_gemini
from competitor_layer.schemas import IngredientRef, SearchContext
from competitor_layer.search_adapter import SearchAdapter, create_search_adapter
from competitor_layer.search_types import RawSearchResult, SearchResultSet

if TYPE_CHECKING:
    from competitor_layer.gemini_client import GeminiClient


def collect_sources(
    ingredient: IngredientRef,
    context: Optional[SearchContext],
    config: CompetitorConfig,
    adapter: Optional[SearchAdapter] = None,
    gemini_client: Optional[GeminiClient] = None,
) -> SearchResultSet:
    """Run queries and collect raw search results.

    Returns a SearchResultSet with deduplicated results and any errors.
    """
    if adapter is None:
        adapter = create_search_adapter(config)

    if gemini_client is not None:
        queries = plan_queries_with_gemini(ingredient, context, gemini_client)
    else:
        queries = plan_queries(ingredient, context)
    all_results: List[RawSearchResult] = []
    errors: List[str] = []
    total_before_dedup = 0

    logger.info("Executing %d queries via %s", len(queries), type(adapter).__name__)
    print(f"    L2 search: {len(queries)} queries via {type(adapter).__name__}", flush=True)
    for i, query in enumerate(queries):
        print(f"      [{i+1}/{len(queries)}] {query[:65]}...", flush=True)
        try:
            results = adapter.search(
                query,
                max_results=config.search_results_per_query,
                region=context.region if context else None,
            )
            all_results.extend(results)
            total_before_dedup += len(results)
            logger.debug("Query %d/%d: '%s' -> %d results", i + 1, len(queries), query, len(results))
        except Exception as e:
            errors.append(f"Query '{query}' failed: {e}")
            logger.warning("Query %d/%d failed: '%s' -> %s", i + 1, len(queries), query, e)

        # Rate limiting delay (skip after last query)
        if i < len(queries) - 1 and config.search_delay > 0:
            time.sleep(config.search_delay)

    # Deduplicate by URL (keep first occurrence)
    deduped = _deduplicate_by_url(all_results)
    logger.info("Collected %d raw results, %d after dedup, %d errors", total_before_dedup, len(deduped), len(errors))

    return SearchResultSet(
        ingredient_id=ingredient.ingredient_id,
        queries_used=queries,
        results=deduped,
        total_results=total_before_dedup,
        errors=errors,
    )


def _deduplicate_by_url(results: List[RawSearchResult]) -> List[RawSearchResult]:
    seen: set = set()
    deduped: List[RawSearchResult] = []
    for r in results:
        if r.url not in seen:
            seen.add(r.url)
            deduped.append(r)
    return deduped

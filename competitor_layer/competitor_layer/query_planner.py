"""Query generation from ingredient context, with optional Gemini enhancement."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

from competitor_layer.schemas import IngredientRef, SearchContext

if TYPE_CHECKING:
    from competitor_layer.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


def plan_queries(
    ingredient: IngredientRef,
    context: Optional[SearchContext] = None,
    max_queries: int = 15,
) -> List[str]:
    """Generate search queries from ingredient, aliases, category, and context.

    Query families (per spec section 7.1.B):
      - ingredient + supplier
      - ingredient + manufacturer
      - ingredient + distributor
      - ingredient + product page
      - ingredient + PDF / spec terms
      - ingredient + use-context term (e.g. food grade)
    """
    queries: List[str] = []
    seen: set = set()

    name = ingredient.canonical_name
    grade = (
        context.grade_hint
        if context and context.grade_hint
        else "food grade"
    )

    # Full query families for canonical name
    _add(queries, seen, f"{name} supplier")
    _add(queries, seen, f"{name} manufacturer")
    _add(queries, seen, f"{name} distributor")
    _add(queries, seen, f"{name} {grade} supplier")
    _add(queries, seen, f"{name} technical data sheet")
    _add(queries, seen, f"{name} product page")

    # Alias queries (2 families each, up to 2 aliases)
    for alias in ingredient.aliases[:2]:
        _add(queries, seen, f"{alias} supplier")
        _add(queries, seen, f"{alias} technical data sheet")

    # Region-qualified queries
    if context and context.region:
        _add(queries, seen, f"{name} supplier {context.region}")
        _add(queries, seen, f"{name} manufacturer {context.region}")

    # Product category query
    if context and context.product_category:
        _add(queries, seen, f"{name} {context.product_category} grade supplier")

    return queries[:max_queries]


def plan_queries_with_gemini(
    ingredient: IngredientRef,
    context: Optional[SearchContext],
    gemini_client: Optional[GeminiClient],
    max_queries: int = 20,
) -> List[str]:
    """Generate queries with Gemini synonym expansion merged into deterministic queries."""
    # Start with deterministic queries
    queries = plan_queries(ingredient, context, max_queries)
    seen = {q.lower() for q in queries}

    if gemini_client is None:
        return queries

    try:
        from competitor_layer.gemini_client import SynonymExpansion
        from competitor_layer.prompts import SYNONYM_EXPANSION_PROMPT

        aliases_str = ", ".join(ingredient.aliases) if ingredient.aliases else "none"
        prompt = SYNONYM_EXPANSION_PROMPT.format(
            canonical_name=ingredient.canonical_name,
            aliases=aliases_str,
            category=ingredient.category,
        )
        result = gemini_client.generate(prompt, SynonymExpansion)
        if result is None:
            return queries

        # Merge Gemini-suggested queries
        for q in result.industry_queries:
            _add(queries, seen, q)

        # Generate supplier queries from additional synonym names
        for name in result.additional_names[:3]:
            _add(queries, seen, f"{name} supplier")

    except Exception as e:
        logger.warning("Gemini query expansion failed: %s", e)

    return queries[:max_queries]


def _add(queries: List[str], seen: set, query: str) -> None:
    key = query.lower()
    if key not in seen:
        seen.add(key)
        queries.append(query)

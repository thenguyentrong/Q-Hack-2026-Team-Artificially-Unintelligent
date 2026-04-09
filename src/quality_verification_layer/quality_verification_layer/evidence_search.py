"""Active evidence search — find TDS, COA, product specs for a supplier."""

from __future__ import annotations

import logging
import time
from typing import List

logger = logging.getLogger(__name__)

# Search query templates for finding supplier technical documents
_QUERY_TEMPLATES = [
    "{supplier} {ingredient} technical data sheet",
    "{supplier} {ingredient} certificate of analysis",
    "{supplier} {ingredient} TDS COA PDF",
    "{supplier} {ingredient} product specification",
    "{supplier} {ingredient} specification sheet",
]


def search_supplier_evidence(
    supplier_name: str,
    ingredient_name: str,
    aliases: List[str] = None,
    max_results_per_query: int = 5,
    search_delay: float = 1.0,
) -> List[str]:
    """Search for TDS, COA, and product spec URLs for a supplier+ingredient pair.

    Uses DuckDuckGo search. Returns a deduplicated list of URLs.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        logger.warning("ddgs not installed — skipping evidence search")
        return []

    # Build queries using canonical name + aliases
    names = [ingredient_name]
    if aliases:
        names.extend(aliases[:2])

    queries: List[str] = []
    for template in _QUERY_TEMPLATES:
        queries.append(template.format(supplier=supplier_name, ingredient=ingredient_name))

    # Add one alias-based query
    for alias in (aliases or [])[:1]:
        queries.append(f"{supplier_name} {alias} TDS specification PDF")

    seen_urls: set = set()
    all_urls: List[str] = []

    logger.info(
        "Searching for evidence: %s + %s (%d queries)",
        supplier_name, ingredient_name, len(queries),
    )

    with DDGS() as ddgs:
        for i, query in enumerate(queries):
            print(
                f"       Searching [{i+1}/{len(queries)}]: {query[:60]}...",
                flush=True,
            )
            try:
                results = list(ddgs.text(query, max_results=max_results_per_query))
                for r in results:
                    url = r.get("href", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_urls.append(url)
            except Exception as e:
                logger.debug("Search query failed: '%s' -> %s", query, e)

            if i < len(queries) - 1 and search_delay > 0:
                time.sleep(search_delay)

    logger.info("Found %d unique URLs for %s", len(all_urls), supplier_name)
    return all_urls

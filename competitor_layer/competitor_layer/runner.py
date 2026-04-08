"""Core runner for the Agnes Competitor Layer."""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import List

from competitor_layer.candidate_extractor import extract_candidates
from competitor_layer.candidate_filter import filter_and_rank
from competitor_layer.config import CompetitorConfig, load_config
from competitor_layer.gemini_client import create_gemini_client
from competitor_layer.models import InternalCandidate
from competitor_layer.query_planner import plan_queries_with_gemini
from competitor_layer.schemas import (
    CompetitorInput,
    CompetitorOutput,
    OutputStats,
    SearchSummary,
)
from competitor_layer.search_types import SearchResultSet
from competitor_layer.source_collector import collect_sources

logger = logging.getLogger(__name__)


def run_competitor_layer(
    input_data: CompetitorInput, config: CompetitorConfig
) -> CompetitorOutput:
    """Run the competitor layer pipeline."""
    trace_id = input_data.trace_id or str(uuid.uuid4())[:8]
    logger.info("[%s] Starting competitor layer for %s", trace_id, input_data.ingredient.ingredient_id)
    t0 = time.monotonic()

    if config.search_engine == "mock":
        output = _mock_run(input_data, config)
    else:
        output = _search_run(input_data, config)

    output.trace_id = trace_id
    elapsed = time.monotonic() - t0
    logger.info("[%s] Completed in %.1fs — %d candidates returned", trace_id, elapsed, len(output.candidates))
    return output


def run_from_json(json_str: str, config: CompetitorConfig = None) -> str:
    """Convenience: accepts raw JSON string, returns raw JSON string."""
    input_data = CompetitorInput.model_validate(json.loads(json_str))
    if config is None:
        config = load_config()
    output = run_competitor_layer(input_data, config)
    return output.model_dump_json(indent=2)


def run_from_file(path: str, config: CompetitorConfig = None) -> CompetitorOutput:
    """Convenience: reads JSON file, returns CompetitorOutput."""
    raw = Path(path).read_text()
    input_data = CompetitorInput.model_validate(json.loads(raw))
    if config is None:
        config = load_config()
    return run_competitor_layer(input_data, config)


def _search_run(
    input_data: CompetitorInput, config: CompetitorConfig
) -> CompetitorOutput:
    """Run the real search-based pipeline."""
    ingredient = input_data.ingredient
    context = input_data.context
    region = context.region if context and context.region else None

    # Resolve runtime overrides
    max_candidates = (
        input_data.runtime.max_candidates
        if input_data.runtime
        else config.max_candidates
    )
    ranking_enabled = (
        input_data.runtime.ranking_enabled
        if input_data.runtime
        else config.ranking_enabled
    )

    # Initialize Gemini client (optional — None if no API key)
    gemini = create_gemini_client(config.gemini_api_key, config.gemini_model)

    # Collect raw search results (with Gemini-enhanced queries if available)
    result_set = collect_sources(ingredient, context, config, gemini_client=gemini)

    # Extract and normalize supplier candidates
    candidates = extract_candidates(
        result_set, ingredient.canonical_name, ingredient.aliases,
        gemini_client=gemini,
    )

    # Filter, score, and rank
    filter_result = filter_and_rank(
        candidates, ingredient, context, max_candidates, ranking_enabled,
        gemini_client=gemini,
    )
    candidates = filter_result.candidates

    output_candidates = [
        c.to_candidate(
            rank=(i + 1) if ranking_enabled else None,
            supplier_id=f"SUP-{i + 1:03d}",
        )
        for i, c in enumerate(candidates)
    ]

    # Warnings
    warnings: List[str] = []
    if not region:
        warnings.append("No region supplied; search remained global")
    if not ranking_enabled:
        warnings.append("Ranking disabled; output is unranked")
    if result_set.errors:
        warnings.append(f"Search errors: {'; '.join(result_set.errors)}")
    warnings.extend(filter_result.warnings)

    return CompetitorOutput(
        ingredient_id=ingredient.ingredient_id,
        search_summary=SearchSummary(
            queries_used=result_set.queries_used,
            region_applied=region,
            ranking_enabled=ranking_enabled,
            gemini_enabled=gemini is not None,
        ),
        candidates=output_candidates,
        warnings=warnings,
        stats=OutputStats(
            raw_results_seen=result_set.total_results,
            deduped_suppliers=len(candidates),
            returned_candidates=len(output_candidates),
        ),
    )



def _mock_run(
    input_data: CompetitorInput, config: CompetitorConfig
) -> CompetitorOutput:
    """Produce realistic mock output for demo and testing purposes."""

    # Resolve effective settings (input overrides config)
    max_candidates = (
        input_data.runtime.max_candidates
        if input_data.runtime
        else config.max_candidates
    )
    ranking_enabled = (
        input_data.runtime.ranking_enabled
        if input_data.runtime
        else config.ranking_enabled
    )

    region = (
        input_data.context.region
        if input_data.context and input_data.context.region
        else None
    )

    # Build mock candidates
    ingredient = input_data.ingredient
    mock_candidates = _build_mock_candidates(ingredient.canonical_name)

    # Truncate
    mock_candidates = mock_candidates[:max_candidates]

    # Convert to output candidates
    candidates = [
        c.to_candidate(
            rank=(i + 1) if ranking_enabled else None,
            supplier_id=f"SUP-{i + 1:03d}",
        )
        for i, c in enumerate(mock_candidates)
    ]

    # Build warnings
    warnings: List[str] = []
    if not region:
        warnings.append("No region supplied; search remained global")
    if not ranking_enabled:
        warnings.append("Ranking disabled; output is unranked")

    # Build search summary
    queries = _build_mock_queries(ingredient.canonical_name, ingredient.aliases, region)

    return CompetitorOutput(
        ingredient_id=ingredient.ingredient_id,
        search_summary=SearchSummary(
            queries_used=queries,
            region_applied=region,
            ranking_enabled=ranking_enabled,
        ),
        candidates=candidates,
        warnings=warnings,
        stats=OutputStats(
            raw_results_seen=42,
            deduped_suppliers=8,
            returned_candidates=len(candidates),
        ),
    )


def _build_mock_candidates(canonical_name: str) -> List[InternalCandidate]:
    """Return hardcoded mock candidates for demo purposes."""
    return [
        InternalCandidate(
            supplier_name="DSM-Firmenich",
            supplier_type="manufacturer",
            country="NL",
            website="https://www.dsm-firmenich.com",
            offers=[
                {
                    "offer_label": f"{canonical_name} Food Grade",
                    "matched_name": canonical_name,
                    "source_url": "https://www.dsm-firmenich.com/ingredients/ascorbic-acid",
                }
            ],
            website_found=True,
            product_page_found=True,
            pdf_found=True,
            technical_doc_likely=True,
            confidence="high",
            reason="Major manufacturer of ascorbic acid with extensive food-grade documentation",
        ),
        InternalCandidate(
            supplier_name="CSPC Pharma",
            supplier_type="manufacturer",
            country="CN",
            website="https://www.cspc.com.hk",
            offers=[
                {
                    "offer_label": f"{canonical_name} USP/FCC Grade",
                    "matched_name": canonical_name,
                    "source_url": "https://www.cspc.com.hk/product/vitamin-c",
                }
            ],
            website_found=True,
            product_page_found=True,
            pdf_found=True,
            technical_doc_likely=True,
            confidence="high",
            reason="One of the world's largest ascorbic acid producers, food and pharma grade",
        ),
        InternalCandidate(
            supplier_name="Prinova USA",
            supplier_type="distributor",
            country="US",
            website="https://www.prinovaglobal.com",
            offers=[
                {
                    "offer_label": f"{canonical_name}",
                    "matched_name": canonical_name,
                    "source_url": "https://www.prinovaglobal.com/ingredients/vitamins",
                }
            ],
            website_found=True,
            product_page_found=True,
            pdf_found=False,
            technical_doc_likely=False,
            confidence="medium",
            reason="Known distributor in database, ascorbic acid in product catalog",
        ),
        InternalCandidate(
            supplier_name="Northeast Pharma",
            supplier_type="manufacturer",
            country="CN",
            website="https://www.nepharm.com",
            offers=[
                {
                    "offer_label": f"{canonical_name} Food Grade",
                    "matched_name": canonical_name,
                    "source_url": "https://www.nepharm.com/products/vitamin-c",
                }
            ],
            website_found=True,
            product_page_found=True,
            pdf_found=False,
            technical_doc_likely=True,
            confidence="medium",
            reason="Established vitamin C manufacturer, some food-grade evidence found",
        ),
        InternalCandidate(
            supplier_name="PureBulk",
            supplier_type="reseller",
            country="US",
            website="https://www.purebulk.com",
            offers=[
                {
                    "offer_label": f"{canonical_name} Powder",
                    "matched_name": canonical_name,
                    "source_url": "https://www.purebulk.com/products/ascorbic-acid",
                }
            ],
            website_found=True,
            product_page_found=True,
            pdf_found=False,
            technical_doc_likely=False,
            confidence="low",
            reason="Reseller in database, limited technical documentation available",
        ),
    ]


def _build_mock_queries(
    canonical_name: str,
    aliases: List[str],
    region: str | None,
) -> List[str]:
    """Build realistic-looking search queries."""
    queries = [
        f"{canonical_name} food grade supplier",
        f"{canonical_name} manufacturer",
    ]
    for alias in aliases[:2]:
        queries.append(f"{alias} supplier technical data sheet")
    if region:
        queries.append(f"{canonical_name} supplier {region}")
    return queries

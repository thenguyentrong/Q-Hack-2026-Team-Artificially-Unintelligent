"""Integration tests using real Google Search and Gemini APIs.

Requires GOOGLE_API_KEY, GOOGLE_CSE_ID, and GEMINI_API_KEY in .env.
Run with: pytest tests/test_integration.py -v -m integration
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Load .env before imports that depend on config
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from competitor_layer.config import load_config
from competitor_layer.gemini_client import (
    GeminiClient,
    SupplierClassification,
    SupplierReasoning,
    SynonymExpansion,
    create_gemini_client,
)
from competitor_layer.query_planner import plan_queries_with_gemini
from competitor_layer.runner import run_competitor_layer
from competitor_layer.schemas import (
    CompetitorInput,
    CompetitorOutput,
    IngredientRef,
    RuntimeConfig,
    SearchContext,
)
from competitor_layer.search_adapter import DuckDuckGoAdapter

# Skip all tests if keys are missing
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

skip_no_gemini = pytest.mark.skipif(
    not GEMINI_API_KEY,
    reason="GEMINI_API_KEY not set",
)


# === DuckDuckGo Search ===


@pytest.mark.integration
class TestDuckDuckGoSearchLive:
    @pytest.mark.xfail(reason="DDG TLS 1.3 may fail on Python 3.9 + LibreSSL")
    def test_search_returns_results(self):
        adapter = DuckDuckGoAdapter()
        results = adapter.search("ascorbic acid food grade supplier", max_results=5)
        assert len(results) > 0
        for r in results:
            assert r.url.startswith("http")
            assert len(r.title) > 0
            assert r.source_engine == "duckduckgo"

    @pytest.mark.xfail(reason="DDG TLS 1.3 may fail on Python 3.9 + LibreSSL")
    def test_search_with_region(self):
        adapter = DuckDuckGoAdapter()
        results = adapter.search("ascorbic acid manufacturer", max_results=5, region="EU")
        assert len(results) > 0


# === Gemini API ===


@pytest.mark.integration
@skip_no_gemini
class TestGeminiLive:
    def test_synonym_expansion(self):
        client = create_gemini_client(GEMINI_API_KEY)
        assert client is not None
        result = client.generate(
            'List synonym names and search queries for the food ingredient "Ascorbic Acid" (also known as: Vitamin C, L-Ascorbic Acid).',
            SynonymExpansion,
        )
        assert result is not None
        assert len(result.additional_names) > 0
        assert len(result.industry_queries) > 0
        print(f"\n  Synonyms: {result.additional_names}")
        print(f"  Queries: {result.industry_queries}")

    def test_supplier_classification(self):
        client = create_gemini_client(GEMINI_API_KEY)
        result = client.generate(
            'Based on these search results from dsm-firmenich.com:\n'
            '- Title: "Ascorbic Acid - DSM-Firmenich"\n'
            '  Snippet: "DSM-Firmenich is a leading manufacturer of ascorbic acid for food applications."\n'
            'Classify this company as: manufacturer, distributor, reseller, or unknown.',
            SupplierClassification,
        )
        assert result is not None
        assert result.supplier_type in ("manufacturer", "distributor", "reseller", "unknown")
        print(f"\n  Type: {result.supplier_type} ({result.confidence})")
        print(f"  Explanation: {result.explanation}")

    def test_supplier_reasoning(self):
        client = create_gemini_client(GEMINI_API_KEY)
        result = client.generate(
            'Write a 1-2 sentence sourcing assessment for this supplier:\n'
            'Supplier: DSM-Firmenich, Type: manufacturer, Country: NL\n'
            'Evidence: product page found, technical docs likely\n'
            'Ingredient: Ascorbic Acid',
            SupplierReasoning,
        )
        assert result is not None
        assert len(result.reason) > 10
        print(f"\n  Reason: {result.reason}")

    def test_gemini_enhanced_query_expansion(self):
        client = create_gemini_client(GEMINI_API_KEY)
        ingredient = IngredientRef(
            ingredient_id="ING-ASCORBIC-ACID",
            canonical_name="Ascorbic Acid",
            aliases=["Vitamin C", "L-Ascorbic Acid"],
        )
        queries = plan_queries_with_gemini(ingredient, None, client)
        # Should have more queries than deterministic alone
        from competitor_layer.query_planner import plan_queries
        base_queries = plan_queries(ingredient, None)
        assert len(queries) >= len(base_queries)
        print(f"\n  Base queries: {len(base_queries)}")
        print(f"  With Gemini: {len(queries)}")
        new_queries = set(queries) - set(base_queries)
        if new_queries:
            print(f"  Gemini added: {new_queries}")


# === Full End-to-End Pipeline ===


@pytest.mark.integration
@skip_no_gemini
class TestFullPipelineLive:
    def test_end_to_end_ascorbic_acid(self):
        """Full pipeline: DuckDuckGo Search + Gemini reasoning for Ascorbic Acid."""
        input_data = CompetitorInput(
            ingredient=IngredientRef(
                ingredient_id="ING-ASCORBIC-ACID",
                canonical_name="Ascorbic Acid",
                aliases=["Vitamin C"],
                category="food ingredient",
            ),
            context=SearchContext(region="EU"),
            runtime=RuntimeConfig(max_candidates=3, ranking_enabled=True),
        )

        from dataclasses import asdict
        from competitor_layer.config import CompetitorConfig
        config = CompetitorConfig(
            gemini_api_key=GEMINI_API_KEY,
            gemini_model="gemini-2.5-flash",
            max_candidates=3,
            ranking_enabled=True,
            google_api_key=None,
            google_cse_id=None,
            search_engine="duckduckgo",
            search_results_per_query=5,
            search_delay=2.0,
        )
        output = run_competitor_layer(input_data, config)

        # Validate output structure
        assert isinstance(output, CompetitorOutput)
        assert output.ingredient_id == "ING-ASCORBIC-ACID"
        assert output.schema_version == "1.0"

        # Should have found some candidates
        assert len(output.candidates) > 0, "No candidates found"
        print(f"\n  Candidates found: {len(output.candidates)}")
        print(f"  Queries used: {len(output.search_summary.queries_used)}")
        print(f"  Raw results seen: {output.stats.raw_results_seen}")

        for c in output.candidates:
            print(f"\n  #{c.rank} {c.supplier.supplier_name}")
            print(f"     Type: {c.supplier.supplier_type}, Country: {c.supplier.country}")
            print(f"     Confidence: {c.candidate_confidence}")
            print(f"     Reason: {c.reason}")
            print(f"     Evidence: web={c.evidence_hints.website_found} "
                  f"product={c.evidence_hints.product_page_found} "
                  f"pdf={c.evidence_hints.pdf_found} "
                  f"tds={c.evidence_hints.technical_doc_likely}")
            for o in c.matched_offers:
                print(f"     Offer: {o.offer_label}")
                print(f"       URL: {o.source_url}")

        # Output should be valid JSON
        json_out = output.model_dump_json(indent=2)
        reparsed = CompetitorOutput.model_validate_json(json_out)
        assert reparsed == output

        # Print warnings if any
        if output.warnings:
            print(f"\n  Warnings: {output.warnings}")

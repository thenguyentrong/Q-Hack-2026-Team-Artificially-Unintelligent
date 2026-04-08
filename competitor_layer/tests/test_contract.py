"""Contract compatibility, backward compatibility, and warning propagation tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from competitor_layer.config import CompetitorConfig
from competitor_layer.runner import run_competitor_layer, run_from_json
from competitor_layer.schemas import (
    CompetitorInput,
    CompetitorOutput,
    IngredientRef,
    SearchContext,
)
from competitor_layer.search_adapter import SearchAdapter
from competitor_layer.search_types import RawSearchResult
from competitor_layer.source_collector import collect_sources

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _mock_config() -> CompetitorConfig:
    return CompetitorConfig(
        gemini_api_key=None,
        gemini_model="gemini-2.5-flash",
        max_candidates=10,
        ranking_enabled=True,
        google_api_key=None,
        google_cse_id=None,
        search_engine="mock",
        search_results_per_query=10,
        search_delay=0.0,
    )


# === Spec-required: Contract compatibility with mock Quality Layer consumer ===


class TestContractCompatibility:
    def test_layer3_can_consume_output(self):
        """Parse output and access all fields a Quality Layer would need."""
        raw = (EXAMPLES_DIR / "output_mock.json").read_text()
        output = CompetitorOutput.model_validate(json.loads(raw))

        assert output.schema_version == "1.0"
        assert output.ingredient_id
        assert output.trace_id  # Phase 6 addition

        for candidate in output.candidates:
            # Layer 3 needs these to fetch and verify
            assert candidate.supplier.supplier_id
            assert candidate.supplier.supplier_name
            assert candidate.supplier.supplier_type in (
                "manufacturer", "distributor", "reseller", "unknown"
            )
            assert candidate.candidate_confidence in ("high", "medium", "low")
            assert candidate.reason

            # Source URLs for document retrieval
            for offer in candidate.matched_offers:
                assert offer.offer_label
                assert offer.matched_name
                # source_url may be None but field must exist

            # Evidence hints for prioritization
            hints = candidate.evidence_hints
            assert isinstance(hints.website_found, bool)
            assert isinstance(hints.product_page_found, bool)
            assert isinstance(hints.pdf_found, bool)
            assert isinstance(hints.technical_doc_likely, bool)

    def test_output_has_stats(self):
        raw = (EXAMPLES_DIR / "output_mock.json").read_text()
        output = CompetitorOutput.model_validate(json.loads(raw))
        assert output.stats.raw_results_seen >= 0
        assert output.stats.deduped_suppliers >= 0
        assert output.stats.returned_candidates == len(output.candidates)


# === Spec-required: Backward compatibility ===


class TestBackwardCompatibility:
    def test_golden_snapshot_still_valid(self):
        """output_mock.json from Phase 1 must still parse as CompetitorOutput."""
        raw = (EXAMPLES_DIR / "output_mock.json").read_text()
        output = CompetitorOutput.model_validate(json.loads(raw))
        assert output.schema_version == "1.0"
        assert len(output.candidates) > 0

    def test_input_without_trace_id_still_works(self):
        """Inputs without trace_id (pre-Phase 6) must still be accepted."""
        input_data = CompetitorInput(
            ingredient=IngredientRef(
                ingredient_id="ING-TEST",
                canonical_name="Test",
            ),
        )
        assert input_data.trace_id is None
        result = run_competitor_layer(input_data, _mock_config())
        # trace_id should be auto-generated
        assert result.trace_id

    def test_run_from_json_convenience(self):
        """run_from_json accepts raw JSON and returns raw JSON."""
        inp = (EXAMPLES_DIR / "input_ascorbic_acid.json").read_text()
        out_json = run_from_json(inp, _mock_config())
        output = CompetitorOutput.model_validate_json(out_json)
        assert output.ingredient_id == "ING-ASCORBIC-ACID"
        assert output.trace_id


# === Spec-required: Warning propagation ===


class PartiallyFailingAdapter(SearchAdapter):
    """Returns results for some queries, fails for others."""

    def search(
        self,
        query: str,
        max_results: int = 10,
        region: Optional[str] = None,
    ) -> List[RawSearchResult]:
        if "technical data sheet" in query:
            raise ConnectionError("Simulated search failure")
        return [
            RawSearchResult(
                url="https://supplier.com/ascorbic-acid",
                title="Ascorbic Acid - Supplier",
                snippet="Leading manufacturer of ascorbic acid.",
                query=query,
                source_engine="mock",
            )
        ]


class TestWarningPropagation:
    def test_search_errors_propagate_to_output(self):
        """Warnings from search errors must appear in final output."""
        ingredient = IngredientRef(
            ingredient_id="ING-ASCORBIC-ACID",
            canonical_name="Ascorbic Acid",
            aliases=["Vitamin C"],
        )
        result_set = collect_sources(
            ingredient, None, _mock_config(),
            adapter=PartiallyFailingAdapter(),
        )
        assert len(result_set.errors) > 0
        assert any("Simulated search failure" in e for e in result_set.errors)

    def test_no_region_warning_in_output(self):
        """Missing region produces a warning in output."""
        inp = CompetitorInput(
            ingredient=IngredientRef(
                ingredient_id="ING-TEST",
                canonical_name="Ascorbic Acid",
            ),
        )
        result = run_competitor_layer(inp, _mock_config())
        assert "No region supplied; search remained global" in result.warnings

    def test_trace_id_in_output(self):
        """Output always has a trace_id."""
        inp = CompetitorInput(
            trace_id="test-trace-123",
            ingredient=IngredientRef(
                ingredient_id="ING-TEST",
                canonical_name="Test",
            ),
        )
        result = run_competitor_layer(inp, _mock_config())
        assert result.trace_id == "test-trace-123"

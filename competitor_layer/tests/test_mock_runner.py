"""Tests for the Competitor Layer mock runner."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from competitor_layer.config import CompetitorConfig
from competitor_layer.runner import run_competitor_layer
from competitor_layer.schemas import (
    CompetitorInput,
    CompetitorOutput,
    IngredientRef,
    RuntimeConfig,
    SearchContext,
)

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _default_config() -> CompetitorConfig:
    return CompetitorConfig(
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


def _minimal_input(**overrides) -> CompetitorInput:
    return CompetitorInput(
        ingredient=IngredientRef(
            ingredient_id="ING-ASCORBIC-ACID",
            canonical_name="Ascorbic Acid",
            aliases=["Vitamin C", "L-Ascorbic Acid"],
        ),
        **overrides,
    )


class TestMockRunner:
    def test_produces_valid_output(self):
        result = run_competitor_layer(_minimal_input(), _default_config())
        assert isinstance(result, CompetitorOutput)
        assert result.ingredient_id == "ING-ASCORBIC-ACID"
        assert len(result.candidates) > 0
        assert result.stats.returned_candidates == len(result.candidates)

    def test_max_candidates_respected(self):
        inp = _minimal_input(runtime=RuntimeConfig(max_candidates=2))
        result = run_competitor_layer(inp, _default_config())
        assert len(result.candidates) <= 2

    def test_ranking_disabled_adds_warning(self):
        inp = _minimal_input(
            runtime=RuntimeConfig(ranking_enabled=False)
        )
        result = run_competitor_layer(inp, _default_config())
        assert "Ranking disabled; output is unranked" in result.warnings
        assert all(c.rank is None for c in result.candidates)

    def test_missing_region_adds_warning(self):
        result = run_competitor_layer(_minimal_input(), _default_config())
        assert "No region supplied; search remained global" in result.warnings

    def test_region_present_no_warning(self):
        inp = _minimal_input(context=SearchContext(region="EU"))
        result = run_competitor_layer(inp, _default_config())
        assert "No region supplied; search remained global" not in result.warnings
        assert result.search_summary.region_applied == "EU"

    def test_candidates_have_required_fields(self):
        result = run_competitor_layer(_minimal_input(), _default_config())
        for c in result.candidates:
            assert c.supplier.supplier_id
            assert c.supplier.supplier_name
            assert c.reason
            assert c.candidate_confidence in ("high", "medium", "low")


class TestCLI:
    def test_cli_smoke(self):
        input_file = EXAMPLES_DIR / "input_ascorbic_acid.json"
        result = subprocess.run(
            [sys.executable, "-m", "competitor_layer.cli", str(input_file)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        output = CompetitorOutput.model_validate_json(result.stdout)
        assert output.ingredient_id == "ING-ASCORBIC-ACID"

    def test_cli_invalid_file(self):
        result = subprocess.run(
            [sys.executable, "-m", "competitor_layer.cli", "nonexistent.json"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode != 0


class TestGoldenSnapshot:
    def test_output_matches_snapshot(self):
        inp_raw = (EXAMPLES_DIR / "input_ascorbic_acid.json").read_text()
        inp = CompetitorInput.model_validate(json.loads(inp_raw))
        result = run_competitor_layer(inp, _default_config())

        golden_raw = (EXAMPLES_DIR / "output_mock.json").read_text()
        golden = CompetitorOutput.model_validate(json.loads(golden_raw))

        # Compare everything except trace_id (random per run)
        r_dict = result.model_dump()
        g_dict = golden.model_dump()
        r_dict.pop("trace_id", None)
        g_dict.pop("trace_id", None)
        assert r_dict == g_dict

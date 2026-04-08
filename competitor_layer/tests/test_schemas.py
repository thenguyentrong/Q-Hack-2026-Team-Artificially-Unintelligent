"""Tests for Competitor Layer I/O schemas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from competitor_layer.schemas import (
    Candidate,
    CandidateConfidence,
    CompetitorInput,
    CompetitorOutput,
    EvidenceHints,
    IngredientRef,
    MatchedOffer,
    SupplierInfo,
    SupplierType,
)

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


class TestInputSchema:
    def test_full_input_parses(self):
        raw = (EXAMPLES_DIR / "input_ascorbic_acid.json").read_text()
        inp = CompetitorInput.model_validate(json.loads(raw))
        assert inp.ingredient.ingredient_id == "ING-ASCORBIC-ACID"
        assert inp.ingredient.canonical_name == "Ascorbic Acid"
        assert "Vitamin C" in inp.ingredient.aliases
        assert inp.context is not None
        assert inp.context.region == "EU"

    def test_minimal_input_validates(self):
        inp = CompetitorInput(
            ingredient=IngredientRef(
                ingredient_id="ING-TEST",
                canonical_name="Test Ingredient",
            )
        )
        assert inp.context is None
        assert inp.requirements_context is None
        assert inp.runtime is None
        assert inp.schema_version == "1.0"

    def test_missing_ingredient_raises(self):
        with pytest.raises(ValidationError):
            CompetitorInput.model_validate({"schema_version": "1.0"})


class TestOutputSchema:
    def test_output_parses(self):
        raw = (EXAMPLES_DIR / "output_mock.json").read_text()
        out = CompetitorOutput.model_validate(json.loads(raw))
        assert out.ingredient_id == "ING-ASCORBIC-ACID"
        assert len(out.candidates) > 0

    def test_output_round_trip(self):
        raw = (EXAMPLES_DIR / "output_mock.json").read_text()
        out1 = CompetitorOutput.model_validate(json.loads(raw))
        serialized = out1.model_dump_json()
        out2 = CompetitorOutput.model_validate_json(serialized)
        assert out1 == out2


class TestEnumEnforcement:
    def test_invalid_supplier_type_raises(self):
        with pytest.raises(ValidationError):
            SupplierInfo(
                supplier_id="SUP-X",
                supplier_name="Bad",
                supplier_type="invalid",
            )

    def test_invalid_confidence_raises(self):
        with pytest.raises(ValidationError):
            Candidate(
                supplier=SupplierInfo(
                    supplier_id="SUP-X",
                    supplier_name="Test",
                ),
                matched_offers=[],
                evidence_hints=EvidenceHints(),
                candidate_confidence="very_high",
                reason="test",
            )

    def test_valid_enums_accepted(self):
        for st in SupplierType:
            info = SupplierInfo(
                supplier_id="SUP-X",
                supplier_name="Test",
                supplier_type=st,
            )
            assert info.supplier_type == st.value

        for cc in CandidateConfidence:
            cand = Candidate(
                supplier=SupplierInfo(supplier_id="SUP-X", supplier_name="T"),
                matched_offers=[],
                evidence_hints=EvidenceHints(),
                candidate_confidence=cc,
                reason="ok",
            )
            assert cand.candidate_confidence == cc.value

"""Tests for quality verification I/O schemas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from quality_verification_layer.schemas import (
    CandidateSupplier,
    Confidence,
    CoverageSummary,
    EvidenceItem,
    EvidenceStatus,
    ExtractedAttribute,
    ExtractionMethod,
    QualityVerificationInput,
    QualityVerificationOutput,
    RequirementInput,
    SourceType,
    SupplierAssessment,
    SupplierAssessmentStatus,
    SupplierRef,
    VerificationResultItem,
    VerificationStatus,
)

INPUTS_DIR = Path(__file__).resolve().parent.parent / "inputs"
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


class TestInputSchema:
    def test_sample_input_parses(self):
        raw = (INPUTS_DIR / "sample_input.json").read_text()
        inp = QualityVerificationInput.model_validate(json.loads(raw))
        assert inp.ingredient.ingredient_id == "ING-ASCORBIC-ACID"
        assert len(inp.requirements) == 2
        assert len(inp.candidate_suppliers) == 1

    def test_minimal_input(self):
        inp = QualityVerificationInput(
            ingredient={"ingredient_id": "ING-X", "canonical_name": "X"},
            requirements=[{
                "requirement_id": "R1",
                "field_name": "purity",
                "rule_type": "minimum",
                "priority": "hard",
            }],
            candidate_suppliers=[{
                "supplier": {"supplier_id": "S1", "supplier_name": "Test"},
            }],
        )
        assert inp.run_config is None

    def test_missing_ingredient_raises(self):
        with pytest.raises(ValidationError):
            QualityVerificationInput.model_validate({"requirements": [], "candidate_suppliers": []})


class TestOutputSchema:
    def test_sample_output_parses(self):
        raw = (OUTPUTS_DIR / "sample_output.json").read_text()
        out = QualityVerificationOutput.model_validate(json.loads(raw))
        assert out.ingredient_id == "ING-ASCORBIC-ACID"
        assert len(out.supplier_assessments) == 1
        sa = out.supplier_assessments[0]
        assert sa.supplier_id == "SUP-001"
        assert sa.overall_status == "verified"

    def test_output_round_trip(self):
        raw = (OUTPUTS_DIR / "sample_output.json").read_text()
        out1 = QualityVerificationOutput.model_validate(json.loads(raw))
        serialized = out1.model_dump_json()
        out2 = QualityVerificationOutput.model_validate_json(serialized)
        assert out1 == out2


class TestEnums:
    def test_evidence_status_values(self):
        assert EvidenceStatus.retrieved.value == "retrieved"
        assert EvidenceStatus.blocked.value == "blocked"

    def test_verification_status_pass(self):
        assert VerificationStatus.pass_.value == "pass"

    def test_supplier_assessment_status(self):
        assert SupplierAssessmentStatus.verified.value == "verified"
        assert SupplierAssessmentStatus.failed_hard_requirements.value == "failed_hard_requirements"

    def test_source_type(self):
        assert SourceType.coa.value == "coa"
        assert SourceType.tds.value == "tds"

    def test_invalid_confidence_raises(self):
        with pytest.raises(ValidationError):
            ExtractedAttribute(
                attribute_id="A1",
                field_name="test",
                value="x",
                confidence="very_high",
            )

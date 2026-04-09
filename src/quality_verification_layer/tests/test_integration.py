"""Integration tests for the full quality verification pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from quality_verification_layer.config import QualityVerificationConfig
from quality_verification_layer.runner import run_quality_verification, run_from_json
from quality_verification_layer.schemas import (
    CandidateSupplier,
    Confidence,
    EvidenceHints,
    IngredientRef,
    QualityVerificationInput,
    QualityVerificationOutput,
    RequirementInput,
    RunConfig,
    SupplierAssessmentStatus,
    SupplierRef,
    VerificationStatus,
)

INPUTS_DIR = Path(__file__).resolve().parent.parent / "inputs"


def _config() -> QualityVerificationConfig:
    return QualityVerificationConfig(
        gemini_api_key=None,  # no Gemini in unit tests
        gemini_model="gemini-2.5-flash",
        max_evidence_per_supplier=5,
        rate_limit_delay=0.0,
        fetch_timeout=5,
        search_delay=0.0,
        search_results_per_query=0,  # disable search in unit tests
    )


def _input(suppliers=None, requirements=None):
    return QualityVerificationInput(
        ingredient=IngredientRef(
            ingredient_id="ING-ASCORBIC-ACID",
            canonical_name="Ascorbic Acid",
            aliases=["Vitamin C"],
        ),
        requirements=requirements or [
            RequirementInput(
                requirement_id="REQ-001",
                field_name="purity",
                rule_type="range",
                min_value=99.0,
                max_value=100.5,
                unit="%",
                priority="hard",
            ),
            RequirementInput(
                requirement_id="REQ-002",
                field_name="heavy_metals",
                rule_type="maximum",
                operator="<=",
                max_value=10,
                unit="ppm",
                priority="soft",
            ),
        ],
        candidate_suppliers=suppliers or [
            CandidateSupplier(
                supplier=SupplierRef(
                    supplier_id="SUP-001",
                    supplier_name="Test Supplier",
                ),
                source_urls=[],  # no URLs = no evidence
            ),
        ],
    )


class TestFullPipeline:
    def test_produces_valid_output(self):
        output = run_quality_verification(_input(), _config())
        assert isinstance(output, QualityVerificationOutput)
        assert output.ingredient_id == "ING-ASCORBIC-ACID"
        assert len(output.supplier_assessments) == 1

    def test_supplier_with_no_urls_is_insufficient(self):
        """Supplier with no source URLs → insufficient evidence."""
        output = run_quality_verification(_input(), _config())
        sa = output.supplier_assessments[0]
        assert sa.overall_status in (
            SupplierAssessmentStatus.insufficient_evidence.value,
            SupplierAssessmentStatus.processing_error.value,
        )

    def test_all_requirements_reported(self):
        """Every requirement gets a verification result, even if unknown."""
        output = run_quality_verification(_input(), _config())
        sa = output.supplier_assessments[0]
        assert len(sa.verification_results) == 2
        # Without Gemini + URLs, all should be unknown
        for vr in sa.verification_results:
            assert vr.status in (
                VerificationStatus.unknown.value,
                "unknown",
            )

    def test_coverage_summary_counts(self):
        output = run_quality_verification(_input(), _config())
        sa = output.supplier_assessments[0]
        cov = sa.coverage_summary
        assert cov.requirements_total == 2
        # Both unknown (no extraction without Gemini/URLs)
        assert cov.hard_unknown >= 1
        assert cov.soft_unknown >= 0

    def test_multiple_suppliers(self):
        suppliers = [
            CandidateSupplier(
                supplier=SupplierRef(supplier_id="S1", supplier_name="Supplier A"),
            ),
            CandidateSupplier(
                supplier=SupplierRef(supplier_id="S2", supplier_name="Supplier B"),
            ),
            CandidateSupplier(
                supplier=SupplierRef(supplier_id="S3", supplier_name="Supplier C"),
            ),
        ]
        output = run_quality_verification(_input(suppliers=suppliers), _config())
        assert len(output.supplier_assessments) == 3
        ids = {sa.supplier_id for sa in output.supplier_assessments}
        assert ids == {"S1", "S2", "S3"}

    def test_notes_include_missing_fields(self):
        output = run_quality_verification(_input(), _config())
        sa = output.supplier_assessments[0]
        # Should note which fields are missing
        all_notes = " ".join(sa.notes)
        assert "purity" in all_notes or "heavy_metals" in all_notes


class TestConvenienceFunctions:
    def test_run_from_json(self):
        raw = (INPUTS_DIR / "sample_input.json").read_text()
        out_json = run_from_json(raw, _config())
        output = QualityVerificationOutput.model_validate_json(out_json)
        assert output.ingredient_id == "ING-ASCORBIC-ACID"

    def test_output_is_valid_json(self):
        output = run_quality_verification(_input(), _config())
        json_str = output.model_dump_json(indent=2)
        reparsed = json.loads(json_str)
        assert "supplier_assessments" in reparsed
        assert reparsed["schema_version"] == "1.0"


class TestContractCompatibility:
    def test_output_matches_spec_structure(self):
        """Verify output has all fields the spec requires."""
        output = run_quality_verification(_input(), _config())
        sa = output.supplier_assessments[0]

        # Required top-level fields
        assert hasattr(sa, "supplier_id")
        assert hasattr(sa, "evidence_items")
        assert hasattr(sa, "extracted_attributes")
        assert hasattr(sa, "verification_results")
        assert hasattr(sa, "coverage_summary")
        assert hasattr(sa, "overall_evidence_confidence")
        assert hasattr(sa, "overall_status")
        assert hasattr(sa, "notes")

        # Coverage summary fields
        cov = sa.coverage_summary
        assert hasattr(cov, "requirements_total")
        assert hasattr(cov, "hard_pass")
        assert hasattr(cov, "hard_fail")
        assert hasattr(cov, "hard_unknown")
        assert hasattr(cov, "soft_pass")
        assert hasattr(cov, "soft_fail")
        assert hasattr(cov, "soft_unknown")

    def test_verification_results_have_ids_and_reasons(self):
        output = run_quality_verification(_input(), _config())
        for vr in output.supplier_assessments[0].verification_results:
            assert vr.verification_id
            assert vr.requirement_id
            assert vr.field_name
            assert vr.reason

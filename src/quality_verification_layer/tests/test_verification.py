"""Tests for requirement verification logic."""

from __future__ import annotations

from quality_verification_layer.id_generator import QualityIdGenerator
from quality_verification_layer.schemas import (
    Confidence,
    ExtractedAttribute,
    RequirementInput,
    VerificationStatus,
)
from quality_verification_layer.verification import verify_requirements


def _attr(field_name: str, value: str, unit: str = None, confidence: str = "high"):
    return ExtractedAttribute(
        attribute_id="A1",
        field_name=field_name,
        value=value,
        unit=unit,
        confidence=confidence,
    )


def _req(field_name: str, rule_type: str, **kwargs):
    return RequirementInput(
        requirement_id="R1",
        field_name=field_name,
        rule_type=rule_type,
        priority=kwargs.pop("priority", "hard"),
        **kwargs,
    )


class TestRangeRequirement:
    def test_pass(self):
        results = verify_requirements(
            [_attr("purity", "99.7", "%")],
            [_req("purity", "range", min_value=99.0, max_value=100.5, unit="%")],
            QualityIdGenerator("S1"),
        )
        assert results[0].status == VerificationStatus.pass_

    def test_fail_below(self):
        results = verify_requirements(
            [_attr("purity", "98.5", "%")],
            [_req("purity", "range", min_value=99.0, max_value=100.5, unit="%")],
            QualityIdGenerator("S1"),
        )
        assert results[0].status == VerificationStatus.fail


class TestMaximumRequirement:
    def test_pass(self):
        results = verify_requirements(
            [_attr("heavy_metals", "8", "ppm")],
            [_req("heavy_metals", "maximum", operator="<=", max_value=10, unit="ppm")],
            QualityIdGenerator("S1"),
        )
        assert results[0].status == VerificationStatus.pass_

    def test_fail_exceeds(self):
        results = verify_requirements(
            [_attr("heavy_metals", "12", "ppm")],
            [_req("heavy_metals", "maximum", operator="<=", max_value=10, unit="ppm")],
            QualityIdGenerator("S1"),
        )
        assert results[0].status == VerificationStatus.fail


class TestMinimumRequirement:
    def test_pass(self):
        results = verify_requirements(
            [_attr("purity", "99.5", "%")],
            [_req("purity", "minimum", operator=">=", min_value=99.0, unit="%")],
            QualityIdGenerator("S1"),
        )
        assert results[0].status == VerificationStatus.pass_

    def test_fail(self):
        results = verify_requirements(
            [_attr("purity", "98.0", "%")],
            [_req("purity", "minimum", operator=">=", min_value=99.0, unit="%")],
            QualityIdGenerator("S1"),
        )
        assert results[0].status == VerificationStatus.fail


class TestMissingValue:
    def test_unknown_when_no_attribute(self):
        results = verify_requirements(
            [],
            [_req("lead", "maximum", operator="<=", max_value=2, unit="ppm")],
            QualityIdGenerator("S1"),
        )
        assert results[0].status == VerificationStatus.unknown
        assert "No value found" in results[0].reason


class TestEnumMatch:
    def test_pass(self):
        results = verify_requirements(
            [_attr("grade", "USP")],
            [_req("grade", "enum_match", allowed_values=["USP", "FCC"])],
            QualityIdGenerator("S1"),
        )
        assert results[0].status == VerificationStatus.pass_

    def test_fail(self):
        results = verify_requirements(
            [_attr("grade", "Industrial")],
            [_req("grade", "enum_match", allowed_values=["USP", "FCC"])],
            QualityIdGenerator("S1"),
        )
        assert results[0].status == VerificationStatus.fail


class TestBooleanRequired:
    def test_pass(self):
        results = verify_requirements(
            [_attr("gmp_certified", "true")],
            [_req("gmp_certified", "boolean_required", required=True)],
            QualityIdGenerator("S1"),
        )
        assert results[0].status == VerificationStatus.pass_

    def test_fail(self):
        results = verify_requirements(
            [_attr("gmp_certified", "false")],
            [_req("gmp_certified", "boolean_required", required=True)],
            QualityIdGenerator("S1"),
        )
        assert results[0].status == VerificationStatus.fail


class TestTraceability:
    def test_ids_generated(self):
        results = verify_requirements(
            [_attr("purity", "99.5", "%")],
            [_req("purity", "minimum", operator=">=", min_value=99.0)],
            QualityIdGenerator("S1"),
        )
        assert results[0].verification_id.startswith("VER-S1-")
        assert results[0].requirement_id == "R1"

    def test_reason_populated(self):
        results = verify_requirements(
            [_attr("purity", "99.5", "%")],
            [_req("purity", "minimum", operator=">=", min_value=99.0)],
            QualityIdGenerator("S1"),
        )
        assert len(results[0].reason) > 0


class TestLowConfidenceDowngrade:
    def test_low_confidence_downgrades_to_partial(self):
        results = verify_requirements(
            [_attr("purity", "99.5", "%", confidence="low")],
            [_req("purity", "minimum", operator=">=", min_value=99.0)],
            QualityIdGenerator("S1"),
        )
        assert results[0].status == VerificationStatus.partial

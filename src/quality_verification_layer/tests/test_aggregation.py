"""Tests for assessment aggregation."""

from __future__ import annotations

from quality_verification_layer.aggregation import (
    compute_coverage_summary,
    compute_overall_confidence,
    compute_overall_status,
)
from quality_verification_layer.schemas import (
    Confidence,
    EvidenceItem,
    EvidenceStatus,
    ExtractedAttribute,
    RequirementInput,
    SourceType,
    SupplierAssessmentStatus,
    VerificationResultItem,
    VerificationStatus,
)


def _vr(req_id: str, status: str, priority: str = "hard"):
    return VerificationResultItem(
        verification_id="V1",
        requirement_id=req_id,
        field_name="test",
        status=status,
    )


def _req(req_id: str, priority: str = "hard"):
    return RequirementInput(
        requirement_id=req_id,
        field_name="test",
        rule_type="minimum",
        priority=priority,
    )


class TestCoverageSummary:
    def test_all_hard_pass(self):
        results = [_vr("R1", "pass"), _vr("R2", "pass")]
        reqs = [_req("R1", "hard"), _req("R2", "hard")]
        cov = compute_coverage_summary(results, reqs)
        assert cov.hard_pass == 2
        assert cov.hard_fail == 0
        assert cov.hard_unknown == 0

    def test_mixed_priorities(self):
        results = [_vr("R1", "pass"), _vr("R2", "fail"), _vr("R3", "unknown")]
        reqs = [_req("R1", "hard"), _req("R2", "hard"), _req("R3", "soft")]
        cov = compute_coverage_summary(results, reqs)
        assert cov.hard_pass == 1
        assert cov.hard_fail == 1
        assert cov.soft_unknown == 1

    def test_counts_correct(self):
        results = [_vr("R1", "pass"), _vr("R2", "unknown")]
        reqs = [_req("R1", "soft"), _req("R2", "soft")]
        cov = compute_coverage_summary(results, reqs)
        assert cov.requirements_total == 2
        assert cov.soft_pass == 1
        assert cov.soft_unknown == 1


class TestOverallStatus:
    def test_verified(self):
        from quality_verification_layer.schemas import CoverageSummary

        cov = CoverageSummary(requirements_total=2, hard_pass=2)
        evidence = [EvidenceItem(evidence_id="E1", source_url="x", status="retrieved")]
        assert compute_overall_status(cov, evidence) == SupplierAssessmentStatus.verified

    def test_failed_hard(self):
        from quality_verification_layer.schemas import CoverageSummary

        cov = CoverageSummary(requirements_total=2, hard_pass=1, hard_fail=1)
        evidence = [EvidenceItem(evidence_id="E1", source_url="x", status="retrieved")]
        assert compute_overall_status(cov, evidence) == SupplierAssessmentStatus.failed_hard_requirements

    def test_all_blocked_is_processing_error(self):
        from quality_verification_layer.schemas import CoverageSummary

        cov = CoverageSummary(requirements_total=2)
        evidence = [EvidenceItem(evidence_id="E1", source_url="x", status="blocked")]
        assert compute_overall_status(cov, evidence) == SupplierAssessmentStatus.processing_error

    def test_no_evidence_is_insufficient(self):
        from quality_verification_layer.schemas import CoverageSummary

        cov = CoverageSummary(requirements_total=2)
        assert compute_overall_status(cov, []) == SupplierAssessmentStatus.insufficient_evidence

    def test_verified_with_gaps(self):
        from quality_verification_layer.schemas import CoverageSummary

        cov = CoverageSummary(requirements_total=3, hard_pass=2, hard_unknown=1)
        evidence = [EvidenceItem(evidence_id="E1", source_url="x", status="retrieved")]
        assert compute_overall_status(cov, evidence) == SupplierAssessmentStatus.verified_with_gaps


class TestOverallConfidence:
    def test_high_with_strong_evidence(self):
        evidence = [EvidenceItem(evidence_id="E1", source_url="x", source_type="tds", status="retrieved")]
        attrs = [
            ExtractedAttribute(attribute_id="A1", field_name="f1", value="v", confidence="high"),
            ExtractedAttribute(attribute_id="A2", field_name="f2", value="v", confidence="high"),
        ]
        assert compute_overall_confidence(evidence, attrs) == Confidence.high

    def test_low_with_no_evidence(self):
        assert compute_overall_confidence([], []) == Confidence.low

    def test_medium_with_tds_only(self):
        evidence = [EvidenceItem(evidence_id="E1", source_url="x", source_type="tds", status="retrieved")]
        attrs = [ExtractedAttribute(attribute_id="A1", field_name="f1", value="v", confidence="medium")]
        assert compute_overall_confidence(evidence, attrs) == Confidence.medium

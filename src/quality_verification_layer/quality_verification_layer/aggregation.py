"""Assessment aggregation — coverage summary, overall status, confidence."""

from __future__ import annotations

from typing import List

from .schemas import (
    Confidence,
    CoverageSummary,
    EvidenceItem,
    EvidenceStatus,
    ExtractedAttribute,
    RequirementInput,
    SupplierAssessmentStatus,
    VerificationResultItem,
    VerificationStatus,
)


def compute_coverage_summary(
    results: List[VerificationResultItem],
    requirements: List[RequirementInput],
) -> CoverageSummary:
    """Count pass/fail/unknown by priority (hard/soft)."""
    req_priority = {r.requirement_id: r.priority for r in requirements}

    hard_pass = hard_fail = hard_unknown = 0
    soft_pass = soft_fail = soft_unknown = 0

    for vr in results:
        priority = req_priority.get(vr.requirement_id, "hard")
        if isinstance(priority, str):
            p = priority
        else:
            p = priority.value

        status = vr.status if isinstance(vr.status, str) else vr.status.value

        if p == "hard":
            if status == "pass":
                hard_pass += 1
            elif status == "fail":
                hard_fail += 1
            else:
                hard_unknown += 1
        else:
            if status == "pass":
                soft_pass += 1
            elif status == "fail":
                soft_fail += 1
            else:
                soft_unknown += 1

    return CoverageSummary(
        requirements_total=len(results),
        hard_pass=hard_pass,
        hard_fail=hard_fail,
        hard_unknown=hard_unknown,
        soft_pass=soft_pass,
        soft_fail=soft_fail,
        soft_unknown=soft_unknown,
    )


def compute_overall_status(
    coverage: CoverageSummary,
    evidence_items: List[EvidenceItem],
) -> SupplierAssessmentStatus:
    """Determine the overall supplier assessment status."""
    # Check if all evidence failed
    if evidence_items and all(
        (e.status if isinstance(e.status, str) else e.status.value)
        not in ("retrieved",)
        for e in evidence_items
    ):
        return SupplierAssessmentStatus.processing_error

    # No evidence retrieved at all
    retrieved = [
        e for e in evidence_items
        if (e.status if isinstance(e.status, str) else e.status.value) == "retrieved"
    ]
    if not retrieved and evidence_items:
        return SupplierAssessmentStatus.insufficient_evidence

    if not evidence_items:
        return SupplierAssessmentStatus.insufficient_evidence

    # Any hard requirement failed
    if coverage.hard_fail > 0:
        return SupplierAssessmentStatus.failed_hard_requirements

    # All hard requirements passed, no unknowns
    if coverage.hard_unknown == 0 and coverage.hard_pass > 0:
        if coverage.soft_unknown == 0 and coverage.soft_fail == 0:
            return SupplierAssessmentStatus.verified
        return SupplierAssessmentStatus.verified_with_gaps

    # Hard requirements have unknowns
    if coverage.hard_pass > 0:
        return SupplierAssessmentStatus.verified_with_gaps

    return SupplierAssessmentStatus.insufficient_evidence


def compute_overall_confidence(
    evidence_items: List[EvidenceItem],
    attributes: List[ExtractedAttribute],
) -> Confidence:
    """Compute overall evidence confidence for a supplier."""
    retrieved = [
        e for e in evidence_items
        if (e.status if isinstance(e.status, str) else e.status.value) == "retrieved"
    ]
    if not retrieved:
        return Confidence.low

    # Check for COA/TDS (strong evidence types)
    has_strong = any(
        (e.source_type if isinstance(e.source_type, str) else e.source_type.value)
        in ("coa", "tds")
        for e in retrieved
    )

    # Count high-confidence attributes
    high_conf = sum(
        1 for a in attributes
        if (a.confidence if isinstance(a.confidence, str) else a.confidence.value) == "high"
    )

    if has_strong and high_conf >= 2:
        return Confidence.high
    if has_strong or high_conf >= 1:
        return Confidence.medium
    return Confidence.low

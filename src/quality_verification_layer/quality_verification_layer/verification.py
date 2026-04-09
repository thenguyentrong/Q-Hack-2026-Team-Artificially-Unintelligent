"""Requirement verification — compare extracted attributes against rules."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple, Union

from .id_generator import QualityIdGenerator
from .schemas import (
    Confidence,
    ExtractedAttribute,
    RequirementInput,
    VerificationResultItem,
    VerificationStatus,
)


def _parse_numeric_or_range(value: str) -> Tuple[Optional[float], Optional[float]]:
    """Parse a value that may be a single number or a range.

    Handles: "99.5", "99.0-100.5", "NMT 10", "not more than 20",
    "< 0.5", "<= 10", ">= 99", "≤ 10 ppm", etc.

    Returns (lo, hi). For a single value both are the same.
    Returns (None, None) if unparseable.
    """
    v = value.strip()

    # Handle "None" string from Gemini
    if v.lower() in ("none", "n/a", "not available", "not tested", ""):
        return (None, None)

    # Handle text prefixes: "not more than", "NMT", "NLT", "less than", "at least"
    v_lower = v.lower()
    for prefix in ("not more than", "nmt", "no more than", "less than", "max", "maximum"):
        if v_lower.startswith(prefix):
            v = v[len(prefix):].strip()
            break
    for prefix in ("not less than", "nlt", "at least", "min", "minimum"):
        if v_lower.startswith(prefix):
            v = v[len(prefix):].strip()
            break

    # Strip units (but keep spaces for now to preserve structure)
    v = re.sub(r"(ppm|ppb|mg/kg|cfu/g|mg|µg|mesh|degrees|months|%)", "", v, flags=re.I).strip()
    v = re.sub(r"\s+", " ", v).strip()

    for sep in ("–", "—", "−", "-", "~", "to"):
        if sep in v:
            parts = v.split(sep, 1)
            try:
                lo = float(parts[0].strip().lstrip("<>≤≥~= "))
                hi = float(parts[1].strip().lstrip("<>≤≥~= "))
                return (lo, hi)
            except (ValueError, IndexError):
                continue

    try:
        cleaned = v.lstrip("<>≤≥~= ")
        n = float(cleaned)
        return (n, n)
    except (ValueError, TypeError):
        return (None, None)


def _evaluate_requirement(
    req: RequirementInput, actual_value: str
) -> Tuple[VerificationStatus, str]:
    """Evaluate a requirement against an actual value.

    Returns (status, reason).
    """
    rule = req.rule_type if isinstance(req.rule_type, str) else req.rule_type.value
    op = req.operator

    # Boolean checks
    if rule == "boolean_required":
        is_true = actual_value.lower() in ("true", "yes", "1")
        if req.required and is_true:
            return VerificationStatus.pass_, f"Required boolean is satisfied"
        elif req.required and not is_true:
            return VerificationStatus.fail, f"Required boolean not met: got '{actual_value}'"
        return VerificationStatus.pass_, "Boolean check passed"

    # Enum match
    if rule == "enum_match":
        if req.allowed_values:
            normed = actual_value.lower().strip()
            if any(e.lower() in normed for e in req.allowed_values):
                matched = [e for e in req.allowed_values if e.lower() in normed]
                return VerificationStatus.pass_, f"Matches allowed value(s): {matched}"
            return VerificationStatus.fail, f"'{actual_value}' not in allowed values {req.allowed_values}"
        # Legacy: operator "in" with allowed_values
        return VerificationStatus.unknown, "No allowed_values specified for enum_match"

    # Free text reference
    if rule == "free_text_reference":
        return VerificationStatus.partial, f"Free text reference found: '{actual_value}'"

    # Numeric comparisons
    lo, hi = _parse_numeric_or_range(actual_value)
    if lo is None or hi is None:
        return VerificationStatus.unknown, f"Could not parse numeric value from '{actual_value}'"

    unit = req.unit or ""

    if rule == "range":
        if req.min_value is not None and req.max_value is not None:
            if lo >= req.min_value and hi <= req.max_value:
                return VerificationStatus.pass_, f"Observed {lo}{unit} is within range {req.min_value}-{req.max_value}{unit}"
            return VerificationStatus.fail, f"Observed {lo}{unit} outside required range {req.min_value}-{req.max_value}{unit}"

    if rule == "minimum" or op == ">=":
        threshold = req.min_value if req.min_value is not None else (float(req.max_value) if req.max_value is not None else None)
        if threshold is not None:
            if lo >= threshold:
                return VerificationStatus.pass_, f"Observed {lo}{unit} meets minimum {threshold}{unit}"
            return VerificationStatus.fail, f"Observed {lo}{unit} below minimum {threshold}{unit}"

    if rule == "maximum" or op == "<=":
        threshold = req.max_value if req.max_value is not None else (float(req.min_value) if req.min_value is not None else None)
        if threshold is not None:
            if hi <= threshold:
                return VerificationStatus.pass_, f"Observed {hi}{unit} within maximum {threshold}{unit}"
            return VerificationStatus.fail, f"Observed {hi}{unit} exceeds maximum {threshold}{unit}"

    return VerificationStatus.unknown, f"Could not evaluate rule_type '{rule}' with operator '{op}'"


def verify_requirements(
    attributes: List[ExtractedAttribute],
    requirements: List[RequirementInput],
    id_gen: QualityIdGenerator,
    ingredient_name: str = "",
) -> List[VerificationResultItem]:
    """Compare extracted attributes against requirements.

    Normalizes both requirement field names and attribute field names
    to canonical form before matching.

    Returns a list of VerificationResultItem — one per requirement.
    """
    from .normalization import normalize_field_name

    # Build field_name -> best attribute lookup
    attr_by_field: Dict[str, ExtractedAttribute] = {}
    for attr in attributes:
        fname = attr.field_name
        if fname not in attr_by_field:
            attr_by_field[fname] = attr
        else:
            # Keep higher-confidence one
            existing = attr_by_field[fname]
            rank = {"high": 0, "medium": 1, "low": 2}
            ec = existing.confidence if isinstance(existing.confidence, str) else existing.confidence.value
            ac = attr.confidence if isinstance(attr.confidence, str) else attr.confidence.value
            if rank.get(ac, 1) < rank.get(ec, 1):
                attr_by_field[fname] = attr

    results: List[VerificationResultItem] = []

    for req in requirements:
        # Try exact match first, then normalized match
        req_field = req.field_name
        attr = attr_by_field.get(req_field)
        if attr is None:
            # Normalize requirement field name and retry
            normalized_req = normalize_field_name(req_field, ingredient_name)
            attr = attr_by_field.get(normalized_req)
            if attr is None and normalized_req != req_field:
                # Also try: maybe extracted field matches the raw req name
                for fname, a in attr_by_field.items():
                    if normalize_field_name(fname, ingredient_name) == normalized_req:
                        attr = a
                        break

        if attr is None:
            results.append(VerificationResultItem(
                verification_id=id_gen.next_verification_id(),
                requirement_id=req.requirement_id,
                field_name=req.field_name,
                status=VerificationStatus.unknown,
                confidence=Confidence.low,
                reason=f"No value found for '{req.field_name}' in any evidence source",
            ))
            continue

        # Evaluate
        actual_str = str(attr.value)
        status, reason = _evaluate_requirement(req, actual_str)

        # Note low confidence but don't downgrade the verdict — the value still meets the requirement
        attr_conf = attr.confidence if isinstance(attr.confidence, str) else attr.confidence.value
        if attr_conf == "low" and status == VerificationStatus.pass_:
            reason = f"{reason} (note: low source confidence)"

        ver_confidence = Confidence(attr_conf) if attr_conf in ("high", "medium", "low") else Confidence.medium

        evidence_ids = [attr.source_evidence_id] if attr.source_evidence_id else []

        results.append(VerificationResultItem(
            verification_id=id_gen.next_verification_id(),
            requirement_id=req.requirement_id,
            field_name=req.field_name,
            status=status,
            observed_value=attr.value,
            unit=attr.unit,
            confidence=ver_confidence,
            reason=reason,
            supporting_evidence_ids=evidence_ids,
        ))

    return results

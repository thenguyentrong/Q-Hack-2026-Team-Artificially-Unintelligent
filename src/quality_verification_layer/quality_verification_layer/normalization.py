"""Canonical field name mapping and conflict resolution."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .schemas import Confidence, ExtractedAttribute, SourceType

logger = logging.getLogger(__name__)

# ── Canonical field name map ─────────────────────────────────────────────────
# Maps common extracted field name variants to canonical requirement field names.

CANONICAL_FIELD_MAP: Dict[str, str] = {
    # Purity / assay
    "purity": "purity",
    "assay": "purity",
    "assay_percent": "purity",
    "content": "purity",
    "potency": "potency",
    "protein": "purity",
    "protein_content": "purity",
    # Grade
    "grade": "grade",
    "grade_claims": "grade",
    # Physical form
    "form": "form",
    "physical_form": "form",
    "appearance": "appearance",
    # Heavy metals
    "heavy_metal": "heavy_metals",
    "heavy_metals": "heavy_metals",
    "heavy_metals_ppm": "heavy_metals",
    "total_heavy_metals": "heavy_metals",
    "heavy_metals_lead": "lead",
    "heavy_metals_arsenic": "arsenic",
    "heavy_metals_cadmium": "cadmium",
    "heavy_metals_mercury": "mercury",
    "heavy_metals_as_lead": "heavy_metals",
    "heavy_metals_as_pb": "heavy_metals",
    # Individual metals
    "lead": "lead",
    "lead_ppm": "lead",
    "pb": "lead",
    "arsenic": "arsenic",
    "arsenic_ppm": "arsenic",
    "as": "arsenic",
    "mercury": "mercury",
    "hg": "mercury",
    "cadmium": "cadmium",
    "cd": "cadmium",
    # Particle / mesh
    "particle_size": "particle_size",
    "particle_size_mesh": "particle_size",
    "mesh": "mesh_size",
    "mesh_size": "mesh_size",
    "sieve": "mesh_size",
    # Loss on drying / moisture
    "loss_on_drying": "loss_on_drying",
    "loss_on_drying_percent": "loss_on_drying",
    "lod": "loss_on_drying",
    "moisture": "loss_on_drying",
    "water_content": "loss_on_drying",
    # pH
    "ph": "ph",
    # Specific rotation
    "specific_rotation": "specific_rotation",
    "optical_rotation": "specific_rotation",
    # Residue on ignition / ash
    "residue_on_ignition": "residue_on_ignition",
    "roi": "residue_on_ignition",
    "sulfated_ash": "residue_on_ignition",
    "ash": "residue_on_ignition",
    # Certifications / compliance
    "gmp": "gmp_certified",
    "gmp_certified": "gmp_certified",
    "gmp_compliant": "gmp_certified",
    "certifications": "certifications",
    "kosher": "kosher",
    "halal": "halal",
    "non_gmo": "non_gmo",
    "organic": "organic",
    "gras": "gras_status",
    "gras_status": "gras_status",
    # Microbial
    "total_plate_count": "total_plate_count",
    "tpc": "total_plate_count",
    "aerobic_count": "total_plate_count",
    "micro_limits": "micro_limits",
    "yeast": "yeast_mold",
    "mold": "yeast_mold",
    "yeast_and_mold": "yeast_mold",
    "yeast_mold": "yeast_mold",
    "coliform": "coliform",
    "e_coli": "e_coli",
    "salmonella": "salmonella",
    # Storage / shelf life
    "storage": "storage_conditions",
    "storage_conditions": "storage_conditions",
    "storage_condition": "storage_conditions",
    "shelf_life": "shelf_life",
    "shelf_life_months": "shelf_life",
    "retest": "shelf_life",
    "expiry": "shelf_life",
}

_NUMERIC_CANONICAL_FIELDS: Set[str] = {
    "purity", "potency", "heavy_metals", "lead", "arsenic", "mercury",
    "cadmium", "particle_size", "mesh_size", "loss_on_drying", "ph",
    "specific_rotation", "residue_on_ignition", "total_plate_count",
    "yeast_mold", "coliform", "shelf_life",
}

_PERCENT_FIELDS: Set[str] = {
    "purity", "potency", "loss_on_drying", "residue_on_ignition",
}

_PPM_FIELDS: Set[str] = {
    "heavy_metals", "lead", "arsenic", "mercury", "cadmium",
}

_CAS_PATTERN = re.compile(r"^\d{2,7}-\d{2}-\d$")
_EC_PATTERN = re.compile(r"^\d{3}-\d{3}-\d$")


def _looks_like_identifier(value: str) -> bool:
    v = value.strip()
    if _CAS_PATTERN.match(v) or _EC_PATTERN.match(v):
        return True
    if re.match(r"^[A-Z][a-z]?\d+([A-Z][a-z]?\d+)+$", v):
        return True
    return False


def _has_unit_mismatch(canonical: str, value: str, unit: Optional[str]) -> bool:
    combined = f"{value.lower()} {(unit or '').lower()}"
    has_pct = "%" in combined or "percent" in combined
    has_ppm = any(tok in combined for tok in ("ppm", "ppb", "mg/kg", "µg/kg", "mg/l"))
    if canonical in _PPM_FIELDS and has_pct and not has_ppm:
        return True
    if canonical in _PERCENT_FIELDS and has_ppm and not has_pct:
        return True
    return False


def _value_is_plausible(canonical: str, value: str, unit: Optional[str] = None) -> bool:
    if canonical not in _NUMERIC_CANONICAL_FIELDS:
        return True
    v = value.strip()
    if _looks_like_identifier(v):
        return False
    if not re.search(r"\d", v):
        return False
    if _has_unit_mismatch(canonical, v, unit):
        return False
    return True


def _ingredient_stop_words(ingredient: str) -> Set[str]:
    words: Set[str] = set()
    for word in ingredient.lower().replace("-", " ").split():
        if len(word) > 2:
            words.add(word)
    return words


def normalize_field_name(raw_name: str, ingredient: str) -> str:
    """Map a raw extracted field name to a canonical requirement field name.

    Strategy (in order):
    1. Exact match in CANONICAL_FIELD_MAP
    2. Strip ingredient stop-words, retry exact match
    3. Match individual underscore-separated parts (e.g. "lead" in "lead_content_ppm")
    4. Match multi-part segments (e.g. "heavy_metals" in "heavy_metals_as_pb")
    5. Return original name unchanged
    """
    key = raw_name.lower().strip()

    # 1. Exact match
    if key in CANONICAL_FIELD_MAP:
        return CANONICAL_FIELD_MAP[key]

    # 2. Strip ingredient stop-words, retry
    stop_words = _ingredient_stop_words(ingredient)
    parts = [p for p in key.split("_") if p not in stop_words]
    stripped = "_".join(parts)
    if stripped and stripped in CANONICAL_FIELD_MAP:
        return CANONICAL_FIELD_MAP[stripped]

    key_parts = key.split("_")

    # 3. Match multi-part segments first (longer = more specific)
    # For "heavy_metals_as_lead_ppm" → tries "heavy_metals_as" then "heavy_metals" before "lead"
    for window_size in range(min(4, len(key_parts)), 1, -1):
        for i in range(len(key_parts) - window_size + 1):
            segment = "_".join(key_parts[i : i + window_size])
            if segment in CANONICAL_FIELD_MAP:
                return CANONICAL_FIELD_MAP[segment]

    # 4. Match individual parts as exact canonical keys
    # Skip generic suffixes that aren't field identifiers
    _SKIP_PARTS = {"content", "count", "percent", "ppm", "ppb", "mg", "cfu",
                   "status", "presence", "test", "total", "value", "limit",
                   "level", "max", "min", "as", "g", "kg"}
    for part in sorted(key_parts, key=len, reverse=True):
        if len(part) >= 2 and part not in _SKIP_PARTS and part in CANONICAL_FIELD_MAP:
            return CANONICAL_FIELD_MAP[part]

    return raw_name


def normalize_attributes(
    attributes: List[ExtractedAttribute],
    ingredient: str,
) -> List[ExtractedAttribute]:
    """Normalize field names on extracted attributes to canonical names.

    Rejects mappings where the value is implausible for the canonical field.
    """
    for attr in attributes:
        original = attr.field_name
        canonical = normalize_field_name(original, ingredient)
        if canonical != original:
            if _value_is_plausible(canonical, str(attr.value), attr.unit):
                attr.field_name = canonical
            else:
                logger.debug(
                    "Rejected mapping %r -> %r: value %r implausible",
                    original, canonical, attr.value,
                )
    return attributes


# ── Source priority ──────────────────────────────────────────────────────────

SOURCE_PRIORITY = {
    "coa": 0,
    "tds": 1,
    "certification_page": 2,
    "product_page": 3,
    "marketing_page": 4,
    "other": 5,
}

CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}


def resolve_conflicts(
    attributes: List[ExtractedAttribute],
    evidence_items: List["EvidenceItem"],
) -> Tuple[List[ExtractedAttribute], List[str]]:
    """Resolve conflicting attributes for the same field.

    When multiple attributes map to the same field_name:
    - Prefer higher-confidence source
    - If equal confidence, prefer stronger evidence type (COA > TDS > ...)
    - Emit conflict notes

    Returns (resolved_attributes, conflict_notes).
    """
    from .schemas import EvidenceItem as _EI

    # Build evidence_id -> source_type lookup
    evid_type: Dict[str, str] = {}
    for ei in evidence_items:
        evid_type[ei.evidence_id] = ei.source_type if isinstance(ei.source_type, str) else ei.source_type.value

    # Group by field_name
    field_groups: Dict[str, List[ExtractedAttribute]] = {}
    for attr in attributes:
        field_groups.setdefault(attr.field_name, []).append(attr)

    resolved: List[ExtractedAttribute] = []
    notes: List[str] = []

    for field_name, group in field_groups.items():
        if len(group) == 1:
            resolved.append(group[0])
            continue

        # Sort by confidence (high first), then by source priority (COA first)
        def sort_key(a: ExtractedAttribute):
            conf = CONFIDENCE_RANK.get(
                a.confidence if isinstance(a.confidence, str) else a.confidence.value, 1
            )
            src_type = evid_type.get(a.source_evidence_id, "other")
            src_prio = SOURCE_PRIORITY.get(src_type, 5)
            return (conf, src_prio)

        group.sort(key=sort_key)
        winner = group[0]
        resolved.append(winner)

        # Check if values actually differ
        values = {str(a.value) for a in group}
        if len(values) > 1:
            notes.append(
                f"Conflict on '{field_name}': {len(group)} sources with values "
                f"{values}; using value from {evid_type.get(winner.source_evidence_id, 'unknown')} source"
            )

    return resolved, notes

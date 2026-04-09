"""Gemini-powered field extraction from evidence documents."""

from __future__ import annotations

import json
import logging
import time
from typing import Dict, List, Optional

from .id_generator import QualityIdGenerator
from .retrieval import FetchedSource
from .schemas import Confidence, ExtractedAttribute, ExtractionMethod

logger = logging.getLogger(__name__)


def _build_extraction_prompt(
    ingredient: str, supplier: str, sources: List[FetchedSource],
    requirement_fields: Optional[List[str]] = None,
) -> str:
    """Build a prompt asking Gemini to extract quality fields from source text."""
    source_blocks: List[str] = []
    sorted_sources = sorted(sources, key=lambda s: (0 if s.content_type == "pdf" else 1))
    remaining_budget = 30_000

    for i, src in enumerate(sorted_sources, 1):
        if not src.ok or remaining_budget <= 0:
            continue
        label = f"[Source {i}: {src.url} ({src.content_type})]"
        trimmed = src.text[:remaining_budget]
        remaining_budget -= len(trimmed)
        source_blocks.append(f"{label}\n{trimmed}")

    combined = "\n\n---\n\n".join(source_blocks) if source_blocks else "(no accessible sources)"

    priority_section = ""
    if requirement_fields:
        fields_str = ", ".join(requirement_fields)
        priority_section = f"""
REQUIRED FIELDS — you MUST attempt to extract these fields. If a field is not
found in the documents, do NOT include it in the output (omit the key entirely).
Required fields: {fields_str}
"""

    return f"""You are a quality-assurance data extraction specialist.

Target ingredient: {ingredient}
Target supplier: {supplier}

Below are documents fetched from the supplier's website.
Extract quality-related fields — especially: purity/assay, heavy metals (lead, arsenic,
cadmium, mercury), pH, loss on drying, residue on ignition, microbial limits,
certifications, storage, shelf life.
{priority_section}
IMPORTANT:
- Only include fields where you found an actual value in the documents.
- Do NOT return "None", "N/A", or "Not Available" as values — simply omit those fields.
- Specification limits ARE valid values. Extract "NMT 10 ppm" as value "10", "≤ 0.5%" as value "0.5", etc.
- If a document says "conforms" or "passes test", extract as value "true".
- If a COA shows an actual test result, prefer that over a TDS spec limit.

IMPORTANT: For each field also rate "source_confidence":
  "high"   = this document is clearly a spec sheet for '{ingredient}' from '{supplier}'
  "medium" = document is from the supplier but product match is uncertain
  "low"    = document appears to describe a DIFFERENT product, grade, or ingredient

Return a JSON object. Each key is a snake_case field name, value is an object:
  "value": extracted value as string,
  "unit": unit string or null,
  "source_url": the URL this came from,
  "source_confidence": "high" | "medium" | "low"

Return ONLY the JSON object, no markdown fences, no extra text.

--- SOURCE DOCUMENTS ---
{combined}
"""


def extract_attributes_with_gemini(
    ingredient: str,
    supplier: str,
    sources: List[FetchedSource],
    id_gen: QualityIdGenerator,
    gemini_client,
    rate_limit_delay: float = 1.0,
    requirement_fields: Optional[List[str]] = None,
) -> List[ExtractedAttribute]:
    """Use Gemini to extract quality fields from fetched source text.

    Returns a list of ExtractedAttribute with IDs and evidence links.
    """
    accessible = [s for s in sources if s.ok]
    if not accessible:
        return []

    # Build URL -> evidence_id mapping for traceability
    url_to_evid: Dict[str, str] = {}
    for s in sources:
        if s.evidence_id:
            url_to_evid[s.url] = s.evidence_id

    prompt = _build_extraction_prompt(ingredient, supplier, sources, requirement_fields)

    time.sleep(rate_limit_delay)

    from .gemini_wrapper import call_gemini_raw

    raw_text = call_gemini_raw(prompt, gemini_client)
    if not raw_text:
        return []

    # Strip markdown fences
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    raw_text = raw_text.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.warning("Gemini returned non-JSON for %s, skipping extraction", supplier)
        return []

    # Filter out null/None/N/A values
    _SKIP_VALUES = {"none", "n/a", "not available", "not tested", "not applicable",
                    "not specified", "not provided", "null", ""}

    attributes: List[ExtractedAttribute] = []
    for key, val in parsed.items():
        if not isinstance(val, dict):
            continue

        raw_value = str(val.get("value", ""))
        if raw_value.lower().strip() in _SKIP_VALUES:
            continue

        sc = val.get("source_confidence", "medium")
        if sc not in ("high", "medium", "low"):
            sc = "medium"

        source_url = val.get("source_url", "")
        evid_id = url_to_evid.get(source_url, "")

        attr = ExtractedAttribute(
            attribute_id=id_gen.next_attribute_id(),
            field_name=key,
            value=str(val.get("value", "")),
            unit=val.get("unit"),
            source_evidence_id=evid_id,
            confidence=Confidence(sc),
            extraction_method=ExtractionMethod.llm_extraction,
        )
        attributes.append(attr)

    low_conf = [a.field_name for a in attributes if a.confidence == Confidence.low]
    if low_conf:
        logger.warning(
            "Low source_confidence on fields %s — values may be from a different product",
            low_conf,
        )

    return attributes

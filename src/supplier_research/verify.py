"""Agent 2 – Quality verification: fetch source URLs, extract fields, compare to requirements."""
from __future__ import annotations

import json
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx

from .models import (
    ComparisonEntry,
    ExtractedField,
    SupplierResult,
    VerificationResult,
)

_REQ_DIR = Path(__file__).parents[2] / "data" / "requirements"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
}
_FETCH_TIMEOUT = 20  # seconds per URL


# ---------------------------------------------------------------------------
# 1. Fetch content from URLs
# ---------------------------------------------------------------------------

class FetchedSource:
    __slots__ = ("url", "content_type", "text", "ok")

    def __init__(self, url: str, content_type: str, text: str, ok: bool):
        self.url = url
        self.content_type = content_type
        self.text = text
        self.ok = ok


def _fetch_url(url: str, client: httpx.Client) -> FetchedSource:
    """Fetch a single URL. Returns extracted text or an error marker."""
    try:
        resp = client.get(url, timeout=_FETCH_TIMEOUT, follow_redirects=True)
        if resp.status_code >= 400:
            return FetchedSource(url, "", f"[HTTP {resp.status_code}]", ok=False)

        ct = resp.headers.get("content-type", "")

        if "pdf" in ct or url.lower().endswith(".pdf"):
            text = _extract_pdf_text(resp.content)
            return FetchedSource(url, "pdf", text, ok=bool(text.strip()))

        # HTML / plain text — strip tags crudely and cap early
        import re as _re
        text = _re.sub(r"<[^>]+>", " ", resp.text)  # strip HTML tags
        text = _re.sub(r"\s{2,}", " ", text).strip()
        text = text[:6_000]  # cap at 6K chars (~1500 tokens)
        return FetchedSource(url, "html", text, ok=True)

    except Exception as exc:
        return FetchedSource(url, "", f"[Error: {exc}]", ok=False)


def _extract_pdf_text(data: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        return "[pdfplumber not installed – pip install pdfplumber]"

    text_parts: list[str] = []
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            for page in pdf.pages[:5]:  # first 5 pages covers TDS/COA
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as exc:
        return f"[PDF parse error: {exc}]"
    return "\n\n".join(text_parts)


def fetch_all_urls(urls: list[str]) -> list[FetchedSource]:
    """Fetch all URLs sequentially with a shared httpx client."""
    results: list[FetchedSource] = []
    with httpx.Client(headers=_HEADERS) as client:
        for url in urls:
            results.append(_fetch_url(url, client))
    return results


# ---------------------------------------------------------------------------
# 2a. Canonical field name map – maps common extracted variants to standard names
# ---------------------------------------------------------------------------

# Keys are patterns that appear in extracted field names (substring match after
# ingredient-word stripping). Values are the canonical requirement field names.
CANONICAL_FIELD_MAP: dict[str, str] = {
    # Purity / assay
    "purity": "purity",
    "assay": "purity",
    "content": "purity",
    "potency": "potency",
    # Grade
    "grade": "grade",
    # Physical form
    "form": "form",
    "physical_form": "form",
    "appearance": "form",
    # Heavy metals
    "heavy_metal": "heavy_metals",
    "heavy_metals": "heavy_metals",
    "total_heavy_metals": "heavy_metals",
    # Individual metals
    "lead": "lead",
    "pb": "lead",
    "arsenic": "arsenic",
    "as": "arsenic",
    "mercury": "mercury",
    "hg": "mercury",
    "cadmium": "cadmium",
    "cd": "cadmium",
    # Particle / mesh
    "particle_size": "particle_size",
    "mesh": "mesh_size",
    "mesh_size": "mesh_size",
    "sieve": "mesh_size",
    # Loss on drying / moisture
    "loss_on_drying": "loss_on_drying",
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
    "retest": "shelf_life",
    "expiry": "shelf_life",
}


import re as _re_module

# Canonical fields that expect numeric (or numeric-like) values.
# Mapping a CAS number or EC number to these is always wrong.
_NUMERIC_CANONICAL_FIELDS: set[str] = {
    "purity", "potency", "heavy_metals", "lead", "arsenic", "mercury",
    "cadmium", "particle_size", "mesh_size", "loss_on_drying", "ph",
    "specific_rotation", "residue_on_ignition", "total_plate_count",
    "yeast_mold", "coliform", "shelf_life",
}

# Fields whose values are typically in percent (%)
_PERCENT_FIELDS: set[str] = {
    "purity", "potency", "loss_on_drying", "residue_on_ignition",
}
# Fields whose values are typically in ppm / ppb / mg/kg / trace-level units
_PPM_FIELDS: set[str] = {
    "heavy_metals", "lead", "arsenic", "mercury", "cadmium",
}

# Patterns that should never be mapped to a numeric field
_CAS_PATTERN = _re_module.compile(r"^\d{2,7}-\d{2}-\d$")        # e.g. 50-81-7
_EC_PATTERN = _re_module.compile(r"^\d{3}-\d{3}-\d$")            # e.g. 200-066-2
_IDENTIFIER_PATTERNS = [_CAS_PATTERN, _EC_PATTERN]


def _looks_like_identifier(value: str) -> bool:
    """Return True if the value looks like a CAS number, EC number, or similar identifier."""
    v = value.strip()
    for pat in _IDENTIFIER_PATTERNS:
        if pat.match(v):
            return True
    # Also catch things like "C6H8O6" (molecular formula)
    if _re_module.match(r"^[A-Z][a-z]?\d+([A-Z][a-z]?\d+)+$", v):
        return True
    return False


def _has_unit_mismatch(canonical: str, value: str, unit: str | None) -> bool:
    """Return True if the value/unit is the wrong scale for the canonical field.

    - % values should not map to ppm fields (arsenic, lead, heavy_metals, …)
    - ppm/ppb/mg values should not map to % fields (purity, potency, …)
    """
    v_lower = value.lower()
    u_lower = (unit or "").lower()
    combined = f"{v_lower} {u_lower}"

    has_pct = "%" in combined or "percent" in combined
    has_ppm = any(tok in combined for tok in ("ppm", "ppb", "mg/kg", "µg/kg", "mg/l"))

    if canonical in _PPM_FIELDS and has_pct and not has_ppm:
        return True
    if canonical in _PERCENT_FIELDS and has_ppm and not has_pct:
        return True
    return False


def _value_is_plausible_for_field(
    canonical: str, value: str, unit: str | None = None,
) -> bool:
    """Check whether the extracted value makes sense for the canonical field.

    Returns False if a numeric-expecting field gets an identifier, pure text,
    or a value whose unit is the wrong scale (% vs ppm).
    """
    if canonical not in _NUMERIC_CANONICAL_FIELDS:
        return True  # non-numeric fields accept anything

    v = value.strip()

    # Reject identifiers (CAS, EC, molecular formula)
    if _looks_like_identifier(v):
        return False

    # For numeric fields, the value should contain at least one digit
    if not _re_module.search(r"\d", v):
        return False

    # Reject unit-scale mismatches (% ↔ ppm)
    if _has_unit_mismatch(canonical, v, unit):
        return False

    return True


def _ingredient_stop_words(ingredient: str) -> set[str]:
    """Return the individual words of an ingredient name for prefix-stripping."""
    words: set[str] = set()
    for word in ingredient.lower().replace("-", " ").split():
        if len(word) > 2:  # skip short words like 'd3'
            words.add(word)
    return words


def normalize_field_name(raw_name: str, ingredient: str) -> str:
    """Map a raw extracted field name to a canonical requirement field name.

    Strategy (in order):
    1. Exact match in CANONICAL_FIELD_MAP
    2. Strip ingredient stop-words from the name, then look up again
    3. Substring match against canonical map keys
    4. Return original name unchanged (keeps novel fields visible)
    """
    key = raw_name.lower().strip()

    # 1. Exact match
    if key in CANONICAL_FIELD_MAP:
        return CANONICAL_FIELD_MAP[key]

    # 2. Strip ingredient-name words and retry
    stop_words = _ingredient_stop_words(ingredient)
    parts = [p for p in key.split("_") if p not in stop_words]
    stripped = "_".join(parts)
    if stripped and stripped in CANONICAL_FIELD_MAP:
        return CANONICAL_FIELD_MAP[stripped]

    # 3. Substring match: if any canonical key is fully contained in our name
    for canon_key, canon_val in CANONICAL_FIELD_MAP.items():
        if canon_key in key:
            return canon_val

    return raw_name  # novel field — keep as-is


def normalize_extracted_fields(
    extracted: dict[str, "ExtractedField"],
    ingredient: str,
) -> dict[str, "ExtractedField"]:
    """Return a new dict with field names normalized to canonical names.

    When multiple raw names map to the same canonical name, the one with
    source_confidence='high' wins; otherwise the first seen is kept.
    Value validation: if a mapping would place a CAS/EC number or non-numeric
    value into a numeric canonical field, the mapping is rejected and the
    original field name is kept.
    """
    normalized: dict[str, "ExtractedField"] = {}
    confidence_rank = {"high": 0, "medium": 1, "low": 2}

    for raw_name, field in extracted.items():
        canonical = normalize_field_name(raw_name, ingredient)

        # Validate: reject mapping if value is implausible for canonical field
        if canonical != raw_name and not _value_is_plausible_for_field(canonical, field.value, field.unit):
            print(
                f"  Rejected mapping {raw_name!r} → {canonical!r}: "
                f"value {field.value!r} (unit={field.unit!r}) is not plausible",
                file=sys.stderr, flush=True,
            )
            canonical = raw_name  # keep as novel field

        if canonical not in normalized:
            normalized[canonical] = field
        else:
            # Keep the higher-confidence entry
            existing = normalized[canonical]
            if confidence_rank.get(field.source_confidence, 1) < confidence_rank.get(existing.source_confidence, 1):
                normalized[canonical] = field

    return normalized


# ---------------------------------------------------------------------------
# 2b. Gemini extraction of ALL quality fields from fetched content
# ---------------------------------------------------------------------------

def _build_extraction_prompt(ingredient: str, supplier: str, sources: list[FetchedSource]) -> str:
    """Build a prompt that asks Gemini to extract every quality field it can find."""
    source_blocks: list[str] = []
    # Budget: ~8000 chars total across all sources (~2000 tokens), prioritise PDFs
    sorted_sources = sorted(sources, key=lambda s: (0 if s.content_type == "pdf" else 1))
    remaining_budget = 8_000
    for i, src in enumerate(sorted_sources, 1):
        if not src.ok or remaining_budget <= 0:
            continue
        label = f"[Source {i}: {src.url} ({src.content_type})]"
        trimmed = src.text[:remaining_budget]
        remaining_budget -= len(trimmed)
        source_blocks.append(f"{label}\n{trimmed}")

    combined = "\n\n---\n\n".join(source_blocks) if source_blocks else "(no accessible sources)"

    return f"""You are a quality-assurance data extraction specialist.

Target ingredient: {ingredient}
Target supplier: {supplier}

Below are documents fetched from the supplier's website.
Extract EVERY quality-related field you can find — specifications, purity, assay,
identity, physical properties, contaminants, heavy metals, microbial limits,
certifications, allergens, storage, shelf life, regulatory status, etc.

IMPORTANT: For each field also rate "source_confidence":
  "high"   = this document is clearly a spec sheet for '{ingredient}' from '{supplier}'
  "medium" = document is from the supplier but product match is uncertain
  "low"    = document appears to describe a DIFFERENT product, grade, or ingredient
             (e.g. purity value came from a DC-grade or filler-blend product,
              or from a third-party SDS for a different manufacturer)

Return a JSON object. Each key is a snake_case field name, value is an object:
  "value": extracted value as string,
  "unit": unit string or null,
  "source_url": the URL this came from,
  "source_confidence": "high" | "medium" | "low"

Example:
{{
  "purity": {{"value": "99.5", "unit": "%", "source_url": "https://...", "source_confidence": "high"}},
  "lead":   {{"value": "<0.5", "unit": "ppm", "source_url": "https://...", "source_confidence": "medium"}}
}}

Return ONLY the JSON object, no markdown fences, no extra text.

--- SOURCE DOCUMENTS ---
{combined}
"""


def extract_fields_with_gemini(
    ingredient: str,
    supplier: str,
    sources: list[FetchedSource],
    call_with_retry,
    build_llm,
    rate_limit_delay: float,
) -> dict[str, "ExtractedField"]:
    """Use Gemini to extract all quality fields from fetched source text."""
    from .models import ExtractedField  # local import to avoid circularity

    accessible = [s for s in sources if s.ok]
    if not accessible:
        return {}

    prompt = _build_extraction_prompt(ingredient, supplier, sources)

    time.sleep(rate_limit_delay)
    llm = build_llm()
    response = call_with_retry(llm.invoke, prompt)

    raw = response.content
    if isinstance(raw, list):
        raw = " ".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in raw
        ).strip()

    # Strip markdown fences if Gemini wraps them
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  WARNING: Gemini returned non-JSON for {supplier}, skipping extraction", file=sys.stderr)
        return {}

    fields: dict[str, ExtractedField] = {}
    for key, val in parsed.items():
        if isinstance(val, dict):
            sc = val.get("source_confidence", "medium")
            if sc not in ("high", "medium", "low"):
                sc = "medium"
            fields[key] = ExtractedField(
                value=str(val.get("value", "")),
                unit=val.get("unit"),
                source_url=val.get("source_url"),
                source_confidence=sc,
            )

    low_conf = [k for k, v in fields.items() if v.source_confidence == "low"]
    if low_conf:
        print(
            f"  WARNING: low source_confidence on fields {low_conf} — "
            "values may be from a different product",
            file=sys.stderr, flush=True,
        )

    return fields


# ---------------------------------------------------------------------------
# 3. Load requirements
# ---------------------------------------------------------------------------

def load_requirements(ingredient: str) -> list[dict[str, Any]]:
    """Load requirements from data/requirements/{slug}.json. Returns [] if not found."""
    slug = ingredient.lower().replace(" ", "-")
    path = _REQ_DIR / f"{slug}.json"
    if not path.exists():
        print(f"  No requirements file at {path}, skipping comparison", file=sys.stderr)
        return []
    data = json.loads(path.read_text())
    return data.get("requirements", [])


# ---------------------------------------------------------------------------
# 4. Compare extracted fields against requirements
# ---------------------------------------------------------------------------

def _format_requirement(req: dict) -> str:
    """Human-readable requirement string."""
    op = req["operator"]
    val = req["value"]
    unit = req.get("unit", "")
    if op == ">=":
        return f">= {val}{unit}"
    if op == "<=":
        return f"<= {val}{unit}"
    if op == "==":
        return f"== {val}"
    if op == "in":
        return f"one of {val}"
    if op == "range":
        return f"{val[0]}{unit} – {val[1]}{unit}"
    return f"{op} {val}"


def _parse_numeric_or_range(value: str) -> tuple[float | None, float | None]:
    """Parse a value that may be a single number or a range like '99.0%-100.5%'.

    Returns (lo, hi).  For a single value both are the same.
    Returns (None, None) if unparseable.
    """
    v = value.strip()
    # Strip unit suffixes (%, ppm, etc.)
    v = _re_module.sub(r"[%\s]", "", v)

    # Try range separators: –, -, ~, to
    for sep in ("–", "—", "−", "-", "~", " to "):
        if sep in v:
            parts = v.split(sep, 1)
            try:
                lo = float(parts[0].strip().lstrip("<>≤≥~ "))
                hi = float(parts[1].strip().lstrip("<>≤≥~ "))
                return (lo, hi)
            except (ValueError, IndexError):
                continue

    # Single value
    try:
        cleaned = v.lstrip("<>≤≥~ ")
        n = float(cleaned)
        return (n, n)
    except (ValueError, TypeError):
        return (None, None)


def _evaluate(req: dict, actual_value: str) -> str:
    """Return 'pass' or 'fail'. Best-effort numeric comparison.

    When the actual value is a range (e.g. '99.0%–100.5%'):
      - For >= requirements: use the LOWER bound (worst case)
      - For <= requirements: use the UPPER bound (worst case)
      - For range requirements: the actual range must overlap
    """
    op = req["operator"]
    expected = req["value"]

    # Boolean checks
    if op == "==" and isinstance(expected, bool):
        return "pass" if actual_value.lower() in ("true", "yes", "1") else "fail"

    # "in" check (list of acceptable strings)
    if op == "in" and isinstance(expected, list):
        normed = actual_value.lower().strip()
        return "pass" if any(e.lower() in normed for e in expected) else "fail"

    # Numeric comparisons — parse actual as single or range
    lo, hi = _parse_numeric_or_range(actual_value)
    if lo is None or hi is None:
        return "fail"

    if op == "range" and isinstance(expected, list):
        try:
            req_lo, req_hi = float(expected[0]), float(expected[1])
            # Actual range must fall within required range
            return "pass" if lo >= req_lo and hi <= req_hi else "fail"
        except (ValueError, IndexError):
            return "fail"

    try:
        num_expected = float(expected)
    except (ValueError, TypeError):
        return "fail"

    if op == ">=":
        # Use lower bound — worst case must still pass
        return "pass" if lo >= num_expected else "fail"
    if op == "<=":
        # Use upper bound — worst case must still pass
        return "pass" if hi <= num_expected else "fail"
    if op == "==":
        return "pass" if lo == num_expected == hi else "fail"

    return "fail"


def compare_fields(
    extracted: dict[str, "ExtractedField"],
    requirements: list[dict[str, Any]],
) -> tuple[list["ComparisonEntry"], list[str]]:
    """Compare extracted fields against requirements. Returns (comparisons, missing_fields)."""
    from .models import ComparisonEntry  # local import to avoid circularity

    comparisons: list[ComparisonEntry] = []
    missing: list[str] = []

    for req in requirements:
        field = req["field"]
        priority = req.get("priority", "major")
        required_str = _format_requirement(req)

        if field not in extracted:
            comparisons.append(ComparisonEntry(
                field=field,
                required=required_str,
                actual=None,
                verdict="missing",
                priority=priority,
                source_confidence="n/a",
            ))
            missing.append(field)
            continue

        ef = extracted[field]
        actual_val = ef.value
        sc = ef.source_confidence

        # Downgrade verdict to "fail" automatically when source_confidence is "low"
        if sc == "low":
            verdict = "fail"
        else:
            verdict = _evaluate(req, actual_val)

        unit = ef.unit or ""
        comparisons.append(ComparisonEntry(
            field=field,
            required=required_str,
            actual=f"{actual_val}{' ' + unit if unit else ''}",
            verdict=verdict,
            priority=priority,
            source_confidence=sc,
        ))

    return comparisons, missing


# ---------------------------------------------------------------------------
# 5. Determine evidence quality
# ---------------------------------------------------------------------------

def assess_evidence_quality(sources: list[FetchedSource]) -> str:
    """Classify overall evidence quality."""
    has_pdf = any(s.ok and s.content_type == "pdf" for s in sources)
    has_html = any(s.ok and s.content_type == "html" for s in sources)
    all_blocked = all(not s.ok for s in sources)

    if has_pdf:
        return "pdf_found"
    if has_html:
        return "html_only"
    if all_blocked:
        return "blocked"
    return "none"


# ---------------------------------------------------------------------------
# 6. Compute confidence score
# ---------------------------------------------------------------------------

def compute_confidence(
    comparisons: list[ComparisonEntry],
    evidence_quality: str,
) -> float:
    """Heuristic confidence score 0.0–1.0."""
    if not comparisons:
        return 0.0

    # Base from evidence quality
    eq_score = {"pdf_found": 0.3, "html_only": 0.15, "blocked": 0.0, "none": 0.0}
    score = eq_score.get(evidence_quality, 0.0)

    # Coverage: fraction of fields that are not missing
    total = len(comparisons)
    resolved = sum(1 for c in comparisons if c.verdict != "missing")
    coverage = resolved / total if total else 0.0
    score += 0.4 * coverage

    # Pass rate among resolved
    passed = sum(1 for c in comparisons if c.verdict == "pass")
    pass_rate = passed / resolved if resolved else 0.0
    score += 0.3 * pass_rate

    return round(min(score, 1.0), 2)


# ---------------------------------------------------------------------------
# 7. Main verification function (called from graph node)
# ---------------------------------------------------------------------------

def _seed_from_quality_properties(qp, ingredient: str) -> dict[str, "ExtractedField"]:
    """Convert Agent 1's QualityProperties into ExtractedField entries.

    These serve as a baseline that Agent 2's URL-fetched extraction can
    override (with higher confidence) or fill gaps for.
    """
    from .models import ExtractedField

    seed: dict[str, ExtractedField] = {}

    # Map QualityProperties attrs → canonical field names + their values
    simple_fields = {
        "purity": qp.purity,
        "form": qp.form,
        "grade": qp.grade,
        "particle_size": qp.particle_size,
        "storage_conditions": qp.storage_conditions,
        "shelf_life": qp.shelf_life,
        "gras_status": qp.gras_status,
        "origin": qp.origin,
    }
    for field_name, value in simple_fields.items():
        if value:
            seed[field_name] = ExtractedField(
                value=str(value),
                source_url=qp.product_url,
                source_confidence="medium",  # Agent 1 data is search-derived
            )

    # Boolean fields
    if qp.gmp_certified is not None:
        seed["gmp_certified"] = ExtractedField(
            value=str(qp.gmp_certified).lower(),
            source_url=qp.product_url,
            source_confidence="medium",
        )
    if qp.third_party_tested is not None:
        seed["third_party_tested"] = ExtractedField(
            value=str(qp.third_party_tested).lower(),
            source_url=qp.product_url,
            source_confidence="medium",
        )

    # List fields → join as comma-separated
    if qp.certifications:
        seed["certifications"] = ExtractedField(
            value=", ".join(qp.certifications),
            source_url=qp.product_url,
            source_confidence="medium",
        )
    if qp.iso_certifications:
        seed["iso_certifications"] = ExtractedField(
            value=", ".join(qp.iso_certifications),
            source_url=qp.product_url,
            source_confidence="medium",
        )
    if qp.pharmacopoeia_compliance:
        seed["pharmacopoeia_compliance"] = ExtractedField(
            value=", ".join(qp.pharmacopoeia_compliance),
            source_url=qp.product_url,
            source_confidence="medium",
        )

    # Check certs for kosher/halal/non_gmo booleans
    cert_lower = {c.lower() for c in (qp.certifications or [])}
    if any("kosher" in c for c in cert_lower):
        seed["kosher"] = ExtractedField(value="true", source_url=qp.product_url, source_confidence="medium")
    if any("halal" in c for c in cert_lower):
        seed["halal"] = ExtractedField(value="true", source_url=qp.product_url, source_confidence="medium")
    if any("non-gmo" in c or "non_gmo" in c for c in cert_lower):
        seed["non_gmo"] = ExtractedField(value="true", source_url=qp.product_url, source_confidence="medium")

    return seed


def verify_supplier_result(
    result: SupplierResult,
    call_with_retry,
    build_llm,
    rate_limit_delay: float,
) -> VerificationResult:
    """Full verification pipeline for a single SupplierResult."""
    ingredient = result.ingredient
    supplier = result.supplier_name

    # --- Seed with Agent 1's quality_properties ---
    qp = result.quality_properties
    seed_fields = _seed_from_quality_properties(qp, ingredient)
    if seed_fields:
        print(f"  Seeded {len(seed_fields)} field(s) from Agent 1", file=sys.stderr, flush=True)

    # Gather all URLs: search_urls + any from quality_properties
    urls = list(result.search_urls)
    for url in [qp.product_url, qp.tds_url, qp.coa_url, qp.sds_url]:
        if url and url not in urls:
            urls.append(url)

    print(f"  Fetching {len(urls)} URL(s)...", file=sys.stderr, flush=True)
    sources = fetch_all_urls(urls)

    ok_count = sum(1 for s in sources if s.ok)
    print(f"  {ok_count}/{len(sources)} accessible", file=sys.stderr, flush=True)

    # Extract fields via Gemini from fetched URLs
    print(f"  Extracting fields with Gemini...", file=sys.stderr, flush=True)
    raw_extracted = extract_fields_with_gemini(
        ingredient, supplier, sources, call_with_retry, build_llm, rate_limit_delay,
    )
    print(f"  Extracted {len(raw_extracted)} raw field(s) from URLs", file=sys.stderr, flush=True)

    # Normalize field names to canonical requirement names
    normalized = normalize_extracted_fields(raw_extracted, ingredient)
    newly_mapped = set(normalized) - set(raw_extracted)
    if newly_mapped:
        print(f"  Field normalization mapped: {newly_mapped}", file=sys.stderr, flush=True)

    # Merge: URL-extracted fields (normalized) take priority over Agent 1 seed.
    # Agent 1 fields fill gaps where URL extraction found nothing.
    confidence_rank = {"high": 0, "medium": 1, "low": 2}
    extracted = dict(seed_fields)  # start with seed
    for fname, ffield in normalized.items():
        if fname not in extracted:
            extracted[fname] = ffield
        else:
            # URL-extracted with higher or equal confidence wins over seed
            existing_rank = confidence_rank.get(extracted[fname].source_confidence, 1)
            new_rank = confidence_rank.get(ffield.source_confidence, 1)
            if new_rank <= existing_rank:
                extracted[fname] = ffield

    print(f"  Total merged fields: {len(extracted)}", file=sys.stderr, flush=True)

    # Load requirements and compare
    requirements = load_requirements(ingredient)
    comparisons, missing_evidence = compare_fields(extracted, requirements)

    evidence_quality = assess_evidence_quality(sources)
    confidence = compute_confidence(comparisons, evidence_quality)

    accessible_urls = [s.url for s in sources if s.ok]

    return VerificationResult(
        supplier_name=supplier,
        ingredient=ingredient,
        extracted_fields=extracted,
        comparison=comparisons,
        missing_evidence=missing_evidence,
        evidence_quality=evidence_quality,
        confidence_score=confidence,
        sources=accessible_urls,
    )

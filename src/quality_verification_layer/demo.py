#!/usr/bin/env python3
"""
Agnes Quality Verification Layer - Live Demo
==============================================
For each ingredient:
1. Loads DB suppliers + discovers 10 competitors via Layer 2
2. Runs quality verification (search evidence, extract via Gemini, verify)
3. Shows only HIGH-confidence suppliers
4. Downloads PDFs to demo_output/

Usage:
    python demo.py                    # all 3 ingredients
    python demo.py -i vitc            # just Vitamin C
    python demo.py -i whey            # just Whey Protein Isolate
    python demo.py -i omega           # just Omega-3 Fish Oil
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from functools import partial
from pathlib import Path
from urllib.parse import urlparse

import httpx

# Temporary status line (overwrites itself) for progress messages
_CLEAR = "\033[2K\r"
def _status(msg: str) -> None:
    """Temporary single-line progress that overwrites itself."""
    sys.stdout.write(f"{_CLEAR}  {DIM}{msg[:100]}{RESET}")
    sys.stdout.flush()
def _status_clear() -> None:
    sys.stdout.write(_CLEAR)
    sys.stdout.flush()

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Add sibling layers to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "competitor_layer"))
# requirement_layer uses "from src.requirement_layer..." imports, so add repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from quality_verification_layer.config import load_config, QualityVerificationConfig
from quality_verification_layer.runner import run_quality_verification
from quality_verification_layer.schemas import (
    CandidateSupplier,
    IngredientRef,
    QualityVerificationInput,
    QualityVerificationOutput,
    RequirementInput,
    SupplierRef,
)
from demo_ui import (
    console,
    show_header,
    show_ingredient_header,
    show_layer1_results,
    show_layer2_results,
    show_layer3_results,
    show_final_ranking,
    show_footer,
)

# ── ANSI ─────────────────────────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
WHITE = "\033[97m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"

STATUS_STYLE = {
    "pass": (GREEN, "+"),
    "fail": (RED, "X"),
    "unknown": (YELLOW, "?"),
    "partial": (CYAN, "~"),
}

OVERALL_STYLE = {
    "verified": GREEN,
    "verified_with_gaps": YELLOW,
    "failed_hard_requirements": RED,
    "insufficient_evidence": DIM,
    "processing_error": RED,
}

# ── Paths ────────────────────────────────────────────────────────────────────

REQ_DIR = Path(__file__).resolve().parents[2] / "data" / "requirements"
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "db.sqlite"
DEMO_OUTPUT = Path(__file__).resolve().parent / "demo_output"
DEMO_EVIDENCE = Path(__file__).resolve().parent / "demo_evidence"

# ── Requirements via Layer 1 ─────────────────────────────────────────────────


def _get_canonical_fields() -> set[str]:
    """Get the set of canonical field names that Layer 3 can verify."""
    from quality_verification_layer.normalization import CANONICAL_FIELD_MAP
    return set(CANONICAL_FIELD_MAP.values())


def _generate_requirements(ingredient: IngredientRef) -> list[RequirementInput]:
    """Call Layer 1 (requirements layer) to generate requirements via Gemini.

    Post-filters to only keep requirements whose field_name matches
    Layer 3's canonical field vocabulary — so every requirement can be verified.
    """
    try:
        from src.requirement_layer.runner import run as run_layer1

        _status(f"Layer 1: Generating requirements for {ingredient.canonical_name}...")

        # Suppress Layer 1's stdout JSON dump
        import io
        _old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            result = run_layer1(
                input_data={
                    "schema_version": "1.0",
                    "ingredient": {
                        "ingredient_id": ingredient.ingredient_id,
                        "canonical_name": ingredient.canonical_name,
                        "aliases": ingredient.aliases,
                    },
                    "context": {"product_category": "food ingredient"},
                },
                model="gemini-2.5-flash",
            )
        finally:
            sys.stdout = _old_stdout

        canonical_fields = _get_canonical_fields()
        from quality_verification_layer.normalization import normalize_field_name

        raw_reqs = result.get("requirements", [])
        reqs = []
        dropped = []
        for r in raw_reqs:
            # Normalize Layer 1 field names to Layer 3 canonical names
            raw_field = r["field_name"]
            canonical = normalize_field_name(raw_field, ingredient.canonical_name)

            if canonical not in canonical_fields:
                dropped.append(raw_field)
                continue

            req = RequirementInput(
                requirement_id=r.get("requirement_id", ""),
                field_name=canonical,
                rule_type=r["rule_type"],
                operator=r.get("operator", ""),
                priority="hard" if r.get("priority") == "hard" else "soft",
                unit=r.get("unit"),
                source_reference=r.get("source_reference"),
                min_value=r.get("min_value"),
                max_value=r.get("max_value"),
                allowed_values=r.get("allowed_values"),
                required=r.get("required"),
                reference_text=r.get("reference_text"),
            )
            reqs.append(req)

        # Deduplicate: when multiple requirements map to the same canonical field,
        # keep the strictest (hard > soft, lower max_value wins for maximums)
        seen_fields: dict[str, RequirementInput] = {}
        deduped: list[RequirementInput] = []
        for req in reqs:
            key = (req.field_name, req.rule_type)
            if key not in seen_fields:
                seen_fields[key] = req
                deduped.append(req)
            else:
                existing = seen_fields[key]
                # Keep hard over soft
                if req.priority == "hard" and existing.priority != "hard":
                    deduped.remove(existing)
                    seen_fields[key] = req
                    deduped.append(req)
                # For same priority + same rule type: keep stricter value
                elif req.max_value is not None and existing.max_value is not None:
                    if req.max_value < existing.max_value:
                        deduped.remove(existing)
                        seen_fields[key] = req
                        deduped.append(req)

        merged = len(reqs) - len(deduped)
        reqs = deduped

        _status_clear()
        hard = sum(1 for r in reqs if r.priority == "hard")
        msg = f"  {CYAN}Layer 1: {len(reqs)} verifiable requirements ({hard} hard, {len(reqs) - hard} soft)"
        if dropped:
            msg += f", dropped {len(dropped)} unsupported"
        if merged:
            msg += f", merged {merged} duplicates"
        msg += f"{RESET}"
        print(msg, flush=True)
        return reqs

    except Exception as e:
        _status_clear()
        print(f"  {YELLOW}Layer 1 failed ({e}), falling back to static requirements{RESET}", flush=True)
        return _load_requirements_fallback(ingredient)


def _load_requirements_fallback(ingredient: IngredientRef) -> list[RequirementInput]:
    """Fallback: load requirements from hardcoded JSON files."""
    slug = ingredient.canonical_name.lower().replace(" ", "-")
    path = REQ_DIR / f"{slug}.json"
    if not path.exists():
        # Try common aliases
        for alias in ingredient.aliases:
            alt = alias.lower().replace(" ", "-")
            alt_path = REQ_DIR / f"{alt}.json"
            if alt_path.exists():
                path = alt_path
                break

    if not path.exists():
        _status_clear()
        print(f"  {YELLOW}No fallback requirements file found for {ingredient.canonical_name}{RESET}", flush=True)
        return []

    data = json.loads(path.read_text())
    reqs = []
    for i, r in enumerate(data["requirements"], 1):
        op = r["operator"]
        rule_type = {
            "<=": "maximum", ">=": "minimum", "in": "enum_match",
            "==": "boolean_required", "range": "range",
        }.get(op, "free_text_reference")

        req = RequirementInput(
            requirement_id=f"REQ-{i:03d}",
            field_name=r["field"],
            rule_type=rule_type,
            operator=op,
            priority="hard" if r.get("priority") == "critical" else "soft",
            unit=r.get("unit"),
        )
        if rule_type == "range" and isinstance(r["value"], list):
            req.min_value = float(r["value"][0])
            req.max_value = float(r["value"][1])
        elif rule_type == "minimum":
            req.min_value = float(r["value"])
        elif rule_type == "maximum":
            req.max_value = float(r["value"])
        elif rule_type == "enum_match":
            req.allowed_values = r["value"]
        elif rule_type == "boolean_required":
            req.required = r["value"]
        reqs.append(req)
    return reqs


# ── DB suppliers ─────────────────────────────────────────────────────────────


def _get_db_suppliers(ingredient_slug: str) -> list[CandidateSupplier]:
    """Load suppliers from the Spherecast database."""
    import sqlite3

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT DISTINCT s.Id AS supplier_id, s.Name AS supplier_name
            FROM Supplier s
            JOIN Supplier_Product sp ON s.Id = sp.SupplierId
            JOIN Product p ON sp.ProductId = p.Id
            WHERE p.Type = 'raw-material' AND p.SKU LIKE ?
            ORDER BY s.Name
            """,
            (f"%{ingredient_slug}%",),
        ).fetchall()

    return [
        CandidateSupplier(
            supplier=SupplierRef(
                supplier_id=f"DB-{r['supplier_id']}",
                supplier_name=r["supplier_name"],
            ),
        )
        for r in rows
    ]


# ── Competitor layer integration ─────────────────────────────────────────────


def _get_competitors(ingredient: IngredientRef, max_candidates: int = 10) -> list[CandidateSupplier]:
    """Run competitor layer to discover additional suppliers."""
    try:
        from competitor_layer.config import CompetitorConfig
        from competitor_layer.runner import run_competitor_layer
        from competitor_layer.schemas import (
            CompetitorInput,
            IngredientRef as CLIngredient,
            RuntimeConfig as CLRuntime,
            SearchContext as CLContext,
        )

        import os
        gemini_key = os.environ.get("GEMINI_API_KEY")

        cl_config = CompetitorConfig(
            gemini_api_key=gemini_key,
            gemini_model="gemini-2.5-flash",
            max_candidates=max_candidates,
            ranking_enabled=True,
            GEMINI_API_KEY=None,
            google_cse_id=None,
            search_engine="duckduckgo",
            search_results_per_query=5,
            search_delay=1.0,
        )

        cl_input = CompetitorInput(
            ingredient=CLIngredient(
                ingredient_id=ingredient.ingredient_id,
                canonical_name=ingredient.canonical_name,
                aliases=ingredient.aliases,
            ),
            context=CLContext(region="EU"),
            runtime=CLRuntime(max_candidates=max_candidates, ranking_enabled=True),
        )

        _status(f"Layer 2: Discovering competitors for {ingredient.canonical_name}...")

        t0 = time.monotonic()
        cl_output = run_competitor_layer(cl_input, cl_config)
        elapsed = time.monotonic() - t0

        _status_clear()

        competitors = []
        for c in cl_output.candidates:
            source_urls = [o.source_url for o in c.matched_offers if o.source_url]
            competitors.append(
                CandidateSupplier(
                    supplier=SupplierRef(
                        supplier_id=c.supplier.supplier_id,
                        supplier_name=c.supplier.supplier_name,
                        country=c.supplier.country,
                        website=c.supplier.website,
                    ),
                    candidate_confidence=c.candidate_confidence,
                    source_urls=source_urls,
                )
            )

        # competitors list already populated above

        return competitors

    except Exception as e:
        _status_clear()
        print(f"  {YELLOW}Competitor layer unavailable: {e}{RESET}", flush=True)
        return []


# ── Cache ────────────────────────────────────────────────────────────────────

CACHE_DIR = DEMO_OUTPUT / ".cache"


def _cache_path(slug: str, stage: str) -> Path:
    return CACHE_DIR / slug / f"{stage}.json"


def _save_cache(slug: str, stage: str, data):
    """Save intermediate result to cache."""
    path = _cache_path(slug, stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump_json"):
        path.write_text(data.model_dump_json(indent=2))
    else:
        path.write_text(json.dumps(data, default=str, indent=2))


def _load_cache(slug: str, stage: str):
    """Load cached intermediate result. Returns None if not found."""
    path = _cache_path(slug, stage)
    if path.exists():
        return json.loads(path.read_text())
    return None


# ── PDF downloader ───────────────────────────────────────────────────────────


def _sanitize(name: str) -> str:
    return re.sub(r"[^\w\-.]", "_", name).strip("_")[:60]


def download_pdfs(output: QualityVerificationOutput, ingredient_name: str) -> list[Path]:
    """Download any PDF evidence found during verification."""
    folder = DEMO_OUTPUT / _sanitize(ingredient_name)
    downloaded = []

    pdf_urls = []
    for sa in output.supplier_assessments:
        for ei in sa.evidence_items:
            if ei.status == "retrieved" and ei.source_url.lower().endswith(".pdf"):
                pdf_urls.append((sa.supplier_id, ei.source_url))

    if not pdf_urls:
        return downloaded

    folder.mkdir(parents=True, exist_ok=True)

    for supplier_id, url in pdf_urls:
        try:
            url_basename = Path(urlparse(url).path).name or "document.pdf"
            filename = f"{_sanitize(supplier_id)}_{url_basename}"
            dest = folder / filename

            if dest.exists():
                downloaded.append(dest)
                continue

            resp = httpx.get(url, timeout=20.0, follow_redirects=True)
            resp.raise_for_status()

            if b"%PDF" in resp.content[:10] or "pdf" in resp.headers.get("content-type", "").lower():
                dest.write_bytes(resp.content)
                downloaded.append(dest)
        except Exception:
            pass

    return downloaded


# ── Ingredient lookup ────────────────────────────────────────────────────────

# Preset shortcuts for convenience
PRESETS = {
    "vitc": ("Ascorbic Acid", ["Vitamin C", "L-Ascorbic Acid", "E300"]),
    "whey": ("Whey Protein Isolate", ["WPI", "Whey Isolate"]),
    "omega": ("Omega-3 Fish Oil", ["Omega-3", "EPA/DHA", "Fish Oil Concentrate"]),
}


def _find_ingredient_in_db(name: str) -> tuple[str, list[dict]]:
    """Search the database for an ingredient by name.

    Returns (matched_slug, suppliers_list).
    Tries exact slug match first, then substring match.
    """
    import sqlite3

    slug = name.lower().replace(" ", "-")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # Get all distinct ingredient slugs from SKUs
        all_skus = conn.execute(
            "SELECT DISTINCT SKU FROM Product WHERE Type = 'raw-material'"
        ).fetchall()

        # Extract ingredient names from SKUs (format: RM-C{id}-{ingredient}-{hash})
        ingredient_slugs: set[str] = set()
        for row in all_skus:
            parts = row["SKU"].split("-", 2)
            if len(parts) >= 3:
                # Remove the trailing hash
                ingredient_part = "-".join(parts[2].rsplit("-", 1)[:-1])
                if ingredient_part:
                    ingredient_slugs.add(ingredient_part)

        # Exact match
        if slug in ingredient_slugs:
            matched = slug
        else:
            # Substring match
            matches = [s for s in sorted(ingredient_slugs) if slug in s or s in slug]
            if matches:
                matched = matches[0]
            else:
                # Broader search: any word overlap
                words = set(slug.split("-"))
                matches = [
                    s for s in sorted(ingredient_slugs)
                    if words & set(s.split("-"))
                ]
                matched = matches[0] if matches else None

        if not matched:
            return slug, []

        # Get suppliers for this ingredient
        suppliers = conn.execute(
            """
            SELECT DISTINCT s.Id AS supplier_id, s.Name AS supplier_name
            FROM Supplier s
            JOIN Supplier_Product sp ON s.Id = sp.SupplierId
            JOIN Product p ON sp.ProductId = p.Id
            WHERE p.Type = 'raw-material' AND p.SKU LIKE ?
            ORDER BY s.Name
            """,
            (f"%{matched}%",),
        ).fetchall()

        return matched, [dict(r) for r in suppliers]


def _list_available_ingredients():
    """List all unique ingredients in the database."""
    import sqlite3

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT DISTINCT SKU FROM Product WHERE Type = 'raw-material' ORDER BY SKU"
        ).fetchall()

    slugs: set[str] = set()
    for row in rows:
        parts = row[0].split("-", 2)
        if len(parts) >= 3:
            ingredient_part = "-".join(parts[2].rsplit("-", 1)[:-1])
            if ingredient_part:
                slugs.add(ingredient_part)

    return sorted(slugs)


def _build_ingredient_ref(name: str, slug: str) -> IngredientRef:
    """Build an IngredientRef from a name and slug."""
    canonical = name.replace("-", " ").title()
    ing_id = "ING-" + slug.upper().replace("-", "-")
    return IngredientRef(
        ingredient_id=ing_id,
        canonical_name=canonical,
        aliases=[],
    )


# ── Display (old ANSI helpers kept for progress output during processing) ────


# ── Supplier ranking (requirements-driven) ──────────────────────────────────


def _rank_suppliers(
    assessments: list,
    requirements: list,
) -> list[tuple]:
    """Rank suppliers by requirements satisfaction score.

    Score = (hard_pass_ratio * 0.70) + (soft_pass_ratio * 0.30)

    - partial counts as pass (value meets requirement, confidence is a data quality signal)
    - unknown is neutral (missing data is a search gap, not a supplier flaw)
    - only fail counts against the score

    Returns list of (assessment, score, details_dict) sorted best-first.
    """
    req_priority = {}
    for r in requirements:
        p = r.priority if isinstance(r.priority, str) else r.priority.value
        req_priority[r.requirement_id] = p

    scored = []
    for sa in assessments:
        if not sa.extracted_attributes:
            continue

        hard_total = hard_pass = hard_fail = 0
        soft_total = soft_pass = soft_fail = 0

        for vr in sa.verification_results:
            priority = req_priority.get(vr.requirement_id, "hard")
            status = vr.status if isinstance(vr.status, str) else vr.status.value

            if priority == "hard":
                hard_total += 1
                if status in ("pass", "partial"):
                    hard_pass += 1
                elif status == "fail":
                    hard_fail += 1
            else:
                soft_total += 1
                if status in ("pass", "partial"):
                    soft_pass += 1
                elif status == "fail":
                    soft_fail += 1

        hard_score = hard_pass / hard_total if hard_total else 0.0
        soft_score = soft_pass / soft_total if soft_total else 0.0
        total_score = hard_score * 0.70 + soft_score * 0.30

        hard_unknown = hard_total - hard_pass - hard_fail
        soft_unknown = soft_total - soft_pass - soft_fail

        details = {
            "hard": f"{hard_pass}/{hard_total}",
            "soft": f"{soft_pass}/{soft_total}",
            "fails": hard_fail + soft_fail,
            "unknowns": hard_unknown + soft_unknown,
        }
        scored.append((sa, round(total_score, 3), details))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored




# ── Sample demo (local TDS files, no network) ───────────────────────────────


def _run_sample_demo(config):
    """Run a fully offline demo using local sample TDS files."""
    from quality_verification_layer.schemas import QualityVerificationOutput

    show_header()
    console.print(f"  [bold yellow]SAMPLE MODE: using local TDS evidence files (no network)[/]")
    console.print(f"  [dim]Gemini: {config.gemini_model}[/]")
    console.print()

    ingredient = IngredientRef(
        ingredient_id="ING-ASCORBIC-ACID",
        canonical_name="Ascorbic Acid",
        aliases=["Vitamin C", "L-Ascorbic Acid"],
    )

    # Load sample TDS files as evidence
    evidence_files = sorted(DEMO_EVIDENCE.glob("*.txt"))
    if not evidence_files:
        console.print(f"  [red]No sample evidence files found in {DEMO_EVIDENCE}[/]")
        return

    # Build suppliers from evidence files
    suppliers = []
    for i, f in enumerate(evidence_files, 1):
        # Extract supplier name from filename (e.g. ascorbic_acid_tds_supplier_a.txt → Supplier A)
        name_parts = f.stem.split("_supplier_")
        supplier_name = f"Sample Supplier {name_parts[-1].upper()}" if len(name_parts) > 1 else f"Supplier {i}"

        suppliers.append(CandidateSupplier(
            supplier=SupplierRef(
                supplier_id=f"SAMPLE-{i:03d}",
                supplier_name=supplier_name,
            ),
            source_urls=[f"file://{f}"],
        ))

    # Generate requirements via Layer 1
    requirements = _generate_requirements(ingredient)
    if not requirements:
        console.print(f"  [red]No requirements generated[/]")
        return

    show_ingredient_header(ingredient.canonical_name, 0, len(suppliers), 1, 1)
    show_layer1_results(requirements, ingredient.canonical_name)
    show_layer2_results([], suppliers, ingredient.canonical_name)

    # Run verification with local evidence
    # Override retrieval: inject local file content directly
    from quality_verification_layer.id_generator import QualityIdGenerator
    from quality_verification_layer.classification import classify_evidence_items
    from quality_verification_layer.extraction import extract_attributes_with_gemini
    from quality_verification_layer.normalization import normalize_attributes, resolve_conflicts
    from quality_verification_layer.verification import verify_requirements
    from quality_verification_layer.aggregation import (
        compute_coverage_summary, compute_overall_status, compute_overall_confidence,
    )
    from quality_verification_layer.retrieval import FetchedSource
    from quality_verification_layer.schemas import (
        EvidenceItem, EvidenceStatus, SupplierAssessment, SupplierAssessmentStatus,
    )
    from quality_verification_layer.gemini_wrapper import create_gemini_client
    from datetime import datetime, timezone

    gemini = create_gemini_client(config.gemini_api_key, config.gemini_model)
    now = datetime.now(timezone.utc).isoformat()

    assessments = []
    for i, (supplier, evidence_file) in enumerate(zip(suppliers, evidence_files), 1):
        sid = supplier.supplier.supplier_id
        sname = supplier.supplier.supplier_name
        print(f"  [{i}/{len(suppliers)}] Verifying {sname}...", flush=True)

        id_gen = QualityIdGenerator(sid)
        text = evidence_file.read_text()

        # Build evidence + source
        evid_id = id_gen.next_evidence_id()
        evidence_items = [EvidenceItem(
            evidence_id=evid_id,
            source_type="tds",
            source_url=str(evidence_file),
            title=evidence_file.name,
            status=EvidenceStatus.retrieved,
            retrieved_at=now,
        )]
        fetched_sources = [FetchedSource(
            url=str(evidence_file),
            content_type="text",
            text=text,
            ok=True,
            evidence_id=evid_id,
        )]

        # Classify
        evidence_items = classify_evidence_items(fetched_sources, evidence_items, ingredient.canonical_name)

        # Extract via Gemini
        req_fields = [r.field_name for r in requirements]
        print(f"       Extracting via Gemini...", flush=True)
        attributes = extract_attributes_with_gemini(
            ingredient.canonical_name, sname, fetched_sources,
            id_gen, gemini, config.rate_limit_delay, req_fields,
        ) if gemini else []

        # Normalize + resolve
        attributes = normalize_attributes(attributes, ingredient.canonical_name)
        attributes, conflict_notes = resolve_conflicts(attributes, evidence_items)

        # Verify
        verification_results = verify_requirements(attributes, requirements, id_gen)

        # Aggregate
        coverage = compute_coverage_summary(verification_results, requirements)
        overall_status = compute_overall_status(coverage, evidence_items)
        overall_confidence = compute_overall_confidence(evidence_items, attributes)

        notes = list(conflict_notes)
        missing = [vr.field_name for vr in verification_results
                   if (vr.status if isinstance(vr.status, str) else vr.status.value) == "unknown"]
        if missing:
            notes.append(f"No values found for: {', '.join(missing)}")

        assessments.append(SupplierAssessment(
            supplier_id=sid,
            evidence_items=evidence_items,
            extracted_attributes=attributes,
            verification_results=verification_results,
            coverage_summary=coverage,
            overall_evidence_confidence=overall_confidence,
            overall_status=overall_status,
            notes=notes,
        ))

    output = QualityVerificationOutput(
        ingredient_id=ingredient.ingredient_id,
        supplier_assessments=assessments,
    )

    supplier_names = {s.supplier.supplier_id: s.supplier.supplier_name for s in suppliers}

    show_layer3_results(output, requirements, names=supplier_names)

    ranked = _rank_suppliers(output.supplier_assessments, requirements)
    show_final_ranking(ranked, ingredient.canonical_name, names=supplier_names)

    show_footer(0, len(assessments), len(assessments), DEMO_OUTPUT)


# ── Main ─────────────────────────────────────────────────────────────────────


def _resolve_ingredients(args) -> list[dict]:
    """Resolve ingredient arguments to a list of {label, slug, ingredient} dicts."""
    ingredients = []

    if args.ingredient:
        for name in args.ingredient:
            # Check presets first
            if name in PRESETS:
                canonical, aliases = PRESETS[name]
                slug = canonical.lower().replace(" ", "-")
                ingredients.append({
                    "label": canonical,
                    "slug": slug,
                    "ingredient": IngredientRef(
                        ingredient_id="ING-" + slug.upper().replace("-", "-"),
                        canonical_name=canonical,
                        aliases=aliases,
                    ),
                })
            else:
                # Look up in database
                slug, suppliers = _find_ingredient_in_db(name)
                if not suppliers:
                    console.print(f"  [red]Ingredient '{name}' not found in database.[/]")
                    console.print(f"  [dim]Available ingredients:[/]")
                    for ing in _list_available_ingredients():
                        console.print(f"    [dim]{ing}[/]")
                    sys.exit(1)

                canonical = slug.replace("-", " ").title()
                ingredients.append({
                    "label": canonical,
                    "slug": slug,
                    "ingredient": _build_ingredient_ref(name, slug),
                })
    else:
        # Default: all 3 presets
        for key, (canonical, aliases) in PRESETS.items():
            slug = canonical.lower().replace(" ", "-")
            ingredients.append({
                "label": canonical,
                "slug": slug,
                "ingredient": IngredientRef(
                    ingredient_id="ING-" + slug.upper().replace("-", "-"),
                    canonical_name=canonical,
                    aliases=aliases,
                ),
            })

    return ingredients


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Agnes Quality Verification Demo",
        epilog="Examples:\n"
               "  python demo.py -i vitc                    # Vitamin C preset\n"
               "  python demo.py -i vitamin-d3-cholecalciferol  # any DB ingredient\n"
               "  python demo.py -i calcium-citrate magnesium-stearate  # multiple\n"
               "  python demo.py --list                      # list all DB ingredients\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--ingredient", "-i",
        nargs="+",
        metavar="NAME",
        help="Ingredient name(s): preset (vitc/whey/omega) or DB slug (e.g. calcium-citrate)",
    )
    parser.add_argument(
        "--no-competitors",
        action="store_true",
        help="Skip competitor discovery (DB suppliers only)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Reuse cached results from a previous run (skip search + Gemini)",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Run with sample TDS evidence files (no network, guaranteed results)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available ingredients in the database",
    )
    args = parser.parse_args()

    if args.list:
        console.print("[bold]Available ingredients in database:[/]\n")
        for ing in _list_available_ingredients():
            console.print(f"  {ing}")
        console.print(f"\n[dim]Usage: python demo.py -i {'{ingredient-name}'}[/]")
        sys.exit(0)

    # Suppress noisy library logging
    import logging
    logging.disable(logging.WARNING)

    config = load_config()
    if not config.gemini_api_key:
        print(f"{RED}Error: GEMINI_API_KEY not set in .env{RESET}")
        sys.exit(1)

    from dataclasses import asdict
    d = asdict(config)
    d["gemini_model"] = "gemini-2.5-flash"
    d["search_delay"] = 1.5
    d["search_results_per_query"] = 4
    d["max_evidence_per_supplier"] = 8
    d["rate_limit_delay"] = 2.0
    config = QualityVerificationConfig(**d)

    selected = _resolve_ingredients(args)
    fast_mode = args.fast

    if args.sample:
        _run_sample_demo(config)
        return

    show_header()
    if fast_mode:
        console.print(f"  [bold yellow]FAST MODE: reusing cached results from previous run[/]")
    console.print(f"  [dim]Gemini: {config.gemini_model}[/]")
    console.print(f"  [dim]Evidence search: DuckDuckGo ({config.search_results_per_query} results/query)[/]")
    console.print(f"  [dim]Ingredients: {', '.join(s['label'] for s in selected)}[/]")
    console.print()

    total_shown = 0
    total_all = 0
    t_start = time.monotonic()

    for idx, spec in enumerate(selected, 1):
        ingredient = spec["ingredient"]
        db_slug = spec["slug"]

        # ── Layer 1: Generate requirements ──
        cached_reqs = _load_cache(db_slug, "requirements") if fast_mode else None
        if cached_reqs:
            requirements = [RequirementInput(**r) for r in cached_reqs]
            console.print(f"  [dim]Layer 1: loaded {len(requirements)} cached requirements[/]")
        else:
            requirements = _generate_requirements(ingredient)
            _save_cache(db_slug, "requirements", [r.model_dump() for r in requirements])

        # ── Layer 2: Gather suppliers ──
        cached_suppliers = _load_cache(db_slug, "suppliers") if fast_mode else None
        if cached_suppliers:
            db_suppliers = [CandidateSupplier(**s) for s in cached_suppliers["db"]]
            competitors = [CandidateSupplier(**s) for s in cached_suppliers["competitors"]]
            console.print(f"  [dim]Layer 2: loaded {len(db_suppliers)} DB + {len(competitors)} competitors from cache[/]")
        else:
            db_suppliers = _get_db_suppliers(db_slug)
            _status(f"Found {len(db_suppliers)} DB suppliers")

            competitors = []
            if not args.no_competitors:
                competitors = _get_competitors(ingredient, max_candidates=10)
                _status(f"Found {len(competitors)} competitors")

            _save_cache(db_slug, "suppliers", {
                "db": [s.model_dump() for s in db_suppliers],
                "competitors": [s.model_dump() for s in competitors],
            })

        # Deduplicate
        seen_names: set = set()
        all_suppliers: list[CandidateSupplier] = []
        for s in db_suppliers + competitors:
            name_key = s.supplier.supplier_name.lower()
            if name_key not in seen_names:
                seen_names.add(name_key)
                all_suppliers.append(s)

        show_ingredient_header(
            spec["label"], len(db_suppliers), len(competitors), idx, len(selected)
        )

        # Show Layer 1 results
        show_layer1_results(requirements, ingredient.canonical_name)

        # Show Layer 2 results
        show_layer2_results(competitors, db_suppliers, ingredient.canonical_name)

        # ── Layer 3: Quality verification ──
        from quality_verification_layer.schemas import QualityVerificationOutput

        cached_output = _load_cache(db_slug, "verification") if fast_mode else None
        if cached_output:
            output = QualityVerificationOutput.model_validate(cached_output)
            elapsed = 0
            console.print(f"  [dim]Layer 3: loaded {len(output.supplier_assessments)} cached assessments[/]")
        else:
            qv_input = QualityVerificationInput(
                ingredient=ingredient,
                requirements=requirements,
                candidate_suppliers=all_suppliers,
            )

            _status(f"Layer 3: Verifying {len(all_suppliers)} suppliers...")
            t0 = time.monotonic()
            output = run_quality_verification(qv_input, config)
            elapsed = time.monotonic() - t0
            _status_clear()

            _save_cache(db_slug, "verification", output.model_dump())

        # Download PDFs (skip in fast mode — already downloaded)
        if not fast_mode:
            pdfs = download_pdfs(output, ingredient.canonical_name)
            if pdfs:
                console.print(f"  [green]Downloaded {len(pdfs)} PDF(s):[/]")
                for p in pdfs:
                    size_kb = p.stat().st_size / 1024
                    console.print(f"    [green]>[/] {p.name} [dim]({size_kb:.0f} KB)[/]")
                console.print()

        total_all += len(output.supplier_assessments)
        total_shown += len([
            sa for sa in output.supplier_assessments
            if sa.overall_status not in ("processing_error", "insufficient_evidence")
        ])

        # Build supplier id → name map for display
        supplier_names = {
            s.supplier.supplier_id: s.supplier.supplier_name
            for s in all_suppliers
        }

        # Filter requirements to only fields where at least one supplier has data
        available_fields: set[str] = set()
        for sa in output.supplier_assessments:
            for attr in sa.extracted_attributes:
                available_fields.add(attr.field_name)

        verifiable_reqs = [r for r in requirements if r.field_name in available_fields]
        dropped_reqs = len(requirements) - len(verifiable_reqs)
        if dropped_reqs:
            console.print(
                f"  [dim]Filtered to {len(verifiable_reqs)} verifiable requirements "
                f"(dropped {dropped_reqs} with no evidence across any supplier)[/]"
            )

        # Re-run verification with filtered requirements for each supplier
        from quality_verification_layer.id_generator import QualityIdGenerator
        from quality_verification_layer.verification import verify_requirements
        from quality_verification_layer.aggregation import (
            compute_coverage_summary, compute_overall_status, compute_overall_confidence,
        )

        for sa in output.supplier_assessments:
            if not sa.extracted_attributes:
                continue
            id_gen = QualityIdGenerator(sa.supplier_id)
            sa.verification_results = verify_requirements(
                sa.extracted_attributes, verifiable_reqs, id_gen,
            )
            sa.coverage_summary = compute_coverage_summary(
                sa.verification_results, verifiable_reqs,
            )
            sa.overall_status = compute_overall_status(
                sa.coverage_summary, sa.evidence_items,
            )
            sa.overall_evidence_confidence = compute_overall_confidence(
                sa.evidence_items, sa.extracted_attributes,
            )
            # Update notes
            missing = [
                vr.field_name for vr in sa.verification_results
                if (vr.status if isinstance(vr.status, str) else vr.status.value) == "unknown"
            ]
            sa.notes = [n for n in sa.notes if not n.startswith("No values found")]
            if missing:
                sa.notes.append(f"No values found for: {', '.join(missing)}")

        # Show Layer 3 results (all suppliers)
        show_layer3_results(output, verifiable_reqs, names=supplier_names)

        # Show final ranking
        ranked = _rank_suppliers(output.supplier_assessments, verifiable_reqs)
        show_final_ranking(ranked, ingredient.canonical_name, names=supplier_names)

        if elapsed:
            console.print(f"  [dim]Completed in {elapsed:.0f}s[/]")
        else:
            console.print(f"  [dim]Completed (from cache)[/]")
        console.print()

    total_time = time.monotonic() - t_start
    show_footer(total_time, total_shown, total_all, DEMO_OUTPUT)


if __name__ == "__main__":
    main()

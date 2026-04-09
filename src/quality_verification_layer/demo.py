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

# Force unbuffered output so progress is visible immediately
print = partial(print, flush=True)

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Also add competitor_layer to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "competitor_layer"))

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

# ── Requirements loader ─────────────────────────────────────────────────────


def _load_requirements(name: str) -> list[RequirementInput]:
    path = REQ_DIR / f"{name}.json"
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
            google_api_key=None,
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

        print(f"  {CYAN}Layer 2: Discovering competitors for {ingredient.canonical_name}...{RESET}")
        print(f"  {DIM}  Search engine: DuckDuckGo | Gemini: {cl_config.gemini_model} | Max candidates: {max_candidates}{RESET}")

        t0 = time.monotonic()
        cl_output = run_competitor_layer(cl_input, cl_config)
        elapsed = time.monotonic() - t0

        print(f"  {DIM}  Queries used: {len(cl_output.search_summary.queries_used)}{RESET}")
        print(f"  {DIM}  Raw results: {cl_output.stats.raw_results_seen} | Deduped: {cl_output.stats.deduped_suppliers} | Returned: {cl_output.stats.returned_candidates}{RESET}")

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

        print(f"  {CYAN}Layer 2: Found {len(competitors)} competitors in {elapsed:.0f}s:{RESET}")
        for comp in competitors:
            conf_color = GREEN if comp.candidate_confidence == "high" else (YELLOW if comp.candidate_confidence == "medium" else DIM)
            country = comp.supplier.country or "?"
            urls_count = len(comp.source_urls)
            print(f"    {conf_color}[{comp.candidate_confidence}]{RESET} {comp.supplier.supplier_name} ({country}) — {urls_count} URL(s)")
        print()

        return competitors

    except Exception as e:
        print(f"  {YELLOW}Competitor layer unavailable: {e}{RESET}")
        return []


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


# ── Ingredient definitions ───────────────────────────────────────────────────

INGREDIENT_SPECS = {
    "vitc": {
        "label": "Vitamin C (Ascorbic Acid)",
        "req_file": "vitamin-c",
        "db_slug": "ascorbic-acid",
        "ingredient": IngredientRef(
            ingredient_id="ING-ASCORBIC-ACID",
            canonical_name="Ascorbic Acid",
            aliases=["Vitamin C", "L-Ascorbic Acid", "E300"],
        ),
    },
    "whey": {
        "label": "Whey Protein Isolate",
        "req_file": "whey-protein-isolate",
        "db_slug": "whey-protein-isolate",
        "ingredient": IngredientRef(
            ingredient_id="ING-WHEY-PROTEIN-ISOLATE",
            canonical_name="Whey Protein Isolate",
            aliases=["WPI", "Whey Isolate"],
        ),
    },
    "omega": {
        "label": "Omega-3 Fish Oil",
        "req_file": "omega-3",
        "db_slug": "omega-3",
        "ingredient": IngredientRef(
            ingredient_id="ING-OMEGA-3",
            canonical_name="Omega-3 Fish Oil",
            aliases=["Omega-3", "EPA/DHA", "Fish Oil Concentrate"],
        ),
    },
}


# ── Display ──────────────────────────────────────────────────────────────────


def print_header():
    print()
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    print(f"{BOLD}{CYAN}  Agnes Quality Verification Layer - Live Demo{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    print()


def print_ingredient_header(label: str, n_db: int, n_comp: int, idx: int, total: int):
    print(f"{BOLD}{WHITE}{'─' * 74}{RESET}")
    print(f"{BOLD}{WHITE}  [{idx}/{total}] {label}{RESET}")
    print(f"  {DIM}Suppliers: {n_db} from DB + {n_comp} competitors = {n_db + n_comp} total{RESET}")
    print(f"{BOLD}{WHITE}{'─' * 74}{RESET}")
    print()


def print_supplier(sa):
    status_color = OVERALL_STYLE.get(sa.overall_status, DIM)
    print(f"  {BOLD}{sa.supplier_id}{RESET}  {status_color}{sa.overall_status}{RESET}  confidence={sa.overall_evidence_confidence}")

    # Evidence
    retrieved = sum(1 for e in sa.evidence_items if e.status == "retrieved")
    types: dict = {}
    for e in sa.evidence_items:
        if e.status == "retrieved":
            t = e.source_type
            types[t] = types.get(t, 0) + 1
    type_str = ", ".join(f"{v}x {k}" for k, v in types.items()) if types else "none"
    print(f"       Evidence: {retrieved}/{len(sa.evidence_items)} retrieved ({type_str})")

    # Extracted attributes — only show high/medium confidence
    good_attrs = [a for a in sa.extracted_attributes if a.confidence in ("high", "medium")]
    print(f"       Extracted: {len(sa.extracted_attributes)} total, {len(good_attrs)} high/medium confidence")
    for attr in good_attrs[:10]:
        conf_color = GREEN if attr.confidence == "high" else YELLOW
        val = str(attr.value)
        if len(val) > 40:
            val = val[:37] + "..."
        unit = f" {attr.unit}" if attr.unit else ""
        print(f"         {attr.field_name:.<30s} {val}{unit}  {conf_color}[{attr.confidence}]{RESET}")
    if len(good_attrs) > 10:
        print(f"         {DIM}... +{len(good_attrs) - 10} more{RESET}")

    # Verification
    cov = sa.coverage_summary
    print(f"       Requirements: {cov.requirements_total} total")
    print(
        f"         Hard: {GREEN}{cov.hard_pass} pass{RESET}  "
        f"{RED}{cov.hard_fail} fail{RESET}  "
        f"{YELLOW}{cov.hard_unknown} unknown{RESET}"
    )
    print(
        f"         Soft: {GREEN}{cov.soft_pass} pass{RESET}  "
        f"{RED}{cov.soft_fail} fail{RESET}  "
        f"{YELLOW}{cov.soft_unknown} unknown{RESET}"
    )
    for vr in sa.verification_results:
        color, icon = STATUS_STYLE.get(vr.status, (DIM, "?"))
        reason = vr.reason
        if len(reason) > 65:
            reason = reason[:62] + "..."
        print(f"         {color}[{icon}]{RESET} {vr.field_name:.<20s} {DIM}{reason}{RESET}")

    if sa.notes:
        print(f"       {YELLOW}Notes:{RESET}")
        for n in sa.notes[:3]:
            note = n if len(n) <= 80 else n[:77] + "..."
            print(f"         {DIM}- {note}{RESET}")

    print()


def print_footer(total_time: float, total_shown: int, total_all: int):
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    print(
        f"{BOLD}{CYAN}  Done. Showing {total_shown} high-confidence suppliers "
        f"(of {total_all} total) in {total_time:.0f}s{RESET}"
    )
    if DEMO_OUTPUT.exists():
        pdf_count = sum(1 for _ in DEMO_OUTPUT.rglob("*.pdf"))
        if pdf_count:
            print(f"{BOLD}{CYAN}  PDFs saved to: {DEMO_OUTPUT}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    print()


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Agnes Quality Verification Demo")
    parser.add_argument(
        "--ingredient", "-i",
        choices=list(INGREDIENT_SPECS.keys()),
        help="Run a single ingredient (vitc, whey, omega)",
    )
    parser.add_argument(
        "--no-competitors",
        action="store_true",
        help="Skip competitor discovery (DB suppliers only)",
    )
    args = parser.parse_args()

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

    if args.ingredient:
        selected = {args.ingredient: INGREDIENT_SPECS[args.ingredient]}
    else:
        selected = INGREDIENT_SPECS

    print_header()
    print(f"  {DIM}Gemini: {config.gemini_model}{RESET}")
    print(f"  {DIM}Evidence search: DuckDuckGo ({config.search_results_per_query} results/query){RESET}")
    print(f"  {DIM}Ingredients: {', '.join(v['label'] for v in selected.values())}{RESET}")
    print()

    total_shown = 0
    total_all = 0
    t_start = time.monotonic()

    for idx, (key, spec) in enumerate(selected.items(), 1):
        ingredient = spec["ingredient"]
        requirements = _load_requirements(spec["req_file"])

        # Gather suppliers: DB + competitors
        db_suppliers = _get_db_suppliers(spec["db_slug"])
        print(f"  {DIM}Found {len(db_suppliers)} DB suppliers{RESET}")

        competitors = []
        if not args.no_competitors:
            competitors = _get_competitors(ingredient, max_candidates=10)
            print(f"  {DIM}Found {len(competitors)} competitors{RESET}")

        # Deduplicate by supplier name
        seen_names: set = set()
        all_suppliers: list[CandidateSupplier] = []
        for s in db_suppliers + competitors:
            name_key = s.supplier.supplier_name.lower()
            if name_key not in seen_names:
                seen_names.add(name_key)
                all_suppliers.append(s)

        print_ingredient_header(
            spec["label"], len(db_suppliers), len(competitors), idx, len(selected)
        )

        qv_input = QualityVerificationInput(
            ingredient=ingredient,
            requirements=requirements,
            candidate_suppliers=all_suppliers,
        )

        t0 = time.monotonic()
        output = run_quality_verification(qv_input, config)
        elapsed = time.monotonic() - t0

        # Download PDFs
        pdfs = download_pdfs(output, ingredient.canonical_name)
        if pdfs:
            print(f"  {GREEN}Downloaded {len(pdfs)} PDF(s):{RESET}")
            for p in pdfs:
                size_kb = p.stat().st_size / 1024
                print(f"    {GREEN}>{RESET} {p.name} {DIM}({size_kb:.0f} KB){RESET}")
            print()

        # Filter: show only high-confidence suppliers
        high_conf = [
            sa for sa in output.supplier_assessments
            if sa.overall_evidence_confidence in ("high", "medium")
            and sa.overall_status not in ("processing_error", "insufficient_evidence")
        ]

        total_all += len(output.supplier_assessments)

        if high_conf:
            print(f"  {GREEN}Showing {len(high_conf)}/{len(output.supplier_assessments)} suppliers with usable evidence:{RESET}")
            print()
            for sa in high_conf:
                print_supplier(sa)
                total_shown += 1
        else:
            print(f"  {YELLOW}No high-confidence suppliers found ({len(output.supplier_assessments)} assessed){RESET}")
            # Show the best one anyway
            best = sorted(
                output.supplier_assessments,
                key=lambda sa: len(sa.extracted_attributes),
                reverse=True,
            )
            if best:
                print(f"  {DIM}Best available:{RESET}")
                print()
                print_supplier(best[0])
                total_shown += 1

        # Show skipped suppliers
        skipped = [
            sa for sa in output.supplier_assessments if sa not in high_conf
        ]
        if skipped:
            skipped_names = ", ".join(sa.supplier_id for sa in skipped[:5])
            extra = f" +{len(skipped) - 5} more" if len(skipped) > 5 else ""
            print(f"  {DIM}Skipped (low confidence): {skipped_names}{extra}{RESET}")

        print(f"  {DIM}Completed in {elapsed:.0f}s{RESET}")
        print()

    total_time = time.monotonic() - t_start
    print_footer(total_time, total_shown, total_all)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Agnes Competitor Layer - Live Demo
===================================
Discovers plausible alternative suppliers for three CPG ingredients
using web search + Gemini-powered reasoning.

Usage:
    python demo.py              # full live search + Gemini
    python demo.py --mock       # instant demo with mock data
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure package is importable when running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from competitor_layer.config import CompetitorConfig, load_config
from competitor_layer.runner import run_competitor_layer
from competitor_layer.schemas import (
    CompetitorInput,
    CompetitorOutput,
    IngredientRef,
    RuntimeConfig,
    SearchContext,
)

# ── ANSI colors ──────────────────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BLUE = "\033[94m"

CONFIDENCE_COLORS = {"high": GREEN, "medium": YELLOW, "low": RED}
TYPE_COLORS = {
    "manufacturer": GREEN,
    "distributor": CYAN,
    "reseller": MAGENTA,
    "unknown": DIM,
}

# ── Ingredients to demo ─────────────────────────────────────────────────────

INGREDIENTS = [
    CompetitorInput(
        ingredient=IngredientRef(
            ingredient_id="ING-ASCORBIC-ACID",
            canonical_name="Ascorbic Acid",
            aliases=["Vitamin C", "L-Ascorbic Acid", "E300"],
            category="food ingredient",
        ),
        context=SearchContext(
            region="EU",
            product_category="beverage",
            grade_hint="food-grade",
        ),
        runtime=RuntimeConfig(max_candidates=5, ranking_enabled=True),
    ),
    CompetitorInput(
        ingredient=IngredientRef(
            ingredient_id="ING-WHEY-PROTEIN-ISOLATE",
            canonical_name="Whey Protein Isolate",
            aliases=["WPI", "Whey Isolate"],
            category="food ingredient",
        ),
        context=SearchContext(
            region="US",
            product_category="sports nutrition",
            grade_hint="food-grade",
        ),
        runtime=RuntimeConfig(max_candidates=5, ranking_enabled=True),
    ),
    CompetitorInput(
        ingredient=IngredientRef(
            ingredient_id="ING-OMEGA-3",
            canonical_name="Omega-3 Fish Oil",
            aliases=["Omega-3", "EPA/DHA", "Fish Oil Concentrate"],
            category="food ingredient",
        ),
        context=SearchContext(
            region="EU",
            product_category="dietary supplement",
            grade_hint="pharmaceutical-grade",
        ),
        runtime=RuntimeConfig(max_candidates=5, ranking_enabled=True),
    ),
]


# ── Display helpers ──────────────────────────────────────────────────────────


def print_header():
    print()
    print(f"{BOLD}{CYAN}{'=' * 70}{RESET}")
    print(f"{BOLD}{CYAN}  Agnes Competitor Layer - Supplier Discovery Demo{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 70}{RESET}")
    print()


def print_ingredient_header(inp: CompetitorInput, idx: int, total: int):
    ing = inp.ingredient
    ctx = inp.context
    print(f"{BOLD}{WHITE}{'─' * 70}{RESET}")
    print(
        f"{BOLD}{WHITE}  [{idx}/{total}] {ing.canonical_name}{RESET}"
        f"  {DIM}({ing.ingredient_id}){RESET}"
    )
    aliases = ", ".join(ing.aliases) if ing.aliases else "none"
    print(f"  {DIM}Aliases: {aliases}{RESET}")
    if ctx:
        parts = []
        if ctx.region:
            parts.append(f"Region: {ctx.region}")
        if ctx.product_category:
            parts.append(f"Category: {ctx.product_category}")
        if ctx.grade_hint:
            parts.append(f"Grade: {ctx.grade_hint}")
        print(f"  {DIM}{' | '.join(parts)}{RESET}")
    print(f"{BOLD}{WHITE}{'─' * 70}{RESET}")
    print()


def print_search_summary(output: CompetitorOutput):
    s = output.search_summary
    st = output.stats
    print(f"  {DIM}Trace: {output.trace_id}{RESET}")
    print(
        f"  {DIM}Queries: {len(s.queries_used)} | "
        f"Raw results: {st.raw_results_seen} | "
        f"Deduped suppliers: {st.deduped_suppliers} | "
        f"Returned: {st.returned_candidates}{RESET}"
    )
    gemini_tag = f"{GREEN}ON{RESET}" if s.gemini_enabled else f"{DIM}OFF{RESET}"
    print(f"  {DIM}Gemini reasoning: {gemini_tag}{RESET}")
    print()


def print_candidate(c, idx: int):
    sup = c.supplier
    conf_color = CONFIDENCE_COLORS.get(c.candidate_confidence, DIM)
    type_color = TYPE_COLORS.get(sup.supplier_type, DIM)

    # Header line
    rank = f"#{c.rank}" if c.rank else " -"
    print(
        f"  {BOLD}{rank:>3}  {sup.supplier_name}{RESET}"
        f"  {conf_color}[{c.candidate_confidence}]{RESET}"
    )

    # Details
    country = sup.country or "?"
    print(
        f"       {type_color}{sup.supplier_type}{RESET}"
        f"  {DIM}|{RESET}  {country}"
        f"  {DIM}|{RESET}  {sup.website or 'no website'}"
    )

    # Evidence bar
    hints = c.evidence_hints
    evidence = []
    if hints.website_found:
        evidence.append(f"{GREEN}web{RESET}")
    if hints.product_page_found:
        evidence.append(f"{GREEN}product{RESET}")
    if hints.pdf_found:
        evidence.append(f"{GREEN}pdf{RESET}")
    if hints.technical_doc_likely:
        evidence.append(f"{GREEN}tds{RESET}")
    missing = []
    if not hints.product_page_found:
        missing.append(f"{DIM}product{RESET}")
    if not hints.pdf_found:
        missing.append(f"{DIM}pdf{RESET}")
    if not hints.technical_doc_likely:
        missing.append(f"{DIM}tds{RESET}")
    all_evidence = evidence + missing
    print(f"       Evidence: {' '.join(all_evidence)}")

    # Reason
    reason = c.reason
    if len(reason) > 100:
        reason = reason[:97] + "..."
    print(f"       {DIM}{reason}{RESET}")

    # Offers
    for offer in c.matched_offers[:2]:
        print(f"       {BLUE}-> {offer.offer_label}{RESET}")
        if offer.source_url:
            url = offer.source_url
            if len(url) > 65:
                url = url[:62] + "..."
            print(f"          {DIM}{url}{RESET}")

    if len(c.matched_offers) > 2:
        print(f"       {DIM}... +{len(c.matched_offers) - 2} more offers{RESET}")

    print()


def print_warnings(output: CompetitorOutput):
    if output.warnings:
        print(f"  {YELLOW}Warnings:{RESET}")
        for w in output.warnings:
            print(f"    {DIM}- {w}{RESET}")
        print()


def print_footer(total_time: float, total_candidates: int):
    print(f"{BOLD}{CYAN}{'=' * 70}{RESET}")
    print(
        f"{BOLD}{CYAN}  Done. "
        f"{total_candidates} candidates found across 3 ingredients "
        f"in {total_time:.1f}s{RESET}"
    )
    print(f"{BOLD}{CYAN}{'=' * 70}{RESET}")
    print()


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    mock_mode = "--mock" in sys.argv

    # Load config
    load_dotenv_path = Path(__file__).resolve().parent / ".env"
    config = load_config(str(load_dotenv_path))

    from dataclasses import asdict

    if mock_mode:
        d = asdict(config)
        d["search_engine"] = "mock"
        config = CompetitorConfig(**d)
    else:
        # Default to duckduckgo for live demo (no CSE ID needed)
        d = asdict(config)
        if d["search_engine"] == "auto":
            d["search_engine"] = "duckduckgo"
        d["gemini_model"] = "gemini-2.5-flash"
        d["search_delay"] = 1.0
        d["search_results_per_query"] = 5
        config = CompetitorConfig(**d)

    print_header()

    if mock_mode:
        print(f"  {YELLOW}Running in MOCK mode (no network calls){RESET}")
    else:
        engine = config.search_engine
        if engine == "auto":
            engine = "duckduckgo (auto)"
        print(f"  {DIM}Search engine: {engine}{RESET}")
        gemini = "enabled" if config.gemini_api_key else "disabled"
        print(f"  {DIM}Gemini: {gemini}{RESET}")
    print()

    total_candidates = 0
    t_start = time.monotonic()

    for idx, inp in enumerate(INGREDIENTS, 1):
        print_ingredient_header(inp, idx, len(INGREDIENTS))

        t0 = time.monotonic()
        output = run_competitor_layer(inp, config)
        elapsed = time.monotonic() - t0

        print_search_summary(output)

        if output.candidates:
            for i, c in enumerate(output.candidates):
                print_candidate(c, i)
            total_candidates += len(output.candidates)
        else:
            print(f"  {RED}No candidates found.{RESET}")
            print()

        print_warnings(output)
        print(f"  {DIM}Completed in {elapsed:.1f}s{RESET}")
        print()

    total_time = time.monotonic() - t_start
    print_footer(total_time, total_candidates)


if __name__ == "__main__":
    main()

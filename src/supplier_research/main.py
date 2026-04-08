"""CLI entry point for the Agnes supplier research agent.

Usage:
    python -m src.supplier_research.main "calcium citrate"
    python -m src.supplier_research.main "vitamin d3" --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def _check_env() -> None:
    missing = [k for k in ("GOOGLE_API_KEY", "TAVILY_API_KEY") if not os.getenv(k)]
    if missing:
        print(f"ERROR: missing environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Copy .env.example to .env and fill in your keys.", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agnes – supplier research agent")
    parser.add_argument("ingredient", help="Ingredient name to research (e.g. 'calcium citrate')")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()
    env_path = Path(__file__).parents[2] / ".env"
    print(f"Loading .env from: {env_path}", file=sys.stderr)
    result = load_dotenv(env_path)
    print(f"load_dotenv success: {result}", file=sys.stderr)

    _check_env()

    # Import here so env check happens before heavy imports
    from .graph import build_graph

    graph = build_graph()

    print(f"\nResearching suppliers for: {args.ingredient!r}\n", flush=True)
    final_state = graph.invoke({
        "ingredient_name": args.ingredient,
        "suppliers": [],
        "results": [],
        "supplier_idx": 0,
        "verify_idx": 0,
        "verifications": [],
    })

    results = final_state.get("results", [])

    if not results:
        print("No suppliers found for this ingredient in the database.")
        return

    verifications = final_state.get("verifications", [])

    if args.json:
        output = {
            "results": [r.model_dump() for r in results],
            "verifications": [v.model_dump() for v in verifications],
        }
        print(json.dumps(output, indent=2))
        return

    # Human-readable output
    print(f"Found {len(results)} supplier(s)\n")
    print("=" * 70)
    for r in results:
        qp = r.quality_properties
        print(f"\nSupplier : {r.supplier_name}")
        print(f"SKUs     : {', '.join(r.skus)}")
        print(f"Grade    : {qp.grade or '—'}")
        print(f"Form     : {qp.form or '—'}")
        print(f"Purity   : {qp.purity or '—'}")
        print(f"Certs    : {', '.join(qp.certifications) if qp.certifications else '—'}")
        print(f"ISO      : {', '.join(qp.iso_certifications) if qp.iso_certifications else '—'}")
        print(f"Pharma   : {', '.join(qp.pharmacopoeia_compliance) if qp.pharmacopoeia_compliance else '—'}")
        print(f"GMP      : {'Yes' if qp.gmp_certified else 'No' if qp.gmp_certified is False else '—'}")
        print(f"3rd Party: {'Yes' if qp.third_party_tested else 'No' if qp.third_party_tested is False else '—'}")
        print(f"GRAS     : {qp.gras_status or '—'}")
        print(f"Storage  : {qp.storage_conditions or '—'}")
        print(f"Shelf life: {qp.shelf_life or '—'}")
        print(f"Product  : {qp.product_url or '—'}")
        print(f"TDS      : {qp.tds_url or '—'}")
        print(f"COA      : {qp.coa_url or '—'}")
        print(f"SDS      : {qp.sds_url or '—'}")
        if qp.notes:
            print(f"Notes    : {qp.notes}")
        if r.search_urls:
            print(f"Sources  : {r.search_urls[0]}")
            for u in r.search_urls[1:]:
                print(f"           {u}")
        print("-" * 70)

    # ---- Verification results ----
    if verifications:
        print("\n\n" + "=" * 70)
        print("QUALITY VERIFICATION REPORT")
        print("=" * 70)
        for v in verifications:
            print(f"\nSupplier  : {v.supplier_name}")
            print(f"Evidence  : {v.evidence_quality}")
            print(f"Confidence: {v.confidence_score}")
            print(f"Sources   : {len(v.sources)}")

            if v.extracted_fields:
                print(f"\n  Extracted fields ({len(v.extracted_fields)}):")
                for fname, fval in sorted(v.extracted_fields.items()):
                    unit = f" {fval.unit}" if fval.unit else ""
                    print(f"    {fname:30s} = {fval.value}{unit}")

            if v.comparison:
                print(f"\n  Compliance check:")
                for c in v.comparison:
                    icon = {"pass": "+", "fail": "X", "missing": "?"}[c.verdict]
                    actual = c.actual or "—"
                    sc_tag = f" [src:{c.source_confidence}]" if c.source_confidence not in ("n/a", "high") else ""
                    print(f"    [{icon}] {c.field:25s}  required: {c.required:20s}  actual: {actual:15s}  ({c.priority}){sc_tag}")

            if v.missing_evidence:
                print(f"\n  Missing evidence: {', '.join(v.missing_evidence)}")

            print("-" * 70)
    else:
        print("\n(No verification results — no requirements file found?)")


if __name__ == "__main__":
    main()

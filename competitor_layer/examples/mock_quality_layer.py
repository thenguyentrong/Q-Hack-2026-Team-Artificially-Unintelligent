#!/usr/bin/env python3
"""Mock Layer 3 (Quality Verification) consumer.

Demonstrates that the Competitor Layer output contract is consumable
by a downstream quality verification layer.

Usage:
    python examples/mock_quality_layer.py [output.json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add parent to path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from competitor_layer.schemas import CompetitorOutput


def consume_competitor_output(output: CompetitorOutput) -> None:
    """Simulate what Layer 3 would do with the Competitor Layer output."""
    print(f"=== Quality Layer Consumer ===")
    print(f"Trace ID: {output.trace_id}")
    print(f"Ingredient: {output.ingredient_id}")
    print(f"Schema version: {output.schema_version}")
    print(f"Candidates to verify: {len(output.candidates)}")
    print()

    for candidate in output.candidates:
        supplier = candidate.supplier
        print(f"--- {supplier.supplier_name} ({supplier.supplier_id}) ---")
        print(f"  Type: {supplier.supplier_type}")
        print(f"  Country: {supplier.country or 'unknown'}")
        print(f"  Website: {supplier.website or 'none'}")
        print(f"  Confidence: {candidate.candidate_confidence}")
        print(f"  Rank: {candidate.rank}")

        # Evidence assessment
        hints = candidate.evidence_hints
        print(f"  Evidence hints:")
        print(f"    Website found: {hints.website_found}")
        print(f"    Product page: {hints.product_page_found}")
        print(f"    PDF available: {hints.pdf_found}")
        print(f"    Technical docs likely: {hints.technical_doc_likely}")

        # What Layer 3 would do
        for offer in candidate.matched_offers:
            if offer.source_url:
                print(f"  -> Would fetch TDS/COA from: {offer.source_url}")
            print(f"  -> Would verify '{offer.offer_label}' against requirements")

        print()

    if output.warnings:
        print(f"Warnings from Competitor Layer:")
        for w in output.warnings:
            print(f"  - {w}")


def main() -> None:
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = str(Path(__file__).parent / "output_mock.json")

    raw = Path(path).read_text()
    output = CompetitorOutput.model_validate(json.loads(raw))
    consume_competitor_output(output)


if __name__ == "__main__":
    main()

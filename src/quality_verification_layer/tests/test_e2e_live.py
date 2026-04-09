"""End-to-end live tests for the quality verification layer.

These tests hit real APIs (DuckDuckGo search + Gemini extraction).
Run with: pytest tests/test_e2e_live.py -v -s -m e2e

Requires: GEMINI_API_KEY in environment or .env file.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from quality_verification_layer.config import QualityVerificationConfig
from quality_verification_layer.runner import run_quality_verification
from quality_verification_layer.schemas import (
    CandidateSupplier,
    Confidence,
    IngredientRef,
    QualityVerificationInput,
    QualityVerificationOutput,
    RequirementInput,
    SupplierAssessmentStatus,
    SupplierRef,
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

skip_no_gemini = pytest.mark.skipif(
    not GEMINI_API_KEY,
    reason="GEMINI_API_KEY not set",
)


def _live_config() -> QualityVerificationConfig:
    return QualityVerificationConfig(
        gemini_api_key=GEMINI_API_KEY,
        gemini_model="gemini-2.5-flash",
        max_evidence_per_supplier=8,
        rate_limit_delay=2.0,
        fetch_timeout=20,
        search_delay=1.5,
        search_results_per_query=4,
    )


def _requirements_from_file(name: str) -> list[RequirementInput]:
    """Load requirements from data/requirements/{name}.json and convert to RequirementInput."""
    req_dir = Path(__file__).resolve().parents[3] / "data" / "requirements"
    path = req_dir / f"{name}.json"
    data = json.loads(path.read_text())

    reqs = []
    for i, r in enumerate(data["requirements"], 1):
        rule_type = "maximum" if r["operator"] == "<=" else (
            "minimum" if r["operator"] == ">=" else (
            "enum_match" if r["operator"] == "in" else (
            "boolean_required" if r["operator"] == "==" else (
            "range" if r["operator"] == "range" else "free_text_reference"
        ))))

        req = RequirementInput(
            requirement_id=f"REQ-{name.upper()[:3]}-{i:03d}",
            field_name=r["field"],
            rule_type=rule_type,
            operator=r["operator"],
            priority="hard" if r.get("priority") == "critical" else "soft",
            unit=r.get("unit"),
            source_reference="industry standard",
        )

        # Set type-specific fields
        if rule_type == "range" and isinstance(r["value"], list):
            req.min_value = float(r["value"][0])
            req.max_value = float(r["value"][1])
        elif rule_type in ("minimum", "maximum"):
            val = float(r["value"])
            if rule_type == "minimum":
                req.min_value = val
            else:
                req.max_value = val
        elif rule_type == "enum_match":
            req.allowed_values = r["value"]
        elif rule_type == "boolean_required":
            req.required = r["value"]

        reqs.append(req)
    return reqs


def _print_assessment(output: QualityVerificationOutput):
    """Pretty-print results for demo visibility."""
    print(f"\n  Ingredient: {output.ingredient_id}")
    for sa in output.supplier_assessments:
        print(f"\n  --- {sa.supplier_id} ---")
        print(f"  Status: {sa.overall_status}")
        print(f"  Confidence: {sa.overall_evidence_confidence}")
        print(f"  Evidence items: {len(sa.evidence_items)}")
        retrieved = sum(1 for e in sa.evidence_items if e.status == "retrieved")
        print(f"  Retrieved: {retrieved}/{len(sa.evidence_items)}")
        print(f"  Attributes extracted: {len(sa.extracted_attributes)}")
        for attr in sa.extracted_attributes[:5]:
            print(f"    {attr.field_name}: {attr.value} {attr.unit or ''} [{attr.confidence}]")
        if len(sa.extracted_attributes) > 5:
            print(f"    ... +{len(sa.extracted_attributes) - 5} more")
        print(f"  Verification results:")
        cov = sa.coverage_summary
        print(f"    Total: {cov.requirements_total} | Hard: {cov.hard_pass}P/{cov.hard_fail}F/{cov.hard_unknown}U | Soft: {cov.soft_pass}P/{cov.soft_fail}F/{cov.soft_unknown}U")
        for vr in sa.verification_results:
            status_icon = {"pass": "+", "fail": "X", "unknown": "?", "partial": "~"}.get(vr.status, "?")
            print(f"    [{status_icon}] {vr.field_name}: {vr.reason[:80]}")
        if sa.notes:
            print(f"  Notes: {sa.notes[:3]}")


def _shared_assertions(output: QualityVerificationOutput, expected_suppliers: int):
    """Common assertions for all E2E tests."""
    assert isinstance(output, QualityVerificationOutput)
    assert output.schema_version == "1.0"
    assert len(output.supplier_assessments) == expected_suppliers

    for sa in output.supplier_assessments:
        # Every supplier gets an assessment
        assert sa.supplier_id
        # Evidence items have IDs
        for ei in sa.evidence_items:
            assert ei.evidence_id.startswith("EVID-")
            assert ei.source_url
        # Verification results cover all requirements
        assert len(sa.verification_results) > 0
        for vr in sa.verification_results:
            assert vr.verification_id.startswith("VER-")
            assert vr.requirement_id
            assert vr.reason
        # Coverage summary is consistent
        cov = sa.coverage_summary
        assert cov.requirements_total == len(sa.verification_results)

    # Output is valid JSON
    json_str = output.model_dump_json(indent=2)
    reparsed = QualityVerificationOutput.model_validate_json(json_str)
    assert reparsed == output


# ── Test 1: Vitamin C ────────────────────────────────────────────────────────


@pytest.mark.e2e
@skip_no_gemini
class TestVitaminCE2E:
    def test_vitamin_c_db_suppliers(self):
        """E2E: Vitamin C with DB suppliers (Prinova USA, PureBulk)."""
        input_data = QualityVerificationInput(
            ingredient=IngredientRef(
                ingredient_id="ING-ASCORBIC-ACID",
                canonical_name="Ascorbic Acid",
                aliases=["Vitamin C", "L-Ascorbic Acid"],
            ),
            requirements=_requirements_from_file("vitamin-c"),
            candidate_suppliers=[
                CandidateSupplier(
                    supplier=SupplierRef(
                        supplier_id="SUP-PRINOVA",
                        supplier_name="Prinova USA",
                        country="US",
                    ),
                ),
                CandidateSupplier(
                    supplier=SupplierRef(
                        supplier_id="SUP-PUREBULK",
                        supplier_name="PureBulk",
                        country="US",
                        website="https://www.purebulk.com",
                    ),
                ),
            ],
        )

        output = run_quality_verification(input_data, _live_config())
        _shared_assertions(output, expected_suppliers=2)
        _print_assessment(output)

        # At least one supplier should have some evidence
        any_evidence = any(
            len(sa.evidence_items) > 0 for sa in output.supplier_assessments
        )
        assert any_evidence, "Expected at least one supplier to have evidence"


# ── Test 2: Whey Protein Isolate ─────────────────────────────────────────────


@pytest.mark.e2e
@skip_no_gemini
class TestWheyProteinE2E:
    def test_whey_protein_db_suppliers(self):
        """E2E: Whey Protein Isolate with DB suppliers."""
        input_data = QualityVerificationInput(
            ingredient=IngredientRef(
                ingredient_id="ING-WHEY-PROTEIN-ISOLATE",
                canonical_name="Whey Protein Isolate",
                aliases=["WPI", "Whey Isolate"],
            ),
            requirements=_requirements_from_file("whey-protein-isolate"),
            candidate_suppliers=[
                CandidateSupplier(
                    supplier=SupplierRef(
                        supplier_id="SUP-ACTUS",
                        supplier_name="Actus Nutrition",
                        country="US",
                    ),
                ),
                CandidateSupplier(
                    supplier=SupplierRef(
                        supplier_id="SUP-PRINOVA",
                        supplier_name="Prinova USA",
                        country="US",
                    ),
                ),
            ],
        )

        output = run_quality_verification(input_data, _live_config())
        _shared_assertions(output, expected_suppliers=2)
        _print_assessment(output)


# ── Test 3: Omega-3 Fish Oil ─────────────────────────────────────────────────


@pytest.mark.e2e
@skip_no_gemini
class TestOmega3E2E:
    def test_omega3_db_suppliers(self):
        """E2E: Omega-3 Fish Oil with DB suppliers."""
        input_data = QualityVerificationInput(
            ingredient=IngredientRef(
                ingredient_id="ING-OMEGA-3",
                canonical_name="Omega-3 Fish Oil",
                aliases=["Omega-3", "EPA/DHA", "Fish Oil Concentrate"],
            ),
            requirements=_requirements_from_file("omega-3"),
            candidate_suppliers=[
                CandidateSupplier(
                    supplier=SupplierRef(
                        supplier_id="SUP-ICELAND",
                        supplier_name="Icelandirect",
                        country="US",
                    ),
                ),
                CandidateSupplier(
                    supplier=SupplierRef(
                        supplier_id="SUP-SOURCEOMEGA",
                        supplier_name="Source-Omega LLC",
                        country="US",
                    ),
                ),
            ],
        )

        output = run_quality_verification(input_data, _live_config())
        _shared_assertions(output, expected_suppliers=2)
        _print_assessment(output)


# ── Test 4: Cross-layer L2 → L3 ─────────────────────────────────────────────


@pytest.mark.e2e
@skip_no_gemini
class TestCrossLayerE2E:
    def test_competitor_to_quality(self):
        """E2E: Run competitor layer for Ascorbic Acid, feed output into quality verification."""
        from competitor_layer.config import CompetitorConfig as CLC
        from competitor_layer.runner import run_competitor_layer
        from competitor_layer.schemas import (
            CompetitorInput,
            IngredientRef as CLIngredient,
            RuntimeConfig as CLRuntime,
            SearchContext as CLContext,
        )

        # Step 1: Run competitor layer
        cl_input = CompetitorInput(
            ingredient=CLIngredient(
                ingredient_id="ING-ASCORBIC-ACID",
                canonical_name="Ascorbic Acid",
                aliases=["Vitamin C"],
            ),
            context=CLContext(region="EU"),
            runtime=CLRuntime(max_candidates=3, ranking_enabled=True),
        )
        cl_config = CLC(
            gemini_api_key=GEMINI_API_KEY,
            gemini_model="gemini-2.5-flash",
            max_candidates=3,
            ranking_enabled=True,
            google_api_key=None,
            google_cse_id=None,
            search_engine="duckduckgo",
            search_results_per_query=3,
            search_delay=1.5,
        )
        cl_output = run_competitor_layer(cl_input, cl_config)
        assert len(cl_output.candidates) > 0

        print(f"\n  Competitor layer found {len(cl_output.candidates)} candidates:")
        for c in cl_output.candidates:
            print(f"    {c.supplier.supplier_name} ({c.candidate_confidence})")

        # Step 2: Convert competitor output to quality verification input
        qv_suppliers = []
        for c in cl_output.candidates:
            source_urls = [o.source_url for o in c.matched_offers if o.source_url]
            qv_suppliers.append(
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

        qv_input = QualityVerificationInput(
            ingredient=IngredientRef(
                ingredient_id="ING-ASCORBIC-ACID",
                canonical_name="Ascorbic Acid",
                aliases=["Vitamin C", "L-Ascorbic Acid"],
            ),
            requirements=_requirements_from_file("vitamin-c"),
            candidate_suppliers=qv_suppliers,
        )

        # Step 3: Run quality verification
        qv_output = run_quality_verification(qv_input, _live_config())
        _shared_assertions(qv_output, expected_suppliers=len(qv_suppliers))
        _print_assessment(qv_output)

        print(f"\n  Cross-layer pipeline complete: L2 ({len(cl_output.candidates)} candidates) -> L3 ({len(qv_output.supplier_assessments)} assessments)")

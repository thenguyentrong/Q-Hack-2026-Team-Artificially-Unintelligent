"""Shared fixtures for quality verification layer tests."""

from __future__ import annotations

import pytest

from quality_verification_layer.schemas import (
    CandidateSupplier,
    Confidence,
    EvidenceHints,
    IngredientRef,
    Priority,
    QualityVerificationInput,
    RequirementInput,
    RunConfig,
    SupplierRef,
)


@pytest.fixture
def ascorbic_acid_ingredient():
    return IngredientRef(
        ingredient_id="ING-ASCORBIC-ACID",
        canonical_name="Ascorbic Acid",
        aliases=["Vitamin C", "L-Ascorbic Acid"],
    )


@pytest.fixture
def sample_requirements():
    return [
        RequirementInput(
            requirement_id="REQ-ASC-001",
            field_name="purity",
            rule_type="range",
            operator="between",
            min_value=99.0,
            max_value=100.5,
            unit="%",
            priority="hard",
            source_reference="USP",
        ),
        RequirementInput(
            requirement_id="REQ-ASC-002",
            field_name="heavy_metals",
            rule_type="maximum",
            operator="<=",
            max_value=10,
            unit="ppm",
            priority="soft",
            source_reference="benchmark",
        ),
    ]


@pytest.fixture
def sample_supplier():
    return CandidateSupplier(
        supplier=SupplierRef(
            supplier_id="SUP-001",
            supplier_name="Test Supplier",
            country="DE",
            website="https://example.com",
        ),
        candidate_confidence="high",
        evidence_hints=EvidenceHints(
            website_found=True,
            product_page_found=True,
            technical_docs_likely=True,
        ),
        source_urls=["https://example.com/products/ascorbic-acid"],
    )


@pytest.fixture
def sample_input(ascorbic_acid_ingredient, sample_requirements, sample_supplier):
    return QualityVerificationInput(
        ingredient=ascorbic_acid_ingredient,
        requirements=sample_requirements,
        candidate_suppliers=[sample_supplier],
    )

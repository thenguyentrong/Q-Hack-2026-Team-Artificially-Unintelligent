"""Tests for candidate extraction and normalization."""

from __future__ import annotations

from competitor_layer.candidate_extractor import (
    extract_candidates,
    extract_domain,
)
from competitor_layer.search_types import RawSearchResult, SearchResultSet


def _make_result(
    url: str = "https://example.com",
    title: str = "Example",
    snippet: str = "Example snippet",
    query: str = "test query",
) -> RawSearchResult:
    return RawSearchResult(
        url=url, title=title, snippet=snippet,
        query=query, source_engine="mock",
    )


def _make_result_set(
    results: list,
    ingredient_id: str = "ING-TEST",
) -> SearchResultSet:
    return SearchResultSet(
        ingredient_id=ingredient_id,
        queries_used=list({r.query for r in results}),
        results=results,
        total_results=len(results),
    )


# === Spec-required: Incorrect-domain rejection ===


class TestDomainRejection:
    def test_wikipedia_rejected(self):
        results = [_make_result(url="https://en.wikipedia.org/wiki/Ascorbic_acid")]
        candidates = extract_candidates(_make_result_set(results), "Ascorbic Acid")
        assert len(candidates) == 0

    def test_amazon_rejected(self):
        results = [_make_result(url="https://www.amazon.com/ascorbic-acid")]
        candidates = extract_candidates(_make_result_set(results), "Ascorbic Acid")
        assert len(candidates) == 0

    def test_government_domain_rejected(self):
        results = [_make_result(url="https://www.fda.gov/food/ingredients")]
        candidates = extract_candidates(_make_result_set(results), "Ascorbic Acid")
        assert len(candidates) == 0

    def test_edu_domain_rejected(self):
        results = [_make_result(url="https://www.mit.edu/research/vitamins")]
        candidates = extract_candidates(_make_result_set(results), "Ascorbic Acid")
        assert len(candidates) == 0

    def test_supplier_domain_kept(self):
        results = [_make_result(
            url="https://www.dsm-firmenich.com/ingredients/ascorbic-acid",
            title="Ascorbic Acid - DSM-Firmenich",
            snippet="DSM-Firmenich is a leading manufacturer.",
        )]
        candidates = extract_candidates(_make_result_set(results), "Ascorbic Acid")
        assert len(candidates) == 1

    def test_all_rejected_returns_empty(self):
        results = [
            _make_result(url="https://en.wikipedia.org/wiki/Vitamin_C"),
            _make_result(url="https://www.reddit.com/r/supplements"),
            _make_result(url="https://www.fda.gov/vitamins"),
        ]
        candidates = extract_candidates(_make_result_set(results), "Ascorbic Acid")
        assert len(candidates) == 0


# === Spec-required: Manufacturer vs distributor labeling ===


class TestSupplierTypeClassification:
    def test_manufacturer_keyword_detected(self):
        results = [_make_result(
            url="https://example-chem.com/products",
            title="Ascorbic Acid - Example Chem",
            snippet="We are a leading manufacturer of ascorbic acid with production facilities worldwide.",
        )]
        candidates = extract_candidates(_make_result_set(results), "Ascorbic Acid")
        assert candidates[0].supplier_type == "manufacturer"

    def test_distributor_keyword_detected(self):
        results = [_make_result(
            url="https://example-dist.com/vitamins",
            title="Vitamins - Example Dist",
            snippet="As a wholesale distributor, we distribute ingredients globally.",
        )]
        candidates = extract_candidates(_make_result_set(results), "Ascorbic Acid")
        assert candidates[0].supplier_type == "distributor"

    def test_reseller_keyword_detected(self):
        results = [_make_result(
            url="https://vitashop.com/ascorbic-acid",
            title="Buy Ascorbic Acid Online",
            snippet="Add to cart. Buy online with free shipping. Shop now.",
        )]
        candidates = extract_candidates(_make_result_set(results), "Ascorbic Acid")
        assert candidates[0].supplier_type == "reseller"

    def test_no_keywords_yields_unknown(self):
        results = [_make_result(
            url="https://someco.com/page",
            title="Page - SomeCo",
            snippet="Information about various chemical compounds.",
        )]
        candidates = extract_candidates(_make_result_set(results), "Ascorbic Acid")
        assert candidates[0].supplier_type == "unknown"


# === Spec-required: Duplicate supplier merge ===


class TestDuplicateSupplierMerge:
    def test_same_domain_different_queries_merged(self):
        results = [
            _make_result(
                url="https://dsm-firmenich.com/products/ascorbic-acid",
                title="Ascorbic Acid - DSM-Firmenich",
                snippet="Leading manufacturer",
                query="ascorbic acid supplier",
            ),
            _make_result(
                url="https://dsm-firmenich.com/ingredients/vitamin-c",
                title="Vitamin C - DSM-Firmenich",
                snippet="Food grade manufacturer",
                query="vitamin c manufacturer",
            ),
        ]
        candidates = extract_candidates(_make_result_set(results), "Ascorbic Acid")
        dsm = [c for c in candidates if "dsm" in c.supplier_name.lower()]
        assert len(dsm) == 1
        assert len(dsm[0].offers) == 2

    def test_name_variant_merge(self):
        results = [
            _make_result(
                url="https://dsm-firmenich.com/product",
                title="Product - DSM-Firmenich",
                snippet="Manufacturer of ingredients.",
            ),
            _make_result(
                url="https://dsm-firmenich.de/produkt",
                title="Produkt - DSM-Firmenich GmbH",
                snippet="Hersteller von Zutaten.",
            ),
        ]
        candidates = extract_candidates(
            _make_result_set(results), "Ascorbic Acid"
        )
        dsm = [c for c in candidates if "dsm" in c.supplier_name.lower()]
        assert len(dsm) == 1


# === Spec-required: Matched-offer roll-up ===


class TestOfferRollup:
    def test_multiple_results_create_multiple_offers(self):
        results = [
            _make_result(
                url="https://supplier.com/product-a",
                title="Product A - Supplier",
            ),
            _make_result(
                url="https://supplier.com/product-b",
                title="Product B - Supplier",
            ),
            _make_result(
                url="https://supplier.com/product-c",
                title="Product C - Supplier",
            ),
        ]
        candidates = extract_candidates(_make_result_set(results), "Test")
        assert len(candidates) == 1
        assert len(candidates[0].offers) == 3

    def test_duplicate_url_offers_deduped(self):
        results = [
            _make_result(
                url="https://supplier.com/product",
                title="Product - Supplier",
                query="query 1",
            ),
            _make_result(
                url="https://supplier.com/product",
                title="Product - Supplier",
                query="query 2",
            ),
        ]
        candidates = extract_candidates(_make_result_set(results), "Test")
        assert len(candidates) == 1
        assert len(candidates[0].offers) == 1

    def test_offer_label_strips_company_name(self):
        results = [_make_result(
            url="https://dsm-firmenich.com/ascorbic",
            title="Ascorbic Acid - DSM-Firmenich",
            snippet="Manufacturer",
        )]
        candidates = extract_candidates(_make_result_set(results), "Ascorbic Acid")
        assert candidates[0].offers[0]["offer_label"] == "Ascorbic Acid"


# === Supplier name extraction ===


class TestSupplierNameExtraction:
    def test_name_from_title_separator(self):
        results = [_make_result(
            url="https://dsm-firmenich.com/page",
            title="Ascorbic Acid - DSM-Firmenich",
        )]
        candidates = extract_candidates(_make_result_set(results), "Ascorbic Acid")
        assert candidates[0].supplier_name == "DSM-Firmenich"

    def test_name_from_domain_fallback(self):
        results = [_make_result(
            url="https://cspc.com.hk/product",
            title="Vitamin C products available",
        )]
        candidates = extract_candidates(
            _make_result_set(results), "Ascorbic Acid", ["Vitamin C"]
        )
        assert candidates[0].supplier_name == "Cspc"


# === Country inference ===


class TestCountryInference:
    def test_country_from_cctld(self):
        results = [_make_result(url="https://supplier.de/product")]
        candidates = extract_candidates(_make_result_set(results), "Test")
        assert candidates[0].country == "DE"

    def test_country_from_multi_tld(self):
        results = [_make_result(url="https://cspc.com.hk/product")]
        candidates = extract_candidates(_make_result_set(results), "Test")
        assert candidates[0].country == "HK"

    def test_country_from_snippet(self):
        results = [_make_result(
            url="https://supplier.com/product",
            snippet="Headquartered in China, serving global markets.",
        )]
        candidates = extract_candidates(_make_result_set(results), "Test")
        assert candidates[0].country == "CN"

    def test_generic_tld_no_country(self):
        results = [_make_result(
            url="https://supplier.com/product",
            snippet="A supplier of chemicals.",
        )]
        candidates = extract_candidates(_make_result_set(results), "Test")
        assert candidates[0].country == ""


# === Evidence hints ===


class TestEvidenceHints:
    def test_pdf_url_detected(self):
        results = [_make_result(url="https://supplier.com/specs/tds.pdf")]
        candidates = extract_candidates(_make_result_set(results), "Test")
        assert candidates[0].pdf_found is True

    def test_product_page_detected(self):
        results = [_make_result(url="https://supplier.com/products/acid")]
        candidates = extract_candidates(_make_result_set(results), "Test")
        assert candidates[0].product_page_found is True

    def test_tds_in_snippet_detected(self):
        results = [_make_result(
            url="https://supplier.com/page",
            snippet="Download the technical data sheet for full specifications.",
        )]
        candidates = extract_candidates(_make_result_set(results), "Test")
        assert candidates[0].technical_doc_likely is True

    def test_coa_in_title_detected(self):
        results = [_make_result(
            url="https://supplier.com/page",
            title="Certificate of Analysis - Supplier",
        )]
        candidates = extract_candidates(_make_result_set(results), "Test")
        assert candidates[0].technical_doc_likely is True


# === Confidence assignment ===


class TestConfidenceAssignment:
    def test_high_confidence(self):
        results = [
            _make_result(
                url="https://mfg.com/products/acid",
                title="Acid - Mfg",
                snippet="We are a manufacturer with production facility.",
            ),
            _make_result(
                url="https://mfg.com/products/acid-2",
                title="Acid 2 - Mfg",
                snippet="Download technical data sheet.",
            ),
        ]
        candidates = extract_candidates(_make_result_set(results), "Acid")
        assert candidates[0].confidence == "high"

    def test_low_confidence(self):
        results = [_make_result(
            url="https://random.com/page",
            title="Some page",
            snippet="General info.",
        )]
        candidates = extract_candidates(_make_result_set(results), "Test")
        assert candidates[0].confidence == "low"


# === End-to-end ===


class TestEndToEnd:
    def test_mock_results_produce_valid_candidates(self):
        """Full pipeline produces InternalCandidates that convert to output Candidates."""
        results = [
            _make_result(
                url="https://dsm-firmenich.com/ingredients/ascorbic-acid",
                title="Ascorbic Acid - DSM-Firmenich",
                snippet="DSM-Firmenich is a leading manufacturer of ascorbic acid for food applications.",
            ),
            _make_result(
                url="https://cspc.com.hk/product/vitamin-c",
                title="Vitamin C - CSPC Pharmaceutical",
                snippet="CSPC produces vitamin C in China.",
            ),
            _make_result(
                url="https://prinovaglobal.com/ingredients/vitamins",
                title="Vitamins - Prinova Global",
                snippet="Prinova is a wholesale distributor of vitamin ingredients.",
            ),
        ]
        candidates = extract_candidates(
            _make_result_set(results, "ING-ASCORBIC-ACID"),
            "Ascorbic Acid",
            ["Vitamin C"],
        )
        assert len(candidates) == 3

        # All should convert to output Candidate without error
        for i, c in enumerate(candidates):
            out = c.to_candidate(rank=i + 1, supplier_id=f"SUP-{i + 1:03d}")
            assert out.supplier.supplier_id == f"SUP-{i + 1:03d}"
            assert out.supplier.supplier_name
            assert out.reason

"""Tests for candidate filtering, scoring, and ranking."""

from __future__ import annotations

from competitor_layer.candidate_filter import filter_and_rank
from competitor_layer.models import InternalCandidate
from competitor_layer.schemas import IngredientRef, SearchContext


def _ingredient() -> IngredientRef:
    return IngredientRef(
        ingredient_id="ING-ASCORBIC-ACID",
        canonical_name="Ascorbic Acid",
        aliases=["Vitamin C", "L-Ascorbic Acid"],
    )


def _make_candidate(
    name: str = "Test Supplier",
    supplier_type: str = "unknown",
    offer_label: str = "Ascorbic Acid",
    source_url: str = "https://example.com/product",
    product_page_found: bool = False,
    pdf_found: bool = False,
    technical_doc_likely: bool = False,
    confidence: str = "low",
    reason: str = "Found via web search (1 result(s))",
) -> InternalCandidate:
    return InternalCandidate(
        supplier_name=name,
        supplier_type=supplier_type,
        country="",
        website=f"https://{name.lower().replace(' ', '')}.com",
        offers=[{
            "offer_label": offer_label,
            "matched_name": "Ascorbic Acid",
            "source_url": source_url,
        }],
        website_found=True,
        product_page_found=product_page_found,
        pdf_found=pdf_found,
        technical_doc_likely=technical_doc_likely,
        confidence=confidence,
        reason=reason,
    )


# === Spec-required: Irrelevant result removal ===


class TestIrrelevantResultRemoval:
    def test_no_ingredient_match_removed(self):
        candidates = [
            _make_candidate(
                name="Wrong Supplier",
                offer_label="Citric Acid Powder",
                source_url="https://wrong.com/citric-acid",
                reason="Found via web search",
            ),
        ]
        result = filter_and_rank(candidates, _ingredient())
        assert len(result.candidates) == 0
        assert result.removed_count == 1

    def test_alias_match_kept(self):
        candidates = [
            _make_candidate(offer_label="Vitamin C Powder"),
        ]
        result = filter_and_rank(candidates, _ingredient())
        assert len(result.candidates) == 1

    def test_canonical_name_match_kept(self):
        candidates = [
            _make_candidate(offer_label="Ascorbic Acid Food Grade"),
        ]
        result = filter_and_rank(candidates, _ingredient())
        assert len(result.candidates) == 1

    def test_url_match_kept(self):
        candidates = [
            _make_candidate(
                offer_label="Product Page",
                source_url="https://supplier.com/ascorbic-acid",
            ),
        ]
        result = filter_and_rank(candidates, _ingredient())
        assert len(result.candidates) == 1


# === Spec-required: Evidence hint population ===


class TestEvidenceHintPopulation:
    def test_evidence_flags_flow_through(self):
        candidates = [
            _make_candidate(
                product_page_found=True,
                pdf_found=True,
                technical_doc_likely=True,
            ),
        ]
        result = filter_and_rank(candidates, _ingredient())
        c = result.candidates[0]
        assert c.product_page_found is True
        assert c.pdf_found is True
        assert c.technical_doc_likely is True

    def test_more_evidence_higher_score(self):
        low_ev = _make_candidate(name="Low Evidence")
        high_ev = _make_candidate(
            name="High Evidence",
            product_page_found=True,
            pdf_found=True,
            technical_doc_likely=True,
        )
        result = filter_and_rank([low_ev, high_ev], _ingredient())
        # High evidence should rank first
        assert result.candidates[0].supplier_name == "High Evidence"


# === Spec-required: Confidence labeling ===


class TestConfidenceLabeling:
    def test_high_score_high_confidence(self):
        candidates = [
            _make_candidate(
                supplier_type="manufacturer",
                product_page_found=True,
                pdf_found=True,
                technical_doc_likely=True,
            ),
        ]
        result = filter_and_rank(candidates, _ingredient())
        assert result.candidates[0].confidence == "high"

    def test_low_score_low_confidence(self):
        candidates = [
            _make_candidate(
                supplier_type="unknown",
                offer_label="Ascorbic Acid",
            ),
        ]
        result = filter_and_rank(candidates, _ingredient())
        assert result.candidates[0].confidence in ("low", "medium")

    def test_score_in_reason(self):
        candidates = [_make_candidate()]
        result = filter_and_rank(candidates, _ingredient())
        assert "[score:" in result.candidates[0].reason


# === Spec-required: Fixed-top-N / threshold behavior ===


class TestTopNThreshold:
    def test_max_candidates_respected(self):
        candidates = [
            _make_candidate(name=f"Supplier {i}", offer_label="Ascorbic Acid")
            for i in range(5)
        ]
        result = filter_and_rank(candidates, _ingredient(), max_candidates=2)
        assert len(result.candidates) <= 2

    def test_below_threshold_dropped(self):
        # A candidate with very weak match should be dropped
        candidates = [
            _make_candidate(
                name="Barely Relevant",
                offer_label="Acids and chemicals",
                source_url="https://barely.com/acids",
                reason="Found via web search",
            ),
        ]
        result = filter_and_rank(candidates, _ingredient())
        # This candidate has no ingredient name match → filtered in stage 1
        assert len(result.candidates) == 0


# === Additional: Scoring ===


class TestScoring:
    def test_manufacturer_scores_higher_than_unknown(self):
        mfg = _make_candidate(name="Mfg Co", supplier_type="manufacturer")
        unk = _make_candidate(name="Unk Co", supplier_type="unknown")
        result = filter_and_rank([unk, mfg], _ingredient())
        assert result.candidates[0].supplier_name == "Mfg Co"

    def test_context_match_boosts_score(self):
        ctx = SearchContext(grade_hint="food grade")
        with_grade = _make_candidate(
            name="Food Grade Co",
            offer_label="Ascorbic Acid Food Grade",
        )
        without_grade = _make_candidate(
            name="Generic Co",
            offer_label="Ascorbic Acid",
        )
        result = filter_and_rank([without_grade, with_grade], _ingredient(), context=ctx)
        assert result.candidates[0].supplier_name == "Food Grade Co"


# === Additional: Ranking disabled ===


class TestRankingDisabled:
    def test_ranking_disabled_still_filters(self):
        candidates = [_make_candidate()]
        result = filter_and_rank(
            candidates, _ingredient(), ranking_enabled=False
        )
        assert len(result.candidates) == 1


# === Additional: Edge cases ===


class TestEdgeCases:
    def test_empty_input(self):
        result = filter_and_rank([], _ingredient())
        assert len(result.candidates) == 0
        assert result.removed_count == 0

    def test_warnings_generated_for_weak_evidence(self):
        candidates = [
            _make_candidate(name=f"Supplier {i}", offer_label="Ascorbic Acid")
            for i in range(3)
        ]
        result = filter_and_rank(candidates, _ingredient())
        # All have weak evidence (no product page, no PDF)
        assert any("No product pages found" in w for w in result.warnings)

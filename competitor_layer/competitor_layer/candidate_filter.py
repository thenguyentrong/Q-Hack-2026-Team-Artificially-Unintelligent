"""Light filtering, scoring, and ranking for supplier candidates."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

from competitor_layer.models import InternalCandidate
from competitor_layer.schemas import IngredientRef, SearchContext

if TYPE_CHECKING:
    from competitor_layer.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

# Scoring weights (spec section 8.1)
W_INGREDIENT = 0.40
W_CONTEXT = 0.25
W_EVIDENCE = 0.20
W_SOURCE = 0.15

# Source quality by supplier type
SOURCE_QUALITY = {
    "manufacturer": 1.0,
    "distributor": 0.7,
    "reseller": 0.4,
    "unknown": 0.2,
}

# Confidence thresholds
CONFIDENCE_HIGH = 0.6
CONFIDENCE_MEDIUM = 0.35

# Minimum score to keep a candidate
MIN_SCORE_THRESHOLD = 0.15


@dataclass
class FilterResult:
    candidates: List[InternalCandidate]
    removed_count: int
    warnings: List[str] = field(default_factory=list)


def filter_and_rank(
    candidates: List[InternalCandidate],
    ingredient: IngredientRef,
    context: Optional[SearchContext] = None,
    max_candidates: int = 10,
    ranking_enabled: bool = True,
    gemini_client: Optional[GeminiClient] = None,
) -> FilterResult:
    """Filter, score, and rank supplier candidates."""
    if not candidates:
        return FilterResult(candidates=[], removed_count=0)

    ingredient_names = {ingredient.canonical_name.lower()} | {
        a.lower() for a in ingredient.aliases
    }

    # Stage 1: ingredient relevance filter
    relevant, irrelevant_count = _filter_by_relevance(candidates, ingredient_names)

    # Stage 2: score each candidate
    scored = [
        (_score_candidate(c, ingredient, context), c)
        for c in relevant
    ]

    # Stage 3: update confidence from score and generate reasoning
    for score, c in scored:
        c.confidence = _score_to_confidence(score)
        gemini_reason = _generate_reasoning(c, ingredient, gemini_client) if gemini_client else None
        if gemini_reason:
            c.reason = f"{gemini_reason} [score: {score:.2f}]"
        else:
            c.reason = _update_reason(c, score)

    # Stage 4: threshold + sort + top-N
    above_threshold = [(s, c) for s, c in scored if s >= MIN_SCORE_THRESHOLD]
    below_threshold_count = len(scored) - len(above_threshold)

    above_threshold.sort(key=lambda x: -x[0])
    top = above_threshold[:max_candidates]

    # Build result
    result_candidates = [c for _, c in top]
    removed = irrelevant_count + below_threshold_count

    # Warnings
    warnings: List[str] = []
    low_evidence = sum(1 for s, _ in top if s < CONFIDENCE_MEDIUM)
    if low_evidence:
        warnings.append(
            f"Candidate confidence low due to weak evidence for {low_evidence} of {len(top)} candidates"
        )
    no_product_page = sum(
        1 for _, c in top if not c.product_page_found
    )
    if no_product_page and len(top) > 0:
        warnings.append(
            f"No product pages found for {no_product_page} of {len(top)} candidates"
        )

    return FilterResult(
        candidates=result_candidates,
        removed_count=removed,
        warnings=warnings,
    )


# === Stage 1: Relevance filter ===


def _filter_by_relevance(
    candidates: List[InternalCandidate],
    ingredient_names: set,
) -> tuple:
    """Remove candidates with no ingredient match in any offer."""
    relevant: List[InternalCandidate] = []
    removed = 0
    for c in candidates:
        if _has_ingredient_match(c, ingredient_names):
            relevant.append(c)
        else:
            removed += 1
    return relevant, removed


def _has_ingredient_match(c: InternalCandidate, names: set) -> bool:
    """Check if any offer label or source URL matches the ingredient."""
    # Build variants: "ascorbic acid" also matches "ascorbic-acid" in URLs
    name_variants = set()
    for name in names:
        name_variants.add(name)
        name_variants.add(name.replace(" ", "-"))

    for offer in c.offers:
        label = offer.get("offer_label", "").lower()
        url = offer.get("source_url", "").lower()
        if any(v in label or v in url for v in name_variants):
            return True
    # Also check supplier name + reason as fallback
    text = f"{c.supplier_name} {c.reason}".lower()
    return any(v in text for v in name_variants)


# === Stage 2: Scoring ===


def _score_candidate(
    c: InternalCandidate,
    ingredient: IngredientRef,
    context: Optional[SearchContext],
) -> float:
    return (
        W_INGREDIENT * _ingredient_match_score(c, ingredient)
        + W_CONTEXT * _context_match_score(c, context)
        + W_EVIDENCE * _evidence_strength_score(c)
        + W_SOURCE * _source_quality_score(c)
    )


def _ingredient_match_score(c: InternalCandidate, ingredient: IngredientRef) -> float:
    canonical = ingredient.canonical_name.lower()
    canonical_url = canonical.replace(" ", "-")
    aliases = {a.lower() for a in ingredient.aliases}
    aliases_url = {a.replace(" ", "-") for a in aliases}

    best = 0.0
    for offer in c.offers:
        label = offer.get("offer_label", "").lower()
        url = offer.get("source_url", "").lower()
        if canonical in label:
            return 1.0  # exact match in label
        if any(a in label for a in aliases):
            best = max(best, 0.7)
        if canonical in url or canonical_url in url:
            best = max(best, 0.3)
        if any(a in url or au in url for a, au in zip(aliases, aliases_url)):
            best = max(best, 0.3)
    return best


def _context_match_score(c: InternalCandidate, context: Optional[SearchContext]) -> float:
    if not context:
        return 0.0

    text = " ".join(
        offer.get("offer_label", "") for offer in c.offers
    ).lower() + " " + c.reason.lower()

    score = 0.0
    if context.grade_hint and context.grade_hint.lower() in text:
        score = max(score, 1.0)
    if context.product_category and context.product_category.lower() in text:
        score = max(score, 0.5)
    return score


def _evidence_strength_score(c: InternalCandidate) -> float:
    flags = [c.website_found, c.product_page_found, c.pdf_found, c.technical_doc_likely]
    return sum(0.25 for f in flags if f)


def _source_quality_score(c: InternalCandidate) -> float:
    return SOURCE_QUALITY.get(c.supplier_type, 0.2)


# === Stage 3: Confidence mapping ===


def _score_to_confidence(score: float) -> str:
    if score >= CONFIDENCE_HIGH:
        return "high"
    if score >= CONFIDENCE_MEDIUM:
        return "medium"
    return "low"


def _update_reason(c: InternalCandidate, score: float) -> str:
    return f"{c.reason} [score: {score:.2f}]"


def _generate_reasoning(
    c: InternalCandidate,
    ingredient: IngredientRef,
    gemini_client: Optional[GeminiClient],
) -> Optional[str]:
    """Use Gemini to generate a concise reasoning string for a candidate."""
    if gemini_client is None:
        return None
    try:
        from competitor_layer.gemini_client import SupplierReasoning
        from competitor_layer.prompts import SUPPLIER_REASONING_PROMPT

        prompt = SUPPLIER_REASONING_PROMPT.format(
            supplier_name=c.supplier_name,
            supplier_type=c.supplier_type,
            country=c.country or "unknown",
            website=c.website,
            result_count=len(c.offers),
            product_page="found" if c.product_page_found else "not found",
            pdf="found" if c.pdf_found else "not found",
            tech_doc="likely" if c.technical_doc_likely else "not found",
            ingredient_name=ingredient.canonical_name,
        )
        result = gemini_client.generate(prompt, SupplierReasoning)
        if result and result.reason:
            return result.reason
    except Exception as e:
        logger.warning("Gemini reasoning failed for %s: %s", c.supplier_name, e)
    return None

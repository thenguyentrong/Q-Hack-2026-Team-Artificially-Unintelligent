"""Internal domain types for the Competitor Layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from competitor_layer.schemas import (
    Candidate,
    CandidateConfidence,
    EvidenceHints,
    MatchedOffer,
    SupplierInfo,
    SupplierType,
)


@dataclass
class InternalCandidate:
    supplier_name: str
    supplier_type: str
    country: str
    website: str
    offers: List[dict] = field(default_factory=list)
    website_found: bool = False
    product_page_found: bool = False
    pdf_found: bool = False
    technical_doc_likely: bool = False
    confidence: str = "low"
    reason: str = ""

    def to_candidate(self, rank: int | None, supplier_id: str) -> Candidate:
        return Candidate(
            supplier=SupplierInfo(
                supplier_id=supplier_id,
                supplier_name=self.supplier_name,
                supplier_type=SupplierType(self.supplier_type),
                country=self.country,
                website=self.website,
            ),
            matched_offers=[
                MatchedOffer(**offer) for offer in self.offers
            ],
            evidence_hints=EvidenceHints(
                website_found=self.website_found,
                product_page_found=self.product_page_found,
                pdf_found=self.pdf_found,
                technical_doc_likely=self.technical_doc_likely,
            ),
            candidate_confidence=CandidateConfidence(self.confidence),
            rank=rank,
            reason=self.reason,
        )

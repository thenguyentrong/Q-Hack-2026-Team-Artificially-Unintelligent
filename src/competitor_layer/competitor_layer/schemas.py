"""Pydantic I/O contracts for the Agnes Competitor Layer."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# --- Enums ---


class SupplierType(str, Enum):
    manufacturer = "manufacturer"
    distributor = "distributor"
    reseller = "reseller"
    unknown = "unknown"


class CandidateConfidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


# --- Input models ---


class IngredientRef(BaseModel):
    ingredient_id: str
    canonical_name: str
    aliases: List[str] = []
    category: str = "food ingredient"


class SearchContext(BaseModel):
    region: Optional[str] = None
    product_category: Optional[str] = None
    grade_hint: Optional[str] = None


class RequirementsContext(BaseModel):
    required_grade: Optional[str] = None
    notes: Optional[str] = None


class RuntimeConfig(BaseModel):
    max_candidates: int = 10
    ranking_enabled: bool = True


class CompetitorInput(BaseModel):
    schema_version: str = "1.0"
    trace_id: Optional[str] = None
    ingredient: IngredientRef
    context: Optional[SearchContext] = None
    requirements_context: Optional[RequirementsContext] = None
    runtime: Optional[RuntimeConfig] = None


# --- Output models ---


class SupplierInfo(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    supplier_id: str
    supplier_name: str
    supplier_type: SupplierType = SupplierType.unknown
    country: Optional[str] = None
    website: Optional[str] = None


class MatchedOffer(BaseModel):
    offer_label: str
    matched_name: str
    source_url: Optional[str] = None


class EvidenceHints(BaseModel):
    website_found: bool = False
    product_page_found: bool = False
    pdf_found: bool = False
    technical_doc_likely: bool = False


class Candidate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    supplier: SupplierInfo
    matched_offers: List[MatchedOffer]
    evidence_hints: EvidenceHints
    candidate_confidence: CandidateConfidence
    rank: Optional[int] = None
    reason: str


class SearchSummary(BaseModel):
    queries_used: List[str]
    region_applied: Optional[str] = None
    ranking_enabled: bool = True
    gemini_enabled: bool = False


class OutputStats(BaseModel):
    raw_results_seen: int
    deduped_suppliers: int
    returned_candidates: int


class CompetitorOutput(BaseModel):
    schema_version: str = "1.0"
    trace_id: str = ""
    ingredient_id: str
    search_summary: SearchSummary
    candidates: List[Candidate]
    warnings: List[str] = []
    stats: OutputStats

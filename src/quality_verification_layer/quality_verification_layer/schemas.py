"""Pydantic I/O contracts for the Agnes Quality Verification Layer."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ────────────────────────────────────────────────────────────────────


class EvidenceStatus(str, Enum):
    retrieved = "retrieved"
    unreachable = "unreachable"
    blocked = "blocked"
    irrelevant = "irrelevant"
    parse_failed = "parse_failed"


class VerificationStatus(str, Enum):
    pass_ = "pass"
    fail = "fail"
    unknown = "unknown"
    partial = "partial"


class SupplierAssessmentStatus(str, Enum):
    verified = "verified"
    verified_with_gaps = "verified_with_gaps"
    failed_hard_requirements = "failed_hard_requirements"
    insufficient_evidence = "insufficient_evidence"
    processing_error = "processing_error"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class SourceType(str, Enum):
    coa = "coa"
    tds = "tds"
    certification_page = "certification_page"
    product_page = "product_page"
    marketing_page = "marketing_page"
    other = "other"


class Priority(str, Enum):
    hard = "hard"
    soft = "soft"


class RuleType(str, Enum):
    range = "range"
    minimum = "minimum"
    maximum = "maximum"
    enum_match = "enum_match"
    boolean_required = "boolean_required"
    free_text_reference = "free_text_reference"


class ExtractionMethod(str, Enum):
    document_parser = "document_parser"
    llm_extraction = "llm_extraction"
    heuristic = "heuristic"
    seed = "seed"


# ── Input models ─────────────────────────────────────────────────────────────


class IngredientRef(BaseModel):
    ingredient_id: str
    canonical_name: str
    aliases: List[str] = Field(default_factory=list)
    category: str = "food ingredient"


class RequirementInput(BaseModel):
    """Accepts both spec format and Layer 1 RequirementRule format."""

    model_config = ConfigDict(use_enum_values=True)

    requirement_id: str
    field_name: str
    rule_type: RuleType
    operator: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = None
    priority: Priority = Priority.hard
    source_reference: Optional[str] = None
    allowed_values: Optional[List[str]] = None
    required: Optional[bool] = None
    reference_text: Optional[str] = None
    notes: Optional[str] = None


class SupplierRef(BaseModel):
    supplier_id: str
    supplier_name: str
    country: Optional[str] = None
    website: Optional[str] = None


class EvidenceHints(BaseModel):
    website_found: bool = False
    product_page_found: bool = False
    technical_docs_likely: bool = False


class CandidateSupplier(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    supplier: SupplierRef
    candidate_confidence: Confidence = Confidence.medium
    evidence_hints: Optional[EvidenceHints] = None
    source_urls: List[str] = Field(default_factory=list)


class RunConfig(BaseModel):
    max_evidence_per_supplier: int = 10
    allowed_source_types: List[str] = Field(
        default_factory=lambda: ["tds", "coa", "product_page", "certification_page"]
    )
    strict_mode: bool = False


class QualityVerificationInput(BaseModel):
    schema_version: str = "1.0"
    ingredient: IngredientRef
    requirements: List[RequirementInput]
    candidate_suppliers: List[CandidateSupplier]
    run_config: Optional[RunConfig] = None


# ── Output models ────────────────────────────────────────────────────────────


class EvidenceItem(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    evidence_id: str
    source_type: SourceType = SourceType.other
    source_url: str
    title: Optional[str] = None
    status: EvidenceStatus = EvidenceStatus.retrieved
    retrieved_at: str = ""


class ExtractedAttribute(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    attribute_id: str
    field_name: str
    value: Union[float, str]
    unit: Optional[str] = None
    source_evidence_id: str = ""
    confidence: Confidence = Confidence.medium
    extraction_method: ExtractionMethod = ExtractionMethod.llm_extraction


class VerificationResultItem(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    verification_id: str
    requirement_id: str
    field_name: str
    status: VerificationStatus
    observed_value: Optional[Union[float, str]] = None
    unit: Optional[str] = None
    confidence: Confidence = Confidence.medium
    reason: str = ""
    supporting_evidence_ids: List[str] = Field(default_factory=list)


class CoverageSummary(BaseModel):
    requirements_total: int = 0
    hard_pass: int = 0
    hard_fail: int = 0
    hard_unknown: int = 0
    soft_pass: int = 0
    soft_fail: int = 0
    soft_unknown: int = 0


class SupplierAssessment(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    supplier_id: str
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    extracted_attributes: List[ExtractedAttribute] = Field(default_factory=list)
    verification_results: List[VerificationResultItem] = Field(default_factory=list)
    coverage_summary: CoverageSummary = Field(default_factory=CoverageSummary)
    overall_evidence_confidence: Confidence = Confidence.low
    overall_status: SupplierAssessmentStatus = SupplierAssessmentStatus.insufficient_evidence
    notes: List[str] = Field(default_factory=list)


class QualityVerificationOutput(BaseModel):
    schema_version: str = "1.0"
    ingredient_id: str
    supplier_assessments: List[SupplierAssessment] = Field(default_factory=list)

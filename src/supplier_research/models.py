from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class QualityProperties(BaseModel):
    """Structured quality properties extracted from supplier research."""

    product_name: Optional[str] = Field(None, description="Supplier's product name for this ingredient")
    product_url: Optional[str] = Field(None, description="Direct product page URL")
    tds_url: Optional[str] = Field(None, description="Technical Data Sheet URL")
    coa_url: Optional[str] = Field(None, description="Certificate of Analysis URL")
    sds_url: Optional[str] = Field(None, description="Safety Data Sheet URL")
    certifications: list[str] = Field(
        default_factory=list,
        description="Quality certifications (e.g. USP, NSF, Kosher, Halal, Non-GMO, Organic)",
    )
    purity: Optional[str] = Field(None, description="Purity or assay specification (e.g. '≥98%')")
    form: Optional[str] = Field(None, description="Physical form (e.g. powder, granule, liquid)")
    grade: Optional[str] = Field(None, description="Grade (e.g. USP, Food Grade, Pharma, FCC)")
    particle_size: Optional[str] = Field(None, description="Particle size specification if stated")
    origin: Optional[str] = Field(None, description="Country of origin or manufacturing location")
    storage_conditions: Optional[str] = Field(None, description="Recommended storage conditions (e.g. 'cool, dry place <25°C')")
    shelf_life: Optional[str] = Field(None, description="Shelf life or retest period (e.g. '24 months from manufacture')")
    gmp_certified: Optional[bool] = Field(None, description="Whether the supplier/facility is GMP certified")
    iso_certifications: list[str] = Field(
        default_factory=list,
        description="ISO certifications held (e.g. ISO 9001, ISO 22000)",
    )
    pharmacopoeia_compliance: list[str] = Field(
        default_factory=list,
        description="Pharmacopoeia standards met (e.g. USP, EP, JP, BP)",
    )
    third_party_tested: Optional[bool] = Field(None, description="Whether the product is independently third-party tested")
    gras_status: Optional[str] = Field(None, description="FDA GRAS status or self-affirmed GRAS, if applicable")
    notes: Optional[str] = Field(None, description="Other relevant quality or compliance notes")


class SupplierResult(BaseModel):
    supplier_id: int
    supplier_name: str
    skus: list[str]
    ingredient: str
    quality_properties: QualityProperties
    raw_findings: str
    search_urls: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent 2 – Verification models
# ---------------------------------------------------------------------------

class ExtractedField(BaseModel):
    value: str
    unit: Optional[str] = None
    source_url: Optional[str] = None
    source_confidence: Literal["high", "medium", "low"] = "medium"
    """high = document is clearly for this ingredient+supplier;
       medium = plausible but uncertain;
       low = document likely describes a different product/grade."""


class ComparisonEntry(BaseModel):
    field: str
    required: str = Field(description="Human-readable requirement string")
    actual: Optional[str] = None
    verdict: Literal["pass", "fail", "missing"] = "missing"
    priority: Literal["critical", "major", "minor"] = "major"
    source_confidence: Literal["high", "medium", "low", "n/a"] = "n/a"


class VerificationResult(BaseModel):
    supplier_name: str
    ingredient: str
    extracted_fields: dict[str, ExtractedField] = Field(default_factory=dict)
    comparison: list[ComparisonEntry] = Field(default_factory=list)
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="Fields required but not found in any source",
    )
    evidence_quality: Literal["pdf_found", "html_only", "blocked", "none"] = "none"
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    sources: list[str] = Field(default_factory=list)

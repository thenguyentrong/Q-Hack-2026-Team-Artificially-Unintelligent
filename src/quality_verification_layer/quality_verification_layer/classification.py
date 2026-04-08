"""Evidence classification — determine source type (COA, TDS, product page, etc.)."""

from __future__ import annotations

import re
from typing import List
from urllib.parse import urlparse

from .retrieval import FetchedSource
from .schemas import EvidenceItem, SourceType

# URL path patterns
_COA_URL_PATTERNS = re.compile(r"(coa|certificate.of.analysis|lot.cert)", re.I)
_TDS_URL_PATTERNS = re.compile(r"(tds|technical.data.sheet|tech.spec|specification)", re.I)
_CERT_URL_PATTERNS = re.compile(r"(certif|compliance|quality.assurance|iso|gmp)", re.I)
_SDS_URL_PATTERNS = re.compile(r"(sds|safety.data.sheet|msds)", re.I)

# Content heuristics
_COA_CONTENT_MARKERS = [
    "certificate of analysis",
    "lot no",
    "lot number",
    "batch no",
    "batch number",
    "date of manufacture",
    "date of analysis",
    "coa",
]
_TDS_CONTENT_MARKERS = [
    "technical data sheet",
    "product specification",
    "specification sheet",
    "general specification",
    "typical analysis",
]


def classify_source(source: FetchedSource, ingredient_name: str) -> SourceType:
    """Classify a fetched source by its type based on URL and content heuristics."""
    if not source.ok:
        return SourceType.other

    url_lower = source.url.lower()
    path = urlparse(source.url).path.lower()
    text_lower = source.text[:3000].lower() if source.text else ""

    # PDF with COA signals
    if source.content_type == "pdf":
        if _COA_URL_PATTERNS.search(path) or _COA_URL_PATTERNS.search(url_lower):
            return SourceType.coa
        if any(marker in text_lower for marker in _COA_CONTENT_MARKERS):
            return SourceType.coa
        if _TDS_URL_PATTERNS.search(path) or _TDS_URL_PATTERNS.search(url_lower):
            return SourceType.tds
        if any(marker in text_lower for marker in _TDS_CONTENT_MARKERS):
            return SourceType.tds
        if _SDS_URL_PATTERNS.search(path):
            return SourceType.other  # SDS is out of scope for quality
        # Generic PDF — likely a spec/TDS
        return SourceType.tds

    # HTML pages
    if _COA_URL_PATTERNS.search(path):
        return SourceType.coa
    if any(marker in text_lower for marker in _COA_CONTENT_MARKERS):
        return SourceType.coa
    if _TDS_URL_PATTERNS.search(path):
        return SourceType.tds
    if any(marker in text_lower for marker in _TDS_CONTENT_MARKERS):
        return SourceType.tds
    if _CERT_URL_PATTERNS.search(path):
        return SourceType.certification_page

    # Check if it's a product page (ingredient name in URL or content)
    ing_lower = ingredient_name.lower()
    if ing_lower.replace(" ", "-") in url_lower or ing_lower in text_lower:
        if "/product" in url_lower or "/ingredient" in url_lower:
            return SourceType.product_page

    # Fallback — if on supplier domain, treat as product page
    if source.content_type == "html" and source.ok:
        return SourceType.product_page

    return SourceType.other


def classify_evidence_items(
    sources: List[FetchedSource],
    evidence_items: List[EvidenceItem],
    ingredient_name: str,
) -> List[EvidenceItem]:
    """Update evidence items with classified source types."""
    url_to_type = {}
    for source in sources:
        url_to_type[source.url] = classify_source(source, ingredient_name)

    for item in evidence_items:
        if item.source_url in url_to_type:
            item.source_type = url_to_type[item.source_url]

    return evidence_items

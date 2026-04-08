"""Evidence retrieval — fetch URLs and build EvidenceItem records."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import List, Optional, Tuple

import httpx

from .id_generator import QualityIdGenerator
from .schemas import (
    CandidateSupplier,
    EvidenceHints,
    EvidenceItem,
    EvidenceStatus,
    IngredientRef,
    RunConfig,
    SourceType,
)

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
}


class FetchedSource:
    """Internal representation of a fetched URL's content."""

    __slots__ = ("url", "content_type", "text", "ok", "evidence_id")

    def __init__(
        self, url: str, content_type: str, text: str, ok: bool, evidence_id: str = ""
    ):
        self.url = url
        self.content_type = content_type
        self.text = text
        self.ok = ok
        self.evidence_id = evidence_id


def _fetch_url(url: str, client: httpx.Client, timeout: int = 20) -> FetchedSource:
    """Fetch a single URL. Returns extracted text or an error marker."""
    try:
        resp = client.get(url, timeout=timeout, follow_redirects=True)
        if resp.status_code >= 400:
            return FetchedSource(url, "", f"[HTTP {resp.status_code}]", ok=False)

        ct = resp.headers.get("content-type", "")

        if "pdf" in ct or url.lower().endswith(".pdf"):
            text = _extract_pdf_text(resp.content)
            return FetchedSource(url, "pdf", text, ok=bool(text.strip()))

        import re

        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s{2,}", " ", text).strip()
        text = text[:6_000]
        return FetchedSource(url, "html", text, ok=True)

    except Exception as exc:
        return FetchedSource(url, "", f"[Error: {exc}]", ok=False)


def _extract_pdf_text(data: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        return "[pdfplumber not installed]"

    text_parts: List[str] = []
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            for page in pdf.pages[:5]:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as exc:
        return f"[PDF parse error: {exc}]"
    return "\n\n".join(text_parts)


def _status_from_fetch(source: FetchedSource) -> EvidenceStatus:
    """Map a FetchedSource result to an EvidenceStatus."""
    if source.ok:
        return EvidenceStatus.retrieved
    text = source.text.lower()
    if "parse error" in text:
        return EvidenceStatus.parse_failed
    if "403" in text or "blocked" in text:
        return EvidenceStatus.blocked
    if "error" in text or "http" in text:
        return EvidenceStatus.unreachable
    return EvidenceStatus.unreachable


def retrieve_evidence(
    candidate: CandidateSupplier,
    ingredient: IngredientRef,
    id_gen: QualityIdGenerator,
    run_config: Optional[RunConfig] = None,
    fetch_timeout: int = 20,
) -> Tuple[List[EvidenceItem], List[FetchedSource]]:
    """Fetch URLs for a supplier candidate and build EvidenceItem records.

    Returns (evidence_items, fetched_sources) where fetched_sources carry
    the actual text content for downstream extraction.
    """
    max_evidence = run_config.max_evidence_per_supplier if run_config else 10

    # Gather URLs from source_urls and supplier website
    urls: List[str] = list(candidate.source_urls or [])
    if candidate.supplier.website and candidate.supplier.website not in urls:
        urls.append(candidate.supplier.website)

    urls = urls[:max_evidence]
    now = datetime.now(timezone.utc).isoformat()

    evidence_items: List[EvidenceItem] = []
    fetched_sources: List[FetchedSource] = []

    logger.info(
        "Fetching %d URL(s) for %s", len(urls), candidate.supplier.supplier_name
    )

    with httpx.Client(headers=_HEADERS) as client:
        for url in urls:
            evid_id = id_gen.next_evidence_id()
            source = _fetch_url(url, client, timeout=fetch_timeout)
            source.evidence_id = evid_id

            status = _status_from_fetch(source)
            evidence_items.append(
                EvidenceItem(
                    evidence_id=evid_id,
                    source_url=url,
                    status=status,
                    retrieved_at=now,
                )
            )
            fetched_sources.append(source)

    ok_count = sum(1 for s in fetched_sources if s.ok)
    logger.info(
        "%d/%d accessible for %s",
        ok_count,
        len(fetched_sources),
        candidate.supplier.supplier_name,
    )

    return evidence_items, fetched_sources

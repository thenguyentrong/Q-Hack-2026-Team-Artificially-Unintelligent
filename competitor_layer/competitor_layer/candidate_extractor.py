"""Candidate extraction and normalization from raw search results."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from competitor_layer.models import InternalCandidate
from competitor_layer.search_types import RawSearchResult, SearchResultSet

if TYPE_CHECKING:
    from competitor_layer.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

# --- Domain rejection ---

REJECTED_DOMAINS = frozenset({
    "wikipedia.org", "en.wikipedia.org",
    "amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
    "reddit.com", "quora.com",
    "youtube.com", "facebook.com", "twitter.com", "x.com", "linkedin.com",
    "instagram.com", "pinterest.com", "tiktok.com",
    "nytimes.com", "bbc.com", "cnn.com", "reuters.com", "theguardian.com",
    "nih.gov", "fda.gov", "efsa.europa.eu", "who.int",
    "pubmed.ncbi.nlm.nih.gov",
    "scholar.google.com", "books.google.com",
    "webmd.com", "healthline.com", "mayoclinic.org",
    "ebay.com", "alibaba.com", "aliexpress.com",
})

REJECTED_DOMAIN_SUFFIXES = (".gov", ".edu", ".mil")

# --- Supplier type keywords (term, weight) ---

TYPE_SIGNALS: Dict[str, List[Tuple[str, int]]] = {
    "manufacturer": [
        ("manufacturer", 3), ("manufactures", 3), ("manufacturing", 3),
        ("producer", 2), ("produces", 2), ("production facility", 3),
        ("we produce", 3), ("our factory", 3), ("our plant", 2),
        ("made by", 1), ("factory direct", 2),
    ],
    "distributor": [
        ("distributor", 3), ("distributes", 3), ("distribution", 2),
        ("wholesale", 2), ("wholesaler", 2),
        ("we distribute", 3), ("supply chain partner", 1),
        ("ingredient supplier", 2), ("ingredient distributor", 3),
    ],
    "reseller": [
        ("reseller", 3), ("resell", 2),
        ("buy online", 2), ("add to cart", 2),
        ("shop now", 2), ("retail", 1), ("e-commerce", 1),
        ("order now", 1),
    ],
}

TYPE_MIN_SCORE = 2

# --- Country inference ---

CCTLD_TO_COUNTRY = {
    ".de": "DE", ".cn": "CN", ".uk": "GB", ".co.uk": "GB",
    ".fr": "FR", ".nl": "NL", ".it": "IT", ".es": "ES",
    ".jp": "JP", ".kr": "KR", ".in": "IN", ".br": "BR",
    ".au": "AU", ".ca": "CA", ".mx": "MX", ".ch": "CH",
    ".at": "AT", ".be": "BE", ".dk": "DK", ".se": "SE",
    ".no": "NO", ".fi": "FI", ".pl": "PL", ".cz": "CZ",
    ".hk": "HK", ".sg": "SG", ".tw": "TW", ".za": "ZA",
    ".ru": "RU", ".ie": "IE", ".nz": "NZ", ".com.hk": "HK",
    ".com.cn": "CN", ".co.jp": "JP", ".co.kr": "KR",
    ".com.au": "AU", ".com.br": "BR", ".co.in": "IN",
}

COUNTRY_KEYWORDS = {
    "germany": "DE", "german": "DE",
    "china": "CN", "chinese": "CN",
    "netherlands": "NL", "dutch": "NL",
    "united states": "US", "usa": "US", "u.s.a": "US", "u.s.": "US",
    "united kingdom": "GB",
    "france": "FR", "french": "FR",
    "japan": "JP", "japanese": "JP",
    "india": "IN", "indian": "IN",
    "canada": "CA", "canadian": "CA",
    "switzerland": "CH", "swiss": "CH",
    "brazil": "BR", "brazilian": "BR",
    "south korea": "KR", "korea": "KR",
    "australia": "AU", "australian": "AU",
    "italy": "IT", "italian": "IT",
    "spain": "ES", "spanish": "ES",
    "mexico": "MX", "mexican": "MX",
    "hong kong": "HK",
    "singapore": "SG",
    "taiwan": "TW",
}

# --- Evidence detection patterns ---

PRODUCT_PAGE_SEGMENTS = {
    "/product", "/products", "/ingredient", "/ingredients",
    "/catalog", "/catalogue", "/item", "/items",
}

TECHNICAL_DOC_TERMS = {
    "technical data sheet", "tds", "coa", "certificate of analysis",
    "specification sheet", "spec sheet", "safety data sheet",
    "sds", "msds", "product specification",
}

# --- Name normalization for merging ---

COMPANY_SUFFIXES = re.compile(
    r"\s*\b(inc|ltd|llc|gmbh|co|corp|corporation|group|"
    r"international|global|plc|ag|sa|srl|bv|nv|pty|pvt)\b\.?\s*$",
    re.IGNORECASE,
)

TITLE_SEPARATORS = (" - ", " | ", " :: ", " >> ", " — ", " – ")


# === Public API ===


def extract_candidates(
    result_set: SearchResultSet,
    canonical_name: str,
    aliases: Optional[List[str]] = None,
    gemini_client: Optional[GeminiClient] = None,
) -> List[InternalCandidate]:
    """Extract normalized supplier candidates from raw search results."""
    if aliases is None:
        aliases = []

    ingredient_names = {canonical_name.lower()} | {a.lower() for a in aliases}

    # Stage 1: group by domain and reject irrelevant
    domain_groups = _group_and_filter(result_set.results)

    # Stage 2-5: extract candidate info per domain
    proto_candidates: List[_ProtoCandidate] = []
    for domain, results in domain_groups.items():
        name = _extract_supplier_name(domain, results, ingredient_names)
        supplier_type = _classify_supplier_type(results)
        # Phase 5: Gemini classification for ambiguous cases
        if supplier_type == "unknown" and gemini_client is not None:
            gemini_type = _classify_with_gemini(domain, results, gemini_client)
            if gemini_type:
                supplier_type = gemini_type
        country = _infer_country(domain, results)
        evidence = _detect_evidence(results)
        offers = _build_offers(results, canonical_name, name)
        proto_candidates.append(
            _ProtoCandidate(
                supplier_name=name,
                supplier_type=supplier_type,
                country=country,
                website=f"https://{domain}",
                offers=offers,
                evidence=evidence,
                result_count=len(results),
            )
        )

    # Stage 6: merge duplicates and assign confidence
    return _merge_candidates(proto_candidates)


# === Internal types ===


class _ProtoCandidate:
    """Intermediate representation before merging."""

    __slots__ = (
        "supplier_name", "supplier_type", "country", "website",
        "offers", "evidence", "result_count",
    )

    def __init__(
        self,
        supplier_name: str,
        supplier_type: str,
        country: str,
        website: str,
        offers: List[dict],
        evidence: _Evidence,
        result_count: int,
    ):
        self.supplier_name = supplier_name
        self.supplier_type = supplier_type
        self.country = country
        self.website = website
        self.offers = offers
        self.evidence = evidence
        self.result_count = result_count


class _Evidence:
    __slots__ = ("website_found", "product_page_found", "pdf_found", "technical_doc_likely")

    def __init__(
        self,
        website_found: bool = True,
        product_page_found: bool = False,
        pdf_found: bool = False,
        technical_doc_likely: bool = False,
    ):
        self.website_found = website_found
        self.product_page_found = product_page_found
        self.pdf_found = pdf_found
        self.technical_doc_likely = technical_doc_likely


# === Stage 1: Domain grouping and filtering ===


def extract_domain(url: str) -> str:
    """Extract clean domain from URL, stripping www. prefix."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.lower()
    except Exception:
        return ""


def _group_and_filter(
    results: List[RawSearchResult],
) -> Dict[str, List[RawSearchResult]]:
    groups: Dict[str, List[RawSearchResult]] = {}
    for r in results:
        domain = extract_domain(r.url)
        if not domain or _is_rejected_domain(domain):
            continue
        groups.setdefault(domain, []).append(r)
    return groups


def _is_rejected_domain(domain: str) -> bool:
    if domain in REJECTED_DOMAINS:
        return True
    # Check parent domain (e.g., "en.wikipedia.org" → "wikipedia.org")
    parts = domain.split(".")
    if len(parts) > 2:
        parent = ".".join(parts[-2:])
        if parent in REJECTED_DOMAINS:
            return True
    for suffix in REJECTED_DOMAIN_SUFFIXES:
        if domain.endswith(suffix):
            return True
    return False


# === Stage 2: Supplier name extraction ===


def _extract_supplier_name(
    domain: str,
    results: List[RawSearchResult],
    ingredient_names: set,
) -> str:
    # Strategy A: title separator extraction
    name = _name_from_titles(results, ingredient_names)
    if name:
        return name

    # Strategy B: domain-to-name conversion
    return _name_from_domain(domain)


def _name_from_titles(
    results: List[RawSearchResult],
    ingredient_names: set,
) -> str:
    """Try to extract company name from title separators."""
    candidates: Dict[str, int] = {}
    for r in results:
        title = r.title
        for sep in TITLE_SEPARATORS:
            if sep in title:
                parts = title.split(sep)
                # Try rightmost segment first (most common for company name)
                right = parts[-1].strip()
                left = parts[0].strip()
                # Pick segment that doesn't contain ingredient name
                if right and not _contains_ingredient(right, ingredient_names):
                    candidates[right] = candidates.get(right, 0) + 1
                elif left and not _contains_ingredient(left, ingredient_names):
                    candidates[left] = candidates.get(left, 0) + 1
                break  # use first separator found

    if not candidates:
        return ""

    # Return the most frequent candidate
    best = max(candidates, key=candidates.get)
    return _clean_name(best)


def _contains_ingredient(text: str, ingredient_names: set) -> bool:
    text_lower = text.lower()
    return any(name in text_lower for name in ingredient_names)


def _name_from_domain(domain: str) -> str:
    """Convert domain to a reasonable company name."""
    # Strip TLD(s)
    name_part = domain
    # Handle multi-part TLDs (.co.uk, .com.hk, etc.)
    for multi_tld in (".co.uk", ".com.hk", ".com.cn", ".co.jp", ".co.kr",
                       ".com.au", ".com.br", ".co.in"):
        if name_part.endswith(multi_tld):
            name_part = name_part[: -len(multi_tld)]
            break
    else:
        # Strip single TLD
        last_dot = name_part.rfind(".")
        if last_dot > 0:
            name_part = name_part[:last_dot]

    # Convert hyphens to spaces, title-case
    name_part = name_part.replace("-", " ").replace("_", " ")
    return name_part.title().strip()


def _clean_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    name = name.rstrip(".,;:-")
    return name


# === Stage 3: Supplier type classification ===


def _classify_supplier_type(results: List[RawSearchResult]) -> str:
    combined_text = " ".join(
        f"{r.title} {r.snippet}" for r in results
    ).lower()

    scores: Dict[str, int] = {}
    for stype, signals in TYPE_SIGNALS.items():
        total = sum(weight for term, weight in signals if term in combined_text)
        if total >= TYPE_MIN_SCORE:
            scores[stype] = total

    if not scores:
        return "unknown"

    # Tiebreaker: prefer manufacturer
    best_score = max(scores.values())
    if scores.get("manufacturer", 0) == best_score:
        return "manufacturer"
    return max(scores, key=scores.get)


# === Stage 4: Country inference ===


def _infer_country(domain: str, results: List[RawSearchResult]) -> str:
    # Source A: ccTLD
    for tld, country in sorted(CCTLD_TO_COUNTRY.items(), key=lambda x: -len(x[0])):
        if domain.endswith(tld):
            return country

    # Source B: snippet keywords
    combined = " ".join(r.snippet for r in results).lower()
    for keyword, country in COUNTRY_KEYWORDS.items():
        if keyword in combined:
            return country

    return ""


# === Stage 5: Evidence hint detection ===


def _detect_evidence(results: List[RawSearchResult]) -> _Evidence:
    product_page = False
    pdf = False
    tech_doc = False

    for r in results:
        url_lower = r.url.lower()
        path = urlparse(r.url).path.lower()

        # Product page check
        if any(seg in path for seg in PRODUCT_PAGE_SEGMENTS):
            product_page = True

        # PDF check
        if url_lower.endswith(".pdf"):
            pdf = True

        # Technical doc check
        text_lower = f"{r.title} {r.snippet}".lower()
        if any(term in text_lower for term in TECHNICAL_DOC_TERMS):
            tech_doc = True

    return _Evidence(
        website_found=True,
        product_page_found=product_page,
        pdf_found=pdf,
        technical_doc_likely=tech_doc,
    )


# === Stage 5b: Offer construction ===


def _build_offers(
    results: List[RawSearchResult],
    canonical_name: str,
    supplier_name: str,
) -> List[dict]:
    seen_urls: set = set()
    offers: List[dict] = []
    for r in results:
        if r.url in seen_urls:
            continue
        seen_urls.add(r.url)
        label = _clean_offer_label(r.title, supplier_name)
        offers.append({
            "offer_label": label,
            "matched_name": canonical_name,
            "source_url": r.url,
        })
    return offers


def _clean_offer_label(title: str, supplier_name: str) -> str:
    """Remove trailing company name from title."""
    for sep in TITLE_SEPARATORS:
        if sep in title:
            parts = title.split(sep)
            # If last part matches supplier name, drop it
            if parts[-1].strip().lower() == supplier_name.lower():
                return sep.join(parts[:-1]).strip()
    return title


# === Stage 6: Merge and confidence ===


def _merge_key(name: str) -> str:
    key = name.lower().strip()
    key = COMPANY_SUFFIXES.sub("", key)
    key = re.sub(r"[^a-z0-9\s]", "", key)
    key = re.sub(r"\s+", " ", key).strip()
    return key


def _merge_candidates(
    protos: List[_ProtoCandidate],
) -> List[InternalCandidate]:
    merged: Dict[str, _ProtoCandidate] = {}

    for p in protos:
        key = _merge_key(p.supplier_name)
        if key in merged:
            existing = merged[key]
            # Merge: keep the one with more results as primary
            if p.result_count > existing.result_count:
                primary, secondary = p, existing
            else:
                primary, secondary = existing, p

            # Union offers (dedup by source_url)
            seen_urls = {o["source_url"] for o in primary.offers}
            for o in secondary.offers:
                if o["source_url"] not in seen_urls:
                    primary.offers.append(o)
                    seen_urls.add(o["source_url"])

            # Keep more specific type
            if primary.supplier_type == "unknown" and secondary.supplier_type != "unknown":
                primary.supplier_type = secondary.supplier_type

            # Keep more specific country
            if not primary.country and secondary.country:
                primary.country = secondary.country

            # OR evidence hints
            primary.evidence.product_page_found |= secondary.evidence.product_page_found
            primary.evidence.pdf_found |= secondary.evidence.pdf_found
            primary.evidence.technical_doc_likely |= secondary.evidence.technical_doc_likely

            primary.result_count += secondary.result_count
            merged[key] = primary
        else:
            merged[key] = p

    # Convert to InternalCandidate with confidence
    candidates: List[InternalCandidate] = []
    for p in merged.values():
        confidence = _assign_confidence(p)
        reason = _build_reason(p, confidence)
        candidates.append(
            InternalCandidate(
                supplier_name=p.supplier_name,
                supplier_type=p.supplier_type,
                country=p.country,
                website=p.website,
                offers=p.offers,
                website_found=p.evidence.website_found,
                product_page_found=p.evidence.product_page_found,
                pdf_found=p.evidence.pdf_found,
                technical_doc_likely=p.evidence.technical_doc_likely,
                confidence=confidence,
                reason=reason,
            )
        )

    # Sort: high confidence first, then by result count
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    candidates.sort(key=lambda c: (confidence_order.get(c.confidence, 3), -len(c.offers)))

    return candidates


def _assign_confidence(p: _ProtoCandidate) -> str:
    has_type = p.supplier_type != "unknown"
    has_evidence = p.evidence.product_page_found or p.evidence.technical_doc_likely
    multi_results = p.result_count >= 2

    if has_type and has_evidence and multi_results:
        return "high"
    if has_type or has_evidence:
        return "medium"
    return "low"


def _build_reason(p: _ProtoCandidate, confidence: str) -> str:
    type_label = p.supplier_type.title() if p.supplier_type != "unknown" else "Supplier"
    parts = [f"{type_label} found via web search ({p.result_count} result(s))"]

    evidence_parts: List[str] = []
    if p.evidence.product_page_found:
        evidence_parts.append("product page found")
    if p.evidence.pdf_found:
        evidence_parts.append("PDF available")
    if p.evidence.technical_doc_likely:
        evidence_parts.append("technical docs likely")

    if evidence_parts:
        parts.append("; ".join(evidence_parts))

    return "; ".join(parts)


# === Gemini-enhanced classification ===


def _classify_with_gemini(
    domain: str,
    results: List[RawSearchResult],
    gemini_client: GeminiClient,
) -> Optional[str]:
    """Use Gemini to classify supplier type for ambiguous cases."""
    try:
        from competitor_layer.gemini_client import SupplierClassification
        from competitor_layer.prompts import SUPPLIER_CLASSIFICATION_PROMPT

        results_text = "\n".join(
            f"- Title: {r.title}\n  Snippet: {r.snippet}" for r in results[:5]
        )
        prompt = SUPPLIER_CLASSIFICATION_PROMPT.format(
            domain=domain,
            results_text=results_text,
        )
        result = gemini_client.generate(prompt, SupplierClassification)
        if result and result.supplier_type in (
            "manufacturer", "distributor", "reseller", "unknown"
        ):
            return result.supplier_type
    except Exception as e:
        logger.warning("Gemini classification failed for %s: %s", domain, e)
    return None

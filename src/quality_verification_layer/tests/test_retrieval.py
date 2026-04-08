"""Tests for evidence retrieval module."""

from __future__ import annotations

from quality_verification_layer.id_generator import QualityIdGenerator
from quality_verification_layer.retrieval import FetchedSource, _status_from_fetch
from quality_verification_layer.schemas import (
    CandidateSupplier,
    EvidenceStatus,
    IngredientRef,
    SupplierRef,
)


class TestStatusMapping:
    def test_ok_source_is_retrieved(self):
        src = FetchedSource("https://x.com", "html", "content", ok=True)
        assert _status_from_fetch(src) == EvidenceStatus.retrieved

    def test_403_is_blocked(self):
        src = FetchedSource("https://x.com", "", "[HTTP 403]", ok=False)
        assert _status_from_fetch(src) == EvidenceStatus.blocked

    def test_http_error_is_unreachable(self):
        src = FetchedSource("https://x.com", "", "[HTTP 500]", ok=False)
        assert _status_from_fetch(src) == EvidenceStatus.unreachable

    def test_parse_error_is_parse_failed(self):
        src = FetchedSource("https://x.com", "", "[PDF parse error: bad]", ok=False)
        assert _status_from_fetch(src) == EvidenceStatus.parse_failed

    def test_generic_error_is_unreachable(self):
        src = FetchedSource("https://x.com", "", "[Error: timeout]", ok=False)
        assert _status_from_fetch(src) == EvidenceStatus.unreachable


class TestFetchedSource:
    def test_evidence_id_tracking(self):
        src = FetchedSource("https://x.com", "html", "text", ok=True, evidence_id="EVID-001")
        assert src.evidence_id == "EVID-001"

    def test_pdf_content_type(self):
        src = FetchedSource("https://x.com/file.pdf", "pdf", "pdf text", ok=True)
        assert src.content_type == "pdf"


class TestIdGenerator:
    def test_evidence_ids_sequential(self):
        gen = QualityIdGenerator("SUP-001")
        assert gen.next_evidence_id() == "EVID-SUP-001-001"
        assert gen.next_evidence_id() == "EVID-SUP-001-002"

    def test_attribute_ids_sequential(self):
        gen = QualityIdGenerator("SUP-001")
        assert gen.next_attribute_id() == "ATTR-SUP-001-001"

    def test_verification_ids_sequential(self):
        gen = QualityIdGenerator("SUP-001")
        assert gen.next_verification_id() == "VER-SUP-001-001"

    def test_ids_scoped_to_supplier(self):
        gen1 = QualityIdGenerator("S1")
        gen2 = QualityIdGenerator("S2")
        assert gen1.next_evidence_id() == "EVID-S1-001"
        assert gen2.next_evidence_id() == "EVID-S2-001"

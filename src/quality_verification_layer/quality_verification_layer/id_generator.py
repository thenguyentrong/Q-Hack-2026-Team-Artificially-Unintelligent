"""ID generation for evidence, attributes, and verification results."""

from __future__ import annotations


class QualityIdGenerator:
    """Generates unique IDs scoped to a supplier."""

    def __init__(self, supplier_id: str) -> None:
        self._slug = supplier_id
        self._evid = 0
        self._attr = 0
        self._ver = 0

    def next_evidence_id(self) -> str:
        self._evid += 1
        return f"EVID-{self._slug}-{self._evid:03d}"

    def next_attribute_id(self) -> str:
        self._attr += 1
        return f"ATTR-{self._slug}-{self._attr:03d}"

    def next_verification_id(self) -> str:
        self._ver += 1
        return f"VER-{self._slug}-{self._ver:03d}"

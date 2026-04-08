"""
IdGenerator: produces stable, deterministic RequirementRule IDs.

ID format: REQ-{ING_CODE}-{SEQ:03d}
Example:   REQ-ASCORBIC-ACID-001
"""

from __future__ import annotations

import re


class IdGenerator:
    """
    Generates stable requirement IDs from an ingredient_id.

    The ingredient_id slug is derived from the ingredient_id by stripping
    the 'ING-' prefix and lower-casing, so that IDs remain consistent
    across runs regardless of order.
    """

    def __init__(self, ingredient_id: str) -> None:
        slug = re.sub(r"^ING-", "", ingredient_id, flags=re.IGNORECASE)
        # Keep alphanumeric and hyphens; collapse anything else
        slug = re.sub(r"[^A-Z0-9-]", "-", slug.upper())
        slug = re.sub(r"-+", "-", slug).strip("-")
        self._slug = slug
        self._counter = 0

    def next_id(self) -> str:
        self._counter += 1
        return f"REQ-{self._slug}-{self._counter:03d}"

    def reset(self) -> None:
        self._counter = 0

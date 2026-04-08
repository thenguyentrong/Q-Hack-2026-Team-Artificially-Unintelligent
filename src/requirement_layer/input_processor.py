"""InputProcessor: validates and normalizes Layer 1 input payloads."""

from __future__ import annotations

import json

from pydantic import ValidationError

from src.requirement_layer.schemas.models import (
    ErrorResponse,
    IngredientContext,
    Layer1Input,
)

# Unit normalization mapping: accepted synonyms → canonical unit
UNIT_ALIASES: dict[str, str] = {
    "mg/kg": "ppm",
    "milligram per kilogram": "ppm",
    "percent": "%",
    "percentage": "%",
    "micrometre": "um",
    "micrometer": "um",
    "µm": "um",
    "deg c": "celsius",
    "°c": "celsius",
    "degrees celsius": "celsius",
}

# Default context applied when caller omits the context field
DEFAULT_CONTEXT = IngredientContext(product_category=None, region="global")


class InputProcessor:
    """Parses, validates, and normalises a Layer 1 JSON input."""

    def load_from_dict(self, data: dict) -> Layer1Input:
        try:
            payload = Layer1Input.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"Input validation failed: {exc}") from exc
        return self._normalize(payload)

    def load_from_json(self, raw_json: str) -> Layer1Input:
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc
        return self.load_from_dict(data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalize(self, payload: Layer1Input) -> Layer1Input:
        """Apply defaults and clean ingredient aliases."""
        if payload.context is None:
            object.__setattr__(payload, "context", DEFAULT_CONTEXT)

        # Normalize aliases: strip whitespace, deduplicate, keep canonical
        aliases = list(
            dict.fromkeys(a.strip() for a in payload.ingredient.aliases if a.strip()),
        )
        object.__setattr__(payload.ingredient, "aliases", aliases)

        return payload

    # ------------------------------------------------------------------
    # Error helpers
    # ------------------------------------------------------------------

    @staticmethod
    def build_error(message: str, detail: str | None = None) -> ErrorResponse:
        return ErrorResponse(error=message, detail=detail)

    @staticmethod
    def normalize_unit(unit: str) -> str:
        """Return the canonical form of a unit string."""
        return UNIT_ALIASES.get(unit.lower().strip(), unit.strip())

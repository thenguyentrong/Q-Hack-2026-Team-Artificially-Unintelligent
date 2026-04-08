"""
RuleValidator: validates and normalises individual RequirementRule objects.

Responsibilities:
- Enforce rule_type-specific field constraints.
- Normalize units using InputProcessor.normalize_unit.
- Return a fully validated RequirementRule or raise ValueError.
"""

from __future__ import annotations

from src.requirement_layer.input_processor import InputProcessor
from src.requirement_layer.schemas.models import RequirementRule, RuleType


class RuleValidator:
    """Validates and normalises a RequirementRule dict before model creation."""

    def validate_and_build(self, raw: dict) -> RequirementRule:
        """
        Accepts a raw dict describing a requirement rule, normalises it,
        and returns a validated RequirementRule Pydantic model.
        """
        raw = dict(raw)  # avoid mutating caller's data

        # Normalize unit if present
        if raw.get("unit"):
            raw["unit"] = InputProcessor.normalize_unit(raw["unit"])

        # Infer operator if missing, based on rule_type
        if not raw.get("operator"):
            raw["operator"] = self._default_operator(raw.get("rule_type", ""))

        # Pydantic will enforce rule_type-specific field validation via model_validator
        return RequirementRule.model_validate(raw)

    # ------------------------------------------------------------------

    @staticmethod
    def _default_operator(rule_type: str) -> str:
        defaults = {
            RuleType.range.value: "between",
            RuleType.minimum.value: ">=",
            RuleType.maximum.value: "<=",
            RuleType.enum_match.value: "in",
            RuleType.boolean_required.value: "==",
            RuleType.free_text_reference.value: "reference",
        }
        return defaults.get(rule_type, "==")

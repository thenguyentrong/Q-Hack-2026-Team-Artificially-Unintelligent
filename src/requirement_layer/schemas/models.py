"""Pydantic models for Layer 1 Requirements Layer input and output contracts."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class IngredientRef(BaseModel):
    ingredient_id: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)


class IngredientContext(BaseModel):
    product_category: str | None = None
    region: str | None = None


class Layer1Input(BaseModel):
    schema_version: str = "1.0"
    ingredient: IngredientRef
    context: IngredientContext | None = None
    baseline_supplier: dict | None = None


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------


class RequirementRule(BaseModel):
    requirement_id: str = ""
    field_name: str
    rule_type: RuleType
    operator: str
    priority: Priority
    source_reference: str
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: list[str] | None = None
    required: bool | None = None
    reference_text: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_rule_fields(self) -> RequirementRule:
        rt = self.rule_type
        if rt == RuleType.range:
            if self.min_value is None or self.max_value is None:
                raise ValueError(
                    "rule_type 'range' requires both min_value and max_value",
                )
            if self.min_value > self.max_value:
                raise ValueError("min_value must be <= max_value for rule_type 'range'")
        elif rt == RuleType.minimum:
            if self.min_value is None:
                raise ValueError("rule_type 'minimum' requires min_value")
        elif rt == RuleType.maximum:
            if self.max_value is None:
                raise ValueError("rule_type 'maximum' requires max_value")
        elif rt == RuleType.enum_match:
            if not self.allowed_values:
                raise ValueError("rule_type 'enum_match' requires allowed_values")
        elif rt == RuleType.boolean_required:
            if self.required is None:
                raise ValueError(
                    "rule_type 'boolean_required' requires the 'required' field",
                )
        elif rt == RuleType.free_text_reference:
            if not self.reference_text:
                raise ValueError(
                    "rule_type 'free_text_reference' requires reference_text",
                )
        return self


class Layer1Output(BaseModel):
    schema_version: str = "1.0"
    ingredient_id: str
    requirements: list[RequirementRule]
    notes: str | None = None


# ---------------------------------------------------------------------------
# Error response model
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    schema_version: str = "1.0"
    error: str
    detail: str | None = None

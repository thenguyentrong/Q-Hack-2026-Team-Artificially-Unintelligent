"""OutputFormatter: serialises RequirementRule objects into the Layer 1 output contract."""

from __future__ import annotations

import json
from pathlib import Path

from src.requirement_layer.schemas.models import Layer1Output, RequirementRule


class OutputFormatter:
    """Converts validated RequirementRule objects into the Layer 1 JSON output."""

    def build(
        self,
        ingredient_id: str,
        requirements: list[RequirementRule],
        notes: str | None = None,
    ) -> Layer1Output:
        return Layer1Output(
            ingredient_id=ingredient_id,
            requirements=requirements,
            notes=notes,
        )

    def to_dict(self, output: Layer1Output) -> dict:
        return output.model_dump(exclude_none=True, mode="json")

    def to_json(self, output: Layer1Output, indent: int = 2) -> str:
        return json.dumps(self.to_dict(output), indent=indent, ensure_ascii=False)

    def write_file(
        self,
        output: Layer1Output,
        path: str | Path,
        indent: int = 2,
    ) -> None:
        Path(path).write_text(self.to_json(output, indent=indent), encoding="utf-8")

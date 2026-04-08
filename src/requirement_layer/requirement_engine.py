"""
RequirementEngine: an LLM agent powered by Google Gemini (via google-genai) that
retrieves ingredient requirements via Google Search Grounding.

Architecture:
1. Agent uses Google Search Grounding to find standards data
2. Agent synthesises raw text into structured RequirementRule dicts
3. RequirementRule objects are validated by RuleValidator + IdGenerator

Environment variables:
  GEMINI_API_KEY  - Required for the Gemini agent (Google AI Studio key)
"""

from __future__ import annotations

import json
import logging
import os
import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from id_generator import IdGenerator
from model_config import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_MODEL,
    DEFAULT_RETRY_DELAY,
    GEMINI_TOOLS,
)
from prompts import SYSTEM_PROMPT
from rule_validator import RuleValidator
from schemas.models import (
    IngredientContext,
    IngredientRef,
    RequirementRule,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RequirementEngine agent (Gemini)
# ---------------------------------------------------------------------------


class RequirementEngine:
    """
    LLM agent (Google Gemini) that fetches ingredient requirements via Google Search.

    Then parses and validates the results into RequirementRule objects.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> None:
        resolved_key = api_key or os.getenv("GEMINI_API_KEY")
        if not resolved_key:
            raise OSError("GEMINI_API_KEY is required for the RequirementEngine agent")

        self._client = genai.Client(api_key=resolved_key)
        self._model = model or DEFAULT_MODEL
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._validator = RuleValidator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        ingredient: IngredientRef,
        context: IngredientContext | None = None,
        ingredient_id: str | None = None,
    ) -> list[RequirementRule]:
        """
        Run the agent loop and return a validated list of RequirementRule objects.
        """
        ing_id = ingredient_id or ingredient.ingredient_id
        id_gen = IdGenerator(ing_id)

        region = (context.region or "global") if context else "global"
        product_category = (
            (context.product_category or "general") if context else "general"
        )

        user_message = (
            f"Generate quality requirements for ingredient: '{ingredient.canonical_name}'. "
            f"Region: {region}. Product category: {product_category}. "
            f"Aliases: {', '.join(ingredient.aliases) if ingredient.aliases else 'none'}."
        )

        # Gemini maintains conversation history as a list of Content objects
        history: list[types.Content] = []
        history.append(
            types.Content(role="user", parts=[types.Part(text=user_message)]),
        )

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=GEMINI_TOOLS,
        )

        response = self._generate_with_retry(history, config)
        candidate = response.candidates[0]
        text_parts = [p.text for p in candidate.content.parts if p.text]
        raw_rules: list[dict] = (
            self._parse_rules("\n".join(text_parts)) if text_parts else []
        )

        return self._validate_rules(raw_rules, id_gen)

    def _generate_with_retry(
        self,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ):
        delay = self._retry_delay
        for attempt in range(self._max_retries):
            try:
                return self._client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                )
            except genai_errors.ClientError as exc:
                if exc.status_code == 429 and attempt < self._max_retries - 1:
                    logger.warning(
                        "Rate limited (429). Retrying in %.0fs (attempt %d/%d)...",
                        delay,
                        attempt + 1,
                        self._max_retries,
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_rules(content: str) -> list[dict]:
        """Extract a JSON array from the LLM's text response."""
        text = content.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.splitlines()
            inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            text = "\n".join(inner).strip()

        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "requirements" in parsed:
                return parsed["requirements"]
        except json.JSONDecodeError as exc:
            logger.error(
                "Failed to parse LLM response as JSON: %s\nContent: %s",
                exc,
                content[:500],
            )

        return []

    def _validate_rules(
        self,
        raw_rules: list[dict],
        id_gen: IdGenerator,
    ) -> list[RequirementRule]:
        """Validate each raw rule dict and assign stable IDs."""
        validated: list[RequirementRule] = []
        for raw in raw_rules:
            try:
                rule = self._validator.validate_and_build(raw)
                rule_with_id = rule.model_copy(
                    update={"requirement_id": id_gen.next_id()},
                )
                validated.append(rule_with_id)
            except Exception as exc:
                logger.warning(
                    "Skipping invalid rule %s: %s",
                    raw.get("field_name", "?"),
                    exc,
                )
        return validated

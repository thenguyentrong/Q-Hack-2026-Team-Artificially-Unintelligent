"""Gemini client wrapper for structured LLM reasoning."""

from __future__ import annotations

import json
import logging
from typing import List, Optional, Type, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

FALLBACK_MODEL = "gemini-2.5-flash"


# --- Response schemas ---


class SynonymExpansion(BaseModel):
    additional_names: List[str]
    industry_queries: List[str]


class SupplierReasoning(BaseModel):
    reason: str


class SupplierClassification(BaseModel):
    supplier_type: str
    confidence: str
    explanation: str


# --- Client ---


class GeminiClient:
    """Wrapper around Google GenAI SDK with structured output and fallback."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._fallback_model = FALLBACK_MODEL if model != FALLBACK_MODEL else None

    def is_available(self) -> bool:
        return self._client is not None

    def generate(
        self,
        prompt: str,
        response_schema: Type[T],
        temperature: float = 0,
    ) -> Optional[T]:
        """Generate structured output from Gemini.

        Returns parsed Pydantic model on success, None on failure.
        Falls back to fallback model if primary fails.
        """
        result = self._try_generate(prompt, response_schema, self._model, temperature)
        if result is not None:
            return result

        # Try fallback model
        if self._fallback_model:
            logger.warning(
                "Primary model %s failed, trying fallback %s",
                self._model,
                self._fallback_model,
            )
            return self._try_generate(
                prompt, response_schema, self._fallback_model, temperature
            )

        return None

    def _try_generate(
        self,
        prompt: str,
        response_schema: Type[T],
        model: str,
        temperature: float,
    ) -> Optional[T]:
        try:
            from google.genai import types

            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=temperature,
                ),
            )

            if not response.text:
                logger.warning("Empty response from Gemini model %s", model)
                return None

            return response_schema.model_validate_json(response.text)

        except Exception as e:
            logger.warning("Gemini call failed (model=%s): %s", model, e)
            return None


def create_gemini_client(
    api_key: Optional[str], model: str = "gemini-2.5-flash"
) -> Optional[GeminiClient]:
    """Create a GeminiClient if API key is available."""
    if not api_key:
        return None
    try:
        return GeminiClient(api_key=api_key, model=model)
    except Exception as e:
        logger.warning("Failed to create Gemini client: %s", e)
        return None

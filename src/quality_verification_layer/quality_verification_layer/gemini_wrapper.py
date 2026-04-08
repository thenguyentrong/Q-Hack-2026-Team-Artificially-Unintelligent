"""Thin Gemini wrapper for the quality verification layer."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_gemini_client(api_key: Optional[str], model: str = "gemini-2.5-flash"):
    """Create a Google GenAI client. Returns None if no API key."""
    if not api_key:
        return None
    try:
        from google import genai

        return genai.Client(api_key=api_key)
    except Exception as e:
        logger.warning("Failed to create Gemini client: %s", e)
        return None


def call_gemini_raw(prompt: str, client, model: str = "gemini-2.5-flash") -> Optional[str]:
    """Call Gemini and return raw text response. Returns None on failure."""
    if client is None:
        return None
    try:
        from google.genai import types

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0,
            ),
        )
        return response.text if response.text else None
    except Exception as e:
        logger.warning("Gemini call failed: %s", e)
        return None

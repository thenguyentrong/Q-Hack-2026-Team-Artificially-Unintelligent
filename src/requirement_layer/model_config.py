"""Model configuration and tool declarations for the Gemini-backed RequirementEngine."""

import os

from google.genai import types

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemma-4-31b-it")
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 10.0

GEMINI_TOOLS = [
    types.Tool(google_search=types.GoogleSearch()),
]

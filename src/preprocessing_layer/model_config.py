"""Model configuration for the preprocessing layer."""

import os

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemma-4-31b-it")

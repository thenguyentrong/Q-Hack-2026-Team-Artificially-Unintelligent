"""Configuration for the Agnes Competitor Layer."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class CompetitorConfig:
    gemini_api_key: Optional[str]
    gemini_model: str
    max_candidates: int
    ranking_enabled: bool
    google_api_key: Optional[str]
    google_cse_id: Optional[str]
    search_engine: str
    search_results_per_query: int
    search_delay: float


def load_config(env_file: Optional[str] = None) -> CompetitorConfig:
    """Load configuration from .env file and environment variables.

    Precedence: explicit env vars > .env file > defaults.
    """
    if env_file:
        load_dotenv(env_file)
    else:
        # Walk up from this file to find .env in the package root
        pkg_root = Path(__file__).resolve().parent.parent
        load_dotenv(pkg_root / ".env")

    return CompetitorConfig(
        gemini_api_key=os.environ.get("GEMINI_API_KEY") or None,
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-pro"),
        max_candidates=int(os.environ.get("COMPETITOR_MAX_CANDIDATES", "10")),
        ranking_enabled=os.environ.get(
            "COMPETITOR_RANKING_ENABLED", "true"
        ).lower()
        in ("true", "1", "yes"),
        google_api_key=os.environ.get("GOOGLE_API_KEY") or None,
        google_cse_id=os.environ.get("GOOGLE_CSE_ID") or None,
        search_engine=os.environ.get("COMPETITOR_SEARCH_ENGINE", "auto"),
        search_results_per_query=int(
            os.environ.get("COMPETITOR_SEARCH_RESULTS_PER_QUERY", "10")
        ),
        search_delay=float(os.environ.get("COMPETITOR_SEARCH_DELAY", "1.0")),
    )

"""Configuration for the Quality Verification Layer."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class QualityVerificationConfig:
    gemini_api_key: Optional[str]
    gemini_model: str
    max_evidence_per_supplier: int
    rate_limit_delay: float
    fetch_timeout: int


def load_config(env_file: Optional[str] = None) -> QualityVerificationConfig:
    """Load configuration from .env file and environment variables."""
    if env_file:
        load_dotenv(env_file)
    else:
        pkg_root = Path(__file__).resolve().parent.parent
        load_dotenv(pkg_root / ".env")

    return QualityVerificationConfig(
        gemini_api_key=os.environ.get("GEMINI_API_KEY") or None,
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        max_evidence_per_supplier=int(os.environ.get("QV_MAX_EVIDENCE_PER_SUPPLIER", "10")),
        rate_limit_delay=float(os.environ.get("QV_RATE_LIMIT_DELAY", "1.0")),
        fetch_timeout=int(os.environ.get("QV_FETCH_TIMEOUT", "20")),
    )

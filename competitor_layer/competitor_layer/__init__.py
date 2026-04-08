"""Agnes Competitor Layer - supplier discovery for CPG ingredient sourcing."""

__version__ = "0.1.0"

from competitor_layer.runner import run_competitor_layer, run_from_file, run_from_json
from competitor_layer.schemas import CompetitorInput, CompetitorOutput

__all__ = [
    "CompetitorInput",
    "CompetitorOutput",
    "run_competitor_layer",
    "run_from_json",
    "run_from_file",
]

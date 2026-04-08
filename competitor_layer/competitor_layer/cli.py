"""CLI entrypoint for the Agnes Competitor Layer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from competitor_layer.config import load_config
from competitor_layer.runner import run_competitor_layer
from competitor_layer.schemas import CompetitorInput


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agnes Competitor Layer - supplier discovery for CPG ingredients"
    )
    parser.add_argument(
        "input_file",
        help="Path to input JSON file",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Output compact JSON (no indentation)",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "mock", "search"],
        default=None,
        help="Execution mode: auto (default from config), mock, or search (Google)",
    )
    args = parser.parse_args()

    # Read and parse input
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        raw = input_path.read_text()
        input_data = CompetitorInput.model_validate(json.loads(raw))
    except Exception as e:
        print(f"Error: invalid input: {e}", file=sys.stderr)
        sys.exit(1)

    # Run
    config = load_config()
    if args.mode == "mock":
        config = _with_search_engine(config, "mock")
    elif args.mode == "search":
        config = _with_search_engine(config, "duckduckgo")
    output = run_competitor_layer(input_data, config)

    # Print result
    indent = None if args.compact else 2
    print(output.model_dump_json(indent=indent))


def _with_search_engine(config, engine: str):
    """Return a new config with a different search_engine."""
    from dataclasses import asdict

    d = asdict(config)
    d["search_engine"] = engine
    from competitor_layer.config import CompetitorConfig

    return CompetitorConfig(**d)


if __name__ == "__main__":
    main()

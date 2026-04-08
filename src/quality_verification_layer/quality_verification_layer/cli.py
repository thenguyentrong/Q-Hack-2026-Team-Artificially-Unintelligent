"""CLI entrypoint for the Agnes Quality Verification Layer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .runner import run_quality_verification
from .schemas import QualityVerificationInput


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agnes Quality Verification Layer"
    )
    parser.add_argument("input_file", help="Path to input JSON file")
    parser.add_argument(
        "-o", "--output",
        help="Path to write output JSON (default: stdout)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Output compact JSON (no indentation)",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        raw = input_path.read_text()
        input_data = QualityVerificationInput.model_validate(json.loads(raw))
    except Exception as e:
        print(f"Error: invalid input: {e}", file=sys.stderr)
        sys.exit(1)

    config = load_config()
    output = run_quality_verification(input_data, config)

    indent = None if args.compact else 2
    result = output.model_dump_json(indent=indent)

    if args.output:
        Path(args.output).write_text(result)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()

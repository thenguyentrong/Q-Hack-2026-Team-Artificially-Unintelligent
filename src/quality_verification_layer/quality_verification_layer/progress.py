"""Single-line overwriting progress display."""

from __future__ import annotations

import sys

_CLEAR = "\033[2K\r"  # ANSI: clear entire line + carriage return
_DIM = "\033[2m"
_RESET = "\033[0m"


def status(msg: str) -> None:
    """Print a temporary status line that overwrites itself."""
    truncated = msg[:100] if len(msg) > 100 else msg
    sys.stdout.write(f"{_CLEAR}       {_DIM}{truncated}{_RESET}")
    sys.stdout.flush()


def clear() -> None:
    """Clear the status line."""
    sys.stdout.write(f"{_CLEAR}")
    sys.stdout.flush()

"""Direct script entrypoint for running the guard from the repository."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    """Run the local CLI entrypoint."""
    guard_root = Path(__file__).resolve().parents[1]

    if str(guard_root) not in sys.path:
        sys.path.insert(0, str(guard_root))

    from code_verification_guard.main import app

    app()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

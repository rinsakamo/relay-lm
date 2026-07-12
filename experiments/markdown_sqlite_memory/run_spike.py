#!/usr/bin/env python3
"""Launcher for the isolated spike CLI (keeps the package off sys.path hacks
in production code — the experiment is not an installed package on purpose).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mdsqlite_spike.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

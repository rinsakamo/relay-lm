#!/usr/bin/env python3
"""Entry point for the non-destructive repository/storage inventory tool.

See scripts/relaylm_repo_inventory/ for the implementation. Run with
--self-test for internal consistency checks, or --storage/--invocations/
--config/--all to generate a report (--format json|markdown, --output PATH).
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from relaylm_repo_inventory.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

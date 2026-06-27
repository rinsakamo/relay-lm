#!/usr/bin/env python3
"""Compatibility wrapper for the O1A scheduler contract smoke name."""
from __future__ import annotations

from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

runpy.run_path(str(ROOT / "scripts" / "relaylm_o1a_two_lane_scheduler_contract_smoke.py"), run_name="__main__")

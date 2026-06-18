#!/usr/bin/env python3
"""Run the explicit Phase 5-C4a authority smoke suite."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    "relaylm_phase5c4a_compiler_smoke.py",
    "relaylm_phase5c4a_runtime_smoke.py",
    "relaylm_phase5c4a_source_smoke.py",
    "relaylm_phase5c4a_renderer_smoke.py",
    "relaylm_phase5c4a_fields_explicit_smoke.py",
    "relaylm_phase5c4a_cache_smoke.py",
    "relaylm_phase5c4a_optional_explicit_smoke.py",
    "relaylm_phase5c4a_gate_explicit_smoke.py",
    "relaylm_phase5c4a_projection_smoke.py",
    "relaylm_phase5c4a_audit_explicit_smoke.py",
    "relaylm_phase5c4a_error_explicit_smoke.py",
)


def main() -> int:
    for name in SCRIPTS:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / name)],
            check=True,
            cwd=ROOT,
        )
    print("relaylm_phase5c4a_suite_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

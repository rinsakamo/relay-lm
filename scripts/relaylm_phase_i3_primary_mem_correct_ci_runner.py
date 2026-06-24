"""Run Phase I-3 functional, security, and fault smokes in isolated processes."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    "relaylm_phase_i3_primary_mem_correct_smoke.py",
    "relaylm_phase_i3_primary_mem_correct_security_smoke.py",
    "relaylm_phase_i3_primary_mem_correct_fault_smoke.py",
)


def main() -> None:
    for name in SCRIPTS:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / name)],
            cwd=ROOT,
            check=True,
        )
    print("Phase I-3 Primary MEM Correct CI runner passed")


if __name__ == "__main__":
    main()

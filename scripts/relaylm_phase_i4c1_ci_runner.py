"""Run all Phase I-4C1 hidden-successor smokes."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    "relaylm_phase_i4c1_primary_forget_hidden_successor_smoke.py",
    "relaylm_phase_i4c1_primary_forget_fault_smoke.py",
    "relaylm_phase_i4c1_primary_forget_concurrency_smoke.py",
    "relaylm_phase_i4c1_primary_forget_security_smoke.py",
)


def main() -> None:
    for name in SCRIPTS:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / name)],
            cwd=ROOT,
            check=True,
        )
    print("Phase I-4C1 CI runner passed")


if __name__ == "__main__":
    main()

"""CI runner for Phase I-1 two-turn Primary MEM recall."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    for script in (
        "scripts/relaylm_phase_i1_two_turn_primary_recall_security_smoke.py",
        "scripts/relaylm_phase_i1_two_turn_primary_recall_smoke.py",
        "scripts/relaylm_documentation_current_boundary_smoke.py",
    ):
        subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, check=True)
    print("Phase I-1 two-turn Primary MEM recall CI runner passed")


if __name__ == "__main__":
    main()

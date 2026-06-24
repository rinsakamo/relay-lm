from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_smoke(script_name: str) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script_name)],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    run_smoke("relaylm_phase_i2_lab_observation_smoke.py")
    run_smoke("relaylm_phase_i2_lab_observation_security_smoke.py")
    run_smoke("relaylm_soul_lab_management_projection_smoke.py")
    run_smoke("relaylm_phase_i2_documentation_boundary_smoke.py")
    print("Phase I-2 Lab observation CI runner passed")


if __name__ == "__main__":
    main()

"""Run all Phase I-4B resolver, fence, Forget, and security smokes."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    "relaylm_phase_i4b_primary_current_state_resolver_smoke.py",
    "relaylm_phase_i4b_primary_mutation_fence_smoke.py",
    "relaylm_phase_i4b_primary_forget_preflight_smoke.py",
    "relaylm_phase_i4b_primary_forget_security_smoke.py",
)


def main() -> None:
    for name in SCRIPTS:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / name)],
            cwd=ROOT,
            check=True,
        )
    print("Phase I-4B CI runner passed")


if __name__ == "__main__":
    main()

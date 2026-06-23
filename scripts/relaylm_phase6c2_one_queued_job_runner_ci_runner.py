"""Bounded CI runner for the Phase 6-C2 one queued-job integration suite."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    "scripts/relaylm_phase6c2_one_queued_job_runner_smoke.py",
    "scripts/relaylm_phase6c2_one_queued_job_runner_security_smoke.py",
)
PROTECTED_MARKERS = (
    "CANARY_RUNTIME_USER_MESSAGE_DO_NOT_LEAK",
    "CANARY_RUNTIME_ASSISTANT_RESPONSE_DO_NOT_LEAK",
    "CANARY_RUNTIME_MEMORY_SUMMARY_DO_NOT_LEAK",
    "CANARY_RUNTIME_NAMESPACE_DO_NOT_LEAK",
    "slp-dispatch-v0:",
    "slp-job-v0:",
)


def main() -> int:
    environment = dict(os.environ)
    prefix = os.pathsep.join((str(REPO_ROOT), str(REPO_ROOT / "scripts")))
    existing = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = prefix if not existing else prefix + os.pathsep + existing
    for script in SCRIPTS:
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / script)],
            cwd=REPO_ROOT,
            env=environment,
            capture_output=True,
            check=False,
            timeout=180,
        )
        combined = result.stdout + result.stderr
        if any(marker.encode("utf-8") in combined for marker in PROTECTED_MARKERS):
            print(f"Phase 6-C2 suite: FAILED ({Path(script).name}: protected_output)")
            return 1
        if result.returncode != 0:
            print(f"Phase 6-C2 suite: FAILED ({Path(script).name}: nonzero_exit)")
            return 1
    print("Phase 6-C2 one queued-job integration suite: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

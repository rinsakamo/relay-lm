"""Bounded CI runner for O0 local one-job functional and security coverage."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    "scripts/relaylm_o0_local_one_job_runner_smoke.py",
    "scripts/relaylm_o0_local_one_job_runner_security_smoke.py",
    "scripts/relaylm_o0_local_one_job_runner_contract_smoke.py",
)
PROTECTED_MARKERS = (
    "CANARY_RUNTIME_USER_MESSAGE_DO_NOT_LEAK",
    "CANARY_RUNTIME_ASSISTANT_RESPONSE_DO_NOT_LEAK",
    "CANARY_RUNTIME_MEMORY_SUMMARY_DO_NOT_LEAK",
    "CANARY_RUNTIME_NAMESPACE_DO_NOT_LEAK",
    "CANARY_O0_EXCEPTION_TEXT_DO_NOT_LEAK",
    "/CANARY/O0/PATH/DO_NOT/LEAK",
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
            timeout=240,
        )
        combined = result.stdout + result.stderr
        if any(marker.encode("utf-8") in combined for marker in PROTECTED_MARKERS):
            print(f"O0 suite: FAILED ({Path(script).name}: protected_output)")
            return 1
        if result.returncode != 0:
            print(f"O0 suite: FAILED ({Path(script).name}: nonzero_exit)")
            sys.stdout.buffer.write(combined[-8192:])
            return 1
    print("O0 local one-job runner suite: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

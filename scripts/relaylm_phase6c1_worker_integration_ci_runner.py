"""Bounded, content-free CI runner for the Phase 6-C1-4 worker suite."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC = REPO_ROOT / "phase6c1-worker-integration-diagnostic.txt"
TIMEOUT_SECONDS = 120

SCRIPTS = (
    "scripts/relaylm_phase6c1_worker_fault_smoke.py",
    "scripts/relaylm_phase6c1_worker_crash_convergence_smoke.py",
    "scripts/relaylm_phase6c1_worker_lease_race_smoke.py",
    "scripts/relaylm_phase6c1_worker_corruption_smoke.py",
    "scripts/relaylm_phase6c1_worker_content_leakage_smoke.py",
    "scripts/relaylm_phase6c1_primary_worker_smoke.py",
    "scripts/relaylm_phase6c1_primary_worker_security_smoke.py",
    "scripts/relaylm_phase6c1_primary_worker_fault_smoke.py",
    "scripts/relaylm_relaymem_primary_pipeline_checkpoint_smoke.py",
    "scripts/relaylm_phase6b3_queue_state_smoke.py",
    "scripts/relaylm_phase6c1_primary_worker_source_smoke.py",
    "scripts/relaylm_phase6c1_primary_worker_outcome_smoke.py",
    "scripts/relaylm_phase6c1_fault_injection_smoke.py",
    "scripts/relaylm_phase6c1_fault_race_smoke.py",
    "scripts/relaylm_relaymem_primary_pipeline_smoke.py",
    "scripts/relaylm_relaymem_primary_pipeline_security_smoke.py",
    "scripts/relaylm_relaymem_primary_page_writer_smoke.py",
    "scripts/relaylm_relaymem_primary_index_log_apply_smoke.py",
    "scripts/relaylm_relaymem_primary_index_log_recovery_audit_smoke.py",
    "scripts/relaylm_phase6c1_worker_contract_smoke.py",
    "scripts/relaylm_docs_link_check.py",
)

PROTECTED_OUTPUT_MARKERS = (
    "CANARY_G_WORKER_MESSAGE_DO_NOT_LEAK",
    "CANARY_G_WORKER_SUMMARY_DO_NOT_LEAK",
    "CANARY_G_NAMESPACE_DO_NOT_LEAK",
    "CANARY_G_DISPATCH_KEY_DO_NOT_LEAK",
    "CANARY_G_MEMORY_KEY_DO_NOT_LEAK",
    "CANARY_G_LEASE_TOKEN_DO_NOT_LEAK",
    "CANARY_G_QUEUE_PATH_DO_NOT_LEAK",
    "CANARY_G_STORE_PATH_DO_NOT_LEAK",
    "CANARY_WORKER_RAW_MESSAGE_DO_NOT_LEAK",
    "CANARY_WORKER_SUMMARY_DO_NOT_LEAK",
    "CANARY_WORKER_NAMESPACE_DO_NOT_LEAK",
    "CANARY_WORKER_LEASE_TOKEN_DO_NOT_LEAK",
    "CANARY_RAW_MESSAGE_DO_NOT_LEAK",
    "CANARY_MEMORY_SUMMARY_DO_NOT_LEAK",
)


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:  # pragma: no cover - Linux CI owns this workflow
        process.kill()
    try:
        process.wait(timeout=5.0)
    except subprocess.TimeoutExpired:  # pragma: no cover - defensive
        pass


def _write_diagnostic(
    *,
    failed_script: str,
    reason: str,
    completed_count: int,
) -> None:
    DIAGNOSTIC.write_text(
        "\n".join(
            (
                "schema_version: relaylm.phase6c1_worker_integration_diagnostic.v0",
                "content_free: true",
                "private_output_included: false",
                f"failed_script: {Path(failed_script).name}",
                f"failure_reason: {reason}",
                f"completed_script_count: {completed_count}",
                "",
            )
        ),
        encoding="utf-8",
    )


def _run_script(script: str) -> tuple[bool, str]:
    env = dict(os.environ)
    pythonpath = os.pathsep.join((str(REPO_ROOT), str(REPO_ROOT / "scripts")))
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = pythonpath if not existing else pythonpath + os.pathsep + existing
    process = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / script)],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=(os.name == "posix"),
    )
    try:
        stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        _terminate(process)
        return False, "timeout"
    combined = stdout + stderr
    if any(marker.encode("utf-8") in combined for marker in PROTECTED_OUTPUT_MARKERS):
        return False, "protected_output_detected"
    if process.returncode != 0:
        return False, "nonzero_exit"
    return True, "passed"


def main() -> int:
    DIAGNOSTIC.unlink(missing_ok=True)
    for completed_count, script in enumerate(SCRIPTS):
        passed, reason = _run_script(script)
        if not passed:
            _write_diagnostic(
                failed_script=script,
                reason=reason,
                completed_count=completed_count,
            )
            print(
                "Phase 6-C1 integrated worker fault suite: FAILED "
                f"({Path(script).name})"
            )
            return 1
    DIAGNOSTIC.unlink(missing_ok=True)
    print("Phase 6-C1 integrated worker fault suite: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from _relaylm_o1f_support import assert_public_result_safe, initial_record, operational_config, require, stale_claimed_record, write_record
from relaylm.relaymem_slp_queue_state import RelayMEMSLPQueueTransitionRequest, transition_relaymem_slp_queue_state
from relaylm.relaymem_slp_scheduler_operational_validation import validate_scheduler_operational_boundary_once

NOW = datetime(2026, 6, 22, 0, 0, 3, tzinfo=timezone.utc)


def main() -> int:
    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        write_record(root, stale_claimed_record())
        config = operational_config(mode="apply", stale="apply", queue_root=root)
        results: list[object] = []

        def run_validation() -> None:
            results.append(validate_scheduler_operational_boundary_once(config=config, now=NOW))

        threads = [Thread(target=run_validation), Thread(target=run_validation)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        require(len(results) == 2, results)
        applied = 0
        for result in results:
            assert_public_result_safe(result)
            require(result.status in {"validated", "operation_unsafe"}, result.projection())
            operation = result.operation_result
            if operation is not None and operation.stale_recovery_applied:
                applied += 1
        require(applied == 1, [result.projection() for result in results])

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = initial_record()
        write_record(root, record)
        request = RelayMEMSLPQueueTransitionRequest(
            transition_kind="claim",
            job_id=str(record["job_id"]),
            dispatch_idempotency_key=str(record["dispatch_idempotency_key"]),
            expected_record_revision=0,
            expected_state="queued",
            claim_owner="worker_o1f",
            claim_generation=0,
            lease_duration_seconds=60,
        )
        claim_results = []

        def claim() -> None:
            claim_results.append(
                transition_relaymem_slp_queue_state(
                    request,
                    queue_root=str(root),
                    enabled=True,
                    dry_run_only=False,
                    apply_enabled=True,
                )
            )

        threads = [Thread(target=claim), Thread(target=claim)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        applied_claims = sum(1 for result in claim_results if result.status == "applied")
        safe_failures = {"blocked", "conflict", "write_failed"}
        require(applied_claims == 1, [result.status for result in claim_results])
        require(all(result.status == "applied" or result.status in safe_failures for result in claim_results), [result.status for result in claim_results])

    print("ok O1F concurrency validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)

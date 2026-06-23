"""Production-worker fault integration smoke for Phase 6-C1-4."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import relaylm.relaymem_primary_pipeline as pipeline
import relaylm.relaymem_slp_queue_state as queue_state
from relaylm.relaymem_slp_primary_worker import execute_relaymem_slp_primary_worker
from relaylm.relaymem_slp_queue_record import parse_timestamp, record_filename

from _relaylm_phase6c1_fault_fixtures import (
    build_claimed_job_fixture,
    build_m3g_lock_contention_fixture,
    build_m3h_lock_contention_fixture,
)
from relaylm_phase6c1_primary_worker_fault_smoke import transition
from relaylm_phase6c1_primary_worker_smoke import (
    normal_success_and_duplicate,
    outcome_mapping,
)
from relaylm_phase6c1_primary_worker_test_support import (
    build_request,
    read_record,
    require,
)


def _claim_again(
    queue_root: Path,
    queued: dict[str, object],
    *,
    owner: str,
    token: str,
) -> tuple[dict[str, object], object]:
    retry_at = parse_timestamp(queued.get("retry_not_before"))
    require(retry_at is not None, "retry_not_before missing")
    resume_at = retry_at + timedelta(seconds=1)
    with (
        patch.object(queue_state, "_new_lease_token", return_value=token),
        patch.object(queue_state, "_now_utc", return_value=resume_at),
    ):
        result = transition(
            queue_root,
            queued,
            "claim",
            claim_owner=owner,
            lease_duration_seconds=300,
        )
    require(result.status == "applied", result.to_log_dict())
    require(type(result.durable_record) is dict, "new claim record missing")
    return dict(result.durable_record), resume_at


def m3g_process_lock_contention_retries_then_converges() -> None:
    with build_claimed_job_fixture() as queue_fixture:
        queue_root = queue_fixture.queue_root
        canonical = queue_fixture.canonical_record
        require(queue_root is not None and canonical is not None, "queue fixture missing")
        queue_path = queue_root / record_filename(
            str(canonical["dispatch_idempotency_key"])
        )

        with build_m3g_lock_contention_fixture() as store_fixture:
            store_root = store_fixture.store_root
            require(store_root is not None, "M3g store fixture missing")
            lock_holder = store_fixture.private_artifacts["lock_holder"]
            require(lock_holder.running, "M3g lock holder not running")
            index_path = store_root / "memory/mem/index.md"
            log_path = store_root / "memory/mem/log.md"
            index_before = index_path.read_bytes()
            log_before = log_path.read_bytes()
            pages_before = len(
                list((store_root / "memory/mem/primary/projects").glob("*.md"))
            )

            request, _ = build_request(
                queue_root,
                store_root,
                record=dict(canonical),
            )
            result = execute_relaymem_slp_primary_worker(request)
            require(result.status == "retry_released", result.to_log_dict())
            require(result.pipeline_result is not None, "M3g pipeline missing")
            require(
                result.pipeline_result.m3g_result["status"] == "blocked",
                result.to_log_dict(),
            )
            require(
                "primary_reconciliation_apply_lock_unavailable"
                in result.pipeline_result.m3g_result["blocked_reasons"],
                result.to_log_dict(),
            )
            require(index_path.read_bytes() == index_before, "M3g contended index changed")
            require(log_path.read_bytes() == log_before, "M3g contended log changed")
            require(
                len(list((store_root / "memory/mem/primary/projects").glob("*.md")))
                == pages_before + 1,
                "M3e page not retained before M3g retry",
            )
            queued = read_record(queue_path)
            require(queued["state"] == "queued", "M3g contention not released")
            require(
                queued["retry_class"] == "transient_lock_contention",
                "M3g retry class",
            )
            require(
                queued["failure_class"] == "resource_contention",
                "M3g failure class",
            )
            require(queued["claim_owner"] == "", "M3g retry owner retained")
            require(queued["lease_token"] == "", "M3g retry token retained")

            lock_holder.release()
            require(not lock_holder.running, "M3g lock holder cleanup")
            retry_record, resume_at = _claim_again(
                queue_root,
                queued,
                owner="worker-c1-4-m3g-retry",
                token="phase6c1-c1-4-m3g-token-b",
            )
            retry_request, _ = build_request(
                queue_root,
                store_root,
                record=retry_record,
            )
            with patch.object(queue_state, "_now_utc", return_value=resume_at):
                converged = execute_relaymem_slp_primary_worker(retry_request)
            require(converged.status == "terminal_succeeded", converged.to_log_dict())
            require(converged.pipeline_result is not None, "M3g convergence missing")
            require(
                converged.pipeline_result.m3e_result["status"] == "already_applied",
                converged.to_log_dict(),
            )
            require(read_record(queue_path)["state"] == "succeeded", "M3g convergence")
            require(
                len(list((store_root / "memory/mem/primary/projects").glob("*.md")))
                == pages_before + 1,
                "M3g retry duplicated page",
            )
            require(
                index_path.read_text(encoding="utf-8").count(
                    "relaymem-primary-index-entry-v0"
                )
                == 1,
                "M3g retry duplicated index",
            )
            require(
                log_path.read_text(encoding="utf-8").count(
                    "relaymem-primary-log-entry-v0"
                )
                == 1,
                "M3g retry duplicated log",
            )


def m3h_process_lock_contention_retries_then_converges() -> None:
    with build_claimed_job_fixture() as queue_fixture:
        queue_root = queue_fixture.queue_root
        canonical = queue_fixture.canonical_record
        require(queue_root is not None and canonical is not None, "queue fixture missing")
        queue_path = queue_root / record_filename(
            str(canonical["dispatch_idempotency_key"])
        )

        with build_m3h_lock_contention_fixture() as store_fixture:
            store_root = store_fixture.store_root
            require(store_root is not None, "M3h store fixture missing")
            lock_holder = store_fixture.private_artifacts["lock_holder"]
            require(lock_holder.running, "M3h lock holder not running")
            index_path = store_root / "memory/mem/index.md"
            log_path = store_root / "memory/mem/log.md"
            index_before = index_path.read_bytes()
            log_before = log_path.read_bytes()
            pages_before = len(
                list((store_root / "memory/mem/primary/projects").glob("*.md"))
            )
            m3g_applied = dict(store_fixture.private_artifacts["m3g_result"])

            request, _ = build_request(
                queue_root,
                store_root,
                record=dict(canonical),
            )
            with patch.object(
                pipeline,
                "apply_relaymem_primary_index_log_reconciliation",
                return_value=m3g_applied,
            ):
                result = execute_relaymem_slp_primary_worker(request)
            require(result.status == "retry_released", result.to_log_dict())
            require(result.pipeline_result is not None, "M3h pipeline missing")
            require(
                result.pipeline_result.m3h_result["status"] == "blocked",
                result.to_log_dict(),
            )
            require(
                "primary_reconciliation_recovery_lock_unavailable"
                in result.pipeline_result.m3h_result["blocked_reasons"],
                result.to_log_dict(),
            )
            require(index_path.read_bytes() == index_before, "M3h audit changed index")
            require(log_path.read_bytes() == log_before, "M3h audit changed log")
            queued = read_record(queue_path)
            require(queued["state"] == "queued", "M3h contention not released")
            require(
                queued["retry_class"] == "transient_lock_contention",
                "M3h retry class",
            )
            require(
                queued["failure_class"] == "resource_contention",
                "M3h failure class",
            )

            lock_holder.release()
            require(not lock_holder.running, "M3h lock holder cleanup")
            retry_record, resume_at = _claim_again(
                queue_root,
                queued,
                owner="worker-c1-4-m3h-retry",
                token="phase6c1-c1-4-m3h-token-b",
            )
            retry_request, _ = build_request(
                queue_root,
                store_root,
                record=retry_record,
            )
            with patch.object(queue_state, "_now_utc", return_value=resume_at):
                converged = execute_relaymem_slp_primary_worker(retry_request)
            require(converged.status == "terminal_succeeded", converged.to_log_dict())
            require(read_record(queue_path)["state"] == "succeeded", "M3h convergence")
            require(
                len(list((store_root / "memory/mem/primary/projects").glob("*.md")))
                == pages_before + 1,
                "M3h retry duplicated page",
            )
            require(
                index_path.read_text(encoding="utf-8").count(
                    "relaymem-primary-index-entry-v0"
                )
                == 2,
                "M3h retry index convergence",
            )
            require(
                log_path.read_text(encoding="utf-8").count(
                    "relaymem-primary-log-entry-v0"
                )
                == 2,
                "M3h retry log convergence",
            )


def main() -> int:
    normal_success_and_duplicate()
    m3g_process_lock_contention_retries_then_converges()
    m3h_process_lock_contention_retries_then_converges()
    outcome_mapping()
    print("Phase 6-C1 integrated worker fault smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

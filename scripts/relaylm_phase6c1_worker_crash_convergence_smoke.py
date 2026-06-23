"""Integrated crash and partial-reconciliation convergence smoke for C1-4."""
from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from relaylm import _relaymem_primary_index_log_apply_io as apply_io
import relaylm.relaymem_primary_pipeline as pipeline
from relaylm.relaymem_slp_primary_worker import execute_relaymem_slp_primary_worker
from relaylm.relaymem_slp_primary_worker_source import (
    validate_relaymem_slp_primary_worker_source,
)
from relaylm.relaymem_slp_queue_record import parse_timestamp

from relaylm_phase6c1_primary_worker_fault_smoke import (
    checkpoint_losses,
    m3e_crash_new_claim_convergence,
    transition,
)
from relaylm_phase6c1_primary_worker_test_support import (
    build_request,
    claimed_record,
    fixed_queue_time,
    prepare_store,
    read_record,
    require,
    write_record,
)


def index_only_partial_state_converges() -> None:
    """Create the canonical M3g index-before-log partial state and retry it."""

    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-c1-4-index-partial")
        queue_path = write_record(queue_root, record)
        prepare_store(store_root)
        request, first_scope = build_request(queue_root, store_root, record=record)

        real_m3g = pipeline.apply_relaymem_primary_index_log_reconciliation
        original_replace = apply_io.os.replace
        replace_calls = 0

        def fail_log_replace(*args: object, **kwargs: object) -> None:
            nonlocal replace_calls
            replace_calls += 1
            if replace_calls == 2:
                raise OSError("phase6c1_c1_4_injected_log_replace_failure")
            original_replace(*args, **kwargs)

        def apply_with_fault(**kwargs: object):
            apply_io.os.replace = fail_log_replace
            try:
                return real_m3g(**kwargs)
            finally:
                apply_io.os.replace = original_replace

        try:
            with (
                fixed_queue_time(),
                patch.object(
                    pipeline,
                    "apply_relaymem_primary_index_log_reconciliation",
                    side_effect=apply_with_fault,
                ),
            ):
                partial = execute_relaymem_slp_primary_worker(request)
        finally:
            apply_io.os.replace = original_replace

        require(partial.status == "retry_released", partial.to_log_dict())
        require(partial.queue_transition_performed, partial.to_log_dict())
        require(partial.pipeline_result is not None, "partial pipeline missing")
        require(
            partial.pipeline_result.m3g_result["status"]
            == "index_applied_log_pending",
            partial.to_log_dict(),
        )
        require(
            partial.pipeline_result.m3h_result["recovery_classification"]
            == "retry_reconciliation",
            partial.to_log_dict(),
        )

        queued = read_record(queue_path)
        require(queued["state"] == "queued", "partial retry not queued")
        require(
            queued["retry_class"] == "primary_reconciliation_retry",
            "partial retry class",
        )
        require(
            queued["failure_class"] == "partial_progress_verified",
            "partial failure class",
        )
        require(queued["claim_owner"] == "", "retry owner not cleared")
        require(queued["lease_token"] == "", "retry token not cleared")
        require(queued["lease_acquired_at"] is None, "retry acquired lease retained")
        require(queued["lease_expires_at"] is None, "retry expiry retained")
        require(
            (store_root / "memory/mem/index.md")
            .read_text(encoding="utf-8")
            .count("relaymem-primary-index-entry-v0")
            == 1,
            "partial index missing",
        )
        require(
            (store_root / "memory/mem/log.md")
            .read_text(encoding="utf-8")
            .count("relaymem-primary-log-entry-v0")
            == 0,
            "partial log unexpectedly applied",
        )

        consumed, consumed_reasons = validate_relaymem_slp_primary_worker_source(
            request.worker_source,
            claimed_record=request.claimed_record,
            request_scope=first_scope,
        )
        require(consumed is None, "consumed source reusable")
        require(
            consumed_reasons == ("worker_source_already_consumed",),
            "consumed source reason",
        )

        retry_ready_at = parse_timestamp(queued["retry_not_before"])
        require(retry_ready_at is not None, "partial retry not-before missing")
        with fixed_queue_time(retry_ready_at):
            claim_result = transition(
                queue_root,
                queued,
                "claim",
                claim_owner="worker-c1-4-partial-retry",
                lease_duration_seconds=300,
            )
        require(claim_result.status == "applied", claim_result.to_log_dict())
        require(type(claim_result.durable_record) is dict, "retry claim missing")
        retry_record = dict(claim_result.durable_record)
        retry_request, retry_scope = build_request(
            queue_root,
            store_root,
            record=retry_record,
        )
        require(retry_scope is not first_scope, "fresh source scope required")

        with fixed_queue_time(retry_ready_at):
            converged = execute_relaymem_slp_primary_worker(retry_request)
        require(converged.status == "terminal_succeeded", converged.to_log_dict())
        require(converged.pipeline_result is not None, "converged pipeline missing")
        require(
            converged.pipeline_result.m3e_result["status"] == "already_applied",
            converged.to_log_dict(),
        )
        durable = read_record(queue_path)
        require(durable["state"] == "succeeded", "partial state did not converge")
        require(durable["state"] != "dead_letter", "dead-letter introduced")
        require(
            len(list((store_root / "memory/mem/primary/projects").glob("*.md")))
            == 1,
            "duplicate page",
        )
        require(
            (store_root / "memory/mem/index.md")
            .read_text(encoding="utf-8")
            .count("relaymem-primary-index-entry-v0")
            == 1,
            "duplicate index",
        )
        require(
            (store_root / "memory/mem/log.md")
            .read_text(encoding="utf-8")
            .count("relaymem-primary-log-entry-v0")
            == 1,
            "duplicate log",
        )


def _run_case(name: str, function: Callable[[], None]) -> None:
    try:
        function()
    except Exception:
        print(f"C1_4_SAFE_FAILURE:{name}", file=sys.stderr)
        raise


def main() -> int:
    _run_case("checkpoint_losses", checkpoint_losses)
    _run_case("m3e_crash_convergence", m3e_crash_new_claim_convergence)
    _run_case("index_partial_convergence", index_only_partial_state_converges)
    print("Phase 6-C1 integrated worker crash convergence smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

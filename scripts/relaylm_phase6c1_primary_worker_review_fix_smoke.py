"""Focused smoke for the final-review fixes on Phase 6-C1-2."""
from __future__ import annotations

import runpy
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import relaylm.relaymem_primary_pipeline as pipeline
import relaylm.relaymem_slp_queue_state as queue_state
from relaylm._relaymem_slp_primary_worker_outcome_adapter import (
    MAX_WORKER_ATTEMPTS,
    _bounded_outcome_and_retry,
)
from relaylm.relaymem_slp_primary_worker import (
    REQUEST_SCHEMA,
    RelayMEMSLPPrimaryWorkerRequest,
    execute_relaymem_slp_primary_worker,
)
from relaylm.relaymem_slp_primary_worker_outcome import (
    RelayMEMSLPPrimaryWorkerOutcome,
)
from relaylm.relaymem_slp_primary_worker_source_adapter import (
    prepare_relaymem_slp_primary_worker_source_for_claim,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_queue_record import parse_timestamp, record_filename
from relaylm.relaymem_slp_runtime_enqueue import apply_relaymem_slp_runtime_enqueue

from relaylm_phase6c1_primary_worker_test_support import (
    build_request,
    claimed_record,
    fixed_queue_time,
    m3g_result,
    prepare_store,
    read_record,
    require,
    write_record,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
_RUNTIME = runpy.run_path(
    str(REPO_ROOT / "scripts/relaylm_phase6_runtime_enqueue_source_capture_smoke.py"),
    run_name="relaylm_phase6c1_review_source_support",
)
CHARACTER_ID = _RUNTIME["CHARACTER_ID"]
finalized = _RUNTIME["finalized"]
claim = _RUNTIME["claim"]


def technical_failure_is_not_policy() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-worker-review-technical")
        queue_path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record)
        with (
            fixed_queue_time(),
            patch.object(
                pipeline,
                "build_relaymem_primary_formation_dry_run",
                side_effect=OSError("bounded technical failure"),
            ),
        ):
            result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "pipeline_blocked", result.to_log_dict())
        require(not result.queue_transition_performed, result.to_log_dict())
        require(read_record(queue_path)["state"] == "claimed", read_record(queue_path))
        require(
            result.outcome_result is not None
            and result.outcome_result.transition_kind == "blocked_invalid_input",
            result.to_log_dict(),
        )


def retry_policy_is_internal_and_bounded() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-worker-review-retry")
        queue_path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record)
        with (
            fixed_queue_time(),
            patch.object(
                pipeline,
                "apply_relaymem_primary_index_log_reconciliation",
                return_value=m3g_result(
                    "blocked", "primary_reconciliation_apply_lock_unavailable"
                ),
            ),
        ):
            result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "retry_released", result.to_log_dict())
        durable = read_record(queue_path)
        retry_at = parse_timestamp(durable["retry_not_before"])
        updated = parse_timestamp(durable["updated_at"])
        require(retry_at is not None and updated is not None and retry_at > updated, durable)

    invalid_request, _ = build_request(
        Path("/tmp/unused-queue"),
        Path("/tmp/unused-store"),
        record=claimed_record(run_id="run-worker-review-caller-retry"),
    )
    invalid = execute_relaymem_slp_primary_worker(
        replace(invalid_request, retry_not_before="2026-06-24T00:00:00.000000Z")
    )
    require(invalid.status == "invalid_input", invalid.to_log_dict())
    require(
        "primary_worker_retry_not_before_caller_owned" in invalid.reason_ids,
        invalid.to_log_dict(),
    )

    retry = RelayMEMSLPPrimaryWorkerOutcome(
        status="classified",
        transition_kind="retry_release",
        terminal_state="",
        retry_class="transient_lock_contention",
        failure_class="resource_contention",
        terminal_reason_id="",
        retryable=True,
        terminal=False,
        policy_held=False,
        manual_confirmation_required=False,
        recovery_isolation_required=False,
        durable_success_verified=False,
        blocked_reason_ids=(),
    )
    exhausted = claimed_record(run_id="run-worker-review-exhausted")
    exhausted["attempt_count"] = MAX_WORKER_ATTEMPTS
    exhausted["claim_generation"] = MAX_WORKER_ATTEMPTS
    terminal, retry_not_before = _bounded_outcome_and_retry(retry, exhausted)
    require(terminal.transition_kind == "commit_failed", terminal)
    require(terminal.terminal_reason_id == "primary_mem_retry_attempt_limit_reached", terminal)
    require(retry_not_before is None, retry_not_before)


def _worker_request(
    queue_root: Path,
    store_root: Path,
    claimed: dict[str, object],
    prepared,
) -> RelayMEMSLPPrimaryWorkerRequest:
    require(prepared.status == "prepared", prepared.to_log_dict())
    require(prepared.source is not None, prepared.to_log_dict())
    require(prepared.request_scope is not None, prepared.to_log_dict())
    return RelayMEMSLPPrimaryWorkerRequest(
        schema_version=REQUEST_SCHEMA,
        runtime_private=True,
        content_included=True,
        claimed_record=dict(claimed),
        worker_source=prepared.source,
        request_scope=prepared.request_scope,
        queue_root=str(queue_root),
        store_root=str(store_root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
        lease_duration_seconds=300,
        retry_not_before=None,
    )


def registry_retry_retains_source_and_converges() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
        prepare_store(store_root)
        applied = apply_relaymem_slp_runtime_enqueue(
            finalized(),
            registry=registry,
            queue_root=str(queue_root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        require(applied.status == "enqueued", applied.to_log_dict())
        require(applied.enqueue_result is not None, applied.to_log_dict())
        queued = applied.enqueue_result.durable_record
        require(type(queued) is dict, applied.to_log_dict())
        claimed = claim(queue_root, queued)
        prepared = prepare_relaymem_slp_primary_worker_source_for_claim(
            registry,
            claimed_record=claimed,
            character_id=CHARACTER_ID,
        )
        with patch.object(
            pipeline,
            "apply_relaymem_primary_index_log_reconciliation",
            return_value=m3g_result(
                "blocked", "primary_reconciliation_apply_lock_unavailable"
            ),
        ):
            first = execute_relaymem_slp_primary_worker(
                _worker_request(queue_root, store_root, claimed, prepared)
            )
        require(first.status == "retry_released", first.to_log_dict())
        prepared.release_prepared_scope()
        require(registry.size == 1, registry)
        queued_again = first.queue_transition_result.durable_record
        require(type(queued_again) is dict and queued_again["state"] == "queued", queued_again)
        retry_at = parse_timestamp(queued_again["retry_not_before"])
        require(retry_at is not None, queued_again)

        original_now = queue_state._now_utc
        queue_state._now_utc = lambda: retry_at + timedelta(seconds=1)
        try:
            claimed_again = claim(queue_root, queued_again)
            prepared_again = prepare_relaymem_slp_primary_worker_source_for_claim(
                registry,
                claimed_record=claimed_again,
                character_id=CHARACTER_ID,
            )
            second = execute_relaymem_slp_primary_worker(
                _worker_request(queue_root, store_root, claimed_again, prepared_again)
            )
        finally:
            queue_state._now_utc = original_now
        require(second.status == "terminal_succeeded", second.to_log_dict())
        prepared_again.release_prepared_scope()
        terminal = second.queue_transition_result.durable_record
        require(type(terminal) is dict and terminal["state"] == "succeeded", terminal)
        released = registry.release(
            durable_record=terminal,
            character_id=CHARACTER_ID,
        )
        require(released.status == "released", released.to_log_dict())
        require(registry.size == 0, registry)
        queue_path = queue_root / record_filename(str(terminal["dispatch_idempotency_key"]))
        durable = read_record(queue_path)
        require(durable["state"] == "succeeded", durable)
        require(
            (store_root / "memory/mem/index.md").read_text().count(
                "relaymem-primary-index-entry-v0"
            )
            == 1,
            "duplicate index",
        )
        require(
            (store_root / "memory/mem/log.md").read_text().count(
                "relaymem-primary-log-entry-v0"
            )
            == 1,
            "duplicate log",
        )


def main() -> int:
    technical_failure_is_not_policy()
    retry_policy_is_internal_and_bounded()
    registry_retry_retains_source_and_converges()
    print("Phase 6-C1 final-review fix smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Functional smoke for the Phase 6-C1-2 one already-claimed job worker."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import relaylm.relaymem_primary_pipeline as pipeline
import relaylm.relaymem_slp_primary_worker as worker
from relaylm.relaymem_slp_primary_worker import (
    build_relaymem_slp_primary_worker_node_result,
    execute_relaymem_slp_primary_worker,
    project_relaymem_slp_primary_worker,
)
from relaylm.relaymem_slp_primary_worker_source import (
    validate_relaymem_slp_primary_worker_source,
)

from relaylm_phase6c1_primary_worker_test_support import (
    assert_no_canary,
    build_request,
    claimed_record,
    fixed_queue_time,
    full_m3h,
    m3g_result,
    prepare_store,
    read_record,
    require,
    write_record,
)


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def normal_success_and_duplicate() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record()
        queue_path = write_record(queue_root, record)
        prepare_store(store_root)
        request, scope = build_request(queue_root, store_root, record=record)
        counts = {"compose": 0, "classifier": 0}
        real_compose = worker.execute_relaymem_primary_pipeline
        real_classifier = worker.classify_relaymem_slp_primary_worker_outcome

        def counted_compose(*args, **kwargs):
            counts["compose"] += 1
            return real_compose(*args, **kwargs)

        def counted_classifier(*args, **kwargs):
            counts["classifier"] += 1
            return real_classifier(*args, **kwargs)

        with (
            fixed_queue_time(),
            patch.object(worker, "execute_relaymem_primary_pipeline", side_effect=counted_compose),
            patch.object(worker, "classify_relaymem_slp_primary_worker_outcome", side_effect=counted_classifier),
        ):
            result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "terminal_succeeded", result.to_log_dict())
        require(counts == {"compose": 1, "classifier": 1}, counts)
        require(result.lease_renewal_count == 2, result.to_log_dict())
        require(result.queue_transition_performed, result.to_log_dict())
        durable = read_record(queue_path)
        require(durable["state"] == "succeeded", durable)
        require(durable["terminal_reason_id"] == "primary_mem_durable_state_verified", durable)
        require(durable["record_revision"] == 4, durable)
        pages = list((store_root / "memory/mem/primary/projects").glob("*.md"))
        require(len(pages) == 1, pages)
        require((store_root / "memory/mem/index.md").read_text().count("relaymem-primary-index-entry-v0") == 1, "index")
        require((store_root / "memory/mem/log.md").read_text().count("relaymem-primary-log-entry-v0") == 1, "log")
        exact, reasons = validate_relaymem_slp_primary_worker_source(
            request.worker_source,
            claimed_record=request.claimed_record,
            request_scope=scope,
        )
        require(exact is None and reasons == ("worker_source_already_consumed",), reasons)
        before = snapshot(store_root), queue_path.read_bytes()
        with fixed_queue_time():
            duplicate = execute_relaymem_slp_primary_worker(request)
        require(duplicate.status == "lease_invalid_before_source", duplicate.to_log_dict())
        require(before == (snapshot(store_root), queue_path.read_bytes()), "unsafe duplicate mutation")
        projection = project_relaymem_slp_primary_worker(result).to_log_dict()
        node = build_relaymem_slp_primary_worker_node_result(result).to_log_dict()
        assert_no_canary(projection, queue_root, store_root, record["claim_owner"], record["lease_token"])
        assert_no_canary(node, queue_root, store_root, record["claim_owner"], record["lease_token"])
        assert_no_canary(repr(result), queue_root, store_root)


def gates_and_validation() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record()
        queue_path = write_record(queue_root, record)
        prepare_store(store_root)
        request, scope = build_request(
            queue_root, store_root, record=record,
            enabled=False, dry_run_only=True, apply_enabled=False,
        )
        before = queue_path.read_bytes(), snapshot(store_root)
        with (
            fixed_queue_time(),
            patch.object(worker, "execute_relaymem_primary_pipeline") as compose,
        ):
            disabled = execute_relaymem_slp_primary_worker(request)
        require(disabled.status == "disabled" and not compose.called, disabled.to_log_dict())
        require(before == (queue_path.read_bytes(), snapshot(store_root)), "disabled mutation")
        exact, reasons = validate_relaymem_slp_primary_worker_source(
            request.worker_source, claimed_record=record, request_scope=scope
        )
        require(exact is request.worker_source and not reasons, reasons)

    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-worker-dry")
        queue_path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(
            queue_root, store_root, record=record,
            dry_run_only=True, apply_enabled=False,
        )
        before = queue_path.read_bytes(), snapshot(store_root)
        with fixed_queue_time():
            result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "dry_run_ready", result.to_log_dict())
        require(result.lease_renewal_count == 0, result.to_log_dict())
        require(not result.queue_transition_performed, result.to_log_dict())
        require(before == (queue_path.read_bytes(), snapshot(store_root)), "dry-run mutation")

        invalids = (
            {},
            replace(request, schema_version="wrong.worker.v0"),
            replace(request, enabled=True, dry_run_only=False, apply_enabled=False),
            replace(request, enabled=1),
            replace(request, lease_duration_seconds=True),
            replace(request, queue_root=Path(queue_root)),
            replace(request, store_root=""),
        )
        for invalid in invalids:
            outcome = execute_relaymem_slp_primary_worker(invalid)
            require(outcome.status == "invalid_input", outcome.to_log_dict())


def pre_source_fences() -> None:
    variants = {
        "revision": {"record_revision": 2},
        "owner": {"claim_owner": "different-worker"},
        "token": {"lease_token": "different-lease-token"},
        "generation": {"record_revision": 2, "claim_generation": 2, "attempt_count": 2},
    }
    for name, changes in variants.items():
        with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
            queue_root, store_root = Path(queue_dir), Path(store_dir)
            canonical = claimed_record(run_id=f"run-fence-{name}")
            path = write_record(queue_root, canonical)
            supplied = dict(canonical)
            supplied.update(changes)
            prepare_store(store_root)
            request, scope = build_request(queue_root, store_root, record=supplied)
            with fixed_queue_time():
                result = execute_relaymem_slp_primary_worker(request)
            require(result.status == "lease_invalid_before_source", (name, result.to_log_dict()))
            exact, reasons = validate_relaymem_slp_primary_worker_source(
                request.worker_source, claimed_record=supplied, request_scope=scope
            )
            require(exact is request.worker_source and not reasons, (name, reasons))
            require(read_record(path)["state"] == "claimed", name)

    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        canonical = claimed_record(run_id="run-fence-expired")
        write_record(queue_root, canonical)
        prepare_store(store_root)
        request, scope = build_request(queue_root, store_root, record=canonical)
        expiry = datetime.fromisoformat(str(canonical["lease_expires_at"])[:-1] + "+00:00")
        with fixed_queue_time(expiry):
            result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "lease_invalid_before_source", result.to_log_dict())
        exact, reasons = validate_relaymem_slp_primary_worker_source(
            request.worker_source, claimed_record=canonical, request_scope=scope
        )
        require(exact is request.worker_source and not reasons, reasons)


def run_outcome_case(
    name: str,
    *,
    scene_type: str = "design_talk",
    m3g: dict[str, object] | None = None,
    m3h: dict[str, object] | None = None,
    expected_status: str,
    expected_state: str,
    retry_class: str | None = None,
    failure_class: str | None = None,
) -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id=f"run-outcome-{name}")
        path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record, scene_type=scene_type)
        contexts = []
        if m3g is not None:
            contexts.append(patch.object(pipeline, "apply_relaymem_primary_index_log_reconciliation", return_value=m3g))
        if m3h is not None:
            contexts.append(patch.object(pipeline, "audit_relaymem_primary_index_log_reconciliation_recovery", return_value=m3h))
        with fixed_queue_time():
            for context in contexts:
                context.__enter__()
            try:
                result = execute_relaymem_slp_primary_worker(request)
            finally:
                for context in reversed(contexts):
                    context.__exit__(None, None, None)
        require(result.status == expected_status, (name, result.to_log_dict()))
        durable = read_record(path)
        require(durable["state"] == expected_state, (name, durable))
        require(durable["state"] != "dead_letter", (name, durable))
        if retry_class is not None:
            require(durable["retry_class"] == retry_class, (name, durable))
        if failure_class is not None:
            require(durable["failure_class"] == failure_class, (name, durable))


def outcome_mapping() -> None:
    run_outcome_case(
        "m3g-lock",
        m3g=m3g_result("blocked", "primary_reconciliation_apply_lock_unavailable"),
        expected_status="retry_released", expected_state="queued",
        retry_class="transient_lock_contention", failure_class="resource_contention",
    )
    run_outcome_case(
        "m3h-lock", m3h=full_m3h("recovery_not_required", lock=True),
        expected_status="retry_released", expected_state="queued",
        retry_class="transient_lock_contention", failure_class="resource_contention",
    )
    run_outcome_case(
        "partial",
        m3g=m3g_result("index_applied_log_pending"),
        m3h=full_m3h("retry_reconciliation"),
        expected_status="retry_released", expected_state="queued",
        retry_class="primary_reconciliation_retry", failure_class="partial_progress_verified",
    )
    run_outcome_case(
        "held", scene_type="system_ops",
        expected_status="terminal_failed", expected_state="failed",
        failure_class="memory_policy_held",
    )
    run_outcome_case(
        "blocked", scene_type="formal_document",
        expected_status="terminal_failed", expected_state="failed",
        failure_class="memory_policy_blocked",
    )
    run_outcome_case(
        "manual", m3h=full_m3h("manual_confirmation_required"),
        expected_status="terminal_failed", expected_state="failed",
        failure_class="manual_confirmation_required",
    )
    run_outcome_case(
        "journal", m3h=full_m3h("journaled_recovery_candidate"),
        expected_status="terminal_failed", expected_state="failed",
        failure_class="recovery_isolation_required",
    )
    run_outcome_case(
        "corrupt",
        m3g=m3g_result("blocked", "primary_reconciliation_index_digest_mismatch"),
        expected_status="terminal_failed", expected_state="failed",
        failure_class="store_corruption",
    )
    run_outcome_case(
        "conflict",
        m3g=m3g_result("blocked", "primary_reconciliation_index_conflict"),
        expected_status="terminal_failed", expected_state="failed",
        failure_class="store_conflict",
    )

    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-outcome-invalid")
        path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record)
        with (
            fixed_queue_time(),
            patch.object(worker, "classify_relaymem_slp_primary_worker_outcome", return_value={"transition_kind": "commit_succeeded"}),
        ):
            result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "pipeline_blocked", result.to_log_dict())
        require(read_record(path)["state"] == "claimed", "invalid classifier transitioned")


def main() -> int:
    normal_success_and_duplicate()
    gates_and_validation()
    pre_source_fences()
    outcome_mapping()
    print("Phase 6-C1 one-claimed-job worker functional smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

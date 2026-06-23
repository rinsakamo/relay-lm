"""Lease-fence, crash convergence, and Thread C fixture smoke for C1-2."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import relaylm.relaymem_primary_pipeline as pipeline
from relaylm.relaymem_slp_primary_worker import execute_relaymem_slp_primary_worker
from relaylm.relaymem_slp_primary_worker_source import validate_relaymem_slp_primary_worker_source
from relaylm.relaymem_slp_queue_record import parse_timestamp
from relaylm.relaymem_slp_queue_state import (
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)

from _relaylm_phase6c1_fault_fixtures import (
    CRASH_POINT_NAMES,
    build_crash_point_fixture,
    build_expired_claim_fixture,
    build_stale_fence_fixture,
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


def transition(root: Path, record: dict[str, object], kind: str, **overrides):
    values = {
        "transition_kind": kind,
        "job_id": record["job_id"],
        "dispatch_idempotency_key": record["dispatch_idempotency_key"],
        "expected_record_revision": record["record_revision"],
        "expected_state": record["state"],
        "claim_owner": record["claim_owner"] if kind != "claim" else "",
        "claim_generation": record["claim_generation"],
        "lease_token": record["lease_token"] if kind != "claim" else "",
        "lease_duration_seconds": 0,
        "retry_class": "unclassified",
        "retry_not_before": None,
        "failure_class": "none",
        "terminal_state": "",
        "terminal_reason_id": "",
    }
    values.update(overrides)
    request = RelayMEMSLPQueueTransitionRequest(**values)
    return transition_relaymem_slp_queue_state(
        request, queue_root=str(root), enabled=True,
        dry_run_only=False, apply_enabled=True,
    )


def renew_current(queue_root: Path, queue_path: Path, seconds: int = 300) -> dict[str, object]:
    current = read_record(queue_path)
    result = transition(
        queue_root, current, "renew_lease",
        claim_owner=current["claim_owner"],
        lease_token=current["lease_token"],
        lease_duration_seconds=seconds,
    )
    require(result.status == "applied", result.to_log_dict())
    require(type(result.durable_record) is dict, result.to_log_dict())
    return dict(result.durable_record)


def stale_reclaim(queue_root: Path, queue_path: Path, owner: str) -> tuple[dict[str, object], object]:
    current = read_record(queue_path)
    expiry = parse_timestamp(current["lease_expires_at"])
    require(expiry is not None, "missing expiry")
    with fixed_queue_time(expiry):
        recovered_result = transition(
            queue_root, current, "stale_recovery",
            claim_owner="",
            lease_token=current["lease_token"],
        )
    require(recovered_result.status == "applied", recovered_result.to_log_dict())
    recovered = dict(recovered_result.durable_record)
    with fixed_queue_time(expiry + timedelta(seconds=1)):
        claimed_result = transition(
            queue_root, recovered, "claim",
            claim_owner=owner,
            lease_token="",
            lease_duration_seconds=300,
        )
    require(claimed_result.status == "applied", claimed_result.to_log_dict())
    return dict(claimed_result.durable_record), expiry + timedelta(seconds=2)


def checkpoint_losses() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-loss-m3e")
        path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record)
        real_m3d = pipeline.build_relaymem_primary_writer_handoff_preflight

        def renew_after_m3d(**kwargs):
            result = real_m3d(**kwargs)
            renew_current(queue_root, path)
            return result

        with (
            fixed_queue_time(),
            patch.object(pipeline, "build_relaymem_primary_writer_handoff_preflight", side_effect=renew_after_m3d),
            patch.object(pipeline, "apply_relaymem_primary_page_write") as m3e,
        ):
            result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "lease_lost_before_m3e", result.to_log_dict())
        require(not m3e.called, "M3e called after lease loss")
        require(not list((store_root / "memory/mem/primary/projects").glob("*.md")), "page mutated")
        require(read_record(path)["state"] == "claimed", "stale transition")

    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-loss-m3g")
        path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record)
        real_m3f = pipeline.build_relaymem_primary_index_log_reconciliation_preflight

        def renew_after_m3f(**kwargs):
            result = real_m3f(**kwargs)
            renew_current(queue_root, path)
            return result

        with (
            fixed_queue_time(),
            patch.object(pipeline, "build_relaymem_primary_index_log_reconciliation_preflight", side_effect=renew_after_m3f),
            patch.object(pipeline, "apply_relaymem_primary_index_log_reconciliation") as m3g,
        ):
            result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "lease_lost_before_m3g", result.to_log_dict())
        require(not m3g.called, "M3g called after lease loss")
        require(len(list((store_root / "memory/mem/primary/projects").glob("*.md"))) == 1, "page missing")
        require((store_root / "memory/mem/index.md").read_text() == "# Index\n", "index mutated")
        require((store_root / "memory/mem/log.md").read_text() == "# Log\n", "log mutated")
        require(read_record(path)["state"] == "claimed", "stale transition")

    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-loss-final")
        path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record)
        real_m3h = pipeline.audit_relaymem_primary_index_log_reconciliation_recovery

        def renew_after_m3h(**kwargs):
            result = real_m3h(**kwargs)
            renew_current(queue_root, path)
            return result

        with (
            fixed_queue_time(),
            patch.object(pipeline, "audit_relaymem_primary_index_log_reconciliation_recovery", side_effect=renew_after_m3h),
        ):
            stale = execute_relaymem_slp_primary_worker(request)
        require(stale.status == "lease_lost_before_transition", stale.to_log_dict())
        require(read_record(path)["state"] == "claimed", "stale terminal commit")
        renewed = read_record(path)
        later_request, _ = build_request(queue_root, store_root, record=renewed)
        with fixed_queue_time():
            later = execute_relaymem_slp_primary_worker(later_request)
        require(later.status == "terminal_succeeded", later.to_log_dict())
        require(read_record(path)["state"] == "succeeded", "later convergence")
        require((store_root / "memory/mem/index.md").read_text().count("relaymem-primary-index-entry-v0") == 1, "duplicate index")
        require((store_root / "memory/mem/log.md").read_text().count("relaymem-primary-log-entry-v0") == 1, "duplicate log")


def m3e_crash_new_claim_convergence() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-crash-m3e")
        path = write_record(queue_root, record)
        prepare_store(store_root)
        request, _ = build_request(queue_root, store_root, record=record)
        with (
            fixed_queue_time(),
            patch.object(
                pipeline,
                "build_relaymem_primary_index_log_reconciliation_preflight",
                side_effect=RuntimeError("test crash after M3e"),
            ),
        ):
            crashed = execute_relaymem_slp_primary_worker(request)
        require(crashed.status == "pipeline_blocked", crashed.to_log_dict())
        require(read_record(path)["state"] == "claimed", "crash queue transition")
        require(len(list((store_root / "memory/mem/primary/projects").glob("*.md"))) == 1, "crash page missing")
        new_record, new_now = stale_reclaim(queue_root, path, "worker-after-m3e-crash")
        later_request, _ = build_request(queue_root, store_root, record=new_record)
        with fixed_queue_time(new_now):
            converged = execute_relaymem_slp_primary_worker(later_request)
        require(converged.status == "terminal_succeeded", converged.to_log_dict())
        require(converged.pipeline_result.m3e_result["status"] == "already_applied", converged.to_log_dict())
        require(read_record(path)["state"] == "succeeded", "new claim did not converge")


def thread_c_fixture_integration() -> None:
    require(CRASH_POINT_NAMES == (
        "after_claim_before_source",
        "after_m3e_before_m3f",
        "after_m3g_index_before_log",
        "after_reconciliation_before_terminal_commit",
        "during_lease_expiry_and_stale_recovery",
    ), CRASH_POINT_NAMES)
    for name in CRASH_POINT_NAMES:
        with build_crash_point_fixture(name) as fixture:
            require(fixture.crash_point == name, (name, fixture))
            require("next_safe_operation" in fixture.private_artifacts, (name, fixture))

    with build_expired_claim_fixture() as fixture, TemporaryDirectory() as store_dir:
        require(fixture.queue_root is not None and fixture.canonical_record is not None, fixture)
        store_root = Path(store_dir)
        prepare_store(store_root)
        request, scope = build_request(
            fixture.queue_root, store_root, record=dict(fixture.canonical_record)
        )
        result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "lease_invalid_before_source", result.to_log_dict())
        exact, reasons = validate_relaymem_slp_primary_worker_source(
            request.worker_source,
            claimed_record=request.claimed_record,
            request_scope=scope,
        )
        require(exact is request.worker_source and not reasons, reasons)

    with build_stale_fence_fixture() as fixture, TemporaryDirectory() as store_dir:
        require(fixture.queue_root is not None, fixture)
        stale_record = dict(fixture.private_artifacts["stale_record"])
        store_root = Path(store_dir)
        prepare_store(store_root)
        request, _ = build_request(fixture.queue_root, store_root, record=stale_record)
        result = execute_relaymem_slp_primary_worker(request)
        require(result.status == "lease_invalid_before_source", result.to_log_dict())
        require(not result.queue_transition_performed, result.to_log_dict())


def main() -> int:
    checkpoint_losses()
    m3e_crash_new_claim_convergence()
    thread_c_fixture_integration()
    print("Phase 6-C1 one-claimed-job worker fault smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Lease-generation and same-revision worker race smoke for Phase 6-C1-4."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier, Lock, Thread

from relaylm.relaymem_slp_primary_worker import execute_relaymem_slp_primary_worker
from relaylm.relaymem_slp_primary_worker_source import (
    validate_relaymem_slp_primary_worker_source,
)
from relaylm.relaymem_slp_queue_record import record_filename

from _relaylm_phase6c1_fault_fixtures import build_stale_fence_fixture
from relaylm_phase6c1_primary_worker_fault_smoke import thread_c_fixture_integration
from relaylm_phase6c1_primary_worker_test_support import (
    build_request,
    claimed_record,
    fixed_queue_time,
    prepare_store,
    read_record,
    require,
    write_record,
)


def stale_generation_is_fenced_and_current_generation_completes() -> None:
    with build_stale_fence_fixture() as fixture, TemporaryDirectory() as store_dir:
        queue_root = fixture.queue_root
        current = fixture.canonical_record
        require(queue_root is not None and current is not None, "stale fixture missing")
        stale = dict(fixture.private_artifacts["stale_record"])
        store_root = Path(store_dir)
        prepare_store(store_root)
        queue_path = queue_root / record_filename(
            str(current["dispatch_idempotency_key"])
        )

        stale_request, stale_scope = build_request(
            queue_root,
            store_root,
            record=stale,
        )
        current_request, _ = build_request(
            queue_root,
            store_root,
            record=dict(current),
        )

        old_result = execute_relaymem_slp_primary_worker(stale_request)
        require(old_result.status == "lease_invalid_before_source", old_result.to_log_dict())
        require(not old_result.source_checkpoint_passed, old_result.to_log_dict())
        require(not old_result.queue_transition_performed, old_result.to_log_dict())
        exact, reasons = validate_relaymem_slp_primary_worker_source(
            stale_request.worker_source,
            claimed_record=stale_request.claimed_record,
            request_scope=stale_scope,
        )
        require(exact is stale_request.worker_source and not reasons, "stale source consumed")
        require(read_record(queue_path)["state"] == "claimed", "old worker transitioned")

        current_result = execute_relaymem_slp_primary_worker(current_request)
        require(current_result.status == "terminal_succeeded", current_result.to_log_dict())
        require(current_result.queue_transition_performed, current_result.to_log_dict())
        durable = read_record(queue_path)
        require(durable["state"] == "succeeded", "current generation did not finish")
        require(durable["claim_generation"] == current["claim_generation"], "generation drift")
        require(durable["state"] != "dead_letter", "dead-letter introduced")
        require(
            len(list((store_root / "memory/mem/primary/projects").glob("*.md")))
            == 1,
            "stale generation duplicated page",
        )


def same_revision_two_worker_race_has_one_winner() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as store_dir:
        queue_root, store_root = Path(queue_dir), Path(store_dir)
        record = claimed_record(run_id="run-c1-4-same-revision-race")
        queue_path = write_record(queue_root, record)
        prepare_store(store_root)
        request_a, scope_a = build_request(queue_root, store_root, record=record)
        request_b, scope_b = build_request(queue_root, store_root, record=record)

        barrier = Barrier(3)
        result_lock = Lock()
        results: list[tuple[object, object, object]] = []
        failures: list[str] = []

        def run(request: object, scope: object) -> None:
            try:
                barrier.wait(timeout=5.0)
                result = execute_relaymem_slp_primary_worker(request)
                with result_lock:
                    results.append((result, request, scope))
            except Exception:
                with result_lock:
                    failures.append("worker_thread_failed")

        thread_a = Thread(target=run, args=(request_a, scope_a), daemon=True)
        thread_b = Thread(target=run, args=(request_b, scope_b), daemon=True)
        with fixed_queue_time():
            thread_a.start()
            thread_b.start()
            barrier.wait(timeout=5.0)
            thread_a.join(timeout=15.0)
            thread_b.join(timeout=15.0)

        require(not thread_a.is_alive() and not thread_b.is_alive(), "worker race timeout")
        require(not failures, "worker race exception")
        require(len(results) == 2, "worker race result count")
        statuses = sorted(result.status for result, _, _ in results)
        require(
            statuses == ["lease_invalid_before_source", "terminal_succeeded"],
            "worker race winner set",
        )

        loser_result, loser_request, loser_scope = next(
            item for item in results if item[0].status == "lease_invalid_before_source"
        )
        require(not loser_result.source_checkpoint_passed, "loser consumed source")
        require(not loser_result.queue_transition_performed, "loser transitioned queue")
        exact, reasons = validate_relaymem_slp_primary_worker_source(
            loser_request.worker_source,
            claimed_record=loser_request.claimed_record,
            request_scope=loser_scope,
        )
        require(exact is loser_request.worker_source and not reasons, "loser source unavailable")

        durable = read_record(queue_path)
        require(durable["state"] == "succeeded", "race terminal state")
        require(durable["record_revision"] == 4, "race duplicate transition")
        require(
            len(list((store_root / "memory/mem/primary/projects").glob("*.md")))
            == 1,
            "race duplicate page",
        )
        require(
            (store_root / "memory/mem/index.md")
            .read_text(encoding="utf-8")
            .count("relaymem-primary-index-entry-v0")
            == 1,
            "race duplicate index",
        )
        require(
            (store_root / "memory/mem/log.md")
            .read_text(encoding="utf-8")
            .count("relaymem-primary-log-entry-v0")
            == 1,
            "race duplicate log",
        )


def main() -> int:
    thread_c_fixture_integration()
    stale_generation_is_fenced_and_current_generation_completes()
    same_revision_two_worker_race_has_one_winner()
    print("Phase 6-C1 integrated worker lease race smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

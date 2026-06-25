"""Functional smoke for O0 local one-job runner."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock, Thread
from unittest.mock import patch

import relaylm.relaymem_primary_pipeline as primary_pipeline
import relaylm.relaymem_slp_one_queued_job_runner as c2_runner
from relaylm.local_worker_once import execute_local_worker_once
from relaylm.relaymem_slp_queue_record import canonical_json_bytes, record_filename

from _relaylm_o0_local_worker_support import (
    assert_content_free,
    build_config,
    build_request,
    prepare_scoped_store,
    produce,
)
from relaylm_phase6c1_primary_worker_test_support import (
    m3g_result,
    read_record,
    require,
)


def primary_pages(root: Path) -> list[Path]:
    return sorted((root / "memory/mem/primary").rglob("*.md"))


def success_and_terminal_no_work() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        scoped = prepare_scoped_store(memory_root)
        queued, source_path = produce(queue_root, protected_root)
        queue_path = queue_root / record_filename(
            str(queued["dispatch_idempotency_key"])
        )
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
        )
        result = execute_local_worker_once(build_request(config))
        require(result.status == "executed", result.to_log_dict())
        require(result.selected and result.character_scope_resolved, result.to_log_dict())
        require(result.c2_result is not None, result.to_log_dict())
        require(result.c2_result.status == "worker_completed", result.to_log_dict())
        require(result.c2_result.worker_status == "terminal_succeeded", result.to_log_dict())
        require(result.c2_result.restart_rehydrated, result.to_log_dict())
        require(read_record(queue_path)["state"] == "succeeded", "terminal state")
        require(not source_path.exists(), "terminal source cleanup")
        require(len(primary_pages(scoped)) == 1, "one Primary MEM page expected")
        assert_content_free(result)
        assert_content_free(result.to_log_dict())

        again = execute_local_worker_once(build_request(config))
        require(again.status == "no_eligible_work", again.to_log_dict())
        require(not again.selected, again.to_log_dict())


def empty_and_dry_run() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_scoped_store(memory_root)
        empty = build_config(
            queue_root,
            protected_root,
            memory_root,
            "character/default",
        )
        no_work = execute_local_worker_once(build_request(empty))
        require(no_work.status == "no_eligible_work", no_work.to_log_dict())

        queued, source_path = produce(queue_root, protected_root)
        queue_path = queue_root / record_filename(
            str(queued["dispatch_idempotency_key"])
        )
        dry_config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
            mode="dry_run",
        )
        before_pages = len(primary_pages(prepare_scoped_store(memory_root)))
        dry = execute_local_worker_once(build_request(dry_config))
        require(dry.status == "dry_run_ready", dry.to_log_dict())
        require(dry.c2_result is not None, dry.to_log_dict())
        require(dry.c2_result.claim_attempted, dry.to_log_dict())
        require(not dry.c2_result.claim_performed, dry.to_log_dict())
        require(not dry.c2_result.worker_invoked, dry.to_log_dict())
        require(read_record(queue_path)["state"] == "queued", "dry-run queue mutation")
        require(source_path.exists(), "dry-run source consumption")
        require(
            len(primary_pages(prepare_scoped_store(memory_root))) == before_pages,
            "dry-run MEM mutation",
        )


def concurrency_invokes_one_worker() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_scoped_store(memory_root)
        queued, _ = produce(queue_root, protected_root)
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
        )
        original_worker = c2_runner.execute_relaymem_slp_primary_worker
        count_lock = Lock()
        count = 0
        results: list[object] = []

        def counted_worker(value: object):
            nonlocal count
            with count_lock:
                count += 1
            return original_worker(value)

        def invoke() -> None:
            results.append(execute_local_worker_once(build_request(config)))

        with patch.object(
            c2_runner,
            "execute_relaymem_slp_primary_worker",
            counted_worker,
        ):
            threads = [Thread(target=invoke) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        require(count == 1, ("worker invocation count", count))
        require(len(results) == 2, ("result count", len(results)))
        winners = [
            value
            for value in results
            if getattr(getattr(value, "c2_result", None), "status", None)
            == "worker_completed"
        ]
        require(len(winners) == 1, [getattr(value, "status", None) for value in results])
        loser = next(value for value in results if value is not winners[0])
        loser_c2 = getattr(loser, "c2_result", None)
        require(
            loser_c2 is None or getattr(loser_c2, "status", None) == "claim_not_applied",
            getattr(loser, "to_log_dict", lambda: loser)(),
        )
        require(
            getattr(loser, "status", None)
            in {"queue_busy", "candidate_changed", "executed"},
            getattr(loser, "to_log_dict", lambda: loser)(),
        )


def retry_release_then_later_success() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_scoped_store(memory_root)
        queued, source_path = produce(queue_root, protected_root)
        queue_path = queue_root / record_filename(
            str(queued["dispatch_idempotency_key"])
        )
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
        )
        with patch.object(
            primary_pipeline,
            "apply_relaymem_primary_index_log_reconciliation",
            return_value=m3g_result(
                "blocked", "primary_reconciliation_apply_lock_unavailable"
            ),
        ):
            first = execute_local_worker_once(build_request(config))
        require(first.c2_result is not None, first.to_log_dict())
        require(first.c2_result.worker_status == "retry_released", first.to_log_dict())
        require(first.c2_result.retryable and not first.c2_result.terminal, first.to_log_dict())
        require(source_path.exists(), "retry source must remain")

        future = execute_local_worker_once(build_request(config))
        require(future.status == "no_eligible_work", future.to_log_dict())

        queued_again = read_record(queue_path)
        generation = int(queued_again["claim_generation"])
        queued_again["retry_not_before"] = queued_again["created_at"]
        queue_path.write_bytes(canonical_json_bytes(queued_again))
        second = execute_local_worker_once(build_request(config))
        require(second.c2_result is not None, second.to_log_dict())
        require(second.c2_result.worker_status == "terminal_succeeded", second.to_log_dict())
        durable = read_record(queue_path)
        require(int(durable["claim_generation"]) == generation + 1, durable)
        require(not source_path.exists(), "later success source cleanup")


def main() -> int:
    success_and_terminal_no_work()
    empty_and_dry_run()
    concurrency_invokes_one_worker()
    retry_release_then_later_success()
    print("O0 local one-job runner smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

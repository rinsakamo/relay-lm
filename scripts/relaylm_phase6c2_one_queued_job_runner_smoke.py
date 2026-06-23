"""Functional smoke for Phase 6-C2 one queued-job integration."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock, Thread
from unittest.mock import patch

import relaylm.relaymem_primary_pipeline as primary_pipeline
import relaylm.relaymem_slp_one_queued_job_runner as runner
import relaylm.relaymem_slp_queue_state as queue_state
from relaylm.relaymem_slp_one_queued_job_runner import (
    REQUEST_SCHEMA,
    RelayMEMSLPOneQueuedJobRunnerRequest,
    build_relaymem_slp_one_queued_job_runner_node_result,
    execute_one_queued_relaymem_slp_primary_job,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_queue_record import parse_timestamp, record_filename

from _relaylm_phase6c1_durable_source_support import (
    CHARACTER_ID,
    PRIVATE_TOKENS,
    REPO_ROOT,
    apply_durable,
    artifact_path,
)
from relaylm_phase6c1_primary_worker_test_support import (
    m3g_result,
    prepare_store,
    read_record,
    require,
)


def request(
    queue_root: Path,
    protected_root: Path,
    memory_root: Path,
    queued: dict[str, object],
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry,
    *,
    owner: str = "worker-c2",
    dry_run_only: bool = False,
) -> RelayMEMSLPOneQueuedJobRunnerRequest:
    return RelayMEMSLPOneQueuedJobRunnerRequest(
        schema_version=REQUEST_SCHEMA,
        runtime_private=True,
        content_included=False,
        queued_record=dict(queued),
        source_registry=registry,
        character_id=CHARACTER_ID,
        queue_root=str(queue_root),
        protected_source_root=str(protected_root),
        store_root=str(memory_root),
        claim_owner=owner,
        enabled=True,
        dry_run_only=dry_run_only,
        apply_enabled=not dry_run_only,
        lease_duration_seconds=300,
    )


def queued_from(applied: object) -> dict[str, object]:
    runtime_result = getattr(applied, "runtime_result", None)
    enqueue = getattr(runtime_result, "enqueue_result", None)
    queued = getattr(enqueue, "durable_record", None)
    require(type(queued) is dict, getattr(applied, "to_log_dict", lambda: applied)())
    return queued


def assert_content_free(value: object) -> None:
    text = repr(value)
    for token in PRIVATE_TOKENS:
        require(token not in text, ("protected leak", token))


def dry_run_restart_success() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_store(memory_root)
        applied = apply_durable(
            queue_root, protected_root, RelayMEMSLPPrimaryWorkerSourceRegistry()
        )
        require(applied.status == "enqueued", applied.to_log_dict())
        queued = queued_from(applied)
        source_path = artifact_path(protected_root)
        queue_path = queue_root / record_filename(
            str(queued["dispatch_idempotency_key"])
        )

        dry = execute_one_queued_relaymem_slp_primary_job(
            request(
                queue_root,
                protected_root,
                memory_root,
                queued,
                RelayMEMSLPPrimaryWorkerSourceRegistry(),
                dry_run_only=True,
            )
        )
        require(dry.status == "dry_run_ready", dry.to_log_dict())
        require(dry.claim_attempted and not dry.claim_performed, dry.to_log_dict())
        require(not dry.source_prepared and not dry.worker_invoked, dry.to_log_dict())
        require(read_record(queue_path)["state"] == "queued", "dry-run mutated queue")
        require(source_path.exists(), "dry-run consumed protected source")

        result = execute_one_queued_relaymem_slp_primary_job(
            request(
                queue_root,
                protected_root,
                memory_root,
                queued,
                RelayMEMSLPPrimaryWorkerSourceRegistry(),
            )
        )
        require(result.status == "worker_completed", result.to_log_dict())
        require(result.worker_status == "terminal_succeeded", result.to_log_dict())
        require(result.terminal and result.queue_transition_performed, result.to_log_dict())
        require(result.restart_rehydrated, result.to_log_dict())
        require(not result.cleanup_required, result.to_log_dict())
        require(read_record(queue_path)["state"] == "succeeded", "terminal state missing")
        require(not source_path.exists(), "terminal cleanup left protected source")
        assert_content_free(result)
        assert_content_free(result.to_log_dict())
        assert_content_free(
            build_relaymem_slp_one_queued_job_runner_node_result(result).to_log_dict()
        )


def retry_release_new_claim_success() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_store(memory_root)
        applied = apply_durable(
            queue_root, protected_root, RelayMEMSLPPrimaryWorkerSourceRegistry()
        )
        queued = queued_from(applied)
        source_path = artifact_path(protected_root)
        with patch.object(
            primary_pipeline,
            "apply_relaymem_primary_index_log_reconciliation",
            return_value=m3g_result(
                "blocked", "primary_reconciliation_apply_lock_unavailable"
            ),
        ):
            first = execute_one_queued_relaymem_slp_primary_job(
                request(
                    queue_root,
                    protected_root,
                    memory_root,
                    queued,
                    RelayMEMSLPPrimaryWorkerSourceRegistry(),
                    owner="worker-c2-n",
                )
            )
        require(first.status == "worker_completed", first.to_log_dict())
        require(first.worker_status == "retry_released", first.to_log_dict())
        require(first.retryable and not first.terminal, first.to_log_dict())
        require(source_path.exists(), "retry release deleted source")
        transition = first.worker_result.queue_transition_result
        queued_again = transition.durable_record
        require(type(queued_again) is dict and queued_again["state"] == "queued", queued_again)
        retry_at = parse_timestamp(queued_again["retry_not_before"])
        require(retry_at is not None, queued_again)

        original_now = queue_state._now_utc
        queue_state._now_utc = lambda: retry_at + timedelta(seconds=1)
        try:
            second = execute_one_queued_relaymem_slp_primary_job(
                request(
                    queue_root,
                    protected_root,
                    memory_root,
                    queued_again,
                    RelayMEMSLPPrimaryWorkerSourceRegistry(),
                    owner="worker-c2-n1",
                )
            )
        finally:
            queue_state._now_utc = original_now
        require(second.worker_status == "terminal_succeeded", second.to_log_dict())
        require(second.restart_rehydrated, second.to_log_dict())
        require(not source_path.exists(), "later success did not clean source")


def claim_race_invokes_one_worker() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_store(memory_root)
        applied = apply_durable(
            queue_root, protected_root, RelayMEMSLPPrimaryWorkerSourceRegistry()
        )
        queued = queued_from(applied)
        original_worker = runner.execute_relaymem_slp_primary_worker
        count_lock = Lock()
        count = 0
        results: list[object] = []

        def counted_worker(value: object):
            nonlocal count
            with count_lock:
                count += 1
            return original_worker(value)

        def invoke(owner: str) -> None:
            results.append(
                execute_one_queued_relaymem_slp_primary_job(
                    request(
                        queue_root,
                        protected_root,
                        memory_root,
                        queued,
                        RelayMEMSLPPrimaryWorkerSourceRegistry(),
                        owner=owner,
                    )
                )
            )

        with patch.object(runner, "execute_relaymem_slp_primary_worker", counted_worker):
            threads = [Thread(target=invoke, args=(f"worker-race-{index}",)) for index in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        require(count == 1, ("worker invocation count", count))
        statuses = sorted(getattr(value, "status", "") for value in results)
        require(statuses == ["claim_not_applied", "worker_completed"], statuses)


def _producer(queue_root: Path, protected_root: Path) -> int:
    result = apply_durable(
        queue_root, protected_root, RelayMEMSLPPrimaryWorkerSourceRegistry()
    )
    require(result.status == "enqueued", result.to_log_dict())
    print("producer_ok")
    return 0


def _consumer(queue_root: Path, protected_root: Path, memory_root: Path) -> int:
    queue_files = list(queue_root.glob("slp-dispatch-v0-*.json"))
    require(len(queue_files) == 1, [path.name for path in queue_files])
    queued = read_record(queue_files[0])
    prepare_store(memory_root)
    result = execute_one_queued_relaymem_slp_primary_job(
        request(
            queue_root,
            protected_root,
            memory_root,
            queued,
            RelayMEMSLPPrimaryWorkerSourceRegistry(),
            owner="worker-restart-c2",
        )
    )
    require(result.worker_status == "terminal_succeeded", result.to_log_dict())
    require(result.restart_rehydrated, result.to_log_dict())
    print("consumer_ok")
    return 0


def separate_process_restart() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        command = [sys.executable, str(Path(__file__).resolve())]
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(
                None,
                [
                    str(REPO_ROOT),
                    str(REPO_ROOT / "scripts"),
                    environment.get("PYTHONPATH"),
                ],
            )
        )
        producer = subprocess.run(
            [*command, "--producer", queue_dir, protected_dir],
            cwd=REPO_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        require(producer.returncode == 0, ("producer failed", producer.stderr))
        consumer = subprocess.run(
            [*command, "--consumer", queue_dir, protected_dir, memory_dir],
            cwd=REPO_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        require(consumer.returncode == 0, ("consumer failed", consumer.stderr))
        require(producer.stdout.strip() == "producer_ok", producer.stdout)
        require(consumer.stdout.strip() == "consumer_ok", consumer.stdout)
        combined = producer.stdout + producer.stderr + consumer.stdout + consumer.stderr
        for token in PRIVATE_TOKENS:
            require(token not in combined, ("subprocess leak", token))


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--producer":
        return _producer(Path(sys.argv[2]), Path(sys.argv[3]))
    if len(sys.argv) > 1 and sys.argv[1] == "--consumer":
        return _consumer(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    dry_run_restart_success()
    retry_release_new_claim_success()
    claim_race_invokes_one_worker()
    separate_process_restart()
    print("Phase 6-C2 one queued-job functional smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

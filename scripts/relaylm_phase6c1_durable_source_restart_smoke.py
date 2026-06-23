"""Restart, retry, fresh-scope, and terminal cleanup smoke for Phase 6-C1-5."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import relaylm.relaymem_primary_pipeline as pipeline
import relaylm.relaymem_slp_queue_state as queue_state
from relaylm.relaymem_slp_primary_worker import execute_relaymem_slp_primary_worker
from relaylm.relaymem_slp_primary_worker_source_adapter import (
    prepare_relaymem_slp_primary_worker_source_for_claim,
    release_relaymem_slp_primary_worker_source_after_terminal,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_protected_source_store import RelayMEMSLPDurableProtectedSourceStore
from relaylm.relaymem_slp_queue_record import parse_timestamp, record_filename
from _relaylm_phase6c1_durable_source_support import (
    CHARACTER_ID,
    PRIVATE_TOKENS,
    REPO_ROOT,
    apply_durable,
    artifact_path,
    claim,
    worker_request,
)
from relaylm_phase6c1_primary_worker_test_support import (
    m3g_result,
    prepare_store,
    read_record,
    require,
)


def restart_retry_new_claim_and_terminal_cleanup() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        queue_root = Path(queue_dir)
        protected_root = Path(protected_dir)
        memory_root = Path(memory_dir)
        prepare_store(memory_root)
        registry_a = RelayMEMSLPPrimaryWorkerSourceRegistry()
        applied = apply_durable(queue_root, protected_root, registry_a)
        require(applied.status == "enqueued", applied.to_log_dict())
        enqueue = applied.runtime_result.enqueue_result
        require(enqueue is not None and type(enqueue.durable_record) is dict, applied.to_log_dict())
        queued = enqueue.durable_record
        source_path = artifact_path(protected_root)
        protected_digest_before = hashlib.sha256(source_path.read_bytes()).hexdigest()
        claimed_n = claim(queue_root, queued)
        prepared_n = prepare_relaymem_slp_primary_worker_source_for_claim(
            registry_a,
            claimed_record=claimed_n,
            character_id=CHARACTER_ID,
            source_store=RelayMEMSLPDurableProtectedSourceStore(str(protected_root)),
        )
        require(prepared_n.status == "prepared", prepared_n.to_log_dict())
        require(not prepared_n.restart_rehydrated, prepared_n.to_log_dict())
        stale_source = prepared_n.source
        stale_scope = prepared_n.request_scope
        with patch.object(
            pipeline,
            "apply_relaymem_primary_index_log_reconciliation",
            return_value=m3g_result("blocked", "primary_reconciliation_apply_lock_unavailable"),
        ):
            first = execute_relaymem_slp_primary_worker(
                worker_request(queue_root, memory_root, claimed_n, prepared_n)
            )
        require(first.status == "retry_released", first.to_log_dict())
        prepared_n.release_prepared_scope()
        require(source_path.exists(), "retry release deleted durable source")
        queued_again = first.queue_transition_result.durable_record
        require(type(queued_again) is dict and queued_again["state"] == "queued", queued_again)
        retry_at = parse_timestamp(queued_again["retry_not_before"])
        require(retry_at is not None, queued_again)
        registry_b = RelayMEMSLPPrimaryWorkerSourceRegistry()
        store_b = RelayMEMSLPDurableProtectedSourceStore(str(protected_root))
        original_now = queue_state._now_utc
        queue_state._now_utc = lambda: retry_at + timedelta(seconds=1)
        try:
            claimed_n1 = claim(queue_root, queued_again)
            prepared_n1 = prepare_relaymem_slp_primary_worker_source_for_claim(
                registry_b,
                claimed_record=claimed_n1,
                character_id=CHARACTER_ID,
                source_store=store_b,
            )
            require(prepared_n1.status == "prepared", prepared_n1.to_log_dict())
            require(prepared_n1.restart_rehydrated, prepared_n1.to_log_dict())
            require(prepared_n1.source is not stale_source, "source object reused")
            require(prepared_n1.request_scope is not stale_scope, "scope object reused")
            require(
                hashlib.sha256(source_path.read_bytes()).hexdigest() == protected_digest_before,
                "protected capture changed across retry",
            )
            stale_request = replace(
                worker_request(queue_root, memory_root, claimed_n1, prepared_n1),
                worker_source=stale_source,
                request_scope=stale_scope,
            )
            stale = execute_relaymem_slp_primary_worker(stale_request)
            require(stale.status in {"invalid_input", "source_invalid"}, stale.to_log_dict())
            require(not stale.side_effect_started, stale.to_log_dict())
            require(not stale.queue_transition_performed, stale.to_log_dict())
            second = execute_relaymem_slp_primary_worker(
                worker_request(queue_root, memory_root, claimed_n1, prepared_n1)
            )
        finally:
            queue_state._now_utc = original_now
        require(second.status == "terminal_succeeded", second.to_log_dict())
        prepared_n1.release_prepared_scope()
        terminal = second.queue_transition_result.durable_record
        require(type(terminal) is dict and terminal["state"] == "succeeded", terminal)
        release = release_relaymem_slp_primary_worker_source_after_terminal(
            registry_b,
            terminal_record=terminal,
            character_id=CHARACTER_ID,
            source_store=store_b,
        )
        require(release.status == "released", release.to_log_dict())
        require(not source_path.exists(), "terminal cleanup left protected artifact")
        queue_path = queue_root / record_filename(str(terminal["dispatch_idempotency_key"]))
        require(read_record(queue_path)["state"] == "succeeded", "cleanup rewound queue")


def _producer(queue_root: Path, protected_root: Path) -> int:
    result = apply_durable(queue_root, protected_root, RelayMEMSLPPrimaryWorkerSourceRegistry())
    require(result.status == "enqueued", result.to_log_dict())
    print("producer_ok")
    return 0


def _consumer(queue_root: Path, protected_root: Path, memory_root: Path) -> int:
    queue_files = list(queue_root.glob("slp-dispatch-v0-*.json"))
    require(len(queue_files) == 1, [path.name for path in queue_files])
    queued = read_record(queue_files[0])
    prepare_store(memory_root)
    claimed_record = claim(queue_root, queued)
    registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
    source_store = RelayMEMSLPDurableProtectedSourceStore(str(protected_root))
    prepared = prepare_relaymem_slp_primary_worker_source_for_claim(
        registry,
        claimed_record=claimed_record,
        character_id=CHARACTER_ID,
        source_store=source_store,
    )
    require(prepared.restart_rehydrated, prepared.to_log_dict())
    result = execute_relaymem_slp_primary_worker(
        worker_request(queue_root, memory_root, claimed_record, prepared)
    )
    require(result.status == "terminal_succeeded", result.to_log_dict())
    terminal = result.queue_transition_result.durable_record
    release = release_relaymem_slp_primary_worker_source_after_terminal(
        registry,
        terminal_record=terminal,
        character_id=CHARACTER_ID,
        source_store=source_store,
    )
    require(release.status == "released", release.to_log_dict())
    prepared.release_prepared_scope()
    print("consumer_ok")
    return 0


def separate_process_restart_smoke() -> None:
    with (
        TemporaryDirectory() as queue_dir,
        TemporaryDirectory() as protected_dir,
        TemporaryDirectory() as memory_dir,
    ):
        command = [sys.executable, str(Path(__file__).resolve())]
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(None, [str(REPO_ROOT), str(REPO_ROOT / "scripts"), environment.get("PYTHONPATH")])
        )
        producer = subprocess.run(
            [*command, "--producer", queue_dir, protected_dir],
            cwd=REPO_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        require(producer.returncode == 0, ("producer_failed", producer.returncode))
        require(producer.stdout.strip() == "producer_ok", "producer_output_invalid")
        consumer = subprocess.run(
            [*command, "--consumer", queue_dir, protected_dir, memory_dir],
            cwd=REPO_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        require(consumer.returncode == 0, ("consumer_failed", consumer.returncode))
        require(consumer.stdout.strip() == "consumer_ok", "consumer_output_invalid")
        combined = producer.stdout + producer.stderr + consumer.stdout + consumer.stderr
        for token in PRIVATE_TOKENS:
            require(token not in combined, ("subprocess output leak", token))


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--producer":
        return _producer(Path(sys.argv[2]), Path(sys.argv[3]))
    if len(sys.argv) > 1 and sys.argv[1] == "--consumer":
        return _consumer(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    restart_retry_new_claim_and_terminal_cleanup()
    separate_process_restart_smoke()
    print("Phase 6-C1-5 durable restart smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

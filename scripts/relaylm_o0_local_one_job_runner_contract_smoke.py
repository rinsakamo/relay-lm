"""Targeted contract smoke for O0 token, scope, and lock behavior."""
from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import relaylm.local_worker_once as local_worker
from relaylm.local_worker_once import execute_local_worker_once
from relaylm.relaymem_slp_queue_record import canonical_json_bytes, record_filename
from relaylm.relaymem_slp_queue_storage import (
    acquire_queue_lock,
    open_queue_root,
    release_queue_lock,
)

from _relaylm_o0_local_worker_support import (
    build_config,
    build_request,
    prepare_scoped_store,
    produce,
)
from relaylm_phase6c1_primary_worker_test_support import read_record, require


def invalid_queue_token_fails_closed() -> None:
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
        invalid = read_record(queue_path)
        invalid["job_id"] = "invalid token with spaces"
        queue_path.write_bytes(canonical_json_bytes(invalid))
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            str(queued["namespace"]),
        )
        with patch.object(
            local_worker,
            "execute_one_queued_relaymem_slp_primary_job",
        ) as delegated:
            result = execute_local_worker_once(build_request(config))
        require(result.status == "unsafe_queue_state", result.to_log_dict())
        require(not delegated.called, "invalid token reached C2")
        require(source_path.exists(), "invalid token consumed protected source")


def known_character_namespace_mismatch_fails_closed() -> None:
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
        character_id = "fixture-character"
        config = build_config(
            queue_root,
            protected_root,
            memory_root,
            "different/namespace",
            mode="dry_run",
            character_id=character_id,
        )
        with patch.object(
            local_worker,
            "execute_one_queued_relaymem_slp_primary_job",
        ) as delegated:
            result = execute_local_worker_once(
                build_request(config, character_id=character_id)
            )
        require(result.status == "invalid_input", result.to_log_dict())
        require(
            "local_worker_character_namespace_mismatch" in result.reason_ids,
            result.to_log_dict(),
        )
        require(not delegated.called, "namespace mismatch reached C2")
        require(source_path.exists(), "namespace mismatch consumed protected source")
        require(
            not list((scoped / "memory/mem/primary").rglob("*.md")),
            "namespace mismatch wrote Primary MEM",
        )
        require(str(queued["namespace"]) != "different/namespace", queued)


def discovery_lock_contention_is_not_no_work() -> None:
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
        root_fd, reasons = open_queue_root(str(queue_root))
        require(root_fd is not None, reasons)
        assert root_fd is not None
        try:
            lock_error = acquire_queue_lock(root_fd, exclusive=True)
            require(lock_error is None, lock_error)
            try:
                with patch.object(
                    local_worker,
                    "execute_one_queued_relaymem_slp_primary_job",
                ) as delegated:
                    result = execute_local_worker_once(build_request(config))
            finally:
                release_queue_lock(root_fd)
        finally:
            os.close(root_fd)
        require(result.status == "queue_busy", result.to_log_dict())
        require(result.exit_category == "completed", result.to_log_dict())
        require("queue_lock_busy" in result.reason_ids, result.to_log_dict())
        require(not result.selected and not result.eligible, result.to_log_dict())
        require(not delegated.called, "queue-busy invocation reached C2")
        require(read_record(queue_path)["state"] == "queued", "queue-busy mutation")
        require(source_path.exists(), "queue-busy source consumption")


def main() -> int:
    invalid_queue_token_fails_closed()
    known_character_namespace_mismatch_fails_closed()
    discovery_lock_contention_is_not_no_work()
    print("O0 local one-job runner contract smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

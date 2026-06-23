"""Store, corruption, ordering, and leakage smoke for Phase 6-C1-5."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch

import relaylm.relaymem_slp_protected_source_store as source_store_module
from relaylm.relaymem_slp_durable_runtime_enqueue import (
    apply_relaymem_slp_durable_runtime_enqueue,
    build_relaymem_slp_durable_runtime_enqueue_node_result,
)
from relaylm.relaymem_slp_primary_worker_source_adapter import (
    prepare_relaymem_slp_primary_worker_source_for_claim,
    release_relaymem_slp_primary_worker_source_after_terminal,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_protected_source_store import (
    ARTIFACT_SCHEMA,
    RelayMEMSLPDurableProtectedSourceStore,
)
from relaylm.relaymem_slp_queue_record import record_filename
from relaylm.relaymem_slp_queue_state import (
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)
from relaylm.relaymem_slp_runtime_enqueue import apply_relaymem_slp_runtime_enqueue

from _relaylm_phase6c1_durable_source_support import (
    CHARACTER_ID,
    PRIVATE_TOKENS,
    apply_durable,
    artifact_path,
    assert_content_free,
    claim,
    finalized,
)
from relaylm_phase6c1_primary_worker_test_support import read_record, require


def create_read_duplicate_race_and_leakage() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as protected_dir:
        queue_root, protected_root = Path(queue_dir), Path(protected_dir)
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
        first = apply_durable(queue_root, protected_root, registry)
        require(first.status == "enqueued" and first.restart_complete, first.to_log_dict())
        artifact = artifact_path(protected_root)
        data = artifact.read_bytes()
        document = json.loads(data.decode("utf-8"))
        require(document["schema_version"] == ARTIFACT_SCHEMA, document.keys())
        require(data == json.dumps(
            document, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8"), "artifact is not canonical")
        queue_data = next(queue_root.glob("slp-dispatch-v0-*.json")).read_bytes()
        require(PRIVATE_TOKENS[0].encode() not in queue_data, "user leaked to queue")
        require(PRIVATE_TOKENS[1].encode() not in queue_data, "assistant leaked to queue")
        require(PRIVATE_TOKENS[0].encode() in data and PRIVATE_TOKENS[1].encode() in data, "capture missing")
        for surface in (
            first, first.to_log_dict(),
            build_relaymem_slp_durable_runtime_enqueue_node_result(first).to_log_dict(),
            registry, RelayMEMSLPDurableProtectedSourceStore(str(protected_root)),
            artifact.name,
        ):
            assert_content_free(surface)
        duplicate = apply_durable(queue_root, protected_root, registry)
        require(duplicate.status == "duplicate_existing", duplicate.to_log_dict())
        require(duplicate.source_store_result.status == "duplicate_existing", duplicate.to_log_dict())
        conflict = apply_durable(
            queue_root, protected_root, registry,
            source_result=finalized(assistant_text="different protected assistant body"),
        )
        require(conflict.status == "source_persistence_failed", conflict.to_log_dict())
        require("protected_source_identity_collision" in conflict.blocked_reasons, conflict.to_log_dict())

    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as protected_dir:
        queue_root, protected_root = Path(queue_dir), Path(protected_dir)
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
        preparation = apply_relaymem_slp_runtime_enqueue(
            finalized(), registry=registry, queue_root=str(queue_root),
            enabled=True, dry_run_only=True, apply_enabled=False,
        )
        candidate = preparation.dispatch_result.durable_job
        source = preparation.finalized_turn_source_result.source
        payload = preparation.protected_source_payload
        require(candidate is not None and source is not None and payload is not None, preparation.to_log_dict())
        if preparation.source_scope is not None:
            preparation.source_scope.close()
        results: list[str] = []

        def persist() -> None:
            store = RelayMEMSLPDurableProtectedSourceStore(str(protected_root))
            for _ in range(100):
                result = store.persist(
                    source_payload=payload, durable_job=candidate,
                    character_id=source.character_id,
                )
                if result.status != "retryable":
                    results.append(result.status)
                    return
                time.sleep(0.001)
            results.append("retryable_exhausted")

        threads = [Thread(target=persist) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        require(results.count("published_new") == 1, results)
        require(results.count("duplicate_existing") == 5, results)


def _case_setup():
    queue_tmp, protected_tmp = TemporaryDirectory(), TemporaryDirectory()
    queue_root, protected_root = Path(queue_tmp.name), Path(protected_tmp.name)
    applied = apply_durable(
        queue_root, protected_root, RelayMEMSLPPrimaryWorkerSourceRegistry()
    )
    require(applied.status == "enqueued", applied.to_log_dict())
    queued = applied.runtime_result.enqueue_result.durable_record
    require(type(queued) is dict, applied.to_log_dict())
    return (queue_tmp, protected_tmp), queue_root, protected_root, queued, artifact_path(protected_root)


def corruption_matrix() -> None:
    mutations = {
        "unsupported_schema": lambda value: value.__setitem__("schema_version", "unsupported.v9"),
        "missing_field": lambda value: value.pop("runtime_private"),
        "additional_field": lambda value: value.__setitem__("unexpected", True),
        "digest": lambda value: value.__setitem__("source_integrity_digest", "0" * 64),
        "job_identity": lambda value: value.__setitem__("job_id", "slp-job-v0:" + "0" * 64),
        "dispatch_identity": lambda value: value.__setitem__(
            "dispatch_idempotency_key", "slp-dispatch-v0:" + "0" * 64
        ),
        "payload": lambda value: value["protected_capture"]["governed_messages"][0].__setitem__(
            "content", "tampered"
        ),
    }
    for label, mutate in mutations.items():
        temps, queue_root, protected_root, queued, artifact = _case_setup()
        try:
            value = json.loads(artifact.read_text(encoding="utf-8"))
            mutate(value)
            artifact.write_text(json.dumps(
                value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            ), encoding="utf-8")
            loaded = RelayMEMSLPDurableProtectedSourceStore(str(protected_root)).load_for_claim(
                claimed_record=claim(queue_root, queued), character_id=CHARACTER_ID
            )
            require(loaded.status == "corrupt", (label, loaded.to_log_dict()))
            assert_content_free(loaded)
        finally:
            for temp in temps:
                temp.cleanup()
    for label, raw in {
        "malformed": b"{", "truncated": b'{"schema_version":',
        "non_utf8": b"\xff\xfe", "noncanonical": b'{"z":1, "a":2}',
    }.items():
        temps, queue_root, protected_root, queued, artifact = _case_setup()
        try:
            artifact.write_bytes(raw)
            loaded = RelayMEMSLPDurableProtectedSourceStore(str(protected_root)).load_for_claim(
                claimed_record=claim(queue_root, queued), character_id=CHARACTER_ID
            )
            require(loaded.status == "corrupt", (label, loaded.to_log_dict()))
        finally:
            for temp in temps:
                temp.cleanup()
    for kind in ("symlink", "directory", "fifo"):
        temps, queue_root, protected_root, queued, artifact = _case_setup()
        try:
            artifact.unlink()
            if kind == "symlink":
                target = protected_root / "target"
                target.write_text("{}", encoding="utf-8")
                artifact.symlink_to(target)
            elif kind == "directory":
                artifact.mkdir()
            else:
                os.mkfifo(artifact)
            loaded = RelayMEMSLPDurableProtectedSourceStore(str(protected_root)).load_for_claim(
                claimed_record=claim(queue_root, queued), character_id=CHARACTER_ID
            )
            require(loaded.status == "corrupt", (kind, loaded.to_log_dict()))
        finally:
            for temp in temps:
                temp.cleanup()
    temps, queue_root, protected_root, queued, _ = _case_setup()
    try:
        (protected_root / ".protected-source-incomplete.tmp").write_bytes(b"partial")
        loaded = RelayMEMSLPDurableProtectedSourceStore(str(protected_root)).load_for_claim(
            claimed_record=claim(queue_root, queued), character_id=CHARACTER_ID
        )
        require(loaded.status == "loaded", loaded.to_log_dict())
    finally:
        for temp in temps:
            temp.cleanup()


def bounds_orphans_and_cleanup_marker() -> None:
    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as protected_dir:
        queue_root, protected_root = Path(queue_dir), Path(protected_dir)
        preparation = apply_relaymem_slp_runtime_enqueue(
            finalized(), registry=RelayMEMSLPPrimaryWorkerSourceRegistry(),
            queue_root=str(queue_root), enabled=True, dry_run_only=True,
            apply_enabled=False,
        )
        candidate = preparation.dispatch_result.durable_job
        source = preparation.finalized_turn_source_result.source
        payload = preparation.protected_source_payload
        if preparation.source_scope is not None:
            preparation.source_scope.close()
        bounded = RelayMEMSLPDurableProtectedSourceStore(
            str(protected_root), max_artifact_bytes=128
        ).persist(source_payload=payload, durable_job=candidate, character_id=source.character_id)
        require("protected_source_artifact_size_exceeded" in bounded.blocked_reasons, bounded.to_log_dict())
        invalid = RelayMEMSLPDurableProtectedSourceStore(
            str(protected_root / ".." / "escape")
        ).persist(source_payload=payload, durable_job=candidate, character_id=source.character_id)
        require("protected_source_root_invalid" in invalid.blocked_reasons, invalid.to_log_dict())

    with TemporaryDirectory() as root_dir:
        root = Path(root_dir)
        source_root = root / "source"
        source_root.mkdir()
        failed = apply_relaymem_slp_durable_runtime_enqueue(
            finalized(), registry=RelayMEMSLPPrimaryWorkerSourceRegistry(),
            source_store=RelayMEMSLPDurableProtectedSourceStore(str(source_root)),
            queue_root=str(root / "missing-queue"), enabled=True,
            dry_run_only=False, apply_enabled=True,
        )
        require(failed.status == "enqueue_failed", failed.to_log_dict())
        require(not list(source_root.glob("protected-source-v0-*.json")), failed.to_log_dict())
        require(failed.orphan_cleanup_result.status == "orphan_removed", failed.to_log_dict())

    with TemporaryDirectory() as queue_dir, TemporaryDirectory() as protected_dir:
        queue_root, protected_root = Path(queue_dir), Path(protected_dir)
        registry = RelayMEMSLPPrimaryWorkerSourceRegistry()
        applied = apply_durable(queue_root, protected_root, registry)
        claimed_record = claim(queue_root, applied.runtime_result.enqueue_result.durable_record)
        store = RelayMEMSLPDurableProtectedSourceStore(str(protected_root))
        prepared = prepare_relaymem_slp_primary_worker_source_for_claim(
            registry, claimed_record=claimed_record, character_id=CHARACTER_ID,
            source_store=store,
        )
        terminal_result = transition_relaymem_slp_queue_state(
            RelayMEMSLPQueueTransitionRequest(
                transition_kind="commit_terminal", job_id=str(claimed_record["job_id"]),
                dispatch_idempotency_key=str(claimed_record["dispatch_idempotency_key"]),
                expected_record_revision=int(claimed_record["record_revision"]),
                expected_state="claimed", claim_owner=str(claimed_record["claim_owner"]),
                claim_generation=int(claimed_record["claim_generation"]),
                lease_token=str(claimed_record["lease_token"]), failure_class="none",
                terminal_state="succeeded",
                terminal_reason_id="primary_mem_durable_state_verified",
            ), queue_root=str(queue_root), enabled=True, dry_run_only=False,
            apply_enabled=True,
        )
        require(terminal_result.status == "applied", terminal_result.to_log_dict())
        terminal = terminal_result.durable_record
        artifact = artifact_path(protected_root)
        real_unlink = source_store_module.os.unlink

        def fail_artifact(path: object, *args: object, **kwargs: object):
            if str(path) == artifact.name:
                raise OSError("bounded cleanup failure")
            return real_unlink(path, *args, **kwargs)

        with patch.object(source_store_module.os, "unlink", side_effect=fail_artifact):
            released = release_relaymem_slp_primary_worker_source_after_terminal(
                registry, terminal_record=terminal, character_id=CHARACTER_ID,
                source_store=store,
            )
        require(released.status == "cleanup_required", released.to_log_dict())
        require(artifact.exists(), "cleanup failure removed artifact")
        require(list(protected_root.glob(".protected-source-cleanup-*.json")), released.to_log_dict())
        queue_path = queue_root / record_filename(str(terminal["dispatch_idempotency_key"]))
        require(read_record(queue_path)["state"] == "succeeded", "cleanup rewound terminal")
        prepared.release_prepared_scope()


def main() -> int:
    create_read_duplicate_race_and_leakage()
    corruption_matrix()
    bounds_orphans_and_cleanup_marker()
    print("Phase 6-C1-5 protected source store smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

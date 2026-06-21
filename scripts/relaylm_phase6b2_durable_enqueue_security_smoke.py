"""Security and fail-closed smoke for Phase 6-B2 durable enqueue."""
from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from relaylm.relaymem_slp_dispatch_preflight import build_relaymem_slp_dispatch_preflight
from relaylm.relaymem_slp_durable_enqueue import (
    build_relaymem_slp_durable_enqueue_node_result,
    enqueue_relaymem_slp_durable_job,
)
from relaylm.relaymem_slp_job_admission import build_relaymem_slp_job_admission_preflight
from relaylm.relaymem_slp_response_handoff import (
    build_relaymem_slp_response_finalization_handoff,
)


def _lineage() -> dict[str, Any]:
    return {
        "schema_version": "relaymem.primary_source_lineage.v0",
        "content_free": True,
        "content_included": False,
        "raw_text_included": False,
        "source_event_kind": "turn",
        "namespace": "private-namespace",
        "valid": True,
        "lineage_fingerprint": "b" * 64,
        "lineage_shape": {
            "source_event_id_present": True,
            "run_id_present": True,
            "session_id_present": True,
            "turn_index_present": True,
        },
        "blocked_reasons": [],
    }


def _ready():
    admission = build_relaymem_slp_job_admission_preflight(
        enabled=True,
        dry_run_only=True,
        enqueue_enabled=False,
        trigger_mode="turn_end",
        processing_stage="primary_formation",
        run_id="private-run",
        turn_index=7,
        session_id="private-session",
        namespace="private-namespace",
        source_event_kind="turn",
        source_lineage_artifact=_lineage(),
        source_count=1,
        visible_response_finalized=True,
        runtime_terminal_status="completed",
        persistence_policy_status="allowed",
    )
    handoff = build_relaymem_slp_response_finalization_handoff(
        admission,
        enabled=True,
        dry_run_only=True,
        response_finalized=True,
    )
    return build_relaymem_slp_dispatch_preflight(
        handoff,
        enabled=True,
        dry_run_only=True,
    )


def _filename(dispatch_key: str) -> str:
    return "slp-dispatch-v0-" + dispatch_key.split(":", 1)[1] + ".json"


def _canonical(value: dict[str, object]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _timestamped_record(ready) -> dict[str, object]:
    assert ready.durable_job is not None
    record = ready.durable_job.to_runtime_dict()
    record["created_at"] = "2026-06-22T00:00:00.000000Z"
    record["updated_at"] = "2026-06-22T00:00:00.000000Z"
    return record


def _contains(value: Any, target: Any) -> bool:
    if value == target:
        return True
    if isinstance(value, dict):
        return any(_contains(item, target) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains(item, target) for item in value)
    return False


def _classify_existing(ready, root: Path):
    return enqueue_relaymem_slp_durable_job(
        ready,
        queue_root=str(root),
        enabled=True,
    )


def main() -> None:
    ready = _ready()
    assert ready.status == "dry_run_ready"
    assert ready.durable_job is not None
    filename = _filename(ready.durable_job.dispatch_idempotency_key)

    bool_as_int = replace(ready, enabled=1)
    invalid_bool = enqueue_relaymem_slp_durable_job(
        bool_as_int,
        queue_root=None,
        enabled=True,
    )
    assert invalid_bool.status == "invalid_input"
    assert "b1_preflight_not_eligible" in invalid_bool.blocked_reasons

    tampered_job = replace(ready.durable_job, turn_index=True)
    tampered_ready = replace(ready, durable_job=tampered_job)
    invalid_integer = enqueue_relaymem_slp_durable_job(
        tampered_ready,
        queue_root=None,
        enabled=True,
    )
    assert invalid_integer.status == "invalid_input"
    assert "durable_job_turn_index_invalid" in invalid_integer.blocked_reasons

    bad_job_id = replace(ready.durable_job, job_id="slp-job-v0:" + "0" * 64)
    bad_job_ready = replace(ready, durable_job=bad_job_id)
    invalid_job_id = enqueue_relaymem_slp_durable_job(
        bad_job_ready,
        queue_root=None,
        enabled=True,
    )
    assert invalid_job_id.status == "invalid_input"
    assert "durable_job_job_id_mismatch" in invalid_job_id.blocked_reasons

    with TemporaryDirectory() as directory:
        parent = Path(directory).resolve()
        real_root = parent / "real"
        real_root.mkdir()
        symlink_root = parent / "queue-link"
        symlink_root.symlink_to(real_root, target_is_directory=True)
        result = enqueue_relaymem_slp_durable_job(
            ready,
            queue_root=str(symlink_root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert result.status == "write_failed"
        assert "queue_root_symlink_blocked" in result.blocked_reasons
        assert list(real_root.iterdir()) == []

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        external = root / "external"
        external.write_text("do not follow", encoding="utf-8")
        (root / filename).symlink_to(external)
        result = _classify_existing(ready, root)
        assert result.status == "blocked_corrupt"
        assert "queue_record_symlink_blocked" in result.blocked_reasons
        assert external.read_text(encoding="utf-8") == "do not follow"

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        (root / filename).mkdir()
        result = _classify_existing(ready, root)
        assert result.status == "blocked_corrupt"
        assert "queue_record_unexpected_file_type" in result.blocked_reasons

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        (root / filename).write_bytes(b"\xff\xfe\xfd")
        result = _classify_existing(ready, root)
        assert result.status == "blocked_corrupt"
        assert "queue_record_malformed_utf8" in result.blocked_reasons

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        (root / filename).write_text('{"x":1,"x":2}', encoding="utf-8")
        result = _classify_existing(ready, root)
        assert result.status == "blocked_corrupt"
        assert "queue_record_duplicate_json_key" in result.blocked_reasons

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = _timestamped_record(ready)
        record["unexpected"] = True
        (root / filename).write_bytes(_canonical(record))
        before = (root / filename).read_bytes()
        result = _classify_existing(ready, root)
        assert result.status == "blocked_corrupt"
        assert "durable_job_shape_mismatch" in result.blocked_reasons
        assert (root / filename).read_bytes() == before

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = _timestamped_record(ready)
        record["run_id"] = "different-run"
        record["unexpected"] = True
        (root / filename).write_bytes(_canonical(record))
        result = _classify_existing(ready, root)
        assert result.status == "blocked_corrupt"
        assert result.outcome == "blocked_corrupt"
        assert "durable_job_shape_mismatch" in result.blocked_reasons

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = _timestamped_record(ready)
        encoded = _canonical(record)
        marker = f'"turn_index":{record["turn_index"]}'.encode("ascii")
        assert marker in encoded
        (root / filename).write_bytes(encoded.replace(marker, b'"turn_index":NaN'))
        result = _classify_existing(ready, root)
        assert result.status == "blocked_corrupt"
        assert result.outcome == "blocked_corrupt"
        assert "queue_record_malformed_json" in result.blocked_reasons

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = _timestamped_record(ready)
        record["run_id"] = "different-run"
        (root / filename).write_bytes(_canonical(record))
        before = (root / filename).read_bytes()
        result = _classify_existing(ready, root)
        assert result.status == "blocked_collision"
        assert result.outcome == "blocked_collision"
        assert "dispatch_identity_collision" in result.blocked_reasons
        assert (root / filename).read_bytes() == before

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = _timestamped_record(ready)
        (root / filename).write_text(json.dumps(record), encoding="utf-8")
        result = _classify_existing(ready, root)
        assert result.status == "blocked_corrupt"
        assert "queue_record_noncanonical_json" in result.blocked_reasons

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = _timestamped_record(ready)
        record["created_at"] = "not-a-timestamp"
        record["updated_at"] = "not-a-timestamp"
        (root / filename).write_bytes(_canonical(record))
        result = _classify_existing(ready, root)
        assert result.status == "blocked_corrupt"
        assert "durable_job_timestamp_invalid" in result.blocked_reasons

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = _timestamped_record(ready)
        record["dispatch_idempotency_key"] = "slp-dispatch-v0:" + "0" * 64
        (root / filename).write_bytes(_canonical(record))
        result = _classify_existing(ready, root)
        assert result.status == "blocked_corrupt"
        assert "queue_record_key_path_mismatch" in result.blocked_reasons

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        applied = enqueue_relaymem_slp_durable_job(
            ready,
            queue_root=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert applied.status == "enqueued_new"
        projection = applied.to_log_dict()
        node = build_relaymem_slp_durable_enqueue_node_result(applied)
        private_values = (
            "private-run",
            "private-session",
            "private-namespace",
            "b" * 64,
            ready.durable_job.job_id,
            ready.durable_job.dispatch_idempotency_key,
            str(root),
            applied.durable_record["created_at"] if applied.durable_record else "",
        )
        for private_value in private_values:
            assert _contains(projection, private_value) is False
            assert _contains(node.to_log_dict(), private_value) is False
        runtime = applied.to_runtime_dict()
        assert runtime["worker_invoked"] is False
        assert runtime["invokes_slp"] is False
        assert runtime["writes_memory"] is False
        assert runtime["mutates_soul"] is False
        assert runtime["changes_visible_response"] is False

    relative_root = enqueue_relaymem_slp_durable_job(
        ready,
        queue_root="relative/queue",
        enabled=True,
    )
    assert relative_root.status == "write_failed"
    assert "queue_root_must_be_absolute" in relative_root.blocked_reasons

    nul_root = enqueue_relaymem_slp_durable_job(
        ready,
        queue_root="/tmp/bad\x00root",
        enabled=True,
    )
    assert nul_root.status == "write_failed"
    assert "queue_root_invalid" in nul_root.blocked_reasons

    print("Phase 6-B2 durable enqueue security smoke: ok")


if __name__ == "__main__":
    main()

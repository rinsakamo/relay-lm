"""Determinism, projection, and no-mutation cases for the outcome smoke."""
import json
import tempfile
from pathlib import Path

from relaylm_phase6c1_primary_worker_outcome_support import (
    classify,
    m3e_applied,
    m3g,
    m3h,
)


def run_purity_cases(results: tuple[object, ...]) -> None:
    repeated = [
        classify(m3e_applied(), m3g(), m3h()).to_runtime_dict()
        for _ in range(20)
    ]
    assert all(item == repeated[0] for item in repeated)

    projection = results[0].to_log_dict()
    assert set(projection) == {
        "schema_version",
        "status",
        "transition_kind",
        "terminal_state",
        "retry_class",
        "failure_class",
        "terminal_reason_id",
        "retryable",
        "terminal",
        "policy_held",
        "manual_confirmation_required",
        "recovery_isolation_required",
        "durable_success_verified",
    }
    serialized = json.dumps(projection, sort_keys=True)
    forbidden = (
        "title",
        "summary",
        "page_relative_path",
        "index.md",
        "log.md",
        "namespace",
        "run_id",
        "session_id",
        "job_id",
        "dispatch",
        "lineage",
        "idempotency_key",
        "claim_owner",
        "lease_token",
        "timestamp",
        "exception",
    )
    assert not any(token in serialized for token in forbidden)

    with tempfile.TemporaryDirectory() as root:
        root_path = Path(root)
        queue_path = root_path / "queue"
        memory_path = root_path / "memory"
        queue_path.mkdir()
        memory_path.mkdir()
        (queue_path / "sentinel").write_text(
            "queue-stable",
            encoding="utf-8",
        )
        (memory_path / "sentinel").write_text(
            "memory-stable",
            encoding="utf-8",
        )
        before = _snapshot(root_path)
        for _ in range(10):
            classify(m3e_applied(), m3g(), m3h())
        assert before == _snapshot(root_path)

    assert all(
        "dead_letter" not in json.dumps(
            item.to_runtime_dict(),
            sort_keys=True,
        )
        for item in results
    )


def _snapshot(root_path: Path) -> list[tuple[Path, bytes]]:
    return sorted(
        (path.relative_to(root_path), path.read_bytes())
        for path in root_path.rglob("*")
        if path.is_file()
    )

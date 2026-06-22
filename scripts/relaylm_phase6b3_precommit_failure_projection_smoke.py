"""Regression smoke for B3 pre-rename failure state projections."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import relaylm.relaymem_slp_queue_state as queue_state
import relaylm.relaymem_slp_queue_storage as queue_storage
from scripts.relaylm_phase6b3_queue_state_security_smoke import (
    _call,
    _filename,
    _read,
    _record,
    _request,
    _write,
)


def main() -> None:
    original_now = queue_state._now_utc
    original_reopen = queue_storage.reopen_and_compare
    try:
        queue_state._now_utc = lambda: datetime(
            2026, 6, 22, 2, 0, tzinfo=timezone.utc
        )
        queue_storage.reopen_and_compare = (
            lambda root_fd, filename, snapshot: "queue_record_bytes_changed"
        )

        record = _record(run_id="precommit-projection", lineage="7" * 64)
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, record)
            original_bytes = path.read_bytes()

            result = _call(root, _request(record))
            assert result.status == "conflict"
            assert result.transition_attempted is True
            assert result.transition_applied is False
            assert result.durability_confirmed is False
            assert "queue_record_bytes_changed" in result.blocked_reasons
            assert result.previous_state == "queued"
            assert result.proposed_state == "queued"
            assert result.durable_record == record

            projection = result.to_log_dict()
            assert projection["queue_state"] == "queued"
            assert projection["attempt_count"] == 0
            assert projection["claim_active"] is False
            assert projection["lease_present"] is False
            assert projection["terminal"] is False
            assert projection["transition_applied"] is False

            assert path.read_bytes() == original_bytes
            assert _read(path) == record
            assert not list(root.glob(".relay-slp-state-*.tmp"))
            assert path.name == _filename(record)

    finally:
        queue_state._now_utc = original_now
        queue_storage.reopen_and_compare = original_reopen

    print("Phase 6-B3 precommit failure projection smoke: ok")


if __name__ == "__main__":
    main()

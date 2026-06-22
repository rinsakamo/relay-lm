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


# Every non-applied failure must project the current persisted queue state.
def main() -> None:
    original_now = queue_state._now_utc
    original_reopen = queue_storage.reopen_and_compare
    original_validate = queue_state.validate_record_mapping
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

        queue_storage.reopen_and_compare = original_reopen

        def reject_claim_proposal(value):
            errors = original_validate(value)
            if errors:
                return errors
            if value.get("state") == "claimed" and value.get("record_revision") == 1:
                return ("test_proposal_invalid",)
            return ()

        queue_state.validate_record_mapping = reject_claim_proposal
        invalid_record = _record(
            run_id="invalid-proposal-projection", lineage="8" * 64
        )
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, invalid_record)
            original_bytes = path.read_bytes()

            result = _call(root, _request(invalid_record))
            assert result.status == "corrupt"
            assert result.transition_attempted is True
            assert result.transition_applied is False
            assert result.durability_confirmed is False
            assert "proposed_record_invalid" in result.blocked_reasons
            assert "test_proposal_invalid" in result.blocked_reasons
            assert result.previous_state == "queued"
            assert result.proposed_state == "queued"
            assert result.durable_record == invalid_record

            projection = result.to_log_dict()
            assert projection["queue_state"] == "queued"
            assert projection["attempt_count"] == 0
            assert projection["claim_active"] is False
            assert projection["lease_present"] is False
            assert projection["terminal"] is False
            assert projection["transition_applied"] is False

            assert path.read_bytes() == original_bytes
            assert _read(path) == invalid_record
            assert not list(root.glob(".relay-slp-state-*.tmp"))

    finally:
        queue_state._now_utc = original_now
        queue_storage.reopen_and_compare = original_reopen
        queue_state.validate_record_mapping = original_validate

    print("Phase 6-B3 precommit failure projection smoke: ok")


if __name__ == "__main__":
    main()

"""Apply the bounded final-review fix for Phase 6-B3 projections."""
from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}")
    target.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    replace_once(
        "relaylm/relaymem_slp_queue_state.py",
        '''            True, apply_requested, False, False, state, str(proposal.get("state")),
            record, ("proposed_record_invalid", *proposal_errors),''',
        '''            True, apply_requested, False, False, state, state,
            record, ("proposed_record_invalid", *proposal_errors),''',
    )

    replace_once(
        "scripts/relaylm_phase6b3_precommit_failure_projection_smoke.py",
        "    original_reopen = queue_storage.reopen_and_compare\n",
        "    original_reopen = queue_storage.reopen_and_compare\n"
        "    original_validate = queue_state.validate_record_mapping\n",
    )

    replace_once(
        "scripts/relaylm_phase6b3_precommit_failure_projection_smoke.py",
        '''            assert path.name == _filename(record)

    finally:''',
        '''            assert path.name == _filename(record)

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

    finally:''',
    )

    replace_once(
        "scripts/relaylm_phase6b3_precommit_failure_projection_smoke.py",
        '''        queue_state._now_utc = original_now
        queue_storage.reopen_and_compare = original_reopen

    print(''',
        '''        queue_state._now_utc = original_now
        queue_storage.reopen_and_compare = original_reopen
        queue_state.validate_record_mapping = original_validate

    print(''',
    )


if __name__ == "__main__":
    main()

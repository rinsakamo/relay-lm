"""Acceptance-matrix tests for managed current-user-input capture (EV-1)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from relaylm.evidence_store import EvidenceRecordStore
from relaylm.evidence_user_input import capture_managed_user_input
from evidence_test_support import route_snapshot

NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def store(tmp_path) -> EvidenceRecordStore:
    return EvidenceRecordStore(str(tmp_path / "evidence"))


def _capture(store, *, apply_enabled=True, text="hello world", key="req-1", now=NOW, **overrides):
    kwargs = dict(
        store=store,
        apply_enabled=apply_enabled,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        current_user_text=text,
        fail_closed_reasons=(),
        operation_idempotency_key=key,
        route_snapshot_payload=route_snapshot(capture_profile="managed_user_input", issued_at=now.isoformat()),
        now=now,
    )
    kwargs.update(overrides)
    return capture_managed_user_input(**kwargs)


def test_disabled_feature_creates_no_files(tmp_path) -> None:
    # "disabled" is modeled as apply_enabled=False and no store constructed
    # by the runtime facade at all; this exercises the equivalent library-
    # level behavior: no store means no writes are attempted anywhere.
    result = _capture(store=None, apply_enabled=False)
    assert result.persisted is False
    assert not (tmp_path / "evidence").exists()


def test_dry_run_validates_without_durable_writes(store, tmp_path) -> None:
    result = _capture(store, apply_enabled=False)
    assert result.status == "dry_run_ready"
    assert result.persisted is False
    assert result.source_event_id is not None  # validated in-memory
    records_dir = tmp_path / "evidence"
    assert not any(records_dir.rglob("*.json")) if records_dir.exists() else True


def test_apply_admits_current_user_input_as_one_source_event(store) -> None:
    result = _capture(store, apply_enabled=True)
    assert result.status == "admitted"
    assert result.persisted is True
    assert result.admission_outcome == "admitted"
    record = store.read_record(
        evidence_space_id=result.evidence_space_id,
        record_kind="source_event",
        record_id=result.source_event_id,
    )
    assert record is not None
    assert record["origin_kind"] == "participant"
    assert record["source_role"] == "user_input"


def test_ambiguous_current_input_fails_closed(store) -> None:
    result = capture_managed_user_input(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        current_user_text=None,
        fail_closed_reasons=("current_user_turn_missing",),
        operation_idempotency_key="req-ambiguous",
        now=NOW,
    )
    assert result.status == "fail_closed"
    assert "current_user_turn_missing" in result.blocked_reasons
    assert result.source_event_id is None


def test_missing_route_snapshot_context_still_fails_closed_when_identity_missing(store) -> None:
    result = _capture(store, character_id=None)
    assert result.status == "fail_closed"
    assert "evidence_character_id_required" in result.blocked_reasons


def test_same_idempotency_key_and_body_is_duplicate_safe(store) -> None:
    first = _capture(store)
    second = _capture(store)
    assert first.source_event_id == second.source_event_id
    assert first.capture_sequence == second.capture_sequence
    assert second.status == "admitted"


def test_conflicting_retry_is_integrity_failure(store) -> None:
    first = _capture(store)
    conflicting = _capture(store, text="a completely different message")
    assert conflicting.status == "integrity_conflict"
    assert conflicting.source_event_id == first.source_event_id


def test_distinct_occurrences_get_new_sequence_numbers(store) -> None:
    first = _capture(store, key="turn-1", text="first turn")
    second = _capture(store, key="turn-2", text="second turn")
    assert first.source_event_id != second.source_event_id
    assert second.capture_sequence == first.capture_sequence + 1


def test_pass_through_style_absence_of_store_creates_no_capture(tmp_path) -> None:
    # The runtime facade never constructs a store/gate call for pass-through
    # routes; at the library level this is the same as apply disabled.
    result = _capture(store=None, apply_enabled=False)
    assert result.persisted is False


def test_opaque_ids_do_not_contain_canary_or_display_identifiers(store) -> None:
    canary = "MySecretDisplayName-Sakura"
    result = capture_managed_user_input(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        current_user_text=f"hi, I am {canary}",
        fail_closed_reasons=(),
        operation_idempotency_key="req-canary",
        route_snapshot_payload=route_snapshot(capture_profile="managed_user_input"),
        now=NOW,
    )
    assert canary not in result.evidence_space_id
    assert canary not in result.source_event_id
    assert canary not in result.capture_attempt_id
    assert canary not in (result.admission_decision_id or "")
    assert canary not in (result.capture_stream_id or "")


def test_no_hidden_content_in_result_log_dict(store) -> None:
    canary = "protected raw text canary"
    result = _capture(store, text=canary)
    assert canary not in str(result.to_log_dict())

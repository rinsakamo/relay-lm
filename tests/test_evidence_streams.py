"""Unit tests for Contract 1D minimal stream/sequence/coverage builders."""
from __future__ import annotations

from relaylm.evidence.common import PrincipalRef
from relaylm.evidence.streams import (
    CaptureSequenceLog,
    build_capture_stream_descriptor,
    compute_coverage_checkpoint,
    reserve_and_complete_authority_change_set,
)


def _descriptor():
    descriptor, reasons = build_capture_stream_descriptor(
        evidence_space_id="evsp_test",
        capture_stream_kind="managed_user_input",
        stream_direction="inbound",
        created_at="t0",
    )
    assert not reasons
    return descriptor


def test_empty_stream_coverage_is_empty_open() -> None:
    descriptor = _descriptor()
    checkpoint = compute_coverage_checkpoint(
        descriptor, [], updated_at="t0", operation_idempotency_key="idem"
    )
    assert checkpoint.derived_coverage_status == "empty_open"
    assert checkpoint.highest_seen_sequence_or_null is None
    assert checkpoint.highest_contiguous_terminal_sequence_or_null is None


def test_contiguous_terminal_sequence_is_sealed_ready() -> None:
    descriptor = _descriptor()
    log = CaptureSequenceLog(descriptor=descriptor)
    for index in range(3):
        sequence, reasons = log.reserve(
            capture_attempt_id=f"ca{index}", recorded_at="t", operation_idempotency_key=f"idem{index}"
        )
        assert not reasons
        ok, reasons = log.terminalize_admission(
            sequence=sequence,
            capture_attempt_id=f"ca{index}",
            admission_decision_id=f"ad{index}",
            terminal_outcome="admitted",
            recorded_at="t",
            operation_idempotency_key=f"idem{index}",
        )
        assert ok, reasons
    checkpoint = compute_coverage_checkpoint(
        descriptor, log.events, updated_at="t1", operation_idempotency_key="idem"
    )
    assert checkpoint.highest_contiguous_terminal_sequence_or_null == 2
    assert checkpoint.missing_sequence_ranges == ()
    assert checkpoint.nonterminal_sequence_ranges == ()
    assert checkpoint.derived_coverage_status == "open_contiguous"
    assert checkpoint.terminal_basis_digest_or_null is not None


def test_gap_and_nonterminal_ranges_are_distinct() -> None:
    descriptor = _descriptor()
    log = CaptureSequenceLog(descriptor=descriptor)
    seq0, _ = log.reserve(capture_attempt_id="ca0", recorded_at="t", operation_idempotency_key="idem0")
    log.terminalize_admission(
        sequence=seq0,
        capture_attempt_id="ca0",
        admission_decision_id="ad0",
        terminal_outcome="admitted",
        recorded_at="t",
        operation_idempotency_key="idem0",
    )
    seq1, _ = log.reserve(
        capture_attempt_id="ca1", recorded_at="t", operation_idempotency_key="idem1"
    )  # left nonterminal
    seq2, _ = log.reserve(capture_attempt_id="ca2", recorded_at="t", operation_idempotency_key="idem2")
    log.terminalize_admission(
        sequence=seq2,
        capture_attempt_id="ca2",
        admission_decision_id="ad2",
        terminal_outcome="admitted",
        recorded_at="t",
        operation_idempotency_key="idem2",
    )

    checkpoint = compute_coverage_checkpoint(
        descriptor, log.events, updated_at="t2", operation_idempotency_key="idem"
    )
    assert checkpoint.highest_seen_sequence_or_null == 2
    assert checkpoint.highest_contiguous_terminal_sequence_or_null == 0
    assert checkpoint.nonterminal_sequence_ranges == ((1, 1),)
    assert checkpoint.missing_sequence_ranges == ()
    assert checkpoint.derived_coverage_status == "open_incomplete"


def test_late_terminalization_closes_nonterminal_range() -> None:
    descriptor = _descriptor()
    log = CaptureSequenceLog(descriptor=descriptor)
    seq0, _ = log.reserve(capture_attempt_id="ca0", recorded_at="t", operation_idempotency_key="idem")
    before = compute_coverage_checkpoint(
        descriptor, log.events, updated_at="t1", operation_idempotency_key="idem"
    )
    assert before.derived_coverage_status == "open_incomplete"
    assert before.nonterminal_sequence_ranges == ((0, 0),)

    ok, reasons = log.terminalize_admission(
        sequence=seq0,
        capture_attempt_id="ca0",
        admission_decision_id="ad0",
        terminal_outcome="admitted",
        recorded_at="t2",
        operation_idempotency_key="idem",
    )
    assert ok, reasons
    after = compute_coverage_checkpoint(
        descriptor, log.events, updated_at="t3", operation_idempotency_key="idem"
    )
    assert after.derived_coverage_status == "open_contiguous"
    assert after.highest_contiguous_terminal_sequence_or_null == 0


def test_restart_rebuild_from_persisted_events_is_exact() -> None:
    descriptor = _descriptor()
    log = CaptureSequenceLog(descriptor=descriptor)
    seq0, _ = log.reserve(capture_attempt_id="ca0", recorded_at="t", operation_idempotency_key="idem")
    log.terminalize_admission(
        sequence=seq0,
        capture_attempt_id="ca0",
        admission_decision_id="ad0",
        terminal_outcome="admitted",
        recorded_at="t",
        operation_idempotency_key="idem",
    )
    before = compute_coverage_checkpoint(
        descriptor, log.events, updated_at="t1", operation_idempotency_key="idem"
    )

    # Simulate a process restart: rebuild purely from the persisted event list.
    rebuilt_log = CaptureSequenceLog.from_events(descriptor, list(log.events))
    after = compute_coverage_checkpoint(
        descriptor, rebuilt_log.events, updated_at="t1", operation_idempotency_key="idem"
    )
    # The checkpoint's own record id is freshly minted per computation; every
    # *derived* field (the actual point of restart rebuild) must be identical.
    before_dict, after_dict = before.to_dict(), after.to_dict()
    del before_dict["coverage_checkpoint_id"], after_dict["coverage_checkpoint_id"]
    assert before_dict == after_dict

    # And the rebuilt log continues sequencing correctly (no reuse of sequence 0).
    seq1, reasons = rebuilt_log.reserve(
        capture_attempt_id="ca1", recorded_at="t2", operation_idempotency_key="idem2"
    )
    assert not reasons
    assert seq1 == 1


def test_terminal_no_source_is_a_valid_terminal_outcome() -> None:
    descriptor = _descriptor()
    log = CaptureSequenceLog(descriptor=descriptor)
    seq0, _ = log.reserve(capture_attempt_id="ca0", recorded_at="t", operation_idempotency_key="idem")
    ok, reasons = log.terminalize_no_source(
        sequence=seq0,
        capture_attempt_id="ca0",
        terminal_reason="no_canonical_content_observed",
        recorded_at="t",
        operation_idempotency_key="idem",
    )
    assert ok, reasons
    checkpoint = compute_coverage_checkpoint(
        descriptor, log.events, updated_at="t1", operation_idempotency_key="idem"
    )
    assert checkpoint.highest_contiguous_terminal_sequence_or_null == 0


def test_sequence_cannot_be_reused_and_conflicting_terminal_is_rejected() -> None:
    descriptor = _descriptor()
    log = CaptureSequenceLog(descriptor=descriptor)
    seq0, _ = log.reserve(capture_attempt_id="ca0", recorded_at="t", operation_idempotency_key="idem")
    log.terminalize_admission(
        sequence=seq0,
        capture_attempt_id="ca0",
        admission_decision_id="ad0",
        terminal_outcome="admitted",
        recorded_at="t",
        operation_idempotency_key="idem",
    )
    ok, reasons = log.terminalize_admission(
        sequence=seq0,
        capture_attempt_id="ca0",
        admission_decision_id="ad-different",
        terminal_outcome="admitted",
        recorded_at="t",
        operation_idempotency_key="idem",
    )
    assert not ok
    assert "capture_sequence_terminal_conflict" in reasons


def test_authority_change_set_rejects_unsupported_change_kind() -> None:
    result, reasons = reserve_and_complete_authority_change_set(
        change_set_id="changeset_x",
        change_kind="source_purged",
        evidence_space_id="evsp_test",
        authoritative_mutation_refs=(),
        recorded_at="t",
    )
    assert result is None
    assert "evidence_change_kind_unsupported_in_ev1" in reasons


def test_authority_change_set_plan_and_complete_share_change_set_id() -> None:
    result, reasons = reserve_and_complete_authority_change_set(
        change_set_id="changeset_y",
        change_kind="source_admitted",
        evidence_space_id="evsp_test",
        participant_ref=PrincipalRef(
            principal_kind="participant",
            principal_id="principal_test",
            authority_domain_ref="participant_domain_test",
        ),
        authoritative_mutation_refs=({"record_kind": "source_event", "record_id": "se1"},),
        recorded_at="t",
    )
    assert not reasons
    assert result is not None
    assert result.plan_event["change_set_id"] == "changeset_y"
    assert result.mark_complete_event["change_set_id"] == "changeset_y"
    assert result.plan_event["change_set_revision"] == 1
    assert result.mark_complete_event["change_set_revision"] == 2

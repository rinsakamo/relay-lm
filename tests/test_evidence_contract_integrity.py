"""Regression tests for EV-1 cross-record, concurrency, and binding invariants."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from relaylm.config import RelayLMConfig
from relaylm.evidence.response_capture import (
    capture_managed_assistant_response_nonstream,
    wrap_stream_with_evidence_response_capture,
)
from relaylm.evidence.response_session import derive_id, prepare_response_capture
from relaylm.evidence.runtime import EvidenceRuntimeGate, _evidence_store_for_gate
from relaylm.evidence.space import (
    derive_evidence_space_id,
    derive_participant_principal,
)
from relaylm.evidence.store import EvidenceRecordStore
from relaylm.evidence.streams import (
    CaptureSequenceLog,
    build_capture_stream_descriptor,
    compute_coverage_checkpoint,
    derive_participant_change_partition_id,
)
from relaylm.evidence.user_input import capture_managed_user_input
from evidence_test_support import route_snapshot

NOW = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc)
BASE_CONFIG_KWARGS = dict(
    backends={
        "local_backend": {
            "type": "openai_compatible",
            "base_url": "http://127.0.0.1:8000/v1",
        }
    },
    model_routes={
        "relaylm-default": {
            "backend": "local_backend",
            "mode": "memory_light",
            "character_id": "char1",
            "memory_namespace": "ns1",
            "user_id": "user1",
            "session_id": "sess1",
        }
    },
)


def _capture_user(
    store: EvidenceRecordStore, key: str, text: str, *, now: datetime = NOW
):
    return capture_managed_user_input(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        current_user_text=text,
        fail_closed_reasons=(),
        operation_idempotency_key=key,
        route_snapshot_payload=route_snapshot(capture_profile="managed_user_input", issued_at=now.isoformat()),
        now=now,
    )


def test_apply_config_rejects_relative_root() -> None:
    with pytest.raises(ValidationError):
        RelayLMConfig(
            **BASE_CONFIG_KWARGS,
            evidence_capture_enabled=True,
            evidence_capture_dry_run_only=False,
            evidence_capture_apply_enabled=True,
            evidence_data_root=".relaylm/evidence",
        )


def test_apply_config_rejects_current_durable_finalization_apply(tmp_path) -> None:
    with pytest.raises(ValidationError):
        RelayLMConfig(
            **BASE_CONFIG_KWARGS,
            evidence_capture_enabled=True,
            evidence_capture_dry_run_only=False,
            evidence_capture_apply_enabled=True,
            evidence_data_root=str(tmp_path / "evidence"),
            relaymem_slp_durable_finalization_enabled=True,
            relaymem_slp_durable_finalization_dry_run_only=False,
            relaymem_slp_durable_finalization_apply_enabled=True,
        )


def test_dry_run_gate_does_not_create_configured_root(tmp_path) -> None:
    root = tmp_path / "must-not-exist"
    config = RelayLMConfig(
        **BASE_CONFIG_KWARGS,
        evidence_capture_enabled=True,
        evidence_capture_dry_run_only=True,
        evidence_capture_apply_enabled=False,
        evidence_data_root=str(root),
    )
    store, reasons = _evidence_store_for_gate(
        config, EvidenceRuntimeGate(True, True, False)
    )
    assert store is None
    assert reasons == ()
    assert not root.exists()


def test_evidence_space_is_character_and_memory_independent() -> None:
    first = derive_evidence_space_id(
        workspace_or_tenant_ref="relaylm-local",
        character_id="char-a",
        memory_namespace="namespace-a",
        session_id="session-1",
    )
    second = derive_evidence_space_id(
        workspace_or_tenant_ref="relaylm-local",
        character_id="char-b",
        memory_namespace="namespace-b",
        session_id="session-1",
    )
    assert first == second


def test_user_capture_persists_attestation_projection_and_coverage_chain(tmp_path) -> None:
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    first = _capture_user(store, "user-one", "first")
    second = _capture_user(
        store, "user-two", "second", now=NOW + timedelta(seconds=1)
    )
    third = _capture_user(
        store, "user-three", "third", now=NOW + timedelta(seconds=2)
    )
    assert first.status == second.status == third.status == "admitted"
    assert first.capture_sequence == 0
    assert second.capture_sequence == 1
    assert third.capture_sequence == 2

    source = store.read_record(
        evidence_space_id=first.evidence_space_id,
        record_kind="source_event",
        record_id=first.source_event_id,
    )
    attestation_ids = source["protected_payload_binding_attestation_ids"]
    assert len(attestation_ids) == 1
    attestation = store.read_record(
        evidence_space_id=first.evidence_space_id,
        record_kind="payload_binding_attestation",
        record_id=attestation_ids[0],
    )
    assert attestation["source_event_id"] == first.source_event_id
    assert attestation["content_digest"] == source["canonical_source_manifest"]["parts"][0]["content_digest_or_null"]

    participant_partition_id = derive_participant_change_partition_id(
        evidence_space_id=first.evidence_space_id,
        participant_ref=derive_participant_principal(
            workspace_or_tenant_ref="relaylm-local", session_id="sess1"
        ),
    )
    projections = store.read_log(
        evidence_space_id=first.evidence_space_id,
        log_kind="change_projection",
        key=participant_partition_id,
    )
    assert [event["partition_sequence"] for event in projections] == [0, 1, 2]
    checkpoints = store.read_log(
        evidence_space_id=first.evidence_space_id,
        log_kind="coverage_checkpoint",
        key="managed_user_input",
    )
    assert [item["coverage_revision"] for item in checkpoints] == [1, 2, 3]
    assert checkpoints[-1]["expected_previous_coverage_revision_or_null"] == 2


def test_capture_sequence_rejects_terminal_attempt_mismatch() -> None:
    descriptor, reasons = build_capture_stream_descriptor(
        evidence_space_id="evsp-test",
        capture_stream_kind="managed_user_input",
        stream_direction="inbound",
        created_at=NOW.isoformat(),
    )
    assert descriptor is not None and not reasons
    log = CaptureSequenceLog(descriptor)
    sequence, reasons = log.reserve(
        capture_attempt_id="attempt-a",
        recorded_at=NOW.isoformat(),
        operation_idempotency_key="reserve-a",
    )
    assert sequence == 0 and not reasons
    ok, reasons = log.terminalize_admission(
        sequence=0,
        capture_attempt_id="attempt-b",
        admission_decision_id="decision-b",
        terminal_outcome="admitted",
        recorded_at=NOW.isoformat(),
        operation_idempotency_key="terminal-b",
    )
    assert not ok
    assert reasons == ("capture_sequence_attempt_mismatch",)
    assert log.unverifiable is True
    checkpoint = compute_coverage_checkpoint(
        descriptor,
        log.events,
        updated_at=NOW.isoformat(),
        operation_idempotency_key="coverage",
    )
    assert checkpoint.derived_coverage_status == "open_incomplete"


def test_nonstream_source_resolves_real_binding_and_attestation(tmp_path) -> None:
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    result = capture_managed_assistant_response_nonstream(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        response_id="response-1",
        delivery_cohort_id="cohort-1",
        request_source_event_ids=(),
        assistant_visible_text="visible answer",
        operation_idempotency_key="assistant-one",
        route_snapshot_payload=route_snapshot(capture_profile="managed_assistant_response", issued_at=NOW.isoformat()),
        now=NOW,
    )
    assert result.status == "admitted"
    source = store.read_record(
        evidence_space_id=result.evidence_space_id,
        record_kind="source_event",
        record_id=result.source_event_id,
    )
    binding_id = source["assistant_response_binding_ref_or_null"]
    binding = store.read_record(
        evidence_space_id=result.evidence_space_id,
        record_kind="assistant_response_binding",
        record_id=binding_id,
    )
    assert binding["response_id"] == "response-1"
    assert binding["completion_extent"] == "response_complete"
    assert binding["termination_cause"] == "normal"
    assert binding["canonical_binding_digest"] == source["source_replay_identity"]["canonical_response_binding_digest"]
    assert len(source["protected_payload_binding_attestation_ids"]) == 1


def test_response_recovery_reuses_persisted_route_snapshot_across_validation_times(
    tmp_path,
) -> None:
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    operation_key = "assistant-route-recovery"
    prepared, reasons = prepare_response_capture(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        response_id="response-recovery",
        delivery_cohort_id="cohort-recovery",
        request_source_event_ids=(),
        operation_idempotency_key=operation_key,
        route_snapshot_payload=route_snapshot(
            capture_profile="managed_assistant_response",
            issued_at=NOW.isoformat(),
        ),
        now=NOW,
    )
    assert prepared is not None and not reasons
    ok, observe_reasons = prepared.observe("visible answer", NOW.isoformat())
    assert ok and not observe_reasons

    recovered = capture_managed_assistant_response_nonstream(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        response_id="response-recovery",
        delivery_cohort_id="cohort-recovery",
        request_source_event_ids=(),
        assistant_visible_text="visible answer",
        operation_idempotency_key=operation_key,
        route_snapshot_payload=route_snapshot(
            capture_profile="managed_assistant_response",
            issued_at=(NOW + timedelta(seconds=5)).isoformat(),
        ),
        now=NOW + timedelta(seconds=5),
    )
    assert recovered.status == "admitted"
    assert recovered.source_event_id is not None


def test_stream_dry_run_hands_off_first_chunk_and_finalizes_diagnostics(tmp_path) -> None:
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    results = []

    async def source():
        yield b'data: {"choices":[{"delta":{"content":"first"},"finish_reason":"stop"}]}\n\n'
        yield b"data: [DONE]\n\n"

    async def run() -> list[bytes]:
        wrapped = wrap_stream_with_evidence_response_capture(
            source(),
            store=store,
            apply_enabled=False,
            character_id="char1",
            memory_namespace="ns1",
            session_id="sess1",
            response_id="response-stream",
            delivery_cohort_id="cohort-stream",
            request_source_event_ids=(),
            operation_idempotency_key="assistant-stream",
            route_snapshot_payload=route_snapshot(
                capture_profile="managed_assistant_response",
                issued_at=NOW.isoformat(),
            ),
            on_finalized=results.append,
        )
        return [chunk async for chunk in wrapped]

    drained = asyncio.run(run())
    assert b"first" in drained[0]
    assert results[0].status == "dry_run_ready"
    assert not any(store.root.rglob("*.json"))

"""Cross-record regressions for EV-1 ValidationBundle and Contract 1C artifacts."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from evidence_test_support import route_snapshot
from relaylm.evidence_response_capture import (
    capture_managed_assistant_response_nonstream,
)
from relaylm.evidence_source_event import build_valid_validation_bundle
from relaylm.evidence_store import EvidenceRecordStore
from relaylm.evidence_user_input import capture_managed_user_input
from relaylm.evidence_validation_artifacts import (
    build_validation_artifact_identities,
)

NOW = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc)


def test_valid_bundle_rejects_missing_artifact_coverage() -> None:
    with pytest.raises(ValueError, match="coverage_incomplete"):
        build_valid_validation_bundle(
            validation_bundle_id="bundle-1",
            validation_bundle_revision_id="bundle-revision-1",
            capture_attempt_id="attempt-1",
            source_event_id="source-1",
            evidence_space_id="space-1",
            recorded_at=NOW.isoformat(),
            gate_kinds=("canonicalization", "integrity"),
            gate_artifact_refs=(("canonicalization", "artifact-1"),),
        )


def test_user_validation_bundle_resolves_real_artifacts_and_change_refs(tmp_path) -> None:
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    operation_key = "request-user:input"
    result = capture_managed_user_input(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        current_user_text="governed input",
        fail_closed_reasons=(),
        operation_idempotency_key=operation_key,
        route_snapshot_payload=route_snapshot(
            capture_profile="managed_user_input",
            issued_at=NOW.isoformat(),
        ),
        now=NOW,
    )
    assert result.status == "admitted"
    identities = build_validation_artifact_identities(
        operation_idempotency_key=operation_key,
        gate_kinds=("canonicalization", "integrity"),
    )
    bundle_id = "valbundle_" + __import__("hashlib").sha256(
        f"{operation_key}\0validation_bundle".encode()
    ).hexdigest()
    bundle = store.read_record(
        evidence_space_id=result.evidence_space_id,
        record_kind="validation_bundle",
        record_id=bundle_id,
    )
    assert bundle["active_artifact_refs"] == [
        identity.derived_artifact_id for identity in identities
    ]
    source = store.read_record(
        evidence_space_id=result.evidence_space_id,
        record_kind="source_event",
        record_id=result.source_event_id,
    )
    for identity in identities:
        artifact = store.read_record(
            evidence_space_id=result.evidence_space_id,
            record_kind="source_derived_artifact_event",
            record_id=identity.artifact_event_id,
        )
        assert artifact["derived_artifact_id"] == identity.derived_artifact_id
        assert artifact["operation_payload"]["result_status"] == "pass"
        assert artifact["authority_change_set_ref_or_null"] == source[
            "authority_change_set_ref"
        ]
    change_set_id = source["authority_change_set_ref"]["change_set_id"]
    change_events = store.read_log(
        evidence_space_id=result.evidence_space_id,
        log_kind="change_set",
        key=change_set_id,
    )
    mutation_refs = change_events[0]["operation_payload"][
        "authoritative_mutation_refs"
    ]
    assert {
        ref["record_id"]
        for ref in mutation_refs
        if ref["record_kind"] == "source_derived_artifact_event"
    } == {identity.artifact_event_id for identity in identities}


def test_assistant_bundle_has_finalization_artifact_bound_to_real_binding(tmp_path) -> None:
    store = EvidenceRecordStore(str(tmp_path / "evidence"))
    operation_key = "request-assistant:response"
    result = capture_managed_assistant_response_nonstream(
        store=store,
        apply_enabled=True,
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
        response_id="response-1",
        delivery_cohort_id="cohort-1",
        request_source_event_ids=(),
        assistant_visible_text="governed answer",
        operation_idempotency_key=operation_key,
        route_snapshot_payload=route_snapshot(
            capture_profile="managed_assistant_response",
            issued_at=NOW.isoformat(),
        ),
        now=NOW,
    )
    assert result.status == "admitted"
    identities = build_validation_artifact_identities(
        operation_idempotency_key=operation_key,
        gate_kinds=("canonicalization", "integrity", "assistant_finalization"),
    )
    source = store.read_record(
        evidence_space_id=result.evidence_space_id,
        record_kind="source_event",
        record_id=result.source_event_id,
    )
    finalization = next(
        identity
        for identity in identities
        if identity.gate_kind == "assistant_finalization"
    )
    artifact = store.read_record(
        evidence_space_id=result.evidence_space_id,
        record_kind="source_derived_artifact_event",
        record_id=finalization.artifact_event_id,
    )
    assert artifact["subject"] == {
        "kind": "assistant_response_binding",
        "assistant_response_binding_id": source[
            "assistant_response_binding_ref_or_null"
        ],
    }
    binding = store.read_record(
        evidence_space_id=result.evidence_space_id,
        record_kind="assistant_response_binding",
        record_id=source["assistant_response_binding_ref_or_null"],
    )
    assert artifact["operation_payload"]["input_digest"] == binding[
        "canonical_binding_digest"
    ]

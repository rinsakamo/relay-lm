from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from relaylm.ctx_ovl_runtime import (
    _AuthorizedCandidate,
    _admit_candidate,
    _build_context_selection,
    _build_sync_event,
    _invalidate_source,
    _new_partition_state,
    _reflex_snapshot,
    _select_overlays,
    evaluate_ctx_ovl_write_attempt,
)
from relaylm.evidence_common import PrincipalRef, utf8_text_digest

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "contracts"
    / "schemas"
    / "ctx-ovl-v1"
    / "relaylm-ctx-ovl-v1.schema.json"
)


def _validate(definition: str, value: dict[str, object]) -> None:
    bundle = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    schema = {
        "$schema": bundle["$schema"],
        "$ref": f"#/$defs/{definition}",
        "$defs": bundle["$defs"],
    }
    Draft202012Validator(
        schema, format_checker=FormatChecker()
    ).validate(value)


def _fixture(now: datetime, text: str = "private prior user text"):
    participant = PrincipalRef(
        principal_kind="participant",
        principal_id="participant_test",
        authority_domain_ref="participant_domain_test",
    )
    state = _new_partition_state(
        session_id="privateconversation_test",
        participant=participant,
        participant_partition_id="ctxovlparticipant_test",
        evidence_space_id="evsp_test",
        change_partition_id="partition_test",
        contract1_partition_epoch_id="partitionepoch_test",
        evaluated_at=now,
    )
    candidate = _AuthorizedCandidate(
        source_event_id="sourceevent_test",
        source_sequence=0,
        text=text,
        content_digest=utf8_text_digest(text),
        actual_bytes=len(text.encode("utf-8")),
        evidence_space_id="evsp_test",
        change_partition_id="partition_test",
        partition_epoch_id="partitionepoch_test",
        authority_snapshot_digest="a" * 64,
        validated_at=now.isoformat(),
        not_after=(now + timedelta(minutes=5)).isoformat(),
    )
    return state, candidate


def test_ovl1_artifacts_match_contract_and_keep_raw_text_private() -> None:
    now = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc)
    canary = "OVL-RAW-CONTENT-CANARY"
    state, candidate = _fixture(now, canary)

    _admit_candidate(
        state,
        candidate,
        partition_sequence=0,
        evaluated_at=now,
        admission_origin="normal_pipeline",
    )
    stored = state.overlays_by_source[candidate.source_event_id]
    selected, reasons = _select_overlays(state, evaluated_at=now)
    assert reasons == ()
    assert selected == [stored]

    selection = _build_context_selection(
        state, selected=selected, evaluated_at=now
    )
    coverage = {
        "change_coverage_checkpoint_id": "changecoverage_test",
        "change_partition_id": "partition_test",
        "partition_epoch_id": "partitionepoch_test",
        "derived_coverage_status": "open_contiguous",
    }
    state.last_observed_partition_sequence = 0
    catch_up = _build_sync_event(
        state,
        mode="catch_up",
        evaluated_at=now,
        admitted_count=1,
        omitted_count=0,
        request_id="request_test",
        coverage_checkpoint=coverage,
    )
    rebuild = _build_sync_event(
        state,
        mode="rebuild",
        evaluated_at=now,
        admitted_count=1,
        omitted_count=0,
        request_id="request_test",
        coverage_checkpoint=coverage,
    )
    reflex = _reflex_snapshot(state, "fresh")

    _validate("PartitionEpochDescriptor", state.partition_epoch_descriptor)
    _validate("CandidateArtifact", stored.artifact)
    _validate("OverlayRecord", stored.record)
    _validate("ContextSelection", selection)
    _validate("CatchUpAttempt", catch_up)
    _validate("RebuildEvent", rebuild)
    _validate("ReflexSnapshot", reflex)
    _validate("WriteAttempt", state.write_attempts[-1])

    serialized = json.dumps(
        {
            "epoch": state.partition_epoch_descriptor,
            "artifact": stored.artifact,
            "record": stored.record,
            "selection": selection,
            "catch_up": catch_up,
            "rebuild": rebuild,
            "reflex": reflex,
            "write_attempts": state.write_attempts,
        },
        sort_keys=True,
    )
    assert canary not in serialized
    assert stored.text == canary
    assert stored.record["durable"] is False
    assert stored.record["rebuildable"] is True
    assert reflex["contains_raw_content"] is False


def test_ttl_is_expired_at_exact_boundary() -> None:
    now = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc)
    state, candidate = _fixture(now)
    _admit_candidate(
        state,
        candidate,
        partition_sequence=0,
        evaluated_at=now,
        admission_origin="normal_pipeline",
    )
    state.overlays_by_source[candidate.source_event_id].record[
        "ttl_expires_at"
    ] = now.isoformat()

    selected, reasons = _select_overlays(state, evaluated_at=now)

    assert reasons == ()
    assert selected == []
    assert candidate.source_event_id not in state.overlays_by_source


def test_invalidation_is_contract_shaped_and_removes_selection() -> None:
    now = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc)
    state, candidate = _fixture(now)
    _admit_candidate(
        state,
        candidate,
        partition_sequence=0,
        evaluated_at=now,
        admission_origin="normal_pipeline",
    )

    _invalidate_source(
        state,
        candidate.source_event_id,
        evaluated_at=now + timedelta(seconds=1),
        reason="restricted",
    )

    invalidation = state.invalidation_events[-1]
    _validate("OverlayInvalidationEvent", invalidation)
    assert (
        state.overlays_by_source[candidate.source_event_id].record[
            "lifecycle_state"
        ]
        == "removed"
    )
    selected, reasons = _select_overlays(
        state, evaluated_at=now + timedelta(seconds=1)
    )
    assert reasons == ()
    assert selected == []


def test_relayatn_write_attempt_is_denied_without_mutation_authority() -> None:
    attempt = evaluate_ctx_ovl_write_attempt(
        session_id="privateconversation_test",
        target_overlay_record_id_or_null="ctxovlrecord_test",
        operation="update",
        attempted_actor_component="relayatn",
    )

    _validate("WriteAttempt", attempt)
    assert attempt["authorized_actor"] is False
    assert attempt["authorized"] is False
    assert attempt["target_authority_domain"] == "ctx_ovl_working_state"

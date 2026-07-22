from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator, FormatChecker

from relaylm.ctx_ovl_change_feed import _bounded_event_slice
from relaylm.ctx_ovl_runtime import (
    _AuthorizedCandidate,
    _admit_candidate,
    _build_context_selection,
    _build_sync_event,
    _config_gate_reasons,
    _invalidate_source,
    _new_partition_state,
    _reflex_snapshot,
    _select_overlays,
    evaluate_ctx_ovl_write_attempt,
)
from relaylm.evidence_common import PrincipalRef, utf8_text_digest

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = (
    _ROOT
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


def _contract_validator():
    path = _ROOT / "scripts" / "relaylm_ctx_ovl_v1_validate.py"
    spec = importlib.util.spec_from_file_location("ctx_ovl_contract_validator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.Validator()


def _fixture(
    now: datetime,
    text: str = "private prior user text",
    *,
    source_event_id: str = "sourceevent_test",
):
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
        source_event_id=source_event_id,
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


def _coverage() -> dict[str, object]:
    return {
        "change_coverage_checkpoint_id": "changecoverage_test",
        "change_partition_id": "partition_test",
        "partition_epoch_id": "partitionepoch_test",
        "derived_coverage_status": "open_contiguous",
    }


def _assert_bounded_state_valid(records: list[dict[str, object]]) -> None:
    errors = _contract_validator().validate_case({"records": records})
    assert errors == [], [(error.error_id, error.detail) for error in errors]


def test_ovl1_artifacts_match_contract_and_keep_raw_text_private() -> None:
    now = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc)
    canary = "OVL-RAW-CONTENT-CANARY"
    state, candidate = _fixture(now, canary)

    overlay_id = _admit_candidate(
        state,
        candidate,
        partition_sequence=0,
        evaluated_at=now,
        admission_origin="normal_pipeline",
    )
    stored = state.overlays_by_source[candidate.source_event_id]
    assert overlay_id == stored.record["overlay_record_id"]
    selected, reasons = _select_overlays(state, evaluated_at=now)
    assert reasons == ()
    assert selected == [stored]

    selection = _build_context_selection(
        state, selected=selected, evaluated_at=now
    )
    reflex = _reflex_snapshot(state, "fresh")

    _validate("PartitionEpochDescriptor", state.partition_epoch_descriptor)
    _validate("CandidateArtifact", stored.artifact)
    _validate("OverlayRecord", stored.record)
    _validate("ContextSelection", selection)
    _validate("ReflexSnapshot", reflex)
    _validate("WriteAttempt", state.write_attempts[-1])
    _assert_bounded_state_valid(
        [
            state.partition_epoch_descriptor,
            stored.artifact,
            stored.record,
            selection,
            reflex,
            state.write_attempts[-1],
        ]
    )

    serialized = json.dumps(
        {
            "epoch": state.partition_epoch_descriptor,
            "artifact": stored.artifact,
            "record": stored.record,
            "selection": selection,
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


def test_runtime_sync_records_are_cross_record_contract_valid() -> None:
    now = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc)
    validator = _contract_validator()

    for mode, origin in (
        ("catch_up", "catch_up_pipeline"),
        ("rebuild", "rebuild_pipeline"),
    ):
        state, candidate = _fixture(
            now, source_event_id=f"sourceevent_{mode}"
        )
        overlay_id = _admit_candidate(
            state,
            candidate,
            partition_sequence=0,
            evaluated_at=now,
            admission_origin=origin,
        )
        state.last_observed_partition_sequence = 0
        operation = _build_sync_event(
            state,
            mode=mode,
            evaluated_at=now,
            produced_overlay_record_ids=(overlay_id,),
            authority_snapshot_digest=candidate.authority_snapshot_digest,
            omitted_count=0,
            request_id="request_test",
            coverage_checkpoint=_coverage(),
        )
        definition = "CatchUpAttempt" if mode == "catch_up" else "RebuildEvent"
        _validate(definition, operation)
        stored = state.overlays_by_source[candidate.source_event_id]
        errors = validator.validate_case(
            {
                "records": [
                    state.partition_epoch_descriptor,
                    stored.artifact,
                    stored.record,
                    operation,
                ]
            }
        )
        assert errors == [], [(error.error_id, error.detail) for error in errors]


def test_noop_catch_up_never_claims_preexisting_active_overlays() -> None:
    now = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc)
    state, candidate = _fixture(now)
    _admit_candidate(
        state,
        candidate,
        partition_sequence=0,
        evaluated_at=now,
        admission_origin="normal_pipeline",
    )
    state.last_observed_partition_sequence = 0

    catch_up = _build_sync_event(
        state,
        mode="catch_up",
        evaluated_at=now,
        produced_overlay_record_ids=(),
        authority_snapshot_digest=None,
        omitted_count=0,
        request_id="request_test",
        coverage_checkpoint=_coverage(),
    )

    _validate("CatchUpAttempt", catch_up)
    assert catch_up["outcome"] == "no_catch_up_needed"
    assert catch_up["produced_overlay_record_ids"] == []


def test_catch_up_backlog_advances_in_bounded_pages() -> None:
    events = [
        {
            "partition_sequence": index,
            "change_partition_id": "partition_test",
            "partition_epoch_id": "partitionepoch_test",
        }
        for index in range(100)
    ]
    coverage = [
        {
            "change_partition_id": "partition_test",
            "partition_epoch_id": "partitionepoch_test",
            "derived_coverage_status": "open_contiguous",
            "highest_contiguous_committed_sequence_or_null": 99,
        }
    ]

    first, first_watermark, reasons = _bounded_event_slice(
        projection_events=events,
        coverage_events=coverage,
        change_partition_id="partition_test",
        partition_epoch_id="partitionepoch_test",
        last_observed=-1,
        mode="catch_up",
    )
    second, second_watermark, reasons2 = _bounded_event_slice(
        projection_events=events,
        coverage_events=coverage,
        change_partition_id="partition_test",
        partition_epoch_id="partitionepoch_test",
        last_observed=first_watermark,
        mode="catch_up",
    )

    assert reasons == ()
    assert reasons2 == ()
    assert len(first) == 64
    assert first_watermark == 63
    assert len(second) == 36
    assert second_watermark == 99


def test_selection_fails_closed_on_artifact_scope_tamper() -> None:
    now = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc)
    state, candidate = _fixture(now)
    _admit_candidate(
        state,
        candidate,
        partition_sequence=0,
        evaluated_at=now,
        admission_origin="normal_pipeline",
    )
    state.overlays_by_source[candidate.source_event_id].artifact[
        "evidence_space_id"
    ] = "evsp_other"

    selected, reasons = _select_overlays(state, evaluated_at=now)

    assert selected == []
    assert reasons == ("ctx_ovl_selection_artifact_scope_invalid",)


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


def test_invalidation_is_contract_shaped_and_retains_resolvable_tombstone() -> None:
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
    stored = state.overlays_by_source[candidate.source_event_id]
    assert stored.record["lifecycle_state"] == "removed"
    selected, reasons = _select_overlays(
        state, evaluated_at=now + timedelta(seconds=1)
    )
    assert reasons == ()
    assert selected == []
    assert candidate.source_event_id in state.overlays_by_source
    _assert_bounded_state_valid(
        [
            state.partition_epoch_descriptor,
            stored.artifact,
            stored.record,
            invalidation,
        ]
    )


def test_watermark_invalidation_records_strict_advancement() -> None:
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
        reason="watermark_advanced",
        new_highest_observed_sequence=2,
    )

    invalidation = state.invalidation_events[-1]
    assert invalidation["prior_highest_observed_partition_sequence_or_null"] == 0
    assert invalidation["authorization_ref"][
        "highest_observed_partition_sequence"
    ] == 2
    _validate("OverlayInvalidationEvent", invalidation)


def test_apply_is_fenced_from_relayemo_and_legacy_relayctx_writer() -> None:
    config = SimpleNamespace(
        ctx_ovl_dry_run_only=False,
        ctx_ovl_apply_enabled=True,
        relayemo_enabled=True,
        relayctx_short_term_runtime_injection_apply_enabled=True,
    )
    assert _config_gate_reasons(config) == (
        "ctx_ovl_apply_conflicts_with_relayemo_analysis",
        "ctx_ovl_apply_conflicts_with_legacy_relayctx_injection",
    )

    dry_run = SimpleNamespace(
        ctx_ovl_dry_run_only=True,
        ctx_ovl_apply_enabled=False,
        relayemo_enabled=True,
        relayctx_short_term_runtime_injection_apply_enabled=True,
    )
    assert _config_gate_reasons(dry_run) == ()


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

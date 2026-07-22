"""OVL-1 candidate admission, invalidation, and sync record builders."""
from __future__ import annotations

from datetime import datetime, timedelta

from relaylm.ctx_ovl_types import (
    _AuthorizedCandidate, _ParticipantPartitionState, _StoredOverlay,
    _CATCH_UP_MAX_EVENTS,
    _CATCH_UP_MAX_TOTAL_BYTES, _MAX_CANDIDATE_BYTES, _REBUILD_MAX_RECORDS,
    _REBUILD_MAX_TOTAL_BYTES, _TTL_SECONDS, _parse_datetime,
    _record_write_attempt,
)
from relaylm.evidence_common import canonical_digest, new_opaque_id


def _admit_candidate(
    state: _ParticipantPartitionState,
    candidate: _AuthorizedCandidate,
    *,
    partition_sequence: int,
    evaluated_at: datetime,
    admission_origin: str,
) -> None:
    producer = (
        "ctx_ovl_rebuild_process"
        if admission_origin == "rebuild_pipeline"
        else "relayctx_pipeline"
    )
    existing = state.overlays_by_source.get(candidate.source_event_id)
    if existing is not None:
        _record_write_attempt(
            state,
            target_overlay_record_id_or_null=str(
                existing.record.get("overlay_record_id")
            ),
            operation="update",
            actor=producer,
        )
        if (
            existing.artifact.get("content_digest") != candidate.content_digest
            or existing.record.get("contract1_binding", {}).get(
                "authority_snapshot_digest"
            )
            != candidate.authority_snapshot_digest
        ):
            existing.record["lifecycle_state"] = "removed"
        else:
            existing.partition_sequence = partition_sequence
            existing.record["last_validated_authorization"] = {
                "change_partition_id": candidate.change_partition_id,
                "partition_epoch_id": candidate.partition_epoch_id,
                "highest_observed_partition_sequence": candidate.source_sequence,
                "authority_snapshot_digest": candidate.authority_snapshot_digest,
                "watermark_freshness": "current",
                "validated_access_state": "admitted",
                "validated_at": candidate.validated_at,
            }
            ttl_limit = min(
                evaluated_at + timedelta(seconds=_TTL_SECONDS),
                _parse_datetime(candidate.not_after) or evaluated_at,
            )
            existing.record["ttl_expires_at"] = ttl_limit.isoformat()
            existing.record["lifecycle_state"] = "active"
            return

    _record_write_attempt(
        state,
        target_overlay_record_id_or_null=None,
        operation="admit",
        actor=producer,
    )
    # IDs are intentionally random opaque tokens. Content identity remains in
    # the explicit digest fields; identifiers must not become reversible or
    # correlation-friendly encodings of source content.
    artifact_id = new_opaque_id("ctxovlartifact")
    artifact = {
        "schema": "relaylm.ctx_ovl_candidate_artifact.v1",
        "artifact_id": artifact_id,
        "artifact_kind": "validated_sidecar",
        "authority_domain": "relayctx_candidate_artifact",
        "producer_component": producer,
        "session_id": state.session_id,
        "source_event_id": candidate.source_event_id,
        "evidence_space_id": candidate.evidence_space_id,
        "content_kind": "opaque_bounded_text",
        "content_digest": candidate.content_digest,
        "actual_bytes": candidate.actual_bytes,
        "immutable": True,
    }
    overlay_id = new_opaque_id("ctxovlrecord")
    ttl_limit = min(
        evaluated_at + timedelta(seconds=_TTL_SECONDS),
        _parse_datetime(candidate.not_after) or evaluated_at,
    )
    record = {
        "schema": "relaylm.ctx_ovl_overlay_record.v1",
        "overlay_record_id": overlay_id,
        "session_id": state.session_id,
        "partition_kind": "participant",
        "partition_id": state.partition_id,
        "partition_epoch_ref": {
            "partition_epoch_descriptor_id": state.partition_epoch_descriptor[
                "partition_epoch_descriptor_id"
            ],
            "epoch_sequence": 1,
        },
        "participant_ref": {
            "participant_id_or_null": state.participant_id,
            "identity_status": "known",
        },
        "source_provenance": {
            "source_event_id": candidate.source_event_id,
            "evidence_space_id": candidate.evidence_space_id,
            "capture_stream_id_or_null": None,
            "source_access_state_at_admission": "admitted",
        },
        "contract1_binding": {
            "evidence_space_id": candidate.evidence_space_id,
            "source_event_id": candidate.source_event_id,
            "change_partition_id": candidate.change_partition_id,
            "partition_epoch_id": candidate.partition_epoch_id,
            "authority_snapshot_digest": candidate.authority_snapshot_digest,
        },
        "last_validated_authorization": {
            "change_partition_id": candidate.change_partition_id,
            "partition_epoch_id": candidate.partition_epoch_id,
            "highest_observed_partition_sequence": candidate.source_sequence,
            "authority_snapshot_digest": candidate.authority_snapshot_digest,
            "watermark_freshness": "current",
            "validated_access_state": "admitted",
            "validated_at": candidate.validated_at,
        },
        "candidate_envelope": {
            "envelope_kind": "validated_sidecar_envelope",
            "content_kind": "opaque_bounded_text",
            "envelope_version": 1,
            "producer_artifact_ref": {
                "artifact_id": artifact_id,
                "artifact_kind": "validated_sidecar",
                "authority_domain": "relayctx_candidate_artifact",
                "producer_component": producer,
                "session_id": state.session_id,
                "source_event_id": candidate.source_event_id,
                "evidence_space_id": candidate.evidence_space_id,
                "content_kind": "opaque_bounded_text",
                "content_digest": candidate.content_digest,
            },
            "content_address_space": "ctx_ovl_candidate_artifact",
            "content_digest": candidate.content_digest,
            "raw_source_content_present": False,
            "size_bound": {
                "bounded": True,
                "max_bytes": _MAX_CANDIDATE_BYTES,
                "actual_bytes": candidate.actual_bytes,
            },
        },
        "admission_origin": admission_origin,
        "created_by_actor": producer,
        "candidate_basis": "validated_sidecar",
        "visibility_scope": "participant_private",
        "lifecycle_state": "active",
        "superseded_by_overlay_record_id_or_null": None,
        "non_shadowing": False,
        "quarantine_shadow_target_overlay_record_id_or_null": None,
        "rebuildable": True,
        "durable": False,
        "ttl_expires_at": ttl_limit.isoformat(),
    }
    state.overlays_by_source[candidate.source_event_id] = _StoredOverlay(
        artifact=artifact,
        record=record,
        text=candidate.text,
        partition_sequence=partition_sequence,
    )


def _invalidate_event_sources(
    state: _ParticipantPartitionState,
    event: dict,
    *,
    evaluated_at: datetime,
    reason: str,
) -> None:
    refs = event.get("authorized_source_event_refs")
    if not isinstance(refs, list):
        return
    for source_id in refs:
        if isinstance(source_id, str):
            _invalidate_source(
                state, source_id, evaluated_at=evaluated_at, reason=reason
            )


def _invalidate_source(
    state: _ParticipantPartitionState,
    source_id: str,
    *,
    evaluated_at: datetime,
    reason: str,
) -> None:
    item = state.overlays_by_source.get(source_id)
    if item is None:
        return
    record = item.record
    prior = record.get("last_validated_authorization", {})
    binding = record.get("contract1_binding", {})
    if not isinstance(prior, dict) or not isinstance(binding, dict):
        record["lifecycle_state"] = "removed"
        return
    _record_write_attempt(
        state,
        target_overlay_record_id_or_null=str(record.get("overlay_record_id")),
        operation="remove",
        actor="relayctx_pipeline",
    )
    record["lifecycle_state"] = "removed"
    event = {
        "schema": "relaylm.ctx_ovl_overlay_invalidation_event.v1",
        "invalidation_event_id": new_opaque_id("ctxovlinvalidation"),
        "session_id": state.session_id,
        "affected_overlay_record_ids": [record["overlay_record_id"]],
        "invalidation_reason": reason,
        "resulting_lifecycle_state": "removed",
        "authorization_ref": {
            "change_partition_id": prior.get("change_partition_id"),
            "partition_epoch_id": prior.get("partition_epoch_id"),
            "highest_observed_partition_sequence": prior.get(
                "highest_observed_partition_sequence"
            ),
            "authority_snapshot_digest": prior.get("authority_snapshot_digest"),
            "watermark_freshness": "stale",
            "validated_access_state": "restricted",
            "validated_at": evaluated_at.isoformat(),
        },
        "prior_highest_observed_partition_sequence_or_null": prior.get(
            "highest_observed_partition_sequence"
        ),
        "invalidation_scope_binding": dict(binding),
    }
    state.invalidation_events.append(event)
    del state.invalidation_events[:-_REBUILD_MAX_RECORDS]


def _build_sync_event(
    state: _ParticipantPartitionState,
    *,
    mode: str,
    evaluated_at: datetime,
    admitted_count: int,
    omitted_count: int,
    request_id: str,
    coverage_checkpoint: dict | None,
) -> dict[str, object]:
    newest = max(
        state.active_overlays(),
        key=lambda item: item.partition_sequence,
        default=None,
    )
    authority_digest = (
        str(
            newest.record["last_validated_authorization"][
                "authority_snapshot_digest"
            ]
        )
        if newest is not None
        else canonical_digest(
            {
                "partition": state.change_partition_id,
                "epoch": state.contract1_partition_epoch_id,
                "watermark": state.last_observed_partition_sequence,
            }
        )
    )
    authorization = {
        "change_partition_id": state.change_partition_id,
        "partition_epoch_id": state.contract1_partition_epoch_id,
        "highest_observed_partition_sequence": max(
            state.last_observed_partition_sequence, 0
        ),
        "authority_snapshot_digest": authority_digest,
        "watermark_freshness": "current",
        "validated_access_state": "admitted",
        "validated_at": evaluated_at.isoformat(),
    }
    coverage_ref = {
        "change_coverage_checkpoint_id": (
            str(coverage_checkpoint.get("change_coverage_checkpoint_id"))
            if isinstance(coverage_checkpoint, dict)
            else "ctxovl_empty_change_coverage"
        ),
        "change_partition_id": state.change_partition_id,
        "partition_epoch_id": state.contract1_partition_epoch_id,
        "derived_coverage_status": (
            str(coverage_checkpoint.get("derived_coverage_status"))
            if isinstance(coverage_checkpoint, dict)
            else "empty_open"
        ),
    }
    if mode == "rebuild":
        return {
            "schema": "relaylm.ctx_ovl_rebuild_event.v1",
            "rebuild_event_id": new_opaque_id("ctxovlrebuild"),
            "session_id": state.session_id,
            "evaluated_at": evaluated_at.isoformat(),
            "triggered_by": "cache_loss",
            "source_basis": "current_authorized_governed_evidence",
            "coverage_checkpoint_ref": coverage_ref,
            "authorization_ref": authorization,
            "durable_state_claimed": False,
            "produced_overlay_record_ids": [
                item.record["overlay_record_id"] for item in state.active_overlays()
            ],
            "excluded_reason_codes": ["restricted"] if omitted_count else [],
            "rebuild_bound": {
                "bounded": True,
                "max_overlay_records": _REBUILD_MAX_RECORDS,
                "max_total_candidate_bytes": _REBUILD_MAX_TOTAL_BYTES,
            },
            "budget_policy_ref": {
                "policy_id": "ctx_ovl_budget_policy_v1",
                "policy_version": 1,
                "authority_domain": "relayctx_contract",
            },
        }
    return {
        "schema": "relaylm.ctx_ovl_catch_up_attempt.v1",
        "catch_up_attempt_id": new_opaque_id("ctxovlcatchup"),
        "session_id": state.session_id,
        "triggering_admitted_request_id": request_id,
        "evaluated_at": evaluated_at.isoformat(),
        "pipeline_path_confirmation": (
            "normal_rel_scn_emo_int_mem_retrieval_ctx_pipeline"
        ),
        "completeness_claimed_from": "coverage_checkpoint",
        "coverage_checkpoint_ref": coverage_ref,
        "authorization_watermark_ref": {
            "change_partition_id": state.change_partition_id,
            "partition_epoch_id": state.contract1_partition_epoch_id,
            "highest_observed_partition_sequence": max(
                state.last_observed_partition_sequence, 0
            ),
            "authority_snapshot_digest": authority_digest,
            "watermark_freshness": "current",
        },
        "eligible_selection_bound": {
            "bounded": True,
            "max_events": _CATCH_UP_MAX_EVENTS,
            "max_total_candidate_bytes": _CATCH_UP_MAX_TOTAL_BYTES,
        },
        "outcome": (
            "bounded_catch_up_applied" if admitted_count else "no_catch_up_needed"
        ),
        "produced_overlay_record_ids": [
            item.record["overlay_record_id"] for item in state.active_overlays()
        ],
        "budget_policy_ref": {
            "policy_id": "ctx_ovl_budget_policy_v1",
            "policy_version": 1,
            "authority_domain": "relayctx_contract",
        },
    }


__all__ = ["_admit_candidate", "_build_sync_event",
           "_invalidate_event_sources", "_invalidate_source"]

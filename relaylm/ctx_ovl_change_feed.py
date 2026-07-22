"""OVL-1 Contract 1 change-partition and coverage validation."""
from __future__ import annotations

from collections.abc import Sequence

from relaylm.ctx_ovl_types import _CATCH_UP_MAX_EVENTS, _REBUILD_MAX_RECORDS
from relaylm.evidence_common import PrincipalRef, dedupe


def _validate_change_partition_descriptor(
    payload: dict | None,
    *,
    evidence_space_id: str,
    change_partition_id: str,
    participant: PrincipalRef,
) -> tuple[str, ...]:
    if payload is None:
        return ("ctx_ovl_change_partition_missing",)
    reasons: list[str] = []
    if payload.get("schema") != "relaylm.evidence_change_partition_descriptor.v1":
        reasons.append("ctx_ovl_change_partition_schema_invalid")
    if payload.get("change_partition_id") != change_partition_id:
        reasons.append("ctx_ovl_change_partition_identity_mismatch")
    if payload.get("evidence_space_id") != evidence_space_id:
        reasons.append("ctx_ovl_change_partition_evidence_space_mismatch")
    if payload.get("partition_kind") != "participant":
        reasons.append("ctx_ovl_non_participant_partition_unsupported_in_ovl1")
    if payload.get("participant_ref_or_null") != participant.to_dict():
        reasons.append("ctx_ovl_change_partition_participant_mismatch")
    if payload.get("partition_status") != "open":
        reasons.append("ctx_ovl_change_partition_not_open")
    epoch_id = payload.get("partition_epoch_id")
    if not isinstance(epoch_id, str) or not epoch_id:
        reasons.append("ctx_ovl_change_partition_epoch_invalid")
    return dedupe(reasons)


def _bounded_event_slice(
    *,
    projection_events: Sequence[dict],
    coverage_events: Sequence[dict],
    change_partition_id: str,
    partition_epoch_id: str,
    last_observed: int,
    mode: str,
) -> tuple[list[dict], int, tuple[str, ...]]:
    """Return one bounded contiguous page and its resulting watermark.

    Coverage is still proven against the complete Contract-1 projection log,
    but catch-up advances in pages instead of becoming permanently blocked
    whenever the backlog exceeds the per-operation event cap.
    """

    if not coverage_events:
        if not projection_events:
            return [], last_observed, ()
        return [], last_observed, ("ctx_ovl_change_coverage_missing",)
    latest = coverage_events[-1]
    reasons: list[str] = []
    if latest.get("change_partition_id") != change_partition_id:
        reasons.append("ctx_ovl_change_coverage_partition_mismatch")
    if latest.get("partition_epoch_id") != partition_epoch_id:
        reasons.append("ctx_ovl_change_coverage_epoch_mismatch")
    if latest.get("derived_coverage_status") not in {
        "open_contiguous",
        "sealed_complete",
    }:
        reasons.append("ctx_ovl_change_coverage_incomplete")
    highest = latest.get("highest_contiguous_committed_sequence_or_null")
    if highest is None:
        if projection_events:
            reasons.append("ctx_ovl_change_coverage_highest_missing")
        return [], last_observed, dedupe(reasons)
    if type(highest) is not int or highest < -1:
        reasons.append("ctx_ovl_change_coverage_highest_invalid")
        return [], last_observed, dedupe(reasons)

    by_sequence: dict[int, dict] = {}
    for event in projection_events:
        sequence = event.get("partition_sequence")
        if type(sequence) is not int or sequence < 0:
            reasons.append("ctx_ovl_change_projection_shape_invalid")
            continue
        if (
            event.get("change_partition_id") != change_partition_id
            or event.get("partition_epoch_id") != partition_epoch_id
        ):
            reasons.append("ctx_ovl_change_projection_scope_mismatch")
            continue
        if sequence in by_sequence:
            reasons.append("ctx_ovl_change_projection_sequence_conflict")
            continue
        by_sequence[sequence] = event
    expected = list(range(0, highest + 1))
    if sorted(by_sequence) != expected:
        reasons.append("ctx_ovl_change_projection_coverage_gap")
    if reasons:
        return [], last_observed, dedupe(reasons)

    if mode == "rebuild":
        selected_sequences = expected[-_REBUILD_MAX_RECORDS:]
        resulting_watermark = highest
    else:
        pending = [seq for seq in expected if seq > last_observed]
        selected_sequences = pending[:_CATCH_UP_MAX_EVENTS]
        resulting_watermark = (
            selected_sequences[-1] if selected_sequences else last_observed
        )
    return [by_sequence[seq] for seq in selected_sequences], resulting_watermark, ()


__all__ = ["_bounded_event_slice", "_validate_change_partition_descriptor"]

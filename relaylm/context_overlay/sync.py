"""OVL-1 bounded rebuild and catch-up over the EV-1 change feed."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from relaylm.context_overlay.change_feed import (
    _bounded_event_slice,
    _validate_change_partition_descriptor,
)
from relaylm.context_overlay.evidence import _read_authorized_candidate
from relaylm.context_overlay.records import (
    _admit_candidate,
    _build_sync_event,
    _invalidate_event_sources,
    _invalidate_source,
)
from relaylm.context_overlay.selection import _prune_partition, _reflex_snapshot
from relaylm.context_overlay.types import (
    CtxOvlRuntimeResult,
    _CATCH_UP_MAX_TOTAL_BYTES,
    _MAX_CANDIDATE_BYTES,
    _ParticipantPartitionState,
    _REBUILD_MAX_RECORDS,
    _REBUILD_MAX_TOTAL_BYTES,
    _new_partition_state,
)
from relaylm.evidence.space import EvidenceSpaceDescriptor
from relaylm.evidence.store import EvidenceRecordStore

CtxOvlSyncMode = Literal["rebuild", "catch_up", "current_source"]


def _synchronize_partition(
    *,
    existing: _ParticipantPartitionState | None,
    tx_store: EvidenceRecordStore,
    descriptor: EvidenceSpaceDescriptor,
    session_id: str,
    participant_partition_id: str,
    change_partition_id: str,
    evaluated_at: datetime,
    mode: CtxOvlSyncMode,
    request_id: str,
) -> tuple[_ParticipantPartitionState | None, CtxOvlRuntimeResult]:
    try:
        with tx_store.transaction(descriptor.evidence_space_id) as tx:
            persisted_descriptor = tx.read_record(
                record_kind="evidence_space_descriptor", record_id="revision-1"
            )
            if persisted_descriptor is None:
                if existing is None:
                    state = _new_partition_state(
                        session_id=session_id,
                        participant=descriptor.controller_principal_ref,
                        participant_partition_id=participant_partition_id,
                        evidence_space_id=descriptor.evidence_space_id,
                        change_partition_id=change_partition_id,
                        contract1_partition_epoch_id="partitionepoch_pending",
                        evaluated_at=evaluated_at,
                    )
                    return state, CtxOvlRuntimeResult(
                        status="applied",
                        sync_mode=mode,
                        sync_outcome="no_governed_events",
                        reflex_snapshot=_reflex_snapshot(state, "fresh"),
                    )
                return existing, _sync_failure(mode, "ctx_ovl_evidence_space_missing")
            try:
                exact_descriptor = EvidenceSpaceDescriptor.from_dict(
                    persisted_descriptor
                )
            except (KeyError, TypeError, ValueError):
                return None, _sync_failure(mode, "ctx_ovl_evidence_space_invalid")
            if (
                exact_descriptor.evidence_space_id != descriptor.evidence_space_id
                or exact_descriptor.controller_principal_ref
                != descriptor.controller_principal_ref
                or exact_descriptor.isolation_mode != "private_conversation"
            ):
                return None, _sync_failure(mode, "ctx_ovl_evidence_space_mismatch")

            partition_descriptor = tx.read_record(
                record_kind="change_partition_descriptor",
                record_id=change_partition_id,
            )
            partition_reasons = _validate_change_partition_descriptor(
                partition_descriptor,
                evidence_space_id=descriptor.evidence_space_id,
                change_partition_id=change_partition_id,
                participant=exact_descriptor.controller_principal_ref,
            )
            if partition_reasons:
                if partition_descriptor is None and existing is None:
                    state = _new_partition_state(
                        session_id=session_id,
                        participant=exact_descriptor.controller_principal_ref,
                        participant_partition_id=participant_partition_id,
                        evidence_space_id=descriptor.evidence_space_id,
                        change_partition_id=change_partition_id,
                        contract1_partition_epoch_id="partitionepoch_pending",
                        evaluated_at=evaluated_at,
                    )
                    return state, CtxOvlRuntimeResult(
                        status="applied",
                        sync_mode=mode,
                        sync_outcome="no_governed_events",
                        reflex_snapshot=_reflex_snapshot(state, "fresh"),
                    )
                return None, CtxOvlRuntimeResult(
                    status="fail_closed",
                    blocked_reasons=partition_reasons,
                    sync_mode=mode,
                    sync_outcome="fail_closed_partition",
                )
            assert partition_descriptor is not None
            epoch_id = str(partition_descriptor["partition_epoch_id"])
            state = existing
            if state is None:
                state = _new_partition_state(
                    session_id=session_id,
                    participant=exact_descriptor.controller_principal_ref,
                    participant_partition_id=participant_partition_id,
                    evidence_space_id=descriptor.evidence_space_id,
                    change_partition_id=change_partition_id,
                    contract1_partition_epoch_id=epoch_id,
                    evaluated_at=evaluated_at,
                )
                if mode != "current_source":
                    mode = "rebuild"
            elif state.contract1_partition_epoch_id != epoch_id:
                prior_state_had_overlays = bool(state.overlays_by_source)
                state = _new_partition_state(
                    session_id=session_id,
                    participant=exact_descriptor.controller_principal_ref,
                    participant_partition_id=participant_partition_id,
                    evidence_space_id=descriptor.evidence_space_id,
                    change_partition_id=change_partition_id,
                    contract1_partition_epoch_id=epoch_id,
                    evaluated_at=evaluated_at,
                )
                if mode != "current_source" or prior_state_had_overlays:
                    mode = "rebuild"

            _prune_partition(state, evaluated_at=evaluated_at)

            projection_events = tx.read_log(
                log_kind="change_projection", key=change_partition_id
            ) or []
            coverage_events = tx.read_log(
                log_kind="change_coverage_checkpoint", key=change_partition_id
            ) or []
            event_slice, resulting_watermark, coverage_reasons = _bounded_event_slice(
                projection_events=projection_events,
                coverage_events=coverage_events,
                change_partition_id=change_partition_id,
                partition_epoch_id=epoch_id,
                last_observed=state.last_observed_partition_sequence,
                mode=mode,
            )
            if coverage_reasons:
                return state, CtxOvlRuntimeResult(
                    status="fail_closed",
                    blocked_reasons=coverage_reasons,
                    sync_mode=mode,
                    sync_outcome="fail_closed_gap",
                    reflex_snapshot=_reflex_snapshot(state, "unknown"),
                )

            admitted = 0
            omitted = 0
            total_bytes = 0
            processed_sources: set[str] = set()
            produced: list[tuple[str, str]] = []
            for event in event_slice:
                sequence = int(event["partition_sequence"])
                candidate, _candidate_reasons = _read_authorized_candidate(
                    tx,
                    event=event,
                    descriptor=exact_descriptor,
                    session_id=session_id,
                    evaluated_at=evaluated_at,
                )
                source_ids = event.get("authorized_source_event_refs")
                if isinstance(source_ids, list):
                    processed_sources.update(
                        source_id
                        for source_id in source_ids
                        if isinstance(source_id, str)
                    )
                if candidate is None:
                    omitted += 1
                    _invalidate_event_sources(
                        state,
                        event,
                        evaluated_at=evaluated_at,
                        reason="restricted",
                        new_highest_observed_sequence=resulting_watermark,
                    )
                    continue
                byte_cap = (
                    _REBUILD_MAX_TOTAL_BYTES
                    if mode == "rebuild"
                    else _CATCH_UP_MAX_TOTAL_BYTES
                )
                if candidate.actual_bytes > _MAX_CANDIDATE_BYTES:
                    omitted += 1
                    continue
                if total_bytes + candidate.actual_bytes > byte_cap:
                    omitted += 1
                    continue
                total_bytes += candidate.actual_bytes
                overlay_id = _admit_candidate(
                    state,
                    candidate,
                    partition_sequence=sequence,
                    evaluated_at=evaluated_at,
                    admission_origin=(
                        "rebuild_pipeline"
                        if mode == "rebuild"
                        else (
                            "normal_pipeline"
                            if mode == "current_source"
                            else "catch_up_pipeline"
                        )
                    ),
                )
                produced.append((overlay_id, candidate.authority_snapshot_digest))
                admitted += 1

            # Revalidate retained records even without a new event. Reauthorization
            # updates no produced-operation list; it only refreshes process-local
            # eligibility for a record already represented by its source event.
            event_by_source: dict[str, dict] = {}
            for source_event in projection_events:
                refs = source_event.get("authorized_source_event_refs")
                if isinstance(refs, list):
                    for source_id in refs:
                        if isinstance(source_id, str):
                            event_by_source[source_id] = source_event
            for source_id in list(state.overlays_by_source):
                if source_id in processed_sources:
                    continue
                item = state.overlays_by_source.get(source_id)
                if item is None or item.record.get("lifecycle_state") != "active":
                    continue
                authority_event = event_by_source.get(source_id)
                if authority_event is None:
                    _invalidate_source(
                        state,
                        source_id,
                        evaluated_at=evaluated_at,
                        reason="watermark_advanced",
                        new_highest_observed_sequence=resulting_watermark,
                    )
                    omitted += 1
                    continue
                candidate, _reauth_reasons = _read_authorized_candidate(
                    tx,
                    event=authority_event,
                    descriptor=exact_descriptor,
                    session_id=session_id,
                    evaluated_at=evaluated_at,
                )
                if candidate is None:
                    _invalidate_source(
                        state,
                        source_id,
                        evaluated_at=evaluated_at,
                        reason="restricted",
                    )
                    omitted += 1
                    continue
                _admit_candidate(
                    state,
                    candidate,
                    partition_sequence=int(authority_event["partition_sequence"]),
                    evaluated_at=evaluated_at,
                    admission_origin=str(item.record.get("admission_origin")),
                )

            state.last_observed_partition_sequence = resulting_watermark
            _prune_partition(state, evaluated_at=evaluated_at)
            state.revision += 1

            new_sync_events: list[dict[str, object]] = []
            coverage_checkpoint = coverage_events[-1] if coverage_events else None
            if mode in {"rebuild", "catch_up"}:
                if produced:
                    # Contract 1 authority snapshots are source-scoped. Emit one
                    # operation record per exact digest instead of falsely
                    # claiming that heterogeneous outputs share one authority.
                    for overlay_id, authority_digest in produced:
                        new_sync_events.append(
                            _build_sync_event(
                                state,
                                mode=mode,
                                evaluated_at=evaluated_at,
                                produced_overlay_record_ids=(overlay_id,),
                                authority_snapshot_digest=authority_digest,
                                omitted_count=omitted,
                                request_id=request_id,
                                coverage_checkpoint=coverage_checkpoint,
                            )
                        )
                else:
                    new_sync_events.append(
                        _build_sync_event(
                            state,
                            mode=mode,
                            evaluated_at=evaluated_at,
                            produced_overlay_record_ids=(),
                            authority_snapshot_digest=None,
                            omitted_count=omitted,
                            request_id=request_id,
                            coverage_checkpoint=coverage_checkpoint,
                        )
                    )
                state.sync_events.extend(new_sync_events)
                del state.sync_events[:-_REBUILD_MAX_RECORDS]
                state.last_sync_event = new_sync_events[-1]
            else:
                state.last_sync_event = None

            outcome = (
                "rebuild_applied"
                if mode == "rebuild"
                else (
                    "current_source_admitted"
                    if mode == "current_source" and admitted
                    else (
                        "bounded_catch_up_applied"
                        if admitted
                        else "no_catch_up_needed"
                    )
                )
            )
            return state, CtxOvlRuntimeResult(
                status="applied",
                sync_mode=mode,
                sync_outcome=outcome,
                admitted_count=admitted,
                omitted_count=omitted,
                reflex_snapshot=_reflex_snapshot(state, "fresh"),
            )
    except (RuntimeError, KeyError, TypeError, ValueError):
        return existing, CtxOvlRuntimeResult(
            status="fail_closed",
            blocked_reasons=("ctx_ovl_store_validation_failed",),
            sync_mode=mode,
            sync_outcome="fail_closed_store",
            reflex_snapshot=(
                _reflex_snapshot(existing, "unknown")
                if existing is not None
                else None
            ),
        )


def _sync_failure(mode: str, reason: str) -> CtxOvlRuntimeResult:
    return CtxOvlRuntimeResult(
        status="fail_closed",
        blocked_reasons=(reason,),
        sync_mode=mode,
        sync_outcome="fail_closed",
    )


__all__ = ["CtxOvlSyncMode", "_synchronize_partition"]

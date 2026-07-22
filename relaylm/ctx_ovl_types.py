"""OVL-1 bounds, process-local value objects, and writer authority."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from relaylm.evidence_common import PrincipalRef, new_opaque_id

_MAX_CANDIDATE_BYTES = 8192
_SELECTION_MAX_RECORDS = 4
_SELECTION_MAX_TOTAL_BYTES = 4096
_CATCH_UP_MAX_EVENTS = 64
_CATCH_UP_MAX_TOTAL_BYTES = 65536
_REBUILD_MAX_RECORDS = 256
_REBUILD_MAX_TOTAL_BYTES = 262144
_TTL_SECONDS = 1800


@dataclass(frozen=True)
class CtxOvlRuntimeResult:
    status: str
    blocked_reasons: tuple[str, ...] = ()
    sync_mode: str = "none"
    sync_outcome: str = "not_run"
    selected_count: int = 0
    admitted_count: int = 0
    omitted_count: int = 0
    payload_injection_applied: bool = False
    reflex_snapshot: dict[str, object] | None = None

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": "relaylm.ctx_ovl_runtime_result.v1",
            "diagnostics_only": True,
            "content_free": True,
            "status": self.status,
            "sync_mode": self.sync_mode,
            "sync_outcome": self.sync_outcome,
            "selected_count": self.selected_count,
            "admitted_count": self.admitted_count,
            "omitted_count": self.omitted_count,
            "payload_injection_applied": self.payload_injection_applied,
            "blocked_reason_ids": list(self.blocked_reasons),
            "reflex_snapshot": dict(self.reflex_snapshot or {}),
        }


@dataclass(frozen=True)
class _AuthorizedCandidate:
    source_event_id: str
    source_sequence: int
    text: str = field(repr=False)
    content_digest: str
    actual_bytes: int
    evidence_space_id: str
    change_partition_id: str
    partition_epoch_id: str
    authority_snapshot_digest: str
    validated_at: str
    not_after: str


@dataclass
class _StoredOverlay:
    artifact: dict[str, object]
    record: dict[str, object]
    text: str = field(repr=False)
    partition_sequence: int


@dataclass
class _ParticipantPartitionState:
    session_id: str
    participant_id: str
    partition_id: str
    evidence_space_id: str
    change_partition_id: str
    contract1_partition_epoch_id: str
    partition_epoch_descriptor: dict[str, object]
    overlays_by_source: dict[str, _StoredOverlay] = field(default_factory=dict)
    invalidation_events: list[dict[str, object]] = field(default_factory=list)
    write_attempts: list[dict[str, object]] = field(default_factory=list)
    sync_events: list[dict[str, object]] = field(default_factory=list)
    last_selection: dict[str, object] | None = None
    last_sync_event: dict[str, object] | None = None
    last_observed_partition_sequence: int = -1
    revision: int = 1

    def active_overlays(self) -> list[_StoredOverlay]:
        return [
            item
            for item in self.overlays_by_source.values()
            if item.record.get("lifecycle_state") == "active"
        ]


def evaluate_ctx_ovl_write_attempt(
    *,
    session_id: str,
    target_overlay_record_id_or_null: str | None,
    operation: str,
    attempted_actor_component: str,
) -> dict[str, object]:
    """Return the contract-shaped writer-authorization decision."""

    allowed_actors = {"relayctx_pipeline", "ctx_ovl_rebuild_process"}
    authorized = attempted_actor_component in allowed_actors
    return {
        "schema": "relaylm.ctx_ovl_write_attempt.v1",
        "write_attempt_id": new_opaque_id("ctxovlwrite"),
        "session_id": session_id,
        "target_overlay_record_id_or_null": target_overlay_record_id_or_null,
        "operation": operation,
        "attempted_actor_component": attempted_actor_component,
        "authorized_actor": authorized,
        "target_authority_domain": "ctx_ovl_working_state",
        "authorized": authorized,
    }


def _record_write_attempt(
    state: _ParticipantPartitionState,
    *,
    target_overlay_record_id_or_null: str | None,
    operation: str,
    actor: str,
) -> None:
    attempt = evaluate_ctx_ovl_write_attempt(
        session_id=state.session_id,
        target_overlay_record_id_or_null=target_overlay_record_id_or_null,
        operation=operation,
        attempted_actor_component=actor,
    )
    state.write_attempts.append(attempt)
    del state.write_attempts[:-_REBUILD_MAX_RECORDS]
    if not attempt["authorized"]:
        raise RuntimeError("ctx_ovl_writer_unauthorized")


def _new_partition_state(
    *,
    session_id: str,
    participant: PrincipalRef,
    participant_partition_id: str,
    evidence_space_id: str,
    change_partition_id: str,
    contract1_partition_epoch_id: str,
    evaluated_at: datetime,
) -> _ParticipantPartitionState:
    epoch_descriptor_id = new_opaque_id("ctxovlepoch")
    epoch = {
        "schema": "relaylm.ctx_ovl_partition_epoch.v1",
        "partition_epoch_descriptor_id": epoch_descriptor_id,
        "session_id": session_id,
        "partition_kind": "participant",
        "partition_id": participant_partition_id,
        "scene_epoch_id_or_null": None,
        "epoch_sequence": 1,
        "epoch_status": "active",
        "established_by_operation": "ctx_ovl_rebuild_process",
        "established_at": evaluated_at.isoformat(),
    }
    return _ParticipantPartitionState(
        session_id=session_id,
        participant_id=participant.principal_id,
        partition_id=participant_partition_id,
        evidence_space_id=evidence_space_id,
        change_partition_id=change_partition_id,
        contract1_partition_epoch_id=contract1_partition_epoch_id,
        partition_epoch_descriptor=epoch,
    )


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


__all__ = [
    "CtxOvlRuntimeResult",
    "_AuthorizedCandidate",
    "_StoredOverlay",
    "_ParticipantPartitionState",
    "_MAX_CANDIDATE_BYTES",
    "_SELECTION_MAX_RECORDS",
    "_SELECTION_MAX_TOTAL_BYTES",
    "_CATCH_UP_MAX_EVENTS",
    "_CATCH_UP_MAX_TOTAL_BYTES",
    "_REBUILD_MAX_RECORDS",
    "_REBUILD_MAX_TOTAL_BYTES",
    "_TTL_SECONDS",
    "_new_partition_state",
    "_parse_datetime",
    "_record_write_attempt",
    "evaluate_ctx_ovl_write_attempt",
]

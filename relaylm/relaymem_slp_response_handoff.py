"""Phase 6-A2 helper-only RelaySLP response-finalization handoff."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result

_SOURCE_SCHEMA = "relaymem.slp_job_admission_preflight.v0"
_SOURCE_PROJECTION_SCHEMA = "relaymem.slp_job_admission_projection.v0"
_RESULT_SCHEMA = "relaymem.slp_response_handoff.v0"
_CANDIDATE_SCHEMA = "relaymem.slp_enqueue_candidate.v0"
_PROJECTION_SCHEMA = "relaymem.slp_response_handoff_projection.v0"

_SOURCE_FIELDS = {
    "schema_version",
    "helper_only",
    "diagnostics_only",
    "read_only",
    "enabled",
    "dry_run_only",
    "enqueue_enabled",
    "admission_status",
    "trigger_mode",
    "processing_stage",
    "source_event_kind",
    "run_id",
    "turn_index",
    "session_id",
    "namespace",
    "source_count",
    "source_reference_valid",
    "source_lineage_fingerprint",
    "visible_response_finalized",
    "runtime_terminal_status",
    "persistence_policy_status",
    "retry_class",
    "blocked_reasons",
    "enqueue_eligible",
    "queue_io_performed",
    "enqueued",
    "worker_invoked",
    "invokes_slp",
    "writes_memory",
    "mutates_soul",
    "changes_visible_response",
    "dispatch_idempotency_key",
    "memory_write_idempotency_key",
    "projection",
}
_SOURCE_PROJECTION_FIELDS = {
    "schema_version",
    "diagnostics_only",
    "content_free",
    "content_included",
    "raw_text_included",
    "enabled",
    "dry_run_only",
    "enqueue_enabled",
    "admission_status",
    "trigger_mode",
    "processing_stage",
    "source_event_kind",
    "source_count",
    "source_count_limit",
    "correlation",
    "source_reference_valid",
    "visible_response_finalized",
    "runtime_terminal_status",
    "persistence_policy_status",
    "retry_class",
    "blocked_reasons",
    "runtime_private_reference_included",
    "lineage_fingerprint_included",
    "dispatch_idempotency_key_included",
    "memory_write_idempotency_key_included",
}
_SOURCE_CORRELATION_FIELDS = {
    "run_id_present",
    "turn_index_present",
    "session_id_present",
    "namespace_present",
}
_SOURCE_TOKEN_FIELDS = {
    "trigger_mode",
    "processing_stage",
    "source_event_kind",
    "runtime_terminal_status",
    "persistence_policy_status",
    "retry_class",
}
_SOURCE_STATUSES = (
    "skipped",
    "blocked",
    "held",
    "admitted_dry_run",
    "eligible_for_enqueue",
)
_ACCEPTED_SOURCE_STATUSES = ("admitted_dry_run", "eligible_for_enqueue")
_ALLOWED_STAGES = ("primary_formation", "primary_write_preflight")
_ALLOWED_RUNTIME_STATUSES = ("completed", "succeeded", "idle")
_ALLOWED_POLICY_STATUSES = ("allowed", "free_to_update")
_MAX_TOKEN = 128
_MAX_REASONS = 32
_MAX_SOURCES = 32

RelayMEMSLPResponseHandoffStatus = Literal[
    "disabled",
    "invalid_input",
    "blocked",
    "held",
    "skipped",
    "dry_run_candidate",
]


@dataclass(frozen=True)
class RelayMEMSLPEnqueueCandidate:
    """Runtime-private metadata-only candidate; no queue operation has occurred."""

    trigger_mode: str
    processing_stage: str
    source_event_kind: str
    run_id: str
    turn_index: int
    session_id: str | None
    namespace: str
    source_count: int
    source_lineage_fingerprint: str
    source_admission_status: str
    runtime_terminal_status: str
    persistence_policy_status: str

    def to_runtime_dict(self) -> dict[str, object]:
        return {
            "schema_version": _CANDIDATE_SCHEMA,
            "candidate_kind": "relayslp_deferred_job",
            "trigger_mode": self.trigger_mode,
            "processing_stage": self.processing_stage,
            "source_event_kind": self.source_event_kind,
            "run_id": self.run_id,
            "turn_index": self.turn_index,
            "session_id": self.session_id,
            "namespace": self.namespace,
            "source_count": self.source_count,
            "source_lineage_fingerprint": self.source_lineage_fingerprint,
            "source_admission_status": self.source_admission_status,
            "runtime_terminal_status": self.runtime_terminal_status,
            "persistence_policy_status": self.persistence_policy_status,
            "response_finalized": True,
            "dry_run_only": True,
            "enqueue_requested": False,
            "queue_io_performed": False,
            "enqueued": False,
            "worker_invoked": False,
            "invokes_slp": False,
            "writes_memory": False,
            "mutates_soul": False,
            "changes_visible_response": False,
            "dispatch_idempotency_key": "",
            "memory_write_idempotency_key": "",
            "content_free": True,
            "runtime_private": True,
        }


@dataclass(frozen=True)
class RelayMEMSLPSourceProjection:
    """Content-free source metadata preserved without candidate creation."""

    trigger_mode: str
    processing_stage: str
    source_event_kind: str
    source_count: int
    run_id_present: bool
    turn_index_present: bool
    session_id_present: bool
    namespace_present: bool

    def to_log_dict(self) -> dict[str, object]:
        return {
            "trigger_mode": self.trigger_mode,
            "processing_stage": self.processing_stage,
            "source_event_kind": self.source_event_kind,
            "source_count": self.source_count,
            "correlation": {
                "run_id_present": self.run_id_present,
                "turn_index_present": self.turn_index_present,
                "session_id_present": self.session_id_present,
                "namespace_present": self.namespace_present,
            },
        }


@dataclass(frozen=True)
class RelayMEMSLPResponseHandoffResult:
    status: RelayMEMSLPResponseHandoffStatus
    enabled: bool
    dry_run_only: bool
    response_finalized: bool
    source_admission_status: str | None
    source_projection: RelayMEMSLPSourceProjection | None
    candidate: RelayMEMSLPEnqueueCandidate | None
    blocked_reasons: tuple[str, ...]

    @property
    def candidate_count(self) -> int:
        return 1 if self.candidate is not None else 0

    @property
    def candidate_created(self) -> bool:
        return self.candidate is not None

    def to_runtime_dict(self) -> dict[str, object]:
        return {
            "schema_version": _RESULT_SCHEMA,
            "helper_only": True,
            "diagnostics_only": True,
            "read_only": True,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "response_finalized": self.response_finalized,
            "status": self.status,
            "source_admission_status": self.source_admission_status,
            "source_projection": (
                self.source_projection.to_log_dict()
                if self.source_projection is not None
                else None
            ),
            "candidate_count": self.candidate_count,
            "candidate_created": self.candidate_created,
            "candidate": self.candidate.to_runtime_dict() if self.candidate else None,
            "queue_io_performed": False,
            "enqueued": False,
            "worker_invoked": False,
            "invokes_slp": False,
            "writes_memory": False,
            "mutates_soul": False,
            "changes_visible_response": False,
            "blocked_reasons": list(self.blocked_reasons),
        }

    def to_log_dict(self) -> dict[str, object]:
        source = self.source_projection
        return {
            "schema_version": _PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_text_included": False,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "response_finalized": self.response_finalized,
            "status": self.status,
            "source_admission_status": self.source_admission_status,
            "candidate_count": self.candidate_count,
            "candidate_created": self.candidate_created,
            "trigger_mode": source.trigger_mode if source else None,
            "processing_stage": source.processing_stage if source else None,
            "source_event_kind": source.source_event_kind if source else None,
            "source_count": source.source_count if source else 0,
            "correlation": (
                source.to_log_dict()["correlation"]
                if source is not None
                else {
                    "run_id_present": False,
                    "turn_index_present": False,
                    "session_id_present": False,
                    "namespace_present": False,
                }
            ),
            "queue_io_performed": False,
            "enqueued": False,
            "worker_invoked": False,
            "dispatch_idempotency_key_included": False,
            "memory_write_idempotency_key_included": False,
            "source_lineage_fingerprint_included": False,
            "runtime_private_candidate_included": False,
            "blocked_reasons": list(self.blocked_reasons),
        }


def build_relaymem_slp_response_finalization_handoff(
    admission_result: object,
    *,
    enabled: bool = False,
    dry_run_only: bool = True,
    response_finalized: bool = False,
) -> RelayMEMSLPResponseHandoffResult:
    """Create one runtime-private enqueue candidate without queue I/O."""

    enabled, enabled_errors = _strict_bool(enabled, "enabled_invalid")
    dry_run_only, dry_run_errors = _strict_bool(
        dry_run_only, "dry_run_only_invalid"
    )
    response_finalized, finalization_errors = _strict_bool(
        response_finalized, "response_finalized_invalid"
    )
    input_errors = _dedupe(
        (*enabled_errors, *dry_run_errors, *finalization_errors)
    )
    if input_errors:
        return _result(
            "invalid_input",
            enabled,
            dry_run_only,
            response_finalized,
            None,
            None,
            None,
            input_errors,
        )
    if not enabled:
        return _result(
            "disabled",
            False,
            dry_run_only,
            response_finalized,
            None,
            None,
            None,
            (),
        )

    source, source_errors = _validate_source_shape(admission_result)
    if source is None:
        return _result(
            "invalid_input",
            True,
            dry_run_only,
            response_finalized,
            None,
            None,
            None,
            source_errors,
        )
    source_status = source["admission_status"]
    source_projection = _build_source_projection(source)

    gate_errors: list[str] = []
    if not dry_run_only:
        gate_errors.append("non_dry_run_not_supported")
    if not response_finalized:
        gate_errors.append("response_not_finalized")
    if gate_errors:
        return _result(
            "blocked",
            True,
            dry_run_only,
            response_finalized,
            source_status,
            source_projection,
            None,
            gate_errors,
        )

    if source_status in ("held", "skipped", "blocked"):
        reason = f"source_admission_{source_status}"
        return _result(
            source_status,
            True,
            dry_run_only,
            response_finalized,
            source_status,
            source_projection,
            None,
            (*_source_reasons(source), reason),
        )

    accepted_errors = _validate_accepted_source(source)
    if accepted_errors:
        return _result(
            "blocked",
            True,
            dry_run_only,
            response_finalized,
            source_status,
            source_projection,
            None,
            accepted_errors,
        )

    candidate = RelayMEMSLPEnqueueCandidate(
        trigger_mode=source["trigger_mode"],
        processing_stage=source["processing_stage"],
        source_event_kind=source["source_event_kind"],
        run_id=source["run_id"],
        turn_index=source["turn_index"],
        session_id=source["session_id"],
        namespace=source["namespace"],
        source_count=source["source_count"],
        source_lineage_fingerprint=source["source_lineage_fingerprint"],
        source_admission_status=source_status,
        runtime_terminal_status=source["runtime_terminal_status"],
        persistence_policy_status=source["persistence_policy_status"],
    )
    return _result(
        "dry_run_candidate",
        True,
        True,
        response_finalized,
        source_status,
        source_projection,
        candidate,
        (),
    )


def build_relaymem_slp_response_handoff_node_result(
    result: RelayMEMSLPResponseHandoffResult,
) -> PipelineNodeResult:
    """Build the content-free A2 diagnostics projection."""

    node_status = "diagnostic_only"
    if result.status == "invalid_input":
        node_status = "failed"
    elif result.status == "blocked":
        node_status = "blocked"
    elif result.status in {"disabled", "held", "skipped"}:
        node_status = "skipped"
    return build_pipeline_node_result(
        node_name="relaymem_slp_response_handoff",
        status=node_status,
        decision=result.status,
        blocked_reasons=result.blocked_reasons,
        diagnostics=result.to_log_dict(),
        artifacts=[
            {
                "artifact_name": "relaymem_slp_enqueue_candidate",
                "schema_version": _CANDIDATE_SCHEMA,
                "present": result.candidate_created,
                "content_free": True,
                "runtime_private": True,
                "candidate_omitted": True,
                "queue_io_performed": False,
                "enqueued": False,
                "dispatch_idempotency_key_included": False,
                "memory_write_idempotency_key_included": False,
            }
        ],
    )


def _validate_source_shape(
    value: object,
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    if not isinstance(value, Mapping):
        return None, ("invalid_admission_result",)
    if len(value) != len(_SOURCE_FIELDS) or set(value) != _SOURCE_FIELDS:
        return None, ("admission_result_shape_mismatch",)
    source = dict(value)
    if source.get("schema_version") != _SOURCE_SCHEMA:
        return None, ("admission_schema_mismatch",)
    for field in ("helper_only", "diagnostics_only", "read_only"):
        if source.get(field) is not True:
            return None, (f"admission_{field}_invalid",)
    for field in (
        "enabled",
        "dry_run_only",
        "enqueue_enabled",
        "source_reference_valid",
        "visible_response_finalized",
        "enqueue_eligible",
        "queue_io_performed",
        "enqueued",
        "worker_invoked",
        "invokes_slp",
        "writes_memory",
        "mutates_soul",
        "changes_visible_response",
    ):
        if type(source.get(field)) is not bool:
            return None, (f"admission_{field}_invalid",)
    status = source.get("admission_status")
    if type(status) is not str or status not in _SOURCE_STATUSES:
        return None, ("admission_status_invalid",)
    for field in _SOURCE_TOKEN_FIELDS:
        _, errors = _required_token(source.get(field), f"admission_{field}_invalid")
        if errors:
            return None, errors

    source_count = source.get("source_count")
    if type(source_count) is not int or not 0 <= source_count <= _MAX_SOURCES:
        return None, ("admission_source_count_invalid",)
    turn_index = source.get("turn_index")
    if turn_index is not None and (type(turn_index) is not int or turn_index < 0):
        return None, ("admission_turn_index_invalid",)
    for field in ("run_id", "session_id", "namespace"):
        field_value = source.get(field)
        if field_value is not None:
            _, errors = _required_token(field_value, f"admission_{field}_invalid")
            if errors:
                return None, errors
    fingerprint = source.get("source_lineage_fingerprint")
    if fingerprint != "" and not _is_sha256(fingerprint):
        return None, ("admission_source_lineage_fingerprint_invalid",)

    reason_errors = _validate_reason_list(
        source.get("blocked_reasons"), "blocked_reasons"
    )
    if reason_errors:
        return None, reason_errors
    if source.get("queue_io_performed") is not False:
        return None, ("source_queue_io_already_performed",)
    if source.get("enqueued") is not False:
        return None, ("source_already_enqueued",)
    for field in (
        "worker_invoked",
        "invokes_slp",
        "writes_memory",
        "mutates_soul",
        "changes_visible_response",
    ):
        if source.get(field) is not False:
            return None, (f"source_{field}_invalid",)
    if type(source.get("dispatch_idempotency_key")) is not str:
        return None, ("dispatch_idempotency_key_not_allowed",)
    if source.get("dispatch_idempotency_key") != "":
        return None, ("dispatch_idempotency_key_not_allowed",)
    if type(source.get("memory_write_idempotency_key")) is not str:
        return None, ("memory_write_idempotency_key_not_allowed",)
    if source.get("memory_write_idempotency_key") != "":
        return None, ("memory_write_idempotency_key_not_allowed",)

    projection_errors = _validate_source_projection(source)
    if projection_errors:
        return None, projection_errors
    return source, ()


def _validate_source_projection(source: Mapping[str, Any]) -> tuple[str, ...]:
    value = source.get("projection")
    if not isinstance(value, Mapping):
        return ("source_projection_invalid",)
    if len(value) != len(_SOURCE_PROJECTION_FIELDS) or set(value) != _SOURCE_PROJECTION_FIELDS:
        return ("source_projection_shape_mismatch",)
    projection = dict(value)
    if projection.get("schema_version") != _SOURCE_PROJECTION_SCHEMA:
        return ("source_projection_schema_mismatch",)

    expected_flags = {
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "raw_text_included": False,
        "runtime_private_reference_included": False,
        "lineage_fingerprint_included": False,
        "dispatch_idempotency_key_included": False,
        "memory_write_idempotency_key_included": False,
    }
    for field, expected in expected_flags.items():
        field_value = projection.get(field)
        if type(field_value) is not bool or field_value is not expected:
            return (f"source_projection_{field}_invalid",)
    for field in (
        "enabled",
        "dry_run_only",
        "enqueue_enabled",
        "source_reference_valid",
        "visible_response_finalized",
    ):
        if type(projection.get(field)) is not bool:
            return (f"source_projection_{field}_invalid",)
    projection_status = projection.get("admission_status")
    if type(projection_status) is not str or projection_status not in _SOURCE_STATUSES:
        return ("source_projection_admission_status_invalid",)
    for field in _SOURCE_TOKEN_FIELDS:
        _, errors = _required_token(
            projection.get(field), f"source_projection_{field}_invalid"
        )
        if errors:
            return errors

    source_count = projection.get("source_count")
    if type(source_count) is not int or not 0 <= source_count <= _MAX_SOURCES:
        return ("source_projection_source_count_invalid",)
    source_count_limit = projection.get("source_count_limit")
    if type(source_count_limit) is not int or source_count_limit != _MAX_SOURCES:
        return ("source_projection_count_limit_invalid",)
    reason_errors = _validate_reason_list(
        projection.get("blocked_reasons"), "source_projection_blocked_reasons"
    )
    if reason_errors:
        return reason_errors

    correlation_value = projection.get("correlation")
    if not isinstance(correlation_value, Mapping):
        return ("source_projection_correlation_invalid",)
    if (
        len(correlation_value) != len(_SOURCE_CORRELATION_FIELDS)
        or set(correlation_value) != _SOURCE_CORRELATION_FIELDS
    ):
        return ("source_projection_correlation_shape_mismatch",)
    correlation = dict(correlation_value)
    if any(
        type(correlation.get(field)) is not bool
        for field in _SOURCE_CORRELATION_FIELDS
    ):
        return ("source_projection_correlation_invalid",)

    for field in (
        "enabled",
        "dry_run_only",
        "enqueue_enabled",
        "admission_status",
        "trigger_mode",
        "processing_stage",
        "source_event_kind",
        "source_count",
        "source_reference_valid",
        "visible_response_finalized",
        "runtime_terminal_status",
        "persistence_policy_status",
        "retry_class",
        "blocked_reasons",
    ):
        if projection.get(field) != source.get(field):
            return (f"source_projection_mismatch:{field}",)

    expected_correlation = {
        "run_id_present": source.get("run_id") is not None,
        "turn_index_present": source.get("turn_index") is not None,
        "session_id_present": source.get("session_id") is not None,
        "namespace_present": source.get("namespace") is not None,
    }
    if correlation != expected_correlation:
        return ("source_projection_correlation_mismatch",)
    return ()


def _validate_accepted_source(source: Mapping[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    status = source["admission_status"]
    if status not in _ACCEPTED_SOURCE_STATUSES:
        errors.append("unsupported_source_admission_status")
    if source.get("enabled") is not True:
        errors.append("source_admission_disabled")
    if source.get("trigger_mode") != "turn_end":
        errors.append("trigger_not_supported_for_response_handoff")
    if source.get("processing_stage") not in _ALLOWED_STAGES:
        errors.append("processing_stage_invalid")
    if source.get("source_event_kind") != "turn":
        errors.append("source_event_kind_invalid")

    _, run_errors = _required_token(source.get("run_id"), "run_id_invalid")
    _, session_errors = _optional_token(
        source.get("session_id"), "session_id_invalid"
    )
    _, namespace_errors = _required_token(
        source.get("namespace"), "namespace_invalid"
    )
    errors.extend((*run_errors, *session_errors, *namespace_errors))

    turn_index = source.get("turn_index")
    if type(turn_index) is not int or turn_index < 0:
        errors.append("turn_index_invalid")
    source_count = source.get("source_count")
    if type(source_count) is not int or not 1 <= source_count <= _MAX_SOURCES:
        errors.append("source_count_invalid")
    if source.get("source_reference_valid") is not True:
        errors.append("source_reference_invalid")
    if not _is_sha256(source.get("source_lineage_fingerprint")):
        errors.append("source_lineage_fingerprint_invalid")
    if source.get("visible_response_finalized") is not True:
        errors.append("source_response_not_finalized")
    if source.get("runtime_terminal_status") not in _ALLOWED_RUNTIME_STATUSES:
        errors.append("runtime_terminal_status_invalid")
    if source.get("persistence_policy_status") not in _ALLOWED_POLICY_STATUSES:
        errors.append("persistence_policy_status_invalid")
    if source.get("retry_class") != "not_dispatched":
        errors.append("retry_class_invalid")
    if source.get("blocked_reasons"):
        errors.append("source_blocked_reasons_not_empty")

    if status == "admitted_dry_run":
        if (
            source.get("dry_run_only") is not True
            or source.get("enqueue_eligible") is not False
        ):
            errors.append("dry_run_source_gate_mismatch")
    elif status == "eligible_for_enqueue":
        if source.get("dry_run_only") is not False:
            errors.append("enqueue_source_dry_run_mismatch")
        if (
            source.get("enqueue_enabled") is not True
            or source.get("enqueue_eligible") is not True
        ):
            errors.append("enqueue_source_gate_mismatch")
    return _dedupe(errors)


def _build_source_projection(
    source: Mapping[str, Any],
) -> RelayMEMSLPSourceProjection:
    return RelayMEMSLPSourceProjection(
        trigger_mode=source["trigger_mode"],
        processing_stage=source["processing_stage"],
        source_event_kind=source["source_event_kind"],
        source_count=source["source_count"],
        run_id_present=source.get("run_id") is not None,
        turn_index_present=source.get("turn_index") is not None,
        session_id_present=source.get("session_id") is not None,
        namespace_present=source.get("namespace") is not None,
    )


def _source_reasons(source: Mapping[str, Any]) -> tuple[str, ...]:
    value = source.get("blocked_reasons")
    return tuple(value[:_MAX_REASONS]) if type(value) is list else ()


def _result(
    status: RelayMEMSLPResponseHandoffStatus,
    enabled: bool,
    dry_run_only: bool,
    response_finalized: bool,
    source_status: str | None,
    source_projection: RelayMEMSLPSourceProjection | None,
    candidate: RelayMEMSLPEnqueueCandidate | None,
    reasons: Sequence[str],
) -> RelayMEMSLPResponseHandoffResult:
    return RelayMEMSLPResponseHandoffResult(
        status=status,
        enabled=enabled,
        dry_run_only=dry_run_only,
        response_finalized=response_finalized,
        source_admission_status=source_status,
        source_projection=source_projection,
        candidate=candidate,
        blocked_reasons=_dedupe(reasons)[:_MAX_REASONS],
    )


def _strict_bool(value: Any, reason: str) -> tuple[bool, tuple[str, ...]]:
    return (value, ()) if type(value) is bool else (False, (reason,))


def _validate_reason_list(value: Any, prefix: str) -> tuple[str, ...]:
    if type(value) is not list:
        return (f"{prefix}_invalid",)
    if len(value) > _MAX_REASONS:
        return (f"{prefix}_limit_exceeded",)
    for reason in value:
        _, errors = _required_token(reason, f"{prefix}_item_invalid")
        if errors:
            return errors
    return ()


def _required_token(
    value: Any, reason: str
) -> tuple[str | None, tuple[str, ...]]:
    if type(value) is not str:
        return None, (reason,)
    if value != value.strip():
        return None, (reason,)
    if not value or len(value) > _MAX_TOKEN:
        return None, (reason,)
    if not all(
        char.isascii() and (char.isalnum() or char in "-_.:/")
        for char in value
    ):
        return None, (reason,)
    return value, ()


def _optional_token(
    value: Any, reason: str
) -> tuple[str | None, tuple[str, ...]]:
    return (None, ()) if value is None else _required_token(value, reason)


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return tuple(result)

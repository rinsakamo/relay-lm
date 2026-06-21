"""Phase 6-B1 helper-only RelaySLP dispatch and durable-job preflight."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.relaymem_slp_response_handoff import (
    RelayMEMSLPEnqueueCandidate,
    RelayMEMSLPResponseHandoffResult,
    RelayMEMSLPSourceProjection,
)

_RESULT_SCHEMA = "relaymem.slp_dispatch_preflight.v0"
_DURABLE_JOB_SCHEMA = "relaymem.slp_durable_job.v0"
_PROJECTION_SCHEMA = "relaymem.slp_queue_status_projection.v0"
_SOURCE_RESULT_SCHEMA = "relaymem.slp_response_handoff.v0"
_SOURCE_CANDIDATE_SCHEMA = "relaymem.slp_enqueue_candidate.v0"
_DISPATCH_KEY_VERSION = "relaymem.slp_dispatch_key.v0"
_JOB_ID_VERSION = "relaymem.slp_job_id.v0"
_DISPATCH_KEY_PREFIX = "slp-dispatch-v0:"
_JOB_ID_PREFIX = "slp-job-v0:"
_MAX_TOKEN = 128
_MAX_REASONS = 32
_MAX_SOURCES = 32
_ACCEPTED_ADMISSION_STATUSES = ("admitted_dry_run", "eligible_for_enqueue")
_ALLOWED_STAGES = ("primary_formation", "primary_write_preflight")
_ALLOWED_RUNTIME_STATUSES = ("completed", "succeeded", "idle")
_ALLOWED_POLICY_STATUSES = ("allowed", "free_to_update")

_A2_RESULT_FIELDS = {
    "schema_version", "helper_only", "diagnostics_only", "read_only", "enabled",
    "dry_run_only", "response_finalized", "status", "source_admission_status",
    "source_projection", "candidate_count", "candidate_created", "candidate",
    "queue_io_performed", "enqueued", "worker_invoked", "invokes_slp",
    "writes_memory", "mutates_soul", "changes_visible_response", "blocked_reasons",
}
_A2_SOURCE_PROJECTION_FIELDS = {
    "trigger_mode",
    "processing_stage",
    "source_event_kind",
    "source_count",
    "correlation",
}
_A2_SOURCE_CORRELATION_FIELDS = {
    "run_id_present",
    "turn_index_present",
    "session_id_present",
    "namespace_present",
}
_A2_CANDIDATE_FIELDS = {
    "schema_version", "candidate_kind", "trigger_mode", "processing_stage",
    "source_event_kind", "run_id", "turn_index", "session_id", "namespace",
    "source_count", "source_lineage_fingerprint", "source_admission_status",
    "runtime_terminal_status", "persistence_policy_status", "response_finalized",
    "dry_run_only", "enqueue_requested", "queue_io_performed", "enqueued",
    "worker_invoked", "invokes_slp", "writes_memory", "mutates_soul",
    "changes_visible_response", "dispatch_idempotency_key",
    "memory_write_idempotency_key", "content_free", "runtime_private",
}

RelayMEMSLPDispatchPreflightStatus = Literal[
    "disabled", "invalid_input", "blocked", "dry_run_ready"
]


@dataclass(frozen=True)
class RelayMEMSLPDurableJobCandidate:
    """Runtime-private B1 durable-job candidate. No queue I/O has occurred."""

    job_id: str
    dispatch_idempotency_key: str
    candidate_schema_version: str
    candidate_kind: str
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
            "schema_version": _DURABLE_JOB_SCHEMA,
            "job_id": self.job_id,
            "dispatch_idempotency_key": self.dispatch_idempotency_key,
            "dispatch_key_version": _DISPATCH_KEY_VERSION,
            "candidate_schema_version": self.candidate_schema_version,
            "candidate_kind": self.candidate_kind,
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
            "state": "queued",
            "record_revision": 0,
            "created_at": None,
            "updated_at": None,
            "attempt_count": 0,
            "claim_generation": 0,
            "claim_owner": "",
            "lease_token": "",
            "lease_acquired_at": None,
            "lease_expires_at": None,
            "retry_class": "unclassified",
            "retry_not_before": None,
            "failure_class": "none",
            "terminal_reason_id": "",
        }


@dataclass(frozen=True)
class RelayMEMSLPDispatchPreflightResult:
    status: RelayMEMSLPDispatchPreflightStatus
    enabled: bool
    dry_run_only: bool
    source_candidate_valid: bool
    response_finalized: bool
    durable_job: RelayMEMSLPDurableJobCandidate | None
    blocked_reasons: tuple[str, ...]

    @property
    def durable_job_count(self) -> int:
        return int(self.durable_job is not None)

    @property
    def durable_job_created(self) -> bool:
        return self.durable_job is not None

    def to_runtime_dict(self) -> dict[str, object]:
        return {
            "schema_version": _RESULT_SCHEMA,
            "helper_only": True,
            "diagnostics_only": True,
            "read_only": True,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "status": self.status,
            "source_candidate_valid": self.source_candidate_valid,
            "response_finalized": self.response_finalized,
            "durable_job_count": self.durable_job_count,
            "durable_job_created": self.durable_job_created,
            "durable_job": self.durable_job.to_runtime_dict() if self.durable_job else None,
            "queue_io_performed": False,
            "enqueue_attempted": False,
            "enqueue_applied": False,
            "duplicate_detected": False,
            "worker_invoked": False,
            "invokes_slp": False,
            "writes_memory": False,
            "mutates_soul": False,
            "changes_visible_response": False,
            "blocked_reasons": list(self.blocked_reasons),
        }

    def to_log_dict(self) -> dict[str, object]:
        job = self.durable_job
        return {
            "schema_version": _PROJECTION_SCHEMA,
            "status": self.status,
            "state": "queued" if job else None,
            "trigger_mode": job.trigger_mode if job else None,
            "processing_stage": job.processing_stage if job else None,
            "source_event_kind": job.source_event_kind if job else None,
            "source_count": job.source_count if job else 0,
            "attempt_count": 0,
            "retry_class": "unclassified" if job else None,
            "response_finalized": self.response_finalized,
            "enqueue_attempted": False,
            "enqueue_applied": False,
            "duplicate_detected": False,
            "claim_active": False,
            "lease_present": False,
            "terminal": False,
            "failure_class": "none",
            "blocked_reason_ids": list(self.blocked_reasons),
        }


def build_relaymem_slp_dispatch_preflight(
    handoff_result: object,
    *,
    enabled: bool = False,
    dry_run_only: bool = True,
) -> RelayMEMSLPDispatchPreflightResult:
    """Derive a deterministic dispatch identity and dry-run job candidate."""

    enabled, enabled_errors = _strict_bool(enabled, "enabled_invalid")
    dry_run_only, dry_run_errors = _strict_bool(dry_run_only, "dry_run_only_invalid")
    gate_errors = _dedupe((*enabled_errors, *dry_run_errors))
    if gate_errors:
        return _result("invalid_input", enabled, dry_run_only, False, False, None, gate_errors)
    if not enabled:
        return _result("disabled", False, dry_run_only, False, False, None, ())
    if not dry_run_only:
        return _result(
            "blocked", True, False, False, False, None,
            ("non_dry_run_not_supported",),
        )

    source, source_errors = _validate_handoff_result(handoff_result)
    if source is None:
        return _result("invalid_input", True, True, False, False, None, source_errors)

    candidate, candidate_errors = _validate_candidate(source.candidate)
    if candidate is None:
        return _result(
            "blocked", True, True, False, source.response_finalized, None,
            candidate_errors,
        )

    consistency_errors = _validate_source_candidate_consistency(source, candidate)
    if consistency_errors:
        return _result(
            "blocked", True, True, False, source.response_finalized, None,
            consistency_errors,
        )

    candidate_dict = candidate.to_runtime_dict()
    dispatch_key = _derive_dispatch_key(candidate_dict)
    job = RelayMEMSLPDurableJobCandidate(
        job_id=_derive_job_id(dispatch_key),
        dispatch_idempotency_key=dispatch_key,
        candidate_schema_version=str(candidate_dict["schema_version"]),
        candidate_kind=str(candidate_dict["candidate_kind"]),
        trigger_mode=candidate.trigger_mode,
        processing_stage=candidate.processing_stage,
        source_event_kind=candidate.source_event_kind,
        run_id=candidate.run_id,
        turn_index=candidate.turn_index,
        session_id=candidate.session_id,
        namespace=candidate.namespace,
        source_count=candidate.source_count,
        source_lineage_fingerprint=candidate.source_lineage_fingerprint,
        source_admission_status=candidate.source_admission_status,
        runtime_terminal_status=candidate.runtime_terminal_status,
        persistence_policy_status=candidate.persistence_policy_status,
    )
    return _result("dry_run_ready", True, True, True, True, job, ())


def build_relaymem_slp_dispatch_preflight_node_result(
    result: RelayMEMSLPDispatchPreflightResult,
) -> PipelineNodeResult:
    """Build the content-free B1 diagnostics projection."""

    status = {
        "invalid_input": "failed",
        "blocked": "blocked",
        "disabled": "skipped",
    }.get(result.status, "diagnostic_only")
    return build_pipeline_node_result(
        node_name="relaymem_slp_dispatch_preflight",
        status=status,
        decision=result.status,
        blocked_reasons=result.blocked_reasons,
        diagnostics=result.to_log_dict(),
        artifacts=[{
            "artifact_name": "relaymem_slp_durable_job_candidate",
            "schema_version": _DURABLE_JOB_SCHEMA,
            "present": result.durable_job_created,
            "content_free": True,
            "runtime_private": True,
            "candidate_omitted": True,
            "dispatch_idempotency_key_included": False,
            "job_id_included": False,
            "queue_io_performed": False,
            "enqueue_attempted": False,
            "enqueue_applied": False,
            "worker_invoked": False,
            "writes_memory": False,
        }],
    )


def _validate_handoff_result(
    value: object,
) -> tuple[RelayMEMSLPResponseHandoffResult | None, tuple[str, ...]]:
    if type(value) is not RelayMEMSLPResponseHandoffResult:
        return None, ("exact_a2_handoff_result_required",)
    source = value
    if type(source.candidate) is not RelayMEMSLPEnqueueCandidate:
        return None, ("exact_a2_enqueue_candidate_required",)
    if type(source.source_projection) is not RelayMEMSLPSourceProjection:
        return None, ("exact_a2_source_projection_required",)
    if type(source.blocked_reasons) is not tuple:
        return None, ("a2_blocked_reasons_invalid",)
    try:
        runtime = source.to_runtime_dict()
        source_projection = source.source_projection.to_log_dict()
        candidate_runtime = source.candidate.to_runtime_dict()
    except (AttributeError, KeyError, TypeError, ValueError):
        return None, ("a2_handoff_runtime_shape_invalid",)
    if not isinstance(runtime, Mapping):
        return None, ("a2_handoff_runtime_shape_invalid",)
    if len(runtime) != len(_A2_RESULT_FIELDS) or set(runtime) != _A2_RESULT_FIELDS:
        return None, ("a2_handoff_runtime_shape_mismatch",)
    if runtime.get("schema_version") != _SOURCE_RESULT_SCHEMA:
        return None, ("a2_handoff_schema_mismatch",)
    projection_errors = _validate_source_projection_runtime(
        source.source_projection,
        source_projection,
    )
    if projection_errors:
        return None, projection_errors
    for field in ("helper_only", "diagnostics_only", "read_only"):
        if runtime.get(field) is not True:
            return None, (f"a2_handoff_{field}_invalid",)
    for field in (
        "queue_io_performed", "enqueued", "worker_invoked", "invokes_slp",
        "writes_memory", "mutates_soul", "changes_visible_response",
    ):
        if runtime.get(field) is not False:
            return None, (f"a2_handoff_{field}_invalid",)
    if source.status != "dry_run_candidate" or runtime.get("status") != source.status:
        return None, ("a2_handoff_status_not_eligible",)
    if source.enabled is not True or runtime.get("enabled") is not True:
        return None, ("a2_handoff_disabled",)
    if source.dry_run_only is not True or runtime.get("dry_run_only") is not True:
        return None, ("a2_handoff_not_dry_run",)
    if source.response_finalized is not True or runtime.get("response_finalized") is not True:
        return None, ("a2_response_not_finalized",)
    if source.source_admission_status not in _ACCEPTED_ADMISSION_STATUSES:
        return None, ("a2_source_admission_status_invalid",)
    if runtime.get("source_admission_status") != source.source_admission_status:
        return None, ("a2_source_admission_status_mismatch",)
    if source.blocked_reasons or runtime.get("blocked_reasons") != []:
        return None, ("a2_blocked_reasons_not_empty",)
    if source.candidate_count != 1 or source.candidate_created is not True:
        return None, ("a2_candidate_cardinality_invalid",)
    if (
        type(runtime.get("candidate_count")) is not int
        or runtime.get("candidate_count") != 1
        or runtime.get("candidate_created") is not True
    ):
        return None, ("a2_runtime_candidate_cardinality_invalid",)
    if runtime.get("source_projection") != source_projection:
        return None, ("a2_source_projection_mismatch",)
    if runtime.get("candidate") != candidate_runtime:
        return None, ("a2_candidate_runtime_mismatch",)
    return source, ()


def _validate_source_projection_runtime(
    projection: RelayMEMSLPSourceProjection,
    runtime: object,
) -> tuple[str, ...]:
    if not isinstance(runtime, Mapping):
        return ("a2_source_projection_shape_invalid",)
    if (
        len(runtime) != len(_A2_SOURCE_PROJECTION_FIELDS)
        or set(runtime) != _A2_SOURCE_PROJECTION_FIELDS
    ):
        return ("a2_source_projection_shape_mismatch",)

    correlation = runtime.get("correlation")
    if not isinstance(correlation, Mapping):
        return ("a2_source_projection_correlation_invalid",)
    if (
        len(correlation) != len(_A2_SOURCE_CORRELATION_FIELDS)
        or set(correlation) != _A2_SOURCE_CORRELATION_FIELDS
    ):
        return ("a2_source_projection_correlation_shape_mismatch",)

    for field in ("trigger_mode", "processing_stage", "source_event_kind"):
        attribute = getattr(projection, field)
        runtime_value = runtime.get(field)
        if type(attribute) is not str or type(runtime_value) is not str:
            return ("a2_source_projection_enum_invalid",)
        if runtime_value != attribute:
            return (f"a2_source_projection_{field}_mismatch",)

    if (
        type(projection.source_count) is not int
        or not 1 <= projection.source_count <= _MAX_SOURCES
        or type(runtime.get("source_count")) is not int
        or runtime.get("source_count") != projection.source_count
    ):
        return ("a2_source_projection_source_count_invalid",)

    for field in _A2_SOURCE_CORRELATION_FIELDS:
        attribute = getattr(projection, field)
        runtime_value = correlation.get(field)
        if type(attribute) is not bool or type(runtime_value) is not bool:
            return ("a2_source_projection_presence_invalid",)
        if runtime_value is not attribute:
            return (f"a2_source_projection_{field}_mismatch",)
    return ()


def _validate_source_candidate_consistency(
    source: RelayMEMSLPResponseHandoffResult,
    candidate: RelayMEMSLPEnqueueCandidate,
) -> tuple[str, ...]:
    projection = source.source_projection
    if type(projection) is not RelayMEMSLPSourceProjection:
        return ("exact_a2_source_projection_required",)
    if (
        type(projection.trigger_mode) is not str
        or type(projection.processing_stage) is not str
        or type(projection.source_event_kind) is not str
    ):
        return ("a2_source_projection_enum_invalid",)
    if (
        type(projection.source_count) is not int
        or not 1 <= projection.source_count <= _MAX_SOURCES
    ):
        return ("a2_source_projection_source_count_invalid",)
    if any(
        type(value) is not bool
        for value in (
            projection.run_id_present,
            projection.turn_index_present,
            projection.session_id_present,
            projection.namespace_present,
        )
    ):
        return ("a2_source_projection_presence_invalid",)
    reasons: list[str] = []
    if not (
        projection.trigger_mode == candidate.trigger_mode
        and projection.processing_stage == candidate.processing_stage
        and projection.source_event_kind == candidate.source_event_kind
        and projection.source_count == candidate.source_count
        and projection.run_id_present is True
        and projection.turn_index_present is True
        and projection.session_id_present is (candidate.session_id is not None)
        and projection.namespace_present is True
    ):
        reasons.append("a2_candidate_source_projection_mismatch")
    if source.source_admission_status != candidate.source_admission_status:
        reasons.append("a2_candidate_admission_status_mismatch")
    return _dedupe(reasons)


def _validate_candidate(
    value: object,
) -> tuple[RelayMEMSLPEnqueueCandidate | None, tuple[str, ...]]:
    if type(value) is not RelayMEMSLPEnqueueCandidate:
        return None, ("exact_a2_enqueue_candidate_required",)
    candidate = value
    try:
        runtime = candidate.to_runtime_dict()
    except (AttributeError, KeyError, TypeError, ValueError):
        return None, ("a2_candidate_runtime_shape_invalid",)
    if not isinstance(runtime, Mapping):
        return None, ("a2_candidate_runtime_shape_invalid",)
    if len(runtime) != len(_A2_CANDIDATE_FIELDS) or set(runtime) != _A2_CANDIDATE_FIELDS:
        return None, ("a2_candidate_shape_mismatch",)
    if runtime.get("schema_version") != _SOURCE_CANDIDATE_SCHEMA:
        return None, ("a2_candidate_schema_mismatch",)
    if runtime.get("candidate_kind") != "relayslp_deferred_job":
        return None, ("a2_candidate_kind_invalid",)
    if candidate.trigger_mode != "turn_end":
        return None, ("a2_trigger_mode_invalid",)
    if candidate.processing_stage not in _ALLOWED_STAGES:
        return None, ("a2_processing_stage_invalid",)
    if candidate.source_event_kind != "turn":
        return None, ("a2_source_event_kind_invalid",)
    for field, field_value in (
        ("run_id", candidate.run_id),
        ("namespace", candidate.namespace),
        ("source_admission_status", candidate.source_admission_status),
        ("runtime_terminal_status", candidate.runtime_terminal_status),
        ("persistence_policy_status", candidate.persistence_policy_status),
    ):
        if not _is_token(field_value):
            return None, (f"a2_{field}_invalid",)
    if candidate.session_id is not None and not _is_token(candidate.session_id):
        return None, ("a2_session_id_invalid",)
    if type(candidate.turn_index) is not int or candidate.turn_index < 0:
        return None, ("a2_turn_index_invalid",)
    if type(candidate.source_count) is not int or not 1 <= candidate.source_count <= _MAX_SOURCES:
        return None, ("a2_source_count_invalid",)
    if type(runtime.get("turn_index")) is not int or runtime.get("turn_index") < 0:
        return None, ("a2_candidate_runtime_turn_index_invalid",)
    if (
        type(runtime.get("source_count")) is not int
        or not 1 <= runtime.get("source_count") <= _MAX_SOURCES
    ):
        return None, ("a2_candidate_runtime_source_count_invalid",)
    if not _is_sha256(candidate.source_lineage_fingerprint):
        return None, ("a2_source_lineage_fingerprint_invalid",)
    if candidate.source_admission_status not in _ACCEPTED_ADMISSION_STATUSES:
        return None, ("a2_source_admission_status_invalid",)
    if candidate.runtime_terminal_status not in _ALLOWED_RUNTIME_STATUSES:
        return None, ("a2_runtime_terminal_status_invalid",)
    if candidate.persistence_policy_status not in _ALLOWED_POLICY_STATUSES:
        return None, ("a2_persistence_policy_status_invalid",)
    expected_flags = {
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
        "content_free": True,
        "runtime_private": True,
    }
    for field, expected in expected_flags.items():
        if type(runtime.get(field)) is not bool or runtime.get(field) is not expected:
            return None, (f"a2_candidate_{field}_invalid",)
    for field in ("dispatch_idempotency_key", "memory_write_idempotency_key"):
        if type(runtime.get(field)) is not str or runtime.get(field) != "":
            return None, (f"a2_candidate_{field}_not_empty",)
    for field in (
        "trigger_mode", "processing_stage", "source_event_kind", "run_id",
        "turn_index", "session_id", "namespace", "source_count",
        "source_lineage_fingerprint", "source_admission_status",
        "runtime_terminal_status", "persistence_policy_status",
    ):
        runtime_value = runtime.get(field)
        attribute = getattr(candidate, field)
        if type(runtime_value) is not type(attribute) or runtime_value != attribute:
            return None, (f"a2_candidate_{field}_mismatch",)
    return candidate, ()


def _derive_dispatch_key(candidate: Mapping[str, Any]) -> str:
    session_id = candidate["session_id"]
    canonical_input = [
        ["dispatch_key_version", _DISPATCH_KEY_VERSION],
        ["candidate_schema_version", candidate["schema_version"]],
        ["candidate_kind", candidate["candidate_kind"]],
        ["trigger_mode", candidate["trigger_mode"]],
        ["processing_stage", candidate["processing_stage"]],
        ["source_event_kind", candidate["source_event_kind"]],
        ["run_id", candidate["run_id"]],
        ["turn_index", candidate["turn_index"]],
        ["session_id_present", session_id is not None],
        ["session_id", session_id if session_id is not None else ""],
        ["namespace", candidate["namespace"]],
        ["source_count", candidate["source_count"]],
        ["source_lineage_fingerprint", candidate["source_lineage_fingerprint"]],
    ]
    encoded = json.dumps(
        canonical_input, ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    return _DISPATCH_KEY_PREFIX + hashlib.sha256(encoded).hexdigest()


def _derive_job_id(dispatch_key: str) -> str:
    encoded = (_JOB_ID_VERSION + "\0" + dispatch_key).encode("utf-8")
    return _JOB_ID_PREFIX + hashlib.sha256(encoded).hexdigest()


def _result(
    status: RelayMEMSLPDispatchPreflightStatus,
    enabled: bool,
    dry_run_only: bool,
    source_candidate_valid: bool,
    response_finalized: bool,
    durable_job: RelayMEMSLPDurableJobCandidate | None,
    reasons: Sequence[str],
) -> RelayMEMSLPDispatchPreflightResult:
    return RelayMEMSLPDispatchPreflightResult(
        status=status,
        enabled=enabled,
        dry_run_only=dry_run_only,
        source_candidate_valid=source_candidate_valid,
        response_finalized=response_finalized,
        durable_job=durable_job,
        blocked_reasons=_dedupe(reasons)[:_MAX_REASONS],
    )


def _strict_bool(value: Any, reason: str) -> tuple[bool, tuple[str, ...]]:
    return (value, ()) if type(value) is bool else (False, (reason,))


def _is_token(value: Any) -> bool:
    return (
        type(value) is str
        and value == value.strip()
        and 0 < len(value) <= _MAX_TOKEN
        and all(char.isascii() and (char.isalnum() or char in "-_.:/") for char in value)
    )


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

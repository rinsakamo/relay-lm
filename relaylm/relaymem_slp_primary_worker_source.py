"""Phase 6-C1-0 protected Primary MEM worker-source bundle.

This boundary converts one exact content-bearing runtime-private payload into an
immutable request-local source object.  The object is never reconstructed from
queue metadata and its public projection is content-free.  No queue I/O,
worker execution, or RelayMEM write occurs here.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.relaymem_slp_queue_record import (
    DISPATCH_KEY_PREFIX,
    DURABLE_JOB_SCHEMA,
    JOB_ID_PREFIX,
    dedupe,
    derive_job_id,
    has_prefixed_digest,
    is_sha256,
    is_token,
    strict_bool,
    validate_record_mapping,
)

SOURCE_SCHEMA = "relaymem.slp_primary_worker_source.v0"
PROJECTION_SCHEMA = "relaymem.slp_primary_worker_source_projection.v0"
RESULT_SCHEMA = "relaymem.slp_primary_worker_source_build.v0"
GOVERNED_EXPERIENCE_SCHEMA = "relaymem.governed_experience_summary.v0"

SOURCE_FIELDS = frozenset({
    "schema_version",
    "runtime_private",
    "content_included",
    "job_id",
    "dispatch_idempotency_key",
    "run_id",
    "turn_index",
    "session_id",
    "namespace",
    "source_event_kind",
    "source_count",
    "source_lineage_fingerprint",
    "relayscn_scene_policy_artifact",
    "relayemo_artifact",
    "governed_messages",
    "governed_experience_artifact",
})
MESSAGE_FIELDS = frozenset({"role", "content"})
EXPERIENCE_FIELDS = frozenset({
    "schema_version",
    "runtime_private",
    "content_included",
    "raw_source_text_included",
    "raw_message_history_included",
    "raw_affect_estimates_included",
    "summary_origin",
    "candidate_id",
    "source_event_kind",
    "namespace",
    "title",
    "summary_text",
    "summary_chars",
    "valid",
    "blocked_reasons",
})
ALLOWED_MESSAGE_ROLES = frozenset({"system", "developer", "user", "assistant"})
ALLOWED_EVENT_KINDS = frozenset({"turn", "session", "communication", "manual_import"})
MAX_MESSAGES = 32
MAX_SOURCES = 32
MAX_MESSAGE_CHARS = 32_768
MAX_TOTAL_MESSAGE_CHARS = 128 * 1024
MAX_TITLE_CHARS = 160
MAX_SUMMARY_CHARS = 2_048
MAX_JSON_DEPTH = 12
MAX_JSON_NODES = 4_096

BuildStatus = Literal["disabled", "invalid_input", "blocked", "dry_run_ready", "ready"]


@dataclass(frozen=True)
class RelayMEMSLPGovernedMessage:
    """Immutable governed message retained only in the protected source object."""

    role: str
    content: str = field(repr=False)

    def to_protected_runtime_dict(self) -> dict[str, object]:
        return {"role": self.role, "content": self.content}


class RelayMEMSLPPrimaryWorkerSourceScope:
    """One request-local owner for protected worker sources.

    A source is valid only while its exact scope is active.  Consumption is
    one-shot within that scope.  Closing the scope makes all retained sources
    stale without publishing a reusable identifier.
    """

    __slots__ = ("_token", "_active", "_consumed")

    def __init__(self) -> None:
        self._token = object()
        self._active = True
        self._consumed: set[object] = set()

    @property
    def active(self) -> bool:
        return self._active

    def close(self) -> None:
        self._active = False
        self._consumed.clear()

    def _owns(self, source: "RelayMEMSLPPrimaryWorkerSource") -> bool:
        return self._active and source._request_scope_token is self._token

    def _is_consumed(self, source: "RelayMEMSLPPrimaryWorkerSource") -> bool:
        return source._source_nonce in self._consumed

    def _consume(self, source: "RelayMEMSLPPrimaryWorkerSource") -> bool:
        if not self._owns(source) or self._is_consumed(source):
            return False
        self._consumed.add(source._source_nonce)
        return True


@dataclass(frozen=True, repr=False)
class RelayMEMSLPPrimaryWorkerSource:
    """Exact immutable runtime-private content-bearing C1-0 source bundle."""

    schema_version: str
    runtime_private: bool
    content_included: bool
    job_id: str
    dispatch_idempotency_key: str
    run_id: str
    turn_index: int
    session_id: str | None
    namespace: str
    source_event_kind: str
    source_count: int
    source_lineage_fingerprint: str
    relayscn_scene_policy_artifact: Mapping[str, object] = field(repr=False)
    relayemo_artifact: Mapping[str, object] | None = field(repr=False)
    governed_messages: tuple[RelayMEMSLPGovernedMessage, ...] = field(repr=False)
    governed_experience_artifact: Mapping[str, object] = field(repr=False)
    _request_scope_token: object = field(repr=False, compare=False)
    _source_nonce: object = field(repr=False, compare=False)

    def to_protected_runtime_dict(self) -> dict[str, object]:
        """Return the exact protected payload; never use this as a log projection."""

        return {
            "schema_version": self.schema_version,
            "runtime_private": self.runtime_private,
            "content_included": self.content_included,
            "job_id": self.job_id,
            "dispatch_idempotency_key": self.dispatch_idempotency_key,
            "run_id": self.run_id,
            "turn_index": self.turn_index,
            "session_id": self.session_id,
            "namespace": self.namespace,
            "source_event_kind": self.source_event_kind,
            "source_count": self.source_count,
            "source_lineage_fingerprint": self.source_lineage_fingerprint,
            "relayscn_scene_policy_artifact": _thaw_json(
                self.relayscn_scene_policy_artifact
            ),
            "relayemo_artifact": (
                _thaw_json(self.relayemo_artifact)
                if self.relayemo_artifact is not None
                else None
            ),
            "governed_messages": [
                message.to_protected_runtime_dict() for message in self.governed_messages
            ],
            "governed_experience_artifact": _thaw_json(
                self.governed_experience_artifact
            ),
        }


@dataclass(frozen=True)
class RelayMEMSLPPrimaryWorkerSourceProjection:
    """Content-free projection safe for generic trace and public diagnostics."""

    status: BuildStatus
    enabled: bool
    dry_run_only: bool
    source_bundle_present: bool
    source_correlation_valid: bool
    message_count: int
    governed_experience_present: bool
    scene_policy_present: bool
    relayemo_present: bool
    blocked_reason_ids: tuple[str, ...]

    def to_log_dict(self) -> dict[str, object]:
        return {
            "schema_version": PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_text_included": False,
            "raw_messages_included": False,
            "governed_title_included": False,
            "governed_summary_included": False,
            "memory_body_included": False,
            "path_included": False,
            "hash_included": False,
            "identifier_values_included": False,
            "idempotency_key_included": False,
            "lease_token_included": False,
            "exception_text_included": False,
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "source_bundle_present": self.source_bundle_present,
            "source_correlation_valid": self.source_correlation_valid,
            "message_count": self.message_count,
            "governed_experience_present": self.governed_experience_present,
            "scene_policy_present": self.scene_policy_present,
            "relayemo_present": self.relayemo_present,
            "queue_io_performed": False,
            "worker_invoked": False,
            "invokes_slp": False,
            "writes_memory": False,
            "mutates_soul": False,
            "changes_visible_response": False,
            "blocked_reason_ids": list(self.blocked_reason_ids),
        }


@dataclass(frozen=True)
class RelayMEMSLPPrimaryWorkerSourceBuildResult:
    """C1-0 result carrying the protected object separately from its projection."""

    status: BuildStatus
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    source: RelayMEMSLPPrimaryWorkerSource | None = field(repr=False)
    source_correlation_valid: bool
    blocked_reasons: tuple[str, ...]

    def to_runtime_dict(self) -> dict[str, object]:
        """Return only content-free status; protected source stays on ``source``."""

        projection = project_relaymem_slp_primary_worker_source(self)
        return {
            "schema_version": RESULT_SCHEMA,
            "runtime_private_source": True,
            "source_bundle_omitted": True,
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "source_created": self.source is not None,
            "source_correlation_valid": self.source_correlation_valid,
            "queue_io_performed": False,
            "worker_invoked": False,
            "invokes_slp": False,
            "writes_memory": False,
            "mutates_soul": False,
            "changes_visible_response": False,
            "blocked_reasons": list(self.blocked_reasons),
            "projection": projection.to_log_dict(),
        }

    def to_log_dict(self) -> dict[str, object]:
        return project_relaymem_slp_primary_worker_source(self).to_log_dict()


def build_relaymem_slp_primary_worker_source(
    source_payload: object,
    *,
    claimed_record: object,
    request_scope: object,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> RelayMEMSLPPrimaryWorkerSourceBuildResult:
    """Build one exact protected source without queue I/O or worker execution."""

    enabled_value, enabled_errors = strict_bool(enabled, "enabled_invalid")
    dry_run_value, dry_run_errors = strict_bool(
        dry_run_only, "dry_run_only_invalid"
    )
    apply_value, apply_errors = strict_bool(apply_enabled, "apply_enabled_invalid")
    gate_errors = dedupe((*enabled_errors, *dry_run_errors, *apply_errors))
    if gate_errors:
        return _result(
            "invalid_input", enabled_value, dry_run_value, apply_value,
            None, False, gate_errors,
        )
    if not enabled_value:
        return _result("disabled", False, dry_run_value, apply_value, None, False, ())
    if type(request_scope) is not RelayMEMSLPPrimaryWorkerSourceScope:
        return _result(
            "invalid_input", True, dry_run_value, apply_value,
            None, False, ("exact_request_scope_required",),
        )
    if not request_scope.active:
        return _result(
            "blocked", True, dry_run_value, apply_value,
            None, False, ("request_scope_stale",),
        )
    if not dry_run_value and not apply_value:
        return _result(
            "blocked", True, False, False, None, False,
            ("apply_gate_incomplete",),
        )

    parsed, payload_errors = _parse_source_payload(source_payload)
    if parsed is None:
        return _result(
            "invalid_input", True, dry_run_value, apply_value,
            None, False, payload_errors,
        )
    record, record_errors = _validate_claimed_record(claimed_record)
    if record is None:
        return _result(
            "invalid_input", True, dry_run_value, apply_value,
            None, False, record_errors,
        )
    correlation_errors = _correlation_errors(parsed, record)
    if correlation_errors:
        return _result(
            "blocked", True, dry_run_value, apply_value,
            None, False, correlation_errors,
        )

    source = RelayMEMSLPPrimaryWorkerSource(
        schema_version=SOURCE_SCHEMA,
        runtime_private=True,
        content_included=True,
        job_id=parsed["job_id"],
        dispatch_idempotency_key=parsed["dispatch_idempotency_key"],
        run_id=parsed["run_id"],
        turn_index=parsed["turn_index"],
        session_id=parsed["session_id"],
        namespace=parsed["namespace"],
        source_event_kind=parsed["source_event_kind"],
        source_count=parsed["source_count"],
        source_lineage_fingerprint=parsed["source_lineage_fingerprint"],
        relayscn_scene_policy_artifact=parsed["relayscn_scene_policy_artifact"],
        relayemo_artifact=parsed["relayemo_artifact"],
        governed_messages=parsed["governed_messages"],
        governed_experience_artifact=parsed["governed_experience_artifact"],
        _request_scope_token=request_scope._token,
        _source_nonce=object(),
    )
    status: BuildStatus = "dry_run_ready" if dry_run_value else "ready"
    return _result(status, True, dry_run_value, apply_value, source, True, ())


def validate_relaymem_slp_primary_worker_source(
    source: object,
    *,
    claimed_record: object,
    request_scope: object,
) -> tuple[RelayMEMSLPPrimaryWorkerSource | None, tuple[str, ...]]:
    """Validate exact type, scope lifetime, consumption state, and correlation."""

    if type(source) is not RelayMEMSLPPrimaryWorkerSource:
        return None, ("exact_worker_source_required",)
    if type(request_scope) is not RelayMEMSLPPrimaryWorkerSourceScope:
        return None, ("exact_request_scope_required",)
    if not request_scope.active:
        return None, ("request_scope_stale",)
    if not request_scope._owns(source):
        return None, ("cross_request_source_rejected",)
    if request_scope._is_consumed(source):
        return None, ("worker_source_already_consumed",)

    typed_errors = _validate_typed_source(source)
    if typed_errors:
        return None, typed_errors
    record, record_errors = _validate_claimed_record(claimed_record)
    if record is None:
        return None, record_errors
    correlation_errors = _correlation_errors(source.to_protected_runtime_dict(), record)
    if correlation_errors:
        return None, correlation_errors
    return source, ()


def consume_relaymem_slp_primary_worker_source(
    source: object,
    *,
    claimed_record: object,
    request_scope: object,
) -> tuple[RelayMEMSLPPrimaryWorkerSource | None, tuple[str, ...]]:
    """Consume one source exactly once after full validation."""

    exact, errors = validate_relaymem_slp_primary_worker_source(
        source,
        claimed_record=claimed_record,
        request_scope=request_scope,
    )
    if exact is None:
        return None, errors
    assert type(request_scope) is RelayMEMSLPPrimaryWorkerSourceScope
    if not request_scope._consume(exact):
        return None, ("worker_source_consume_conflict",)
    return exact, ()


def project_relaymem_slp_primary_worker_source(
    value: RelayMEMSLPPrimaryWorkerSourceBuildResult,
) -> RelayMEMSLPPrimaryWorkerSourceProjection:
    """Project build state without protected content or correlation values."""

    source = value.source
    return RelayMEMSLPPrimaryWorkerSourceProjection(
        status=value.status,
        enabled=value.enabled,
        dry_run_only=value.dry_run_only,
        source_bundle_present=source is not None,
        source_correlation_valid=value.source_correlation_valid,
        message_count=len(source.governed_messages) if source is not None else 0,
        governed_experience_present=source is not None,
        scene_policy_present=source is not None,
        relayemo_present=(
            source is not None and source.relayemo_artifact is not None
        ),
        blocked_reason_ids=value.blocked_reasons,
    )


def build_relaymem_slp_primary_worker_source_node_result(
    result: RelayMEMSLPPrimaryWorkerSourceBuildResult,
) -> PipelineNodeResult:
    """Build the content-free generic node projection."""

    node_status = {
        "disabled": "skipped",
        "invalid_input": "failed",
        "blocked": "blocked",
    }.get(result.status, "diagnostic_only")
    projection = result.to_log_dict()
    return build_pipeline_node_result(
        node_name="relaymem_slp_primary_worker_source",
        status=node_status,
        decision=result.status,
        blocked_reasons=result.blocked_reasons,
        diagnostics=projection,
        artifacts=[{
            "artifact_name": "relaymem_slp_primary_worker_source",
            "schema_version": SOURCE_SCHEMA,
            "present": result.source is not None,
            "content_free": True,
            "runtime_private": True,
            "source_omitted": True,
            "raw_messages_included": False,
            "governed_experience_included": False,
            "identifier_values_included": False,
            "idempotency_key_included": False,
            "lease_token_included": False,
            "queue_io_performed": False,
            "worker_invoked": False,
            "writes_memory": False,
            "mutates_soul": False,
            "changes_visible_response": False,
        }],
    )


def _result(
    status: BuildStatus,
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    source: RelayMEMSLPPrimaryWorkerSource | None,
    source_correlation_valid: bool,
    blocked_reasons: Sequence[str],
) -> RelayMEMSLPPrimaryWorkerSourceBuildResult:
    return RelayMEMSLPPrimaryWorkerSourceBuildResult(
        status=status,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        source=source,
        source_correlation_valid=source_correlation_valid,
        blocked_reasons=dedupe(tuple(blocked_reasons)),
    )


def _parse_source_payload(
    value: object,
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    if type(value) is not dict:
        return None, ("worker_source_shape_invalid",)
    if len(value) != len(SOURCE_FIELDS) or set(value) != SOURCE_FIELDS:
        return None, ("worker_source_shape_mismatch",)

    errors: list[str] = []
    if value.get("schema_version") != SOURCE_SCHEMA:
        errors.append("worker_source_schema_mismatch")
    if value.get("runtime_private") is not True:
        errors.append("worker_source_runtime_private_required")
    if value.get("content_included") is not True:
        errors.append("worker_source_content_required")

    job_id = value.get("job_id")
    dispatch_key = value.get("dispatch_idempotency_key")
    if not has_prefixed_digest(job_id, JOB_ID_PREFIX):
        errors.append("worker_source_job_id_invalid")
    if not has_prefixed_digest(dispatch_key, DISPATCH_KEY_PREFIX):
        errors.append("worker_source_dispatch_key_invalid")
    if (
        has_prefixed_digest(job_id, JOB_ID_PREFIX)
        and has_prefixed_digest(dispatch_key, DISPATCH_KEY_PREFIX)
        and job_id != derive_job_id(dispatch_key)
    ):
        errors.append("worker_source_job_dispatch_identity_mismatch")

    for field_name in ("run_id", "namespace"):
        if not is_token(value.get(field_name)):
            errors.append(f"worker_source_{field_name}_invalid")
    turn_index = value.get("turn_index")
    if type(turn_index) is not int or turn_index < 0:
        errors.append("worker_source_turn_index_invalid")
    session_id = value.get("session_id")
    if session_id is not None and not is_token(session_id):
        errors.append("worker_source_session_id_invalid")
    event_kind = value.get("source_event_kind")
    if type(event_kind) is not str or event_kind not in ALLOWED_EVENT_KINDS:
        errors.append("worker_source_event_kind_invalid")
    source_count = value.get("source_count")
    if type(source_count) is not int or not 1 <= source_count <= MAX_SOURCES:
        errors.append("worker_source_count_invalid")
    lineage = value.get("source_lineage_fingerprint")
    if not is_sha256(lineage):
        errors.append("worker_source_lineage_invalid")

    messages, message_errors = _parse_governed_messages(value.get("governed_messages"))
    errors.extend(message_errors)
    scene, scene_errors = _parse_scene_artifact(
        value.get("relayscn_scene_policy_artifact")
    )
    errors.extend(scene_errors)
    emo, emo_errors = _parse_relayemo_artifact(value.get("relayemo_artifact"))
    errors.extend(emo_errors)
    experience, experience_errors = _parse_governed_experience(
        value.get("governed_experience_artifact")
    )
    errors.extend(experience_errors)

    if experience is not None:
        if experience.get("source_event_kind") != event_kind:
            errors.append("worker_source_experience_event_mismatch")
        if experience.get("namespace") != value.get("namespace"):
            errors.append("worker_source_experience_namespace_mismatch")

    if errors:
        return None, dedupe(errors)
    assert messages is not None and scene is not None
    assert experience is not None
    return {
        "job_id": job_id,
        "dispatch_idempotency_key": dispatch_key,
        "run_id": value["run_id"],
        "turn_index": turn_index,
        "session_id": session_id,
        "namespace": value["namespace"],
        "source_event_kind": event_kind,
        "source_count": source_count,
        "source_lineage_fingerprint": lineage,
        "relayscn_scene_policy_artifact": scene,
        "relayemo_artifact": emo,
        "governed_messages": messages,
        "governed_experience_artifact": experience,
    }, ()


def _parse_governed_messages(
    value: object,
) -> tuple[tuple[RelayMEMSLPGovernedMessage, ...] | None, tuple[str, ...]]:
    if type(value) not in {list, tuple}:
        return None, ("governed_messages_shape_invalid",)
    if not 1 <= len(value) <= MAX_MESSAGES:
        return None, ("governed_messages_count_invalid",)
    output: list[RelayMEMSLPGovernedMessage] = []
    total_chars = 0
    user_present = False
    for item in value:
        if type(item) is not dict:
            return None, ("governed_message_shape_invalid",)
        if len(item) != len(MESSAGE_FIELDS) or set(item) != MESSAGE_FIELDS:
            return None, ("governed_message_field_set_mismatch",)
        role = item.get("role")
        content = item.get("content")
        if type(role) is not str or role not in ALLOWED_MESSAGE_ROLES:
            return None, ("governed_message_role_invalid",)
        if type(content) is not str or not content or len(content) > MAX_MESSAGE_CHARS:
            return None, ("governed_message_content_invalid",)
        if _bad_content_text(content, allow_newlines=True):
            return None, ("governed_message_content_invalid",)
        total_chars += len(content)
        if total_chars > MAX_TOTAL_MESSAGE_CHARS:
            return None, ("governed_messages_content_unbounded",)
        user_present = user_present or role == "user"
        output.append(RelayMEMSLPGovernedMessage(role=role, content=content))
    if not user_present:
        return None, ("governed_messages_user_missing",)
    return tuple(output), ()


def _parse_scene_artifact(
    value: object,
) -> tuple[Mapping[str, object] | None, tuple[str, ...]]:
    if type(value) is not dict:
        return None, ("relayscn_scene_policy_artifact_invalid",)
    scene_state = value.get("scene_state")
    scene_policy = value.get("scene_policy")
    if type(scene_state) is not dict or type(scene_policy) is not dict:
        return None, ("relayscn_scene_policy_artifact_shape_invalid",)
    if type(value.get("persistence_block")) is not bool:
        return None, ("relayscn_persistence_block_invalid",)
    reasons = value.get("persistence_block_reasons")
    if not _is_string_sequence(reasons):
        return None, ("relayscn_persistence_reasons_invalid",)
    frozen, errors = _freeze_json(value, "relayscn_scene_policy_artifact")
    return (frozen, ()) if frozen is not None else (None, errors)


def _parse_relayemo_artifact(
    value: object,
) -> tuple[Mapping[str, object] | None, tuple[str, ...]]:
    if value is None:
        return None, ()
    if type(value) is not dict:
        return None, ("relayemo_artifact_invalid",)
    assistant_state = value.get("assistant_emotion_state")
    user_affect = value.get("user_affect_estimate")
    if type(assistant_state) is not dict or type(user_affect) is not dict:
        return None, ("relayemo_artifact_shape_invalid",)
    frozen, errors = _freeze_json(value, "relayemo_artifact")
    return (frozen, ()) if frozen is not None else (None, errors)


def _parse_governed_experience(
    value: object,
) -> tuple[Mapping[str, object] | None, tuple[str, ...]]:
    if type(value) is not dict:
        return None, ("governed_experience_artifact_invalid",)
    if len(value) != len(EXPERIENCE_FIELDS) or set(value) != EXPERIENCE_FIELDS:
        return None, ("governed_experience_field_set_mismatch",)
    fixed = {
        "schema_version": GOVERNED_EXPERIENCE_SCHEMA,
        "runtime_private": True,
        "content_included": True,
        "raw_source_text_included": False,
        "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "summary_origin": "trusted_in_process_summary",
        "valid": True,
    }
    errors: list[str] = []
    for key, expected in fixed.items():
        if value.get(key) != expected or type(value.get(key)) is not type(expected):
            errors.append(f"governed_experience_{key}_invalid")
    for field_name in ("candidate_id", "source_event_kind", "namespace"):
        if not is_token(value.get(field_name)):
            errors.append(f"governed_experience_{field_name}_invalid")
    if value.get("source_event_kind") not in ALLOWED_EVENT_KINDS:
        errors.append("governed_experience_source_event_kind_invalid")
    title = value.get("title")
    if (
        type(title) is not str
        or not title
        or len(title) > MAX_TITLE_CHARS
        or _bad_content_text(title)
    ):
        errors.append("governed_experience_title_invalid")
    summary = value.get("summary_text")
    if (
        type(summary) is not str
        or not summary
        or len(summary) > MAX_SUMMARY_CHARS
        or _bad_content_text(summary, allow_newlines=True)
    ):
        errors.append("governed_experience_summary_invalid")
        summary = ""
    summary_chars = value.get("summary_chars")
    if type(summary_chars) is not int or summary_chars != len(summary):
        errors.append("governed_experience_summary_chars_mismatch")
    blocked = value.get("blocked_reasons")
    if type(blocked) not in {list, tuple} or blocked:
        errors.append("governed_experience_blocked")
    if errors:
        return None, dedupe(errors)
    frozen, freeze_errors = _freeze_json(value, "governed_experience_artifact")
    return (frozen, ()) if frozen is not None else (None, freeze_errors)


def _validate_claimed_record(
    value: object,
) -> tuple[Mapping[str, object] | None, tuple[str, ...]]:
    errors = validate_record_mapping(value)
    if errors:
        return None, errors
    assert isinstance(value, Mapping)
    if value.get("schema_version") != DURABLE_JOB_SCHEMA:
        return None, ("claimed_record_schema_mismatch",)
    if value.get("state") != "claimed":
        return None, ("claimed_record_state_invalid",)
    return value, ()


def _correlation_errors(
    source: Mapping[str, object],
    record: Mapping[str, object],
) -> tuple[str, ...]:
    checks = (
        ("job_id", "worker_source_job_id_mismatch"),
        ("dispatch_idempotency_key", "worker_source_dispatch_key_mismatch"),
        ("run_id", "worker_source_run_id_mismatch"),
        ("turn_index", "worker_source_turn_index_mismatch"),
        ("session_id", "worker_source_session_id_mismatch"),
        ("namespace", "worker_source_namespace_mismatch"),
        ("source_event_kind", "worker_source_event_kind_mismatch"),
        ("source_count", "worker_source_count_claim_mismatch"),
        ("source_lineage_fingerprint", "worker_source_lineage_mismatch"),
    )
    return dedupe(tuple(reason for field_name, reason in checks if source.get(field_name) != record.get(field_name)))


def _validate_typed_source(
    source: RelayMEMSLPPrimaryWorkerSource,
) -> tuple[str, ...]:
    try:
        payload = source.to_protected_runtime_dict()
    except Exception:
        return ("worker_source_snapshot_invalid",)
    parsed, errors = _parse_source_payload(payload)
    if parsed is None:
        return errors
    if set(payload) != SOURCE_FIELDS:
        return ("worker_source_shape_mismatch",)
    return ()


def _freeze_json(
    value: object,
    reason_prefix: str,
) -> tuple[object | None, tuple[str, ...]]:
    node_count = 0

    def freeze(item: object, depth: int) -> object:
        nonlocal node_count
        node_count += 1
        if depth > MAX_JSON_DEPTH or node_count > MAX_JSON_NODES:
            raise ValueError("bounded")
        if item is None or type(item) in {str, bool, int}:
            return item
        if type(item) is float:
            if not math.isfinite(item):
                raise ValueError("finite")
            return item
        if type(item) is dict:
            output: dict[str, object] = {}
            for key, child in item.items():
                if type(key) is not str or not key or _bad_key(key):
                    raise TypeError("key")
                output[key] = freeze(child, depth + 1)
            return MappingProxyType(output)
        if type(item) in {list, tuple}:
            return tuple(freeze(child, depth + 1) for child in item)
        raise TypeError("type")

    try:
        return freeze(value, 0), ()
    except Exception:
        return None, (f"{reason_prefix}_json_invalid",)


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(child) for child in value]
    return value


def _is_string_sequence(value: object) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
        and len(value) <= 32
        and all(type(item) is str and item and is_token(item) for item in value)
    )


def _bad_key(value: str) -> bool:
    return len(value) > 128 or any(ord(character) < 32 or ord(character) == 127 for character in value)


def _bad_content_text(value: str, *, allow_newlines: bool = False) -> bool:
    for character in value:
        code = ord(character)
        if code == 127:
            return True
        if code < 32 and not (allow_newlines and character in "\n\t"):
            return True
    return False


__all__ = [
    "GOVERNED_EXPERIENCE_SCHEMA",
    "PROJECTION_SCHEMA",
    "RESULT_SCHEMA",
    "SOURCE_FIELDS",
    "SOURCE_SCHEMA",
    "RelayMEMSLPGovernedMessage",
    "RelayMEMSLPPrimaryWorkerSource",
    "RelayMEMSLPPrimaryWorkerSourceBuildResult",
    "RelayMEMSLPPrimaryWorkerSourceProjection",
    "RelayMEMSLPPrimaryWorkerSourceScope",
    "build_relaymem_slp_primary_worker_source",
    "build_relaymem_slp_primary_worker_source_node_result",
    "consume_relaymem_slp_primary_worker_source",
    "project_relaymem_slp_primary_worker_source",
    "validate_relaymem_slp_primary_worker_source",
]

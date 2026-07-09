"""Typed audit metadata projections for content-free trace records.

Only fields explicitly copied by a registered projector can reach persisted
audit metadata. Unknown artifacts, unknown nodes, and unknown nested fields are
omitted by default.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable, Final

Projection = tuple[object, int]
Validator = Callable[[Any], Projection]


@dataclass(frozen=True)
class AuditProjectionResult:
    metadata: dict[str, object]
    dropped_field_count: int
    unsupported_artifact_count: int


_DROP: Final = object()
_OMIT: Final = object()

_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_LOWER_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$")
_CLASS_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_CONTENT_TYPE_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,63}/"
    r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,63}"
    r"(?:\s*;\s*charset=[A-Za-z0-9._-]{1,32})?$"
)
_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_WINDOWS_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")

_UUID_TEXT = (
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)

_PIPELINE_STATUSES = frozenset(
    {"applied", "skipped", "blocked", "failed", "diagnostic_only"}
)
_STATE_COUNT_KEYS = frozenset({"active", "promoted", "demoted", "disabled"})
_CONTENT_SHAPE_KEYS = frozenset(
    {
        "string",
        "empty_string",
        "text_parts",
        "empty_parts",
        "multimodal_parts",
        "missing",
        "unknown",
        "invalid_parts",
        "unsupported",
        "text",
        "empty_text",
    }
)
_FINGERPRINT_SCOPE_KEYS = frozenset(
    {
        "candidate_count",
        "candidate_role_count",
        "candidate_index_count",
        "content_shape_kind_count",
    }
)


def project_audit_metadata(
    metadata: Mapping[str, Any] | None,
) -> AuditProjectionResult:
    """Project runtime metadata through exact, pure projector registries."""

    if not isinstance(metadata, Mapping):
        return AuditProjectionResult({}, 0, 0)

    projected: dict[str, object] = {}
    dropped = 0
    unsupported = 0

    for raw_key, value in metadata.items():
        key = str(raw_key)
        projector = TOP_LEVEL_PROJECTORS.get(key)
        if projector is None:
            unsupported += 1
            continue
        clean, child_dropped = projector(value)
        dropped += child_dropped
        if clean is _OMIT:
            continue
        if clean is _DROP:
            dropped += 1
            continue
        projected[key] = clean

    if dropped:
        projected["projection_dropped_field_count"] = dropped
    if unsupported:
        projected["projection_unsupported_artifact_count"] = unsupported
    return AuditProjectionResult(projected, dropped, unsupported)


def _ok(value: object) -> Projection:
    return value, 0


def _drop() -> Projection:
    return _DROP, 0


def _omit() -> Projection:
    return _OMIT, 0


def _optional(validator: Validator) -> Validator:
    def validate(value: Any) -> Projection:
        if value is None:
            return _omit()
        return validator(value)

    return validate


def _bool(value: Any) -> Projection:
    return _ok(value) if isinstance(value, bool) else _drop()


def _non_negative_int(value: Any) -> Projection:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return _drop()
    return _ok(value)


def _non_negative_number(value: Any) -> Projection:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _drop()
    if not math.isfinite(value) or value < 0:
        return _drop()
    return _ok(value)


def _http_status(value: Any) -> Projection:
    if isinstance(value, bool) or not isinstance(value, int):
        return _drop()
    return _ok(value) if 100 <= value <= 599 else _drop()


def _bounded_token(value: Any) -> Projection:
    if not isinstance(value, str) or not value or len(value) > 128:
        return _drop()
    if _looks_like_url_or_path(value):
        return _drop()
    return _ok(value) if _TOKEN_RE.fullmatch(value) else _drop()


def _lower_token(value: Any) -> Projection:
    if not isinstance(value, str) or not value or len(value) > 128:
        return _drop()
    if _looks_like_url_or_path(value):
        return _drop()
    return _ok(value) if _LOWER_TOKEN_RE.fullmatch(value) else _drop()


def _class_token(value: Any) -> Projection:
    if not isinstance(value, str) or not value or len(value) > 128:
        return _drop()
    return _ok(value) if _CLASS_TOKEN_RE.fullmatch(value) else _drop()


def _opaque_id(value: Any) -> Projection:
    if not isinstance(value, str) or not value or len(value) > 256:
        return _drop()
    if _looks_like_url_or_path(value):
        return _drop()
    return _ok(value) if _OPAQUE_ID_RE.fullmatch(value) else _drop()


def _sha256(value: Any) -> Projection:
    return _ok(value) if isinstance(value, str) and _SHA256_RE.fullmatch(value) else _drop()


def _content_type(value: Any) -> Projection:
    if not isinstance(value, str):
        return _drop()
    return _ok(value) if _CONTENT_TYPE_RE.fullmatch(value) else _drop()


def _scoped_uuid_id(suffix: str) -> Validator:
    pattern = re.compile(rf"^{_UUID_TEXT}:{re.escape(suffix)}$", re.IGNORECASE)

    def validate(value: Any) -> Projection:
        if isinstance(value, str) and pattern.fullmatch(value):
            return _ok(value)
        return _drop()

    return validate


def _enum(*allowed: str) -> Validator:
    values = frozenset(allowed)

    def validate(value: Any) -> Projection:
        return _ok(value) if isinstance(value, str) and value in values else _drop()

    return validate


def _list_of(
    validator: Validator,
    *,
    max_items: int = 256,
) -> Validator:
    def validate(value: Any) -> Projection:
        if not isinstance(value, Sequence) or isinstance(
            value, (str, bytes, bytearray)
        ):
            return _drop()
        output: list[object] = []
        dropped = 0
        for item in list(value)[:max_items]:
            clean, child_dropped = validator(item)
            dropped += child_dropped
            if clean is _DROP:
                dropped += 1
                continue
            if clean is _OMIT:
                continue
            output.append(clean)
        if len(value) > max_items:
            dropped += len(value) - max_items
        return output, dropped

    return validate


def _mapping(
    fields: Mapping[str, Validator],
) -> Validator:
    exact_fields = dict(fields)

    def validate(value: Any) -> Projection:
        if not isinstance(value, Mapping):
            return _drop()
        output: dict[str, object] = {}
        dropped = 0
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            validator = exact_fields.get(key)
            if validator is None:
                dropped += 1
                continue
            clean, child_dropped = validator(raw_value)
            dropped += child_dropped
            if clean is _DROP:
                dropped += 1
                continue
            if clean is _OMIT:
                continue
            output[key] = clean
        return output, dropped

    return validate


def _exact_string_int_map(keys: frozenset[str]) -> Validator:
    def validate(value: Any) -> Projection:
        if not isinstance(value, Mapping):
            return _drop()
        output: dict[str, int] = {}
        dropped = 0
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if key not in keys:
                dropped += 1
                continue
            clean, _ = _non_negative_int(raw_value)
            if clean is _DROP:
                dropped += 1
                continue
            output[key] = clean  # type: ignore[assignment]
        return output, dropped

    return validate


_REASON_LIST = _list_of(_lower_token)
_TOKEN_LIST = _list_of(_bounded_token)
_OPAQUE_ID_LIST = _list_of(_opaque_id)
_INDEX_LIST = _list_of(_non_negative_int)
_STATE_COUNTS = _exact_string_int_map(_STATE_COUNT_KEYS)
_CONTENT_SHAPE_COUNTS = _exact_string_int_map(_CONTENT_SHAPE_KEYS)
_FINGERPRINT_SCOPE = _exact_string_int_map(_FINGERPRINT_SCOPE_KEYS)

def _reject_non_none(value: Any) -> Projection:
    return _drop()


def _artifact_fields(
    name: str,
    schema_version: str | None,
    *,
    extras: Mapping[str, Validator] | None = None,
) -> Validator:
    fields: dict[str, Validator] = {
        "artifact_name": _enum(name),
        "schema_version": (
            _optional(_enum(schema_version))
            if schema_version is not None
            else _optional(_reject_non_none)
        ),
        "present": _bool,
        "diagnostics_only": _optional(_bool),
        "content_free": _optional(_bool),
        "applied": _optional(_bool),
    }
    if extras:
        fields.update(extras)
    return _mapping(fields)


_ARTIFACT_PROJECTORS: dict[str, Validator] = {
    "client_message_canonicalization_dry_run": _artifact_fields(
        "client_message_canonicalization_dry_run",
        "client_message_canonicalization_dry_run.v0",
    ),
    "client_instruction_extraction_dry_run": _artifact_fields(
        "client_instruction_extraction_dry_run",
        "client_instruction_extraction_dry_run.v0",
    ),
    "client_instruction_fingerprint_dry_run": _artifact_fields(
        "client_instruction_fingerprint_dry_run",
        "client_instruction_fingerprint_dry_run.v0",
    ),
    "client_instruction_identity_runtime_summary": _artifact_fields(
        "client_instruction_identity_runtime_summary",
        "client_instruction_identity.v0",
        extras={"runtime_private_source": _optional(_bool)},
    ),
    "client_instruction_cache_dry_run": _artifact_fields(
        "client_instruction_cache_dry_run",
        "client_instruction_cache_dry_run.v0",
        extras={"dry_run_only": _optional(_bool)},
    ),
    "client_instruction_cache_lookup_runtime_summary": _artifact_fields(
        "client_instruction_cache_lookup_runtime_summary",
        "client_instruction_cache_lookup_runtime.v0",
        extras={
            "runtime_private_source": _optional(_bool),
            "read_only": _optional(_bool),
        },
    ),
    "client_history_exclusion_preflight_summary": _artifact_fields(
        "client_history_exclusion_preflight_summary",
        "client_history_exclusion_preflight.v0",
        extras={
            "runtime_private_source": _optional(_bool),
            "payload_mutation_applied": _optional(_bool),
        },
    ),
    "client_history_exclusion_apply_summary": _mapping(
        {
            "artifact_name": _enum("client_history_exclusion_apply_summary"),
            "schema_version": _enum("client_history_exclusion_apply.v0"),
            "present": _bool,
            "diagnostics_only": _bool,
            "content_free": _bool,
            "runtime_private_source": _bool,
            "payload_candidate_present": _bool,
            "payload_mutation_applied": _bool,
            "content_bearing_candidate_persisted": _bool,
        }
    ),
    "relayref_artifact": _artifact_fields(
        "relayref_artifact",
        "relayref.dry_run_artifact.v0",
    ),
    "relayint_intent_artifact": _artifact_fields(
        "relayint_intent_artifact",
        "relayint.intent.v1",
    ),
    "relayint_fast_path_dry_run": _artifact_fields(
        "relayint_fast_path_dry_run",
        "relayint_fast_path_dry_run.v0",
    ),
    "relayint_quick_clarification_preflight": _artifact_fields(
        "relayint_quick_clarification_preflight",
        "relayint_quick_clarification_preflight.v0",
    ),
    "relayint_quick_clarification_apply_plan": _artifact_fields(
        "relayint_quick_clarification_apply_plan",
        "relayint_quick_clarification_apply_plan.v0",
    ),
    "runtime_ctx_injection_result": _artifact_fields(
        "runtime_ctx_injection_result",
        "relaymem.runtime_ctx_injection_result.v0",
    ),
    "runtime_snippet_injection_result": _artifact_fields(
        "runtime_snippet_injection_result",
        "relaymem.runtime_snippet_injection_result.v0",
    ),
    "token_budget_truncation": _artifact_fields(
        "token_budget_truncation",
        None,
    ),
    "relayctx_short_term_runtime_injection_apply_result": _artifact_fields(
        "relayctx_short_term_runtime_injection_apply_result",
        "relayctx_short_term_runtime_injection_apply_result.v0",
    ),
    "relayctx_unpack_runtime_result": _mapping(
        {
            "artifact_name": _enum("relayctx_unpack_runtime_result"),
            "schema_version": _optional(_enum("relayctx_unpack_runtime.v0")),
            "present": _bool,
            "content_free": _optional(_bool),
            "applied_to_response": _optional(_bool),
            "candidate_present": _optional(_bool),
            "persistence_allowed": _optional(_bool),
        }
    ),
}


@dataclass(frozen=True)
class NodeProjector:
    decisions: frozenset[str] | None
    diagnostics: Validator
    artifact_names: frozenset[str]


def _artifact_list(allowed_names: frozenset[str]) -> Validator:
    def validate(value: Any) -> Projection:
        if not isinstance(value, Sequence) or isinstance(
            value, (str, bytes, bytearray)
        ):
            return _drop()
        output: list[object] = []
        dropped = 0
        for item in value:
            if not isinstance(item, Mapping):
                dropped += 1
                continue
            artifact_name = item.get("artifact_name")
            if not isinstance(artifact_name, str) or artifact_name not in allowed_names:
                dropped += 1
                continue
            projector = _ARTIFACT_PROJECTORS.get(artifact_name)
            if projector is None:
                dropped += 1
                continue
            clean, child_dropped = projector(item)
            dropped += child_dropped
            if clean is _DROP or clean is _OMIT:
                dropped += 1
                continue
            output.append(clean)
        return output, dropped

    return validate


def _project_node(
    value: Mapping[str, Any],
    *,
    node_name: str,
    spec: NodeProjector,
) -> Projection:
    output: dict[str, object] = {"node_name": node_name}
    dropped = 0

    clean_status, _ = _enum(*sorted(_PIPELINE_STATUSES))(value.get("status"))
    if clean_status is _DROP:
        dropped += 1
    else:
        output["status"] = clean_status

    decision = value.get("decision")
    if decision is not None:
        validator = _bounded_token if spec.decisions is None else _enum(*sorted(spec.decisions))
        clean_decision, _ = validator(decision)
        if clean_decision is _DROP:
            dropped += 1
        else:
            output["decision"] = clean_decision

    if "blocked_reasons" in value:
        clean_reasons, child_dropped = _REASON_LIST(value.get("blocked_reasons"))
        dropped += child_dropped
        if clean_reasons is _DROP:
            dropped += 1
        else:
            output["blocked_reasons"] = clean_reasons

    if "diagnostics" in value:
        clean_diagnostics, child_dropped = spec.diagnostics(value.get("diagnostics"))
        dropped += child_dropped
        if clean_diagnostics is _DROP:
            dropped += 1
        elif clean_diagnostics is not _OMIT and clean_diagnostics:
            output["diagnostics"] = clean_diagnostics

    if "artifacts" in value:
        clean_artifacts, child_dropped = _artifact_list(spec.artifact_names)(
            value.get("artifacts")
        )
        dropped += child_dropped
        if clean_artifacts is _DROP:
            dropped += 1
        elif clean_artifacts is not _OMIT and clean_artifacts:
            output["artifacts"] = clean_artifacts

    for key in value:
        if str(key) not in {
            "node_name",
            "status",
            "decision",
            "blocked_reasons",
            "diagnostics",
            "artifacts",
        }:
            dropped += 1
    return output, dropped


_CANONICALIZATION_DIAGNOSTICS = _mapping(
    {
        "schema_version": _enum("client_message_canonicalization_dry_run.v0"),
        "enabled": _bool,
        "diagnostics_only": _bool,
        "content_free": _bool,
        "managed_route": _bool,
        "route_policy": _enum("relay_managed", "pass_through"),
        "messages_present": _bool,
        "message_count": _non_negative_int,
        "valid_message_count": _non_negative_int,
        "invalid_message_count": _non_negative_int,
        "system_message_count": _non_negative_int,
        "developer_message_count": _non_negative_int,
        "instruction_message_count": _non_negative_int,
        "instruction_text_message_count": _non_negative_int,
        "instruction_without_text_count": _non_negative_int,
        "current_user_turn_present": _bool,
        "current_user_content_valid": _bool,
        "current_user_content_kind": _enum(
            "text", "empty_text", "missing", "unsupported",
            "multimodal_parts", "text_parts", "invalid_parts",
        ),
        "current_user_text_part_count": _non_negative_int,
        "current_user_non_text_part_count": _non_negative_int,
        "current_user_invalid_part_count": _non_negative_int,
        "current_user_multimodal": _bool,
        "messages_before_current_user_count": _non_negative_int,
        "messages_after_current_user_count": _non_negative_int,
        "prior_user_message_count": _non_negative_int,
        "prior_assistant_message_count": _non_negative_int,
        "tool_message_count": _non_negative_int,
        "assistant_tool_call_message_count": _non_negative_int,
        "post_user_tool_message_count": _non_negative_int,
        "active_tool_transaction_candidate": _bool,
        "canonicalization_candidate_ready": _bool,
    }
)

_EXTRACTION_DIAGNOSTICS = _mapping(
    {
        "schema_version": _enum("client_instruction_extraction_dry_run.v0"),
        "enabled": _bool,
        "diagnostics_only": _bool,
        "content_free": _bool,
        "managed_route": _bool,
        "route_policy": _enum("relay_managed", "pass_through"),
        "messages_present": _bool,
        "message_count": _non_negative_int,
        "valid_message_count": _non_negative_int,
        "invalid_message_count": _non_negative_int,
        "instruction_candidate_count": _non_negative_int,
        "candidate_roles": _list_of(_enum("system", "developer")),
        "candidate_indices": _INDEX_LIST,
        "content_shape_counts": _CONTENT_SHAPE_COUNTS,
        "invalid_instruction_candidate_count": _non_negative_int,
        "unknown_instruction_candidate_shape_count": _non_negative_int,
        "multimodal_instruction_candidate_count": _non_negative_int,
        "has_multimodal_instruction_candidate": _bool,
        "active_tool_transaction_candidate": _bool,
        "assistant_tool_call_message_count_after_latest_user": _non_negative_int,
        "tool_message_count_after_latest_user": _non_negative_int,
        "fingerprint_candidate_ready": _bool,
    }
)

_FINGERPRINT_DIAGNOSTICS = _mapping(
    {
        "schema_version": _enum("client_instruction_fingerprint_dry_run.v0"),
        "enabled": _bool,
        "diagnostics_only": _bool,
        "content_free": _bool,
        "source_artifact_present": _bool,
        "source_schema_version": _optional(_bounded_token),
        "source_schema_supported": _bool,
        "managed_route": _bool,
        "route_policy": _optional(_enum("relay_managed", "pass_through")),
        "extraction_candidate_ready": _bool,
        "fingerprint_plan_ready": _bool,
        "fingerprint_plan_mode": _enum("metadata_contract_only"),
        "fingerprint_hash_computed": _bool,
        "cache_key_computed": _bool,
        "cache_lookup_attempted": _bool,
        "cache_save_attempted": _bool,
        "instruction_candidate_count": _non_negative_int,
        "candidate_roles": _list_of(_enum("system", "developer")),
        "candidate_indices": _INDEX_LIST,
        "content_shape_counts": _CONTENT_SHAPE_COUNTS,
        "message_count": _non_negative_int,
        "valid_message_count": _non_negative_int,
        "invalid_message_count": _non_negative_int,
        "invalid_instruction_candidate_count": _non_negative_int,
        "unknown_instruction_candidate_shape_count": _non_negative_int,
        "multimodal_instruction_candidate_count": _non_negative_int,
        "has_multimodal_instruction_candidate": _bool,
        "active_tool_transaction_candidate": _bool,
        "fingerprint_scope_summary": _FINGERPRINT_SCOPE,
        "source_blocked_reasons": _REASON_LIST,
    }
)

_IDENTITY_DIAGNOSTICS = _mapping(
    {
        "schema_version": _enum("client_instruction_identity.v0"),
        "enabled": _bool,
        "ready": _bool,
        "runtime_private_artifact_present": _bool,
        "content_bearing_artifact_present": _bool,
        "instruction_candidate_count": _non_negative_int,
        "candidate_roles": _list_of(_enum("system", "developer")),
        "candidate_indices": _INDEX_LIST,
        "empty_instruction": _bool,
        "normalization_applied": _bool,
        "instruction_fingerprint_computed": _bool,
        "cache_key_computed": _bool,
        "hash_algorithm": _optional(_enum("sha256")),
    }
)

_CACHE_DIAGNOSTICS = _mapping(
    {
        "schema_version": _enum("client_instruction_cache_dry_run.v0"),
        "enabled": _bool,
        "diagnostics_only": _bool,
        "content_free": _bool,
        "dry_run_only": _bool,
        "operation_plan_mode": _enum("metadata_contract_only"),
        "source_artifact_present": _bool,
        "source_schema_version": _optional(_bounded_token),
        "source_schema_supported": _bool,
        "cache_operation_plan_ready": _bool,
        "lookup_requested": _bool,
        "save_requested": _bool,
        "lookup_plan_ready": _bool,
        "save_plan_ready": _bool,
        "cache_lookup_attempted": _bool,
        "cache_save_attempted": _bool,
        "cache_key_computed": _bool,
        "cache_key_available": _bool,
        "fingerprint_hash_computed": _bool,
        "fingerprint_hash_available": _bool,
        "cache_hit_known": _bool,
        "cache_hit": _optional(_bool),
        "cache_result_available": _bool,
        "payload_mutation_applied": _bool,
        "history_exclusion_applied": _bool,
        "persistence_applied": _bool,
        "instruction_candidate_count": _non_negative_int,
        "candidate_roles": _list_of(_enum("system", "developer")),
        "candidate_indices": _INDEX_LIST,
        "content_shape_counts": _CONTENT_SHAPE_COUNTS,
        "fingerprint_scope_summary": _FINGERPRINT_SCOPE,
        "source_blocked_reasons": _REASON_LIST,
    }
)

_LOOKUP_DIAGNOSTICS = _mapping(
    {
        "schema_version": _enum("client_instruction_cache_lookup_runtime.v0"),
        "enabled": _bool,
        "status": _enum("hit", "miss", "blocked", "skipped"),
        "cache_hit": _bool,
        "cache_miss": _bool,
        "cache_read_attempted": _bool,
        "cache_lookup_attempted": _bool,
        "reader_status": _optional(_bounded_token),
        "lookup_status": _optional(_bounded_token),
        "entry_present": _bool,
        "entry_parsed": _bool,
        "bytes_read": _non_negative_int,
        "max_entry_bytes": _non_negative_int,
        "cache_root_configured": _bool,
        "cache_root_present": _bool,
        "reader_miss_reason": _optional(_lower_token),
        "lookup_miss_reason": _optional(_lower_token),
        "runtime_private_source": _bool,
        "applied": _bool,
        "read_only": _bool,
    }
)

_RELAYSCN_PROJECTION_DIAGNOSTICS = _mapping(
    {
        "schema_version": _enum("client_instruction_relayscn_projection.v0"),
        "status": _enum("projected", "miss", "blocked", "skipped"),
        "cache_hit": _bool,
        "projection_ready": _bool,
        "projected_scene_type": _optional(_bounded_token),
        "projected_scene_role_present": _bool,
        "projected_scene_role_scope": _optional(_lower_token),
        "projected_scene_role_source": _optional(_lower_token),
        "projected_scene_role_confidence_bucket": _optional(
            _enum("very_high", "high", "medium", "low", "unknown")
        ),
        "projected_scene_context_present": _bool,
        "projected_scene_context_field_count": _non_negative_int,
        "projected_scene_context_participant_count": _non_negative_int,
        "projected_scene_constraint_count": _non_negative_int,
        "durable_candidate_count": _non_negative_int,
        "blocked_instruction_kind_count": _non_negative_int,
        "miss_reason": _optional(_lower_token),
        "diagnostics_only": _bool,
        "content_free": _bool,
        "read_only": _bool,
        "applied": _bool,
    }
)


_HISTORY_DIAGNOSTICS = _mapping(
    {
        "schema_version": _enum("client_history_exclusion_preflight.v0"),
        "enabled": _bool,
        "status": _enum("ready", "pending", "blocked", "skipped"),
        "managed_route": _bool,
        "preflight_ready": _bool,
        "history_exclusion_apply_ready": _bool,
        "instruction_resolution_mode": _enum(
            "none", "cache_hit", "cache_miss_first_pass", "blocked", "not_applicable",
        ),
        "first_pass_evidence_required": _bool,
        "original_message_count": _non_negative_int,
        "valid_message_count": _non_negative_int,
        "excluded_message_count_candidate": _non_negative_int,
        "preserved_client_message_count_candidate": _non_negative_int,
        "system_message_count": _non_negative_int,
        "developer_message_count": _non_negative_int,
        "instruction_message_count": _non_negative_int,
        "prior_user_message_count": _non_negative_int,
        "prior_assistant_message_count": _non_negative_int,
        "tool_message_count": _non_negative_int,
        "current_user_turn_present": _bool,
        "current_user_content_valid": _bool,
        "current_user_content_kind": _enum(
            "text", "empty_text", "missing", "unsupported",
            "multimodal_parts", "text_parts", "invalid_parts",
        ),
        "current_user_multimodal": _bool,
        "current_user_text_part_count": _non_negative_int,
        "current_user_non_text_part_count": _non_negative_int,
        "active_tool_transaction_candidate": _bool,
        "cache_lookup_status": _optional(_enum("hit", "miss", "blocked", "skipped")),
        "raw_instruction_exclusion_candidate": _bool,
        "payload_mutation_applied": _bool,
        "runtime_private_source": _bool,
    }
)

_REFERENCE_DIAGNOSTICS = _mapping(
    {
        "diagnostics_only": _bool,
        "content_free": _bool,
        "source_node_alias": _enum("relayint_reference_repair"),
        "compatibility_source_node": _enum("relayref"),
        "artifact_present": _bool,
        "unresolved_reference_detected": _bool,
        "apply_allowed": _bool,
    }
)

_REFERENCE_INTENT_DIAGNOSTICS = _mapping(
    {
        "diagnostics_only": _bool,
        "content_free": _bool,
        "source_node_alias": _enum("relayint_reference_intent"),
        "compatibility_source_node": _enum("relayint"),
        "artifact_present": _bool,
        "unresolved_reference_detected": _bool,
        "apply_allowed": _bool,
    }
)

_HISTORY_APPLY_DIAGNOSTICS = _mapping(
    {
        "schema_version": _enum("client_history_exclusion_apply.v0"),
        "enabled": _bool,
        "status": _enum("ready", "applied", "blocked", "skipped"),
        "dry_run_only": _bool,
        "managed_route": _bool,
        "compiler_used": _bool,
        "relay_owned_prefix_message_count": _non_negative_int,
        "original_compiled_message_count": _non_negative_int,
        "forwarded_message_count": _non_negative_int,
        "excluded_client_message_count": _non_negative_int,
        "preserved_client_message_count": _non_negative_int,
        "instruction_resolution_mode": _enum(
            "none", "cache_hit", "cache_miss_first_pass", "blocked", "not_applicable",
        ),
        "payload_candidate_present": _bool,
        "payload_mutation_applied": _bool,
        "runtime_private_source": _bool,
        "content_bearing_candidate_persisted": _bool,
    }
)

_QUICK_DIAGNOSTICS = _mapping(
    {
        "diagnostics_only": _bool,
        "content_free": _bool,
        "fast_path_present": _bool,
        "preflight_present": _bool,
        "apply_plan_present": _bool,
        "candidate_action": _optional(_bounded_token),
        "preflight_applicable": _bool,
        "apply_allowed": _bool,
    }
)

_REPACK_DIAGNOSTICS = _mapping(
    {
        "diagnostics_only": _bool,
        "content_free": _bool,
        "payload_mutation_applied": _bool,
        "last_mutating_step": _optional(_bounded_token),
        "phase_artifact_count": _non_negative_int,
    }
)

_RELAYCTX_UNPACK_DIAGNOSTICS = _mapping(
    {
        "schema_version": _optional(_enum("relayctx_unpack_result.v0")),
        "runtime_schema_version": _enum("relayctx_unpack_runtime.v0"),
        "status": _optional(
            _enum("plain_text", "structured_update", "update_blocked", "empty_response")
        ),
        "marker_present": _optional(_bool),
        "update_candidate_present": _optional(_bool),
        "update_accepted": _optional(_bool),
        "input_chars": _optional(_non_negative_int),
        "visible_chars": _optional(_non_negative_int),
        "update_chars": _optional(_non_negative_int),
        "accepted_field_names": _optional(_TOKEN_LIST),
        "contains_user_visible_text": _optional(_bool),
        "contains_ctx_working_update": _optional(_bool),
        "content_free": _bool,
        "persistence_allowed": _optional(_bool),
        "apply_enabled": _bool,
        "dry_run_only": _bool,
        "applied_to_response": _bool,
        "candidate_present": _bool,
        "candidate_persistence_allowed": _bool,
        "response_shape_supported": _bool,
    }
)

_RELAYMEM_SLP_FINALIZED_TURN_SOURCE_DIAGNOSTICS = _mapping(
    {
        "schema_version": _enum("relaymem.slp_finalized_turn_source_projection.v0"),
        "diagnostics_only": _bool,
        "content_free": _bool,
        "content_included": _bool,
        "raw_text_included": _bool,
        "raw_messages_included": _bool,
        "governed_title_included": _bool,
        "governed_summary_included": _bool,
        "identifier_values_included": _bool,
        "namespace_value_included": _bool,
        "lineage_fingerprint_included": _bool,
        "status": _enum("disabled", "invalid_input", "blocked", "ready"),
        "enabled": _bool,
        "response_finalized": _bool,
        "source_ready": _bool,
        "source_count": _non_negative_int,
        "current_user_present": _bool,
        "assistant_response_present": _bool,
        "scene_policy_present": _bool,
        "relayemo_present": _bool,
        "worker_invoked": _bool,
        "queue_io_performed": _bool,
        "writes_memory": _bool,
        "mutates_soul": _bool,
        "changes_visible_response": _bool,
        "blocked_reason_ids": _REASON_LIST,
    }
)

_RELAYMEM_SLP_RUNTIME_ENQUEUE_DIAGNOSTICS = _mapping(
    {
        "schema_version": _enum("relaymem.slp_runtime_enqueue_projection.v0"),
        "diagnostics_only": _bool,
        "content_free": _bool,
        "content_included": _bool,
        "raw_text_included": _bool,
        "raw_messages_included": _bool,
        "governed_title_included": _bool,
        "governed_summary_included": _bool,
        "namespace_value_included": _bool,
        "identifier_values_included": _bool,
        "lineage_fingerprint_included": _bool,
        "idempotency_key_included": _bool,
        "queue_path_included": _bool,
        "timestamp_values_included": _bool,
        "exception_text_included": _bool,
        "status": _enum(
            "disabled", "invalid_input", "skipped", "held", "blocked",
            "dry_run_ready", "enqueued", "duplicate_existing",
            "enqueue_failed", "source_retention_failed",
        ),
        "enabled": _bool,
        "dry_run_only": _bool,
        "apply_enabled": _bool,
        "finalized_turn_source_ready": _bool,
        "admission_eligible": _bool,
        "handoff_ready": _bool,
        "dispatch_ready": _bool,
        "source_capture_built": _bool,
        "typed_source_built": _bool,
        "source_retained": _bool,
        "worker_ready": _bool,
        "enqueue_attempted": _bool,
        "enqueue_new": _bool,
        "duplicate_existing": _bool,
        "blocked": _bool,
        "failure_stage": _enum(
            "none", "gate", "source_capture", "admission", "handoff",
            "dispatch", "enqueue", "source_retention",
        ),
        "process_local_source_retention": _bool,
        "restart_complete_source_persistence": _bool,
        "worker_invoked": _bool,
        "b3_claim_performed": _bool,
        "invokes_slp": _bool,
        "writes_memory": _bool,
        "mutates_soul": _bool,
        "changes_visible_response": _bool,
        "blocked_reason_ids": _REASON_LIST,
    }
)

PIPELINE_NODE_PROJECTORS: dict[str, NodeProjector] = {
    "client_message_canonicalization": NodeProjector(
        decisions=frozenset({
            "pass_through_route_exempt", "current_request_evidence_identified",
            "canonicalization_candidate_blocked",
        }),
        diagnostics=_CANONICALIZATION_DIAGNOSTICS,
        artifact_names=frozenset({"client_message_canonicalization_dry_run"}),
    ),
    "client_instruction_extraction": NodeProjector(
        decisions=frozenset({
            "pass_through_route_exempt", "instruction_fingerprint_candidate_ready",
            "instruction_fingerprint_candidate_blocked",
        }),
        diagnostics=_EXTRACTION_DIAGNOSTICS,
        artifact_names=frozenset({"client_instruction_extraction_dry_run"}),
    ),
    "client_instruction_fingerprint": NodeProjector(
        decisions=frozenset({
            "pass_through_route_exempt", "instruction_fingerprint_plan_ready",
            "instruction_fingerprint_plan_blocked",
        }),
        diagnostics=_FINGERPRINT_DIAGNOSTICS,
        artifact_names=frozenset({"client_instruction_fingerprint_dry_run"}),
    ),
    "client_instruction_identity": NodeProjector(
        decisions=frozenset({"instruction_identity_ready", "instruction_identity_blocked"}),
        diagnostics=_IDENTITY_DIAGNOSTICS,
        artifact_names=frozenset({"client_instruction_identity_runtime_summary"}),
    ),
    "client_instruction_cache": NodeProjector(
        decisions=frozenset({
            "instruction_cache_operation_plan_ready",
            "instruction_cache_operation_plan_blocked",
        }),
        diagnostics=_CACHE_DIAGNOSTICS,
        artifact_names=frozenset({"client_instruction_cache_dry_run"}),
    ),
    "client_instruction_cache_lookup": NodeProjector(
        decisions=frozenset({
            "instruction_cache_hit", "instruction_cache_miss",
            "pass_through_route_exempt", "instruction_cache_runtime_preparation_failed",
            "instruction_cache_read_blocked", "instruction_cache_source_blocked",
            "instruction_cache_lookup_blocked",
        }),
        diagnostics=_LOOKUP_DIAGNOSTICS,
        artifact_names=frozenset({"client_instruction_cache_lookup_runtime_summary"}),
    ),
    "client_instruction_relayscn_projection": NodeProjector(
        decisions=frozenset({
            "cache_hit_relayscn_projection_ready",
            "cache_hit_relayscn_projection_miss",
            "cache_hit_relayscn_projection_blocked",
            "cache_hit_relayscn_projection_skipped",
        }),
        diagnostics=_RELAYSCN_PROJECTION_DIAGNOSTICS,
        artifact_names=frozenset({"client_instruction_relayscn_projection_summary"}),
    ),
    "client_history_exclusion_preflight": NodeProjector(
        decisions=frozenset({
            "history_exclusion_preflight_ready", "client_instruction_first_pass_required",
            "pass_through_route_exempt", "history_exclusion_preflight_preparation_failed",
            "history_exclusion_preflight_blocked",
        }),
        diagnostics=_HISTORY_DIAGNOSTICS,
        artifact_names=frozenset({"client_history_exclusion_preflight_summary"}),
    ),
    "relayint_reference_repair": NodeProjector(
        decisions=frozenset({"none", "context_repair", "suggest_reflect"}),
        diagnostics=_REFERENCE_DIAGNOSTICS,
        artifact_names=frozenset({"relayref_artifact", "relayint_intent_artifact"}),
    ),
    "relayint_reference_intent": NodeProjector(
        decisions=frozenset({"none", "context_repair", "suggest_reflect"}),
        diagnostics=_REFERENCE_INTENT_DIAGNOSTICS,
        artifact_names=frozenset({"relayint_intent_artifact"}),
    ),
    "client_history_exclusion_apply": NodeProjector(
        decisions=frozenset({
            "pass_through_route_exempt",
            "client_history_exclusion_apply_blocked",
            "client_history_exclusion_applied",
            "client_history_exclusion_apply_ready",
        }),
        diagnostics=_HISTORY_APPLY_DIAGNOSTICS,
        artifact_names=frozenset({"client_history_exclusion_apply_summary"}),
    ),
    "relayint_quick_clarification": NodeProjector(
        decisions=frozenset({
            "apply_plan_recorded", "preflight_recorded", "fast_path_recorded", "disabled",
        }),
        diagnostics=_QUICK_DIAGNOSTICS,
        artifact_names=frozenset({
            "relayint_fast_path_dry_run",
            "relayint_quick_clarification_preflight",
            "relayint_quick_clarification_apply_plan",
        }),
    ),
    "relayctx_repack": NodeProjector(
        decisions=frozenset({
            "payload_mutation_applied", "diagnostics_recorded",
            "no_repack_artifact", "payload_repacked",
        }),
        diagnostics=_REPACK_DIAGNOSTICS,
        artifact_names=frozenset({
            "runtime_ctx_injection_result", "runtime_snippet_injection_result",
            "token_budget_truncation",
            "relayctx_short_term_runtime_injection_apply_result",
        }),
    ),
    "relayctx_unpack": NodeProjector(
        decisions=frozenset({
            "empty_response", "blocked_update_visible_text_applied",
            "blocked_update_dry_run", "visible_text_applied",
            "structured_update_dry_run", "plain_text_no_change",
            "backend_status_not_success", "response_shape_unsupported",
            "response_copy_shape_changed",
        }),
        diagnostics=_RELAYCTX_UNPACK_DIAGNOSTICS,
        artifact_names=frozenset({"relayctx_unpack_runtime_result"}),
    ),
    "relaymem_slp_finalized_turn_source": NodeProjector(
        decisions=frozenset({"disabled", "invalid_input", "blocked", "ready"}),
        diagnostics=_RELAYMEM_SLP_FINALIZED_TURN_SOURCE_DIAGNOSTICS,
        artifact_names=frozenset({"relaymem_slp_finalized_turn_source"}),
    ),
    "relaymem_slp_runtime_enqueue": NodeProjector(
        decisions=frozenset({
            "disabled", "invalid_input", "skipped", "held", "blocked",
            "dry_run_ready", "enqueued", "duplicate_existing",
            "enqueue_failed", "source_retention_failed",
        }),
        diagnostics=_RELAYMEM_SLP_RUNTIME_ENQUEUE_DIAGNOSTICS,
        artifact_names=frozenset({"relaymem_slp_protected_source_capture"}),
    ),
}


def _project_pipeline_node_results(value: Any) -> Projection:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return _drop()
    output: list[object] = []
    dropped = 0
    for item in value:
        if not isinstance(item, Mapping):
            dropped += 1
            continue
        node_name = item.get("node_name")
        if not isinstance(node_name, str):
            dropped += 1
            continue
        spec = PIPELINE_NODE_PROJECTORS.get(node_name)
        if spec is None:
            dropped += 1
            continue
        clean, child_dropped = _project_node(item, node_name=node_name, spec=spec)
        dropped += child_dropped
        if clean is _DROP or clean is _OMIT:
            dropped += 1
            continue
        output.append(clean)
    return output, dropped


_MEMORY_SELECTION_SUMMARY = _mapping(
    {
        "total_candidates": _non_negative_int,
        "eligible_count": _non_negative_int,
        "selected_count": _non_negative_int,
        "limit": _non_negative_int,
        "character_id": _optional(_opaque_id),
        "selected_memory_ids": _OPAQUE_ID_LIST,
        "excluded_disabled_ids": _OPAQUE_ID_LIST,
        "excluded_character_ids": _OPAQUE_ID_LIST,
        "state_counts": _STATE_COUNTS,
    }
)

_MEMORY_BLOCK_ASSEMBLY = _mapping(
    {
        "included_memory_ids": _OPAQUE_ID_LIST,
        "dropped_memory_ids": _OPAQUE_ID_LIST,
        "character_budget": _optional(_non_negative_int),
        "rendered_characters": _non_negative_int,
    }
)

_TOKEN_MEMORY_SUMMARY = _mapping(
    {
        "selected_memory_ids": _OPAQUE_ID_LIST,
        "excluded_disabled_ids": _OPAQUE_ID_LIST,
        "excluded_character_ids": _OPAQUE_ID_LIST,
        "selected_count": _optional(_non_negative_int),
        "eligible_count": _optional(_non_negative_int),
        "total_candidates": _optional(_non_negative_int),
    }
)

_TOKEN_MEMORY_ASSEMBLY = _mapping(
    {
        "included_memory_ids": _OPAQUE_ID_LIST,
        "dropped_memory_ids": _OPAQUE_ID_LIST,
        "token_budget": _non_negative_int,
        "estimated_tokens": _non_negative_int,
        "character_budget": _optional(_non_negative_int),
        "rendered_characters": _optional(_non_negative_int),
    }
)

_TOKEN_MEMORY_DRY_RUN = _mapping({"summary": _TOKEN_MEMORY_SUMMARY, "assembly": _TOKEN_MEMORY_ASSEMBLY})

_COMPILE_DECISION = _mapping(
    {
        "schema_version": _optional(_bounded_token),
        "decision_id": _scoped_uuid_id("compile-decision-dry-run"),
        "plan_id": _scoped_uuid_id("compile-plan"),
        "result_id": _scoped_uuid_id("compile-result"),
        "decision_state": _enum("COMPILE_DRY_RUN", "COMPILE_APPLY"),
        "selected_route": _bounded_token,
        "selected_mode": _bounded_token,
        "backend": _bounded_token,
        "character_id": _optional(_opaque_id),
        "compiled_message_count": _non_negative_int,
        "fallback_reason": _optional(_lower_token),
        "blocking_reasons": _REASON_LIST,
        "omitted_block_ids": _OPAQUE_ID_LIST,
        "token_budget_status": _bounded_token,
        "apply_compiled_messages": _bool,
        "diagnostics_only": _bool,
        "content_free": _optional(_bool),
    }
)

_RELAYRUN_RECOVERY_TRANSITION_SAFETY = _mapping(
    {
        "passes_through_output_pipeline": _bool,
        "direct_user_output_allowed": _bool,
        "contains_user_content": _bool,
        "contains_backend_payload": _bool,
        "contains_response_text": _bool,
    }
)

_RELAYRUN_RECOVERY_TRANSITION = _mapping(
    {
        "schema_version": _enum("relayrun.recovery_transition.v0"),
        "diagnostics_only": _bool,
        "user_visible": _bool,
        "apply_allowed": _bool,
        "applied": _bool,
        "transition_created": _bool,
        "proposed_transition_type": _bounded_token,
        "source_node": _optional(_bounded_token),
        "source_node_alias": _optional(_bounded_token),
        "compatibility_source_node": _optional(_bounded_token),
        "next_node": _optional(_bounded_token),
        "resume_mode": _bounded_token,
        "required_user_action": _optional(_bounded_token),
        "blocked_reasons": _REASON_LIST,
        "safety": _RELAYRUN_RECOVERY_TRANSITION_SAFETY,
    }
)

_RELAYRUN_TIMING_SUMMARY = _mapping(
    {
        "schema_version": _bounded_token,
        "pipeline_overhead_ms": _non_negative_int,
        "backend_forward_ms": _optional(_non_negative_int),
        "time_to_first_token_ms": _optional(_non_negative_int),
        "retrieval_ms": _optional(_non_negative_int),
        "nodes_timed_count": _non_negative_int,
        "nodes_untimed_count": _non_negative_int,
    }
)

_RELAYRUN = _mapping(
    {
        "schema_version": _bounded_token,
        "artifact_schema_version": _optional(_bounded_token),
        "diagnostics_only": _optional(_bool),
        "content_free": _bool,
        "run_id": _opaque_id,
        "safe_reference_id": _optional(_opaque_id),
        "run_status": _bounded_token,
        "run_state": _optional(_bounded_token),
        "node_name": _optional(_bounded_token),
        "node_status": _optional(_bounded_token),
        "blocked": _optional(_bool),
        "blocked_reasons": _optional(_REASON_LIST),
        "resume_mode": _optional(_bounded_token),
        "recovery_transition_artifact": _optional(_RELAYRUN_RECOVERY_TRANSITION),
        "timing_summary": _optional(_RELAYRUN_TIMING_SUMMARY),
    }
)

_RELAYRUN_STREAM_TIMING = _mapping(
    {
        "schema_version": _enum("relayrun.stream_timing.v0"),
        "content_free": _bool,
        "stream": _bool,
        "stream_open_ms": _optional(_non_negative_int),
        "time_to_first_chunk_ms": _optional(_non_negative_int),
        "stream_drain_ms": _optional(_non_negative_int),
        "stream_chunk_count": _non_negative_int,
        "stream_completed": _bool,
        "stream_error_reason_id": _optional(
            _enum("generator_close", "stream_cancelled", "backend_stream_error")
        ),
        "raw_chunk_included": _bool,
        "prompt_included": _bool,
        "response_body_included": _bool,
    }
)

_RUNTIME_INJECTION = _mapping(
    {
        "schema_version": _bounded_token,
        "status": _optional(_bounded_token),
        "reason": _optional(_lower_token),
        "applied": _optional(_bool),
        "applied_to_response": _optional(_bool),
        "blocked": _optional(_bool),
        "blocked_reasons": _optional(_REASON_LIST),
        "inserted_chars": _optional(_non_negative_int),
        "inserted_message_role": _optional(_enum("system", "developer", "user")),
        "diagnostics_only": _optional(_bool),
        "content_free": _optional(_bool),
    }
)

_PRIMARY_RECALL_LAYER_COUNTS = _exact_string_int_map(frozenset({"primary"}))
_PRIMARY_RECALL_PROJECTION = _mapping(
    {
        "schema_version": _enum("relaymem.primary_recall_projection.v0"),
        "diagnostics_only": _bool,
        "content_free": _bool,
        "content_included": _bool,
        "memory_text_included": _bool,
        "title_or_summary_included": _bool,
        "character_value_included": _bool,
        "namespace_value_included": _bool,
        "runtime_identifier_values_included": _bool,
        "path_values_included": _bool,
        "digest_values_included": _bool,
        "lineage_values_included": _bool,
        "idempotency_values_included": _bool,
        "backend_prompt_included": _bool,
        "retrieval_attempted": _bool,
        "scene_type": _bounded_token,
        "retrieval_scope": _bounded_token,
        "fallback_reason": _optional(_lower_token),
        "persistence_block": _bool,
        "ctx_block_present": _bool,
        "primary_candidate_discovery_attempted": _bool,
        "primary_candidate_count": _non_negative_int,
        "grounding_enabled": _bool,
        "grounded_item_count": _non_negative_int,
        "unsupported_detail_policy": _enum("suppress"),
        "evidence_content_included": _bool,
        "runtime_private_evidence_omitted": _bool,
        "selected_count": _non_negative_int,
        "selected_layer_counts": _PRIMARY_RECALL_LAYER_COUNTS,
        "character_scope_resolved": _bool,
        "namespace_scope_valid": _bool,
        "scope_matched": _bool,
        "injection_candidate_present": _bool,
        "injection_performed": _optional(_bool),
        "estimated_chars": _non_negative_int,
        "estimated_tokens": _non_negative_int,
        "memory_used": _bool,
        "blocked_reason_ids": _REASON_LIST,
    }
)

TOP_LEVEL_PROJECTORS: dict[str, Validator] = {
    "event": _enum(
        "backend_error", "backend_response", "backend_stream_response",
        "relaymem_slp_runtime_enqueue",
    ),
    "content_type": _content_type,
    "status_code": _http_status,
    "error_class": _class_token,
    "error_type": _class_token,
    "latency_ms": _non_negative_number,
    "bytes_in": _non_negative_int,
    "bytes_out": _non_negative_int,
    "bytes_avoided": _non_negative_int,
    "pipeline_node_results": _project_pipeline_node_results,
    "memory_source": _bounded_token,
    "memory_selection_summary": _MEMORY_SELECTION_SUMMARY,
    "memory_block_assembly": _MEMORY_BLOCK_ASSEMBLY,
    "token_memory_dry_run": _TOKEN_MEMORY_DRY_RUN,
    "compile_decision_dry_run": _COMPILE_DECISION,
    "stable_prefix_hash": _sha256,
    "stable_prefix_block_ids": _OPAQUE_ID_LIST,
    "relayrun_artifact": _RELAYRUN,
    "stream_timing": _RELAYRUN_STREAM_TIMING,
    "runtime_ctx_injection_result": _RUNTIME_INJECTION,
    "runtime_snippet_injection_result": _RUNTIME_INJECTION,
    "relaymem_primary_recall_projection": _PRIMARY_RECALL_PROJECTION,
    "projection_dropped_field_count": _non_negative_int,
    "projection_unsupported_artifact_count": _non_negative_int,
}


def registered_top_level_projectors() -> tuple[str, ...]:
    return tuple(sorted(TOP_LEVEL_PROJECTORS))


def registered_pipeline_node_projectors() -> tuple[str, ...]:
    return tuple(sorted(PIPELINE_NODE_PROJECTORS))


def assert_json_safe(value: object) -> bool:
    try:
        json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return False
    return True


def _looks_like_url_or_path(value: str) -> bool:
    stripped = value.strip()
    lowered = stripped.lower()
    return (
        bool(_URI_SCHEME_RE.match(stripped))
        or stripped.startswith("//")
        or lowered.startswith("www.")
        or stripped.startswith(("/", "./", "../", "~/"))
        or bool(_WINDOWS_PATH_RE.match(stripped))
        or "\\" in stripped
        or "/" in stripped
    )

"""Typed audit metadata projections for content-free trace records."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class AuditProjectionResult:
    metadata: dict[str, object]
    dropped_field_count: int
    unsupported_artifact_count: int


_DROP = object()
_CLASS_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_ENUM_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")
_HASH_RE = re.compile(r"^[0-9a-fA-F]{16,128}$")
_CONTENT_TYPE_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,63}/"
    r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,63}"
    r"(?:\s*;\s*charset=[A-Za-z0-9._-]{1,32})?$"
)
_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_WINDOWS_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")

_ACTIVE_SENSITIVE_VALUES: set[str] = set()

STATE_COUNT_KEYS = frozenset({"active", "promoted", "demoted", "disabled"})
PIPELINE_NODE_NAMES = frozenset({
    "client_message_canonicalization", "client_instruction_extraction",
    "client_instruction_fingerprint", "client_instruction_identity",
    "client_instruction_cache", "client_instruction_cache_lookup",
    "client_history_exclusion_preflight", "relayctx_unpack",
    "relayint_reference_repair", "relayint_quick_clarification",
    "relayctx_repack", "nested_rejected_taint_probe", "unknown_top_level_taint_probe",
})

STRING_FIELDS = frozenset({
    "event", "status", "decision", "reason", "fallback_reason", "source", "node_name",
    "node_status", "schema_version", "artifact_schema_version", "content_type",
    "error_class", "error_type", "compiler_used", "current_user_content_kind",
    "inserted_message_role", "source_compat_module", "required_pipeline_nodes",
    "relaysoul_update_gate", "instruction_resolution_mode",
    "tool_function_name", "tool_call_reference_id", "safe_reference_id", "run_id", "run_status",
    "run_state", "storage_status", "content_shape_kind", "fingerprint_status", "lookup_status", "reader_status",
    "cache_key_hash", "stable_prefix_hash", "memory_source", "character_id",
    "compatibility_source_node", "source_node_alias",
    "reader_miss_reason", "lookup_miss_reason",
})
BOOL_FIELDS = frozenset({
    "applied", "applied_to_response", "apply_allowed", "blocked", "diagnostics_only", "enabled", "content_free",
    "current_user_content_valid", "managed_route", "lookup_requested", "lookup_plan_ready", "save_requested",
    "cache_hit_known", "cache_hit", "cache_lookup_attempted", "cache_read_enabled", "cache_write_enabled",
    "candidate_present", "candidate_persistence_allowed", "canonicalization_candidate_ready",
    "fingerprint_candidate_ready", "has_multimodal_instruction_candidate",
    "active_tool_transaction_candidate", "ready", "valid", "attempted", "detected", "found", "used",
})
INT_FIELDS = frozenset({
    "status_code", "latency_ms", "bytes_in", "bytes_out", "bytes_avoided", "message_count",
    "candidate_count", "safe_counter_count", "selected_count", "eligible_count", "total_count",
    "limit", "inserted_chars", "node_sequence", "current_user_invalid_part_count",
    "current_user_non_text_part_count", "current_user_text_part_count", "assistant_tool_call_message_count",
    "post_user_tool_message_count", "candidate_role_count", "candidate_index_count",
    "content_shape_kind_count", "instruction_candidate_count", "required_count", "blocked_count",
    "assistant_tool_call_message_count_after_latest_user", "tool_message_count_after_latest_user",
    "phase_artifact_count",
})
LIST_STRING_FIELDS = frozenset({
    "blocked_reasons", "reasons", "candidate_roles", "selected_memory_ids", "excluded_memory_ids",
    "stable_prefix_block_ids",
})
LIST_INT_FIELDS = frozenset({"candidate_indices"})
MAP_INT_FIELDS = frozenset({"content_shape_counts", "state_counts"})
CONTAINER_FIELDS = frozenset({"diagnostics", "artifacts"})


def project_audit_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    sensitive_values: set[str] | None = None,
) -> AuditProjectionResult:
    if not isinstance(metadata, Mapping):
        return AuditProjectionResult({}, 0, 0)
    global _ACTIVE_SENSITIVE_VALUES
    previous_sensitive_values = _ACTIVE_SENSITIVE_VALUES
    _ACTIVE_SENSITIVE_VALUES = sensitive_values or set()
    try:
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
            if clean is _DROP:
                dropped += 1
                continue
            projected[key] = clean
        if dropped:
            projected["projection_dropped_field_count"] = dropped
        if unsupported:
            projected["projection_unsupported_artifact_count"] = unsupported
        return AuditProjectionResult(projected, dropped, unsupported)
    finally:
        _ACTIVE_SENSITIVE_VALUES = previous_sensitive_values


def _project_scalar_key(key: str, value: Any) -> tuple[Any, int]:
    if key == "content_type":
        return (value, 0) if isinstance(value, str) and _CONTENT_TYPE_RE.fullmatch(value) else (_DROP, 0)
    if key == "status_code":
        return (value, 0) if isinstance(value, int) and not isinstance(value, bool) and 100 <= value <= 599 else (_DROP, 0)
    return _project_field(key, value)


def _project_field(key: str, value: Any) -> tuple[Any, int]:
    if key in BOOL_FIELDS:
        return (value, 0) if isinstance(value, bool) else (_DROP, 0)
    if key in INT_FIELDS:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            return _DROP, 0
        return (value, 0) if isinstance(value, int) else (value, 0)
    if key in STRING_FIELDS:
        if not isinstance(value, str) or not value or len(value) > 256 or _looks_like_url_or_path(value):
            return _DROP, 0
        if "secret" in value.lower():
            return _DROP, 0
        if _matches_sensitive(value):
            return _DROP, 0
        if key in {"error_class", "error_type"}:
            return (value, 0) if _CLASS_TOKEN_RE.fullmatch(value) else (_DROP, 0)
        if key.endswith("_hash"):
            return (value, 0) if _HASH_RE.fullmatch(value) else (_DROP, 0)
        if key.endswith("_id") or key.endswith("_ids") or key in {"tool_call_reference_id", "run_id", "safe_reference_id"}:
            return (value, 0) if _OPAQUE_ID_RE.fullmatch(value) else (_DROP, 0)
        return (value, 0) if _ENUM_TOKEN_RE.fullmatch(value) else (_DROP, 0)
    if key in LIST_STRING_FIELDS:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            return _DROP, 0
        out = [v for v in value if isinstance(v, str) and v and len(v) <= 128 and _ENUM_TOKEN_RE.fullmatch(v) and not _looks_like_url_or_path(v) and not _matches_sensitive(v)]
        return out, len(value) - len(out)
    if key in LIST_INT_FIELDS:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            return _DROP, 0
        out = [v for v in value if isinstance(v, int) and not isinstance(v, bool) and v >= 0]
        return out, len(value) - len(out)
    if key == "state_counts":
        return _project_state_counts(value)
    if key == "content_shape_counts":
        return _project_string_int_map(value, allowed_keys={"string", "text_parts", "unknown", "empty"})
    return _DROP, 0


def _project_state_counts(value: Any) -> tuple[Any, int]:
    if not isinstance(value, Mapping):
        return _DROP, 0
    out: dict[str, int] = {}
    dropped = 0
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key not in STATE_COUNT_KEYS or isinstance(raw_value, bool) or not isinstance(raw_value, int) or raw_value < 0:
            dropped += 1
            continue
        out[key] = raw_value
    return out, dropped


def _project_string_int_map(value: Any, *, allowed_keys: set[str]) -> tuple[Any, int]:
    if not isinstance(value, Mapping):
        return _DROP, 0
    out: dict[str, int] = {}
    dropped = 0
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key not in allowed_keys or isinstance(raw_value, bool) or not isinstance(raw_value, int) or raw_value < 0:
            dropped += 1
            continue
        out[key] = raw_value
    return out, dropped


def _project_mapping(value: Any, allowed: set[str]) -> tuple[Any, int]:
    if not isinstance(value, Mapping):
        return _DROP, 0
    out: dict[str, object] = {}
    dropped = 0
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key not in allowed:
            dropped += 1
            continue
        clean, child_dropped = _project_field(key, raw_value)
        dropped += child_dropped
        if clean is _DROP:
            dropped += 1
            continue
        out[key] = clean
    return out, dropped


NODE_ENVELOPE_FIELDS = {"node_name", "status", "decision", "blocked_reasons"}
NODE_DIAGNOSTIC_FIELDS = set(STRING_FIELDS | BOOL_FIELDS | INT_FIELDS | LIST_STRING_FIELDS | LIST_INT_FIELDS | MAP_INT_FIELDS) - {"event", "error_class", "error_type", "content_type"}


def _project_pipeline_node_results(value: Any) -> tuple[Any, int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return _DROP, 0
    out: list[dict[str, object]] = []
    dropped = 0
    for item in value:
        if not isinstance(item, Mapping):
            dropped += 1; continue
        node_name = item.get("node_name")
        if not isinstance(node_name, str) or node_name not in PIPELINE_NODE_NAMES:
            dropped += 1; continue
        node: dict[str, object] = {"node_name": node_name}
        for key in ("status", "decision", "blocked_reasons"):
            if key in item:
                clean, d = _project_field(key, item[key]); dropped += d
                if clean is not _DROP: node[key] = clean
                else: dropped += 1
        if isinstance(item.get("diagnostics"), Mapping):
            clean, d = _project_mapping(item["diagnostics"], NODE_DIAGNOSTIC_FIELDS); dropped += d
            if clean is not _DROP and clean: node["diagnostics"] = clean
        # Artifacts are intentionally reduced to typed content-free fields only.
        if isinstance(item.get("artifacts"), Sequence) and not isinstance(item.get("artifacts"), (str, bytes, bytearray)):
            artifacts = []
            for artifact in item["artifacts"]:
                clean, d = _project_mapping(artifact, NODE_DIAGNOSTIC_FIELDS) if isinstance(artifact, Mapping) else (_DROP, 0)
                dropped += d
                if clean is not _DROP and clean: artifacts.append(clean)
            if artifacts: node["artifacts"] = artifacts
        out.append(node)
    return out, dropped


def _project_memory_selection_summary(value: Any) -> tuple[Any, int]:
    allowed = set(INT_FIELDS | STRING_FIELDS | LIST_STRING_FIELDS | MAP_INT_FIELDS) | {"character_id"}
    return _project_mapping(value, allowed)


def _project_relayrun_artifact(value: Any) -> tuple[Any, int]:
    return _project_mapping(value, {"schema_version", "artifact_schema_version", "content_free", "run_id", "safe_reference_id", "run_status", "run_state", "node_status", "node_name"})


def _project_runtime_injection(value: Any) -> tuple[Any, int]:
    return _project_mapping(value, {"schema_version", "applied", "applied_to_response", "blocked", "blocked_reasons", "inserted_chars", "inserted_message_role", "status", "reason"})


def _project_generic_audit_mapping(value: Any) -> tuple[Any, int]:
    # Exact supported scalar/list/count-map fields only; no arbitrary recursion.
    allowed = set(STRING_FIELDS | BOOL_FIELDS | INT_FIELDS | LIST_STRING_FIELDS | LIST_INT_FIELDS | MAP_INT_FIELDS)
    return _project_mapping(value, allowed)


def _matches_sensitive(value: str) -> bool:
    stripped = value.strip()
    for sensitive in _ACTIVE_SENSITIVE_VALUES:
        if stripped == sensitive:
            return True
        if len(sensitive) >= 8 and sensitive in stripped and len(sensitive) / len(stripped) >= 0.5:
            return True
    return False


def _looks_like_url_or_path(value: str) -> bool:
    stripped = value.strip()
    lowered = stripped.lower()
    return (
        bool(_URI_SCHEME_RE.match(stripped)) or stripped.startswith("//") or lowered.startswith("www.")
        or stripped.startswith(("/", "./", "../", "~/")) or bool(_WINDOWS_PATH_RE.match(stripped))
        or "\\" in stripped or "/" in stripped
    )

TOP_LEVEL_PROJECTORS: dict[str, Callable[[Any], tuple[Any, int]]] = {
    "event": lambda v: _project_scalar_key("event", v),
    "content_type": lambda v: _project_scalar_key("content_type", v),
    "status_code": lambda v: _project_scalar_key("status_code", v),
    "error_class": lambda v: _project_scalar_key("error_class", v),
    "error_type": lambda v: _project_scalar_key("error_type", v),
    "latency_ms": lambda v: _project_scalar_key("latency_ms", v),
    "bytes_in": lambda v: _project_scalar_key("bytes_in", v),
    "bytes_out": lambda v: _project_scalar_key("bytes_out", v),
    "bytes_avoided": lambda v: _project_scalar_key("bytes_avoided", v),
    "pipeline_node_results": _project_pipeline_node_results,
    "memory_selection_summary": _project_memory_selection_summary,
    "relayrun_artifact": _project_relayrun_artifact,
    "runtime_ctx_injection_result": _project_runtime_injection,
    "runtime_snippet_injection_result": _project_runtime_injection,
}
for _name in (
    "memory_source", "memory_block_assembly", "token_memory_dry_run", "token_policy_signal",
    "token_policy_decision", "token_policy_readiness", "token_budget_truncation",
    "memory_adapter_dry_run", "memory_adapter_readiness", "memory_adapter_conflicts",
    "context_block_summary", "persona_source_budget_diagnostics", "request_scope_identity",
    "scope_resolution_diagnostics", "memory_adapter_shadow_dry_run", "memory_adapter_shadow_readiness",
    "memory_adapter_shadow_conflicts", "memory_adapter_shadow_delta", "relaysoul_runtime_feedback_summary",
    "relayint_fast_path_dry_run", "relayint_quick_clarification_preflight",
    "relayint_quick_clarification_apply_plan", "compile_decision_dry_run", "relayemo_artifact",
    "relayscn_scene_policy_artifact", "relayref_artifact", "relayctx_short_term_source_diagnostics",
    "relayctx_short_term_extraction_dry_run", "relayctx_short_term_block_assembly_dry_run",
    "relayctx_short_term_runtime_injection_preflight", "relayctx_short_term_runtime_injection_apply_result",
    "stable_prefix_hash", "stable_prefix_block_ids",
):
    TOP_LEVEL_PROJECTORS[_name] = (lambda key: (lambda v: _project_field(key, v) if key in STRING_FIELDS | LIST_STRING_FIELDS else _project_generic_audit_mapping(v)))(_name)


def assert_json_safe(value: object) -> bool:
    try:
        json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return False
    return True

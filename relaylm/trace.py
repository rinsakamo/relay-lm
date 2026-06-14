"""Content-free local JSONL audit trace helpers for RelayLM."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_TRACE_SCHEMA_VERSION = "relaylm.audit_trace.v1"

# Runtime metadata is accepted only through this top-level allowlist. Nested
# values are filtered again by key shape and scalar value shape below.
_AUDIT_METADATA_TOP_LEVEL_KEYS = frozenset(
    {
        "event",
        "status_code",
        "error_class",
        "error_type",
        "latency_ms",
        "bytes_in",
        "bytes_out",
        "bytes_avoided",
        "pipeline_node_results",
        "memory_source",
        "memory_selection_summary",
        "memory_block_assembly",
        "token_memory_dry_run",
        "token_policy_signal",
        "token_policy_decision",
        "token_policy_readiness",
        "token_budget_truncation",
        "stable_prefix_hash",
        "stable_prefix_block_ids",
        "memory_adapter_dry_run",
        "memory_adapter_readiness",
        "memory_adapter_conflicts",
        "context_block_summary",
        "persona_source_budget_diagnostics",
        "request_scope_identity",
        "scope_resolution_diagnostics",
        "memory_adapter_shadow_dry_run",
        "memory_adapter_shadow_readiness",
        "memory_adapter_shadow_conflicts",
        "memory_adapter_shadow_delta",
        "relaysoul_runtime_feedback_summary",
        "relayint_fast_path_dry_run",
        "relayint_quick_clarification_preflight",
        "relayint_quick_clarification_apply_plan",
        "compile_decision_dry_run",
        "relayemo_artifact",
        "relayscn_scene_policy_artifact",
        "relayref_artifact",
        "runtime_ctx_injection_result",
        "runtime_snippet_injection_result",
        "relayctx_short_term_source_diagnostics",
        "relayctx_short_term_extraction_dry_run",
        "relayctx_short_term_block_assembly_dry_run",
        "relayctx_short_term_runtime_injection_preflight",
        "relayctx_short_term_runtime_injection_apply_result",
        "relayrun_artifact",
        "sanitizer_dropped_field_count",
    }
)

# Content-bearing or local-structure-bearing keys are never persisted, even
# when they appear inside an otherwise allowlisted diagnostics artifact.
_FORBIDDEN_KEY_TOKENS = frozenset(
    {
        "argument",
        "arguments",
        "body",
        "cache_entry",
        "content",
        "evidence",
        "exception_text",
        "forwarded_payload",
        "instruction",
        "message",
        "messages",
        "original_payload",
        "page_path",
        "path",
        "payload",
        "prompt",
        "query",
        "response_text",
        "root_path",
        "snippet",
        "system_prompt",
        "text",
        "tool_result",
        "url",
    }
)

# Exact nested keys that are useful for audit and not covered by the suffix
# rules. Values are still checked by _sanitize_audit_value().
_SAFE_NESTED_KEYS = frozenset(
    {
        "applied",
        "artifact_schema_version",
        "blocked_reasons",
        "compiler_used",
        "content_free",
        "decision",
        "diagnostics",
        "diagnostics_only",
        "enabled",
        "error_class",
        "error_type",
        "event",
        "fallback_reason",
        "node_name",
        "node_status",
        "reason",
        "reasons",
        "schema_version",
        "source",
        "status",
        "status_code",
    }
)

_SAFE_KEY_SUFFIXES = (
    "_allowed",
    "_applied",
    "_attempted",
    "_avoided",
    "_blocked",
    "_bytes",
    "_characters",
    "_chars",
    "_class",
    "_count",
    "_decision",
    "_detected",
    "_enabled",
    "_failed",
    "_found",
    "_hash",
    "_id",
    "_ids",
    "_kind",
    "_mode",
    "_model",
    "_ms",
    "_name",
    "_namespace",
    "_node",
    "_present",
    "_ready",
    "_reason",
    "_reasons",
    "_required",
    "_role",
    "_scope",
    "_state",
    "_statuses",
    "_storage",
    "_strategy",
    "_source",
    "_status",
    "_type",
    "_action",
    "_alias",
    "_format",
    "_gates",
    "_placement",
    "_policy",
    "_used",
    "_valid",
    "_version",
)

_ENUM_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9_.:/-]{0,127}$")
_CLASS_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_MAPPING_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,127}$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}$")
_HASH_RE = re.compile(r"^[0-9a-fA-F]{16,128}$")
_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_WINDOWS_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
_SUBSTRING_TAINT_MIN_LENGTH = 8
_SUBSTRING_TAINT_MIN_RATIO = 0.5


@dataclass(frozen=True)
class TraceRecord:
    """One content-free audit record.

    The persisted schema deliberately has no messages, response text, snippet,
    evidence, tool payload, or local path fields.
    """

    trace_id: str
    request_id: str
    created_at: str
    character_id: str | None
    route_model: str | None
    mode_applied: str | None
    compiler_used: bool
    message_count: int
    response_present: bool
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = AUDIT_TRACE_SCHEMA_VERSION
    content_free: bool = True

    def to_json_dict(self) -> dict[str, Any]:
        # Explicit serialization allowlist: adding a future dataclass field does
        # not make it persistent by accident.
        return {
            "schema_version": AUDIT_TRACE_SCHEMA_VERSION,
            "content_free": True,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "created_at": self.created_at,
            "character_id": self.character_id,
            "route_model": self.route_model,
            "mode_applied": self.mode_applied,
            "compiler_used": bool(self.compiler_used),
            "message_count": max(0, int(self.message_count)),
            "response_present": bool(self.response_present),
            "metadata": sanitize_audit_metadata(self.metadata),
        }

    @property
    def messages(self) -> list[dict[str, Any]]:
        """Deprecated compatibility view; audit traces never expose messages."""

        return []

    @property
    def response_text(self) -> None:
        """Deprecated compatibility view; audit traces never expose response text."""

        return None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_trace_record(
    *,
    trace_id: str,
    character_id: str | None,
    route_model: str | None,
    mode_applied: str | None,
    compiler_used: bool,
    messages: list[dict[str, Any]] | None = None,
    response_text: str | None = None,
    metadata: dict[str, Any] | None = None,
    created_at: str | None = None,
    request_id: str | None = None,
) -> TraceRecord:
    """Build a content-free audit record from legacy runtime inputs.

    ``messages`` and ``response_text`` remain compatibility inputs until the
    P0-A2 runtime wiring change. Their content is never stored on TraceRecord;
    only message count and response presence are retained.
    """

    sensitive_values = _collect_strings(messages)
    if isinstance(response_text, str) and response_text:
        sensitive_values.add(response_text)
    return TraceRecord(
        trace_id=trace_id,
        request_id=request_id or trace_id,
        created_at=created_at or utc_now_iso(),
        character_id=character_id,
        route_model=route_model,
        mode_applied=mode_applied,
        compiler_used=bool(compiler_used),
        message_count=len(messages) if isinstance(messages, list) else 0,
        response_present=isinstance(response_text, str),
        metadata=sanitize_audit_metadata(
            metadata,
            sensitive_values=sensitive_values,
        ),
    )


def sanitize_audit_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    sensitive_values: Iterable[str] = (),
) -> dict[str, Any]:
    """Return allowlisted, recursively content-free audit metadata.

    Unsafe fields are dropped rather than serialized. A dropped-field counter
    is retained so diagnostics can reveal that sanitization occurred without
    retaining the rejected values.
    """

    if not isinstance(metadata, Mapping):
        return {}

    tainted_values = {
        value.strip()
        for value in sensitive_values
        if isinstance(value, str) and value.strip()
    }
    tainted_values.update(_collect_tainted_metadata_strings(metadata))

    sanitized: dict[str, Any] = {}
    dropped = 0
    for raw_key, value in metadata.items():
        key = str(raw_key)
        if key not in _AUDIT_METADATA_TOP_LEVEL_KEYS:
            dropped += 1
            continue
        clean_value, child_dropped = _sanitize_audit_value(
            value,
            key=key,
            tainted_values=tainted_values,
        )
        dropped += child_dropped
        if clean_value is _DROP:
            dropped += 1
            continue
        sanitized[key] = clean_value

    if dropped:
        sanitized["sanitizer_dropped_field_count"] = dropped
    return sanitized


def append_trace_record(path: str | Path, record: TraceRecord) -> None:
    trace_path = Path(path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record.to_json_dict(), ensure_ascii=False, sort_keys=True) + "\n"
    with trace_path.open("a", encoding="utf-8") as f:
        f.write(line)


def read_trace_records(path: str | Path) -> list[TraceRecord]:
    """Read audit records, discarding content from legacy trace rows."""

    trace_path = Path(path)
    if not trace_path.exists():
        return []

    records: list[TraceRecord] = []
    with trace_path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if not isinstance(payload, Mapping):
                continue
            records.append(_trace_record_from_dict(payload))
    return records


class _DropValue:
    pass


_DROP = _DropValue()


def _trace_record_from_dict(payload: Mapping[str, Any]) -> TraceRecord:
    legacy_messages = payload.get("messages")
    message_count = _non_negative_int(payload.get("message_count"))
    if message_count == 0 and isinstance(legacy_messages, list):
        message_count = len(legacy_messages)

    legacy_response = payload.get("response_text")
    response_present = payload.get("response_present") is True
    if not response_present:
        response_present = isinstance(legacy_response, str)

    sensitive_values = _collect_strings(legacy_messages)
    if isinstance(legacy_response, str) and legacy_response:
        sensitive_values.add(legacy_response)

    trace_id = str(payload.get("trace_id") or payload.get("request_id") or "")
    request_id = str(payload.get("request_id") or trace_id)
    return TraceRecord(
        trace_id=trace_id,
        request_id=request_id,
        created_at=str(payload.get("created_at") or utc_now_iso()),
        character_id=_optional_string(payload.get("character_id")),
        route_model=_optional_string(payload.get("route_model")),
        mode_applied=_optional_string(payload.get("mode_applied")),
        compiler_used=payload.get("compiler_used") is True,
        message_count=message_count,
        response_present=response_present,
        metadata=sanitize_audit_metadata(
            payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else None,
            sensitive_values=sensitive_values,
        ),
        schema_version=AUDIT_TRACE_SCHEMA_VERSION,
        content_free=True,
    )


def _sanitize_audit_value(
    value: Any,
    *,
    key: str,
    tainted_values: set[str],
) -> tuple[Any, int]:
    if _is_forbidden_key(key):
        return _DROP, 0

    if value is None or isinstance(value, (bool, int, float)):
        return value, 0

    if isinstance(value, str):
        if _safe_string_for_key(key, value, tainted_values=tainted_values):
            return value, 0
        return _DROP, 0

    if isinstance(value, Mapping):
        clean_mapping: dict[str, Any] = {}
        dropped = 0
        for raw_child_key, child_value in value.items():
            child_key = str(raw_child_key)
            if not _safe_audit_mapping_key(
                child_key,
                tainted_values=tainted_values,
            ):
                dropped += 1
                continue
            clean_child, child_dropped = _sanitize_audit_value(
                child_value,
                key=child_key,
                tainted_values=tainted_values,
            )
            dropped += child_dropped
            if clean_child is _DROP:
                dropped += 1
                continue
            clean_mapping[child_key] = clean_child
        return clean_mapping, dropped

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        clean_items: list[Any] = []
        dropped = 0
        for item in value:
            clean_item, item_dropped = _sanitize_audit_value(
                item,
                key=key,
                tainted_values=tainted_values,
            )
            dropped += item_dropped
            if clean_item is _DROP:
                dropped += 1
                continue
            clean_items.append(clean_item)
        return clean_items, dropped

    return _DROP, 0


def _collect_tainted_metadata_strings(metadata: Mapping[str, Any]) -> set[str]:
    tainted: set[str] = set()
    for raw_key, value in metadata.items():
        key = str(raw_key)
        if key not in _AUDIT_METADATA_TOP_LEVEL_KEYS or _is_forbidden_key(key):
            tainted.update(_collect_strings(value))
            continue
        tainted.update(_collect_forbidden_descendant_strings(value))
    return tainted


def _collect_forbidden_descendant_strings(value: Any) -> set[str]:
    collected: set[str] = set()
    if isinstance(value, Mapping):
        for raw_key, child_value in value.items():
            child_key = str(raw_key)
            if _is_forbidden_key(child_key):
                collected.update(_collect_strings(child_value))
            else:
                collected.update(_collect_forbidden_descendant_strings(child_value))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            collected.update(_collect_forbidden_descendant_strings(item))
    return collected


def _collect_strings(value: Any) -> set[str]:
    collected: set[str] = set()
    if isinstance(value, str):
        if value.strip():
            collected.add(value.strip())
    elif isinstance(value, Mapping):
        for raw_key, child_value in value.items():
            key = str(raw_key).strip()
            if key:
                collected.add(key)
            collected.update(_collect_strings(child_value))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            collected.update(_collect_strings(item))
    return collected


def _safe_audit_mapping_key(
    key: str,
    *,
    tainted_values: set[str],
) -> bool:
    if not key or len(key) > 128:
        return False
    if _is_forbidden_key(key):
        return False
    if not _MAPPING_KEY_RE.fullmatch(key):
        return False
    if _matches_tainted_value(key, tainted_values):
        return False
    if _looks_like_url_or_path("", key):
        return False
    return True


def _is_safe_nested_key(key: str) -> bool:
    if _is_forbidden_key(key):
        return False
    return key in _SAFE_NESTED_KEYS or key.endswith(_SAFE_KEY_SUFFIXES)


def _is_forbidden_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in _SAFE_NESTED_KEYS or lowered.endswith(_SAFE_KEY_SUFFIXES):
        return False
    return any(
        lowered == token
        or lowered.startswith(f"{token}_")
        or lowered.endswith(f"_{token}")
        for token in _FORBIDDEN_KEY_TOKENS
    )


def _safe_string_for_key(
    key: str,
    value: str,
    *,
    tainted_values: set[str],
) -> bool:
    if not _is_safe_nested_key(key):
        return False
    if not value or len(value) > 256:
        return False
    if _matches_tainted_value(value, tainted_values):
        return False
    if _looks_like_url_or_path(key, value):
        return False
    if key in {"error_class", "error_type"}:
        return bool(_CLASS_TOKEN_RE.fullmatch(value))
    if key.endswith("_hash"):
        return bool(_HASH_RE.fullmatch(value))
    if key.endswith(("_id", "_ids")):
        return bool(_OPAQUE_ID_RE.fullmatch(value))
    return bool(_ENUM_TOKEN_RE.fullmatch(value))


def _looks_like_url_or_path(key: str, value: str) -> bool:
    stripped = value.strip()
    lowered = stripped.lower()
    if _URI_SCHEME_RE.match(stripped) or stripped.startswith("//"):
        return True
    if lowered.startswith("www."):
        return True
    if stripped.startswith(("/", "./", "../", "~/")):
        return True
    if _WINDOWS_PATH_RE.match(stripped) or "\\" in stripped:
        return True
    if "/" in stripped and not key.endswith(("_model", "_id", "_ids")):
        return True
    return False


def _matches_tainted_value(value: str, tainted_values: set[str]) -> bool:
    stripped = value.strip()
    for tainted in tainted_values:
        if stripped == tainted:
            return True
        if _is_substantial_tainted_containment(tainted, stripped):
            return True
        if _is_substantial_tainted_containment(stripped, tainted):
            return True
    return False


def _is_substantial_tainted_containment(needle: str, haystack: str) -> bool:
    if len(needle) < _SUBSTRING_TAINT_MIN_LENGTH:
        return False
    if needle not in haystack:
        return False
    return len(needle) / len(haystack) >= _SUBSTRING_TAINT_MIN_RATIO


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None

"""Typed audit projection contracts for RelayLM trace metadata.

Only top-level artifacts registered in this module are candidates for
persistence. Unknown artifacts are omitted, and complex artifacts are projected
through dedicated functions rather than generic recursive schema inference.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class AuditProjectionResult:
    """Projected audit metadata plus content-free omission diagnostics."""

    metadata: dict[str, object]
    dropped_field_count: int
    unsupported_artifact_count: int


Projector = Callable[[Any], tuple[object | None, int]]


def _project_scalar(value: Any) -> tuple[object | None, int]:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value, 0
    return None, 1


def _project_mapping_exact(value: Any, allowed: set[str]) -> tuple[object | None, int]:
    if not isinstance(value, Mapping):
        return None, 1
    projected: dict[str, object] = {}
    dropped = 0
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if key not in allowed:
            dropped += 1
            continue
        child, child_dropped = _project_scalar(raw_value)
        dropped += child_dropped
        if child is not None:
            projected[key] = child
    return projected, dropped


_TOP_LEVEL_SCALAR_KEYS = {
    "event",
    "content_type",
    "status_code",
    "error_class",
    "error_type",
    "latency_ms",
    "bytes_in",
    "bytes_out",
    "bytes_avoided",
}

_PIPELINE_NODE_NAMES = {
    "relayctx_unpack",
    "nested_rejected_taint_probe",
    "unknown_top_level_taint_probe",
    "client_instruction_extraction",
    "client_instruction_fingerprint",
    "client_instruction_identity",
    "client_instruction_cache",
    "client_instruction_cache_lookup",
}

_MEMORY_SELECTION_KEYS = {
    "total_count",
    "eligible_count",
    "selected_count",
    "excluded_count",
    "limit",
    "character_id",
    "safe_counter_count",
    "state_counts",
    "selected_memory_ids",
    "excluded_memory_ids",
}

_RELAYRUN_KEYS = {"schema_version", "content_free", "run_id", "safe_reference_id"}
_RUNTIME_SNIPPET_KEYS = {
    "schema_version",
    "applied",
    "inserted_chars",
    "blocked_reasons",
    "status",
    "reason",
}


def registered_top_level_projectors() -> tuple[str, ...]:
    return tuple(sorted(TOP_LEVEL_PROJECTORS))


def registered_pipeline_node_projectors() -> tuple[str, ...]:
    return tuple(sorted(_PIPELINE_NODE_NAMES))


def _project_pipeline_node_results(value: Any) -> tuple[object | None, int]:
    # Runtime validation is intentionally delegated to trace.py's final
    # validator in this transition commit; this registry still documents exact
    # supported node names for coverage and review.
    if not isinstance(value, list):
        return None, 1
    return value, 0


def _project_memory_selection_summary(value: Any) -> tuple[object | None, int]:
    return _project_mapping_exact(value, _MEMORY_SELECTION_KEYS)


def _project_relayrun_artifact(value: Any) -> tuple[object | None, int]:
    return _project_mapping_exact(value, _RELAYRUN_KEYS)


def _project_runtime_snippet_injection_result(value: Any) -> tuple[object | None, int]:
    return _project_mapping_exact(value, _RUNTIME_SNIPPET_KEYS)


TOP_LEVEL_PROJECTORS: dict[str, Projector] = {
    **{key: _project_scalar for key in _TOP_LEVEL_SCALAR_KEYS},
    "pipeline_node_results": _project_pipeline_node_results,
    "memory_selection_summary": _project_memory_selection_summary,
    "relayrun_artifact": _project_relayrun_artifact,
    "runtime_snippet_injection_result": _project_runtime_snippet_injection_result,
}


def project_audit_metadata(metadata: Mapping[str, Any] | None) -> AuditProjectionResult:
    """Project registered top-level audit metadata without inspecting unknowns."""

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
        if clean is None:
            dropped += 1
            continue
        projected[key] = clean
    if dropped:
        projected["projection_dropped_field_count"] = dropped
    if unsupported:
        projected["projection_unsupported_artifact_count"] = unsupported
    return AuditProjectionResult(projected, dropped, unsupported)

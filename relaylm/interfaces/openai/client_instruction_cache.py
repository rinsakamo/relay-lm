"""Content-free dry-run planning for instruction cache operations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result


_SCHEMA_VERSION = "client_instruction_cache_dry_run.v0"
_EXPECTED_FINGERPRINT_SCHEMA_VERSION = "client_instruction_fingerprint_dry_run.v0"
_FORBIDDEN_CONTENT_KEYS = frozenset(
    {
        "content",
        "text",
        "raw_content",
        "raw_message",
        "prompt",
        "messages",
        "history",
        "body",
        "instruction_text",
        "fingerprint",
        "fingerprint_bytes",
        "fingerprint_hash",
        "cache_key",
        "cache_value",
        "cache_result",
    }
)


def build_client_instruction_cache_dry_run(
    fingerprint_artifact: Mapping[str, Any] | None,
    *,
    enabled: bool,
    lookup_requested: bool = False,
    save_requested: bool = False,
) -> dict[str, Any] | None:
    """Plan future instruction-cache lookup/save operations from metadata only.

    This helper deliberately consumes only the content-free fingerprint dry-run
    artifact. It does not accept raw messages, instruction text, fingerprint
    bytes, or cache keys, and it never computes hashes or performs cache I/O.
    """

    if not enabled:
        return None

    blocked_reasons: list[str] = []
    lookup_requested = bool(lookup_requested)
    save_requested = bool(save_requested)
    artifact: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "enabled": True,
        "diagnostics_only": True,
        "content_free": True,
        "dry_run_only": True,
        "operation_plan_mode": "metadata_contract_only",
        "source_artifact_present": isinstance(fingerprint_artifact, Mapping),
        "source_schema_version": None,
        "source_schema_supported": False,
        "cache_operation_plan_ready": False,
        "lookup_requested": lookup_requested,
        "save_requested": save_requested,
        "lookup_plan_ready": False,
        "save_plan_ready": False,
        "cache_lookup_attempted": False,
        "cache_save_attempted": False,
        "cache_key_computed": False,
        "cache_key_available": False,
        "fingerprint_hash_computed": False,
        "fingerprint_hash_available": False,
        "cache_hit_known": False,
        "cache_hit": None,
        "cache_result_available": False,
        "payload_mutation_applied": False,
        "history_exclusion_applied": False,
        "persistence_applied": False,
        "instruction_candidate_count": 0,
        "candidate_roles": [],
        "candidate_indices": [],
        "content_shape_counts": {},
        "fingerprint_scope_summary": {
            "candidate_count": 0,
            "candidate_role_count": 0,
            "candidate_index_count": 0,
            "content_shape_kind_count": 0,
        },
        "source_blocked_reasons": [],
        "blocked_reasons": [],
    }

    if not isinstance(fingerprint_artifact, Mapping):
        artifact["blocked_reasons"] = ["source_fingerprint_artifact_missing"]
        return artifact

    source_schema_version = _text(fingerprint_artifact.get("schema_version"))
    source_blocked_reasons = _strings(fingerprint_artifact.get("blocked_reasons"))
    instruction_candidate_count = _non_negative_int(
        fingerprint_artifact.get("instruction_candidate_count")
    )
    candidate_roles = _strings(fingerprint_artifact.get("candidate_roles"))
    candidate_indices = _ints(fingerprint_artifact.get("candidate_indices"))
    content_shape_counts = _string_int_mapping(
        fingerprint_artifact.get("content_shape_counts")
    )
    fingerprint_scope_summary = _fingerprint_scope_summary(
        fingerprint_artifact.get("fingerprint_scope_summary"),
        instruction_candidate_count=instruction_candidate_count,
        candidate_roles=candidate_roles,
        candidate_indices=candidate_indices,
        content_shape_counts=content_shape_counts,
    )
    source_cache_key_computed = fingerprint_artifact.get("cache_key_computed") is True
    source_cache_key_available = fingerprint_artifact.get("cache_key_available") is True
    source_fingerprint_hash_computed = (
        fingerprint_artifact.get("fingerprint_hash_computed") is True
    )
    source_fingerprint_hash_available = (
        fingerprint_artifact.get("fingerprint_hash_available") is True
    )

    if source_schema_version != _EXPECTED_FINGERPRINT_SCHEMA_VERSION:
        blocked_reasons.append("source_fingerprint_schema_unsupported")
    if fingerprint_artifact.get("content_free") is not True:
        blocked_reasons.append("source_fingerprint_not_content_free")
    if fingerprint_artifact.get("fingerprint_plan_ready") is not True:
        blocked_reasons.append("source_fingerprint_plan_not_ready")
    if source_blocked_reasons:
        blocked_reasons.append("source_fingerprint_blocked")
    if instruction_candidate_count <= 0:
        blocked_reasons.append("source_instruction_candidates_missing")
    if source_cache_key_computed or source_cache_key_available:
        blocked_reasons.append("unexpected_source_cache_key_state")
    if source_fingerprint_hash_computed or source_fingerprint_hash_available:
        blocked_reasons.append("unexpected_source_fingerprint_hash_state")

    blocked_reasons = _unique_in_order(blocked_reasons)
    cache_operation_plan_ready = not blocked_reasons
    artifact.update(
        {
            "source_schema_version": source_schema_version,
            "source_schema_supported": (
                source_schema_version == _EXPECTED_FINGERPRINT_SCHEMA_VERSION
            ),
            "cache_operation_plan_ready": cache_operation_plan_ready,
            "lookup_plan_ready": cache_operation_plan_ready and lookup_requested,
            "save_plan_ready": cache_operation_plan_ready and save_requested,
            "instruction_candidate_count": instruction_candidate_count,
            "candidate_roles": candidate_roles,
            "candidate_indices": candidate_indices,
            "content_shape_counts": content_shape_counts,
            "fingerprint_scope_summary": fingerprint_scope_summary,
            "source_blocked_reasons": source_blocked_reasons,
            "blocked_reasons": blocked_reasons,
        }
    )
    return artifact


def build_client_instruction_cache_node_result(
    artifact: Mapping[str, Any] | None,
) -> PipelineNodeResult | None:
    """Build a content-free pipeline node result for cache dry-run planning."""

    if not isinstance(artifact, Mapping):
        return None

    ready = artifact.get("cache_operation_plan_ready") is True
    decision = (
        "instruction_cache_operation_plan_ready"
        if ready
        else "instruction_cache_operation_plan_blocked"
    )
    blocked_reasons = _strings(artifact.get("blocked_reasons"))
    diagnostics = {key: value for key, value in artifact.items() if key != "blocked_reasons"}
    return build_pipeline_node_result(
        node_name="client_instruction_cache",
        status="diagnostic_only",
        decision=decision,
        blocked_reasons=blocked_reasons,
        diagnostics=diagnostics,
        artifacts=[
            {
                "artifact_name": "client_instruction_cache_dry_run",
                "schema_version": _SCHEMA_VERSION,
                "present": True,
                "diagnostics_only": True,
                "content_free": True,
                "dry_run_only": True,
                "applied": False,
            }
        ],
    )


def assert_client_instruction_cache_content_free(value: Any) -> None:
    """Fail if a cache dry-run artifact exposes content-bearing keys."""

    if isinstance(value, PipelineNodeResult):
        assert_client_instruction_cache_content_free(value.to_log_dict())
        return

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in _FORBIDDEN_CONTENT_KEYS:
                raise ValueError(f"content-bearing key is not allowed: {key}")
            assert_client_instruction_cache_content_free(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            assert_client_instruction_cache_content_free(nested)


def _fingerprint_scope_summary(
    value: Any,
    *,
    instruction_candidate_count: int,
    candidate_roles: Sequence[str],
    candidate_indices: Sequence[int],
    content_shape_counts: Mapping[str, int],
) -> dict[str, int]:
    fallback = {
        "candidate_count": instruction_candidate_count,
        "candidate_role_count": len(candidate_roles),
        "candidate_index_count": len(candidate_indices),
        "content_shape_kind_count": len(content_shape_counts),
    }
    if not isinstance(value, Mapping):
        return fallback
    return {
        "candidate_count": _non_negative_int(value.get("candidate_count")),
        "candidate_role_count": _non_negative_int(value.get("candidate_role_count")),
        "candidate_index_count": _non_negative_int(value.get("candidate_index_count")),
        "content_shape_kind_count": _non_negative_int(value.get("content_shape_kind_count")),
    }


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _ints(value: Any) -> list[int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [item for item in value if isinstance(item, int) and item >= 0]


def _string_int_mapping(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, int] = {}
    for key, count in value.items():
        if not isinstance(key, str) or not isinstance(count, int) or count < 0:
            continue
        result[key] = count
    return result


def _non_negative_int(value: Any) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _unique_in_order(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result

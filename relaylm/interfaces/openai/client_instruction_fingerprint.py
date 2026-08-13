"""Content-free dry-run planning for instruction fingerprints."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result


_SCHEMA_VERSION = "client_instruction_fingerprint_dry_run.v0"
_EXPECTED_EXTRACTION_SCHEMA_VERSION = "client_instruction_extraction_dry_run.v0"
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
    }
)


def build_client_instruction_fingerprint_dry_run(
    extraction_artifact: Mapping[str, Any] | None,
    *,
    enabled: bool,
) -> dict[str, Any] | None:
    """Plan a future instruction fingerprint from extraction metadata only.

    This helper deliberately does not accept raw messages or instruction text.
    It consumes the content-free client instruction extraction artifact and emits
    only a content-free readiness contract for a later hash/cache phase.
    """

    if not enabled:
        return None

    blocked_reasons: list[str] = []
    artifact: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "enabled": True,
        "diagnostics_only": True,
        "content_free": True,
        "source_artifact_present": isinstance(extraction_artifact, Mapping),
        "source_schema_version": None,
        "source_schema_supported": False,
        "managed_route": False,
        "route_policy": None,
        "extraction_candidate_ready": False,
        "fingerprint_plan_ready": False,
        "fingerprint_plan_mode": "metadata_contract_only",
        "fingerprint_hash_computed": False,
        "cache_key_computed": False,
        "cache_lookup_attempted": False,
        "cache_save_attempted": False,
        "instruction_candidate_count": 0,
        "candidate_roles": [],
        "candidate_indices": [],
        "content_shape_counts": {},
        "message_count": 0,
        "valid_message_count": 0,
        "invalid_message_count": 0,
        "invalid_instruction_candidate_count": 0,
        "unknown_instruction_candidate_shape_count": 0,
        "multimodal_instruction_candidate_count": 0,
        "has_multimodal_instruction_candidate": False,
        "active_tool_transaction_candidate": False,
        "fingerprint_scope_summary": {
            "candidate_count": 0,
            "candidate_role_count": 0,
            "candidate_index_count": 0,
            "content_shape_kind_count": 0,
        },
        "source_blocked_reasons": [],
        "blocked_reasons": [],
    }

    if not isinstance(extraction_artifact, Mapping):
        artifact["blocked_reasons"] = ["source_extraction_artifact_missing"]
        return artifact

    source_schema_version = _text(extraction_artifact.get("schema_version"))
    source_blocked_reasons = _strings(extraction_artifact.get("blocked_reasons"))
    candidate_roles = _strings(extraction_artifact.get("candidate_roles"))
    candidate_indices = _ints(extraction_artifact.get("candidate_indices"))
    content_shape_counts = _string_int_mapping(
        extraction_artifact.get("content_shape_counts")
    )
    managed_route = extraction_artifact.get("managed_route") is True
    extraction_candidate_ready = (
        extraction_artifact.get("fingerprint_candidate_ready") is True
    )
    instruction_candidate_count = _non_negative_int(
        extraction_artifact.get("instruction_candidate_count")
    )
    message_count = _non_negative_int(extraction_artifact.get("message_count"))
    valid_message_count = _non_negative_int(
        extraction_artifact.get("valid_message_count")
    )
    invalid_message_count = _non_negative_int(
        extraction_artifact.get("invalid_message_count")
    )
    invalid_instruction_candidate_count = _non_negative_int(
        extraction_artifact.get("invalid_instruction_candidate_count")
    )
    unknown_instruction_candidate_shape_count = _non_negative_int(
        extraction_artifact.get("unknown_instruction_candidate_shape_count")
    )
    multimodal_instruction_candidate_count = _non_negative_int(
        extraction_artifact.get("multimodal_instruction_candidate_count")
    )

    if source_schema_version != _EXPECTED_EXTRACTION_SCHEMA_VERSION:
        blocked_reasons.append("source_extraction_schema_unsupported")
    if extraction_artifact.get("content_free") is not True:
        blocked_reasons.append("source_extraction_not_content_free")
    if not managed_route:
        blocked_reasons.append("pass_through_route_exempt")
    if not extraction_candidate_ready:
        blocked_reasons.append("source_extraction_not_ready")
    if source_blocked_reasons:
        blocked_reasons.append("source_extraction_blocked")
    if invalid_message_count:
        blocked_reasons.append("source_messages_invalid")
    if invalid_instruction_candidate_count:
        blocked_reasons.append("source_instruction_candidate_content_invalid")
    if unknown_instruction_candidate_shape_count:
        blocked_reasons.append("source_instruction_candidate_shape_unknown")
    if multimodal_instruction_candidate_count:
        blocked_reasons.append("source_multimodal_instruction_candidate_requires_preservation")
    if extraction_artifact.get("active_tool_transaction_candidate") is True:
        blocked_reasons.append("active_tool_transaction_requires_preservation")

    blocked_reasons = _unique_in_order(blocked_reasons)
    artifact.update(
        {
            "source_schema_version": source_schema_version,
            "source_schema_supported": (
                source_schema_version == _EXPECTED_EXTRACTION_SCHEMA_VERSION
            ),
            "managed_route": managed_route,
            "route_policy": _text(extraction_artifact.get("route_policy")),
            "extraction_candidate_ready": extraction_candidate_ready,
            "fingerprint_plan_ready": not blocked_reasons,
            "instruction_candidate_count": instruction_candidate_count,
            "candidate_roles": candidate_roles,
            "candidate_indices": candidate_indices,
            "content_shape_counts": content_shape_counts,
            "message_count": message_count,
            "valid_message_count": valid_message_count,
            "invalid_message_count": invalid_message_count,
            "invalid_instruction_candidate_count": invalid_instruction_candidate_count,
            "unknown_instruction_candidate_shape_count": unknown_instruction_candidate_shape_count,
            "multimodal_instruction_candidate_count": multimodal_instruction_candidate_count,
            "has_multimodal_instruction_candidate": (
                extraction_artifact.get("has_multimodal_instruction_candidate") is True
            ),
            "active_tool_transaction_candidate": (
                extraction_artifact.get("active_tool_transaction_candidate") is True
            ),
            "fingerprint_scope_summary": {
                "candidate_count": instruction_candidate_count,
                "candidate_role_count": len(candidate_roles),
                "candidate_index_count": len(candidate_indices),
                "content_shape_kind_count": len(content_shape_counts),
            },
            "source_blocked_reasons": source_blocked_reasons,
            "blocked_reasons": blocked_reasons,
        }
    )
    return artifact


def build_client_instruction_fingerprint_node_result(
    artifact: Mapping[str, Any] | None,
) -> PipelineNodeResult | None:
    """Build a content-free pipeline node result for future runtime wiring."""

    if not isinstance(artifact, Mapping):
        return None

    managed_route = artifact.get("managed_route") is True
    ready = artifact.get("fingerprint_plan_ready") is True
    if not managed_route:
        status = "skipped"
        decision = "pass_through_route_exempt"
    elif ready:
        status = "diagnostic_only"
        decision = "instruction_fingerprint_plan_ready"
    else:
        status = "diagnostic_only"
        decision = "instruction_fingerprint_plan_blocked"

    blocked_reasons = _strings(artifact.get("blocked_reasons"))
    diagnostics = {key: value for key, value in artifact.items() if key != "blocked_reasons"}
    return build_pipeline_node_result(
        node_name="client_instruction_fingerprint",
        status=status,
        decision=decision,
        blocked_reasons=blocked_reasons,
        diagnostics=diagnostics,
        artifacts=[
            {
                "artifact_name": "client_instruction_fingerprint_dry_run",
                "schema_version": _SCHEMA_VERSION,
                "present": True,
                "diagnostics_only": True,
                "content_free": True,
                "applied": False,
            }
        ],
    )


def assert_client_instruction_fingerprint_content_free(value: Any) -> None:
    """Fail if a fingerprint dry-run artifact exposes content-bearing keys."""

    if isinstance(value, PipelineNodeResult):
        assert_client_instruction_fingerprint_content_free(value.to_log_dict())
        return

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in _FORBIDDEN_CONTENT_KEYS:
                raise ValueError(f"content-bearing key is not allowed: {key}")
            assert_client_instruction_fingerprint_content_free(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            assert_client_instruction_fingerprint_content_free(nested)


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

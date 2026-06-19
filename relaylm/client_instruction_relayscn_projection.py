"""Content-free RelaySCN projection from validated instruction cache hits."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any, Literal

from relaylm.client_instruction_cache_lookup_runtime import (
    ClientInstructionCacheLookupRuntimeResult,
)
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result

_SCHEMA_VERSION = "client_instruction_relayscn_projection.v0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CONFIDENCE_BUCKETS = (
    (0.90, "very_high"),
    (0.75, "high"),
    (0.50, "medium"),
    (0.0, "low"),
)
_FORBIDDEN_KEYS = frozenset(
    {
        "cache_key_sha256",
        "instruction_fingerprint_sha256",
        "route_model",
        "character_id",
        "entry",
        "candidate_entry",
        "lookup_entry",
        "reader_result",
        "lookup_result",
        "scene_state",
        "scene_role",
        "scene_context",
        "scene_constraints",
        "role_name",
        "setting",
        "task",
        "participants",
        "constraint_type",
        "value",
        "content",
        "text",
        "normalized_text",
        "raw_instruction",
        "raw_response",
        "raw_message",
        "messages",
        "prompt",
        "path",
        "filename",
        "file_path",
        "root_path",
        "raw_json",
    }
)


@dataclass(frozen=True)
class ClientInstructionRelaySCNProjectionResult:
    schema_version: str
    status: Literal["projected", "miss", "blocked", "skipped"]
    cache_hit: bool
    projection_ready: bool
    projected_scene_type: str | None = None
    projected_scene_role_present: bool = False
    projected_scene_role_scope: str | None = None
    projected_scene_role_source: str | None = None
    projected_scene_role_confidence_bucket: str | None = None
    projected_scene_context_present: bool = False
    projected_scene_context_field_count: int = 0
    projected_scene_context_participant_count: int = 0
    projected_scene_constraint_count: int = 0
    durable_candidate_count: int = 0
    blocked_instruction_kind_count: int = 0
    miss_reason: str | None = None
    blocked_reasons: tuple[str, ...] = ()
    diagnostics_only: bool = True
    content_free: bool = True
    read_only: bool = True
    applied: bool = False


def build_client_instruction_relayscn_projection(
    runtime_result: ClientInstructionCacheLookupRuntimeResult | None,
) -> ClientInstructionRelaySCNProjectionResult | None:
    """Project a validated cache hit into an allowlisted RelaySCN summary.

    The input runtime result is request-local and content-bearing. This helper
    only emits enum/count/boolean diagnostics. It never exposes cache hashes,
    raw instruction text, role names, scene setting/task/participants, paths, or
    opaque cache bodies, and it never mutates payloads or RelaySCN runtime state.
    """

    if runtime_result is None:
        return None

    if runtime_result.status == "skipped":
        return ClientInstructionRelaySCNProjectionResult(
            schema_version=_SCHEMA_VERSION,
            status="skipped",
            cache_hit=False,
            projection_ready=False,
            blocked_reasons=tuple(_unique([*runtime_result.blocked_reasons])),
        )

    lookup = runtime_result.lookup_result
    if runtime_result.status == "miss":
        return ClientInstructionRelaySCNProjectionResult(
            schema_version=_SCHEMA_VERSION,
            status="miss",
            cache_hit=False,
            projection_ready=False,
            miss_reason=(lookup.miss_reason if lookup is not None else None),
            blocked_reasons=tuple(_unique([*runtime_result.blocked_reasons])),
        )

    if runtime_result.status != "hit":
        return ClientInstructionRelaySCNProjectionResult(
            schema_version=_SCHEMA_VERSION,
            status="blocked",
            cache_hit=False,
            projection_ready=False,
            blocked_reasons=tuple(_blocked_reasons(runtime_result)),
        )

    if lookup is None or lookup.entry is None or lookup.status != "hit":
        return ClientInstructionRelaySCNProjectionResult(
            schema_version=_SCHEMA_VERSION,
            status="blocked",
            cache_hit=False,
            projection_ready=False,
            blocked_reasons=tuple(
                _unique([*runtime_result.blocked_reasons, "cache_hit_entry_missing"])
            ),
        )

    entry = lookup.entry
    role = entry.scene_role
    context = entry.scene_context
    context_field_count = int(context.setting is not None) + int(context.task is not None)
    result = ClientInstructionRelaySCNProjectionResult(
        schema_version=_SCHEMA_VERSION,
        status="projected",
        cache_hit=True,
        projection_ready=True,
        projected_scene_type=entry.scene_type,
        projected_scene_role_present=role is not None,
        projected_scene_role_scope=role.role_scope if role is not None else None,
        projected_scene_role_source=role.role_source if role is not None else None,
        projected_scene_role_confidence_bucket=(
            _confidence_bucket(role.confidence) if role is not None else None
        ),
        projected_scene_context_present=(
            context.setting is not None
            or context.task is not None
            or bool(context.participants)
        ),
        projected_scene_context_field_count=context_field_count,
        projected_scene_context_participant_count=len(context.participants),
        projected_scene_constraint_count=len(entry.scene_constraints),
        durable_candidate_count=entry.durable_candidate_count,
        blocked_instruction_kind_count=len(entry.blocked_instruction_kinds),
        blocked_reasons=(),
    )
    assert_client_instruction_relayscn_projection_content_free(result_to_log_dict(result))
    return result


def build_client_instruction_relayscn_projection_diagnostics(
    result: ClientInstructionRelaySCNProjectionResult | None,
) -> dict[str, Any] | None:
    if result is None:
        return None
    diagnostics = result_to_log_dict(result)
    assert_client_instruction_relayscn_projection_content_free(diagnostics)
    return diagnostics


def build_client_instruction_relayscn_projection_node_result(
    runtime_result: ClientInstructionCacheLookupRuntimeResult | None,
) -> PipelineNodeResult | None:
    result = build_client_instruction_relayscn_projection(runtime_result)
    diagnostics = build_client_instruction_relayscn_projection_diagnostics(result)
    if result is None or diagnostics is None:
        return None
    node_result = build_pipeline_node_result(
        node_name="client_instruction_relayscn_projection",
        status="diagnostic_only",
        decision=_decision(result),
        blocked_reasons=list(result.blocked_reasons),
        diagnostics={key: value for key, value in diagnostics.items() if key != "blocked_reasons"},
        artifacts=[
            {
                "artifact_name": "client_instruction_relayscn_projection_summary",
                "schema_version": _SCHEMA_VERSION,
                "present": True,
                "diagnostics_only": True,
                "content_free": True,
                "read_only": True,
                "applied": False,
                "projection_ready": result.projection_ready,
            }
        ],
    )
    assert_client_instruction_relayscn_projection_content_free(node_result.to_log_dict())
    return node_result


def result_to_log_dict(result: ClientInstructionRelaySCNProjectionResult) -> dict[str, Any]:
    return {
        "schema_version": result.schema_version,
        "status": result.status,
        "cache_hit": result.cache_hit,
        "projection_ready": result.projection_ready,
        "projected_scene_type": result.projected_scene_type,
        "projected_scene_role_present": result.projected_scene_role_present,
        "projected_scene_role_scope": result.projected_scene_role_scope,
        "projected_scene_role_source": result.projected_scene_role_source,
        "projected_scene_role_confidence_bucket": (
            result.projected_scene_role_confidence_bucket
        ),
        "projected_scene_context_present": result.projected_scene_context_present,
        "projected_scene_context_field_count": (
            result.projected_scene_context_field_count
        ),
        "projected_scene_context_participant_count": (
            result.projected_scene_context_participant_count
        ),
        "projected_scene_constraint_count": result.projected_scene_constraint_count,
        "durable_candidate_count": result.durable_candidate_count,
        "blocked_instruction_kind_count": result.blocked_instruction_kind_count,
        "miss_reason": result.miss_reason,
        "blocked_reasons": list(result.blocked_reasons),
        "diagnostics_only": result.diagnostics_only,
        "content_free": result.content_free,
        "read_only": result.read_only,
        "applied": result.applied,
    }


def assert_client_instruction_relayscn_projection_content_free(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in _FORBIDDEN_KEYS:
                raise ValueError(f"content-bearing projection key is not allowed: {key}")
            assert_client_instruction_relayscn_projection_content_free(nested)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            assert_client_instruction_relayscn_projection_content_free(nested)
        return
    if isinstance(value, str) and _SHA256_RE.fullmatch(value):
        raise ValueError("hash value is not allowed in projection diagnostics")


def _decision(result: ClientInstructionRelaySCNProjectionResult) -> str:
    if result.status == "projected":
        return "cache_hit_relayscn_projection_ready"
    if result.status == "miss":
        return "cache_hit_relayscn_projection_miss"
    if result.status == "skipped":
        return "cache_hit_relayscn_projection_skipped"
    return "cache_hit_relayscn_projection_blocked"


def _blocked_reasons(runtime_result: ClientInstructionCacheLookupRuntimeResult) -> list[str]:
    reasons = list(runtime_result.blocked_reasons)
    lookup = runtime_result.lookup_result
    reader = runtime_result.reader_result
    if lookup is not None:
        reasons.extend(lookup.blocked_reasons)
    if reader is not None:
        reasons.extend(reader.blocked_reasons)
    if not reasons:
        reasons.append("cache_hit_projection_source_not_ready")
    return _unique(reasons)


def _confidence_bucket(value: float) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "unknown"
    for threshold, bucket in _CONFIDENCE_BUCKETS:
        if numeric >= threshold:
            return bucket
    return "unknown"


def _unique(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, str) and value and value not in seen:
            result.append(value)
            seen.add(value)
    return result

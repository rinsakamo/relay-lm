"""Diagnostics-only cache-write preflight for typed client instruction parses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import re
from typing import Any, Literal

from relaylm.client_instruction_identity import ClientInstructionIdentityResult
from relaylm.client_instruction_typed_parse import ClientInstructionTypedParseResult
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result

SCHEMA_VERSION = "client_instruction_cache_write_preflight.v0"
_ENTRY_SCHEMA_VERSION = "relaylm.client_instruction_cache.v0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_DIAGNOSTIC_KEYS = frozenset(
    {
        "cache_key",
        "cache_key_sha256",
        "instruction_fingerprint_sha256",
        "fingerprint",
        "hash",
        "route_model",
        "character_id",
        "candidate",
        "entry",
        "cache_entry",
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
        "raw_instruction",
        "raw_response",
        "content",
        "text",
        "messages",
        "prompt",
        "path",
        "filename",
        "file_path",
        "root_path",
    }
)


@dataclass(frozen=True)
class ClientInstructionCacheWriteResult:
    schema_version: str
    status: Literal["ready", "dry_run", "blocked", "skipped"]
    write_preflight_ready: bool
    dry_run_only: bool
    cache_entry_candidate: Mapping[str, Any] | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    blocked_reasons: tuple[str, ...] = ()
    cache_entry_candidate_built: bool = False
    cache_write_attempted: bool = False
    cache_entry_written: bool = False
    runtime_private: bool = True
    content_bearing: bool = True
    diagnostics_only: bool = True
    applied: bool = False


def build_client_instruction_cache_write_preflight(
    *,
    parse_result: ClientInstructionTypedParseResult | None,
    identity_result: ClientInstructionIdentityResult | None,
    enabled: bool,
    dry_run_only: bool,
    managed_route: bool,
    route_model: str,
    character_id: str | None,
) -> ClientInstructionCacheWriteResult | None:
    """Plan a future cache write without performing any filesystem mutation."""

    if not enabled:
        return None
    if not managed_route:
        return ClientInstructionCacheWriteResult(
            schema_version=SCHEMA_VERSION,
            status="skipped",
            write_preflight_ready=False,
            dry_run_only=dry_run_only,
            blocked_reasons=("pass_through_route_exempt",),
        )

    identity = identity_result.identity if identity_result is not None else None
    reasons: list[str] = []
    if identity_result is None or identity_result.ready is not True or identity is None:
        reasons.append("source_identity_not_ready")
    elif (
        identity.empty_instruction is True
        or len(identity.candidates) == 0
        or not _is_sha256(identity.cache_key_sha256)
        or not _is_sha256(identity.instruction_fingerprint_sha256)
    ):
        reasons.append("source_identity_invalid")

    if parse_result is None or parse_result.parse_ready is not True or parse_result.artifact is None:
        reasons.append("source_typed_parse_not_ready")
    elif parse_result.artifact.scene_type is None:
        reasons.append("source_typed_parse_scene_type_missing")

    if not _bounded_text(route_model, 128) or (
        character_id is not None and not _bounded_text(character_id, 128)
    ):
        reasons.append("cache_write_scope_invalid")

    if reasons:
        return ClientInstructionCacheWriteResult(
            schema_version=SCHEMA_VERSION,
            status="blocked",
            write_preflight_ready=False,
            dry_run_only=dry_run_only,
            blocked_reasons=tuple(_unique(reasons)),
        )

    assert identity is not None and parse_result is not None and parse_result.artifact is not None
    artifact = parse_result.artifact
    entry = {
        "schema_version": _ENTRY_SCHEMA_VERSION,
        "cache_key_sha256": identity.cache_key_sha256,
        "instruction_fingerprint_sha256": identity.instruction_fingerprint_sha256,
        "route_model": route_model,
        "character_id": character_id,
        "instruction_parse_schema_version": artifact.schema_version,
        "authority_policy_version": "client_instruction_authority.v1",
        "parser_version": parse_result.parser_version,
        "parse_status": "valid",
        "scene_state": {
            "scene_type": artifact.scene_type,
            "scene_role": _entry_role(artifact.scene_role),
            "scene_context": _entry_context(artifact.scene_context),
            "scene_constraints": [
                {"constraint_type": item.constraint_type, "value": item.value}
                for item in artifact.scene_constraints
            ],
        },
        "durable_candidate_count": len(artifact.durable_persona_candidates),
        "blocked_instruction_kinds": list(artifact.blocked_instruction_kinds),
        "raw_instruction_persisted": False,
        "raw_response_persisted": False,
    }
    if not dry_run_only:
        return ClientInstructionCacheWriteResult(
            schema_version=SCHEMA_VERSION,
            status="blocked",
            write_preflight_ready=False,
            dry_run_only=False,
            cache_entry_candidate=entry,
            cache_entry_candidate_built=True,
            blocked_reasons=("cache_writer_not_implemented",),
        )
    return ClientInstructionCacheWriteResult(
        schema_version=SCHEMA_VERSION,
        status="dry_run",
        write_preflight_ready=True,
        dry_run_only=True,
        cache_entry_candidate=entry,
        cache_entry_candidate_built=True,
    )


def build_client_instruction_cache_write_diagnostics(
    result: ClientInstructionCacheWriteResult | None,
) -> dict[str, Any] | None:
    if result is None:
        return None
    diagnostics = {
        "schema_version": result.schema_version,
        "enabled": True,
        "status": result.status,
        "write_preflight_ready": result.write_preflight_ready,
        "dry_run_only": result.dry_run_only,
        "cache_entry_candidate_built": result.cache_entry_candidate_built,
        "cache_write_attempted": result.cache_write_attempted,
        "cache_entry_written": result.cache_entry_written,
        "raw_instruction_persisted": False,
        "raw_response_persisted": False,
        "blocked_reasons": tuple(result.blocked_reasons),
        "diagnostics_only": result.diagnostics_only,
        "runtime_private_source": result.runtime_private,
        "content_bearing_source": result.content_bearing,
        "applied": result.applied,
    }
    assert_client_instruction_cache_write_diagnostics_content_free(diagnostics)
    return diagnostics


def build_client_instruction_cache_write_node_result(
    result: ClientInstructionCacheWriteResult | None,
) -> PipelineNodeResult | None:
    diagnostics = build_client_instruction_cache_write_diagnostics(result)
    if result is None or diagnostics is None:
        return None
    return build_pipeline_node_result(
        node_name="client_instruction_cache_write",
        status="diagnostic_only",
        decision=_decision(result),
        blocked_reasons=list(result.blocked_reasons),
        diagnostics={key: value for key, value in diagnostics.items() if key != "blocked_reasons"},
        artifacts=[
            {
                "artifact_name": "client_instruction_cache_write_preflight_summary",
                "schema_version": SCHEMA_VERSION,
                "present": True,
                "diagnostics_only": True,
                "content_free": True,
                "runtime_private_source": True,
                "applied": False,
            }
        ],
    )


def assert_client_instruction_cache_write_diagnostics_content_free(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in _FORBIDDEN_DIAGNOSTIC_KEYS:
                raise ValueError(f"private/content-bearing diagnostics key: {key}")
            assert_client_instruction_cache_write_diagnostics_content_free(nested)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            assert_client_instruction_cache_write_diagnostics_content_free(nested)
        return
    if isinstance(value, str) and _SHA256_RE.fullmatch(value):
        raise ValueError("hash value is not allowed in diagnostics")


def _entry_role(role: Any) -> dict[str, Any] | None:
    if role is None:
        return None
    return {
        "role_name": role.role_name,
        "role_scope": role.role_scope,
        "role_source": "client_instruction_cache",
        "confidence": role.confidence,
    }


def _entry_context(context: Any) -> dict[str, Any]:
    return {
        "setting": context.setting,
        "task": context.task,
        "participants": list(context.participants),
    }


def _decision(result: ClientInstructionCacheWriteResult) -> str:
    if result.status == "dry_run":
        return "client_instruction_cache_write_dry_run"
    if result.status == "ready":
        return "client_instruction_cache_write_ready"
    if result.status == "skipped":
        return "client_instruction_cache_write_skipped"
    return "client_instruction_cache_write_blocked"


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _bounded_text(value: Any, maximum: int) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if isinstance(value, str) and value))

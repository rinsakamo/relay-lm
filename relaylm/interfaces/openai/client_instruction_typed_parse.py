"""Runtime-private typed parse contract for client instruction artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
import re
from typing import Any, Literal

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.relayscn import KNOWN_SCENE_TYPES

SCHEMA_VERSION = "client_instruction_parse.v1"
_RUNTIME_SCHEMA_VERSION = "client_instruction_typed_parse_runtime.v0"
_ROLE_SCOPES = frozenset({"turn", "scene"})
_DURABLE_KINDS = frozenset(
    {"identity", "value", "worldview", "output_policy", "relationship"}
)
_TOP_LEVEL_KEYS = frozenset(
    {
        "scene_type",
        "scene_role",
        "scene_context",
        "scene_constraints",
        "durable_persona_candidates",
        "blocked_instruction_kinds",
    }
)
_ROLE_KEYS = frozenset({"role_name", "role_scope", "confidence"})
_CONTEXT_KEYS = frozenset({"setting", "task", "participants"})
_CONSTRAINT_KEYS = frozenset({"constraint_type", "value"})
_DURABLE_KEYS = frozenset({"candidate_kind", "normalized_value", "confidence"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_LOWER_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$")
_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_WINDOWS_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
_FORBIDDEN_KEYS = frozenset(
    {
        "content",
        "text",
        "normalized_text",
        "raw_instruction",
        "raw_response",
        "raw_message",
        "messages",
        "prompt",
        "backend_payload",
        "response_text",
        "cache_key",
        "cache_key_sha256",
        "instruction_fingerprint_sha256",
        "fingerprint",
        "hash",
        "path",
        "filename",
        "file_path",
        "root_path",
        "url",
        "tool_call_id",
    }
)
_DIAGNOSTIC_FORBIDDEN_KEYS = _FORBIDDEN_KEYS | frozenset(
    {
        "candidate",
        "artifact",
        "scene_role",
        "scene_context",
        "scene_constraints",
        "role_name",
        "setting",
        "task",
        "participants",
        "constraint_type",
        "value",
        "normalized_value",
    }
)


@dataclass(frozen=True)
class ClientInstructionParsedRole:
    role_name: str | None
    role_scope: Literal["turn", "scene"]
    confidence: float


@dataclass(frozen=True)
class ClientInstructionParsedContext:
    setting: str | None
    task: str | None
    participants: tuple[str, ...]


@dataclass(frozen=True)
class ClientInstructionParsedConstraint:
    constraint_type: str
    value: str | int | float | bool


@dataclass(frozen=True)
class ClientInstructionDurableCandidate:
    candidate_kind: Literal[
        "identity",
        "value",
        "worldview",
        "output_policy",
        "relationship",
    ]
    normalized_value: str
    confidence: float


@dataclass(frozen=True)
class ClientInstructionTypedParseArtifact:
    schema_version: str
    scene_type: str | None
    scene_role: ClientInstructionParsedRole | None
    scene_context: ClientInstructionParsedContext
    scene_constraints: tuple[ClientInstructionParsedConstraint, ...]
    durable_persona_candidates: tuple[ClientInstructionDurableCandidate, ...]
    blocked_instruction_kinds: tuple[str, ...]
    runtime_private: bool = True
    content_bearing: bool = True


@dataclass(frozen=True)
class ClientInstructionTypedParseResult:
    schema_version: str
    status: Literal["valid", "blocked", "skipped"]
    parse_ready: bool
    artifact: ClientInstructionTypedParseArtifact | None = None
    blocked_reasons: tuple[str, ...] = ()
    parser_version: str | None = None
    diagnostics_only: bool = True
    runtime_private: bool = True
    content_bearing: bool = True
    applied: bool = False


def validate_client_instruction_typed_parse_candidate(
    candidate: Mapping[str, Any] | None,
    *,
    enabled: bool,
    parser_version: str | None = None,
) -> ClientInstructionTypedParseResult | None:
    """Validate one runtime-private parse candidate without persistence or apply."""

    if not enabled:
        return None
    if candidate is None:
        return ClientInstructionTypedParseResult(
            schema_version=_RUNTIME_SCHEMA_VERSION,
            status="skipped",
            parse_ready=False,
            blocked_reasons=("parse_candidate_missing",),
            parser_version=parser_version,
        )
    try:
        return _validate(candidate, parser_version=parser_version)
    except Exception:
        return _blocked("typed_parse_validation_failed", parser_version=parser_version)


def build_client_instruction_typed_parse_diagnostics(
    result: ClientInstructionTypedParseResult | None,
) -> dict[str, Any] | None:
    """Return a content-free summary of typed parse validation."""

    if result is None:
        return None
    artifact = result.artifact
    context = artifact.scene_context if artifact is not None else None
    diagnostics = {
        "schema_version": result.schema_version,
        "parse_schema_version": SCHEMA_VERSION,
        "enabled": True,
        "status": result.status,
        "parse_ready": result.parse_ready,
        "candidate_present": artifact is not None,
        "scene_type_present": artifact is not None and artifact.scene_type is not None,
        "scene_role_present": artifact is not None and artifact.scene_role is not None,
        "scene_context_present": (
            context is not None
            and (context.setting is not None or context.task is not None or bool(context.participants))
        ),
        "scene_context_field_count": (
            int(context.setting is not None) + int(context.task is not None)
            if context is not None
            else 0
        ),
        "scene_context_participant_count": len(context.participants) if context else 0,
        "scene_constraint_count": len(artifact.scene_constraints) if artifact else 0,
        "durable_candidate_count": len(artifact.durable_persona_candidates) if artifact else 0,
        "blocked_instruction_kind_count": len(artifact.blocked_instruction_kinds) if artifact else 0,
        "parser_version_present": result.parser_version is not None,
        "blocked_reasons": tuple(result.blocked_reasons),
        "diagnostics_only": result.diagnostics_only,
        "runtime_private_source": result.runtime_private,
        "content_bearing_source": result.content_bearing,
        "applied": result.applied,
    }
    assert_client_instruction_typed_parse_diagnostics_content_free(diagnostics)
    return diagnostics


def build_client_instruction_typed_parse_node_result(
    result: ClientInstructionTypedParseResult | None,
) -> PipelineNodeResult | None:
    diagnostics = build_client_instruction_typed_parse_diagnostics(result)
    if result is None or diagnostics is None:
        return None
    return build_pipeline_node_result(
        node_name="client_instruction_typed_parse",
        status="diagnostic_only",
        decision=_decision(result),
        blocked_reasons=list(result.blocked_reasons),
        diagnostics={key: value for key, value in diagnostics.items() if key != "blocked_reasons"},
        artifacts=[
            {
                "artifact_name": "client_instruction_typed_parse_summary",
                "schema_version": _RUNTIME_SCHEMA_VERSION,
                "present": True,
                "diagnostics_only": True,
                "content_free": True,
                "runtime_private_source": True,
                "applied": False,
            }
        ],
    )


def assert_client_instruction_typed_parse_diagnostics_content_free(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in _DIAGNOSTIC_FORBIDDEN_KEYS:
                raise ValueError(f"content-bearing diagnostics key is not allowed: {key}")
            assert_client_instruction_typed_parse_diagnostics_content_free(nested)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            assert_client_instruction_typed_parse_diagnostics_content_free(nested)
        return
    if isinstance(value, str) and _SHA256_RE.fullmatch(value):
        raise ValueError("hash value is not allowed in diagnostics")


def _validate(
    candidate: Mapping[str, Any],
    *,
    parser_version: str | None,
) -> ClientInstructionTypedParseResult:
    reasons: list[str] = []
    if not isinstance(candidate, Mapping):
        return _blocked("parse_candidate_invalid", parser_version=parser_version)
    keys = {str(key) for key in candidate}
    if keys != _TOP_LEVEL_KEYS:
        reasons.append("parse_candidate_unknown_or_missing_field")
    if _contains_forbidden_key(candidate):
        reasons.append("parse_candidate_content_forbidden")

    scene_type = candidate.get("scene_type")
    if scene_type is not None and (
        not isinstance(scene_type, str) or scene_type not in KNOWN_SCENE_TYPES
    ):
        reasons.append("scene_type_invalid")

    role, role_reasons = _parse_role(candidate.get("scene_role"))
    context, context_reasons = _parse_context(candidate.get("scene_context"))
    constraints, constraint_reasons = _parse_constraints(candidate.get("scene_constraints"))
    durable, durable_reasons = _parse_durable_candidates(
        candidate.get("durable_persona_candidates")
    )
    blocked_kinds, kind_reasons = _parse_bounded_strings(
        candidate.get("blocked_instruction_kinds"),
        max_items=32,
        max_length=64,
        invalid_reason="blocked_instruction_kinds_invalid",
        duplicate_reason="blocked_instruction_kinds_duplicate",
    )
    reasons.extend(
        role_reasons
        + context_reasons
        + constraint_reasons
        + durable_reasons
        + kind_reasons
    )
    if reasons:
        return _blocked(*_unique(reasons), parser_version=parser_version)
    assert context is not None and constraints is not None and durable is not None
    return ClientInstructionTypedParseResult(
        schema_version=_RUNTIME_SCHEMA_VERSION,
        status="valid",
        parse_ready=True,
        artifact=ClientInstructionTypedParseArtifact(
            schema_version=SCHEMA_VERSION,
            scene_type=scene_type,
            scene_role=role,
            scene_context=context,
            scene_constraints=constraints,
            durable_persona_candidates=durable,
            blocked_instruction_kinds=blocked_kinds,
        ),
        parser_version=parser_version,
    )


def _parse_role(value: Any) -> tuple[ClientInstructionParsedRole | None, list[str]]:
    if value is None:
        return None, []
    if not isinstance(value, Mapping):
        return None, ["scene_role_invalid"]
    reasons: list[str] = []
    if {str(key) for key in value} != _ROLE_KEYS:
        reasons.append("scene_role_unknown_or_missing_field")
    role_name = value.get("role_name")
    if role_name is not None and not _safe_text(role_name, 128):
        reasons.append("scene_role_name_invalid")
    role_scope = value.get("role_scope")
    if not isinstance(role_scope, str) or role_scope not in _ROLE_SCOPES:
        reasons.append("scene_role_scope_invalid")
    confidence = value.get("confidence")
    if not _probability(confidence):
        reasons.append("scene_role_confidence_invalid")
    if reasons:
        return None, reasons
    return ClientInstructionParsedRole(role_name, role_scope, float(confidence)), []


def _parse_context(value: Any) -> tuple[ClientInstructionParsedContext | None, list[str]]:
    if not isinstance(value, Mapping):
        return None, ["scene_context_invalid"]
    reasons: list[str] = []
    if {str(key) for key in value} != _CONTEXT_KEYS:
        reasons.append("scene_context_unknown_or_missing_field")
    setting = value.get("setting")
    task = value.get("task")
    if setting is not None and not _safe_text(setting, 256):
        reasons.append("scene_context_setting_invalid")
    if task is not None and not _safe_text(task, 256):
        reasons.append("scene_context_task_invalid")
    participants, participant_reasons = _parse_bounded_strings(
        value.get("participants"),
        max_items=16,
        max_length=128,
        invalid_reason="scene_context_participants_invalid",
    )
    reasons.extend(participant_reasons)
    if reasons:
        return None, _unique(reasons)
    return ClientInstructionParsedContext(setting, task, participants), []


def _parse_constraints(
    value: Any,
) -> tuple[tuple[ClientInstructionParsedConstraint, ...] | None, list[str]]:
    if not _is_sequence(value) or len(value) > 32:
        return None, ["scene_constraints_invalid"]
    reasons: list[str] = []
    constraints: list[ClientInstructionParsedConstraint] = []
    for item in value:
        if not isinstance(item, Mapping):
            reasons.append("scene_constraint_invalid")
            continue
        if {str(key) for key in item} != _CONSTRAINT_KEYS:
            reasons.append("scene_constraint_unknown_or_missing_field")
        constraint_type = item.get("constraint_type")
        constraint_value = item.get("value")
        type_ok = _safe_text(constraint_type, 64)
        value_ok = _constraint_value_valid(constraint_value)
        if not type_ok:
            reasons.append("scene_constraint_type_invalid")
        if not value_ok:
            reasons.append("scene_constraint_value_invalid")
        if type_ok and value_ok:
            constraints.append(ClientInstructionParsedConstraint(constraint_type, constraint_value))
    if reasons:
        return None, _unique(reasons)
    return tuple(constraints), []


def _parse_durable_candidates(
    value: Any,
) -> tuple[tuple[ClientInstructionDurableCandidate, ...] | None, list[str]]:
    if not _is_sequence(value) or len(value) > 16:
        return None, ["durable_persona_candidates_invalid"]
    reasons: list[str] = []
    candidates: list[ClientInstructionDurableCandidate] = []
    for item in value:
        if not isinstance(item, Mapping):
            reasons.append("durable_persona_candidate_invalid")
            continue
        if {str(key) for key in item} != _DURABLE_KEYS:
            reasons.append("durable_persona_candidate_unknown_or_missing_field")
        kind = item.get("candidate_kind")
        normalized_value = item.get("normalized_value")
        confidence = item.get("confidence")
        kind_ok = isinstance(kind, str) and kind in _DURABLE_KINDS
        value_ok = _safe_text(normalized_value, 256)
        confidence_ok = _probability(confidence)
        if not kind_ok:
            reasons.append("durable_persona_candidate_kind_invalid")
        if not value_ok:
            reasons.append("durable_persona_candidate_value_invalid")
        if not confidence_ok:
            reasons.append("durable_persona_candidate_confidence_invalid")
        if kind_ok and value_ok and confidence_ok:
            candidates.append(ClientInstructionDurableCandidate(kind, normalized_value, float(confidence)))
    if reasons:
        return None, _unique(reasons)
    return tuple(candidates), []


def _parse_bounded_strings(
    value: Any,
    *,
    max_items: int,
    max_length: int,
    invalid_reason: str,
    duplicate_reason: str | None = None,
) -> tuple[tuple[str, ...], list[str]]:
    if (
        not _is_sequence(value)
        or len(value) > max_items
        or any(not _safe_text(item, max_length) for item in value)
    ):
        return (), [invalid_reason]
    result = tuple(value)
    if duplicate_reason is not None and len(set(result)) != len(result):
        return (), [duplicate_reason]
    return result, []


def _constraint_value_valid(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return _safe_text(value, 256)
    return _finite_number(value)


def _probability(value: Any) -> bool:
    return _finite_number(value) and 0.0 <= float(value) <= 1.0


def _finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, TypeError, ValueError):
        return False


def _safe_text(value: Any, max_length: int) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and len(value) <= max_length
        and not _looks_like_url_or_path(value)
        and not _SHA256_RE.fullmatch(value)
    )


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in _FORBIDDEN_KEYS or _contains_forbidden_key(nested)
            for key, nested in value.items()
        )
    if _is_sequence(value):
        return any(_contains_forbidden_key(item) for item in value)
    return False


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
    )


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _blocked(*reasons: str, parser_version: str | None) -> ClientInstructionTypedParseResult:
    return ClientInstructionTypedParseResult(
        schema_version=_RUNTIME_SCHEMA_VERSION,
        status="blocked",
        parse_ready=False,
        blocked_reasons=tuple(_unique(reasons)),
        parser_version=parser_version,
    )


def _decision(result: ClientInstructionTypedParseResult) -> str:
    if result.status == "valid":
        return "client_instruction_typed_parse_ready"
    if result.status == "skipped":
        return "client_instruction_typed_parse_skipped"
    return "client_instruction_typed_parse_blocked"


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if isinstance(value, str) and value))

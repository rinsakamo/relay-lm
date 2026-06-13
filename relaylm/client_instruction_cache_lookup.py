"""Pure fail-closed lookup contract for validated client instruction cache entries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
import re
from typing import Any, Literal

from relaylm.client_instruction_identity import (
    ClientInstructionIdentityResult,
)
from relaylm.relayscn import KNOWN_SCENE_TYPES


_SCHEMA_VERSION = "client_instruction_cache_lookup.v0"
_ENTRY_SCHEMA_VERSION = "relaylm.client_instruction_cache.v0"
_CACHE_KEY_RE = re.compile(r"^[0-9a-f]{64}$")
_ROLE_SCOPES = frozenset({"turn", "scene"})
_ROLE_SOURCES = frozenset(
    {
        "client_system",
        "client_developer",
        "mixed",
        "client_instruction_cache",
    }
)
_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "cache_key_sha256",
        "instruction_fingerprint_sha256",
        "route_model",
        "character_id",
        "instruction_parse_schema_version",
        "authority_policy_version",
        "parser_version",
        "parse_status",
        "scene_state",
        "durable_candidate_count",
        "blocked_instruction_kinds",
        "raw_instruction_persisted",
        "raw_response_persisted",
    }
)
_SCENE_STATE_KEYS = frozenset(
    {"scene_type", "scene_role", "scene_context", "scene_constraints"}
)
_SCENE_ROLE_KEYS = frozenset(
    {"role_name", "role_scope", "role_source", "confidence"}
)
_SCENE_CONTEXT_KEYS = frozenset({"setting", "task", "participants"})
_SCENE_CONSTRAINT_KEYS = frozenset({"constraint_type", "value"})
_FORBIDDEN_CONTENT_KEYS = frozenset(
    {
        "content",
        "text",
        "normalized_text",
        "raw_instruction",
        "raw_response",
        "raw_message",
        "messages",
        "prompt",
        "canonical_json",
        "tool_call_id",
        "url",
    }
)
_FORBIDDEN_DIAGNOSTIC_KEYS = frozenset(
    {
        "cache_key_sha256",
        "instruction_fingerprint_sha256",
        "route_model",
        "character_id",
        "role_name",
        "setting",
        "task",
        "participants",
        "scene_constraints",
        "constraint_type",
        "value",
    }
) | _FORBIDDEN_CONTENT_KEYS


@dataclass(frozen=True)
class CachedInstructionSceneRole:
    role_name: str | None
    role_scope: Literal["turn", "scene"]
    role_source: Literal[
        "client_system",
        "client_developer",
        "mixed",
        "client_instruction_cache",
    ]
    confidence: float


@dataclass(frozen=True)
class CachedInstructionSceneContext:
    setting: str | None
    task: str | None
    participants: tuple[str, ...]


@dataclass(frozen=True)
class CachedInstructionSceneConstraint:
    constraint_type: str
    value: str | int | float | bool


@dataclass(frozen=True)
class ClientInstructionCacheEntry:
    schema_version: str
    cache_key_sha256: str
    instruction_fingerprint_sha256: str
    route_model: str
    character_id: str | None
    instruction_parse_schema_version: str
    authority_policy_version: str
    parser_version: str | None
    scene_type: str
    scene_role: CachedInstructionSceneRole | None
    scene_context: CachedInstructionSceneContext
    scene_constraints: tuple[CachedInstructionSceneConstraint, ...]
    durable_candidate_count: int
    blocked_instruction_kinds: tuple[str, ...]
    raw_instruction_persisted: bool
    raw_response_persisted: bool
    runtime_private: bool
    content_bearing: bool


@dataclass(frozen=True)
class ClientInstructionCacheLookupResult:
    schema_version: str
    status: Literal["hit", "miss", "blocked"]
    hit: bool
    entry: ClientInstructionCacheEntry | None
    miss_reason: str | None
    blocked_reasons: tuple[str, ...]


def resolve_client_instruction_cache_lookup(
    identity_result: ClientInstructionIdentityResult | None,
    candidate_entry: Mapping[str, Any] | None,
    *,
    enabled: bool,
    route_model: str,
    character_id: str | None,
    instruction_parse_schema_version: str = "client_instruction_parse.v1",
    authority_policy_version: str = "client_instruction_authority.v1",
    parser_version: str | None = None,
) -> ClientInstructionCacheLookupResult | None:
    """Resolve a supplied cache-entry candidate without performing any I/O."""

    if not enabled:
        return None
    try:
        return _resolve_client_instruction_cache_lookup(
            identity_result,
            candidate_entry,
            route_model=route_model,
            character_id=character_id,
            instruction_parse_schema_version=instruction_parse_schema_version,
            authority_policy_version=authority_policy_version,
            parser_version=parser_version,
        )
    except Exception:
        return _blocked(["cache_entry_validation_failed"])


def _resolve_client_instruction_cache_lookup(
    identity_result: ClientInstructionIdentityResult | None,
    candidate_entry: Mapping[str, Any] | None,
    *,
    route_model: str,
    character_id: str | None,
    instruction_parse_schema_version: str,
    authority_policy_version: str,
    parser_version: str | None,
) -> ClientInstructionCacheLookupResult:
    identity, identity_reasons = _validated_identity(identity_result)
    if identity_reasons:
        return _blocked(identity_reasons)
    assert identity is not None

    context_reasons = _lookup_context_reasons(
        route_model=route_model,
        character_id=character_id,
        instruction_parse_schema_version=instruction_parse_schema_version,
        authority_policy_version=authority_policy_version,
        parser_version=parser_version,
    )
    if context_reasons:
        return _blocked(context_reasons)

    if candidate_entry is None:
        return ClientInstructionCacheLookupResult(
            schema_version=_SCHEMA_VERSION,
            status="miss",
            hit=False,
            entry=None,
            miss_reason="cache_entry_not_found",
            blocked_reasons=(),
        )
    if not isinstance(candidate_entry, Mapping):
        return _blocked(["cache_entry_invalid"])

    blocked_reasons: list[str] = []
    keys = {str(key) for key in candidate_entry.keys()}
    if keys - _TOP_LEVEL_KEYS:
        blocked_reasons.append("cache_entry_unknown_field")
    if _TOP_LEVEL_KEYS - keys:
        blocked_reasons.append("cache_entry_missing_field")
    if _contains_forbidden_content_key(candidate_entry):
        blocked_reasons.append("cache_entry_content_forbidden")

    if candidate_entry.get("schema_version") != _ENTRY_SCHEMA_VERSION:
        blocked_reasons.append("cache_entry_schema_unsupported")
    if candidate_entry.get("parse_status") != "valid":
        blocked_reasons.append("cache_entry_parse_status_invalid")
    if candidate_entry.get("raw_instruction_persisted") is not False:
        blocked_reasons.append("raw_instruction_persisted_not_false")
    if candidate_entry.get("raw_response_persisted") is not False:
        blocked_reasons.append("raw_response_persisted_not_false")

    raw_cache_key = candidate_entry.get("cache_key_sha256")
    raw_fingerprint = candidate_entry.get("instruction_fingerprint_sha256")
    if not _sha256(raw_cache_key) or not _sha256(raw_fingerprint):
        blocked_reasons.append("cache_entry_hash_invalid")
    else:
        if raw_cache_key != identity.cache_key_sha256:
            blocked_reasons.append("cache_key_mismatch")
        if raw_fingerprint != identity.instruction_fingerprint_sha256:
            blocked_reasons.append("instruction_fingerprint_mismatch")

    _append_mismatch(
        blocked_reasons,
        candidate_entry.get("route_model"),
        route_model,
        "route_model_mismatch",
    )
    _append_mismatch(
        blocked_reasons,
        candidate_entry.get("character_id"),
        character_id,
        "character_id_mismatch",
    )
    _append_mismatch(
        blocked_reasons,
        candidate_entry.get("instruction_parse_schema_version"),
        instruction_parse_schema_version,
        "instruction_parse_schema_version_mismatch",
    )
    _append_mismatch(
        blocked_reasons,
        candidate_entry.get("authority_policy_version"),
        authority_policy_version,
        "authority_policy_version_mismatch",
    )
    _append_mismatch(
        blocked_reasons,
        candidate_entry.get("parser_version"),
        parser_version,
        "parser_version_mismatch",
    )

    scene_state, scene_reasons = _parse_scene_state(candidate_entry.get("scene_state"))
    blocked_reasons.extend(scene_reasons)

    durable_candidate_count = candidate_entry.get("durable_candidate_count")
    if (
        not isinstance(durable_candidate_count, int)
        or isinstance(durable_candidate_count, bool)
        or durable_candidate_count < 0
        or durable_candidate_count > 64
    ):
        blocked_reasons.append("durable_candidate_count_invalid")

    blocked_instruction_kinds, kinds_reasons = _parse_blocked_instruction_kinds(
        candidate_entry.get("blocked_instruction_kinds")
    )
    blocked_reasons.extend(kinds_reasons)
    blocked_reasons = _unique(blocked_reasons)
    if blocked_reasons:
        return _blocked(blocked_reasons)

    assert scene_state is not None
    scene_type, scene_role, scene_context, scene_constraints = scene_state
    entry = ClientInstructionCacheEntry(
        schema_version=_ENTRY_SCHEMA_VERSION,
        cache_key_sha256=raw_cache_key,
        instruction_fingerprint_sha256=raw_fingerprint,
        route_model=route_model,
        character_id=character_id,
        instruction_parse_schema_version=instruction_parse_schema_version,
        authority_policy_version=authority_policy_version,
        parser_version=parser_version,
        scene_type=scene_type,
        scene_role=scene_role,
        scene_context=scene_context,
        scene_constraints=scene_constraints,
        durable_candidate_count=durable_candidate_count,
        blocked_instruction_kinds=blocked_instruction_kinds,
        raw_instruction_persisted=False,
        raw_response_persisted=False,
        runtime_private=True,
        content_bearing=True,
    )
    return ClientInstructionCacheLookupResult(
        schema_version=_SCHEMA_VERSION,
        status="hit",
        hit=True,
        entry=entry,
        miss_reason=None,
        blocked_reasons=(),
    )


def build_client_instruction_cache_lookup_diagnostics(
    result: ClientInstructionCacheLookupResult | None,
) -> dict[str, Any] | None:
    """Return a content-free summary of lookup resolution."""

    if result is None:
        return None
    entry = result.entry
    diagnostics = {
        "schema_version": _SCHEMA_VERSION,
        "enabled": True,
        "status": result.status,
        "lookup_resolved": result.status in {"hit", "miss"},
        "cache_hit": result.hit,
        "cache_miss": result.status == "miss",
        "entry_present": entry is not None,
        "entry_validated": entry is not None,
        "scene_state_available": entry is not None,
        "scene_role_present": entry is not None and entry.scene_role is not None,
        "scene_context_present": entry is not None,
        "scene_constraint_count": len(entry.scene_constraints) if entry is not None else 0,
        "durable_candidate_count": entry.durable_candidate_count if entry is not None else 0,
        "blocked_instruction_kind_count": (
            len(entry.blocked_instruction_kinds) if entry is not None else 0
        ),
        "raw_instruction_persisted": (
            entry.raw_instruction_persisted if entry is not None else False
        ),
        "raw_response_persisted": (
            entry.raw_response_persisted if entry is not None else False
        ),
        "miss_reason": result.miss_reason,
        "blocked_reasons": list(result.blocked_reasons),
    }
    assert_client_instruction_cache_lookup_diagnostics_content_free(diagnostics)
    return diagnostics


def assert_client_instruction_cache_lookup_diagnostics_content_free(value: Any) -> None:
    """Reject cache-private values and content-bearing keys from diagnostics."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in _FORBIDDEN_DIAGNOSTIC_KEYS:
                raise ValueError(f"private/content-bearing diagnostics key: {key}")
            if _sha256(nested):
                raise ValueError(f"hash value is not allowed in diagnostics: {key}")
            assert_client_instruction_cache_lookup_diagnostics_content_free(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            assert_client_instruction_cache_lookup_diagnostics_content_free(nested)
    elif _sha256(value):
        raise ValueError("hash value is not allowed in diagnostics")


def _validated_identity(identity_result: Any) -> tuple[Any | None, list[str]]:
    if identity_result is None:
        return None, ["source_identity_missing"]
    if not isinstance(identity_result, ClientInstructionIdentityResult):
        return None, ["source_identity_invalid"]
    if (
        identity_result.ready is not True
        or identity_result.identity is None
        or bool(identity_result.blocked_reasons)
    ):
        return None, ["source_identity_not_ready"]
    identity = identity_result.identity
    if (
        identity.runtime_private is not True
        or identity.content_bearing is not True
        or not _sha256(identity.cache_key_sha256)
        or not _sha256(identity.instruction_fingerprint_sha256)
    ):
        return None, ["source_identity_invalid"]
    return identity, []


def _lookup_context_reasons(
    *,
    route_model: Any,
    character_id: Any,
    instruction_parse_schema_version: Any,
    authority_policy_version: Any,
    parser_version: Any,
) -> list[str]:
    if not _bounded_text(route_model, 128):
        return ["lookup_context_invalid"]
    if character_id is not None and not _bounded_text(character_id, 128):
        return ["lookup_context_invalid"]
    for value in (instruction_parse_schema_version, authority_policy_version):
        if not _bounded_text(value, 128):
            return ["lookup_context_invalid"]
    if parser_version is not None and not _bounded_text(parser_version, 128):
        return ["lookup_context_invalid"]
    return []


def _parse_scene_state(
    value: Any,
) -> tuple[
    tuple[
        str,
        CachedInstructionSceneRole | None,
        CachedInstructionSceneContext,
        tuple[CachedInstructionSceneConstraint, ...],
    ]
    | None,
    list[str],
]:
    reasons: list[str] = []
    if not isinstance(value, Mapping):
        return None, ["scene_state_invalid"]
    if {str(key) for key in value.keys()} != _SCENE_STATE_KEYS:
        reasons.append("scene_state_unknown_or_missing_field")

    scene_type = value.get("scene_type")
    if not isinstance(scene_type, str) or scene_type not in KNOWN_SCENE_TYPES:
        reasons.append("scene_type_invalid")

    scene_role, role_reasons = _parse_scene_role(value.get("scene_role"))
    scene_context, context_reasons = _parse_scene_context(value.get("scene_context"))
    constraints, constraint_reasons = _parse_scene_constraints(
        value.get("scene_constraints")
    )
    reasons.extend(role_reasons)
    reasons.extend(context_reasons)
    reasons.extend(constraint_reasons)
    if reasons:
        return None, _unique(reasons)
    assert isinstance(scene_type, str)
    assert scene_context is not None
    assert constraints is not None
    return (scene_type, scene_role, scene_context, constraints), []


def _parse_scene_role(
    value: Any,
) -> tuple[CachedInstructionSceneRole | None, list[str]]:
    if value is None:
        return None, []
    if not isinstance(value, Mapping):
        return None, ["scene_role_invalid"]
    reasons: list[str] = []
    if {str(key) for key in value.keys()} != _SCENE_ROLE_KEYS:
        reasons.append("scene_role_unknown_or_missing_field")
    role_name = value.get("role_name")
    if role_name is not None and not _bounded_text(role_name, 128):
        reasons.append("scene_role_name_invalid")
    role_scope = value.get("role_scope")
    if not isinstance(role_scope, str) or role_scope not in _ROLE_SCOPES:
        reasons.append("scene_role_scope_invalid")
    role_source = value.get("role_source")
    if not isinstance(role_source, str) or role_source not in _ROLE_SOURCES:
        reasons.append("scene_role_source_invalid")
    confidence = value.get("confidence")
    if not _finite_number(confidence) or not 0.0 <= float(confidence) <= 1.0:
        reasons.append("scene_role_confidence_invalid")
    if reasons:
        return None, reasons
    return CachedInstructionSceneRole(
        role_name=role_name,
        role_scope=role_scope,
        role_source=role_source,
        confidence=float(confidence),
    ), []


def _parse_scene_context(
    value: Any,
) -> tuple[CachedInstructionSceneContext | None, list[str]]:
    if not isinstance(value, Mapping):
        return None, ["scene_context_invalid"]
    reasons: list[str] = []
    if {str(key) for key in value.keys()} != _SCENE_CONTEXT_KEYS:
        reasons.append("scene_context_unknown_or_missing_field")
    setting = value.get("setting")
    task = value.get("task")
    if setting is not None and not _bounded_text(setting, 256):
        reasons.append("scene_context_setting_invalid")
    if task is not None and not _bounded_text(task, 256):
        reasons.append("scene_context_task_invalid")
    participants = value.get("participants")
    normalized_participants: tuple[str, ...] = ()
    if (
        not isinstance(participants, Sequence)
        or isinstance(participants, (str, bytes, bytearray))
        or len(participants) > 16
        or any(not _bounded_text(item, 128) for item in participants)
    ):
        reasons.append("scene_context_participants_invalid")
    else:
        normalized_participants = tuple(participants)
    if reasons:
        return None, reasons
    return CachedInstructionSceneContext(
        setting=setting,
        task=task,
        participants=normalized_participants,
    ), []


def _parse_scene_constraints(
    value: Any,
) -> tuple[tuple[CachedInstructionSceneConstraint, ...] | None, list[str]]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) > 32
    ):
        return None, ["scene_constraints_invalid"]
    constraints: list[CachedInstructionSceneConstraint] = []
    reasons: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            reasons.append("scene_constraint_invalid")
            continue
        if {str(key) for key in item.keys()} != _SCENE_CONSTRAINT_KEYS:
            reasons.append("scene_constraint_unknown_or_missing_field")
        constraint_type = item.get("constraint_type")
        constraint_value = item.get("value")
        if not _bounded_text(constraint_type, 64):
            reasons.append("scene_constraint_type_invalid")
        if not _constraint_value_valid(constraint_value):
            reasons.append("scene_constraint_value_invalid")
        if _bounded_text(constraint_type, 64) and _constraint_value_valid(
            constraint_value
        ):
            constraints.append(
                CachedInstructionSceneConstraint(
                    constraint_type=constraint_type,
                    value=constraint_value,
                )
            )
    if reasons:
        return None, _unique(reasons)
    return tuple(constraints), []


def _parse_blocked_instruction_kinds(value: Any) -> tuple[tuple[str, ...], list[str]]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) > 32
        or any(not _bounded_text(item, 64) for item in value)
    ):
        return (), ["blocked_instruction_kinds_invalid"]
    normalized = tuple(value)
    if len(set(normalized)) != len(normalized):
        return (), ["blocked_instruction_kinds_duplicate"]
    return normalized, []


def _contains_forbidden_content_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in _FORBIDDEN_CONTENT_KEYS:
                return True
            if _contains_forbidden_content_key(nested):
                return True
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_forbidden_content_key(item) for item in value)
    return False


def _constraint_value_valid(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return len(value) <= 256
    return _finite_number(value)


def _finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, TypeError, ValueError):
        return False


def _bounded_text(value: Any, limit: int) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and _CACHE_KEY_RE.fullmatch(value) is not None


def _append_mismatch(
    reasons: list[str],
    actual: Any,
    expected: Any,
    reason: str,
) -> None:
    if actual != expected:
        reasons.append(reason)


def _blocked(reasons: Sequence[str]) -> ClientInstructionCacheLookupResult:
    return ClientInstructionCacheLookupResult(
        schema_version=_SCHEMA_VERSION,
        status="blocked",
        hit=False,
        entry=None,
        miss_reason=None,
        blocked_reasons=tuple(_unique(reasons)),
    )


def _unique(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result

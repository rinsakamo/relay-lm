"""Pure fail-closed lookup contract for validated client instruction cache entries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
import re
from typing import Any, Literal

from relaylm.client_instruction_identity import ClientInstructionIdentityResult
from relaylm.relayscn import KNOWN_SCENE_TYPES


_SCHEMA_VERSION = "client_instruction_cache_lookup.v0"
_ENTRY_SCHEMA_VERSION = "relaylm.client_instruction_cache.v0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ROLE_SCOPES = frozenset({"turn", "scene"})
_ROLE_SOURCES = frozenset(
    {"client_system", "client_developer", "mixed", "client_instruction_cache"}
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
_FORBIDDEN_DIAGNOSTIC_KEYS = _FORBIDDEN_CONTENT_KEYS | frozenset(
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
)


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
        return _resolve_lookup(
            identity_result,
            candidate_entry,
            route_model=route_model,
            character_id=character_id,
            instruction_parse_schema_version=instruction_parse_schema_version,
            authority_policy_version=authority_policy_version,
            parser_version=parser_version,
        )
    except Exception:
        return _blocked("cache_entry_validation_failed")


def _resolve_lookup(
    identity_result: ClientInstructionIdentityResult | None,
    candidate_entry: Mapping[str, Any] | None,
    *,
    route_model: str,
    character_id: str | None,
    instruction_parse_schema_version: str,
    authority_policy_version: str,
    parser_version: str | None,
) -> ClientInstructionCacheLookupResult:
    identity, reasons = _validate_identity(identity_result)
    if reasons:
        return _blocked(*reasons)
    assert identity is not None

    if not _lookup_context_valid(
        route_model,
        character_id,
        instruction_parse_schema_version,
        authority_policy_version,
        parser_version,
    ):
        return _blocked("lookup_context_invalid")

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
        return _blocked("cache_entry_invalid")

    reasons = _validate_entry_header(candidate_entry)
    cache_key = candidate_entry.get("cache_key_sha256")
    fingerprint = candidate_entry.get("instruction_fingerprint_sha256")
    if not _is_sha256(cache_key) or not _is_sha256(fingerprint):
        reasons.append("cache_entry_hash_invalid")
    else:
        _append_mismatch(reasons, cache_key, identity.cache_key_sha256, "cache_key_mismatch")
        _append_mismatch(
            reasons,
            fingerprint,
            identity.instruction_fingerprint_sha256,
            "instruction_fingerprint_mismatch",
        )

    for key, expected, reason in (
        ("route_model", route_model, "route_model_mismatch"),
        ("character_id", character_id, "character_id_mismatch"),
        (
            "instruction_parse_schema_version",
            instruction_parse_schema_version,
            "instruction_parse_schema_version_mismatch",
        ),
        (
            "authority_policy_version",
            authority_policy_version,
            "authority_policy_version_mismatch",
        ),
        ("parser_version", parser_version, "parser_version_mismatch"),
    ):
        _append_mismatch(reasons, candidate_entry.get(key), expected, reason)

    scene, scene_reasons = _parse_scene_state(candidate_entry.get("scene_state"))
    reasons.extend(scene_reasons)

    durable_count = candidate_entry.get("durable_candidate_count")
    if not _bounded_int(durable_count, 64):
        reasons.append("durable_candidate_count_invalid")

    blocked_kinds, kind_reasons = _parse_bounded_strings(
        candidate_entry.get("blocked_instruction_kinds"),
        max_items=32,
        max_length=64,
        invalid_reason="blocked_instruction_kinds_invalid",
        duplicate_reason="blocked_instruction_kinds_duplicate",
    )
    reasons.extend(kind_reasons)
    reasons = _unique(reasons)
    if reasons:
        return _blocked(*reasons)

    assert scene is not None
    scene_type, scene_role, scene_context, constraints = scene
    return ClientInstructionCacheLookupResult(
        schema_version=_SCHEMA_VERSION,
        status="hit",
        hit=True,
        entry=ClientInstructionCacheEntry(
            schema_version=_ENTRY_SCHEMA_VERSION,
            cache_key_sha256=cache_key,
            instruction_fingerprint_sha256=fingerprint,
            route_model=route_model,
            character_id=character_id,
            instruction_parse_schema_version=instruction_parse_schema_version,
            authority_policy_version=authority_policy_version,
            parser_version=parser_version,
            scene_type=scene_type,
            scene_role=scene_role,
            scene_context=scene_context,
            scene_constraints=constraints,
            durable_candidate_count=durable_count,
            blocked_instruction_kinds=blocked_kinds,
            raw_instruction_persisted=False,
            raw_response_persisted=False,
            runtime_private=True,
            content_bearing=True,
        ),
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
        "scene_constraint_count": len(entry.scene_constraints) if entry else 0,
        "durable_candidate_count": entry.durable_candidate_count if entry else 0,
        "blocked_instruction_kind_count": len(entry.blocked_instruction_kinds) if entry else 0,
        "raw_instruction_persisted": entry.raw_instruction_persisted if entry else False,
        "raw_response_persisted": entry.raw_response_persisted if entry else False,
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
            assert_client_instruction_cache_lookup_diagnostics_content_free(nested)
        return
    if _is_sequence(value):
        for nested in value:
            assert_client_instruction_cache_lookup_diagnostics_content_free(nested)
        return
    if _is_sha256(value):
        raise ValueError("hash value is not allowed in diagnostics")


def _validate_identity(identity_result: Any) -> tuple[Any | None, list[str]]:
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
    if identity.empty_instruction is True or len(identity.candidates) == 0:
        return None, ["source_instruction_candidates_missing"]
    if (
        identity.runtime_private is not True
        or identity.content_bearing is not True
        or not _is_sha256(identity.cache_key_sha256)
        or not _is_sha256(identity.instruction_fingerprint_sha256)
    ):
        return None, ["source_identity_invalid"]
    return identity, []


def _validate_entry_header(entry: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    keys = {str(key) for key in entry}
    if keys - _TOP_LEVEL_KEYS:
        reasons.append("cache_entry_unknown_field")
    if _TOP_LEVEL_KEYS - keys:
        reasons.append("cache_entry_missing_field")
    if _contains_forbidden_key(entry):
        reasons.append("cache_entry_content_forbidden")
    _append_mismatch(
        reasons,
        entry.get("schema_version"),
        _ENTRY_SCHEMA_VERSION,
        "cache_entry_schema_unsupported",
    )
    _append_mismatch(
        reasons,
        entry.get("parse_status"),
        "valid",
        "cache_entry_parse_status_invalid",
    )
    if entry.get("raw_instruction_persisted") is not False:
        reasons.append("raw_instruction_persisted_not_false")
    if entry.get("raw_response_persisted") is not False:
        reasons.append("raw_response_persisted_not_false")
    return reasons


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
    if not isinstance(value, Mapping):
        return None, ["scene_state_invalid"]
    reasons: list[str] = []
    if {str(key) for key in value} != _SCENE_STATE_KEYS:
        reasons.append("scene_state_unknown_or_missing_field")

    scene_type = value.get("scene_type")
    if not isinstance(scene_type, str) or scene_type not in KNOWN_SCENE_TYPES:
        reasons.append("scene_type_invalid")
    role, role_reasons = _parse_scene_role(value.get("scene_role"))
    context, context_reasons = _parse_scene_context(value.get("scene_context"))
    constraints, constraint_reasons = _parse_constraints(value.get("scene_constraints"))
    reasons.extend(role_reasons + context_reasons + constraint_reasons)
    if reasons:
        return None, _unique(reasons)
    assert isinstance(scene_type, str) and context is not None and constraints is not None
    return (scene_type, role, context, constraints), []


def _parse_scene_role(value: Any) -> tuple[CachedInstructionSceneRole | None, list[str]]:
    if value is None:
        return None, []
    if not isinstance(value, Mapping):
        return None, ["scene_role_invalid"]
    reasons: list[str] = []
    if {str(key) for key in value} != _SCENE_ROLE_KEYS:
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
    if not _probability(confidence):
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
    if {str(key) for key in value} != _SCENE_CONTEXT_KEYS:
        reasons.append("scene_context_unknown_or_missing_field")
    setting = value.get("setting")
    task = value.get("task")
    if setting is not None and not _bounded_text(setting, 256):
        reasons.append("scene_context_setting_invalid")
    if task is not None and not _bounded_text(task, 256):
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
    return CachedInstructionSceneContext(setting, task, participants), []


def _parse_constraints(
    value: Any,
) -> tuple[tuple[CachedInstructionSceneConstraint, ...] | None, list[str]]:
    if not _is_sequence(value) or len(value) > 32:
        return None, ["scene_constraints_invalid"]
    constraints: list[CachedInstructionSceneConstraint] = []
    reasons: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            reasons.append("scene_constraint_invalid")
            continue
        if {str(key) for key in item} != _SCENE_CONSTRAINT_KEYS:
            reasons.append("scene_constraint_unknown_or_missing_field")
        constraint_type = item.get("constraint_type")
        constraint_value = item.get("value")
        if not _bounded_text(constraint_type, 64):
            reasons.append("scene_constraint_type_invalid")
        if not _constraint_value_valid(constraint_value):
            reasons.append("scene_constraint_value_invalid")
        if _bounded_text(constraint_type, 64) and _constraint_value_valid(constraint_value):
            constraints.append(
                CachedInstructionSceneConstraint(constraint_type, constraint_value)
            )
    if reasons:
        return None, _unique(reasons)
    return tuple(constraints), []


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
        or any(not _bounded_text(item, max_length) for item in value)
    ):
        return (), [invalid_reason]
    result = tuple(value)
    if duplicate_reason is not None and len(set(result)) != len(result):
        return (), [duplicate_reason]
    return result, []


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in _FORBIDDEN_CONTENT_KEYS or _contains_forbidden_key(nested)
            for key, nested in value.items()
        )
    if _is_sequence(value):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _lookup_context_valid(*values: Any) -> bool:
    route_model, character_id, parse_version, policy_version, parser_version = values
    return (
        _bounded_text(route_model, 128)
        and (character_id is None or _bounded_text(character_id, 128))
        and _bounded_text(parse_version, 128)
        and _bounded_text(policy_version, 128)
        and (parser_version is None or _bounded_text(parser_version, 128))
    )


def _constraint_value_valid(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return len(value) <= 256
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


def _bounded_int(value: Any, maximum: int) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value <= maximum
    )


def _bounded_text(value: Any, maximum: int) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _append_mismatch(
    reasons: list[str], actual: Any, expected: Any, reason: str
) -> None:
    if actual != expected:
        reasons.append(reason)


def _blocked(*reasons: str) -> ClientInstructionCacheLookupResult:
    return ClientInstructionCacheLookupResult(
        schema_version=_SCHEMA_VERSION,
        status="blocked",
        hit=False,
        entry=None,
        miss_reason=None,
        blocked_reasons=tuple(_unique(reasons)),
    )


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))

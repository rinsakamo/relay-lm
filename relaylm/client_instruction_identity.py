"""Deterministic runtime-private identity for client instruction evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Literal
import unicodedata


_SCHEMA_VERSION = "client_instruction_identity.v0"
_EXPECTED_EXTRACTION_SCHEMA_VERSION = "client_instruction_extraction_dry_run.v0"
_NORMALIZED_SCHEMA_VERSION = "client_instruction_normalized.v0"
_CACHE_KEY_SCHEMA_VERSION = "client_instruction_cache_key.v0"
_INSTRUCTION_ROLES = frozenset({"system", "developer"})
_TEXT_PART_TYPES = frozenset({"text", "input_text"})
_MAX_CONTEXT_VERSION_LENGTH = 128
_FORBIDDEN_DIAGNOSTIC_KEYS = frozenset(
    {
        "content",
        "text",
        "normalized_text",
        "raw_content",
        "raw_message",
        "messages",
        "prompt",
        "canonical_json",
        "instruction_fingerprint_sha256",
        "cache_key_sha256",
        "route_model",
        "character_id",
        "tool_call_id",
        "url",
    }
)


@dataclass(frozen=True)
class NormalizedInstructionCandidate:
    role: Literal["system", "developer"]
    source_index: int
    normalized_text: str


@dataclass(frozen=True)
class ClientInstructionIdentity:
    schema_version: str
    candidates: tuple[NormalizedInstructionCandidate, ...]
    empty_instruction: bool
    instruction_fingerprint_sha256: str
    cache_key_sha256: str
    runtime_private: bool
    content_bearing: bool


@dataclass(frozen=True)
class ClientInstructionIdentityResult:
    schema_version: str
    ready: bool
    identity: ClientInstructionIdentity | None
    blocked_reasons: tuple[str, ...]


def build_client_instruction_identity(
    payload: Mapping[str, Any] | None,
    extraction_artifact: Mapping[str, Any] | None,
    *,
    enabled: bool,
    route_model: str,
    character_id: str | None,
    instruction_parse_schema_version: str = "client_instruction_parse.v1",
    authority_policy_version: str = "client_instruction_authority.v1",
    parser_version: str | None = None,
) -> ClientInstructionIdentityResult | None:
    """Build a deterministic, content-bearing instruction identity artifact.

    The returned identity is runtime-private. It intentionally contains
    normalized instruction text and hash values, so callers must not place it in
    traces, PipelineNodeResults, RequestDiagnostics, or forwarded payloads.
    """

    if not enabled:
        return None

    blocked_reasons: list[str] = []
    if not isinstance(extraction_artifact, Mapping):
        blocked_reasons.append("source_extraction_artifact_missing")
    else:
        if extraction_artifact.get("schema_version") != _EXPECTED_EXTRACTION_SCHEMA_VERSION:
            blocked_reasons.append("source_extraction_schema_unsupported")
        if extraction_artifact.get("content_free") is not True:
            blocked_reasons.append("source_extraction_not_content_free")
        if extraction_artifact.get("fingerprint_candidate_ready") is not True:
            blocked_reasons.append("source_extraction_not_ready")
        if extraction_artifact.get("managed_route") is not True:
            blocked_reasons.append("source_extraction_not_managed")
        if _strings(extraction_artifact.get("blocked_reasons")):
            blocked_reasons.append("source_extraction_blocked")
        raw_candidate_roles = extraction_artifact.get("candidate_roles")
        if (
            not isinstance(raw_candidate_roles, Sequence)
            or isinstance(raw_candidate_roles, (str, bytes, bytearray))
            or any(
                not isinstance(role, str) or role not in _INSTRUCTION_ROLES
                for role in raw_candidate_roles
            )
        ):
            blocked_reasons.append("instruction_candidate_role_invalid")
        if extraction_artifact.get("active_tool_transaction_candidate") is True:
            blocked_reasons.append("active_tool_transaction_requires_preservation")

    if not _bounded_non_empty_string(route_model):
        blocked_reasons.append("route_model_invalid")
    if not _identity_context_valid(
        character_id=character_id,
        instruction_parse_schema_version=instruction_parse_schema_version,
        authority_policy_version=authority_policy_version,
        parser_version=parser_version,
    ):
        blocked_reasons.append("identity_context_version_invalid")

    messages: list[Any] | None = None
    if not isinstance(payload, Mapping) or not isinstance(payload.get("messages"), list):
        blocked_reasons.append("messages_not_list")
    else:
        messages = payload["messages"]
        if _payload_has_active_tool_transaction(messages):
            blocked_reasons.append("active_tool_transaction_requires_preservation")

    candidate_indices: list[int] = []
    if isinstance(extraction_artifact, Mapping):
        raw_candidate_indices = extraction_artifact.get("candidate_indices")
        if _candidate_indices_valid(raw_candidate_indices, messages):
            candidate_indices = list(raw_candidate_indices)
        else:
            blocked_reasons.append("candidate_indices_invalid")
        raw_count = extraction_artifact.get("instruction_candidate_count")
        if not isinstance(raw_count, int) or isinstance(raw_count, bool) or raw_count < 0:
            blocked_reasons.append("instruction_candidate_count_invalid")
        elif raw_count != len(candidate_indices):
            blocked_reasons.append("instruction_candidate_count_mismatch")

    normalized_candidates: list[NormalizedInstructionCandidate] = []
    if messages is not None and candidate_indices:
        payload_instruction_indices = [
            index
            for index, message in enumerate(messages)
            if isinstance(message, Mapping) and message.get("role") in _INSTRUCTION_ROLES
        ]
        if payload_instruction_indices != candidate_indices:
            blocked_reasons.append("candidate_indices_mismatch")
        if isinstance(extraction_artifact, Mapping):
            actual_candidate_roles = _unique_in_order(
                [
                    str(messages[index].get("role"))
                    for index in candidate_indices
                    if isinstance(messages[index], Mapping)
                    and messages[index].get("role") in _INSTRUCTION_ROLES
                ]
            )
            raw_candidate_roles = extraction_artifact.get("candidate_roles")
            if (
                isinstance(raw_candidate_roles, Sequence)
                and not isinstance(raw_candidate_roles, (str, bytes, bytearray))
                and list(raw_candidate_roles) != actual_candidate_roles
            ):
                blocked_reasons.append("candidate_roles_mismatch")

        for index in candidate_indices:
            message = messages[index]
            if not isinstance(message, Mapping):
                blocked_reasons.append("candidate_indices_invalid")
                continue
            role = message.get("role")
            if role not in _INSTRUCTION_ROLES:
                blocked_reasons.append("instruction_candidate_role_invalid")
                continue
            normalized_text, content_reasons = _normalized_instruction_text(
                message.get("content")
            )
            blocked_reasons.extend(content_reasons)
            if normalized_text is not None:
                normalized_candidates.append(
                    NormalizedInstructionCandidate(
                        role=role,  # type: ignore[arg-type]
                        source_index=index,
                        normalized_text=normalized_text,
                    )
                )
    elif messages is not None and candidate_indices == [] and isinstance(extraction_artifact, Mapping):
        payload_instruction_indices = [
            index
            for index, message in enumerate(messages)
            if isinstance(message, Mapping) and message.get("role") in _INSTRUCTION_ROLES
        ]
        if payload_instruction_indices:
            blocked_reasons.append("candidate_indices_mismatch")
        if isinstance(extraction_artifact, Mapping):
            raw_candidate_roles = extraction_artifact.get("candidate_roles")
            if (
                isinstance(raw_candidate_roles, Sequence)
                and not isinstance(raw_candidate_roles, (str, bytes, bytearray))
                and list(raw_candidate_roles) != []
            ):
                blocked_reasons.append("candidate_roles_mismatch")

    blocked_reasons = _unique_in_order(blocked_reasons)
    if blocked_reasons:
        return ClientInstructionIdentityResult(
            schema_version=_SCHEMA_VERSION,
            ready=False,
            identity=None,
            blocked_reasons=tuple(blocked_reasons),
        )

    candidates_tuple = tuple(normalized_candidates)
    empty_instruction = len(candidates_tuple) == 0
    fingerprint_sha256 = _sha256_json(
        {
            "schema_version": _NORMALIZED_SCHEMA_VERSION,
            "empty_instruction": empty_instruction,
            "candidates": [
                {"role": candidate.role, "text": candidate.normalized_text}
                for candidate in candidates_tuple
            ],
        }
    )
    cache_key_sha256 = _sha256_json(
        {
            "schema_version": _CACHE_KEY_SCHEMA_VERSION,
            "instruction_fingerprint_sha256": fingerprint_sha256,
            "route_model": route_model,
            "character_id": character_id,
            "instruction_parse_schema_version": instruction_parse_schema_version,
            "authority_policy_version": authority_policy_version,
            "parser_version": parser_version,
        }
    )
    identity = ClientInstructionIdentity(
        schema_version=_SCHEMA_VERSION,
        candidates=candidates_tuple,
        empty_instruction=empty_instruction,
        instruction_fingerprint_sha256=fingerprint_sha256,
        cache_key_sha256=cache_key_sha256,
        runtime_private=True,
        content_bearing=True,
    )
    return ClientInstructionIdentityResult(
        schema_version=_SCHEMA_VERSION,
        ready=True,
        identity=identity,
        blocked_reasons=(),
    )


def build_client_instruction_identity_diagnostics(
    result: ClientInstructionIdentityResult | None,
) -> dict[str, Any] | None:
    """Build a content-free diagnostics summary for an identity result."""

    if result is None:
        return None

    identity = result.identity
    candidates = identity.candidates if identity is not None else ()
    summary = {
        "schema_version": _SCHEMA_VERSION,
        "enabled": True,
        "ready": result.ready,
        "runtime_private_artifact_present": identity is not None,
        "content_bearing_artifact_present": identity is not None,
        "instruction_candidate_count": len(candidates),
        "candidate_roles": [candidate.role for candidate in candidates],
        "candidate_indices": [candidate.source_index for candidate in candidates],
        "empty_instruction": identity.empty_instruction if identity is not None else False,
        "normalization_applied": identity is not None,
        "instruction_fingerprint_computed": identity is not None,
        "cache_key_computed": identity is not None,
        "hash_algorithm": "sha256" if identity is not None else None,
        "blocked_reasons": list(result.blocked_reasons),
    }
    assert_client_instruction_identity_diagnostics_content_free(summary)
    return summary


def assert_client_instruction_identity_diagnostics_content_free(value: Any) -> None:
    """Fail if identity diagnostics expose content-bearing fields."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in _FORBIDDEN_DIAGNOSTIC_KEYS:
                raise ValueError(f"content-bearing key is not allowed: {key}")
            if _looks_like_sha256(nested):
                raise ValueError(f"hash value is not allowed in diagnostics: {key}")
            assert_client_instruction_identity_diagnostics_content_free(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            assert_client_instruction_identity_diagnostics_content_free(nested)
    elif _looks_like_sha256(value):
        raise ValueError("hash value is not allowed in diagnostics")


def _normalized_instruction_text(content: Any) -> tuple[str | None, list[str]]:
    if isinstance(content, str):
        normalized = _normalize_text(content)
        if not normalized:
            return None, ["instruction_candidate_content_invalid"]
        return normalized, []

    if not isinstance(content, list) or not content:
        return None, ["instruction_candidate_content_invalid"]

    normalized_parts: list[str] = []
    blocked_reasons: list[str] = []
    for part in content:
        if not isinstance(part, Mapping):
            blocked_reasons.append("instruction_candidate_content_invalid")
            continue
        part_type = part.get("type")
        if part_type not in _TEXT_PART_TYPES:
            if isinstance(part_type, str) and part_type:
                blocked_reasons.append(
                    "multimodal_instruction_candidate_requires_preservation"
                )
            else:
                blocked_reasons.append("instruction_candidate_content_invalid")
            continue
        part_text = part.get("text")
        if not isinstance(part_text, str):
            blocked_reasons.append("instruction_candidate_content_invalid")
            continue
        normalized_part = _normalize_text(part_text)
        if not normalized_part:
            blocked_reasons.append("instruction_candidate_content_invalid")
            continue
        normalized_parts.append(normalized_part)

    if blocked_reasons:
        return None, _unique_in_order(blocked_reasons)
    if not normalized_parts:
        return None, ["instruction_candidate_content_invalid"]
    return "\n".join(normalized_parts), []


def _normalize_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = unicodedata.normalize("NFC", value)
    value = "\n".join(line.rstrip(" \t") for line in value.split("\n"))
    return value.strip()


def _latest_user_message_index(messages: Sequence[Any]) -> int | None:
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if isinstance(message, Mapping) and message.get("role") == "user":
            return index
    return None


def _payload_has_active_tool_transaction(messages: Sequence[Any]) -> bool:
    latest_user_index = _latest_user_message_index(messages)
    if latest_user_index is None:
        return False

    for message in messages[latest_user_index + 1 :]:
        if not isinstance(message, Mapping):
            continue

        if (
            message.get("role") == "assistant"
            and isinstance(message.get("tool_calls"), list)
            and bool(message.get("tool_calls"))
        ):
            return True

        if message.get("role") == "tool":
            return True

    return False


def _candidate_indices_valid(value: Any, messages: list[Any] | None) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return False
    previous = -1
    seen: set[int] = set()
    message_count = len(messages) if messages is not None else None
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool):
            return False
        if item in seen or item <= previous:
            return False
        if item < 0 or (message_count is not None and item >= message_count):
            return False
        seen.add(item)
        previous = item
    return True


def _identity_context_valid(
    *,
    character_id: str | None,
    instruction_parse_schema_version: str,
    authority_policy_version: str,
    parser_version: str | None,
) -> bool:
    if character_id is not None and not _bounded_non_empty_string(character_id):
        return False
    return all(
        _bounded_non_empty_string(value)
        for value in (instruction_parse_schema_version, authority_policy_version)
    ) and (parser_version is None or _bounded_non_empty_string(parser_version))


def _bounded_non_empty_string(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and len(value) <= _MAX_CONTEXT_VERSION_LENGTH
    )


def _sha256_json(value: Mapping[str, Any]) -> str:
    canonical_json = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _looks_like_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)


def _unique_in_order(values: Sequence[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return unique

"""Explicit request-local provenance for client instruction evidence."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from relaylm.client_instruction_identity import (
    ClientInstructionIdentityResult,
    NormalizedInstructionCandidate,
)


SCHEMA_VERSION = "client_instruction_source.v1"
CONTROL_NAMESPACE = "relaylm"
CONTROL_FIELD = "instruction_evidence"
_INSTRUCTION_ROLES = frozenset({"system", "developer"})
_MAX_SELECTED_INDICES = 64


@dataclass(frozen=True, repr=False)
class ClientInstructionEvidenceSelection:
    schema_version: str
    source_mode: Literal["explicit"]
    provenance_present: bool
    ready: bool
    selected_source_indices: tuple[int, ...]
    excluded_source_indices: tuple[int, ...]
    blocked_reasons: tuple[str, ...]
    runtime_private: bool = True


def select_client_instruction_evidence(
    original_payload: Mapping[str, Any] | None,
    identity_result: ClientInstructionIdentityResult | None,
) -> ClientInstructionEvidenceSelection:
    """Select only explicitly provenanced identity candidates.

    Role, content, and position are not sufficient provenance. Managed v1 apply
    accepts only source indices declared through the reserved request-local
    ``relaylm.instruction_evidence`` control envelope.
    """

    reasons: list[str] = []
    payload = original_payload if isinstance(original_payload, Mapping) else None
    messages = payload.get("messages") if payload is not None else None
    identity = identity_result.identity if identity_result is not None else None
    candidates = identity.candidates if identity is not None else ()
    all_indices = tuple(candidate.source_index for candidate in candidates)

    envelope: Mapping[str, Any] | None = None
    if payload is None:
        reasons.append("instruction_source_provenance_missing")
    else:
        namespace = payload.get(CONTROL_NAMESPACE)
        if namespace is None:
            reasons.append("instruction_source_provenance_missing")
        elif not isinstance(namespace, Mapping):
            reasons.append("instruction_source_control_invalid")
        else:
            raw_envelope = namespace.get(CONTROL_FIELD)
            if raw_envelope is None:
                reasons.append("instruction_source_provenance_missing")
            elif not isinstance(raw_envelope, Mapping):
                reasons.append("instruction_source_control_invalid")
            else:
                envelope = raw_envelope

    selected_indices: tuple[int, ...] = ()
    if envelope is not None:
        if set(envelope.keys()) != {"schema_version", "message_indices"}:
            reasons.append("instruction_source_control_invalid")
        if envelope.get("schema_version") != SCHEMA_VERSION:
            reasons.append("instruction_source_schema_unsupported")
        raw_indices = envelope.get("message_indices")
        if _indices_valid(raw_indices):
            selected_indices = tuple(raw_indices)
        else:
            reasons.append("instruction_source_indices_invalid")

    if not isinstance(messages, list):
        reasons.append("instruction_source_indices_invalid")
        messages = []
    latest_user_index = _latest_user_index(messages)
    candidate_by_index = {candidate.source_index: candidate for candidate in candidates}
    for index in selected_indices:
        if index >= len(messages):
            reasons.append("instruction_source_indices_invalid")
            continue
        message = messages[index]
        if not isinstance(message, Mapping) or message.get("role") not in _INSTRUCTION_ROLES:
            reasons.append("instruction_source_role_mismatch")
            continue
        if latest_user_index is None or index >= latest_user_index:
            reasons.append("instruction_source_after_current_user")
        candidate = candidate_by_index.get(index)
        if candidate is None or candidate.role != message.get("role"):
            reasons.append("instruction_source_identity_mismatch")

    if not selected_indices and envelope is not None:
        reasons.append("instruction_source_indices_invalid")
    if identity_result is None or identity is None or identity_result.ready is not True:
        reasons.append("instruction_source_identity_mismatch")

    reasons = _unique(reasons)
    selected_set = set(selected_indices)
    excluded_indices = tuple(index for index in all_indices if index not in selected_set)
    return ClientInstructionEvidenceSelection(
        schema_version=SCHEMA_VERSION,
        source_mode="explicit",
        provenance_present=envelope is not None,
        ready=not reasons,
        selected_source_indices=selected_indices if not reasons else (),
        excluded_source_indices=excluded_indices,
        blocked_reasons=tuple(reasons),
    )


def selected_candidates(
    identity_result: ClientInstructionIdentityResult,
    selection: ClientInstructionEvidenceSelection,
) -> tuple[NormalizedInstructionCandidate, ...]:
    """Return selected candidates in the explicit provenance order."""

    identity = identity_result.identity
    if identity is None or selection.ready is not True:
        return ()
    by_index = {candidate.source_index: candidate for candidate in identity.candidates}
    return tuple(by_index[index] for index in selection.selected_source_indices)


def strip_relaylm_control(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a shallow detached payload without RelayLM's control namespace."""

    result = dict(payload)
    result.pop(CONTROL_NAMESPACE, None)
    return result


def _indices_valid(value: Any) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return False
    if not value or len(value) > _MAX_SELECTED_INDICES:
        return False
    previous = -1
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool) or item < 0:
            return False
        if item <= previous:
            return False
        previous = item
    return True


def _latest_user_index(messages: Sequence[Any]) -> int | None:
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if isinstance(message, Mapping) and message.get("role") == "user":
            return index
    return None


def _unique(values: Sequence[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            output.append(value)
            seen.add(value)
    return output

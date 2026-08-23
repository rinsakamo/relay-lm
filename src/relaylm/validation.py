from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Literal, Mapping
from uuid import uuid4

from relaylm.events import Event
from relaylm.state import (
    CanonicalState,
    STATE_CLASS_DEFINITIONS,
    USER_PREFERENCE_GENERIC_KEYS,
    StateCandidate,
    StateRecord,
    _degree_hint_rejection,
    is_state_json_value,
)

DecisionStatus = Literal["accepted", "noop", "rejected"]
DecisionAction = Literal["create", "replace", "remove"] | None


@dataclass(frozen=True, slots=True)
class CandidateDecision:
    candidate: StateCandidate
    status: DecisionStatus
    action: DecisionAction = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    state: CanonicalState
    decisions: tuple[CandidateDecision, ...]
    changed: bool


def apply_state_candidates(
    *,
    current_state: CanonicalState,
    candidates: Iterable[StateCandidate],
    events: Mapping[str, Event],
    required_source_ids: frozenset[str] = frozenset(),
) -> ValidationResult:
    """Validate proposals deterministically and derive current-State transitions."""

    records = list(current_state.states)
    decisions: list[CandidateDecision] = []
    changed = False

    for candidate in candidates:
        rejection = _rejection_reason(candidate, events, required_source_ids)
        if rejection is not None:
            decisions.append(
                CandidateDecision(candidate=candidate, status="rejected", reason=rejection)
            )
            continue

        key = (candidate.state_class, candidate.key)
        existing_index = _current_record_index(records, key)
        existing = records[existing_index] if existing_index is not None else None

        if candidate.op == "remove":
            if existing_index is None:
                decisions.append(CandidateDecision(candidate=candidate, status="noop"))
                continue
            records.pop(existing_index)
            changed = True
            decisions.append(
                CandidateDecision(candidate=candidate, status="accepted", action="remove")
            )
            continue

        if existing is not None and _state_values_equal(existing.value, candidate.value):
            decisions.append(CandidateDecision(candidate=candidate, status="noop"))
            continue

        now = datetime.now(timezone.utc).isoformat()
        replacement = StateRecord(
            state_id=str(uuid4()),
            state_class=candidate.state_class,
            key=candidate.key,
            value=candidate.value,
            sources=tuple(dict.fromkeys(candidate.sources)),
            valid_from=now,
        )
        if existing_index is None:
            records.append(replacement)
        else:
            records[existing_index] = replacement
        changed = True
        decisions.append(
            CandidateDecision(
                candidate=candidate,
                status="accepted",
                action="replace" if existing is not None else "create",
            )
        )

    next_state = CanonicalState(
        format_version=current_state.format_version,
        states=tuple(records),
    )
    return ValidationResult(
        state=next_state,
        decisions=tuple(decisions),
        changed=changed,
    )


def _state_values_equal(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right

    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if left.keys() != right.keys():
            return False
        return all(_state_values_equal(left[key], right[key]) for key in left)

    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _state_values_equal(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )

    if isinstance(left, tuple) and isinstance(right, tuple):
        return len(left) == len(right) and all(
            _state_values_equal(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )

    return left == right


def _current_record_index(
    records: list[StateRecord],
    key: tuple[str, str],
) -> int | None:
    for index, record in enumerate(records):
        if record.status != "active" or record.valid_to is not None:
            continue
        if (record.state_class, record.key) == key:
            return index
    return None


def _rejection_reason(
    candidate: StateCandidate,
    events: Mapping[str, Event],
    required_source_ids: frozenset[str],
) -> str | None:
    if candidate.state_class not in STATE_CLASS_DEFINITIONS:
        return "unsupported_state_class"
    if (
        candidate.state_class == "user.preference"
        and candidate.key.strip().casefold() in USER_PREFERENCE_GENERIC_KEYS
    ):
        return "generic_preference_key"
    if not candidate.sources:
        return "missing_sources"
    if any(source not in events for source in candidate.sources):
        return "unknown_source"
    if required_source_ids and not required_source_ids.intersection(candidate.sources):
        return "missing_current_evidence"
    if candidate.state_class.startswith("user.") and not any(
        events[source].actor == "user" for source in candidate.sources
    ):
        return "user_state_requires_user_source"
    if candidate.op == "set":
        degree_rejection = _degree_hint_rejection(candidate.value)
        if degree_rejection is not None:
            return degree_rejection
        if not is_state_json_value(candidate.value):
            return "non_json_value"
    return None

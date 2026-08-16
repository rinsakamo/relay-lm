from __future__ import annotations

import json
import math
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

    ordered_keys: list[tuple[str, str]] = []
    current: dict[tuple[str, str], StateRecord] = {}
    for record in current_state.states:
        key = (record.state_class, record.key)
        if key not in current:
            ordered_keys.append(key)
        current[key] = record

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
        existing = current.get(key)

        if candidate.op == "remove":
            if existing is None:
                decisions.append(CandidateDecision(candidate=candidate, status="noop"))
                continue
            del current[key]
            ordered_keys = [item for item in ordered_keys if item != key]
            changed = True
            decisions.append(
                CandidateDecision(candidate=candidate, status="accepted", action="remove")
            )
            continue

        if existing is not None and existing.value == candidate.value:
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
        current[key] = replacement
        if key not in ordered_keys:
            ordered_keys.append(key)
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
        states=tuple(current[key] for key in ordered_keys if key in current),
    )
    return ValidationResult(
        state=next_state,
        decisions=tuple(decisions),
        changed=changed,
    )


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
        try:
            json.dumps(candidate.value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError):
            return "non_json_value"
    return None


def _degree_hint_rejection(value: object) -> str | None:
    """Validate the reserved optional semantic degree-hint envelope without inferring meaning."""

    if not isinstance(value, Mapping):
        return None
    if "semantic" not in value and "degree_hint" not in value:
        return None
    if set(value) != {"semantic", "degree_hint"}:
        return "invalid_degree_hint_value"

    semantic = value.get("semantic")
    degree = value.get("degree_hint")
    if not isinstance(semantic, str) or not semantic.strip():
        return "invalid_degree_hint_value"
    if isinstance(degree, bool) or not isinstance(degree, (int, float)):
        return "invalid_degree_hint_value"
    if not math.isfinite(float(degree)) or not 0.0 <= float(degree) <= 1.0:
        return "invalid_degree_hint_value"
    return None

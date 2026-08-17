from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Literal, Mapping

from relaylm.continuity import (
    ContinuityCandidate,
    ContinuityContext,
    ContinuityItem,
    freeze_continuity_value,
)
from relaylm.events import Event

ContinuityDecisionStatus = Literal["accepted", "noop", "rejected"]
ContinuityDecisionAction = Literal["admit", "supersede", "resolve"] | None


@dataclass(frozen=True, slots=True)
class ContinuityDecision:
    """Deterministic disposition of one ContinuityCandidate."""

    candidate: ContinuityCandidate
    status: ContinuityDecisionStatus
    action: ContinuityDecisionAction = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ContinuityValidationResult:
    """One revision transition of temporary Continuity Context."""

    context: ContinuityContext
    decisions: tuple[ContinuityDecision, ...]
    expired_item_ids: tuple[str, ...]
    evicted_item_ids: tuple[str, ...]
    changed: bool


def apply_continuity_candidates(
    *,
    current_context: ContinuityContext,
    candidates: Iterable[ContinuityCandidate],
    events: Mapping[str, Event],
    lifetime_revisions: int,
    required_source_ids: frozenset[str] = frozenset(),
) -> ContinuityValidationResult:
    """Advance one deterministic Continuity Context revision.

    Lifetime and capacity are explicit inputs/attributes rather than hidden runtime
    policy. Expiry happens at the new revision before candidates are evaluated.
    """

    if isinstance(lifetime_revisions, bool) or not isinstance(lifetime_revisions, int):
        raise TypeError("lifetime_revisions must be an integer")
    if lifetime_revisions <= 0:
        raise ValueError("lifetime_revisions must be positive")

    next_revision = current_context.revision + 1
    expired_item_ids = tuple(
        item.item_id
        for item in current_context.items
        if item.expires_revision <= next_revision
    )
    items = [
        item
        for item in current_context.items
        if item.expires_revision > next_revision
    ]

    decisions: list[ContinuityDecision] = []
    changed = bool(expired_item_ids)

    for candidate_index, candidate in enumerate(candidates, start=1):
        rejection = _rejection_reason(candidate, events, required_source_ids)
        if rejection is not None:
            decisions.append(
                ContinuityDecision(
                    candidate=candidate,
                    status="rejected",
                    reason=rejection,
                )
            )
            continue

        existing_index = _find_key_index(items, candidate.key)
        existing = items[existing_index] if existing_index is not None else None

        if candidate.op == "resolve":
            if existing is None:
                decisions.append(
                    ContinuityDecision(
                        candidate=candidate,
                        status="noop",
                        reason="not_found",
                    )
                )
                continue
            if existing.kind != candidate.kind:
                decisions.append(
                    ContinuityDecision(
                        candidate=candidate,
                        status="rejected",
                        reason="kind_mismatch",
                    )
                )
                continue
            assert existing_index is not None
            items.pop(existing_index)
            changed = True
            decisions.append(
                ContinuityDecision(
                    candidate=candidate,
                    status="accepted",
                    action="resolve",
                )
            )
            continue

        sources = tuple(dict.fromkeys(candidate.sources))
        if existing is not None and _is_exact_duplicate(existing, candidate, sources):
            decisions.append(
                ContinuityDecision(
                    candidate=candidate,
                    status="noop",
                    reason="duplicate",
                )
            )
            continue

        replacement = ContinuityItem(
            item_id=f"continuity:{next_revision}:{candidate_index}",
            kind=candidate.kind,
            key=candidate.key,
            value=candidate.value,
            sources=sources,
            epistemic_role=candidate.epistemic_role,
            accepted_revision=next_revision,
            expires_revision=next_revision + lifetime_revisions,
        )
        action: ContinuityDecisionAction
        if existing_index is None:
            items.append(replacement)
            action = "admit"
        else:
            items.pop(existing_index)
            items.append(replacement)
            action = "supersede"
        changed = True
        decisions.append(
            ContinuityDecision(
                candidate=candidate,
                status="accepted",
                action=action,
            )
        )

    evicted_item_ids: list[str] = []
    while len(items) > current_context.max_items:
        oldest_index = min(
            range(len(items)),
            key=lambda index: (items[index].accepted_revision, index),
        )
        evicted_item_ids.append(items.pop(oldest_index).item_id)
        changed = True

    context = ContinuityContext(
        max_items=current_context.max_items,
        revision=next_revision,
        items=tuple(items),
    )
    return ContinuityValidationResult(
        context=context,
        decisions=tuple(decisions),
        expired_item_ids=expired_item_ids,
        evicted_item_ids=tuple(evicted_item_ids),
        changed=changed,
    )


def _rejection_reason(
    candidate: ContinuityCandidate,
    events: Mapping[str, Event],
    required_source_ids: frozenset[str],
) -> str | None:
    if any(source not in events for source in candidate.sources):
        return "unknown_source"
    if required_source_ids and not required_source_ids.intersection(candidate.sources):
        return "missing_current_evidence"
    if candidate.epistemic_role == "user_assertion" and not any(
        events[source].actor == "user" for source in candidate.sources
    ):
        return "user_assertion_requires_user_source"
    if candidate.op == "set":
        try:
            json.dumps(candidate.value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError):
            return "non_json_value"
    return None


def _find_key_index(items: list[ContinuityItem], key: str) -> int | None:
    for index, item in enumerate(items):
        if item.key == key:
            return index
    return None


def _is_exact_duplicate(
    existing: ContinuityItem,
    candidate: ContinuityCandidate,
    sources: tuple[str, ...],
) -> bool:
    return (
        existing.kind == candidate.kind
        and existing.value == freeze_continuity_value(candidate.value)
        and existing.sources == sources
        and existing.epistemic_role == candidate.epistemic_role
    )

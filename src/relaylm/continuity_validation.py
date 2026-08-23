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
    """One deterministic transition of temporary Continuity Context."""

    context: ContinuityContext
    decisions: tuple[ContinuityDecision, ...]
    expired_item_ids: tuple[str, ...]
    evicted_item_ids: tuple[str, ...]
    changed: bool


def advance_continuity_lifecycle(
    *,
    current_context: ContinuityContext,
    lifetime_revisions: int,
) -> ContinuityValidationResult:
    """Advance the ordinary-turn Continuity clock exactly once and expire due items."""

    _validate_lifetime_revisions(lifetime_revisions)
    next_revision = current_context.revision + 1
    expired_item_ids = tuple(
        item.item_id
        for item in current_context.items
        if item.expires_revision <= next_revision
    )
    context = ContinuityContext(
        max_items=current_context.max_items,
        revision=next_revision,
        items=tuple(
            item
            for item in current_context.items
            if item.expires_revision > next_revision
        ),
    )
    return ContinuityValidationResult(
        context=context,
        decisions=(),
        expired_item_ids=expired_item_ids,
        evicted_item_ids=(),
        changed=bool(expired_item_ids),
    )


def apply_continuity_candidates_at_current_revision(
    *,
    current_context: ContinuityContext,
    candidates: Iterable[ContinuityCandidate],
    events: Mapping[str, Event],
    lifetime_revisions: int,
    required_source_ids: frozenset[str] = frozenset(),
) -> ContinuityValidationResult:
    """Apply candidates at an already-advanced turn revision without advancing again."""

    _validate_lifetime_revisions(lifetime_revisions)
    revision = current_context.revision
    items = list(current_context.items)
    decisions: list[ContinuityDecision] = []
    changed = False

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
            item_id=f"continuity:{revision}:{candidate_index}",
            kind=candidate.kind,
            key=candidate.key,
            value=candidate.value,
            sources=sources,
            epistemic_role=candidate.epistemic_role,
            accepted_revision=revision,
            expires_revision=revision + lifetime_revisions,
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
        revision=revision,
        items=tuple(items),
    )
    return ContinuityValidationResult(
        context=context,
        decisions=tuple(decisions),
        expired_item_ids=(),
        evicted_item_ids=tuple(evicted_item_ids),
        changed=changed,
    )


def apply_continuity_candidates(
    *,
    current_context: ContinuityContext,
    candidates: Iterable[ContinuityCandidate],
    events: Mapping[str, Event],
    lifetime_revisions: int,
    required_source_ids: frozenset[str] = frozenset(),
) -> ContinuityValidationResult:
    """Advance one ordinary-turn revision, then apply candidates at that revision.

    Lifetime and capacity are explicit inputs/attributes rather than hidden runtime
    policy. Expiry happens at the new revision before candidates are evaluated.
    This composed operation preserves the original K2 single-pass semantics while
    allowing response-first two-pass execution to reserve the turn revision before
    its later candidate result arrives.
    """

    lifecycle = advance_continuity_lifecycle(
        current_context=current_context,
        lifetime_revisions=lifetime_revisions,
    )
    candidate_result = apply_continuity_candidates_at_current_revision(
        current_context=lifecycle.context,
        candidates=candidates,
        events=events,
        lifetime_revisions=lifetime_revisions,
        required_source_ids=required_source_ids,
    )
    return ContinuityValidationResult(
        context=candidate_result.context,
        decisions=candidate_result.decisions,
        expired_item_ids=lifecycle.expired_item_ids,
        evicted_item_ids=candidate_result.evicted_item_ids,
        changed=lifecycle.changed or candidate_result.changed,
    )


def _validate_lifetime_revisions(lifetime_revisions: int) -> None:
    if isinstance(lifetime_revisions, bool) or not isinstance(lifetime_revisions, int):
        raise TypeError("lifetime_revisions must be an integer")
    if lifetime_revisions <= 0:
        raise ValueError("lifetime_revisions must be positive")


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

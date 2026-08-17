from __future__ import annotations

from relaylm.continuity import ContinuityCandidate, ContinuityContext, ContinuityItem
from relaylm.continuity_validation import apply_continuity_candidates
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.events import Event


def _event(event_id: str, *, actor: str, minute: int) -> Event:
    return Event.create(
        type="message",
        actor=actor,
        payload={"content": f"evidence for {event_id}"},
        event_id=event_id,
        timestamp=f"2026-08-17T13:{minute:02d}:00+00:00",
    )


def _candidate(
    *,
    kind: str,
    key: str,
    value: object,
    source: str,
) -> ContinuityCandidate:
    return ContinuityCandidate.set(
        kind=kind,
        key=key,
        value=value,
        sources=(source,),
        epistemic_role="user_assertion",
    )


async def evaluate_continuity_lifecycle() -> EvaluationScenarioResult:
    user_one = _event("user-1", actor="user", minute=0)
    user_two = _event("user-2", actor="user", minute=1)
    events = {user_one.id: user_one, user_two.id: user_two}

    mutable_value = {"draft": {"color": "blue", "labels": ["current"]}}
    initial = ContinuityContext(max_items=2)
    admitted = apply_continuity_candidates(
        current_context=initial,
        candidates=(
            _candidate(
                kind="referent",
                key="draft.current",
                value=mutable_value,
                source=user_one.id,
            ),
        ),
        events=events,
        lifetime_revisions=3,
        required_source_ids=frozenset({user_one.id}),
    )
    admitted_item = admitted.context.items[0]

    duplicate = apply_continuity_candidates(
        current_context=admitted.context,
        candidates=(
            _candidate(
                kind="referent",
                key="draft.current",
                value={"draft": {"color": "blue", "labels": ["current"]}},
                source=user_one.id,
            ),
        ),
        events=events,
        lifetime_revisions=3,
        required_source_ids=frozenset({user_one.id}),
    )
    duplicate_item = duplicate.context.items[0]
    mutable_value["draft"]["color"] = "red"
    mutable_value["draft"]["labels"].append("mutated")
    frozen_value = admitted_item.value

    superseded = apply_continuity_candidates(
        current_context=duplicate.context,
        candidates=(
            _candidate(
                kind="referent",
                key="draft.current",
                value={"draft": {"color": "green"}},
                source=user_two.id,
            ),
        ),
        events=events,
        lifetime_revisions=3,
        required_source_ids=frozenset({user_two.id}),
    )

    rejected = apply_continuity_candidates(
        current_context=superseded.context,
        candidates=(
            _candidate(
                kind="unresolved",
                key="question.delivery",
                value="Which address?",
                source="missing-event",
            ),
        ),
        events=events,
        lifetime_revisions=3,
    )

    resolved = apply_continuity_candidates(
        current_context=rejected.context,
        candidates=(
            ContinuityCandidate.resolve(
                kind="referent",
                key="draft.current",
                sources=(user_two.id,),
                epistemic_role="user_assertion",
            ),
        ),
        events=events,
        lifetime_revisions=3,
    )

    expiry_seed = ContinuityContext(
        max_items=2,
        revision=4,
        items=(
            ContinuityItem(
                item_id="expiry-seed",
                kind="unresolved",
                key="question.expiring",
                value="Pending?",
                sources=(user_one.id,),
                epistemic_role="user_assertion",
                accepted_revision=3,
                expires_revision=5,
            ),
        ),
    )
    expired = apply_continuity_candidates(
        current_context=expiry_seed,
        candidates=(),
        events=events,
        lifetime_revisions=2,
    )

    capacity_seed = ContinuityContext(
        max_items=1,
        revision=4,
        items=(
            ContinuityItem(
                item_id="oldest-seed",
                kind="referent",
                key="draft.old",
                value="old draft",
                sources=(user_one.id,),
                epistemic_role="user_assertion",
                accepted_revision=2,
                expires_revision=9,
            ),
        ),
    )
    capacity = apply_continuity_candidates(
        current_context=capacity_seed,
        candidates=(
            _candidate(
                kind="active_task",
                key="task.current",
                value="send draft",
                source=user_two.id,
            ),
        ),
        events=events,
        lifetime_revisions=3,
    )

    decisions = (
        *admitted.decisions,
        *duplicate.decisions,
        *superseded.decisions,
        *rejected.decisions,
        *resolved.decisions,
        *expired.decisions,
        *capacity.decisions,
    )
    checks = (
        EvaluationCheck(
            check_id="known_user_assertion_admitted",
            boundary="continuity_validation",
            passed=(
                admitted.decisions[0].status == "accepted"
                and admitted.decisions[0].action == "admit"
                and admitted.context.revision == 1
                and admitted_item.sources == (user_one.id,)
            ),
            expected=True,
            observed=admitted.decisions[0].status == "accepted",
        ),
        EvaluationCheck(
            check_id="accepted_value_is_deeply_immutable",
            boundary="continuity_validation",
            passed=(
                frozen_value["draft"]["color"] == "blue"
                and frozen_value["draft"]["labels"] == ("current",)
            ),
            expected=True,
            observed=frozen_value["draft"]["color"] == "blue",
        ),
        EvaluationCheck(
            check_id="duplicate_is_noop_without_lifetime_refresh",
            boundary="continuity_validation",
            passed=(
                duplicate.decisions[0].status == "noop"
                and duplicate.decisions[0].reason == "duplicate"
                and duplicate.context.revision == 2
                and duplicate_item.item_id == admitted_item.item_id
                and duplicate_item.expires_revision == admitted_item.expires_revision
            ),
            expected=True,
            observed=duplicate.decisions[0].reason == "duplicate",
        ),
        EvaluationCheck(
            check_id="changed_same_key_supersedes",
            boundary="continuity_validation",
            passed=(
                superseded.decisions[0].status == "accepted"
                and superseded.decisions[0].action == "supersede"
                and superseded.context.items[0].value["draft"]["color"] == "green"
            ),
            expected=True,
            observed=superseded.decisions[0].action == "supersede",
        ),
        EvaluationCheck(
            check_id="unknown_source_is_rejected",
            boundary="continuity_validation",
            passed=(
                rejected.decisions[0].status == "rejected"
                and rejected.decisions[0].reason == "unknown_source"
                and rejected.context.items == superseded.context.items
            ),
            expected=True,
            observed=rejected.decisions[0].reason == "unknown_source",
        ),
        EvaluationCheck(
            check_id="same_kind_resolve_removes_item",
            boundary="continuity_validation",
            passed=(
                resolved.decisions[0].status == "accepted"
                and resolved.decisions[0].action == "resolve"
                and resolved.context.items == ()
            ),
            expected=True,
            observed=resolved.decisions[0].action == "resolve",
        ),
        EvaluationCheck(
            check_id="expiry_advances_before_candidate_processing",
            boundary="continuity_validation",
            passed=(
                expired.context.revision == 5
                and expired.expired_item_ids == ("expiry-seed",)
                and expired.context.items == ()
            ),
            expected=True,
            observed=expired.expired_item_ids == ("expiry-seed",),
        ),
        EvaluationCheck(
            check_id="capacity_evicts_oldest_deterministically",
            boundary="continuity_validation",
            passed=(
                capacity.evicted_item_ids == ("oldest-seed",)
                and len(capacity.context.items) == 1
                and capacity.context.items[0].key == "task.current"
            ),
            expected=True,
            observed=capacity.evicted_item_ids == ("oldest-seed",),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="continuity_lifecycle",
        checks=checks,
        metrics={
            "validation_call_count": 7,
            "accepted_decision_count": sum(
                decision.status == "accepted" for decision in decisions
            ),
            "noop_decision_count": sum(decision.status == "noop" for decision in decisions),
            "rejected_decision_count": sum(
                decision.status == "rejected" for decision in decisions
            ),
            "expired_item_count": len(expired.expired_item_ids),
            "evicted_item_count": len(capacity.evicted_item_ids),
        },
    )

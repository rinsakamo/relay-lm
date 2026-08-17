from relaylm.continuity import ContinuityCandidate, ContinuityContext
from relaylm.continuity_validation import apply_continuity_candidates
from relaylm.events import Event


def _event(event_id: str, actor: str) -> Event:
    return Event.create(
        type="message",
        actor=actor,
        payload={"content": event_id},
        event_id=event_id,
        timestamp="2026-08-17T00:00:00+00:00",
    )


def test_continuity_acceptance_admits_only_valid_event_grounded_proposals() -> None:
    user_event = _event("event-user-1", "user")
    assistant_event = _event("event-assistant-1", "assistant")
    events = {event.id: event for event in (user_event, assistant_event)}
    context = ContinuityContext(max_items=4)

    accepted = ContinuityCandidate.set(
        kind="unresolved",
        key="location.choice",
        value={"question": "Which location?"},
        sources=(user_event.id, user_event.id),
        epistemic_role="user_assertion",
    )
    wrong_role_source = ContinuityCandidate.set(
        kind="referent",
        key="referent.assistant-only",
        value="the draft",
        sources=(assistant_event.id,),
        epistemic_role="user_assertion",
    )
    unknown_source = ContinuityCandidate.set(
        kind="referent",
        key="referent.unknown",
        value="the draft",
        sources=("missing-event",),
        epistemic_role="assistant_inference",
    )
    missing_current_evidence = ContinuityCandidate.set(
        kind="active_task",
        key="task.previous",
        value="finish the outline",
        sources=(assistant_event.id,),
        epistemic_role="assistant_inference",
    )

    result = apply_continuity_candidates(
        current_context=context,
        candidates=(accepted, wrong_role_source, unknown_source, missing_current_evidence),
        events=events,
        required_source_ids=frozenset({user_event.id}),
        lifetime_revisions=3,
    )

    assert context.revision == 0
    assert context.items == ()
    assert result.context.revision == 1
    assert len(result.context.items) == 1
    item = result.context.items[0]
    assert item.item_id == "continuity:1:1"
    assert item.kind == "unresolved"
    assert item.key == "location.choice"
    assert item.sources == (user_event.id,)
    assert item.epistemic_role == "user_assertion"
    assert item.accepted_revision == 1
    assert item.expires_revision == 4
    assert result.decisions[0].status == "accepted"
    assert result.decisions[0].action == "admit"
    assert result.decisions[1].status == "rejected"
    assert result.decisions[1].reason == "missing_current_evidence"
    assert result.decisions[2].status == "rejected"
    assert result.decisions[2].reason == "unknown_source"
    assert result.decisions[3].status == "rejected"
    assert result.decisions[3].reason == "missing_current_evidence"


def test_user_assertion_requires_a_user_actor_source_after_evidence_checks() -> None:
    assistant_event = _event("event-assistant-1", "assistant")
    candidate = ContinuityCandidate.set(
        kind="referent",
        key="referent.assistant-only",
        value="the draft",
        sources=(assistant_event.id,),
        epistemic_role="user_assertion",
    )

    result = apply_continuity_candidates(
        current_context=ContinuityContext(max_items=2),
        candidates=(candidate,),
        events={assistant_event.id: assistant_event},
        lifetime_revisions=2,
    )

    assert result.context.items == ()
    assert result.decisions[0].status == "rejected"
    assert result.decisions[0].reason == "user_assertion_requires_user_source"


def test_exact_duplicate_is_noop_without_refresh_and_changed_value_supersedes() -> None:
    user_event = _event("event-user-1", "user")
    events = {user_event.id: user_event}
    candidate = ContinuityCandidate.set(
        kind="unresolved",
        key="draft.subject",
        value={"question": "Which draft?"},
        sources=(user_event.id,),
        epistemic_role="assistant_inference",
    )
    admitted = apply_continuity_candidates(
        current_context=ContinuityContext(max_items=2),
        candidates=(candidate,),
        events=events,
        lifetime_revisions=4,
    )
    original = admitted.context.items[0]

    duplicate = apply_continuity_candidates(
        current_context=admitted.context,
        candidates=(candidate,),
        events=events,
        lifetime_revisions=4,
    )

    assert duplicate.context.revision == 2
    assert duplicate.context.items == (original,)
    assert duplicate.decisions[0].status == "noop"
    assert duplicate.decisions[0].reason == "duplicate"
    assert duplicate.changed is False

    resolved_referent = ContinuityCandidate.set(
        kind="referent",
        key="draft.subject",
        value="the first draft",
        sources=(user_event.id,),
        epistemic_role="assistant_inference",
    )
    superseded = apply_continuity_candidates(
        current_context=duplicate.context,
        candidates=(resolved_referent,),
        events=events,
        lifetime_revisions=4,
    )

    assert len(superseded.context.items) == 1
    replacement = superseded.context.items[0]
    assert replacement.item_id == "continuity:3:1"
    assert replacement.kind == "referent"
    assert replacement.key == "draft.subject"
    assert replacement.value == "the first draft"
    assert replacement.accepted_revision == 3
    assert replacement.expires_revision == 7
    assert superseded.decisions[0].status == "accepted"
    assert superseded.decisions[0].action == "supersede"
    assert superseded.changed is True


def test_resolve_requires_matching_kind_and_removes_only_the_keyed_item() -> None:
    user_event = _event("event-user-1", "user")
    events = {user_event.id: user_event}
    set_candidate = ContinuityCandidate.set(
        kind="active_task",
        key="task.current",
        value="finish the outline",
        sources=(user_event.id,),
        epistemic_role="assistant_inference",
    )
    admitted = apply_continuity_candidates(
        current_context=ContinuityContext(max_items=2),
        candidates=(set_candidate,),
        events=events,
        lifetime_revisions=4,
    )

    mismatched = ContinuityCandidate.resolve(
        kind="unresolved",
        key="task.current",
        sources=(user_event.id,),
        epistemic_role="assistant_inference",
    )
    mismatch_result = apply_continuity_candidates(
        current_context=admitted.context,
        candidates=(mismatched,),
        events=events,
        lifetime_revisions=4,
    )
    assert mismatch_result.context.items == admitted.context.items
    assert mismatch_result.decisions[0].status == "rejected"
    assert mismatch_result.decisions[0].reason == "kind_mismatch"

    matching = ContinuityCandidate.resolve(
        kind="active_task",
        key="task.current",
        sources=(user_event.id,),
        epistemic_role="assistant_inference",
    )
    resolved = apply_continuity_candidates(
        current_context=mismatch_result.context,
        candidates=(matching,),
        events=events,
        lifetime_revisions=4,
    )
    assert resolved.context.items == ()
    assert resolved.decisions[0].status == "accepted"
    assert resolved.decisions[0].action == "resolve"
    assert resolved.changed is True

    absent = apply_continuity_candidates(
        current_context=resolved.context,
        candidates=(matching,),
        events=events,
        lifetime_revisions=4,
    )
    assert absent.decisions[0].status == "noop"
    assert absent.decisions[0].reason == "not_found"


def test_expiry_advances_by_revision_even_without_new_candidates() -> None:
    user_event = _event("event-user-1", "user")
    candidate = ContinuityCandidate.set(
        kind="referent",
        key="referent.current",
        value="the first draft",
        sources=(user_event.id,),
        epistemic_role="assistant_inference",
    )
    admitted = apply_continuity_candidates(
        current_context=ContinuityContext(max_items=2),
        candidates=(candidate,),
        events={user_event.id: user_event},
        lifetime_revisions=2,
    )
    item_id = admitted.context.items[0].item_id
    assert admitted.context.items[0].expires_revision == 3

    retained = apply_continuity_candidates(
        current_context=admitted.context,
        candidates=(),
        events={},
        lifetime_revisions=2,
    )
    assert retained.context.revision == 2
    assert retained.context.items[0].item_id == item_id
    assert retained.expired_item_ids == ()
    assert retained.changed is False

    expired = apply_continuity_candidates(
        current_context=retained.context,
        candidates=(),
        events={},
        lifetime_revisions=2,
    )
    assert expired.context.revision == 3
    assert expired.context.items == ()
    assert expired.expired_item_ids == (item_id,)
    assert expired.changed is True


def test_capacity_evicts_oldest_accepted_items_deterministically() -> None:
    user_event = _event("event-user-1", "user")
    candidates = tuple(
        ContinuityCandidate.set(
            kind="referent",
            key=f"referent.{name}",
            value=name,
            sources=(user_event.id,),
            epistemic_role="assistant_inference",
        )
        for name in ("first", "second", "third")
    )

    result = apply_continuity_candidates(
        current_context=ContinuityContext(max_items=2),
        candidates=candidates,
        events={user_event.id: user_event},
        lifetime_revisions=5,
    )

    assert [item.key for item in result.context.items] == [
        "referent.second",
        "referent.third",
    ]
    assert result.evicted_item_ids == ("continuity:1:1",)
    assert [decision.action for decision in result.decisions] == ["admit", "admit", "admit"]


def test_non_json_value_is_rejected_and_lifetime_policy_is_explicitly_positive() -> None:
    user_event = _event("event-user-1", "user")
    candidate = ContinuityCandidate.set(
        kind="referent",
        key="referent.invalid",
        value=object(),
        sources=(user_event.id,),
        epistemic_role="assistant_inference",
    )

    rejected = apply_continuity_candidates(
        current_context=ContinuityContext(max_items=2),
        candidates=(candidate,),
        events={user_event.id: user_event},
        lifetime_revisions=2,
    )
    assert rejected.context.items == ()
    assert rejected.decisions[0].status == "rejected"
    assert rejected.decisions[0].reason == "non_json_value"

    try:
        apply_continuity_candidates(
            current_context=ContinuityContext(max_items=2),
            candidates=(),
            events={},
            lifetime_revisions=0,
        )
    except ValueError as exc:
        assert str(exc) == "lifetime_revisions must be positive"
    else:
        raise AssertionError("zero lifetime must be rejected")

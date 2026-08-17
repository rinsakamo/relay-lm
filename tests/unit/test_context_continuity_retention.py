from __future__ import annotations

import json
from typing import Any

from relaylm.context import compile_cognitive_input, compile_cognitive_input_with_diagnostics
from relaylm.continuity import ContinuityContext, ContinuityItem
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState


def _current() -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": "What were we referring to?"},
        event_id="current-event",
        timestamp="2026-08-17T13:24:00+00:00",
    )


def _item(
    *,
    item_id: str,
    kind: str,
    key: str,
    value: Any,
    sources: tuple[str, ...],
    epistemic_role: str,
) -> ContinuityItem:
    return ContinuityItem(
        item_id=item_id,
        kind=kind,  # type: ignore[arg-type]
        key=key,
        value=value,
        sources=sources,
        epistemic_role=epistemic_role,  # type: ignore[arg-type]
        accepted_revision=1,
        expires_revision=4,
    )


def _context(*items: ContinuityItem) -> ContinuityContext:
    return ContinuityContext(max_items=4, revision=1, items=items)


def _compile(*, continuity_context: ContinuityContext, recent_events: tuple[Event, ...] = ()):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=_current(),
        recent_events=recent_events,
        continuity_context=continuity_context,
    )


def _decoded(item_content: str) -> dict[str, Any]:
    value = json.loads(item_content)
    assert isinstance(value, dict)
    return value


def test_accepted_referent_and_unresolved_survive_zero_recent_message_budget() -> None:
    referent = _item(
        item_id="continuity-referent-1",
        kind="referent",
        key="draft.current",
        value={"entity": "the blue draft"},
        sources=("event-user-1",),
        epistemic_role="user_assertion",
    )
    unresolved = _item(
        item_id="continuity-unresolved-1",
        kind="unresolved",
        key="question.delivery",
        value={"question": "Which address should receive it?"},
        sources=("event-assistant-1",),
        epistemic_role="assistant_inference",
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=_current(),
        continuity_context=_context(referent, unresolved),
        max_working_context_events=0,
        max_working_context_chars=0,
    )

    assert [_decoded(item.content) for item in compiled.context] == [
        {
            "continuity": {
                "epistemic_role": "user_assertion",
                "key": "draft.current",
                "kind": "referent",
                "value": {"entity": "the blue draft"},
            }
        },
        {
            "continuity": {
                "epistemic_role": "assistant_inference",
                "key": "question.delivery",
                "kind": "unresolved",
                "value": {"question": "Which address should receive it?"},
            }
        },
    ]
    assert [item.sources for item in compiled.context] == [
        ("event-user-1",),
        ("event-assistant-1",),
    ]
    assert [item.actor for item in compiled.context] == ["user", "assistant"]


def test_active_task_is_not_projected_by_c2() -> None:
    active_task = _item(
        item_id="continuity-task-1",
        kind="active_task",
        key="task.current",
        value={"task": "send the draft"},
        sources=("event-user-2",),
        epistemic_role="assistant_commitment",
    )

    compiled = _compile(continuity_context=_context(active_task))

    assert compiled.context == ()


def test_continuity_projection_precedes_recent_working_context_without_reordering_it() -> None:
    referent = _item(
        item_id="continuity-referent-2",
        kind="referent",
        key="draft.current",
        value="the blue draft",
        sources=("event-user-1",),
        epistemic_role="user_assertion",
    )
    recent_user = Event.create(
        type="message",
        actor="user",
        payload={"content": "I will send it tonight."},
        event_id="recent-user",
        timestamp="2026-08-17T13:22:00+00:00",
    )
    recent_assistant = Event.create(
        type="message",
        actor="assistant",
        payload={"content": "Okay, tonight."},
        event_id="recent-assistant",
        timestamp="2026-08-17T13:23:00+00:00",
    )

    compiled = _compile(
        continuity_context=_context(referent),
        recent_events=(recent_user, recent_assistant),
    )

    assert _decoded(compiled.context[0].content)["continuity"]["kind"] == "referent"
    assert [item.content for item in compiled.context[1:]] == [
        "I will send it tonight.",
        "Okay, tonight.",
    ]
    assert [item.sources for item in compiled.context[1:]] == [
        ("recent-user",),
        ("recent-assistant",),
    ]


def test_diagnostic_compiler_projects_same_continuity_without_adding_diagnostic_authority() -> None:
    unresolved = _item(
        item_id="continuity-unresolved-2",
        kind="unresolved",
        key="question.delivery",
        value="Which address?",
        sources=("event-assistant-2",),
        epistemic_role="assistant_inference",
    )

    result = compile_cognitive_input_with_diagnostics(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=_current(),
        continuity_context=_context(unresolved),
        max_working_context_events=0,
        max_working_context_chars=0,
    )

    assert _decoded(result.cognitive_input.context[0].content)["continuity"]["kind"] == "unresolved"
    assert [diagnostic.layer for diagnostic in result.diagnostics] == [
        "canonical_state",
        "working_context",
        "retrieved_memory",
        "event_evidence",
    ]


def test_no_accepted_continuity_means_zero_recent_budget_stays_empty() -> None:
    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=_current(),
        continuity_context=ContinuityContext(max_items=1),
        max_working_context_events=0,
        max_working_context_chars=0,
    )

    assert compiled.context == ()

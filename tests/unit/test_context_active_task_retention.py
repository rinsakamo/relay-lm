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
        payload={"content": "What should we do next?"},
        event_id="current-event",
        timestamp="2026-08-17T13:42:00+00:00",
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
        accepted_revision=2,
        expires_revision=5,
    )


def _context(*items: ContinuityItem) -> ContinuityContext:
    return ContinuityContext(max_items=5, revision=2, items=items)


def _decoded(content: str) -> dict[str, Any]:
    value = json.loads(content)
    assert isinstance(value, dict)
    return value


def test_accepted_active_task_survives_zero_recent_message_budget() -> None:
    active_task = _item(
        item_id="continuity-task-1",
        kind="active_task",
        key="task.current",
        value={"task": "send the blue draft", "status": "active"},
        sources=("event-user-1", "event-assistant-1"),
        epistemic_role="assistant_commitment",
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=_current(),
        continuity_context=_context(active_task),
        max_working_context_events=0,
        max_working_context_chars=0,
    )

    assert [_decoded(item.content) for item in compiled.context] == [
        {
            "continuity": {
                "epistemic_role": "assistant_commitment",
                "key": "task.current",
                "kind": "active_task",
                "value": {"status": "active", "task": "send the blue draft"},
            }
        }
    ]
    assert compiled.context[0].sources == ("event-user-1", "event-assistant-1")
    assert compiled.context[0].actor is None


def test_active_task_keeps_accepted_order_with_referent_and_unresolved() -> None:
    referent = _item(
        item_id="continuity-referent-1",
        kind="referent",
        key="draft.current",
        value="the blue draft",
        sources=("event-user-1",),
        epistemic_role="user_assertion",
    )
    active_task = _item(
        item_id="continuity-task-2",
        kind="active_task",
        key="task.current",
        value="send the draft",
        sources=("event-assistant-1",),
        epistemic_role="assistant_commitment",
    )
    unresolved = _item(
        item_id="continuity-unresolved-1",
        kind="unresolved",
        key="question.address",
        value="Which address?",
        sources=("event-assistant-2",),
        epistemic_role="assistant_inference",
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=_current(),
        continuity_context=_context(referent, active_task, unresolved),
        max_working_context_events=0,
        max_working_context_chars=0,
    )

    assert [
        _decoded(item.content)["continuity"]["kind"] for item in compiled.context
    ] == ["referent", "active_task", "unresolved"]


def test_active_task_does_not_change_existing_diagnostic_layer_ownership() -> None:
    active_task = _item(
        item_id="continuity-task-3",
        kind="active_task",
        key="task.current",
        value="send the draft",
        sources=("event-assistant-1",),
        epistemic_role="assistant_commitment",
    )

    result = compile_cognitive_input_with_diagnostics(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=_current(),
        continuity_context=_context(active_task),
        max_working_context_events=0,
        max_working_context_chars=0,
    )

    assert _decoded(result.cognitive_input.context[0].content)["continuity"]["kind"] == "active_task"
    assert [diagnostic.layer for diagnostic in result.diagnostics] == [
        "canonical_state",
        "working_context",
        "retrieved_memory",
        "event_evidence",
    ]

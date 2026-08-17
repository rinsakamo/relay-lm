from __future__ import annotations

import pytest

from relaylm.cognitive import EventEvidenceItem
from relaylm.context import compile_cognitive_input
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.providers.openai_compatible import (
    PROVIDER_WIRE_INSTRUCTION,
    SYSTEM_INSTRUCTION,
    serialize_cognitive_input,
)
from relaylm.state import CanonicalState


def _event(
    event_id: str,
    *,
    actor: str,
    content: str,
    second: int,
    event_type: str = "message",
) -> Event:
    return Event.create(
        type=event_type,
        actor=actor,
        payload={"content": content},
        event_id=event_id,
        timestamp=f"2026-08-17T06:40:{second:02d}+00:00",
    )


def test_selected_events_project_into_distinct_evidence_layer() -> None:
    user = _event(
        "user-evidence",
        actor="user",
        content="I used to live in Hokkaido.",
        second=0,
    )
    assistant = _event(
        "assistant-evidence",
        actor="assistant",
        content="You told me about that move.",
        second=1,
    )
    current = _event(
        "current-event",
        actor="user",
        content="Where did I say I lived before?",
        second=2,
    )
    original = (user, assistant, current)

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=current,
        event_evidence=original,
    )

    assert compiled.context == ()
    assert compiled.memory == ()
    assert compiled.state == ()
    assert compiled.input == current
    assert compiled.event_evidence == (
        EventEvidenceItem(
            event_id=user.id,
            event_type=user.type,
            actor=user.actor,
            timestamp=user.timestamp,
            content=user.payload["content"],
        ),
        EventEvidenceItem(
            event_id=assistant.id,
            event_type=assistant.type,
            actor=assistant.actor,
            timestamp=assistant.timestamp,
            content=assistant.payload["content"],
        ),
    )
    assert original == (user, assistant, current)


def test_provider_serializes_event_evidence_separately_with_real_event_ids() -> None:
    evidence = _event(
        "evidence-event",
        actor="user",
        content="I preferred tea then.",
        second=3,
    )
    current = _event(
        "current-event",
        actor="user",
        content="What did I prefer before?",
        second=4,
    )

    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=current,
        event_evidence=(evidence,),
    )
    payload = serialize_cognitive_input(compiled)

    assert payload["event_evidence"] == [
        {
            "event_id": evidence.id,
            "type": evidence.type,
            "actor": evidence.actor,
            "timestamp": evidence.timestamp,
            "content": evidence.payload["content"],
        }
    ]
    assert payload["context"] == []
    assert payload["memory"] == []
    assert payload["input"]["event_id"] == current.id


def test_provider_contract_allows_real_event_evidence_ids_but_not_memory_locations() -> None:
    assert "Event Evidence" in SYSTEM_INSTRUCTION
    assert "State, Context, Event Evidence, or Input" in PROVIDER_WIRE_INSTRUCTION
    assert "Memory `location` values" in PROVIDER_WIRE_INSTRUCTION


def test_event_evidence_item_requires_nonempty_occurrence_fields() -> None:
    with pytest.raises(ValueError, match="event evidence event_id must not be empty"):
        EventEvidenceItem(
            event_id=" ",
            event_type="message",
            actor="user",
            timestamp="2026-08-17T06:40:00+00:00",
            content="evidence",
        )
    with pytest.raises(ValueError, match="event evidence content must not be empty"):
        EventEvidenceItem(
            event_id="event",
            event_type="message",
            actor="user",
            timestamp="2026-08-17T06:40:00+00:00",
            content=" ",
        )


def test_projection_rejects_selected_event_without_string_content() -> None:
    invalid = Event.create(
        type="message",
        actor="user",
        payload={"content": 123},
        event_id="invalid-evidence",
        timestamp="2026-08-17T06:40:05+00:00",
    )
    current = _event(
        "current-event",
        actor="user",
        content="current",
        second=6,
    )

    with pytest.raises(ValueError, match="event evidence Event must contain non-empty string payload.content"):
        compile_cognitive_input(
            identity=Identity("# ReLM\nBe grounded."),
            state=CanonicalState(),
            current_event=current,
            event_evidence=(invalid,),
        )

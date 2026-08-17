from __future__ import annotations

from relaylm.context import compile_cognitive_input
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_retrieval import MemoryChunk
from relaylm.providers.openai_compatible import (
    PROVIDER_WIRE_INSTRUCTION,
    SYSTEM_INSTRUCTION,
    serialize_cognitive_input,
)
from relaylm.state import CanonicalState


def _current() -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": "What did I say about coffee?"},
        event_id="current-event",
        timestamp="2026-08-17T03:50:00+00:00",
    )


def _chunk() -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", "Coffee"),
        location="memory/MEMORY.md#memory/coffee",
        content="## Coffee\n\nRin currently prefers coffee over tea.",
    )


def test_compiler_projects_preselected_memory_as_distinct_layer() -> None:
    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=_current(),
        retrieved_memory=(_chunk(),),
    )

    assert compiled.context == ()
    assert len(compiled.memory) == 1
    assert compiled.memory[0].content == _chunk().content
    assert compiled.memory[0].location == _chunk().location


def test_memory_location_is_not_event_provenance_in_provider_payload() -> None:
    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=_current(),
        retrieved_memory=(_chunk(),),
    )

    payload = serialize_cognitive_input(compiled)

    assert payload["memory"] == [
        {
            "content": _chunk().content,
            "location": _chunk().location,
        }
    ]
    assert payload["context"] == []
    assert all(
        _chunk().location not in record.get("sources", [])
        for record in payload["state"]
    )
    assert payload["input"]["event_id"] == "current-event"


def test_provider_instructions_keep_memory_below_state_and_out_of_sources() -> None:
    assert "Memory is not accepted current State" in SYSTEM_INSTRUCTION
    assert "treat active State as the current understanding" in SYSTEM_INSTRUCTION
    assert "Memory `location` values" in PROVIDER_WIRE_INSTRUCTION
    assert "must never be used as `sources`" in PROVIDER_WIRE_INSTRUCTION


def test_no_retrieved_memory_preserves_empty_memory_layer() -> None:
    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=CanonicalState(),
        current_event=_current(),
    )

    assert compiled.memory == ()
    assert serialize_cognitive_input(compiled)["memory"] == []

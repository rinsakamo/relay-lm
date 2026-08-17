from __future__ import annotations

from relaylm.context import compile_cognitive_input
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_retrieval import MemoryChunk
from relaylm.state import CanonicalState, StateRecord


def _current() -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": "What is current?"},
        event_id="current-event",
        timestamp="2026-08-17T15:52:00+00:00",
    )


def _state(*, key: str = "residence_location", value: object = "Fukuoka") -> CanonicalState:
    return CanonicalState(
        states=(
            StateRecord(
                state_id="current-state",
                state_class="user.fact",
                key=key,
                value=value,
                sources=("source-event",),
            ),
        )
    )


def _chunk(content: str, *, heading: str = "Profile Notes") -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", heading),
        location=f"memory/MEMORY.md#memory/{heading.casefold().replace(' ', '-')}",
        content=f"## {heading}\n\n{content}",
    )


def _compile(*, chunk: MemoryChunk, state: CanonicalState | None = None):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state or _state(),
        current_event=_current(),
        retrieved_memory=(chunk,),
    )


def test_unannotated_current_wording_does_not_gain_temporal_authority() -> None:
    memory = _chunk("Current residence location is Hokkaido.")

    compiled = _compile(chunk=memory)

    assert [item.location for item in compiled.memory] == [memory.location]


def test_unannotated_now_wording_does_not_gain_temporal_authority() -> None:
    memory = _chunk("Preferred beverage is now tea.")

    compiled = _compile(
        chunk=memory,
        state=_state(key="preferred_beverage", value="coffee"),
    )

    assert [item.location for item in compiled.memory] == [memory.location]


def test_structural_state_addressing_remains_authoritative_without_temporal_guessing() -> None:
    memory = _chunk(
        "Rin lived in Hokkaido.",
        heading="Residence location",
    )

    compiled = _compile(chunk=memory)

    assert compiled.memory == ()

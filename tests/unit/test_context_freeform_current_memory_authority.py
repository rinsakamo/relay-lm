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
        timestamp="2026-08-17T13:55:00+00:00",
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


def _chunk(content: str) -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", "Profile Notes"),
        location="memory/MEMORY.md#memory/profile-notes",
        content=f"## Profile Notes\n\n{content}",
    )


def _compile(*, chunk: MemoryChunk, state: CanonicalState | None = None):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state or _state(),
        current_event=_current(),
        retrieved_memory=(chunk,),
    )


def test_current_wording_without_typed_metadata_is_retained() -> None:
    unknown = _chunk("Current residence location is Hokkaido.")

    compiled = _compile(chunk=unknown)

    assert [item.location for item in compiled.memory] == [unknown.location]


def test_currently_wording_without_typed_metadata_is_retained() -> None:
    unknown = _chunk("The residence location is currently Fukuoka.")

    compiled = _compile(chunk=unknown)

    assert [item.location for item in compiled.memory] == [unknown.location]


def test_now_wording_without_typed_metadata_is_retained() -> None:
    unknown = _chunk("Preferred beverage is now tea.")
    state = _state(key="preferred_beverage", value="coffee")

    compiled = _compile(chunk=unknown, state=state)

    assert [item.location for item in compiled.memory] == [unknown.location]


def test_prefixed_current_phrase_remains_non_authoritative() -> None:
    ambiguous = _chunk("Previous current residence location is Hokkaido.")

    compiled = _compile(chunk=ambiguous)

    assert [item.location for item in compiled.memory] == [ambiguous.location]


def test_temporally_ambiguous_freeform_key_prose_remains_for_c5() -> None:
    history = _chunk("Residence location in 2020 was Hokkaido.")

    compiled = _compile(chunk=history)

    assert [item.location for item in compiled.memory] == [history.location]


def test_freeform_prose_without_canonical_key_is_not_semantically_inferred() -> None:
    unaddressed = _chunk("Rin currently lives in Hokkaido.")

    compiled = _compile(chunk=unaddressed)

    assert [item.location for item in compiled.memory] == [unaddressed.location]


def test_freeform_current_boolean_claim_is_not_temporally_inferred() -> None:
    boolean_claim = _chunk("Current notifications enabled is false.")
    state = _state(key="notifications_enabled", value=True)

    compiled = _compile(chunk=boolean_claim, state=state)

    assert [item.location for item in compiled.memory] == [boolean_claim.location]

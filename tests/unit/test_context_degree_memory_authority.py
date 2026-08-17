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
        payload={"content": "What do you remember about tea?"},
        event_id="current-event",
        timestamp="2026-08-17T12:10:00+00:00",
    )


def _state(*, degree_hint: float = 0.85) -> CanonicalState:
    return CanonicalState(
        states=(
            StateRecord(
                state_id="tea-current",
                state_class="user.preference",
                key="tea",
                value={"semantic": "likes", "degree_hint": degree_hint},
                sources=("source-event",),
            ),
        )
    )


def _chunk(*, heading: str, content: str) -> MemoryChunk:
    slug = heading.casefold().replace(" ", "-")
    return MemoryChunk(
        heading_path=("Memory", heading),
        location=f"memory/MEMORY.md#memory/{slug}",
        content=f"## {heading}\n\n{content}",
    )


def _compile(chunk: MemoryChunk):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current(),
        retrieved_memory=(chunk,),
    )


def test_explicit_stale_degree_hint_is_suppressed_for_current_semantic() -> None:
    stale = _chunk(
        heading="Tea",
        content="Rin likes tea.\ndegree_hint: 0.65",
    )

    compiled = _compile(stale)

    assert compiled.memory == ()


def test_matching_explicit_degree_hint_is_retained() -> None:
    current = _chunk(
        heading="Tea",
        content="Rin likes tea.\ndegree_hint = 0.85",
    )

    compiled = _compile(current)

    assert [item.location for item in compiled.memory] == [current.location]


def test_missing_degree_hint_is_not_inferred_as_a_conflict() -> None:
    compatible = _chunk(
        heading="Tea",
        content="Rin likes tea.",
    )

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_matching_degree_number_does_not_rescue_conflicting_semantic_value() -> None:
    stale = _chunk(
        heading="Tea",
        content="Rin dislikes tea.\ndegree_hint: 0.85",
    )

    compiled = _compile(stale)

    assert compiled.memory == ()


def test_inline_key_assignment_uses_same_line_degree_authority() -> None:
    stale = _chunk(
        heading="Profile Notes",
        content="tea: likes; degree_hint: 0.65",
    )

    compiled = _compile(stale)

    assert compiled.memory == ()


def test_inline_key_does_not_borrow_another_assignment_degree_hint() -> None:
    mixed = _chunk(
        heading="Profile Notes",
        content="tea: likes\ncoffee: likes; degree_hint: 0.65",
    )

    compiled = _compile(mixed)

    assert [item.location for item in compiled.memory] == [mixed.location]


def test_unaddressed_historical_degree_prose_is_left_untouched() -> None:
    history = _chunk(
        heading="Preference History",
        content="An old tea survey recorded degree_hint: 0.65.",
    )

    compiled = _compile(history)

    assert [item.location for item in compiled.memory] == [history.location]

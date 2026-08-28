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
        payload={"content": "What do you remember?"},
        event_id="current-event",
        timestamp="2026-08-17T05:55:00+00:00",
    )


def _record(
    *,
    state_id: str,
    state_class: str,
    key: str,
    value: object,
    status: str = "active",
    valid_to: str | None = None,
) -> StateRecord:
    return StateRecord(
        state_id=state_id,
        state_class=state_class,
        key=key,
        value=value,
        sources=("source-event",),
        status=status,
        valid_to=valid_to,
    )


def _chunk(*, heading: str, content: str) -> MemoryChunk:
    slug = heading.casefold().replace(" ", "-")
    return MemoryChunk(
        heading_path=("Memory", heading),
        location=f"memory/MEMORY.md#memory/{slug}",
        content=f"## {heading}\n\n{content}",
    )


def _compile(
    *,
    state: CanonicalState,
    chunks: tuple[MemoryChunk, ...],
    max_state_records: int | None = None,
):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state,
        current_event=_current(),
        retrieved_memory=chunks,
        max_state_records=max_state_records,
    )


def test_stale_key_addressing_memory_is_suppressed() -> None:
    state = CanonicalState(
        states=(
            _record(
                state_id="residence",
                state_class="user.fact",
                key="residence_location",
                value="Fukuoka",
            ),
        )
    )
    stale = _chunk(heading="Residence Location", content="Rin lives in Hokkaido.")

    compiled = _compile(state=state, chunks=(stale,))

    assert compiled.memory == ()


def test_key_addressing_memory_with_current_value_is_retained() -> None:
    state = CanonicalState(
        states=(
            _record(
                state_id="residence",
                state_class="user.fact",
                key="residence_location",
                value="Fukuoka",
            ),
        )
    )
    current = _chunk(heading="Residence Location", content="Rin lives in Fukuoka.")

    compiled = _compile(state=state, chunks=(current,))

    assert [item.location for item in compiled.memory] == [current.location]
    assert compiled.memory[0].content == current.content


def test_unrelated_historical_memory_is_not_semantically_reclassified() -> None:
    state = CanonicalState(
        states=(
            _record(
                state_id="residence",
                state_class="user.fact",
                key="residence_location",
                value="Fukuoka",
            ),
        )
    )
    history = _chunk(heading="Trip History", content="Rin once stayed in Hokkaido.")

    compiled = _compile(state=state, chunks=(history,))

    assert [item.location for item in compiled.memory] == [history.location]


def test_full_active_state_filters_memory_even_when_state_projection_is_capped_out() -> None:
    state = CanonicalState(
        states=(
            _record(
                state_id="residence",
                state_class="user.fact",
                key="residence_location",
                value="Fukuoka",
            ),
        )
    )
    stale = _chunk(heading="Residence Location", content="Rin lives in Hokkaido.")

    compiled = _compile(state=state, chunks=(stale,), max_state_records=0)

    assert compiled.state == ()
    assert compiled.memory == ()


def test_inactive_or_expired_state_does_not_suppress_memory() -> None:
    stale = _chunk(heading="Residence Location", content="Rin lives in Hokkaido.")
    state = CanonicalState(
        states=(
            _record(
                state_id="inactive-residence",
                state_class="user.fact",
                key="residence_location",
                value="Fukuoka",
                status="inactive",
            ),
            _record(
                state_id="expired-residence",
                state_class="user.fact",
                key="residence_location",
                value="Fukuoka",
                valid_to="2026-08-16T00:00:00+00:00",
            ),
        )
    )

    compiled = _compile(state=state, chunks=(stale,))

    assert [item.location for item in compiled.memory] == [stale.location]


def test_preferred_beverage_shadow_does_not_delete_separate_tea_liking_memory() -> None:
    state = CanonicalState(
        states=(
            _record(
                state_id="tea-liking",
                state_class="user.preference",
                key="tea",
                value="likes",
            ),
            _record(
                state_id="preferred-beverage",
                state_class="user.preference",
                key="preferred_beverage",
                value="coffee",
            ),
        )
    )
    stale_preferred = _chunk(
        heading="Preferred Beverage",
        content="Tea is Rin's preferred beverage.",
    )
    tea_liking = _chunk(heading="Tea", content="Rin likes tea.")

    compiled = _compile(state=state, chunks=(stale_preferred, tea_liking))

    assert [item.location for item in compiled.memory] == [tea_liking.location]
    assert compiled.state == ()


def test_current_value_match_uses_tokens_not_substrings() -> None:
    state = CanonicalState(
        states=(
            _record(
                state_id="coffee-liking",
                state_class="user.preference",
                key="coffee",
                value="likes",
            ),
        )
    )
    conflicting = _chunk(heading="Coffee", content="Rin dislikes coffee.")

    compiled = _compile(state=state, chunks=(conflicting,))

    assert compiled.memory == ()


def test_inline_state_key_addressing_memory_is_suppressed_without_key_heading() -> None:
    state = CanonicalState(
        states=(
            _record(
                state_id="residence",
                state_class="user.fact",
                key="residence_location",
                value="Fukuoka",
            ),
        )
    )
    stale = _chunk(
        heading="Profile Notes",
        content="residence_location: Hokkaido",
    )

    compiled = _compile(state=state, chunks=(stale,))

    assert compiled.memory == ()


def test_boolean_key_heading_with_opposite_value_is_suppressed() -> None:
    state = CanonicalState(
        states=(
            _record(
                state_id="notifications",
                state_class="user.fact",
                key="notifications_enabled",
                value=True,
            ),
        )
    )
    stale = _chunk(
        heading="Notifications Enabled",
        content="false",
    )

    compiled = _compile(state=state, chunks=(stale,))

    assert compiled.memory == ()


def test_boolean_inline_assignment_with_opposite_value_is_suppressed() -> None:
    state = CanonicalState(
        states=(
            _record(
                state_id="notifications",
                state_class="user.fact",
                key="notifications_enabled",
                value=True,
            ),
        )
    )
    stale = _chunk(
        heading="Profile Notes",
        content="notifications_enabled = false",
    )

    compiled = _compile(state=state, chunks=(stale,))

    assert compiled.memory == ()


def test_boolean_key_addressing_memory_with_current_value_is_retained() -> None:
    state = CanonicalState(
        states=(
            _record(
                state_id="notifications",
                state_class="user.fact",
                key="notifications_enabled",
                value=True,
            ),
        )
    )
    current = _chunk(
        heading="Notifications Enabled",
        content="true",
    )

    compiled = _compile(state=state, chunks=(current,))

    assert [item.location for item in compiled.memory] == [current.location]


def test_boolean_general_historical_prose_without_key_addressing_is_retained() -> None:
    state = CanonicalState(
        states=(
            _record(
                state_id="notifications",
                state_class="user.fact",
                key="notifications_enabled",
                value=True,
            ),
        )
    )
    history = _chunk(
        heading="Notification History",
        content="Notifications were disabled during a past quiet period.",
    )

    compiled = _compile(state=state, chunks=(history,))

    assert [item.location for item in compiled.memory] == [history.location]


def test_single_character_state_key_heading_suppresses_conflicting_memory() -> None:
    state = CanonicalState(
        states=(
            _record(
                state_id="tea-preference",
                state_class="user.preference",
                key="茶",
                value="likes",
            ),
        )
    )
    stale = _chunk(heading="茶", content="Rin dislikes tea.")

    compiled = _compile(state=state, chunks=(stale,))

    assert compiled.memory == ()

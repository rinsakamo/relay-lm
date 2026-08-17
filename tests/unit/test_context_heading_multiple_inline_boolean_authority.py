from __future__ import annotations

import pytest

from relaylm.context import compile_cognitive_input
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_provenance import (
    MemoryProvenance,
    MemoryProvenanceSource,
    MemoryProvenanceSourceKind,
    MemoryTemporalAuthority,
    MemoryTemporalScope,
)
from relaylm.memory_retrieval import MemoryChunk
from relaylm.state import CanonicalState, StateRecord


def _current_event() -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": "Are notifications enabled?"},
        event_id="current-event",
        timestamp="2026-08-18T08:25:00+09:00",
    )


def _state(value: bool) -> CanonicalState:
    return CanonicalState(
        states=(
            StateRecord(
                state_id="notifications-current",
                state_class="user.fact",
                key="notifications_enabled",
                value=value,
                sources=("source-event",),
            ),
        )
    )


def _authority(scope: MemoryTemporalScope) -> MemoryTemporalAuthority:
    if scope is MemoryTemporalScope.UNKNOWN:
        return MemoryTemporalAuthority(temporal_scope=scope)
    return MemoryTemporalAuthority(
        temporal_scope=scope,
        provenance=MemoryProvenance(
            memory_id=f"memory-heading-multi-bool-{scope.value}",
            derivation_id=f"derivation-heading-multi-bool-{scope.value}",
            sources=(
                MemoryProvenanceSource(
                    kind=MemoryProvenanceSourceKind.EVENT,
                    reference_id="memory-source-event",
                ),
            ),
        ),
    )


def _chunk(
    assignments: tuple[str, ...],
    *,
    scope: MemoryTemporalScope = MemoryTemporalScope.UNKNOWN,
    tail: str | None = None,
) -> MemoryChunk:
    lines = assignments + ((tail,) if tail is not None else ())
    return MemoryChunk(
        heading_path=("Memory", "Notifications Enabled"),
        location=f"memory/MEMORY.md#memory/heading-multi-bool-{scope.value}",
        content="## Notifications Enabled\n\n" + "\n".join(lines),
        temporal_authority=_authority(scope),
    )


def _compile(chunk: MemoryChunk, *, value: bool):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(value),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


@pytest.mark.parametrize(
    ("state_value", "assignments"),
    [
        (True, ("notifications_enabled: true", "notifications_enabled: false")),
        (
            True,
            (
                "notifications_enabled: not false",
                "notifications_enabled: not true",
            ),
        ),
        (False, ("notifications_enabled: false", "notifications_enabled: true")),
        (
            False,
            (
                "notifications_enabled: not true",
                "notifications_enabled: not false",
            ),
        ),
    ],
)
def test_any_conflicting_exact_heading_assignment_suppresses(
    state_value: bool,
    assignments: tuple[str, ...],
) -> None:
    stale = _chunk(assignments)

    assert _compile(stale, value=state_value).memory == ()


@pytest.mark.parametrize(
    ("state_value", "assignments"),
    [
        (
            True,
            (
                "notifications_enabled: true",
                "notifications_enabled: not false",
            ),
        ),
        (
            False,
            (
                "notifications_enabled: false",
                "notifications_enabled: not true",
            ),
        ),
    ],
)
def test_all_matching_exact_heading_assignments_retain(
    state_value: bool,
    assignments: tuple[str, ...],
) -> None:
    compatible = _chunk(assignments)

    compiled = _compile(compatible, value=state_value)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_conflicting_assignment_set_is_not_rescued_by_unrelated_current_token() -> None:
    stale = _chunk(
        (
            "notifications_enabled: true",
            "notifications_enabled: false",
        ),
        tail="A separate note says true.",
    )

    assert _compile(stale, value=True).memory == ()


def test_typed_current_uses_same_heading_multiple_assignment_rule() -> None:
    stale = _chunk(
        (
            "notifications_enabled: true",
            "notifications_enabled: false",
        ),
        scope=MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale, value=True).memory == ()


def test_historical_heading_multiple_assignments_remain_exempt() -> None:
    historical = _chunk(
        (
            "notifications_enabled: true",
            "notifications_enabled: false",
        ),
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(historical, value=True)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_nonexact_assignment_prevents_partial_c17_interpretation() -> None:
    fallback = _chunk(
        (
            "notifications_enabled: true",
            "notifications_enabled: disabled",
        )
    )

    compiled = _compile(fallback, value=True)

    assert [item.location for item in compiled.memory] == [fallback.location]

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
        timestamp="2026-08-18T08:02:00+09:00",
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
            memory_id=f"memory-multiple-inline-boolean-{scope.value}",
            derivation_id=f"derivation-multiple-inline-boolean-{scope.value}",
            sources=(
                MemoryProvenanceSource(
                    kind=MemoryProvenanceSourceKind.EVENT,
                    reference_id="memory-source-event",
                ),
            ),
        ),
    )


def _chunk(
    lines: tuple[str, ...],
    *,
    scope: MemoryTemporalScope = MemoryTemporalScope.UNKNOWN,
    heading: str = "Profile Notes",
    tail: str | None = None,
) -> MemoryChunk:
    body = "\n".join(lines + ((tail,) if tail is not None else ()))
    return MemoryChunk(
        heading_path=("Memory", heading),
        location=f"memory/MEMORY.md#memory/multiple-inline-boolean-{scope.value}",
        content=f"## {heading}\n\n{body}",
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
def test_any_conflicting_exact_assignment_suppresses(
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
def test_all_matching_exact_assignments_retain(
    state_value: bool,
    assignments: tuple[str, ...],
) -> None:
    compatible = _chunk(assignments)

    compiled = _compile(compatible, value=state_value)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_three_matching_exact_assignments_retain() -> None:
    compatible = _chunk(
        (
            "notifications_enabled: true",
            "notifications_enabled = not false",
            "notifications_enabled: true",
        )
    )

    compiled = _compile(compatible, value=True)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_exact_assignment_set_ignores_unrelated_opposite_boolean_token() -> None:
    compatible = _chunk(
        (
            "notifications_enabled: true",
            "notifications_enabled: not false",
        ),
        tail="A separate note contains false.",
    )

    compiled = _compile(compatible, value=True)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_typed_current_uses_same_multiple_assignment_rule() -> None:
    stale = _chunk(
        (
            "notifications_enabled: true",
            "notifications_enabled: false",
        ),
        scope=MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale, value=True).memory == ()


def test_historical_multiple_assignments_remain_exempt() -> None:
    historical = _chunk(
        (
            "notifications_enabled: true",
            "notifications_enabled: false",
        ),
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(historical, value=True)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_one_nonexact_assignment_falls_back_without_partial_c15_interpretation() -> None:
    fallback = _chunk(
        (
            "notifications_enabled: true",
            "notifications_enabled: disabled",
        )
    )

    compiled = _compile(fallback, value=True)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_heading_plus_multiple_inline_assignments_remains_outside_c15() -> None:
    deferred = _chunk(
        (
            "notifications_enabled: true",
            "notifications_enabled: false",
        ),
        heading="Notifications Enabled",
    )

    compiled = _compile(deferred, value=True)

    assert [item.location for item in compiled.memory] == [deferred.location]

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
        timestamp="2026-08-18T08:15:00+09:00",
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
            memory_id=f"memory-heading-inline-boolean-{scope.value}",
            derivation_id=f"derivation-heading-inline-boolean-{scope.value}",
            sources=(
                MemoryProvenanceSource(
                    kind=MemoryProvenanceSourceKind.EVENT,
                    reference_id="memory-source-event",
                ),
            ),
        ),
    )


def _chunk(
    assignment: str,
    *,
    scope: MemoryTemporalScope = MemoryTemporalScope.UNKNOWN,
    tail: str | None = None,
) -> MemoryChunk:
    body = assignment if tail is None else f"{assignment}\n{tail}"
    return MemoryChunk(
        heading_path=("Memory", "Notifications Enabled"),
        location=f"memory/MEMORY.md#memory/heading-inline-boolean-{scope.value}",
        content=f"## Notifications Enabled\n\n{body}",
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
    ("state_value", "assignment", "retained"),
    [
        (True, "notifications_enabled: true", True),
        (True, "notifications_enabled: false", False),
        (True, "notifications_enabled: not true", False),
        (True, "notifications_enabled: not false", True),
        (False, "notifications_enabled = false", True),
        (False, "notifications_enabled = true", False),
        (False, "notifications_enabled = not false", False),
        (False, "notifications_enabled = not true", True),
    ],
)
def test_heading_plus_single_inline_assignment_uses_exact_boolean_value(
    state_value: bool,
    assignment: str,
    retained: bool,
) -> None:
    chunk = _chunk(assignment)

    compiled = _compile(chunk, value=state_value)

    assert bool(compiled.memory) is retained


def test_typed_current_uses_same_heading_inline_boolean_rule() -> None:
    compatible = _chunk(
        "notifications_enabled: not false",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(compatible, value=True)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_historical_heading_inline_boolean_remains_exempt() -> None:
    historical = _chunk(
        "notifications_enabled: not true",
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(historical, value=True)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_exact_assignment_ignores_unrelated_opposite_boolean_token() -> None:
    compatible = _chunk(
        "notifications_enabled: not false",
        tail="A separate note contains false.",
    )

    compiled = _compile(compatible, value=True)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_nonexact_single_assignment_falls_through_existing_rule() -> None:
    fallback = _chunk("notifications_enabled: disabled")

    compiled = _compile(fallback, value=True)

    assert [item.location for item in compiled.memory] == [fallback.location]

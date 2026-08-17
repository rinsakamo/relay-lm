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
        timestamp="2026-08-18T07:15:00+09:00",
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
            memory_id=f"memory-inline-boolean-{scope.value}",
            derivation_id=f"derivation-inline-boolean-{scope.value}",
            sources=(
                MemoryProvenanceSource(
                    kind=MemoryProvenanceSourceKind.EVENT,
                    reference_id="memory-source-event",
                ),
            ),
        ),
    )


def _chunk(
    content: str,
    *,
    scope: MemoryTemporalScope = MemoryTemporalScope.UNKNOWN,
    heading: str = "Profile Notes",
) -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", heading),
        location=f"memory/MEMORY.md#memory/inline-boolean-{scope.value}",
        content=f"## {heading}\n\n{content}",
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
def test_single_inline_assignment_uses_exact_boolean_value(
    state_value: bool,
    assignment: str,
    retained: bool,
) -> None:
    chunk = _chunk(assignment)

    compiled = _compile(chunk, value=state_value)

    assert bool(compiled.memory) is retained


def test_typed_current_uses_same_structural_inline_boolean_rule() -> None:
    compatible = _chunk(
        "notifications_enabled: not false",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(compatible, value=True)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_historical_inline_boolean_negation_remains_exempt() -> None:
    historical = _chunk(
        "notifications_enabled: not true",
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(historical, value=True)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_exact_assignment_is_not_overridden_by_unrelated_boolean_token() -> None:
    stale = _chunk(
        "notifications_enabled: false\nA separate note contains true."
    )

    assert _compile(stale, value=True).memory == ()


def test_matching_exact_assignment_ignores_unrelated_opposite_token() -> None:
    compatible = _chunk(
        "notifications_enabled: not false\nA separate note contains false."
    )

    compiled = _compile(compatible, value=True)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_assignment_does_not_consume_a_boolean_value_from_the_next_line() -> None:
    deferred = _chunk("notifications_enabled:\nnot true")

    assert _compile(deferred, value=False).memory == ()


def test_multiple_same_key_assignments_remain_outside_c13() -> None:
    deferred = _chunk(
        "notifications_enabled: not false\nnotifications_enabled: false"
    )

    assert _compile(deferred, value=True).memory == ()


def test_heading_addressed_boolean_negation_remains_outside_c13() -> None:
    deferred = _chunk("not false", heading="Notifications Enabled")

    assert _compile(deferred, value=True).memory == ()


@pytest.mark.parametrize(
    "assignment",
    [
        "notifications_enabled: disabled",
        "notifications_enabled: not not true",
        "notifications_enabled: not true or false",
    ],
)
def test_nonexact_inline_boolean_values_fall_through_existing_rule(
    assignment: str,
) -> None:
    chunk = _chunk(assignment)

    compiled = _compile(chunk, value=True)

    assert [item.location for item in compiled.memory] == [chunk.location]

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
        timestamp="2026-08-18T07:02:00+09:00",
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
            memory_id=f"memory-boolean-negation-{scope.value}",
            derivation_id=f"derivation-boolean-negation-{scope.value}",
            sources=(
                MemoryProvenanceSource(
                    kind=MemoryProvenanceSourceKind.EVENT,
                    reference_id="memory-source-event",
                ),
            ),
        ),
    )


def _chunk(content: str, scope: MemoryTemporalScope) -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", "Profile Notes"),
        location=f"memory/MEMORY.md#memory/boolean-negation-{scope.value}",
        content=f"## Profile Notes\n\n{content}",
        temporal_authority=_authority(scope),
    )


def _compile(chunk: MemoryChunk, *, value: bool):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(value),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


def test_not_true_conflicts_with_true_state() -> None:
    stale = _chunk(
        "Current notifications enabled is not true.",
        MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale, value=True).memory == ()


def test_not_false_matches_true_state() -> None:
    compatible = _chunk(
        "Current notifications enabled is not false.",
        MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(compatible, value=True)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_not_false_conflicts_with_false_state() -> None:
    stale = _chunk(
        "The notifications enabled is currently not false.",
        MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale, value=False).memory == ()


def test_not_true_matches_false_state() -> None:
    compatible = _chunk(
        "Notifications enabled is now not true.",
        MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(compatible, value=False)

    assert [item.location for item in compiled.memory] == [compatible.location]


@pytest.mark.parametrize(
    "scope",
    [MemoryTemporalScope.UNKNOWN, MemoryTemporalScope.HISTORICAL],
)
def test_noncurrent_scope_does_not_gain_boolean_negation_authority(
    scope: MemoryTemporalScope,
) -> None:
    chunk = _chunk("Current notifications enabled is not true.", scope)

    compiled = _compile(chunk, value=True)

    assert [item.location for item in compiled.memory] == [chunk.location]


@pytest.mark.parametrize(
    "claim",
    [
        "Current notifications enabled is not true or false.",
        "Current notifications enabled is not not true.",
        "Current notifications enabled is never true.",
        "Current notifications enabled is disabled.",
    ],
)
def test_nonexact_boolean_negations_remain_uninterpreted(claim: str) -> None:
    chunk = _chunk(claim, MemoryTemporalScope.CURRENT)

    compiled = _compile(chunk, value=True)

    assert [item.location for item in compiled.memory] == [chunk.location]


def test_positive_boolean_conflict_remains_suppressed_by_c7() -> None:
    stale = _chunk(
        "Current notifications enabled is false.",
        MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale, value=True).memory == ()


def test_positive_boolean_match_remains_retained_by_c7() -> None:
    current = _chunk(
        "Current notifications enabled is true.",
        MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(current, value=True)

    assert [item.location for item in compiled.memory] == [current.location]

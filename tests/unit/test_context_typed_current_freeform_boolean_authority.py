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
        timestamp="2026-08-17T16:35:00+00:00",
    )


def _state(value: bool = True) -> CanonicalState:
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
            memory_id=f"memory-notifications-{scope.value}",
            derivation_id=f"derivation-notifications-{scope.value}",
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
        location=f"memory/MEMORY.md#memory/notifications-{scope.value}",
        content=f"## Profile Notes\n\n{content}",
        temporal_authority=_authority(scope),
    )


def _compile(chunk: MemoryChunk, *, value: bool = True):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(value),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


def test_typed_current_freeform_false_conflicts_with_true_state() -> None:
    stale = _chunk(
        "Current notifications enabled is false.",
        MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale).memory == ()


def test_typed_current_freeform_true_matches_true_state() -> None:
    current = _chunk(
        "The notifications enabled is currently true.",
        MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(current)

    assert [item.location for item in compiled.memory] == [current.location]


def test_typed_current_now_false_conflicts_with_true_state() -> None:
    stale = _chunk(
        "Notifications enabled is now false.",
        MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale).memory == ()


def test_typed_current_true_conflicts_with_false_state() -> None:
    stale = _chunk(
        "Current notifications enabled is true.",
        MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale, value=False).memory == ()


@pytest.mark.parametrize(
    "scope",
    [MemoryTemporalScope.UNKNOWN, MemoryTemporalScope.HISTORICAL],
)
def test_noncurrent_scope_does_not_gain_freeform_boolean_authority(
    scope: MemoryTemporalScope,
) -> None:
    chunk = _chunk("Current notifications enabled is false.", scope)

    compiled = _compile(chunk)

    assert [item.location for item in compiled.memory] == [chunk.location]


@pytest.mark.parametrize(
    "claim",
    [
        "Current notifications enabled is disabled.",
        "Current notifications enabled is not true.",
        "Current notifications enabled is true or false.",
    ],
)
def test_nonliteral_boolean_claims_remain_uninterpreted(claim: str) -> None:
    chunk = _chunk(claim, MemoryTemporalScope.CURRENT)

    compiled = _compile(chunk)

    assert [item.location for item in compiled.memory] == [chunk.location]


def test_prefixed_boolean_claim_remains_outside_bounded_grammar() -> None:
    chunk = _chunk(
        "Previous current notifications enabled is false.",
        MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(chunk)

    assert [item.location for item in compiled.memory] == [chunk.location]

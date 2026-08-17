from __future__ import annotations

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
        payload={"content": "What is current?"},
        event_id="current-event",
        timestamp="2026-08-18T06:45:00+09:00",
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


def _authority(scope: MemoryTemporalScope) -> MemoryTemporalAuthority:
    if scope is MemoryTemporalScope.UNKNOWN:
        return MemoryTemporalAuthority(temporal_scope=scope)
    return MemoryTemporalAuthority(
        temporal_scope=scope,
        provenance=MemoryProvenance(
            memory_id=f"memory-inline-negation-{scope.value}",
            derivation_id=f"derivation-inline-negation-{scope.value}",
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
        location=f"memory/MEMORY.md#memory/inline-negation-{scope.value}",
        content=f"## {heading}\n\n{content}",
        temporal_authority=_authority(scope),
    )


def _compile(*, chunk: MemoryChunk, state: CanonicalState | None = None):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state or _state(),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


def test_unknown_single_inline_assignment_negating_current_scalar_is_suppressed() -> None:
    stale = _chunk("residence_location: not Fukuoka")

    assert _compile(chunk=stale).memory == ()


def test_unknown_single_inline_assignment_negating_different_scalar_is_retained() -> None:
    compatible = _chunk("residence_location = not Hokkaido")

    compiled = _compile(chunk=compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_current_single_inline_assignment_negating_current_scalar_is_suppressed() -> None:
    stale = _chunk(
        "residence_location: not Fukuoka",
        scope=MemoryTemporalScope.CURRENT,
    )

    assert _compile(chunk=stale).memory == ()


def test_current_single_inline_assignment_negating_different_scalar_is_retained() -> None:
    compatible = _chunk(
        "residence_location: not Hokkaido",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(chunk=compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_historical_inline_negation_remains_exempt() -> None:
    historical = _chunk(
        "residence_location: not Fukuoka",
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(chunk=historical)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_positive_inline_assignment_mismatch_remains_suppressed() -> None:
    stale = _chunk("residence_location: Hokkaido")

    assert _compile(chunk=stale).memory == ()


def test_positive_inline_assignment_match_remains_retained() -> None:
    current = _chunk("residence_location: Fukuoka")

    compiled = _compile(chunk=current)

    assert [item.location for item in compiled.memory] == [current.location]


def test_heading_addressed_negation_remains_outside_c10() -> None:
    deferred = _chunk("not Fukuoka", heading="Residence Location")

    compiled = _compile(chunk=deferred)

    assert [item.location for item in compiled.memory] == [deferred.location]


def test_multiple_inline_assignments_remain_outside_c10() -> None:
    deferred = _chunk(
        "residence_location: not Hokkaido\nresidence_location: Hokkaido"
    )

    assert _compile(chunk=deferred).memory == ()


def test_not_prefix_without_token_boundary_remains_positive_mismatch() -> None:
    stale = _chunk("residence_location: notFukuoka")

    assert _compile(chunk=stale).memory == ()


def test_boolean_inline_negation_remains_outside_c10() -> None:
    deferred = _chunk("notifications_enabled: not true")

    compiled = _compile(
        chunk=deferred,
        state=_state(key="notifications_enabled", value=True),
    )

    assert [item.location for item in compiled.memory] == [deferred.location]


def test_reserved_degree_inline_negation_remains_outside_c10() -> None:
    deferred = _chunk("tea: not likes; degree_hint: 0.85")

    compiled = _compile(
        chunk=deferred,
        state=_state(
            key="tea",
            value={"semantic": "likes", "degree_hint": 0.85},
        ),
    )

    assert [item.location for item in compiled.memory] == [deferred.location]

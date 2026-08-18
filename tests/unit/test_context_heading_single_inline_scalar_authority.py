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
        timestamp="2026-08-18T10:30:00+09:00",
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
            memory_id=f"memory-heading-inline-scalar-{scope.value}",
            derivation_id=f"derivation-heading-inline-scalar-{scope.value}",
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
        heading_path=("Memory", "Residence Location"),
        location=f"memory/MEMORY.md#memory/heading-inline-scalar-{scope.value}",
        content=f"## Residence Location\n\n{body}",
        temporal_authority=_authority(scope),
    )


def _compile(*, chunk: MemoryChunk, state: CanonicalState | None = None):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state or _state(),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


def test_heading_single_inline_positive_conflict_suppresses_despite_tail_current_value() -> None:
    stale = _chunk(
        "residence_location: Hokkaido",
        tail="A separate note mentions Fukuoka.",
    )

    assert _compile(chunk=stale).memory == ()


def test_heading_single_inline_positive_match_retains() -> None:
    current = _chunk("residence_location: Fukuoka")

    compiled = _compile(chunk=current)

    assert [item.location for item in compiled.memory] == [current.location]


def test_heading_single_inline_negating_current_scalar_suppresses() -> None:
    stale = _chunk("residence_location: not Fukuoka")

    assert _compile(chunk=stale).memory == ()


def test_heading_single_inline_negating_different_scalar_retains() -> None:
    compatible = _chunk("residence_location = not Hokkaido")

    compiled = _compile(chunk=compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_heading_single_inline_numeric_conflict_suppresses() -> None:
    stale = MemoryChunk(
        heading_path=("Memory", "Lucky Number"),
        location="memory/MEMORY.md#memory/heading-inline-number-unknown",
        content="## Lucky Number\n\nlucky_number: 7\nA separate note mentions 5.",
        temporal_authority=_authority(MemoryTemporalScope.UNKNOWN),
    )

    assert _compile(
        chunk=stale,
        state=_state(key="lucky_number", value=5),
    ).memory == ()


def test_typed_current_uses_same_heading_single_inline_scalar_rule() -> None:
    stale = _chunk(
        "residence_location: Hokkaido",
        scope=MemoryTemporalScope.CURRENT,
        tail="A separate note mentions Fukuoka.",
    )

    assert _compile(chunk=stale).memory == ()


def test_historical_heading_single_inline_scalar_remains_exempt() -> None:
    historical = _chunk(
        "residence_location: Hokkaido",
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(chunk=historical)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_empty_heading_single_inline_assignment_falls_through_existing_rule() -> None:
    empty = _chunk("residence_location:")

    assert _compile(chunk=empty).memory == ()


def test_heading_multiple_inline_scalar_assignments_remain_outside_c19() -> None:
    deferred = MemoryChunk(
        heading_path=("Memory", "Residence Location"),
        location="memory/MEMORY.md#memory/heading-multiple-scalar-unknown",
        content=(
            "## Residence Location\n\n"
            "residence_location: Fukuoka\n"
            "residence_location: Hokkaido"
        ),
        temporal_authority=_authority(MemoryTemporalScope.UNKNOWN),
    )

    compiled = _compile(chunk=deferred)

    assert [item.location for item in compiled.memory] == [deferred.location]

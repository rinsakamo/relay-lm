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
        timestamp="2026-08-18T06:55:00+09:00",
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
            memory_id=f"memory-heading-negation-{scope.value}",
            derivation_id=f"derivation-heading-negation-{scope.value}",
            sources=(
                MemoryProvenanceSource(
                    kind=MemoryProvenanceSourceKind.EVENT,
                    reference_id="memory-source-event",
                ),
            ),
        ),
    )


def _chunk(
    body: str,
    *,
    scope: MemoryTemporalScope = MemoryTemporalScope.UNKNOWN,
    heading: str = "Residence Location",
) -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", heading),
        location=f"memory/MEMORY.md#memory/heading-negation-{scope.value}",
        content=f"## {heading}\n\n{body}",
        temporal_authority=_authority(scope),
    )


def _compile(*, chunk: MemoryChunk, state: CanonicalState | None = None):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state or _state(),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


def test_unknown_heading_single_body_negating_current_scalar_is_suppressed() -> None:
    stale = _chunk("not Fukuoka")

    assert _compile(chunk=stale).memory == ()


def test_unknown_heading_single_body_negating_different_scalar_is_retained() -> None:
    compatible = _chunk("not Hokkaido")

    compiled = _compile(chunk=compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_current_heading_single_body_negating_current_scalar_is_suppressed() -> None:
    stale = _chunk("not Fukuoka", scope=MemoryTemporalScope.CURRENT)

    assert _compile(chunk=stale).memory == ()


def test_current_heading_single_body_negating_different_scalar_is_retained() -> None:
    compatible = _chunk("not Hokkaido", scope=MemoryTemporalScope.CURRENT)

    compiled = _compile(chunk=compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_numeric_heading_single_body_negating_different_scalar_is_retained() -> None:
    compatible = _chunk("not 7", heading="Lucky Number")

    compiled = _compile(
        chunk=compatible,
        state=_state(key="lucky_number", value=5),
    )

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_numeric_heading_single_body_negating_current_scalar_is_suppressed() -> None:
    stale = _chunk("not 5", heading="Lucky Number")

    assert _compile(chunk=stale, state=_state(key="lucky_number", value=5)).memory == ()


def test_historical_heading_negation_remains_exempt() -> None:
    historical = _chunk("not Fukuoka", scope=MemoryTemporalScope.HISTORICAL)

    compiled = _compile(chunk=historical)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_positive_heading_mismatch_remains_suppressed() -> None:
    stale = _chunk("Hokkaido")

    assert _compile(chunk=stale).memory == ()


def test_positive_heading_match_remains_retained() -> None:
    current = _chunk("Fukuoka")

    compiled = _compile(chunk=current)

    assert [item.location for item in compiled.memory] == [current.location]


def test_multiple_nonempty_body_lines_remain_outside_c11() -> None:
    deferred = _chunk("not Hokkaido\nadditional note")

    assert _compile(chunk=deferred).memory == ()


def test_not_prefix_without_token_boundary_remains_positive_mismatch() -> None:
    stale = _chunk("notFukuoka")

    assert _compile(chunk=stale).memory == ()

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
        payload={"content": "What is current?"},
        event_id="current-event",
        timestamp="2026-08-18T10:45:00+09:00",
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
            memory_id=f"memory-heading-multi-scalar-{scope.value}",
            derivation_id=f"derivation-heading-multi-scalar-{scope.value}",
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
    heading: str = "Residence Location",
    tail: str | None = None,
) -> MemoryChunk:
    body_lines = assignments + ((tail,) if tail is not None else ())
    return MemoryChunk(
        heading_path=("Memory", heading),
        location=f"memory/MEMORY.md#memory/heading-multi-scalar-{scope.value}",
        content=f"## {heading}\n\n" + "\n".join(body_lines),
        temporal_authority=_authority(scope),
    )


def _compile(*, chunk: MemoryChunk, state: CanonicalState | None = None):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=state or _state(),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


@pytest.mark.parametrize(
    "assignments",
    [
        ("residence_location: Fukuoka", "residence_location: Hokkaido"),
        ("residence_location: Fukuoka", "residence_location: not Fukuoka"),
        ("residence_location: Hokkaido", "residence_location: Tokyo"),
    ],
)
def test_heading_multiple_any_conflicting_scalar_assignment_suppresses(
    assignments: tuple[str, ...],
) -> None:
    stale = _chunk(assignments, tail="A separate note mentions Fukuoka.")

    assert _compile(chunk=stale).memory == ()


@pytest.mark.parametrize(
    "assignments",
    [
        ("residence_location: Fukuoka", "residence_location: not Hokkaido"),
        ("residence_location: not Hokkaido", "residence_location: not Tokyo"),
    ],
)
def test_heading_multiple_all_compatible_scalar_assignments_retain(
    assignments: tuple[str, ...],
) -> None:
    compatible = _chunk(assignments)

    compiled = _compile(chunk=compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_heading_multiple_numeric_conflicting_assignment_suppresses() -> None:
    stale = _chunk(
        ("lucky_number: 5", "lucky_number: 7"),
        heading="Lucky Number",
        tail="A separate note mentions 5.",
    )

    assert _compile(
        chunk=stale,
        state=_state(key="lucky_number", value=5),
    ).memory == ()


def test_heading_multiple_numeric_compatible_negations_retain() -> None:
    compatible = _chunk(
        ("lucky_number: not 7", "lucky_number: not 8"),
        heading="Lucky Number",
    )

    compiled = _compile(
        chunk=compatible,
        state=_state(key="lucky_number", value=5),
    )

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_typed_current_uses_same_heading_multiple_scalar_rule() -> None:
    stale = _chunk(
        ("residence_location: Fukuoka", "residence_location: Hokkaido"),
        scope=MemoryTemporalScope.CURRENT,
    )

    assert _compile(chunk=stale).memory == ()


def test_historical_heading_multiple_scalar_assignments_remain_exempt() -> None:
    historical = _chunk(
        ("residence_location: Fukuoka", "residence_location: Hokkaido"),
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(chunk=historical)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_empty_assignment_prevents_partial_c20_interpretation() -> None:
    fallback = _chunk(
        ("residence_location:", "residence_location: Fukuoka"),
    )

    compiled = _compile(chunk=fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_nonlexical_assignment_prevents_partial_c20_interpretation() -> None:
    fallback = _chunk(
        ("residence_location: !!!", "residence_location: Fukuoka"),
    )

    compiled = _compile(chunk=fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_heading_single_inline_scalar_remains_governed_by_c19() -> None:
    stale = _chunk(("residence_location: Hokkaido",), tail="Fukuoka is mentioned elsewhere.")

    assert _compile(chunk=stale).memory == ()

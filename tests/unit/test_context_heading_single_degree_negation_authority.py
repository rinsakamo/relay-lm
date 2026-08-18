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
        payload={"content": "What is current about tea?"},
        event_id="current-event",
        timestamp="2026-08-18T23:05:00+09:00",
    )


def _state() -> CanonicalState:
    return CanonicalState(
        states=(
            StateRecord(
                state_id="tea-current",
                state_class="user.preference",
                key="tea",
                value={"semantic": "likes", "degree_hint": 0.85},
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
            memory_id=f"memory-heading-degree-negation-{scope.value}",
            derivation_id=f"derivation-heading-degree-negation-{scope.value}",
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
    heading: str = "Tea",
) -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", heading),
        location=f"memory/MEMORY.md#memory/heading-degree-negation-{scope.value}",
        content=f"## {heading}\n\n{body}",
        temporal_authority=_authority(scope),
    )


def _compile(chunk: MemoryChunk):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


def test_heading_single_exact_negation_of_active_reserved_pair_suppresses() -> None:
    stale = _chunk("tea: not likes; degree_hint: 0.85")

    assert _compile(stale).memory == ()


def test_heading_single_negation_of_different_semantic_pair_is_compatible() -> None:
    compatible = _chunk("tea: not dislikes; degree_hint: 0.85")

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_heading_single_negation_of_different_degree_pair_is_compatible() -> None:
    compatible = _chunk("tea: not likes; degree_hint: 0.65")

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_typed_current_uses_same_heading_single_degree_negation_rule() -> None:
    compatible = _chunk(
        "tea: not dislikes; degree_hint: 0.85",
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_historical_heading_single_degree_negation_remains_exempt() -> None:
    historical = _chunk(
        "tea: not likes; degree_hint: 0.85",
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(historical)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_additional_section_degree_keeps_c1_authority() -> None:
    fallback = _chunk(
        "tea: not dislikes; degree_hint: 0.85\n"
        "degree_hint: 0.65"
    )

    assert _compile(fallback).memory == ()


def test_positive_heading_single_reserved_pair_remains_governed_by_c21() -> None:
    stale = _chunk(
        "tea: dislikes; degree_hint: 0.85\n"
        "A separate note says Rin likes tea."
    )

    assert _compile(stale).memory == ()


def test_inline_only_single_reserved_negation_remains_governed_by_c25() -> None:
    inline_only = _chunk(
        "tea: not dislikes; degree_hint: 0.85",
        heading="Profile Notes",
    )

    compiled = _compile(inline_only)

    assert [item.location for item in compiled.memory] == [inline_only.location]


def test_bare_not_remains_outside_c26_and_on_c1_fallback() -> None:
    fallback = _chunk("tea: not; degree_hint: 0.85")

    assert _compile(fallback).memory == ()


def test_double_negation_remains_outside_c26_and_on_c1_fallback() -> None:
    fallback = _chunk("tea: not not dislikes; degree_hint: 0.85")

    assert _compile(fallback).memory == ()


def test_nonexact_negated_reserved_pair_remains_on_c1_fallback() -> None:
    fallback = _chunk("tea: not dislikes; degree_hint: 0.85; note: survey")

    assert _compile(fallback).memory == ()


def test_heading_multiple_reserved_negation_remains_outside_c26() -> None:
    deferred = _chunk(
        "tea: not dislikes; degree_hint: 0.85\n"
        "tea: likes; degree_hint: 0.85"
    )

    compiled = _compile(deferred)

    assert [item.location for item in compiled.memory] == [deferred.location]


def test_heading_body_without_inline_assignment_remains_outside_c26() -> None:
    fallback = _chunk("not dislikes; degree_hint: 0.85")

    assert _compile(fallback).memory == ()

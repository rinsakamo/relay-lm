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
        timestamp="2026-08-19T00:45:00+09:00",
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
            memory_id=f"memory-inline-multi-degree-negation-{scope.value}",
            derivation_id=f"derivation-inline-multi-degree-negation-{scope.value}",
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
    heading: str = "Profile Notes",
    tail: str | None = None,
) -> MemoryChunk:
    body_lines = assignments + ((tail,) if tail is not None else ())
    return MemoryChunk(
        heading_path=("Memory", heading),
        location=f"memory/MEMORY.md#memory/inline-multi-degree-negation-{scope.value}",
        content=f"## {heading}\n\n" + "\n".join(body_lines),
        temporal_authority=_authority(scope),
    )


def _compile(chunk: MemoryChunk):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


def test_inline_multiple_all_negated_active_pair_member_suppresses() -> None:
    stale = _chunk(
        (
            "tea: not likes; degree_hint: 0.85",
            "tea: not dislikes; degree_hint: 0.85",
        )
    )

    assert _compile(stale).memory == ()


def test_inline_multiple_all_negated_different_semantic_pairs_are_compatible() -> None:
    compatible = _chunk(
        (
            "tea: not dislikes; degree_hint: 0.85",
            "tea = not avoids; degree_hint=0.65",
        )
    )

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_inline_multiple_all_negated_different_degree_pair_is_compatible() -> None:
    compatible = _chunk(
        (
            "tea: not likes; degree_hint: 0.65",
            "tea: not dislikes; degree_hint: 0.85",
        )
    )

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_typed_current_uses_same_inline_multiple_all_negated_rule() -> None:
    compatible = _chunk(
        (
            "tea: not dislikes; degree_hint: 0.85",
            "tea: not avoids; degree_hint: 0.65",
        ),
        scope=MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_historical_inline_multiple_all_negated_set_remains_exempt() -> None:
    historical = _chunk(
        (
            "tea: not likes; degree_hint: 0.85",
            "tea: not dislikes; degree_hint: 0.85",
        ),
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(historical)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_positive_only_multiple_set_remains_governed_by_c23() -> None:
    stale = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea: dislikes; degree_hint: 0.85",
        )
    )

    assert _compile(stale).memory == ()


def test_mixed_positive_and_negated_set_remains_outside_c28() -> None:
    fallback = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea: not dislikes; degree_hint: 0.85",
        )
    )

    compiled = _compile(fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_nonexact_member_prevents_partial_c28_interpretation() -> None:
    fallback = _chunk(
        (
            "tea: not dislikes; degree_hint: 0.85; note: survey",
            "tea: not avoids; degree_hint: 0.65",
        )
    )

    assert _compile(fallback).memory == ()


def test_bare_not_member_prevents_c28_set_interpretation() -> None:
    fallback = _chunk(
        (
            "tea: not; degree_hint: 0.85",
            "tea: not dislikes; degree_hint: 0.85",
        )
    )

    assert _compile(fallback).memory == ()


def test_double_negation_member_prevents_c28_set_interpretation() -> None:
    fallback = _chunk(
        (
            "tea: not not likes; degree_hint: 0.85",
            "tea: not dislikes; degree_hint: 0.85",
        )
    )

    compiled = _compile(fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_single_inline_negated_pair_remains_governed_by_c25() -> None:
    compatible = _chunk(("tea: not dislikes; degree_hint: 0.85",))

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]

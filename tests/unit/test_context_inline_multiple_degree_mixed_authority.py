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
        timestamp="2026-08-19T08:00:00+09:00",
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
            memory_id=f"memory-inline-multi-degree-mixed-{scope.value}",
            derivation_id=f"derivation-inline-multi-degree-mixed-{scope.value}",
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
        location=f"memory/MEMORY.md#memory/inline-multi-degree-mixed-{scope.value}",
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


def test_inline_multiple_mixed_active_pair_negation_suppresses() -> None:
    stale = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea: not likes; degree_hint: 0.85",
        )
    )

    assert _compile(stale).memory == ()


def test_inline_multiple_mixed_different_semantic_negation_is_compatible() -> None:
    compatible = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea = not dislikes; degree_hint=0.85",
        )
    )

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_inline_multiple_mixed_different_degree_negation_is_compatible() -> None:
    compatible = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea: not likes; degree_hint: 0.65",
        )
    )

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_inline_multiple_mixed_positive_mismatch_suppresses() -> None:
    stale = _chunk(
        (
            "tea: dislikes; degree_hint: 0.85",
            "tea: not avoids; degree_hint: 0.65",
        )
    )

    assert _compile(stale).memory == ()


def test_inline_multiple_mixed_positive_mismatch_and_active_negation_suppress() -> None:
    stale = _chunk(
        (
            "tea: dislikes; degree_hint: 0.85",
            "tea: not likes; degree_hint: 0.85",
        )
    )

    assert _compile(stale).memory == ()


def test_typed_current_uses_same_inline_multiple_mixed_rule() -> None:
    stale = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea: not likes; degree_hint: 0.85",
        ),
        scope=MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale).memory == ()


def test_historical_inline_multiple_mixed_set_remains_exempt() -> None:
    historical = _chunk(
        (
            "tea: dislikes; degree_hint: 0.85",
            "tea: not likes; degree_hint: 0.85",
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


def test_all_negated_multiple_set_remains_governed_by_c28() -> None:
    stale = _chunk(
        (
            "tea: not likes; degree_hint: 0.85",
            "tea: not dislikes; degree_hint: 0.85",
        )
    )

    assert _compile(stale).memory == ()


def test_nonexact_member_prevents_partial_c30_interpretation() -> None:
    fallback = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea: not dislikes; degree_hint: 0.85; note: survey",
        )
    )

    compiled = _compile(fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_bare_not_member_prevents_c30_interpretation() -> None:
    fallback = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea: not; degree_hint: 0.85",
        )
    )

    compiled = _compile(fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_double_negation_member_prevents_c30_interpretation() -> None:
    fallback = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea: not not dislikes; degree_hint: 0.85",
        )
    )

    compiled = _compile(fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_single_inline_negated_pair_remains_governed_by_c25() -> None:
    compatible = _chunk(("tea: not dislikes; degree_hint: 0.85",))

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]

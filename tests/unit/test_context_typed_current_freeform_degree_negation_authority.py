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
        payload={"content": "How much do I like tea?"},
        event_id="current-event",
        timestamp="2026-08-19T08:55:00+09:00",
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
            memory_id=f"memory-freeform-degree-negation-{scope.value}",
            derivation_id=f"derivation-freeform-degree-negation-{scope.value}",
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
    scope: MemoryTemporalScope = MemoryTemporalScope.CURRENT,
) -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", "Profile Notes"),
        location=f"memory/MEMORY.md#memory/freeform-degree-negation-{scope.value}",
        content=f"## Profile Notes\n\n{content}",
        temporal_authority=_authority(scope),
    )


def _compile(chunk: MemoryChunk):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


def test_typed_current_freeform_active_pair_negation_suppresses() -> None:
    stale = _chunk("Current tea is not likes; degree_hint: 0.85.")

    assert _compile(stale).memory == ()


def test_typed_current_freeform_different_semantic_negation_is_compatible() -> None:
    compatible = _chunk("Current tea is not dislikes; degree_hint: 0.85.")

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_typed_current_freeform_different_degree_negation_is_compatible() -> None:
    compatible = _chunk("Tea is currently not likes; degree_hint=0.65.")

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_positive_exact_pair_match_remains_governed_by_c8() -> None:
    current = _chunk("Current tea is likes; degree_hint: 0.85.")

    compiled = _compile(current)

    assert [item.location for item in compiled.memory] == [current.location]


def test_positive_semantic_mismatch_remains_governed_by_c8() -> None:
    stale = _chunk("Current tea is dislikes; degree_hint: 0.85.")

    assert _compile(stale).memory == ()


def test_positive_degree_mismatch_remains_governed_by_c8() -> None:
    stale = _chunk("Current tea is likes; degree_hint: 0.65.")

    assert _compile(stale).memory == ()


def test_compatible_negation_does_not_hide_later_positive_conflict() -> None:
    stale = _chunk(
        "Current tea is not dislikes; degree_hint: 0.85.\n"
        "Current tea is dislikes; degree_hint: 0.85."
    )

    assert _compile(stale).memory == ()


def test_positive_match_does_not_hide_later_active_pair_negation() -> None:
    stale = _chunk(
        "Current tea is likes; degree_hint: 0.85.\n"
        "Current tea is not likes; degree_hint: 0.85."
    )

    assert _compile(stale).memory == ()


def test_compatible_negation_and_positive_match_retain() -> None:
    compatible = _chunk(
        "Current tea is not dislikes; degree_hint: 0.85.\n"
        "Current tea is likes; degree_hint: 0.85."
    )

    compiled = _compile(compatible)

    assert [item.location for item in compiled.memory] == [compatible.location]


def test_bare_not_reserved_pair_remains_uninterpreted() -> None:
    fallback = _chunk("Current tea is not; degree_hint: 0.85.")

    compiled = _compile(fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_double_negation_reserved_pair_remains_uninterpreted() -> None:
    fallback = _chunk("Current tea is not not likes; degree_hint: 0.85.")

    compiled = _compile(fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_missing_degree_negation_remains_outside_reserved_pair_grammar() -> None:
    fallback = _chunk("Current tea is not likes.")

    compiled = _compile(fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_unknown_scope_does_not_gain_freeform_negation_authority() -> None:
    unknown = _chunk(
        "Current tea is not likes; degree_hint: 0.85.",
        scope=MemoryTemporalScope.UNKNOWN,
    )

    compiled = _compile(unknown)

    assert [item.location for item in compiled.memory] == [unknown.location]


def test_historical_scope_remains_exempt() -> None:
    historical = _chunk(
        "Current tea is not likes; degree_hint: 0.85.",
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(historical)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_prefixed_current_claim_remains_outside_bounded_freeform_grammar() -> None:
    fallback = _chunk("Previous current tea is not likes; degree_hint: 0.85.")

    compiled = _compile(fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_structural_inline_negation_remains_governed_by_c25() -> None:
    stale = _chunk("tea: not likes; degree_hint: 0.85")

    assert _compile(stale).memory == ()

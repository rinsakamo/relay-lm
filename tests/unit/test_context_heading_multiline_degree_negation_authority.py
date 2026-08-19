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
        timestamp="2026-08-19T12:30:00+09:00",
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
            memory_id=f"memory-heading-multiline-degree-negation-{scope.value}",
            derivation_id=f"derivation-heading-multiline-degree-negation-{scope.value}",
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
        location=(
            "memory/MEMORY.md#memory/heading-multiline-degree-negation-"
            f"{scope.value}"
        ),
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


def _assert_retained(chunk: MemoryChunk) -> None:
    compiled = _compile(chunk)
    assert [item.location for item in compiled.memory] == [chunk.location]


def test_multiline_exact_active_pair_negation_suppresses_despite_prose_rescue() -> None:
    stale = _chunk(
        "not likes; degree_hint: 0.85\n"
        "A separate prose note says likes."
    )

    assert _compile(stale).memory == ()


def test_multiline_different_semantic_negation_is_compatible() -> None:
    compatible = _chunk(
        "not dislikes; degree_hint: 0.85\n"
        "A separate prose note."
    )

    _assert_retained(compatible)


def test_multiline_different_degree_negation_is_compatible() -> None:
    compatible = _chunk(
        "not likes; degree_hint=0.65\n"
        "A separate prose note."
    )

    _assert_retained(compatible)


def test_typed_current_uses_same_multiline_structural_rule() -> None:
    compatible = _chunk(
        "not dislikes; degree_hint: 0.85\n"
        "A separate prose note.",
        scope=MemoryTemporalScope.CURRENT,
    )

    _assert_retained(compatible)


def test_historical_multiline_active_pair_negation_remains_exempt() -> None:
    historical = _chunk(
        "not likes; degree_hint: 0.85\n"
        "A separate prose note.",
        scope=MemoryTemporalScope.HISTORICAL,
    )

    _assert_retained(historical)


def test_additional_matching_section_degree_disables_c33_decision() -> None:
    fallback = _chunk(
        "not likes; degree_hint: 0.85\n"
        "A separate degree_hint: 0.85 note."
    )

    _assert_retained(fallback)


def test_additional_stale_section_degree_remains_c1_conflict() -> None:
    fallback = _chunk(
        "not likes; degree_hint: 0.85\n"
        "A separate degree_hint: 0.65 note."
    )

    assert _compile(fallback).memory == ()


def test_multiple_exact_negated_body_claims_remain_on_c1_fallback() -> None:
    fallback = _chunk(
        "not likes; degree_hint: 0.85\n"
        "not dislikes; degree_hint: 0.85"
    )

    _assert_retained(fallback)


def test_positive_multiline_reserved_pair_match_remains_c1() -> None:
    current = _chunk(
        "likes; degree_hint: 0.85\n"
        "A separate prose note."
    )

    _assert_retained(current)


def test_positive_multiline_reserved_semantic_conflict_remains_c1() -> None:
    stale = _chunk(
        "dislikes; degree_hint: 0.85\n"
        "A separate prose note."
    )

    assert _compile(stale).memory == ()


def test_positive_multiline_reserved_degree_conflict_remains_c1() -> None:
    stale = _chunk(
        "likes; degree_hint: 0.65\n"
        "A separate prose note."
    )

    assert _compile(stale).memory == ()


def test_single_body_exact_negation_remains_c27() -> None:
    stale = _chunk("not likes; degree_hint: 0.85")

    assert _compile(stale).memory == ()


def test_heading_inline_negation_remains_c26() -> None:
    compatible = _chunk(
        "tea: not dislikes; degree_hint: 0.85\n"
        "A separate prose note."
    )

    _assert_retained(compatible)


def test_bare_not_multiline_remains_on_c1_fallback() -> None:
    fallback = _chunk(
        "not; degree_hint: 0.85\n"
        "A separate prose note."
    )

    assert _compile(fallback).memory == ()


def test_double_negation_multiline_remains_on_c1_fallback() -> None:
    fallback = _chunk(
        "not not dislikes; degree_hint: 0.85\n"
        "A separate prose note."
    )

    assert _compile(fallback).memory == ()


def test_nonexact_negated_pair_multiline_remains_on_c1_fallback() -> None:
    fallback = _chunk(
        "not likes; degree_hint: 0.85; note: survey\n"
        "A separate prose note."
    )

    _assert_retained(fallback)

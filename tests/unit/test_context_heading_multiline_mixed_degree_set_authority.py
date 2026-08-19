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
        timestamp="2026-08-19T14:15:00+09:00",
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
            memory_id=f"memory-heading-multiline-mixed-set-{scope.value}",
            derivation_id=f"derivation-heading-multiline-mixed-set-{scope.value}",
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
            "memory/MEMORY.md#memory/heading-multiline-mixed-set-"
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


def test_matching_positive_and_different_negated_pair_are_compatible() -> None:
    current = _chunk(
        "likes; degree_hint: 0.85\n"
        "not dislikes; degree_hint: 0.85"
    )

    _assert_retained(current)


def test_exact_active_pair_negation_suppresses_mixed_set() -> None:
    stale = _chunk(
        "likes; degree_hint: 0.85\n"
        "not likes; degree_hint: 0.85"
    )

    assert _compile(stale).memory == ()


def test_exact_active_pair_negation_suppresses_when_first() -> None:
    stale = _chunk(
        "not likes; degree_hint: 0.85\n"
        "likes; degree_hint: 0.85"
    )

    assert _compile(stale).memory == ()


def test_matching_positive_cannot_hide_later_positive_mismatch() -> None:
    stale = _chunk(
        "likes; degree_hint: 0.85\n"
        "dislikes; degree_hint: 0.85\n"
        "not avoids; degree_hint: 0.85"
    )

    assert _compile(stale).memory == ()


def test_positive_mismatch_cannot_hide_before_matching_positive() -> None:
    stale = _chunk(
        "dislikes; degree_hint: 0.85\n"
        "likes; degree_hint: 0.85\n"
        "not avoids; degree_hint: 0.85"
    )

    assert _compile(stale).memory == ()


def test_different_degree_negation_is_compatible_in_mixed_set() -> None:
    current = _chunk(
        "likes; degree_hint: 0.85\n"
        "not likes; degree_hint: 0.65"
    )

    _assert_retained(current)


def test_three_member_mixed_set_checks_every_member() -> None:
    stale = _chunk(
        "likes; degree_hint: 0.85\n"
        "not dislikes; degree_hint: 0.85\n"
        "not likes; degree_hint: 0.85"
    )

    assert _compile(stale).memory == ()


def test_typed_current_uses_same_structural_mixed_set_rule() -> None:
    stale = _chunk(
        "likes; degree_hint: 0.85\n"
        "not likes; degree_hint: 0.85",
        scope=MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale).memory == ()


def test_historical_mixed_set_remains_exempt() -> None:
    historical = _chunk(
        "likes; degree_hint: 0.85\n"
        "not likes; degree_hint: 0.85",
        scope=MemoryTemporalScope.HISTORICAL,
    )

    _assert_retained(historical)


def test_degree_free_prose_does_not_become_a_mixed_member() -> None:
    current = _chunk(
        "likes; degree_hint: 0.85\n"
        "A degree-free prose note says dislikes.\n"
        "not dislikes; degree_hint: 0.85"
    )

    _assert_retained(current)


def test_degree_free_prose_does_not_rescue_active_pair_negation() -> None:
    stale = _chunk(
        "likes; degree_hint: 0.85\n"
        "A degree-free prose note says likes.\n"
        "not likes; degree_hint: 0.85"
    )

    assert _compile(stale).memory == ()


def test_additional_matching_section_degree_disables_c36_local_suppression() -> None:
    fallback = _chunk(
        "likes; degree_hint: 0.85\n"
        "not likes; degree_hint: 0.85\n"
        "A separate degree_hint: 0.85 note."
    )

    _assert_retained(fallback)


def test_additional_stale_section_degree_disables_c36_compatibility() -> None:
    fallback = _chunk(
        "likes; degree_hint: 0.85\n"
        "not dislikes; degree_hint: 0.85\n"
        "A separate degree_hint: 0.65 note."
    )

    assert _compile(fallback).memory == ()


def test_positive_only_set_remains_c34_authority() -> None:
    stale = _chunk(
        "likes; degree_hint: 0.85\n"
        "dislikes; degree_hint: 0.85"
    )

    assert _compile(stale).memory == ()


def test_all_negated_set_remains_c35_authority() -> None:
    stale = _chunk(
        "not dislikes; degree_hint: 0.85\n"
        "not likes; degree_hint: 0.85"
    )

    assert _compile(stale).memory == ()


def test_bare_not_member_prevents_mixed_set_activation() -> None:
    fallback = _chunk(
        "likes; degree_hint: 0.85\n"
        "not; degree_hint: 0.85"
    )

    _assert_retained(fallback)


def test_double_negation_member_prevents_mixed_set_activation() -> None:
    fallback = _chunk(
        "likes; degree_hint: 0.85\n"
        "not not dislikes; degree_hint: 0.85"
    )

    _assert_retained(fallback)


def test_nonexact_degree_bearing_body_text_disables_mixed_set_activation() -> None:
    fallback = _chunk(
        "likes; degree_hint: 0.85\n"
        "not dislikes; degree_hint: 0.85\n"
        "not likes; degree_hint: 0.85; note: survey"
    )

    _assert_retained(fallback)

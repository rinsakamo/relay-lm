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
        timestamp="2026-08-19T17:30:00+09:00",
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
            memory_id=f"memory-heading-multiline-single-positive-{scope.value}",
            derivation_id=f"derivation-heading-multiline-single-positive-{scope.value}",
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
            "memory/MEMORY.md#memory/heading-multiline-single-positive-"
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


def test_active_semantic_prose_cannot_rescue_single_positive_semantic_mismatch() -> None:
    stale = _chunk(
        "dislikes; degree_hint: 0.85\n"
        "A degree-free prose note also mentions likes."
    )

    assert _compile(stale).memory == ()


def test_matching_single_positive_pair_with_degree_free_prose_is_compatible() -> None:
    current = _chunk(
        "likes; degree_hint: 0.85\n"
        "A degree-free prose note mentions dislikes."
    )

    _assert_retained(current)


def test_single_positive_degree_mismatch_suppresses() -> None:
    stale = _chunk(
        "likes; degree_hint: 0.65\n"
        "A degree-free prose note also mentions likes."
    )

    assert _compile(stale).memory == ()


def test_typed_current_uses_same_single_positive_locality() -> None:
    stale = _chunk(
        "dislikes; degree_hint: 0.85\n"
        "A degree-free prose note also mentions likes.",
        scope=MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale).memory == ()


def test_historical_single_positive_pair_remains_exempt() -> None:
    historical = _chunk(
        "dislikes; degree_hint: 0.85\n"
        "A degree-free prose note also mentions likes.",
        scope=MemoryTemporalScope.HISTORICAL,
    )

    _assert_retained(historical)


def test_degree_free_prose_does_not_become_a_second_positive_claim() -> None:
    current = _chunk(
        "likes; degree_hint: 0.85\n"
        "A degree-free prose note says dislikes."
    )

    _assert_retained(current)


def test_additional_matching_section_degree_disables_c37_local_mismatch() -> None:
    fallback = _chunk(
        "dislikes; degree_hint: 0.85\n"
        "A degree-free prose note mentions likes.\n"
        "A separate degree_hint: 0.85 note."
    )

    _assert_retained(fallback)


def test_additional_stale_section_degree_remains_c1_conflict() -> None:
    fallback = _chunk(
        "dislikes; degree_hint: 0.85\n"
        "A degree-free prose note mentions likes.\n"
        "A separate degree_hint: 0.65 note."
    )

    assert _compile(fallback).memory == ()


def test_single_negated_exact_pair_remains_c33_authority() -> None:
    stale = _chunk(
        "not likes; degree_hint: 0.85\n"
        "A degree-free prose note mentions likes."
    )

    assert _compile(stale).memory == ()


def test_two_positive_exact_pairs_remain_c34_authority() -> None:
    stale = _chunk(
        "likes; degree_hint: 0.85\n"
        "dislikes; degree_hint: 0.85"
    )

    assert _compile(stale).memory == ()


def test_two_all_negated_exact_pairs_remain_c35_authority() -> None:
    stale = _chunk(
        "not dislikes; degree_hint: 0.85\n"
        "not likes; degree_hint: 0.85"
    )

    assert _compile(stale).memory == ()


def test_mixed_exact_pair_set_remains_c36_authority() -> None:
    stale = _chunk(
        "likes; degree_hint: 0.85\n"
        "not likes; degree_hint: 0.85"
    )

    assert _compile(stale).memory == ()


def test_bare_not_exact_pair_prevents_c37_single_claim_activation() -> None:
    fallback = _chunk(
        "dislikes; degree_hint: 0.85\n"
        "not; degree_hint: 0.85\n"
        "A degree-free prose note mentions likes."
    )

    _assert_retained(fallback)


def test_double_negation_exact_pair_prevents_c37_single_claim_activation() -> None:
    fallback = _chunk(
        "dislikes; degree_hint: 0.85\n"
        "not not avoids; degree_hint: 0.85\n"
        "A degree-free prose note mentions likes."
    )

    _assert_retained(fallback)


def test_nonexact_degree_bearing_body_text_disables_c37_local_mismatch() -> None:
    fallback = _chunk(
        "dislikes; degree_hint: 0.85\n"
        "A degree-free prose note mentions likes.\n"
        "not likes; degree_hint: 0.85; note: survey"
    )

    _assert_retained(fallback)

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
        timestamp="2026-08-18T12:40:00+09:00",
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
            memory_id=f"memory-inline-degree-{scope.value}",
            derivation_id=f"derivation-inline-degree-{scope.value}",
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
) -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", "Profile Notes"),
        location=f"memory/MEMORY.md#memory/inline-degree-{scope.value}",
        content=f"## Profile Notes\n\n{body}",
        temporal_authority=_authority(scope),
    )


def _compile(chunk: MemoryChunk):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


def test_inline_single_exact_degree_semantic_conflict_suppresses_despite_tail_match() -> None:
    stale = _chunk(
        "tea: dislikes; degree_hint: 0.85\n"
        "A separate note says Rin likes tea."
    )

    assert _compile(stale).memory == ()


def test_inline_single_exact_degree_match_retains() -> None:
    current = _chunk("tea: likes; degree_hint = 0.85")

    compiled = _compile(current)

    assert [item.location for item in compiled.memory] == [current.location]


def test_inline_single_exact_stale_degree_remains_c1_suppressed() -> None:
    stale = _chunk("tea: likes; degree_hint: 0.65")

    assert _compile(stale).memory == ()


def test_typed_current_uses_same_inline_single_degree_rule() -> None:
    stale = _chunk(
        "tea: dislikes; degree_hint: 0.85\n"
        "A separate note says Rin likes tea.",
        scope=MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale).memory == ()


def test_historical_inline_single_degree_remains_exempt() -> None:
    historical = _chunk(
        "tea: dislikes; degree_hint: 0.65",
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(historical)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_nonexact_inline_single_degree_value_remains_c1_fallback() -> None:
    fallback = _chunk(
        "tea: dislikes; degree_hint: 0.85; note: survey\n"
        "A separate note says Rin likes tea."
    )

    compiled = _compile(fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_multiple_inline_same_key_reserved_assignments_remain_outside_c22() -> None:
    deferred = _chunk(
        "tea: likes; degree_hint: 0.85\n"
        "tea: dislikes; degree_hint: 0.85"
    )

    compiled = _compile(deferred)

    assert [item.location for item in compiled.memory] == [deferred.location]

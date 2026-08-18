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
        payload={"content": "What is current about tea?"},
        event_id="current-event",
        timestamp="2026-08-18T18:58:00+09:00",
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
            memory_id=f"memory-inline-multi-degree-{scope.value}",
            derivation_id=f"derivation-inline-multi-degree-{scope.value}",
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
        location=f"memory/MEMORY.md#memory/inline-multi-degree-{scope.value}",
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


def test_inline_multiple_semantic_conflict_suppresses_despite_local_match() -> None:
    stale = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea: dislikes; degree_hint: 0.85",
        )
    )

    assert _compile(stale).memory == ()


def test_inline_multiple_semantic_conflicts_suppress_despite_tail_match() -> None:
    stale = _chunk(
        (
            "tea: dislikes; degree_hint: 0.85",
            "tea: avoids; degree_hint: 0.85",
        ),
        tail="A separate note says Rin likes tea.",
    )

    assert _compile(stale).memory == ()


def test_typed_current_uses_same_inline_multiple_degree_rule() -> None:
    stale = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea: dislikes; degree_hint: 0.85",
        ),
        scope=MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale).memory == ()


def test_inline_multiple_all_matching_exact_reserved_assignments_retain() -> None:
    current = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea = likes; degree_hint=0.85",
        )
    )

    compiled = _compile(current)

    assert [item.location for item in compiled.memory] == [current.location]


def test_inline_multiple_degree_mismatch_remains_suppressed() -> None:
    stale = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea: likes; degree_hint: 0.65",
        )
    )

    assert _compile(stale).memory == ()


def test_historical_inline_multiple_reserved_assignments_remain_exempt() -> None:
    historical = _chunk(
        (
            "tea: likes; degree_hint: 0.85",
            "tea: dislikes; degree_hint: 0.85",
        ),
        scope=MemoryTemporalScope.HISTORICAL,
    )

    compiled = _compile(historical)

    assert [item.location for item in compiled.memory] == [historical.location]


def test_nonexact_member_prevents_partial_c23_interpretation() -> None:
    fallback = _chunk(
        (
            "tea: likes; degree_hint: 0.85; note: survey",
            "tea: dislikes; degree_hint: 0.85",
        )
    )

    compiled = _compile(fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_negated_member_prevents_partial_c23_interpretation() -> None:
    fallback = _chunk(
        (
            "tea: not likes; degree_hint: 0.85",
            "tea: dislikes; degree_hint: 0.85",
        )
    )

    compiled = _compile(fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]


def test_single_inline_reserved_assignment_remains_governed_by_c22() -> None:
    stale = _chunk(
        ("tea: dislikes; degree_hint: 0.85",),
        tail="A separate note says Rin likes tea.",
    )

    assert _compile(stale).memory == ()


@pytest.mark.parametrize(
    "assignments",
    [
        (
            "tea: likes; degree_hint: 0.85",
            "tea: dislikes; degree_hint: 0.85; note: survey",
        ),
        (
            "tea: likes; degree_hint: 0.85",
            "tea: not dislikes; degree_hint: 0.85",
        ),
    ],
)
def test_any_unrecognized_member_keeps_set_on_c1_fallback(
    assignments: tuple[str, ...],
) -> None:
    fallback = _chunk(assignments)

    compiled = _compile(fallback)

    assert [item.location for item in compiled.memory] == [fallback.location]

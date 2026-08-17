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
        payload={"content": "How much do I like tea?"},
        event_id="current-event",
        timestamp="2026-08-18T06:24:00+09:00",
    )


def _state(*, semantic: str = "likes", degree_hint: float = 0.85) -> CanonicalState:
    return CanonicalState(
        states=(
            StateRecord(
                state_id="tea-current",
                state_class="user.preference",
                key="tea",
                value={"semantic": semantic, "degree_hint": degree_hint},
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
            memory_id=f"memory-tea-{scope.value}",
            derivation_id=f"derivation-tea-{scope.value}",
            sources=(
                MemoryProvenanceSource(
                    kind=MemoryProvenanceSourceKind.EVENT,
                    reference_id="memory-source-event",
                ),
            ),
        ),
    )


def _chunk(content: str, scope: MemoryTemporalScope) -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", "Profile Notes"),
        location=f"memory/MEMORY.md#memory/tea-{scope.value}",
        content=f"## Profile Notes\n\n{content}",
        temporal_authority=_authority(scope),
    )


def _compile(
    chunk: MemoryChunk,
    *,
    semantic: str = "likes",
    degree_hint: float = 0.85,
):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(semantic=semantic, degree_hint=degree_hint),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


def test_typed_current_freeform_degree_conflict_is_suppressed() -> None:
    stale = _chunk(
        "Current tea is likes; degree_hint: 0.65.",
        MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale).memory == ()


def test_typed_current_freeform_degree_match_is_retained() -> None:
    current = _chunk(
        "Tea is currently likes; degree_hint=0.85.",
        MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(current)

    assert [item.location for item in compiled.memory] == [current.location]


def test_matching_degree_does_not_rescue_freeform_semantic_conflict() -> None:
    stale = _chunk(
        "Current tea is dislikes; degree_hint: 0.85.",
        MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale).memory == ()


def test_typed_current_now_degree_conflict_is_suppressed() -> None:
    stale = _chunk(
        "Tea is now likes; degree_hint=0.65.",
        MemoryTemporalScope.CURRENT,
    )

    assert _compile(stale).memory == ()


@pytest.mark.parametrize(
    "scope",
    [MemoryTemporalScope.UNKNOWN, MemoryTemporalScope.HISTORICAL],
)
def test_noncurrent_scope_does_not_gain_freeform_degree_authority(
    scope: MemoryTemporalScope,
) -> None:
    chunk = _chunk("Current tea is likes; degree_hint: 0.65.", scope)

    compiled = _compile(chunk)

    assert [item.location for item in compiled.memory] == [chunk.location]


@pytest.mark.parametrize(
    "claim",
    [
        "Current tea is likes.",
        "Current tea is likes 0.65.",
        "Current tea is strongly liked.",
    ],
)
def test_missing_or_nonreserved_degree_claims_remain_uninterpreted(claim: str) -> None:
    chunk = _chunk(claim, MemoryTemporalScope.CURRENT)

    compiled = _compile(chunk)

    assert [item.location for item in compiled.memory] == [chunk.location]


def test_prefixed_degree_claim_remains_outside_bounded_grammar() -> None:
    chunk = _chunk(
        "Previous current tea is likes; degree_hint: 0.65.",
        MemoryTemporalScope.CURRENT,
    )

    compiled = _compile(chunk)

    assert [item.location for item in compiled.memory] == [chunk.location]

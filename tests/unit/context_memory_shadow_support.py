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


def memory_authority(scope: MemoryTemporalScope) -> MemoryTemporalAuthority:
    if scope is MemoryTemporalScope.UNKNOWN:
        return MemoryTemporalAuthority(temporal_scope=scope)
    return MemoryTemporalAuthority(
        temporal_scope=scope,
        provenance=MemoryProvenance(
            memory_id=f"memory-shadow-{scope.value}",
            derivation_id=f"derivation-shadow-{scope.value}",
            sources=(
                MemoryProvenanceSource(
                    kind=MemoryProvenanceSourceKind.EVENT,
                    reference_id="memory-source-event",
                ),
            ),
        ),
    )


def memory_chunk(
    content: str,
    *,
    heading: str = "Profile Notes",
    scope: MemoryTemporalScope = MemoryTemporalScope.UNKNOWN,
) -> MemoryChunk:
    slug = heading.casefold().replace(" ", "-")
    return MemoryChunk(
        heading_path=("Memory", heading),
        location=f"memory/MEMORY.md#memory/{slug}-{scope.value}",
        content=f"## {heading}\n\n{content}",
        temporal_authority=memory_authority(scope),
    )


def canonical_state(
    *,
    key: str,
    value: object,
    state_class: str = "user.fact",
) -> CanonicalState:
    return CanonicalState(
        states=(
            StateRecord(
                state_id="current-state",
                state_class=state_class,
                key=key,
                value=value,
                sources=("source-event",),
            ),
        )
    )


def memory_is_retained(
    *,
    content: str,
    key: str,
    value: object,
    heading: str = "Profile Notes",
    scope: MemoryTemporalScope = MemoryTemporalScope.UNKNOWN,
    state_class: str = "user.fact",
) -> bool:
    chunk = memory_chunk(content, heading=heading, scope=scope)
    current_event = Event.create(
        type="message",
        actor="user",
        payload={"content": "What is current?"},
        event_id="current-event",
        timestamp="2026-08-24T06:30:00+09:00",
    )
    compiled = compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=canonical_state(key=key, value=value, state_class=state_class),
        current_event=current_event,
        retrieved_memory=(chunk,),
    )
    return bool(compiled.memory)

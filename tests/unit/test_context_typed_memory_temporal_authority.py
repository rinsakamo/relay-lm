from __future__ import annotations

from relaylm.context import (
    compile_cognitive_input,
    compile_cognitive_input_with_diagnostics,
)
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
        payload={"content": "Where do I live now?"},
        event_id="current-event",
        timestamp="2026-08-17T16:10:00+00:00",
    )


def _state() -> CanonicalState:
    return CanonicalState(
        states=(
            StateRecord(
                state_id="state-current-residence",
                state_class="user.fact",
                key="residence_location",
                value="Fukuoka",
                sources=("event-current-residence",),
            ),
        )
    )


def _authority(scope: MemoryTemporalScope) -> MemoryTemporalAuthority:
    if scope is MemoryTemporalScope.UNKNOWN:
        return MemoryTemporalAuthority(temporal_scope=scope)
    return MemoryTemporalAuthority(
        temporal_scope=scope,
        provenance=MemoryProvenance(
            memory_id=f"memory-residence-{scope.value}",
            derivation_id=f"derivation-residence-{scope.value}",
            sources=(
                MemoryProvenanceSource(
                    kind=MemoryProvenanceSourceKind.EVENT,
                    reference_id="event-historical-residence",
                ),
            ),
        ),
    )


def _chunk(
    scope: MemoryTemporalScope,
    *,
    body: str = "Residence location: Hokkaido.",
) -> MemoryChunk:
    return MemoryChunk(
        heading_path=("Memory", "Residence location"),
        location=f"memory/MEMORY.md#memory/residence-location-{scope.value}",
        content=f"## Residence location\n\n{body}",
        temporal_authority=_authority(scope),
    )


def _compile(chunk: MemoryChunk):
    return compile_cognitive_input(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current_event(),
        retrieved_memory=(chunk,),
    )


def test_typed_historical_memory_is_not_a_current_state_shadow() -> None:
    memory = _chunk(MemoryTemporalScope.HISTORICAL)

    compiled = _compile(memory)

    assert [item.location for item in compiled.memory] == [memory.location]


def test_typed_current_memory_still_yields_to_active_state_on_structural_conflict() -> None:
    memory = _chunk(MemoryTemporalScope.CURRENT)

    compiled = _compile(memory)

    assert compiled.memory == ()


def test_typed_unknown_memory_gets_no_historical_exemption() -> None:
    memory = _chunk(MemoryTemporalScope.UNKNOWN)

    compiled = _compile(memory)

    assert compiled.memory == ()


def test_typed_historical_scope_wins_over_current_sounding_prose() -> None:
    memory = _chunk(
        MemoryTemporalScope.HISTORICAL,
        body="Current residence location is Hokkaido.",
    )

    compiled = _compile(memory)

    assert [item.location for item in compiled.memory] == [memory.location]


def test_unknown_scope_is_not_inferred_historical_from_prose() -> None:
    memory = _chunk(
        MemoryTemporalScope.UNKNOWN,
        body="In 2020, the residence location was Hokkaido; formerly it was home.",
    )

    compiled = _compile(memory)

    assert compiled.memory == ()


def test_historical_exemption_uses_existing_memory_diagnostics_only() -> None:
    historical = _chunk(MemoryTemporalScope.HISTORICAL)

    result = compile_cognitive_input_with_diagnostics(
        identity=Identity("# ReLM\nBe grounded."),
        state=_state(),
        current_event=_current_event(),
        retrieved_memory=(historical,),
    )

    assert [item.location for item in result.cognitive_input.memory] == [
        historical.location
    ]
    assert [diagnostic.layer for diagnostic in result.diagnostics] == [
        "canonical_state",
        "working_context",
        "retrieved_memory",
        "event_evidence",
    ]
    memory_diagnostic = result.diagnostics[2]
    assert memory_diagnostic.selected_count == 1
    assert memory_diagnostic.authority_suppressed_count == 0

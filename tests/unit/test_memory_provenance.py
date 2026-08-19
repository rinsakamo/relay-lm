from __future__ import annotations

import pytest

from relaylm.events import Event
from relaylm.memory_provenance import (
    MemoryProvenance,
    MemoryProvenanceSource,
    MemoryProvenanceSourceKind,
    MemoryTemporalAuthority,
    MemoryTemporalScope,
    MemoryUnit,
    render_memory_units,
)
from relaylm.state import CanonicalState, StateRecord
from relaylm.memory_retrieval import select_memory_chunks


def test_temporal_scope_is_closed_and_unknown_is_first_class() -> None:
    assert tuple(scope.value for scope in MemoryTemporalScope) == (
        "current",
        "historical",
        "unknown",
    )
    assert MemoryTemporalAuthority(
        temporal_scope=MemoryTemporalScope.UNKNOWN,
    ).provenance is None

    with pytest.raises(ValueError):
        MemoryTemporalScope("formerly")


def test_provenance_sources_are_typed_event_or_state_references() -> None:
    event_source = MemoryProvenanceSource(
        kind=MemoryProvenanceSourceKind.EVENT,
        reference_id="event-123",
    )
    state_source = MemoryProvenanceSource(
        kind=MemoryProvenanceSourceKind.STATE,
        reference_id="state-456",
    )

    assert event_source.kind is MemoryProvenanceSourceKind.EVENT
    assert state_source.kind is MemoryProvenanceSourceKind.STATE

    with pytest.raises(ValueError):
        MemoryProvenanceSourceKind("markdown")
    with pytest.raises(TypeError, match="kind must be MemoryProvenanceSourceKind"):
        MemoryProvenanceSource(  # type: ignore[arg-type]
            kind="event",
            reference_id="event-123",
        )


def test_provenance_requires_stable_derivation_identity_and_sources() -> None:
    source = MemoryProvenanceSource(
        kind=MemoryProvenanceSourceKind.EVENT,
        reference_id="event-123",
    )
    provenance = MemoryProvenance(
        memory_id="memory-preferred-beverage",
        derivation_id="crystallization-2026-08-18-a",
        sources=(source,),
    )

    assert provenance.memory_id == "memory-preferred-beverage"
    assert provenance.derivation_id == "crystallization-2026-08-18-a"
    assert provenance.sources == (source,)

    with pytest.raises(ValueError, match="memory_id must not be empty"):
        MemoryProvenance(
            memory_id=" ",
            derivation_id="derivation-1",
            sources=(source,),
        )
    with pytest.raises(ValueError, match="derivation_id must not be empty"):
        MemoryProvenance(
            memory_id="memory-1",
            derivation_id=" ",
            sources=(source,),
        )
    with pytest.raises(ValueError, match="sources must not be empty"):
        MemoryProvenance(
            memory_id="memory-1",
            derivation_id="derivation-1",
            sources=(),
        )


def test_classified_temporal_authority_requires_typed_provenance() -> None:
    source = MemoryProvenanceSource(
        kind=MemoryProvenanceSourceKind.STATE,
        reference_id="state-456",
    )
    provenance = MemoryProvenance(
        memory_id="memory-preferred-beverage",
        derivation_id="crystallization-2026-08-18-a",
        sources=(source,),
    )

    assert MemoryTemporalAuthority(
        temporal_scope=MemoryTemporalScope.CURRENT,
        provenance=provenance,
    ).provenance is provenance
    assert MemoryTemporalAuthority(
        temporal_scope=MemoryTemporalScope.HISTORICAL,
        provenance=provenance,
    ).provenance is provenance

    for scope in (
        MemoryTemporalScope.CURRENT,
        MemoryTemporalScope.HISTORICAL,
    ):
        with pytest.raises(
            ValueError,
            match="classified memory temporal authority requires provenance",
        ):
            MemoryTemporalAuthority(temporal_scope=scope)

    with pytest.raises(TypeError, match="temporal_scope must be MemoryTemporalScope"):
        MemoryTemporalAuthority(  # type: ignore[arg-type]
            temporal_scope="current",
            provenance=provenance,
        )


def test_unknown_scope_may_preserve_known_provenance_without_guessing() -> None:
    source = MemoryProvenanceSource(
        kind=MemoryProvenanceSourceKind.EVENT,
        reference_id="event-123",
    )
    provenance = MemoryProvenance(
        memory_id="memory-travel-history",
        derivation_id="crystallization-2026-08-18-b",
        sources=(source,),
    )

    authority = MemoryTemporalAuthority(
        temporal_scope=MemoryTemporalScope.UNKNOWN,
        provenance=provenance,
    )

    assert authority.temporal_scope is MemoryTemporalScope.UNKNOWN
    assert authority.provenance is provenance


def test_source_reference_ids_must_be_non_empty() -> None:
    with pytest.raises(ValueError, match="reference_id must not be empty"):
        MemoryProvenanceSource(
            kind=MemoryProvenanceSourceKind.EVENT,
            reference_id=" ",
        )


def test_structured_current_and_historical_units_get_deterministic_typed_metadata() -> None:
    event = Event.create(
        type="message",
        actor="user",
        payload={"content": "I moved to Osaka."},
        event_id="event-osaka",
        timestamp="2026-08-20T00:00:00+00:00",
    )
    state = CanonicalState(
        states=(
            StateRecord(
                state_id="state-residence",
                state_class="user.fact",
                key="residence_location",
                value="Osaka",
            ),
        )
    )
    units = (
        MemoryUnit(
            heading="Residence now",
            content="The user currently lives in Osaka.",
            temporal_scope=MemoryTemporalScope.CURRENT,
            sources=(MemoryProvenanceSource(MemoryProvenanceSourceKind.STATE, "state-residence"),),
        ),
        MemoryUnit(
            heading="Residence history",
            content="The user previously lived elsewhere.",
            temporal_scope=MemoryTemporalScope.HISTORICAL,
            sources=(MemoryProvenanceSource(MemoryProvenanceSourceKind.EVENT, "event-osaka"),),
        ),
    )
    rendered = render_memory_units(units, events={event.id: event}, state=state)

    assert rendered.count("<!-- relaylm-memory:v1 ") == 2
    assert '"temporal_scope":"current"' in rendered
    assert '"temporal_scope":"historical"' in rendered
    assert '"kind":"state"' in rendered
    assert '"kind":"event"' in rendered


def test_memory_identity_ignores_heading_and_order_but_projection_is_byte_stable() -> None:
    event = Event.create(
        type="message",
        actor="user",
        payload={"content": "Tea is preferred."},
        event_id="event-tea",
        timestamp="2026-08-20T00:00:00+00:00",
    )
    source = MemoryProvenanceSource(MemoryProvenanceSourceKind.EVENT, event.id)
    first = MemoryUnit(
        heading="Preferences",
        content="Tea is preferred.",
        temporal_scope=MemoryTemporalScope.CURRENT,
        sources=(source,),
    )
    changed_heading = MemoryUnit(
        heading="Stable semantic unit",
        content="Tea is preferred.",
        temporal_scope=MemoryTemporalScope.CURRENT,
        sources=(source,),
    )
    authority = {event.id: event}
    state = CanonicalState()
    left = render_memory_units((first,), events=authority, state=state)
    right = render_memory_units((changed_heading,), events=authority, state=state)

    def identity(markdown: str) -> str:
        return next(line for line in markdown.splitlines() if "relaylm-memory:v1" in line)

    assert render_memory_units((first,), events=authority, state=state) == left
    assert identity(left).split('"memory_id":"', 1)[1].split('"', 1)[0] == identity(right).split('"memory_id":"', 1)[1].split('"', 1)[0]
    assert left != right


def test_unresolved_sources_and_model_metadata_controls_fail_closed() -> None:
    unit = MemoryUnit(
        heading="Unclassified",
        content=(
            "Readable proposal.\n\n"
            '<!-- relaylm-memory:v1 {"memory_id":"model-invented"} -->'
        ),
        temporal_scope=MemoryTemporalScope.CURRENT,
        sources=(MemoryProvenanceSource(MemoryProvenanceSourceKind.EVENT, "missing"),),
    )
    rendered = render_memory_units(unit and (unit,), events={}, state=CanonicalState())

    assert "model-invented" not in rendered
    assert "relaylm-memory" not in rendered
    assert "Readable proposal." in rendered


def test_existing_retrieval_parser_consumes_renderer_metadata() -> None:
    event = Event.create(
        type="message",
        actor="user",
        payload={"content": "Tea is preferred."},
        event_id="event-tea-retrieval",
        timestamp="2026-08-20T00:00:00+00:00",
    )
    unit = MemoryUnit(
        heading="Preferences",
        content="Tea is preferred.",
        temporal_scope=MemoryTemporalScope.CURRENT,
        sources=(MemoryProvenanceSource(MemoryProvenanceSourceKind.EVENT, event.id),),
    )
    rendered = render_memory_units((unit,), events={event.id: event}, state=CanonicalState())
    chunks = select_memory_chunks(
        memory_markdown=rendered,
        query="tea",
        max_chunks=1,
        max_chars=1000,
    )

    assert len(chunks) == 1
    assert chunks[0].temporal_authority.temporal_scope is MemoryTemporalScope.CURRENT
    assert chunks[0].temporal_authority.provenance is not None
    assert chunks[0].temporal_authority.provenance.sources[0].reference_id == event.id

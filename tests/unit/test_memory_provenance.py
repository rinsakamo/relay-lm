from __future__ import annotations

import pytest

from relaylm.memory_provenance import (
    MemoryProvenance,
    MemoryProvenanceSource,
    MemoryProvenanceSourceKind,
    MemoryTemporalAuthority,
    MemoryTemporalScope,
)


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

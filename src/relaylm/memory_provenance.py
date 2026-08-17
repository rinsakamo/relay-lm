from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MemoryTemporalScope(StrEnum):
    """Typed currentness carried by a retrievable MEMORY semantic unit."""

    CURRENT = "current"
    HISTORICAL = "historical"
    UNKNOWN = "unknown"


class MemoryProvenanceSourceKind(StrEnum):
    """Canonical authority roots that may ground crystallized MEMORY lineage."""

    EVENT = "event"
    STATE = "state"


@dataclass(frozen=True, slots=True)
class MemoryProvenanceSource:
    """One typed authority reference used to derive crystallized MEMORY."""

    kind: MemoryProvenanceSourceKind
    reference_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, MemoryProvenanceSourceKind):
            raise TypeError("kind must be MemoryProvenanceSourceKind")
        if not self.reference_id.strip():
            raise ValueError("reference_id must not be empty")


@dataclass(frozen=True, slots=True)
class MemoryProvenance:
    """Stable logical and derivation identity for one MEMORY semantic unit."""

    memory_id: str
    derivation_id: str
    sources: tuple[MemoryProvenanceSource, ...]

    def __post_init__(self) -> None:
        if not self.memory_id.strip():
            raise ValueError("memory_id must not be empty")
        if not self.derivation_id.strip():
            raise ValueError("derivation_id must not be empty")
        if not self.sources:
            raise ValueError("sources must not be empty")
        if not all(isinstance(source, MemoryProvenanceSource) for source in self.sources):
            raise TypeError("sources must contain MemoryProvenanceSource values")


@dataclass(frozen=True, slots=True)
class MemoryTemporalAuthority:
    """Typed temporal authority for crystallized MEMORY.

    Unknown is intentionally first-class. Classified current or historical
    authority is invalid without explicit typed provenance.
    """

    temporal_scope: MemoryTemporalScope
    provenance: MemoryProvenance | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.temporal_scope, MemoryTemporalScope):
            raise TypeError("temporal_scope must be MemoryTemporalScope")
        if self.provenance is not None and not isinstance(
            self.provenance, MemoryProvenance
        ):
            raise TypeError("provenance must be MemoryProvenance when present")
        if (
            self.temporal_scope is not MemoryTemporalScope.UNKNOWN
            and self.provenance is None
        ):
            raise ValueError(
                "classified memory temporal authority requires provenance"
            )

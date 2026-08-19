from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from relaylm.events import Event
    from relaylm.state import CanonicalState


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
        if not isinstance(self.reference_id, str) or not self.reference_id.strip():
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


@dataclass(frozen=True, slots=True)
class MemoryUnit:
    """One model-proposed semantic MEMORY unit.

    Heading and content are presentation text.  Typed sources and temporal
    scope are the only machine-relevant proposal fields; RelayLM derives
    persistent metadata from canonical State/Event authority at projection
    time.
    """

    heading: str
    content: str
    temporal_scope: MemoryTemporalScope
    sources: tuple[MemoryProvenanceSource, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.heading, str) or not self.heading.strip():
            raise ValueError("memory unit heading must not be empty")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("memory unit content must not be empty")
        if not isinstance(self.temporal_scope, MemoryTemporalScope):
            raise TypeError("memory unit temporal_scope must be MemoryTemporalScope")
        if not all(isinstance(source, MemoryProvenanceSource) for source in self.sources):
            raise TypeError("memory unit sources must contain MemoryProvenanceSource values")
        canonical_sources = tuple(
            sorted(self.sources, key=lambda source: (source.kind.value, source.reference_id))
        )
        if len({(source.kind, source.reference_id) for source in canonical_sources}) != len(
            canonical_sources
        ):
            raise ValueError("memory unit sources must not contain duplicates")
        object.__setattr__(self, "sources", canonical_sources)


_MEMORY_METADATA_LINE = re.compile(r"^[ \t]*<!--[ \t]*relaylm-memory:")
_FENCE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")


def _clean_model_markdown(value: str) -> str:
    """Remove model-authored metadata controls while preserving fenced text."""

    lines: list[str] = []
    fence_char: str | None = None
    fence_length = 0
    for line in value.splitlines():
        fence = _FENCE.match(line)
        if fence_char is not None:
            lines.append(line)
            marker = fence.group(1) if fence is not None else ""
            if marker and marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = None
                fence_length = 0
            continue
        if fence is not None:
            marker = fence.group(1)
            fence_char = marker[0]
            fence_length = len(marker)
            lines.append(line)
            continue
        if _MEMORY_METADATA_LINE.match(line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _canonical_identity_basis(
    unit: MemoryUnit,
    *,
    events: Mapping[str, "Event"],
    state: "CanonicalState",
) -> tuple[dict[str, object], tuple[MemoryProvenanceSource, ...]] | None:
    if not unit.sources:
        return None
    valid_sources: list[MemoryProvenanceSource] = []
    state_ids = {record.state_id for record in state.states}
    for source in unit.sources:
        if source.kind is MemoryProvenanceSourceKind.EVENT:
            valid = source.reference_id in events
        else:
            valid = source.reference_id in state_ids
        if not valid:
            return None
        valid_sources.append(source)
    canonical_sources = tuple(
        sorted(valid_sources, key=lambda source: (source.kind.value, source.reference_id))
    )
    basis = {
        "temporal_scope": unit.temporal_scope.value,
        "sources": [
            {"kind": source.kind.value, "reference_id": source.reference_id}
            for source in canonical_sources
        ],
    }
    return basis, canonical_sources


def _identity_digest(basis: Mapping[str, object]) -> str:
    encoded = json.dumps(
        basis,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def render_memory_units(
    units: Sequence[MemoryUnit],
    *,
    events: Mapping[str, "Event"],
    state: "CanonicalState",
) -> str:
    """Project semantic units to deterministic portable MEMORY Markdown.

    A typed identity is emitted only when every supplied source resolves to
    canonical Event or State authority and the identity basis is unique in
    this projection.  Otherwise the unit remains readable but unclassified.
    """

    if not units:
        raise ValueError("memory units must not be empty")
    if not all(isinstance(unit, MemoryUnit) for unit in units):
        raise TypeError("units must contain MemoryUnit values")

    resolved: list[tuple[MemoryUnit, str | None, MemoryProvenance | None]] = []
    basis_counts: dict[str, int] = {}
    for unit in units:
        resolved_basis = _canonical_identity_basis(unit, events=events, state=state)
        if resolved_basis is None:
            resolved.append((unit, None, None))
            continue
        basis, canonical_sources = resolved_basis
        digest = _identity_digest(basis)
        basis_counts[digest] = basis_counts.get(digest, 0) + 1
        resolved.append(
            (
                unit,
                digest,
                MemoryProvenance(
                    memory_id=f"memory-authority-v1-{digest}",
                    derivation_id=f"derivation-authority-v1-{digest}",
                    sources=canonical_sources,
                ),
            )
        )

    def sort_key(item: tuple[MemoryUnit, str | None, MemoryProvenance | None]) -> tuple[object, ...]:
        unit, digest, _ = item
        if digest is not None:
            return (0, digest)
        return (1, " ".join(unit.heading.split()).casefold(), unit.content)

    ordered = sorted(resolved, key=sort_key)
    lines = ["# Memory", ""]
    for unit, digest, provenance in ordered:
        heading = " ".join(unit.heading.split())
        content = _clean_model_markdown(unit.content)
        if not content:
            continue
        lines.extend((f"## {heading}", ""))
        if digest is not None and basis_counts[digest] == 1 and provenance is not None:
            payload = {
                "memory_id": provenance.memory_id,
                "derivation_id": provenance.derivation_id,
                "temporal_scope": unit.temporal_scope.value,
                "sources": [
                    {"kind": source.kind.value, "reference_id": source.reference_id}
                    for source in provenance.sources
                ],
            }
            lines.append(
                "<!-- relaylm-memory:v1 "
                + json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + " -->"
            )
        lines.extend((content, ""))
    return "\n".join(lines).rstrip() + "\n"

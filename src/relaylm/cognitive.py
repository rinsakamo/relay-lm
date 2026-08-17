from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import StateCandidate, StateRecord


@dataclass(frozen=True, slots=True)
class ContextItem:
    """RelayLM-prepared cognitive material with preserved provenance."""

    content: str
    sources: tuple[str, ...] = ()
    actor: str | None = None

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("context content must not be empty")
        if self.actor is not None and not self.actor.strip():
            raise ValueError("context actor must not be empty when present")
        if not all(isinstance(source, str) and source.strip() for source in self.sources):
            raise ValueError("context sources must contain non-empty strings")


@dataclass(frozen=True, slots=True)
class RetrievedMemoryItem:
    """Selected crystallized synthesis with a non-authoritative document locator."""

    content: str
    location: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("memory content must not be empty")
        if not self.location.strip():
            raise ValueError("memory location must not be empty")


@dataclass(frozen=True, slots=True)
class CognitiveInput:
    identity: Identity
    state_classes: Mapping[str, str]
    state: tuple[StateRecord, ...]
    context: tuple[ContextItem, ...]
    input: Event
    memory: tuple[RetrievedMemoryItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CognitiveOutput:
    response: str
    state_candidates: tuple[StateCandidate, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.response.strip():
            raise ValueError("cognitive response must not be empty")


class CognitiveProvider(Protocol):
    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        """Perform exactly one semantic cognitive generation."""
        ...

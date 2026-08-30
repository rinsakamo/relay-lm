from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Protocol

from relaylm.continuity import ContinuityCandidate
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import StateCandidate, StateRecord


class CognitionExecutionMode(StrEnum):
    """Closed RelayLM 1.0 ordinary-turn cognition execution-policy vocabulary."""

    SINGLE_PASS = "single_pass"
    TWO_PASS = "two_pass"
    SHADOW_TWO_PASS = "shadow_two_pass"
    AUTO = "auto"


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
class KnowledgeItem:
    """Package-authored read-only reference material with a document locator."""

    content: str
    location: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("knowledge content must not be empty")
        if not self.location.strip():
            raise ValueError("knowledge location must not be empty")


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
class EventEvidenceItem:
    """Selected persisted occurrence with real Event provenance."""

    event_id: str
    event_type: str
    actor: str
    timestamp: str
    content: str

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event evidence event_id must not be empty")
        if not self.event_type.strip():
            raise ValueError("event evidence event_type must not be empty")
        if not self.actor.strip():
            raise ValueError("event evidence actor must not be empty")
        if not self.timestamp.strip():
            raise ValueError("event evidence timestamp must not be empty")
        if not self.content.strip():
            raise ValueError("event evidence content must not be empty")


@dataclass(frozen=True, slots=True)
class CognitiveInput:
    identity: Identity
    state_classes: Mapping[str, str]
    state: tuple[StateRecord, ...]
    context: tuple[ContextItem, ...]
    input: Event
    knowledge: tuple[KnowledgeItem, ...] = field(default_factory=tuple)
    memory: tuple[RetrievedMemoryItem, ...] = field(default_factory=tuple)
    event_evidence: tuple[EventEvidenceItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CognitiveOutput:
    response: str
    state_candidates: tuple[StateCandidate, ...] = field(default_factory=tuple)
    continuity_candidates: tuple[ContinuityCandidate, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.response.strip():
            raise ValueError("cognitive response must not be empty")


class CognitiveProvider(Protocol):
    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        """Perform one provider generation for the supplied cognitive input."""
        ...

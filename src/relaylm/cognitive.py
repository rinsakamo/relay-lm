from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import StateCandidate, StateRecord


@dataclass(frozen=True, slots=True)
class ContextItem:
    """RelayLM-prepared trusted cognitive material."""

    content: str
    sources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("context content must not be empty")


@dataclass(frozen=True, slots=True)
class CognitiveInput:
    identity: Identity
    state_classes: Mapping[str, str]
    state: tuple[StateRecord, ...]
    context: tuple[ContextItem, ...]
    input: Event


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

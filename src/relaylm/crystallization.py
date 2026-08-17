from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.validation import CandidateDecision, apply_state_candidates


@dataclass(frozen=True, slots=True)
class CrystallizationInput:
    identity: Identity
    state: CanonicalState
    events: tuple[Event, ...]
    prior_memory: str | None = None


@dataclass(frozen=True, slots=True)
class CrystallizationOutput:
    memory_markdown: str
    state_candidates: tuple[StateCandidate, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.memory_markdown.strip():
            raise ValueError("crystallized memory Markdown must not be empty")


class Crystallizer(Protocol):
    async def generate(
        self, crystallization_input: CrystallizationInput
    ) -> CrystallizationOutput:
        """Perform one off-turn crystallization generation."""
        ...


@dataclass(frozen=True, slots=True)
class CrystallizationResult:
    memory_changed: bool
    state: CanonicalState
    decisions: tuple[CandidateDecision, ...]


async def run_crystallization(
    *,
    character: CharacterDirectory,
    crystallizer: Crystallizer,
    max_events: int = 100,
) -> CrystallizationResult:
    """Run one bounded off-turn crystallization pass."""

    if max_events < 0:
        raise ValueError("max_events must not be negative")

    character.load_config()
    identity = character.load_identity()
    state = character.load_state()
    all_events = tuple(character.iter_events())
    recent_events = all_events[-max_events:] if max_events else ()
    prior_memory = character.load_memory_markdown()

    output = await crystallizer.generate(
        CrystallizationInput(
            identity=identity,
            state=state,
            events=recent_events,
            prior_memory=prior_memory,
        )
    )

    event_by_id = {event.id: event for event in all_events}
    validation = apply_state_candidates(
        current_state=state,
        candidates=output.state_candidates,
        events=event_by_id,
    )

    memory_changed = character.save_memory_markdown(output.memory_markdown)
    if validation.changed:
        character.save_state(validation.state)

    return CrystallizationResult(
        memory_changed=memory_changed,
        state=validation.state,
        decisions=validation.decisions,
    )

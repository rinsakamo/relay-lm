from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_provenance import MemoryUnit, render_memory_units
from relaylm.state import CanonicalState, StateCandidate, StateRecord
from relaylm.storage.filesystem import (
    CharacterDirectory,
    StateRevisionConflictError,
)
from relaylm.validation import CandidateDecision, apply_state_candidates


@dataclass(frozen=True, slots=True)
class CrystallizationInput:
    identity: Identity
    state: CanonicalState
    events: tuple[Event, ...]
    prior_memory: str | None = None


@dataclass(frozen=True, slots=True)
class CrystallizationOutput:
    memory_units: tuple[MemoryUnit, ...]
    state_candidates: tuple[StateCandidate, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.memory_units:
            raise ValueError("crystallized memory units must not be empty")
        if not all(isinstance(unit, MemoryUnit) for unit in self.memory_units):
            raise TypeError("memory_units must contain MemoryUnit values")


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


@dataclass(frozen=True, slots=True)
class _CrystallizationStateValidation:
    state: CanonicalState
    decisions: tuple[CandidateDecision, ...]
    changed: bool


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
    origin_state, _ = character.load_state_with_revision()
    all_events = tuple(character.iter_events())
    recent_events = all_events[-max_events:] if max_events else ()
    prior_memory = character.load_memory_markdown()

    output = await crystallizer.generate(
        CrystallizationInput(
            identity=identity,
            state=origin_state,
            events=recent_events,
            prior_memory=prior_memory,
        )
    )

    current_state, current_revision = character.load_state_with_revision()
    event_by_id = {event.id: event for event in all_events}
    validation = _apply_crystallization_state_candidates(
        origin_state=origin_state,
        current_state=current_state,
        candidates=output.state_candidates,
        events=event_by_id,
    )

    input_event_by_id = {event.id: event for event in recent_events}
    memory_markdown = render_memory_units(
        output.memory_units,
        events=input_event_by_id,
        state=validation.state,
    )

    final_revision = current_revision
    if validation.changed:
        character.save_state(
            validation.state,
            expected_revision=current_revision,
        )
        final_state, final_revision = character.load_state_with_revision()
        if final_state != validation.state:
            raise StateRevisionConflictError(
                "state revision changed before MEMORY persistence"
            )

    memory_changed = character.save_memory_markdown(
        memory_markdown,
        expected_state_revision=final_revision,
    )

    return CrystallizationResult(
        memory_changed=memory_changed,
        state=validation.state,
        decisions=validation.decisions,
    )


def _apply_crystallization_state_candidates(
    *,
    origin_state: CanonicalState,
    current_state: CanonicalState,
    candidates: tuple[StateCandidate, ...],
    events: Mapping[str, Event],
) -> _CrystallizationStateValidation:
    state = current_state
    decisions: list[CandidateDecision] = []
    changed = False

    for candidate in candidates:
        if _state_slot_changed_since_generation(
            origin_state=origin_state,
            current_state=current_state,
            candidate=candidate,
        ):
            decisions.append(
                CandidateDecision(
                    candidate=candidate,
                    status="rejected",
                    reason="stale_state_slot",
                )
            )
            continue

        validation = apply_state_candidates(
            current_state=state,
            candidates=(candidate,),
            events=events,
        )
        state = validation.state
        decisions.extend(validation.decisions)
        changed = changed or validation.changed

    return _CrystallizationStateValidation(
        state=state,
        decisions=tuple(decisions),
        changed=changed,
    )


def _state_slot_changed_since_generation(
    *,
    origin_state: CanonicalState,
    current_state: CanonicalState,
    candidate: StateCandidate,
) -> bool:
    return _active_state_record(origin_state, candidate) != _active_state_record(
        current_state,
        candidate,
    )


def _active_state_record(
    state: CanonicalState,
    candidate: StateCandidate,
) -> StateRecord | None:
    for record in state.states:
        if record.status != "active" or record.valid_to is not None:
            continue
        if record.state_class == candidate.state_class and record.key == candidate.key:
            return record
    return None

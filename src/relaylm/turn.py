from __future__ import annotations

from dataclasses import dataclass

from relaylm.cognitive import CognitiveProvider
from relaylm.context import compile_cognitive_input
from relaylm.events import Event
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.validation import CandidateDecision, apply_state_candidates


@dataclass(frozen=True, slots=True)
class TurnResult:
    response: str
    user_event: Event
    assistant_event: Event
    state: CanonicalState
    decisions: tuple[CandidateDecision, ...]


async def run_user_turn(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    content: str,
) -> TurnResult:
    """Run one ordinary turn with one semantic cognitive generation."""

    if not content.strip():
        raise ValueError("user content must not be empty")

    character.load_config()
    identity = character.load_identity()
    state = character.load_state()

    user_event = Event.create(
        type="message",
        actor="user",
        payload={"content": content},
    )
    character.append_event(user_event)

    cognitive_input = compile_cognitive_input(
        identity=identity,
        state=state,
        current_event=user_event,
    )
    output = await provider.generate(cognitive_input)

    assistant_event = Event.create(
        type="message",
        actor="assistant",
        payload={"content": output.response},
    )
    character.append_event(assistant_event)

    event_by_id = {event.id: event for event in character.iter_events()}
    validation = apply_state_candidates(
        current_state=state,
        candidates=output.state_candidates,
        events=event_by_id,
        required_source_ids=frozenset({user_event.id}),
    )
    if validation.changed:
        character.save_state(validation.state)

    return TurnResult(
        response=output.response,
        user_event=user_event,
        assistant_event=assistant_event,
        state=validation.state,
        decisions=validation.decisions,
    )

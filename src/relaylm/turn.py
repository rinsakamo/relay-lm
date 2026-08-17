from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from relaylm.cognitive import CognitiveInput, CognitiveOutput, CognitiveProvider
from relaylm.context import compile_cognitive_input
from relaylm.event_retrieval import (
    EventRetrievalDiagnostics,
    select_event_evidence,
    select_event_evidence_with_diagnostics,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.memory_retrieval import (
    MemoryRetrievalDiagnostics,
    select_memory_chunks,
    select_memory_chunks_with_diagnostics,
)
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.validation import CandidateDecision, apply_state_candidates


@dataclass(frozen=True, slots=True)
class MemoryRetrievalBudget:
    """Explicit opt-in budget for ordinary-turn crystallized-memory retrieval."""

    max_chunks: int
    max_chars: int

    def __post_init__(self) -> None:
        if self.max_chunks < 0:
            raise ValueError("memory max_chunks must not be negative")
        if self.max_chars < 0:
            raise ValueError("memory max_chars must not be negative")


@dataclass(frozen=True, slots=True)
class EventRetrievalBudget:
    """Explicit opt-in budget for ordinary-turn targeted Event retrieval."""

    max_events: int
    max_chars: int

    def __post_init__(self) -> None:
        if self.max_events < 0:
            raise ValueError("event max_events must not be negative")
        if self.max_chars < 0:
            raise ValueError("event max_chars must not be negative")


@dataclass(frozen=True, slots=True)
class TurnResult:
    response: str
    user_event: Event
    assistant_event: Event
    state: CanonicalState
    decisions: tuple[CandidateDecision, ...]


@dataclass(frozen=True, slots=True)
class MemoryTurnRetrievalDiagnostics:
    """Configured MEMORY budget paired with selector-owned aggregate observations."""

    budget: MemoryRetrievalBudget
    selector: MemoryRetrievalDiagnostics


@dataclass(frozen=True, slots=True)
class EventTurnRetrievalDiagnostics:
    """Configured Event budget paired with selector-owned aggregate observations."""

    budget: EventRetrievalBudget
    selector: EventRetrievalDiagnostics


@dataclass(frozen=True, slots=True)
class TurnRetrievalDiagnostics:
    """Content-free retrieval diagnostics for one explicit ordinary-turn observation."""

    memory: MemoryTurnRetrievalDiagnostics | None
    event: EventTurnRetrievalDiagnostics | None


@dataclass(frozen=True, slots=True)
class TurnResultWithRetrievalDiagnostics:
    """Ordinary turn result plus explicitly requested retrieval diagnostics."""

    turn: TurnResult
    retrieval: TurnRetrievalDiagnostics


async def run_user_turn(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    content: str,
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
) -> TurnResult:
    """Run one ordinary turn with one semantic cognitive generation."""

    user_event, state, cognitive_input, _diagnostics = _prepare_user_turn(
        character=character,
        content=content,
        memory_budget=memory_budget,
        event_budget=event_budget,
        include_retrieval_diagnostics=False,
    )
    output = await provider.generate(cognitive_input)
    return _commit_cognitive_output(
        character=character,
        state=state,
        user_event=user_event,
        output=output,
    )


async def run_user_turn_with_retrieval_diagnostics(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    content: str,
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
) -> TurnResultWithRetrievalDiagnostics:
    """Run one ordinary turn and explicitly return content-free retrieval diagnostics."""

    user_event, state, cognitive_input, diagnostics = _prepare_user_turn(
        character=character,
        content=content,
        memory_budget=memory_budget,
        event_budget=event_budget,
        include_retrieval_diagnostics=True,
    )
    output = await provider.generate(cognitive_input)
    turn = _commit_cognitive_output(
        character=character,
        state=state,
        user_event=user_event,
        output=output,
    )
    assert diagnostics is not None
    return TurnResultWithRetrievalDiagnostics(turn=turn, retrieval=diagnostics)


async def run_user_turn_streaming(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    content: str,
    emit_response_delta: Callable[[str], Awaitable[None]],
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
) -> TurnResult:
    """Run one streamed ordinary turn without committing before provider completion."""

    stream_generate = getattr(provider, "stream_generate", None)
    if stream_generate is None:
        raise TypeError("provider does not support cognitive streaming")

    user_event, state, cognitive_input, _diagnostics = _prepare_user_turn(
        character=character,
        content=content,
        memory_budget=memory_budget,
        event_budget=event_budget,
        include_retrieval_diagnostics=False,
    )
    output = await stream_generate(cognitive_input, emit_response_delta)
    return _commit_cognitive_output(
        character=character,
        state=state,
        user_event=user_event,
        output=output,
    )


async def run_user_turn_streaming_with_retrieval_diagnostics(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    content: str,
    emit_response_delta: Callable[[str], Awaitable[None]],
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
) -> TurnResultWithRetrievalDiagnostics:
    """Run one streamed ordinary turn and explicitly return retrieval diagnostics."""

    stream_generate = getattr(provider, "stream_generate", None)
    if stream_generate is None:
        raise TypeError("provider does not support cognitive streaming")

    user_event, state, cognitive_input, diagnostics = _prepare_user_turn(
        character=character,
        content=content,
        memory_budget=memory_budget,
        event_budget=event_budget,
        include_retrieval_diagnostics=True,
    )
    output = await stream_generate(cognitive_input, emit_response_delta)
    turn = _commit_cognitive_output(
        character=character,
        state=state,
        user_event=user_event,
        output=output,
    )
    assert diagnostics is not None
    return TurnResultWithRetrievalDiagnostics(turn=turn, retrieval=diagnostics)


def _prepare_user_turn(
    *,
    character: CharacterDirectory,
    content: str,
    memory_budget: MemoryRetrievalBudget | None,
    event_budget: EventRetrievalBudget | None,
    include_retrieval_diagnostics: bool,
) -> tuple[Event, CanonicalState, CognitiveInput, TurnRetrievalDiagnostics | None]:
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

    cognitive_input, diagnostics = _compile_turn_cognitive_input(
        character=character,
        identity=identity,
        state=state,
        user_event=user_event,
        memory_budget=memory_budget,
        event_budget=event_budget,
        include_retrieval_diagnostics=include_retrieval_diagnostics,
    )
    return user_event, state, cognitive_input, diagnostics


def _compile_turn_cognitive_input(
    *,
    character: CharacterDirectory,
    identity: Identity,
    state: CanonicalState,
    user_event: Event,
    memory_budget: MemoryRetrievalBudget | None,
    event_budget: EventRetrievalBudget | None,
    include_retrieval_diagnostics: bool = False,
) -> tuple[CognitiveInput, TurnRetrievalDiagnostics | None]:
    retrieved_memory = ()
    memory_diagnostics = None
    if memory_budget is not None:
        memory_markdown = character.load_memory_markdown()
        if include_retrieval_diagnostics:
            memory_result = select_memory_chunks_with_diagnostics(
                memory_markdown=memory_markdown,
                query=user_event.payload["content"],
                max_chunks=memory_budget.max_chunks,
                max_chars=memory_budget.max_chars,
            )
            retrieved_memory = memory_result.chunks
            memory_diagnostics = MemoryTurnRetrievalDiagnostics(
                budget=memory_budget,
                selector=memory_result.diagnostics,
            )
        else:
            retrieved_memory = select_memory_chunks(
                memory_markdown=memory_markdown,
                query=user_event.payload["content"],
                max_chunks=memory_budget.max_chunks,
                max_chars=memory_budget.max_chars,
            )

    event_evidence = ()
    event_diagnostics = None
    if event_budget is None:
        recent_events = character.iter_events()
    else:
        recent_events = tuple(character.iter_events())
        if include_retrieval_diagnostics:
            event_result = select_event_evidence_with_diagnostics(
                events=recent_events,
                query=user_event.payload["content"],
                max_events=event_budget.max_events,
                max_chars=event_budget.max_chars,
                exclude_event_ids=(user_event.id,),
            )
            event_evidence = event_result.events
            event_diagnostics = EventTurnRetrievalDiagnostics(
                budget=event_budget,
                selector=event_result.diagnostics,
            )
        else:
            event_evidence = select_event_evidence(
                events=recent_events,
                query=user_event.payload["content"],
                max_events=event_budget.max_events,
                max_chars=event_budget.max_chars,
                exclude_event_ids=(user_event.id,),
            )

    cognitive_input = compile_cognitive_input(
        identity=identity,
        state=state,
        current_event=user_event,
        recent_events=recent_events,
        retrieved_memory=retrieved_memory,
        event_evidence=event_evidence,
    )
    if not include_retrieval_diagnostics:
        return cognitive_input, None
    return cognitive_input, TurnRetrievalDiagnostics(
        memory=memory_diagnostics,
        event=event_diagnostics,
    )


def _commit_cognitive_output(
    *,
    character: CharacterDirectory,
    state: CanonicalState,
    user_event: Event,
    output: CognitiveOutput,
) -> TurnResult:
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
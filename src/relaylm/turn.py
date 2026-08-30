from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace

from relaylm.budget import BudgetPlan
from relaylm.budget_controls import owner_controls_for_budget_plan
from relaylm.budget_diagnostics import (
    CognitiveBudgetDiagnostics,
    budget_failure_with_diagnostics,
    diagnostics_for_budget_result,
)
from relaylm.budget_enforcement import (
    BudgetEnforcementResult,
    CognitiveBudgetExceeded,
    enforce_total_cognitive_budget,
)
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import (
    CognitiveInput,
    CognitiveOutput,
    CognitiveProvider,
    KnowledgeItem,
)
from relaylm.cognition_execution import CognitionPassRequest
from relaylm.context import compile_cognitive_input
from relaylm.continuity import ContinuityContext
from relaylm.continuity_validation import (
    ContinuityValidationResult,
    apply_continuity_candidates,
)
from relaylm.event_retrieval import (
    EventRetrievalDiagnostics,
    select_event_evidence,
    select_event_evidence_with_diagnostics,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.knowledge import select_knowledge_items
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


@dataclass(slots=True)
class ContinuityRuntime:
    """Process-local holder that orchestrates already-owned Continuity semantics."""

    context: ContinuityContext
    lifetime_revisions: int

    def __post_init__(self) -> None:
        if isinstance(self.lifetime_revisions, bool) or not isinstance(
            self.lifetime_revisions, int
        ):
            raise TypeError("lifetime_revisions must be an integer")
        if self.lifetime_revisions <= 0:
            raise ValueError("lifetime_revisions must be positive")


@dataclass(frozen=True, slots=True)
class TurnResult:
    response: str
    user_event: Event
    assistant_event: Event
    state: CanonicalState
    decisions: tuple[CandidateDecision, ...]
    continuity: ContinuityValidationResult | None = None


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
class RetrievalAggregateDiagnostics:
    """Content-free retrieval-only totals derived from configured layers."""

    enabled_layer_count: int
    configured_character_budget_total: int
    selected_character_usage_total: int
    character_budget_pressured_layer_count: int
    any_character_budget_pressure: bool


@dataclass(frozen=True, slots=True)
class TurnRetrievalDiagnostics:
    """Content-free retrieval diagnostics for one explicit ordinary-turn observation."""

    memory: MemoryTurnRetrievalDiagnostics | None
    event: EventTurnRetrievalDiagnostics | None
    aggregate: RetrievalAggregateDiagnostics


@dataclass(frozen=True, slots=True)
class TurnResultWithRetrievalDiagnostics:
    """Ordinary turn result plus explicitly requested retrieval diagnostics."""

    turn: TurnResult
    retrieval: TurnRetrievalDiagnostics


@dataclass(frozen=True, slots=True)
class TurnResultWithCognitiveBudgetDiagnostics:
    """Ordinary turn result plus explicitly requested total-budget diagnostics."""

    turn: TurnResult
    cognitive_budget: CognitiveBudgetDiagnostics


@dataclass(slots=True)
class _StreamingResponseDelivery:
    emit_response_delta: Callable[[str], Awaitable[None]]
    delivered: str = ""

    async def emit(self, text: str) -> None:
        self.delivered += text
        await self.emit_response_delta(text)

    async def reconcile(self, final_response: str) -> None:
        if not final_response.startswith(self.delivered):
            raise RuntimeError(
                "streamed response does not match final cognitive response"
            )
        remaining = final_response[len(self.delivered) :]
        if remaining:
            await self.emit(remaining)


async def run_user_turn(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    content: str,
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
    continuity_runtime: ContinuityRuntime | None = None,
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
    pass_request: CognitionPassRequest | None = None,
) -> TurnResult:
    """Run one ordinary turn with one semantic cognitive generation."""

    if pass_request is not None and not isinstance(pass_request, CognitionPassRequest):
        raise TypeError("pass_request must be CognitionPassRequest or None")
    if cognitive_budget is None:
        user_event, state, cognitive_input, _diagnostics = _prepare_user_turn(
            character=character,
            content=content,
            memory_budget=memory_budget,
            event_budget=event_budget,
            continuity_runtime=continuity_runtime,
            include_retrieval_diagnostics=False,
        )
    else:
        _reject_overlapping_budget_configuration(
            memory_budget=memory_budget,
            event_budget=event_budget,
        )
        user_event, state, cognitive_input = _prepare_budgeted_user_turn(
            character=character,
            content=content,
            continuity_runtime=continuity_runtime,
            cognitive_budget=cognitive_budget,
        )
    if pass_request is None:
        output = await provider.generate(cognitive_input)
    else:
        output = await provider.generate(cognitive_input, pass_request=pass_request)
    return _commit_cognitive_output(
        character=character,
        state=state,
        user_event=user_event,
        output=output,
        continuity_runtime=continuity_runtime,
    )


async def run_user_turn_with_retrieval_diagnostics(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    content: str,
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
    continuity_runtime: ContinuityRuntime | None = None,
) -> TurnResultWithRetrievalDiagnostics:
    """Run one ordinary turn and explicitly return content-free retrieval diagnostics."""

    user_event, state, cognitive_input, diagnostics = _prepare_user_turn(
        character=character,
        content=content,
        memory_budget=memory_budget,
        event_budget=event_budget,
        continuity_runtime=continuity_runtime,
        include_retrieval_diagnostics=True,
    )
    output = await provider.generate(cognitive_input)
    turn = _commit_cognitive_output(
        character=character,
        state=state,
        user_event=user_event,
        output=output,
        continuity_runtime=continuity_runtime,
    )
    assert diagnostics is not None
    return TurnResultWithRetrievalDiagnostics(turn=turn, retrieval=diagnostics)


async def run_user_turn_with_cognitive_budget_diagnostics(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    content: str,
    cognitive_budget: CognitiveBudgetRuntimeConfig,
    continuity_runtime: ContinuityRuntime | None = None,
) -> TurnResultWithCognitiveBudgetDiagnostics:
    """Run one budget-enforced turn and explicitly return content-free diagnostics."""

    try:
        user_event, state, enforcement = _enforce_budgeted_user_turn(
            character=character,
            content=content,
            continuity_runtime=continuity_runtime,
            cognitive_budget=cognitive_budget,
        )
    except CognitiveBudgetExceeded as failure:
        raise budget_failure_with_diagnostics(
            config=cognitive_budget.total,
            policy=cognitive_budget.policy,
            failure=failure,
        ) from failure

    diagnostics = diagnostics_for_budget_result(
        config=cognitive_budget.total,
        policy=cognitive_budget.policy,
        result=enforcement,
    )
    output = await provider.generate(enforcement.cognitive_input)
    turn = _commit_cognitive_output(
        character=character,
        state=state,
        user_event=user_event,
        output=output,
        continuity_runtime=continuity_runtime,
    )
    return TurnResultWithCognitiveBudgetDiagnostics(
        turn=turn,
        cognitive_budget=diagnostics,
    )


async def run_user_turn_streaming(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    content: str,
    emit_response_delta: Callable[[str], Awaitable[None]],
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
    continuity_runtime: ContinuityRuntime | None = None,
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
) -> TurnResult:
    """Run one streamed ordinary turn without committing before provider completion."""

    if not content.strip():
        raise ValueError("user content must not be empty")

    stream_generate = getattr(provider, "stream_generate", None)
    if not callable(stream_generate):
        raise TypeError("provider does not support cognitive streaming")

    if cognitive_budget is None:
        user_event, state, cognitive_input, _diagnostics = _prepare_user_turn(
            character=character,
            content=content,
            memory_budget=memory_budget,
            event_budget=event_budget,
            continuity_runtime=continuity_runtime,
            include_retrieval_diagnostics=False,
        )
    else:
        _reject_overlapping_budget_configuration(
            memory_budget=memory_budget,
            event_budget=event_budget,
        )
        user_event, state, cognitive_input = _prepare_budgeted_user_turn(
            character=character,
            content=content,
            continuity_runtime=continuity_runtime,
            cognitive_budget=cognitive_budget,
        )
    delivery = _StreamingResponseDelivery(emit_response_delta)
    output = await stream_generate(cognitive_input, delivery.emit)
    if isinstance(output, CognitiveOutput):
        await delivery.reconcile(output.response)
    return _commit_cognitive_output(
        character=character,
        state=state,
        user_event=user_event,
        output=output,
        continuity_runtime=continuity_runtime,
    )


async def run_user_turn_streaming_with_retrieval_diagnostics(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    content: str,
    emit_response_delta: Callable[[str], Awaitable[None]],
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
    continuity_runtime: ContinuityRuntime | None = None,
) -> TurnResultWithRetrievalDiagnostics:
    """Run one streamed ordinary turn and explicitly return retrieval diagnostics."""

    if not content.strip():
        raise ValueError("user content must not be empty")

    stream_generate = getattr(provider, "stream_generate", None)
    if not callable(stream_generate):
        raise TypeError("provider does not support cognitive streaming")

    user_event, state, cognitive_input, diagnostics = _prepare_user_turn(
        character=character,
        content=content,
        memory_budget=memory_budget,
        event_budget=event_budget,
        continuity_runtime=continuity_runtime,
        include_retrieval_diagnostics=True,
    )
    delivery = _StreamingResponseDelivery(emit_response_delta)
    output = await stream_generate(cognitive_input, delivery.emit)
    if isinstance(output, CognitiveOutput):
        await delivery.reconcile(output.response)
    turn = _commit_cognitive_output(
        character=character,
        state=state,
        user_event=user_event,
        output=output,
        continuity_runtime=continuity_runtime,
    )
    assert diagnostics is not None
    return TurnResultWithRetrievalDiagnostics(turn=turn, retrieval=diagnostics)


async def run_user_turn_streaming_with_cognitive_budget_diagnostics(
    *,
    character: CharacterDirectory,
    provider: CognitiveProvider,
    content: str,
    emit_response_delta: Callable[[str], Awaitable[None]],
    cognitive_budget: CognitiveBudgetRuntimeConfig,
    continuity_runtime: ContinuityRuntime | None = None,
) -> TurnResultWithCognitiveBudgetDiagnostics:
    """Run one streamed budget-enforced turn and return content-free diagnostics."""

    if not content.strip():
        raise ValueError("user content must not be empty")

    stream_generate = getattr(provider, "stream_generate", None)
    if not callable(stream_generate):
        raise TypeError("provider does not support cognitive streaming")

    try:
        user_event, state, enforcement = _enforce_budgeted_user_turn(
            character=character,
            content=content,
            continuity_runtime=continuity_runtime,
            cognitive_budget=cognitive_budget,
        )
    except CognitiveBudgetExceeded as failure:
        raise budget_failure_with_diagnostics(
            config=cognitive_budget.total,
            policy=cognitive_budget.policy,
            failure=failure,
        ) from failure

    diagnostics = diagnostics_for_budget_result(
        config=cognitive_budget.total,
        policy=cognitive_budget.policy,
        result=enforcement,
    )
    delivery = _StreamingResponseDelivery(emit_response_delta)
    output = await stream_generate(enforcement.cognitive_input, delivery.emit)
    if isinstance(output, CognitiveOutput):
        await delivery.reconcile(output.response)
    turn = _commit_cognitive_output(
        character=character,
        state=state,
        user_event=user_event,
        output=output,
        continuity_runtime=continuity_runtime,
    )
    return TurnResultWithCognitiveBudgetDiagnostics(
        turn=turn,
        cognitive_budget=diagnostics,
    )


def _reject_overlapping_budget_configuration(
    *,
    memory_budget: MemoryRetrievalBudget | None,
    event_budget: EventRetrievalBudget | None,
) -> None:
    if memory_budget is not None or event_budget is not None:
        raise ValueError(
            "cognitive_budget cannot be combined with legacy memory_budget/event_budget"
        )


def _prepare_budgeted_user_turn(
    *,
    character: CharacterDirectory,
    content: str,
    continuity_runtime: ContinuityRuntime | None,
    cognitive_budget: CognitiveBudgetRuntimeConfig,
) -> tuple[Event, CanonicalState, CognitiveInput]:
    user_event, state, enforcement = _enforce_budgeted_user_turn(
        character=character,
        content=content,
        continuity_runtime=continuity_runtime,
        cognitive_budget=cognitive_budget,
    )
    return user_event, state, enforcement.cognitive_input


def _enforce_budgeted_user_turn(
    *,
    character: CharacterDirectory,
    content: str,
    continuity_runtime: ContinuityRuntime | None,
    cognitive_budget: CognitiveBudgetRuntimeConfig,
) -> tuple[Event, CanonicalState, BudgetEnforcementResult]:
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

    continuity_context = (
        continuity_runtime.context if continuity_runtime is not None else None
    )
    enforcement = enforce_total_cognitive_budget(
        config=cognitive_budget.total,
        policy=cognitive_budget.policy,
        compile_protected_cognitive_input=lambda: _compile_protected_turn_cognitive_input(
            identity=identity,
            state=state,
            user_event=user_event,
        ),
        compile_cognitive_input=lambda plan: _compile_budget_plan_cognitive_input(
            character=character,
            identity=identity,
            state=state,
            user_event=user_event,
            continuity_context=continuity_context,
            plan=plan,
        ),
        token_counter=cognitive_budget.token_counter,
    )
    return user_event, state, enforcement


def _compile_protected_turn_cognitive_input(
    *,
    identity: Identity,
    state: CanonicalState,
    user_event: Event,
) -> CognitiveInput:
    """Project only mandatory framing, Identity, and Current Event for fit probing."""

    return compile_cognitive_input(
        identity=identity,
        state=state,
        current_event=user_event,
        recent_events=(),
        continuity_context=None,
        retrieved_memory=(),
        event_evidence=(),
        max_working_context_events=0,
        max_working_context_chars=0,
        max_state_records=0,
    )


def _compile_budget_plan_cognitive_input(
    *,
    character: CharacterDirectory,
    identity: Identity,
    state: CanonicalState,
    user_event: Event,
    continuity_context: ContinuityContext | None,
    plan: BudgetPlan,
) -> CognitiveInput:
    """Apply Budget-owned room limits through existing semantic-owner controls."""

    controls = owner_controls_for_budget_plan(plan)

    package_knowledge = ()
    if controls.knowledge.max_items > 0 and controls.knowledge.max_chars > 0:
        package_knowledge = select_knowledge_items(
            _load_package_knowledge(character),
            max_items=controls.knowledge.max_items,
            max_chars=controls.knowledge.max_chars,
        )

    retrieved_memory = ()
    if (
        controls.retrieval.memory_max_chunks > 0
        and controls.retrieval.memory_max_chars > 0
    ):
        retrieved_memory = select_memory_chunks(
            memory_markdown=character.load_memory_markdown(),
            query=user_event.payload["content"],
            max_chunks=controls.retrieval.memory_max_chunks,
            max_chars=controls.retrieval.memory_max_chars,
        )

    event_evidence = ()
    if (
        controls.retrieval.event_max_events > 0
        and controls.retrieval.event_max_chars > 0
    ):
        event_evidence = select_event_evidence(
            events=character.event_retrieval_source(),
            query=user_event.payload["content"],
            max_events=controls.retrieval.event_max_events,
            max_chars=controls.retrieval.event_max_chars,
            exclude_event_ids=(user_event.id,),
        )

    cognitive_input = compile_cognitive_input(
        identity=identity,
        state=state,
        current_event=user_event,
        recent_events=character.iter_events(),
        continuity_context=continuity_context,
        retrieved_memory=retrieved_memory,
        event_evidence=event_evidence,
        max_working_context_events=(
            controls.context_compiler.max_working_context_events
        ),
        max_working_context_chars=controls.context_compiler.max_working_context_chars,
        max_state_records=controls.context_compiler.max_state_records,
    )
    return replace(cognitive_input, knowledge=package_knowledge)


def _prepare_user_turn(
    *,
    character: CharacterDirectory,
    content: str,
    memory_budget: MemoryRetrievalBudget | None,
    event_budget: EventRetrievalBudget | None,
    continuity_runtime: ContinuityRuntime | None,
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

    continuity_context = (
        continuity_runtime.context if continuity_runtime is not None else None
    )
    cognitive_input, diagnostics = _compile_turn_cognitive_input(
        character=character,
        identity=identity,
        state=state,
        user_event=user_event,
        memory_budget=memory_budget,
        event_budget=event_budget,
        continuity_context=continuity_context,
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
    continuity_context: ContinuityContext | None,
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
    recent_events = character.iter_events()
    event_diagnostics = None
    if event_budget is not None:
        event_source = character.event_retrieval_source()
        if include_retrieval_diagnostics:
            event_result = select_event_evidence_with_diagnostics(
                events=event_source,
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
                events=event_source,
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
        continuity_context=continuity_context,
        retrieved_memory=retrieved_memory,
        event_evidence=event_evidence,
    )
    cognitive_input = replace(
        cognitive_input,
        knowledge=_load_package_knowledge(character),
    )
    if not include_retrieval_diagnostics:
        return cognitive_input, None
    return cognitive_input, TurnRetrievalDiagnostics(
        memory=memory_diagnostics,
        event=event_diagnostics,
        aggregate=_aggregate_retrieval_diagnostics(
            memory=memory_diagnostics,
            event=event_diagnostics,
        ),
    )


def _load_package_knowledge(
    character: CharacterDirectory,
) -> tuple[KnowledgeItem, ...]:
    loader = getattr(character, "load_knowledge", None)
    if loader is None:
        return ()
    if not callable(loader):
        raise TypeError("package load_knowledge must be callable")
    items = loader()
    if not isinstance(items, tuple) or not all(
        isinstance(item, KnowledgeItem) for item in items
    ):
        raise TypeError("package load_knowledge must return KnowledgeItem values")
    return items


def _aggregate_retrieval_diagnostics(
    *,
    memory: MemoryTurnRetrievalDiagnostics | None,
    event: EventTurnRetrievalDiagnostics | None,
) -> RetrievalAggregateDiagnostics:
    layers = tuple(layer for layer in (memory, event) if layer is not None)
    pressure_flags = tuple(
        layer.selector.character_budget_pressure for layer in layers
    )
    return RetrievalAggregateDiagnostics(
        enabled_layer_count=len(layers),
        configured_character_budget_total=sum(layer.budget.max_chars for layer in layers),
        selected_character_usage_total=sum(
            layer.selector.character_budget_used for layer in layers
        ),
        character_budget_pressured_layer_count=sum(pressure_flags),
        any_character_budget_pressure=any(pressure_flags),
    )


def _commit_cognitive_output(
    *,
    character: CharacterDirectory,
    state: CanonicalState,
    user_event: Event,
    output: CognitiveOutput,
    continuity_runtime: ContinuityRuntime | None,
) -> TurnResult:
    if not isinstance(output, CognitiveOutput):
        raise TypeError("provider generation must return CognitiveOutput")
    if output.continuity_candidates and continuity_runtime is None:
        raise RuntimeError("continuity candidates require an explicit runtime")

    assistant_event = Event.create(
        type="message",
        actor="assistant",
        payload={"content": output.response},
    )
    character.append_event(assistant_event)

    event_by_id = {event.id: event for event in character.iter_events()}
    state_validation = apply_state_candidates(
        current_state=state,
        candidates=output.state_candidates,
        events=event_by_id,
        required_source_ids=frozenset({user_event.id}),
    )

    continuity_validation = None
    if continuity_runtime is not None:
        continuity_validation = apply_continuity_candidates(
            current_context=continuity_runtime.context,
            candidates=output.continuity_candidates,
            events=event_by_id,
            required_source_ids=frozenset({user_event.id}),
            lifetime_revisions=continuity_runtime.lifetime_revisions,
        )

    if state_validation.changed:
        character.save_state(state_validation.state)
    if continuity_validation is not None:
        continuity_runtime.context = continuity_validation.context

    return TurnResult(
        response=output.response,
        user_event=user_event,
        assistant_event=assistant_event,
        state=state_validation.state,
        decisions=state_validation.decisions,
        continuity=continuity_validation,
    )
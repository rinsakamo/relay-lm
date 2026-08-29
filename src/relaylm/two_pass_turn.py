from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum

from relaylm.budget_enforcement import evaluate_serialized_input_fit
from relaylm.budget_runtime import (
    CognitiveBudgetRuntimeConfig,
    TwoPassCognitiveBudgetRuntimeConfig,
    TwoPassSerializedInputTokenCounter,
)
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionCompletionMetadata,
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
    TwoPassCognitiveProvider,
)
from relaylm.continuity import ContinuityContext
from relaylm.continuity_validation import (
    ContinuityValidationResult,
    advance_continuity_lifecycle,
    apply_continuity_candidates_at_current_revision,
)
from relaylm.events import Event
from relaylm.state import CanonicalState
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    ContinuityRuntime,
    EventRetrievalBudget,
    MemoryRetrievalBudget,
    _prepare_budgeted_user_turn,
    _prepare_user_turn,
    _reject_overlapping_budget_configuration,
    _StreamingResponseDelivery,
)
from relaylm.validation import CandidateDecision, apply_state_candidates


class TwoPassExtractionStatus(StrEnum):
    """Content-free terminal status for one turn-bound Pass 2 attempt."""

    COMMITTED = "committed"
    STALE = "stale"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TwoPassExtractionResult:
    """Deterministic Pass 2 disposition after the visible response already exists."""

    status: TwoPassExtractionStatus
    originating_event_id: str
    state: CanonicalState
    decisions: tuple[CandidateDecision, ...] = ()
    continuity: ContinuityValidationResult | None = None
    failure_reason: str | None = None
    completion: CognitionCompletionMetadata | None = None

    def __post_init__(self) -> None:
        if not self.originating_event_id.strip():
            raise ValueError("originating_event_id must not be empty")
        if self.status is TwoPassExtractionStatus.FAILED:
            if self.failure_reason is None or not self.failure_reason.strip():
                raise ValueError("failed extraction requires failure_reason")
        elif self.failure_reason is not None:
            raise ValueError("non-failed extraction must not carry failure_reason")
        if self.completion is not None and not isinstance(
            self.completion, CognitionCompletionMetadata
        ):
            raise TypeError("completion must be CognitionCompletionMetadata or None")


@dataclass(frozen=True, slots=True)
class TwoPassTurnResult:
    """Response-first ordinary-turn result plus its independently completing Pass 2."""

    response: str
    user_event: Event
    assistant_event: Event
    extraction: asyncio.Task[TwoPassExtractionResult]
    conversation_completion: CognitionCompletionMetadata = field(
        default_factory=CognitionCompletionMetadata
    )


@dataclass(slots=True)
class CognitionExecutionRuntime:
    """Process-local ordering holder for response-first two-pass execution.

    A newly reserved turn makes all older extraction work semantically stale. Core
    1.0 also cancels and joins those obsolete local Pass 2 tasks before the newer
    turn begins provider generation, so response-first execution does not silently
    accumulate overlapping stale provider requests.
    """

    revision: int = 0
    latest_turn_event_id: str | None = None
    _conversation_lock: asyncio.Lock = field(
        default_factory=asyncio.Lock,
        init=False,
        repr=False,
    )
    _authority_lock: asyncio.Lock = field(
        default_factory=asyncio.Lock,
        init=False,
        repr=False,
    )
    _pending_extractions: set[asyncio.Task[TwoPassExtractionResult]] = field(
        default_factory=set,
        init=False,
        repr=False,
    )

    def _reserve_turn(self) -> int:
        """Invalidate older extraction before preparing the newly arrived turn."""

        self.revision += 1
        self.latest_turn_event_id = None
        return self.revision

    async def _cancel_superseded_extractions(self) -> None:
        """Cancel and join obsolete Pass 2 tasks before newer provider work starts."""

        pending = tuple(task for task in self._pending_extractions if not task.done())
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    def _bind_turn(self, *, revision: int, event_id: str) -> None:
        if revision != self.revision:
            raise RuntimeError("cannot bind a superseded cognition execution revision")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("turn event_id must not be empty")
        self.latest_turn_event_id = event_id

    def _is_current(self, *, revision: int, event_id: str) -> bool:
        return self.revision == revision and self.latest_turn_event_id == event_id

    def _track(self, task: asyncio.Task[TwoPassExtractionResult]) -> None:
        self._pending_extractions.add(task)
        task.add_done_callback(self._pending_extractions.discard)

    @property
    def pending_extraction_count(self) -> int:
        return len(self._pending_extractions)


@dataclass(frozen=True, slots=True)
class _ConversationBudgetTokenCounter:
    """Adapt the exact Pass 1 serializer to the existing #1387 enforcement loop."""

    token_counter: TwoPassSerializedInputTokenCounter
    pass_request: CognitionPassRequest | None

    def count_serialized_input(self, cognitive_input: CognitiveInput):
        return self.token_counter.count_conversation_input(
            cognitive_input,
            pass_request=self.pass_request,
        )


async def run_user_turn_two_pass(
    *,
    character: CharacterDirectory,
    provider: TwoPassCognitiveProvider,
    content: str,
    execution_runtime: CognitionExecutionRuntime,
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
    continuity_runtime: ContinuityRuntime | None = None,
    cognitive_budget: TwoPassCognitiveBudgetRuntimeConfig | None = None,
    pass1_request: CognitionPassRequest | None = None,
    pass2_request: CognitionPassRequest | None = None,
) -> TwoPassTurnResult:
    """Complete Pass 1, then background the turn-bound Pass 2 proposal path."""

    generate_conversation = _require_two_pass_provider(provider, streaming=False)
    _require_execution_runtime(execution_runtime)
    _require_two_pass_budget(cognitive_budget)
    if pass1_request is not None and not isinstance(pass1_request, CognitionPassRequest):
        raise TypeError("pass1_request must be CognitionPassRequest or None")
    if pass2_request is not None and not isinstance(pass2_request, CognitionPassRequest):
        raise TypeError("pass2_request must be CognitionPassRequest or None")
    if not content.strip():
        raise ValueError("user content must not be empty")

    async with execution_runtime._conversation_lock:
        async with execution_runtime._authority_lock:
            execution_revision = execution_runtime._reserve_turn()
        await execution_runtime._cancel_superseded_extractions()
        user_event, state, cognitive_input = _prepare_two_pass_user_turn(
            character=character,
            content=content,
            memory_budget=memory_budget,
            event_budget=event_budget,
            continuity_runtime=continuity_runtime,
            cognitive_budget=cognitive_budget,
            pass1_request=pass1_request,
        )
        async with execution_runtime._authority_lock:
            execution_runtime._bind_turn(
                revision=execution_revision,
                event_id=user_event.id,
            )
        if pass1_request is None:
            conversation = await generate_conversation(cognitive_input)
        else:
            conversation = await generate_conversation(
                cognitive_input,
                pass_request=pass1_request,
            )
        if not isinstance(conversation, CognitionConversationOutput):
            raise TypeError(
                "two-pass provider generate_conversation must return CognitionConversationOutput"
            )
        assistant_event = _commit_conversation_response(
            character=character,
            response=conversation.response,
        )
        async with execution_runtime._authority_lock:
            origin_continuity = _advance_continuity_after_conversation(
                continuity_runtime
            )
        extraction = _schedule_extraction(
            character=character,
            provider=provider,
            cognitive_input=cognitive_input,
            assistant_response=conversation.response,
            origin_state=state,
            origin_continuity=origin_continuity,
            continuity_runtime=continuity_runtime,
            execution_runtime=execution_runtime,
            execution_revision=execution_revision,
            cognitive_budget=cognitive_budget,
            pass_request=pass2_request,
        )

    return TwoPassTurnResult(
        response=conversation.response,
        user_event=user_event,
        assistant_event=assistant_event,
        extraction=extraction,
        conversation_completion=conversation.completion,
    )


async def run_user_turn_two_pass_streaming(
    *,
    character: CharacterDirectory,
    provider: TwoPassCognitiveProvider,
    content: str,
    emit_response_delta: Callable[[str], Awaitable[None]],
    execution_runtime: CognitionExecutionRuntime,
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
    continuity_runtime: ContinuityRuntime | None = None,
    cognitive_budget: TwoPassCognitiveBudgetRuntimeConfig | None = None,
    pass1_request: CognitionPassRequest | None = None,
    pass2_request: CognitionPassRequest | None = None,
) -> TwoPassTurnResult:
    """Stream Pass 1, then background Pass 2 after the complete response is valid."""

    stream_generate_conversation = _require_two_pass_provider(provider, streaming=True)
    _require_execution_runtime(execution_runtime)
    _require_two_pass_budget(cognitive_budget)
    if pass1_request is not None and not isinstance(pass1_request, CognitionPassRequest):
        raise TypeError("pass1_request must be CognitionPassRequest or None")
    if pass2_request is not None and not isinstance(pass2_request, CognitionPassRequest):
        raise TypeError("pass2_request must be CognitionPassRequest or None")
    if not content.strip():
        raise ValueError("user content must not be empty")

    async with execution_runtime._conversation_lock:
        async with execution_runtime._authority_lock:
            execution_revision = execution_runtime._reserve_turn()
        await execution_runtime._cancel_superseded_extractions()
        user_event, state, cognitive_input = _prepare_two_pass_user_turn(
            character=character,
            content=content,
            memory_budget=memory_budget,
            event_budget=event_budget,
            continuity_runtime=continuity_runtime,
            cognitive_budget=cognitive_budget,
            pass1_request=pass1_request,
        )
        async with execution_runtime._authority_lock:
            execution_runtime._bind_turn(
                revision=execution_revision,
                event_id=user_event.id,
            )
        delivery = _StreamingResponseDelivery(emit_response_delta)
        if pass1_request is None:
            conversation = await stream_generate_conversation(
                cognitive_input,
                delivery.emit,
            )
        else:
            conversation = await stream_generate_conversation(
                cognitive_input,
                delivery.emit,
                pass_request=pass1_request,
            )
        if not isinstance(conversation, CognitionConversationOutput):
            raise TypeError(
                "two-pass provider stream_generate_conversation must return "
                "CognitionConversationOutput"
            )
        await delivery.reconcile(conversation.response)
        assistant_event = _commit_conversation_response(
            character=character,
            response=conversation.response,
        )
        async with execution_runtime._authority_lock:
            origin_continuity = _advance_continuity_after_conversation(
                continuity_runtime
            )
        extraction = _schedule_extraction(
            character=character,
            provider=provider,
            cognitive_input=cognitive_input,
            assistant_response=conversation.response,
            origin_state=state,
            origin_continuity=origin_continuity,
            continuity_runtime=continuity_runtime,
            execution_runtime=execution_runtime,
            execution_revision=execution_revision,
            cognitive_budget=cognitive_budget,
            pass_request=pass2_request,
        )

    return TwoPassTurnResult(
        response=conversation.response,
        user_event=user_event,
        assistant_event=assistant_event,
        extraction=extraction,
        conversation_completion=conversation.completion,
    )


def _prepare_two_pass_user_turn(
    *,
    character: CharacterDirectory,
    content: str,
    memory_budget: MemoryRetrievalBudget | None,
    event_budget: EventRetrievalBudget | None,
    continuity_runtime: ContinuityRuntime | None,
    cognitive_budget: TwoPassCognitiveBudgetRuntimeConfig | None,
    pass1_request: CognitionPassRequest | None,
):
    if cognitive_budget is None:
        user_event, state, cognitive_input, _ = _prepare_user_turn(
            character=character,
            content=content,
            memory_budget=memory_budget,
            event_budget=event_budget,
            continuity_runtime=continuity_runtime,
            include_retrieval_diagnostics=False,
        )
        return user_event, state, cognitive_input

    _reject_overlapping_budget_configuration(
        memory_budget=memory_budget,
        event_budget=event_budget,
    )
    pass1_budget = CognitiveBudgetRuntimeConfig(
        total=cognitive_budget.pass1_total,
        policy=cognitive_budget.policy,
        token_counter=_ConversationBudgetTokenCounter(
            token_counter=cognitive_budget.token_counter,
            pass_request=pass1_request,
        ),
    )
    return _prepare_budgeted_user_turn(
        character=character,
        content=content,
        continuity_runtime=continuity_runtime,
        cognitive_budget=pass1_budget,
    )


def _commit_conversation_response(
    *,
    character: CharacterDirectory,
    response: str,
) -> Event:
    assistant_event = Event.create(
        type="message",
        actor="assistant",
        payload={"content": response},
    )
    character.append_event(assistant_event)
    return assistant_event


def _advance_continuity_after_conversation(
    continuity_runtime: ContinuityRuntime | None,
) -> ContinuityContext | None:
    if continuity_runtime is None:
        return None
    lifecycle = advance_continuity_lifecycle(
        current_context=continuity_runtime.context,
        lifetime_revisions=continuity_runtime.lifetime_revisions,
    )
    continuity_runtime.context = lifecycle.context
    return lifecycle.context


def _schedule_extraction(
    *,
    character: CharacterDirectory,
    provider: TwoPassCognitiveProvider,
    cognitive_input: CognitiveInput,
    assistant_response: str,
    origin_state: CanonicalState,
    origin_continuity: ContinuityContext | None,
    continuity_runtime: ContinuityRuntime | None,
    execution_runtime: CognitionExecutionRuntime,
    execution_revision: int,
    cognitive_budget: TwoPassCognitiveBudgetRuntimeConfig | None,
    pass_request: CognitionPassRequest | None = None,
) -> asyncio.Task[TwoPassExtractionResult]:
    task = asyncio.create_task(
        _complete_extraction(
            character=character,
            provider=provider,
            extraction_input=CognitionExtractionInput(
                cognitive_input=cognitive_input,
                assistant_response=assistant_response,
            ),
            origin_state=origin_state,
            origin_continuity=origin_continuity,
            continuity_runtime=continuity_runtime,
            execution_runtime=execution_runtime,
            execution_revision=execution_revision,
            cognitive_budget=cognitive_budget,
            pass_request=pass_request,
        )
    )
    execution_runtime._track(task)
    return task


async def _complete_extraction(
    *,
    character: CharacterDirectory,
    provider: TwoPassCognitiveProvider,
    extraction_input: CognitionExtractionInput,
    origin_state: CanonicalState,
    origin_continuity: ContinuityContext | None,
    continuity_runtime: ContinuityRuntime | None,
    execution_runtime: CognitionExecutionRuntime,
    execution_revision: int,
    cognitive_budget: TwoPassCognitiveBudgetRuntimeConfig | None,
    pass_request: CognitionPassRequest | None = None,
) -> TwoPassExtractionResult:
    event_id = extraction_input.originating_event_id
    completion: CognitionCompletionMetadata | None = None
    try:
        if cognitive_budget is not None:
            count = cognitive_budget.token_counter.count_extraction_input(
                extraction_input,
                pass_request=pass_request,
            )
            fit = evaluate_serialized_input_fit(
                config=cognitive_budget.pass2_total,
                count=count,
            )
            if not fit.fits:
                return TwoPassExtractionResult(
                    status=TwoPassExtractionStatus.FAILED,
                    originating_event_id=event_id,
                    state=origin_state,
                    failure_reason="pass2_budget_exceeded",
                )

        if pass_request is None:
            output = await provider.generate_extraction(extraction_input)
        else:
            output = await provider.generate_extraction(
                extraction_input,
                pass_request=pass_request,
            )
        if not isinstance(output, CognitionExtractionOutput):
            raise TypeError(
                "two-pass provider generate_extraction must return CognitionExtractionOutput"
            )
        completion = output.completion

        async with execution_runtime._authority_lock:
            if not execution_runtime._is_current(
                revision=execution_revision,
                event_id=event_id,
            ):
                return TwoPassExtractionResult(
                    status=TwoPassExtractionStatus.STALE,
                    originating_event_id=event_id,
                    state=character.load_state(),
                    completion=completion,
                )

            current_state = character.load_state()
            if current_state != origin_state:
                return TwoPassExtractionResult(
                    status=TwoPassExtractionStatus.STALE,
                    originating_event_id=event_id,
                    state=current_state,
                    completion=completion,
                )
            if (
                continuity_runtime is not None
                and continuity_runtime.context != origin_continuity
            ):
                return TwoPassExtractionResult(
                    status=TwoPassExtractionStatus.STALE,
                    originating_event_id=event_id,
                    state=current_state,
                    completion=completion,
                )

            if output.continuity_candidates and continuity_runtime is None:
                return TwoPassExtractionResult(
                    status=TwoPassExtractionStatus.FAILED,
                    originating_event_id=event_id,
                    state=origin_state,
                    failure_reason="continuity_runtime_required",
                    completion=completion,
                )

            event_by_id = {event.id: event for event in character.iter_events()}
            state_validation = apply_state_candidates(
                current_state=current_state,
                candidates=output.state_candidates,
                events=event_by_id,
                required_source_ids=frozenset({event_id}),
            )

            continuity_validation = None
            if continuity_runtime is not None:
                continuity_validation = apply_continuity_candidates_at_current_revision(
                    current_context=continuity_runtime.context,
                    candidates=output.continuity_candidates,
                    events=event_by_id,
                    required_source_ids=frozenset({event_id}),
                    lifetime_revisions=continuity_runtime.lifetime_revisions,
                )

            if state_validation.changed:
                character.save_state(state_validation.state)
            if continuity_validation is not None:
                continuity_runtime.context = continuity_validation.context

            return TwoPassExtractionResult(
                status=TwoPassExtractionStatus.COMMITTED,
                originating_event_id=event_id,
                state=state_validation.state,
                decisions=state_validation.decisions,
                continuity=continuity_validation,
                completion=completion,
            )
    except asyncio.CancelledError:
        if not execution_runtime._is_current(
            revision=execution_revision,
            event_id=event_id,
        ):
            return TwoPassExtractionResult(
                status=TwoPassExtractionStatus.STALE,
                originating_event_id=event_id,
                state=character.load_state(),
                completion=completion,
            )
        raise
    except Exception:
        return TwoPassExtractionResult(
            status=TwoPassExtractionStatus.FAILED,
            originating_event_id=event_id,
            state=origin_state,
            failure_reason="pass2_failed",
            completion=completion,
        )


def _require_two_pass_provider(provider: object, *, streaming: bool):
    if not callable(getattr(provider, "generate_extraction", None)):
        raise TypeError("provider does not support two-pass structured extraction")
    if not streaming:
        method = getattr(provider, "generate_conversation", None)
        if not callable(method):
            raise TypeError("provider does not support two-pass conversation generation")
        return method
    stream_method = getattr(provider, "stream_generate_conversation", None)
    if not callable(stream_method):
        raise TypeError("provider does not support two-pass conversation streaming")
    return stream_method


def _require_execution_runtime(runtime: object) -> None:
    if not isinstance(runtime, CognitionExecutionRuntime):
        raise TypeError("execution_runtime must be CognitionExecutionRuntime")


def _require_two_pass_budget(
    budget: TwoPassCognitiveBudgetRuntimeConfig | None,
) -> None:
    if budget is not None and not isinstance(budget, TwoPassCognitiveBudgetRuntimeConfig):
        raise TypeError(
            "cognitive_budget must be TwoPassCognitiveBudgetRuntimeConfig or None"
        )

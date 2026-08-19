from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognition_execution import CognitionExtractionInput, CognitionExtractionOutput
from relaylm.cognition_execution_evidence import (
    BUFFERED_EXECUTION_PATH,
    STREAMING_EXECUTION_PATH,
    CognitionExecutionEvidenceIdentity,
    ShadowExtractionEvidence,
    ShadowExtractionStatus,
)
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    ContinuityRuntime,
    EventRetrievalBudget,
    MemoryRetrievalBudget,
    TurnResult,
    run_user_turn,
    run_user_turn_streaming,
)


@dataclass(frozen=True, slots=True)
class ShadowTwoPassTurnResult:
    """Canonical single-pass turn plus independently completing shadow evidence."""

    turn: TurnResult
    execution_identity: CognitionExecutionEvidenceIdentity
    shadow: asyncio.Task[ShadowExtractionEvidence]


class _CapturingCanonicalProvider:
    """Transparent single-pass wrapper that preserves the originating CognitiveInput."""

    def __init__(self, delegate: object) -> None:
        self.delegate = delegate
        self.cognitive_input: CognitiveInput | None = None

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        generate = getattr(self.delegate, "generate", None)
        if not callable(generate):
            raise TypeError("provider does not support canonical single-pass generation")
        self.cognitive_input = cognitive_input
        output = await generate(cognitive_input)
        if not isinstance(output, CognitiveOutput):
            raise TypeError("canonical provider generate must return CognitiveOutput")
        return output

    async def stream_generate(
        self,
        cognitive_input: CognitiveInput,
        emit_response_delta: Callable[[str], Awaitable[None]],
    ) -> CognitiveOutput:
        stream_generate = getattr(self.delegate, "stream_generate", None)
        if not callable(stream_generate):
            raise TypeError("provider does not support canonical single-pass streaming")
        self.cognitive_input = cognitive_input
        output = await stream_generate(cognitive_input, emit_response_delta)
        if not isinstance(output, CognitiveOutput):
            raise TypeError("canonical provider stream_generate must return CognitiveOutput")
        return output


async def run_user_turn_shadow_two_pass(
    *,
    character: CharacterDirectory,
    provider: object,
    content: str,
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
    continuity_runtime: ContinuityRuntime | None = None,
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
) -> ShadowTwoPassTurnResult:
    """Commit canonical single-pass semantics, then observe Pass 2 without mutation."""

    _require_shadow_provider(provider)
    recording = _CapturingCanonicalProvider(provider)
    turn = await run_user_turn(
        character=character,
        provider=recording,
        content=content,
        memory_budget=memory_budget,
        event_budget=event_budget,
        continuity_runtime=continuity_runtime,
        cognitive_budget=cognitive_budget,
    )
    cognitive_input = _require_captured_input(recording)
    identity = CognitionExecutionEvidenceIdentity.shadow_two_pass(
        execution_path=BUFFERED_EXECUTION_PATH
    )
    shadow = _schedule_shadow(
        provider=provider,
        cognitive_input=cognitive_input,
        response=turn.response,
        identity=identity,
    )
    return ShadowTwoPassTurnResult(
        turn=turn,
        execution_identity=identity,
        shadow=shadow,
    )


async def run_user_turn_shadow_two_pass_streaming(
    *,
    character: CharacterDirectory,
    provider: object,
    content: str,
    emit_response_delta: Callable[[str], Awaitable[None]],
    memory_budget: MemoryRetrievalBudget | None = None,
    event_budget: EventRetrievalBudget | None = None,
    continuity_runtime: ContinuityRuntime | None = None,
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
) -> ShadowTwoPassTurnResult:
    """Stream canonical single-pass response, then observe non-mutating shadow Pass 2."""

    _require_shadow_provider(provider, streaming=True)
    recording = _CapturingCanonicalProvider(provider)
    turn = await run_user_turn_streaming(
        character=character,
        provider=recording,
        content=content,
        emit_response_delta=emit_response_delta,
        memory_budget=memory_budget,
        event_budget=event_budget,
        continuity_runtime=continuity_runtime,
        cognitive_budget=cognitive_budget,
    )
    cognitive_input = _require_captured_input(recording)
    identity = CognitionExecutionEvidenceIdentity.shadow_two_pass(
        execution_path=STREAMING_EXECUTION_PATH
    )
    shadow = _schedule_shadow(
        provider=provider,
        cognitive_input=cognitive_input,
        response=turn.response,
        identity=identity,
    )
    return ShadowTwoPassTurnResult(
        turn=turn,
        execution_identity=identity,
        shadow=shadow,
    )


def _schedule_shadow(
    *,
    provider: object,
    cognitive_input: CognitiveInput,
    response: str,
    identity: CognitionExecutionEvidenceIdentity,
) -> asyncio.Task[ShadowExtractionEvidence]:
    return asyncio.create_task(
        _complete_shadow(
            provider=provider,
            extraction_input=CognitionExtractionInput(
                cognitive_input=cognitive_input,
                assistant_response=response,
            ),
            identity=identity,
        )
    )


async def _complete_shadow(
    *,
    provider: object,
    extraction_input: CognitionExtractionInput,
    identity: CognitionExecutionEvidenceIdentity,
) -> ShadowExtractionEvidence:
    event_id = extraction_input.originating_event_id
    try:
        generate_extraction = getattr(provider, "generate_extraction")
        output = await generate_extraction(extraction_input)
        if not isinstance(output, CognitionExtractionOutput):
            raise TypeError(
                "shadow provider generate_extraction must return CognitionExtractionOutput"
            )
        return ShadowExtractionEvidence(
            execution_identity=identity,
            originating_event_id=event_id,
            status=ShadowExtractionStatus.COMPLETED,
            output=output,
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        return ShadowExtractionEvidence(
            execution_identity=identity,
            originating_event_id=event_id,
            status=ShadowExtractionStatus.FAILED,
            failure_reason="shadow_pass2_failed",
        )


def _require_shadow_provider(provider: object, *, streaming: bool = False) -> None:
    if not callable(getattr(provider, "generate", None)):
        raise TypeError("provider does not support canonical single-pass generation")
    if streaming and not callable(getattr(provider, "stream_generate", None)):
        raise TypeError("provider does not support canonical single-pass streaming")
    if not callable(getattr(provider, "generate_extraction", None)):
        raise TypeError("provider does not support shadow structured extraction")


def _require_captured_input(recording: _CapturingCanonicalProvider) -> CognitiveInput:
    if recording.cognitive_input is None:
        raise RuntimeError("canonical turn completed without captured CognitiveInput")
    return recording.cognitive_input

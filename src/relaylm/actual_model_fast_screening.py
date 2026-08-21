from __future__ import annotations

import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Literal

from relaylm.actual_model_vllm_host import VLLMScreeningPlan
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
    CognitionReasoningMode,
)


ScreeningPhase = Literal["single_pass", "pass1", "pass2"]
ScreeningCallOutcome = Literal["completed", "failed"]


class ActualModelFastScreeningError(ValueError):
    """The frozen host plan cannot realize the staged fast-screening contract."""


@dataclass(frozen=True, slots=True)
class ScreeningCallTiming:
    """One provider-call timing observation; never semantic authority or a score."""

    phase: ScreeningPhase
    duration_ms: float
    first_visible_ms: float | None
    outcome: ScreeningCallOutcome

    def __post_init__(self) -> None:
        if self.phase not in {"single_pass", "pass1", "pass2"}:
            raise ValueError(f"unsupported screening timing phase: {self.phase}")
        _validate_non_negative_finite(self.duration_ms, "duration_ms")
        if self.first_visible_ms is not None:
            _validate_non_negative_finite(self.first_visible_ms, "first_visible_ms")
            if self.first_visible_ms > self.duration_ms:
                raise ValueError("first_visible_ms cannot exceed duration_ms")
        if self.outcome not in {"completed", "failed"}:
            raise ValueError(f"unsupported screening call outcome: {self.outcome}")

    def to_mapping(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "duration_ms": self.duration_ms,
            "first_visible_ms": self.first_visible_ms,
            "outcome": self.outcome,
        }


@dataclass(slots=True)
class ScreeningTimingRecorder:
    """Monotonic provider timing captured during the same actual-model execution."""

    clock_ns: Callable[[], int] = time.monotonic_ns
    calls: list[ScreeningCallTiming] = field(default_factory=list)

    def append(
        self,
        *,
        phase: ScreeningPhase,
        started_ns: int,
        completed_ns: int,
        first_visible_ns: int | None,
        outcome: ScreeningCallOutcome,
    ) -> None:
        if completed_ns < started_ns:
            raise ValueError("screening timing clock moved backwards")
        first_visible_ms = None
        if first_visible_ns is not None:
            if first_visible_ns < started_ns or first_visible_ns > completed_ns:
                raise ValueError("first visible timestamp is outside provider call")
            first_visible_ms = (first_visible_ns - started_ns) / 1_000_000
        self.calls.append(
            ScreeningCallTiming(
                phase=phase,
                duration_ms=(completed_ns - started_ns) / 1_000_000,
                first_visible_ms=first_visible_ms,
                outcome=outcome,
            )
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "clock": "monotonic_ns",
            "calls": [call.to_mapping() for call in self.calls],
        }


def topology_screening_condition_ids(plan: VLLMScreeningPlan) -> tuple[str, str]:
    """Return only the no-reasoning A/B topology comparison for Stage 1."""

    _require_plan(plan)
    single = plan.conditions["A"]
    two_pass = plan.conditions["B"]
    if single.cognition_execution.mode != "single_pass":
        raise ActualModelFastScreeningError("Stage 1 condition A must be single_pass")
    if two_pass.cognition_execution.mode != "two_pass":
        raise ActualModelFastScreeningError("Stage 1 condition B must be two_pass")
    if single.pass_requests.single_request is None:
        raise ActualModelFastScreeningError("Stage 1 condition A requires single_pass request")
    if two_pass.pass_requests.pass1 is None or two_pass.pass_requests.pass2 is None:
        raise ActualModelFastScreeningError("Stage 1 condition B requires pass1 and pass2")
    _require_reasoning_off(single.pass_requests.single_request, "A.single_pass")
    _require_reasoning_off(two_pass.pass_requests.pass1, "B.pass1")
    _require_reasoning_off(two_pass.pass_requests.pass2, "B.pass2")
    return ("A", "B")


def reasoning_escalation_condition_ids(
    plan: VLLMScreeningPlan,
    *,
    structured_semantic_quality_sufficient: bool,
) -> tuple[str, ...]:
    """Expose Pass 2 reasoning only after Stage 1 demonstrates semantic need."""

    if not isinstance(structured_semantic_quality_sufficient, bool):
        raise TypeError("structured_semantic_quality_sufficient must be bool")
    topology_screening_condition_ids(plan)
    if structured_semantic_quality_sufficient:
        return ()

    baseline = plan.conditions["B"]
    escalation = plan.conditions["C"]
    if escalation.cognition_execution.mode != "two_pass":
        raise ActualModelFastScreeningError("reasoning escalation condition C must be two_pass")
    if escalation.pass_requests.pass1 is None or escalation.pass_requests.pass2 is None:
        raise ActualModelFastScreeningError("condition C requires pass1 and pass2")
    if baseline.pass_requests.pass1 != escalation.pass_requests.pass1:
        raise ActualModelFastScreeningError(
            "reasoning escalation must keep Pass 1 identical to the two-pass baseline"
        )
    baseline_pass2 = baseline.pass_requests.pass2
    escalation_pass2 = escalation.pass_requests.pass2
    assert baseline_pass2 is not None
    _require_reasoning_off(baseline_pass2, "B.pass2")
    if escalation_pass2.reasoning_mode in {None, CognitionReasoningMode.OFF}:
        raise ActualModelFastScreeningError(
            "condition C must add an explicit non-off Pass 2 reasoning condition"
        )
    if (
        baseline_pass2.temperature != escalation_pass2.temperature
        or baseline_pass2.top_p != escalation_pass2.top_p
        or baseline_pass2.max_output_tokens != escalation_pass2.max_output_tokens
    ):
        raise ActualModelFastScreeningError(
            "reasoning escalation may not drift unrelated Pass 2 decoding controls"
        )
    return ("C",)


def instrument_screening_provider(
    provider: object,
    *,
    recorder: ScreeningTimingRecorder,
) -> object:
    """Wrap one already-resolved provider without changing request or output semantics."""

    if not isinstance(recorder, ScreeningTimingRecorder):
        raise TypeError("recorder must be ScreeningTimingRecorder")
    return _TimedScreeningProvider(provider, recorder)


class _TimedScreeningProvider:
    def __init__(self, delegate: object, recorder: ScreeningTimingRecorder) -> None:
        self._delegate = delegate
        self._recorder = recorder

    async def generate(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitiveOutput:
        async def call() -> CognitiveOutput:
            generate = getattr(self._delegate, "generate", None)
            if not callable(generate):
                raise TypeError("provider does not support cognitive generation")
            if pass_request is None:
                return await generate(cognitive_input)
            return await generate(cognitive_input, pass_request=pass_request)

        return await self._timed_buffered("single_pass", call)

    async def stream_generate(
        self,
        cognitive_input: CognitiveInput,
        emit_response_delta: Callable[[str], Awaitable[None]],
    ) -> CognitiveOutput:
        stream_generate = getattr(self._delegate, "stream_generate", None)
        if not callable(stream_generate):
            raise TypeError("provider does not support cognitive streaming")
        return await self._timed_streaming(
            "single_pass",
            lambda emit: stream_generate(cognitive_input, emit),
            emit_response_delta,
        )

    async def generate_conversation(
        self,
        cognitive_input: CognitiveInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionConversationOutput:
        async def call() -> CognitionConversationOutput:
            generate = getattr(self._delegate, "generate_conversation", None)
            if not callable(generate):
                raise TypeError("provider does not support two-pass conversation generation")
            if pass_request is None:
                return await generate(cognitive_input)
            return await generate(cognitive_input, pass_request=pass_request)

        return await self._timed_buffered("pass1", call)

    async def stream_generate_conversation(
        self,
        cognitive_input: CognitiveInput,
        emit_response_delta: Callable[[str], Awaitable[None]],
    ) -> CognitionConversationOutput:
        generate = getattr(self._delegate, "stream_generate_conversation", None)
        if not callable(generate):
            raise TypeError("provider does not support two-pass conversation streaming")
        return await self._timed_streaming(
            "pass1",
            lambda emit: generate(cognitive_input, emit),
            emit_response_delta,
        )

    async def generate_extraction(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None = None,
    ) -> CognitionExtractionOutput:
        async def call() -> CognitionExtractionOutput:
            generate = getattr(self._delegate, "generate_extraction", None)
            if not callable(generate):
                raise TypeError("provider does not support structured extraction")
            if pass_request is None:
                return await generate(extraction_input)
            return await generate(extraction_input, pass_request=pass_request)

        return await self._timed_buffered("pass2", call)

    async def _timed_buffered(self, phase: ScreeningPhase, call):
        started = self._recorder.clock_ns()
        outcome: ScreeningCallOutcome = "completed"
        try:
            return await call()
        except BaseException:
            outcome = "failed"
            raise
        finally:
            completed = self._recorder.clock_ns()
            self._recorder.append(
                phase=phase,
                started_ns=started,
                completed_ns=completed,
                first_visible_ns=None,
                outcome=outcome,
            )

    async def _timed_streaming(
        self,
        phase: ScreeningPhase,
        call,
        emit_response_delta: Callable[[str], Awaitable[None]],
    ):
        started = self._recorder.clock_ns()
        first_visible: int | None = None
        outcome: ScreeningCallOutcome = "completed"

        async def emit(delta: str) -> None:
            nonlocal first_visible
            if first_visible is None:
                first_visible = self._recorder.clock_ns()
            await emit_response_delta(delta)

        try:
            return await call(emit)
        except BaseException:
            outcome = "failed"
            raise
        finally:
            completed = self._recorder.clock_ns()
            self._recorder.append(
                phase=phase,
                started_ns=started,
                completed_ns=completed,
                first_visible_ns=first_visible,
                outcome=outcome,
            )


def _require_plan(plan: VLLMScreeningPlan) -> None:
    if not isinstance(plan, VLLMScreeningPlan):
        raise TypeError("plan must be VLLMScreeningPlan")
    missing = tuple(key for key in ("A", "B", "C") if key not in plan.conditions)
    if missing:
        raise ActualModelFastScreeningError(
            "fast screening requires frozen A/B/C conditions: " + ", ".join(missing)
        )


def _require_reasoning_off(request: CognitionPassRequest, label: str) -> None:
    if request.reasoning_mode is not CognitionReasoningMode.OFF:
        raise ActualModelFastScreeningError(f"{label} must use reasoning=off")
    if request.reasoning_budget is not None:
        raise ActualModelFastScreeningError(f"{label} reasoning=off cannot carry a budget")


def _validate_non_negative_finite(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric")
    if not math.isfinite(float(value)) or value < 0:
        raise ValueError(f"{label} must be finite and non-negative")

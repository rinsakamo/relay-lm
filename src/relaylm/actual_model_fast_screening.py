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
from relaylm.providers.openai_compatible import ProviderProtocolError


ScreeningPhase = Literal["single_pass", "pass1", "pass2"]
ScreeningCallOutcome = Literal["completed", "failed"]
ScreeningConditionRole = Literal[
    "reference_baseline",
    "pass2_reasoning_escalation",
]

REFERENCE_BASELINE_ROLE: ScreeningConditionRole = "reference_baseline"
PASS2_REASONING_ESCALATION_ROLE: ScreeningConditionRole = "pass2_reasoning_escalation"
SCREENING_CONDITION_ROLES: tuple[ScreeningConditionRole, ...] = (
    REFERENCE_BASELINE_ROLE,
    PASS2_REASONING_ESCALATION_ROLE,
)


class ActualModelFastScreeningError(ValueError):
    """The frozen host plan cannot realize the current two-pass screening contract."""


@dataclass(frozen=True, slots=True)
class ScreeningCallTiming:
    """One provider-call timing observation; never semantic authority or a score."""

    phase: ScreeningPhase
    duration_ms: float
    first_visible_ms: float | None
    outcome: ScreeningCallOutcome
    failure_exception_type: str | None = None
    failure_exception_message: str | None = None

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
        if self.outcome == "completed":
            if (
                self.failure_exception_type is not None
                or self.failure_exception_message is not None
            ):
                raise ValueError("completed screening call cannot carry failure diagnostics")
        if self.failure_exception_type is not None:
            if not isinstance(self.failure_exception_type, str):
                raise TypeError("failure_exception_type must be a string or None")
            if not self.failure_exception_type.strip():
                raise ValueError("failure_exception_type must not be empty")
        if self.failure_exception_message is not None:
            if self.failure_exception_type is None:
                raise ValueError(
                    "failure_exception_message requires failure_exception_type"
                )
            if not isinstance(self.failure_exception_message, str):
                raise TypeError("failure_exception_message must be a string or None")
            if not self.failure_exception_message.strip():
                raise ValueError("failure_exception_message must not be empty")

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
        failure_exception_type: str | None = None,
        failure_exception_message: str | None = None,
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
                failure_exception_type=failure_exception_type,
                failure_exception_message=failure_exception_message,
            )
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "clock": "monotonic_ns",
            "calls": [call.to_mapping() for call in self.calls],
        }


def screening_condition_key_for_role(
    plan: VLLMScreeningPlan,
    role: ScreeningConditionRole,
) -> str:
    """Resolve one current Stage R role to an immutable plan coordinate."""

    if not isinstance(plan, VLLMScreeningPlan):
        raise TypeError("plan must be VLLMScreeningPlan")
    if role not in SCREENING_CONDITION_ROLES:
        raise ActualModelFastScreeningError(
            f"unsupported Stage R screening role: {role}"
        )

    baseline_key = _reference_baseline_key(plan)
    if role == REFERENCE_BASELINE_ROLE:
        return baseline_key
    return _pass2_reasoning_escalation_key(plan, baseline_key=baseline_key)


def reference_screening_condition_roles(
    plan: VLLMScreeningPlan,
) -> tuple[ScreeningConditionRole]:
    """Expose the two-pass OFF/OFF reference without historical plan labels."""

    screening_condition_key_for_role(plan, REFERENCE_BASELINE_ROLE)
    return (REFERENCE_BASELINE_ROLE,)


def reasoning_escalation_condition_roles(
    plan: VLLMScreeningPlan,
    *,
    pass2_semantic_quality_sufficient: bool,
) -> tuple[ScreeningConditionRole, ...]:
    """Expose Pass 2 escalation only after the reference shows semantic need."""

    if not isinstance(pass2_semantic_quality_sufficient, bool):
        raise TypeError("pass2_semantic_quality_sufficient must be bool")
    screening_condition_key_for_role(plan, REFERENCE_BASELINE_ROLE)
    if pass2_semantic_quality_sufficient:
        return ()
    screening_condition_key_for_role(plan, PASS2_REASONING_ESCALATION_ROLE)
    return (PASS2_REASONING_ESCALATION_ROLE,)


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
        failure_exception_type: str | None = None
        failure_exception_message: str | None = None
        try:
            return await call()
        except BaseException as exc:
            outcome = "failed"
            failure_exception_type, failure_exception_message = (
                _bounded_failure_diagnostic(exc)
            )
            raise
        finally:
            completed = self._recorder.clock_ns()
            self._recorder.append(
                phase=phase,
                started_ns=started,
                completed_ns=completed,
                first_visible_ns=None,
                outcome=outcome,
                failure_exception_type=failure_exception_type,
                failure_exception_message=failure_exception_message,
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
        failure_exception_type: str | None = None
        failure_exception_message: str | None = None

        async def emit(delta: str) -> None:
            nonlocal first_visible
            if first_visible is None:
                first_visible = self._recorder.clock_ns()
            await emit_response_delta(delta)

        try:
            return await call(emit)
        except BaseException as exc:
            outcome = "failed"
            failure_exception_type, failure_exception_message = (
                _bounded_failure_diagnostic(exc)
            )
            raise
        finally:
            completed = self._recorder.clock_ns()
            self._recorder.append(
                phase=phase,
                started_ns=started,
                completed_ns=completed,
                first_visible_ns=first_visible,
                outcome=outcome,
                failure_exception_type=failure_exception_type,
                failure_exception_message=failure_exception_message,
            )


def _bounded_failure_diagnostic(exc: BaseException) -> tuple[str, str | None]:
    exception_type = type(exc).__name__
    if not isinstance(exc, ProviderProtocolError):
        return exception_type, None
    message = " ".join(str(exc).split())
    if not message:
        return exception_type, None
    return exception_type, message[:512]


def _reference_baseline_key(plan: VLLMScreeningPlan) -> str:
    candidates: list[str] = []
    for key, condition in plan.conditions.items():
        if condition.cognition_execution.mode != "two_pass":
            continue
        pass1 = condition.pass_requests.pass1
        pass2 = condition.pass_requests.pass2
        if pass1 is None or pass2 is None:
            continue
        if _is_reasoning_off(pass1) and _is_reasoning_off(pass2):
            candidates.append(key)
    if len(candidates) != 1:
        raise ActualModelFastScreeningError(
            "Stage R requires exactly one two-pass reasoning-off reference baseline"
        )
    return candidates[0]


def _pass2_reasoning_escalation_key(
    plan: VLLMScreeningPlan,
    *,
    baseline_key: str,
) -> str:
    baseline = plan.conditions[baseline_key]
    baseline_pass1 = baseline.condition.pass_requests.pass1 if False else baseline.pass_requests.pass1
    baseline_pass2 = baseline.pass_requests.pass2
    assert baseline_pass1 is not None
    assert baseline_pass2 is not None
    _require_reasoning_off(baseline_pass1, f"{baseline_key}.pass1")
    _require_reasoning_off(baseline_pass2, f"{baseline_key}.pass2")

    candidates: list[str] = []
    for key, condition in plan.conditions.items():
        if key == baseline_key or condition.cognition_execution.mode != "two_pass":
            continue
        pass1 = condition.pass_requests.pass1
        pass2 = condition.pass_requests.pass2
        if pass1 is None or pass2 is None:
            continue
        if pass1 != baseline_pass1:
            continue
        if pass2.reasoning_mode in {None, CognitionReasoningMode.OFF}:
            continue
        if (
            baseline_pass2.temperature != pass2.temperature
            or baseline_pass2.top_p != pass2.top_p
            or baseline_pass2.max_output_tokens != pass2.max_output_tokens
        ):
            continue
        candidates.append(key)
    if len(candidates) != 1:
        raise ActualModelFastScreeningError(
            "Stage R requires exactly one Pass 2-only reasoning escalation condition"
        )
    return candidates[0]


def _is_reasoning_off(request: CognitionPassRequest) -> bool:
    return (
        request.reasoning_mode is CognitionReasoningMode.OFF
        and request.reasoning_budget is None
    )


def _require_reasoning_off(request: CognitionPassRequest, label: str) -> None:
    if request.reasoning_mode is not CognitionReasoningMode.OFF:
        raise ActualModelFastScreeningError(f"{label} must use reasoning=off")
    if request.reasoning_budget is not None:
        raise ActualModelFastScreeningError(
            f"{label} reasoning=off cannot carry a budget"
        )


def _validate_non_negative_finite(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric")
    if not math.isfinite(float(value)) or value < 0:
        raise ValueError(f"{label} must be finite and non-negative")

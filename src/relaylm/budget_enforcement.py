from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from relaylm.budget import BudgetDegradationPolicy, BudgetPlan, TotalBudgetConfig
from relaylm.cognitive import CognitiveInput


def _require_non_negative_token_count(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer token count")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


class TokenCountMode(str, Enum):
    """How a final provider-input token count was established."""

    EXACT = "exact"
    CONSERVATIVE_ESTIMATE = "conservative_estimate"


@dataclass(frozen=True, slots=True)
class SerializedInputTokenCount:
    """Token accounting for the real serialized provider model input.

    ``CONSERVATIVE_ESTIMATE`` is a contract: ``total_input_tokens`` must be an
    upper bound for the configured provider/model path. A merely typical or
    optimistic estimate is not a valid value for this type.

    ``required_input_framing_tokens`` attributes the provider/schema/framing part
    of that same total. The remaining tokens are accounted as cognitive input.
    The final total remains authoritative for hard fit because tokenizer boundary
    effects need not be independently additive across those conceptual parts.
    """

    total_input_tokens: int
    required_input_framing_tokens: int
    mode: TokenCountMode

    def __post_init__(self) -> None:
        _require_non_negative_token_count("total_input_tokens", self.total_input_tokens)
        _require_non_negative_token_count(
            "required_input_framing_tokens",
            self.required_input_framing_tokens,
        )
        if self.required_input_framing_tokens > self.total_input_tokens:
            raise ValueError(
                "required_input_framing_tokens must not exceed total_input_tokens"
            )
        if not isinstance(self.mode, TokenCountMode):
            raise TypeError("mode must be a TokenCountMode")

    @property
    def cognitive_input_tokens(self) -> int:
        return self.total_input_tokens - self.required_input_framing_tokens


@runtime_checkable
class SerializedCognitiveInputTokenCounter(Protocol):
    """Provider/model-specific counter for the exact input serialization it uses."""

    def count_serialized_input(
        self,
        cognitive_input: CognitiveInput,
    ) -> SerializedInputTokenCount:
        """Count or conservatively upper-bound the final serialized model input."""
        ...


@dataclass(frozen=True, slots=True)
class SerializedInputFit:
    """Content-free hard-fit result for one final serialized provider input."""

    config: TotalBudgetConfig
    count: SerializedInputTokenCount

    @property
    def effective_input_capacity(self) -> int:
        return self.config.serialized_input_capacity

    @property
    def fits(self) -> bool:
        return (
            self.count.total_input_tokens + self.config.reserved_output_tokens
            <= self.config.model_context_window
        )

    @property
    def overflow_tokens(self) -> int:
        return max(
            0,
            self.count.total_input_tokens
            + self.config.reserved_output_tokens
            - self.config.model_context_window,
        )


def evaluate_serialized_input_fit(
    *,
    config: TotalBudgetConfig,
    count: SerializedInputTokenCount,
) -> SerializedInputFit:
    """Evaluate the hard total-context equation without changing semantic content."""

    return SerializedInputFit(config=config, count=count)


CompileCognitiveInputForBudgetPlan = Callable[[BudgetPlan], CognitiveInput]


class BudgetEnforcementOutcome(str, Enum):
    FIT = "fit"
    DEGRADED_FIT = "degraded_fit"


class BudgetEnforcementFailureReason(str, Enum):
    DEGRADATION_EXHAUSTED = "degradation_exhausted"


@dataclass(frozen=True, slots=True)
class BudgetEnforcementResult:
    """A fit CognitiveInput that is safe to pass to exactly one generation call."""

    cognitive_input: CognitiveInput
    plan: BudgetPlan
    count: SerializedInputTokenCount
    degradation_step_count: int

    def __post_init__(self) -> None:
        if isinstance(self.degradation_step_count, bool) or not isinstance(
            self.degradation_step_count,
            int,
        ):
            raise TypeError("degradation_step_count must be an integer")
        if self.degradation_step_count < 0:
            raise ValueError("degradation_step_count must be non-negative")

    @property
    def outcome(self) -> BudgetEnforcementOutcome:
        if self.degradation_step_count == 0:
            return BudgetEnforcementOutcome.FIT
        return BudgetEnforcementOutcome.DEGRADED_FIT

    @property
    def pressure_occurred(self) -> bool:
        return self.degradation_step_count > 0


class CognitiveBudgetExceeded(RuntimeError):
    """Bounded pre-generation failure after all configured reductions are exhausted."""

    def __init__(
        self,
        *,
        reason: BudgetEnforcementFailureReason,
        config: TotalBudgetConfig,
        final_plan: BudgetPlan,
        final_count: SerializedInputTokenCount,
        degradation_step_count: int,
    ) -> None:
        self.reason = reason
        self.config = config
        self.final_plan = final_plan
        self.final_count = final_count
        self.degradation_step_count = degradation_step_count
        overflow = evaluate_serialized_input_fit(
            config=config,
            count=final_count,
        ).overflow_tokens
        super().__init__(f"cognitive budget exceeded: {reason.value}; overflow_tokens={overflow}")


def enforce_serialized_input_budget(
    *,
    config: TotalBudgetConfig,
    policy: BudgetDegradationPolicy,
    compile_cognitive_input: CompileCognitiveInputForBudgetPlan,
    token_counter: SerializedCognitiveInputTokenCounter,
) -> BudgetEnforcementResult:
    """Compile, count, and deterministically degrade until final input fits.

    The compiler callback is the semantic-owner boundary: it decides what content
    belongs inside each explicit ``BudgetPlan`` envelope. It must be deterministic
    and side-effect free for the duration of enforcement; in particular, repeated
    pressure projections must not mutate State, Continuity lifecycle/authority, or
    persistence. This function never inspects or ranks semantic payload.

    No provider generation is accepted by this API. A fit ``CognitiveInput`` is
    returned only after the final serialized provider input satisfies the hard
    context equation. If all caller-configured degradation steps are exhausted,
    the function raises before any generation can occur.
    """

    final_plan: BudgetPlan | None = None
    final_count: SerializedInputTokenCount | None = None

    for step_count in range(len(policy.steps) + 1):
        plan = policy.plan_after_steps(step_count)
        cognitive_input = compile_cognitive_input(plan)
        if not isinstance(cognitive_input, CognitiveInput):
            raise TypeError("compile_cognitive_input must return CognitiveInput")
        count = token_counter.count_serialized_input(cognitive_input)
        if not isinstance(count, SerializedInputTokenCount):
            raise TypeError(
                "token_counter.count_serialized_input must return SerializedInputTokenCount"
            )
        final_plan = plan
        final_count = count
        fit = evaluate_serialized_input_fit(config=config, count=count)
        if fit.fits:
            return BudgetEnforcementResult(
                cognitive_input=cognitive_input,
                plan=plan,
                count=count,
                degradation_step_count=step_count,
            )

    assert final_plan is not None
    assert final_count is not None
    raise CognitiveBudgetExceeded(
        reason=BudgetEnforcementFailureReason.DEGRADATION_EXHAUSTED,
        config=config,
        final_plan=final_plan,
        final_count=final_count,
        degradation_step_count=len(policy.steps),
    )

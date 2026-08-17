from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relaylm.budget import BudgetDegradationPolicy, TotalBudgetConfig
from relaylm.budget_enforcement import (
    BudgetEnforcementFailureReason,
    BudgetEnforcementResult,
    CognitiveBudgetExceeded,
    SerializedInputTokenCount,
    TokenCountMode,
)


class CognitiveBudgetDiagnosticOutcome(str, Enum):
    """Aggregate final result of total cognitive-budget enforcement."""

    FIT = "fit"
    DEGRADED_FIT = "degraded_fit"
    BOUNDED_FAILURE = "bounded_failure"


@dataclass(frozen=True, slots=True)
class BudgetTierReductionDiagnostics:
    """Content-free reductions applied within one protection tier."""

    tier: int
    reduction_step_count: int
    reduced_layer_count: int


@dataclass(frozen=True, slots=True)
class CognitiveBudgetDiagnostics:
    """Aggregate content-free observations for one total-budget enforcement.

    Diagnostics intentionally contain only configured capacities, token counts,
    counting mode, deterministic reduction counts, and bounded outcome metadata.
    They never retain CognitiveInput, State, Continuity, MEMORY, Event content, or
    other semantic payload.
    """

    model_context_window: int
    effective_input_capacity: int
    reserved_output_tokens: int
    required_input_framing_tokens: int
    final_input_tokens: int
    final_cognitive_input_tokens: int
    available_cognitive_capacity: int
    pressure_occurred: bool
    degradation_step_count: int
    reduced_layer_count: int
    reduced_tier_count: int
    tier_reductions: tuple[BudgetTierReductionDiagnostics, ...]
    outcome: CognitiveBudgetDiagnosticOutcome
    failure_reason: BudgetEnforcementFailureReason | None
    count_mode: TokenCountMode


def diagnostics_for_budget_result(
    *,
    config: TotalBudgetConfig,
    policy: BudgetDegradationPolicy,
    result: BudgetEnforcementResult,
) -> CognitiveBudgetDiagnostics:
    """Build aggregate diagnostics for a successful final serialized fit."""

    outcome = (
        CognitiveBudgetDiagnosticOutcome.FIT
        if result.degradation_step_count == 0
        else CognitiveBudgetDiagnosticOutcome.DEGRADED_FIT
    )
    return _build_diagnostics(
        config=config,
        policy=policy,
        count=result.count,
        degradation_step_count=result.degradation_step_count,
        outcome=outcome,
        failure_reason=None,
    )


def diagnostics_for_budget_failure(
    *,
    config: TotalBudgetConfig,
    policy: BudgetDegradationPolicy,
    failure: CognitiveBudgetExceeded,
) -> CognitiveBudgetDiagnostics:
    """Build aggregate diagnostics for a bounded pre-generation failure."""

    if failure.config != config:
        raise ValueError("failure config must match diagnostics config")
    return _build_diagnostics(
        config=config,
        policy=policy,
        count=failure.final_count,
        degradation_step_count=failure.degradation_step_count,
        outcome=CognitiveBudgetDiagnosticOutcome.BOUNDED_FAILURE,
        failure_reason=failure.reason,
    )


def _build_diagnostics(
    *,
    config: TotalBudgetConfig,
    policy: BudgetDegradationPolicy,
    count: SerializedInputTokenCount,
    degradation_step_count: int,
    outcome: CognitiveBudgetDiagnosticOutcome,
    failure_reason: BudgetEnforcementFailureReason | None,
) -> CognitiveBudgetDiagnostics:
    if isinstance(degradation_step_count, bool) or not isinstance(
        degradation_step_count,
        int,
    ):
        raise TypeError("degradation_step_count must be an integer")
    if degradation_step_count < 0 or degradation_step_count > len(policy.steps):
        raise ValueError("degradation_step_count is outside the configured policy")

    applied_steps = policy.steps[:degradation_step_count]
    reduced_layers = frozenset(step.layer for step in applied_steps)
    reduced_tiers = tuple(sorted({step.tier for step in applied_steps}, reverse=True))
    tier_reductions = tuple(
        BudgetTierReductionDiagnostics(
            tier=tier,
            reduction_step_count=sum(step.tier == tier for step in applied_steps),
            reduced_layer_count=len(
                {step.layer for step in applied_steps if step.tier == tier}
            ),
        )
        for tier in reduced_tiers
    )
    effective_input_capacity = config.serialized_input_capacity
    available_cognitive_capacity = max(
        0,
        effective_input_capacity - count.required_input_framing_tokens,
    )

    return CognitiveBudgetDiagnostics(
        model_context_window=config.model_context_window,
        effective_input_capacity=effective_input_capacity,
        reserved_output_tokens=config.reserved_output_tokens,
        required_input_framing_tokens=count.required_input_framing_tokens,
        final_input_tokens=count.total_input_tokens,
        final_cognitive_input_tokens=count.cognitive_input_tokens,
        available_cognitive_capacity=available_cognitive_capacity,
        pressure_occurred=(
            outcome is not CognitiveBudgetDiagnosticOutcome.FIT
            or degradation_step_count > 0
        ),
        degradation_step_count=degradation_step_count,
        reduced_layer_count=len(reduced_layers),
        reduced_tier_count=len(reduced_tiers),
        tier_reductions=tier_reductions,
        outcome=outcome,
        failure_reason=failure_reason,
        count_mode=count.mode,
    )

from __future__ import annotations

from dataclasses import dataclass

from relaylm.budget import (
    BudgetDegradationPolicy,
    BudgetDegradationStep,
    BudgetPlan,
    CountCharacterEnvelope,
    CountEnvelope,
    LayerEnvelope,
    TotalBudgetConfig,
)
from relaylm.budget_diagnostics import CognitiveBudgetDiagnostics
from relaylm.budget_runtime import (
    CognitiveBudgetRuntimeConfig,
    TwoPassCognitiveBudgetRuntimeConfig,
)
from relaylm.providers.openai_compatible_budget import SerializedInputCounterIdentity


@dataclass(frozen=True, slots=True)
class ExplicitCognitiveBudgetConfiguration:
    """#1386 evidence identity for one explicit #1387 total-budget policy.

    Historical single-pass identity keeps the original ``total`` shape. Canonical
    two-pass identity carries both real per-pass total-capacity equations while
    sharing the same deterministic degradation policy and serialized-input
    counter identity used by the runtime.
    """

    total: TotalBudgetConfig | None
    policy: BudgetDegradationPolicy
    token_counter_identity: SerializedInputCounterIdentity | None = None
    pass1_total: TotalBudgetConfig | None = None
    pass2_total: TotalBudgetConfig | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.policy, BudgetDegradationPolicy):
            raise TypeError("policy must be BudgetDegradationPolicy")
        if self.token_counter_identity is not None and not isinstance(
            self.token_counter_identity,
            SerializedInputCounterIdentity,
        ):
            raise TypeError(
                "token_counter_identity must be SerializedInputCounterIdentity or None"
            )

        single_pass = self.total is not None
        two_pass = (
            self.total is None
            and self.pass1_total is not None
            and self.pass2_total is not None
        )
        if single_pass:
            if not isinstance(self.total, TotalBudgetConfig):
                raise TypeError("total must be TotalBudgetConfig")
            if self.pass1_total is not None or self.pass2_total is not None:
                raise ValueError(
                    "single-pass cognitive budget must not carry pass1_total/pass2_total"
                )
            return
        if not two_pass:
            raise ValueError(
                "cognitive budget identity must carry total or both pass1_total/pass2_total"
            )
        if not isinstance(self.pass1_total, TotalBudgetConfig):
            raise TypeError("pass1_total must be TotalBudgetConfig")
        if not isinstance(self.pass2_total, TotalBudgetConfig):
            raise TypeError("pass2_total must be TotalBudgetConfig")

    @property
    def mode(self) -> str:
        return "single_pass" if self.total is not None else "two_pass"

    @classmethod
    def from_runtime(
        cls,
        runtime: CognitiveBudgetRuntimeConfig | TwoPassCognitiveBudgetRuntimeConfig,
    ) -> "ExplicitCognitiveBudgetConfiguration":
        if isinstance(runtime, CognitiveBudgetRuntimeConfig):
            total = runtime.total
            pass1_total = None
            pass2_total = None
        elif isinstance(runtime, TwoPassCognitiveBudgetRuntimeConfig):
            total = None
            pass1_total = runtime.pass1_total
            pass2_total = runtime.pass2_total
        else:
            raise TypeError(
                "runtime must be CognitiveBudgetRuntimeConfig or "
                "TwoPassCognitiveBudgetRuntimeConfig"
            )
        identity = getattr(runtime.token_counter, "evidence_identity", None)
        if identity is not None and not isinstance(identity, SerializedInputCounterIdentity):
            raise TypeError(
                "runtime token counter evidence_identity must be SerializedInputCounterIdentity"
            )
        return cls(
            total=total,
            policy=runtime.policy,
            token_counter_identity=identity,
            pass1_total=pass1_total,
            pass2_total=pass2_total,
        )

    def uses_context_window(self, effective_context_window: int) -> bool:
        if self.total is not None:
            return self.total.model_context_window == effective_context_window
        assert self.pass1_total is not None
        assert self.pass2_total is not None
        return (
            self.pass1_total.model_context_window == effective_context_window
            and self.pass2_total.model_context_window == effective_context_window
        )

    def to_mapping(self) -> dict[str, object]:
        if self.total is not None:
            mapping: dict[str, object] = {
                "model_context_window": self.total.model_context_window,
                "reserved_output_tokens": self.total.reserved_output_tokens,
                "initial_plan": _serialize_budget_plan(self.policy.initial_plan),
                "degradation_steps": [
                    _serialize_degradation_step(step) for step in self.policy.steps
                ],
            }
        else:
            assert self.pass1_total is not None
            assert self.pass2_total is not None
            mapping = {
                "mode": "two_pass",
                "pass1": _serialize_total_budget(self.pass1_total),
                "pass2": _serialize_total_budget(self.pass2_total),
                "initial_plan": _serialize_budget_plan(self.policy.initial_plan),
                "degradation_steps": [
                    _serialize_degradation_step(step) for step in self.policy.steps
                ],
            }
        if self.token_counter_identity is not None:
            mapping["token_counter"] = self.token_counter_identity.to_mapping()
        return mapping


@dataclass(frozen=True, slots=True)
class ActualModelBudgetTierReductionObservation:
    """Content-free copy of one runtime tier-reduction diagnostic."""

    tier: int
    reduction_step_count: int
    reduced_layer_count: int

    def to_mapping(self) -> dict[str, int]:
        return {
            "tier": self.tier,
            "reduction_step_count": self.reduction_step_count,
            "reduced_layer_count": self.reduced_layer_count,
        }


@dataclass(frozen=True, slots=True)
class ActualModelCognitiveBudgetDiagnostics:
    """Immutable #1386 evidence copy of #1387 aggregate runtime diagnostics."""

    model_context_window: int
    effective_context_capacity: int
    reserved_output_tokens: int
    required_input_framing_tokens: int
    final_input_tokens: int
    final_cognitive_input_tokens: int
    available_cognitive_capacity: int
    pressure_occurred: bool
    degradation_step_count: int
    reduced_layer_count: int
    reduced_tier_count: int
    tier_reductions: tuple[ActualModelBudgetTierReductionObservation, ...]
    outcome: str
    failure_reason: str | None
    count_mode: str

    @classmethod
    def from_runtime(
        cls,
        diagnostics: CognitiveBudgetDiagnostics,
    ) -> "ActualModelCognitiveBudgetDiagnostics":
        if not isinstance(diagnostics, CognitiveBudgetDiagnostics):
            raise TypeError("diagnostics must be CognitiveBudgetDiagnostics")
        return cls(
            model_context_window=diagnostics.model_context_window,
            effective_context_capacity=diagnostics.effective_context_capacity,
            reserved_output_tokens=diagnostics.reserved_output_tokens,
            required_input_framing_tokens=diagnostics.required_input_framing_tokens,
            final_input_tokens=diagnostics.final_input_tokens,
            final_cognitive_input_tokens=diagnostics.final_cognitive_input_tokens,
            available_cognitive_capacity=diagnostics.available_cognitive_capacity,
            pressure_occurred=diagnostics.pressure_occurred,
            degradation_step_count=diagnostics.degradation_step_count,
            reduced_layer_count=diagnostics.reduced_layer_count,
            reduced_tier_count=diagnostics.reduced_tier_count,
            tier_reductions=tuple(
                ActualModelBudgetTierReductionObservation(
                    tier=item.tier,
                    reduction_step_count=item.reduction_step_count,
                    reduced_layer_count=item.reduced_layer_count,
                )
                for item in diagnostics.tier_reductions
            ),
            outcome=diagnostics.outcome.value,
            failure_reason=(
                diagnostics.failure_reason.value
                if diagnostics.failure_reason is not None
                else None
            ),
            count_mode=diagnostics.count_mode.value,
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "model_context_window": self.model_context_window,
            "effective_context_capacity": self.effective_context_capacity,
            "reserved_output_tokens": self.reserved_output_tokens,
            "required_input_framing_tokens": self.required_input_framing_tokens,
            "final_input_tokens": self.final_input_tokens,
            "final_cognitive_input_tokens": self.final_cognitive_input_tokens,
            "available_cognitive_capacity": self.available_cognitive_capacity,
            "pressure_occurred": self.pressure_occurred,
            "degradation_step_count": self.degradation_step_count,
            "reduced_layer_count": self.reduced_layer_count,
            "reduced_tier_count": self.reduced_tier_count,
            "tier_reductions": [item.to_mapping() for item in self.tier_reductions],
            "outcome": self.outcome,
            "failure_reason": self.failure_reason,
            "count_mode": self.count_mode,
        }


@dataclass(frozen=True, slots=True)
class ActualModelBoundedBudgetFailureEvidence:
    """One #1387 bounded pre-generation failure preserved without fake model output."""

    turn_index: int
    input: str
    cognitive_budget: ActualModelCognitiveBudgetDiagnostics

    def __post_init__(self) -> None:
        if isinstance(self.turn_index, bool) or not isinstance(self.turn_index, int):
            raise TypeError("turn_index must be an integer")
        if self.turn_index <= 0:
            raise ValueError("turn_index must be positive")
        if not isinstance(self.input, str) or not self.input.strip():
            raise ValueError("bounded-failure input must be non-empty")
        if self.cognitive_budget.outcome != "bounded_failure":
            raise ValueError("bounded failure evidence requires bounded_failure diagnostics")
        if self.cognitive_budget.failure_reason is None:
            raise ValueError("bounded failure evidence requires a failure reason")

    def to_mapping(self) -> dict[str, object]:
        return {
            "turn_index": self.turn_index,
            "input": self.input,
            "provider_generation_occurred": False,
            "cognitive_budget": self.cognitive_budget.to_mapping(),
        }


def validate_cognitive_budget_runtime_identity(
    *,
    declared: ExplicitCognitiveBudgetConfiguration | None,
    runtime: CognitiveBudgetRuntimeConfig | TwoPassCognitiveBudgetRuntimeConfig | None,
    effective_context_window: int,
) -> None:
    """Fail before model generation when manifest and supplied #1387 runtime drift."""

    if declared is None:
        if runtime is not None:
            raise ValueError(
                "supplied CognitiveBudgetRuntimeConfig must be declared in the run manifest"
            )
        return
    if runtime is None:
        raise ValueError(
            "declared cognitive budget requires supplied CognitiveBudgetRuntimeConfig"
        )
    if not declared.uses_context_window(effective_context_window):
        raise ValueError(
            "cognitive budget model_context_window does not match effective_context_window"
        )
    observed = ExplicitCognitiveBudgetConfiguration.from_runtime(runtime)
    if observed != declared:
        raise ValueError(
            "supplied CognitiveBudgetRuntimeConfig does not match the run manifest"
        )


def _serialize_total_budget(total: TotalBudgetConfig) -> dict[str, int]:
    return {
        "model_context_window": total.model_context_window,
        "reserved_output_tokens": total.reserved_output_tokens,
    }


def _serialize_budget_plan(plan: BudgetPlan) -> dict[str, object]:
    return {
        "canonical_state": _serialize_envelope(plan.canonical_state),
        "working_context": _serialize_envelope(plan.working_context),
        "retrieved_memory": _serialize_envelope(plan.retrieved_memory),
        "event_evidence": _serialize_envelope(plan.event_evidence),
    }


def _serialize_degradation_step(step: BudgetDegradationStep) -> dict[str, object]:
    return {
        "layer": step.layer.value,
        "tier": step.tier,
        "target": _serialize_envelope(step.target),
    }


def _serialize_envelope(envelope: LayerEnvelope) -> dict[str, int]:
    if isinstance(envelope, CountEnvelope):
        return {
            "max_items": envelope.max_items,
            "floor_items": envelope.floor_items,
        }
    if isinstance(envelope, CountCharacterEnvelope):
        return {
            "max_items": envelope.max_items,
            "floor_items": envelope.floor_items,
            "max_chars": envelope.max_chars,
            "floor_chars": envelope.floor_chars,
        }
    raise TypeError(f"unsupported BudgetPlan envelope: {type(envelope).__name__}")

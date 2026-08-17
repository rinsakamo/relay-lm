from __future__ import annotations

from dataclasses import dataclass

from relaylm.budget import BudgetDegradationPolicy, TotalBudgetConfig
from relaylm.budget_enforcement import SerializedCognitiveInputTokenCounter


@dataclass(frozen=True, slots=True)
class CognitiveBudgetRuntimeConfig:
    """Explicit runtime inputs for total cognitive-budget enforcement.

    This type owns no numeric defaults. The caller supplies hard total capacity,
    reserved output capacity, the complete deterministic degradation policy, and
    the configured provider/model-specific serialized-input counter.
    """

    total: TotalBudgetConfig
    policy: BudgetDegradationPolicy
    token_counter: SerializedCognitiveInputTokenCounter

    def __post_init__(self) -> None:
        if not isinstance(self.total, TotalBudgetConfig):
            raise TypeError("total must be TotalBudgetConfig")
        if not isinstance(self.policy, BudgetDegradationPolicy):
            raise TypeError("policy must be BudgetDegradationPolicy")
        if not isinstance(self.token_counter, SerializedCognitiveInputTokenCounter):
            raise TypeError(
                "token_counter must implement SerializedCognitiveInputTokenCounter"
            )

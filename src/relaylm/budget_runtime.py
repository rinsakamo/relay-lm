from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from relaylm.budget import BudgetDegradationPolicy, TotalBudgetConfig
from relaylm.budget_enforcement import (
    SerializedCognitiveInputTokenCounter,
    SerializedInputTokenCount,
)


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


@runtime_checkable
class TwoPassSerializedInputTokenCounter(Protocol):
    """Exact serialized-input counter for both current two-pass model requests.

    Budget semantics deliberately keep the concrete cognition/pass request types
    opaque. The cognitive-turn/provider owners supply those exact request objects;
    this boundary only requires the two count operations and their typed token
    accounting result.
    """

    def count_conversation_input(
        self,
        cognitive_input: Any,
        *,
        pass_request: Any = None,
    ) -> SerializedInputTokenCount:
        ...

    def count_extraction_input(
        self,
        extraction_input: Any,
        *,
        pass_request: Any = None,
    ) -> SerializedInputTokenCount:
        ...


@dataclass(frozen=True, slots=True)
class TwoPassCognitiveBudgetRuntimeConfig:
    """Explicit total-budget inputs for the two real two-pass generations.

    No numeric defaults or hidden pass-2 degradation policy live here. Pass 1
    carries the existing deterministic layer-degradation policy. Pass 2 receives
    its own total-context/output-reserve equation and must fit its exact extraction
    serialization before provider delegation.
    """

    pass1_total: TotalBudgetConfig
    pass2_total: TotalBudgetConfig
    policy: BudgetDegradationPolicy
    token_counter: TwoPassSerializedInputTokenCounter

    def __post_init__(self) -> None:
        if not isinstance(self.pass1_total, TotalBudgetConfig):
            raise TypeError("pass1_total must be TotalBudgetConfig")
        if not isinstance(self.pass2_total, TotalBudgetConfig):
            raise TypeError("pass2_total must be TotalBudgetConfig")
        if not isinstance(self.policy, BudgetDegradationPolicy):
            raise TypeError("policy must be BudgetDegradationPolicy")
        if not isinstance(self.token_counter, TwoPassSerializedInputTokenCounter):
            raise TypeError(
                "token_counter must implement TwoPassSerializedInputTokenCounter"
            )

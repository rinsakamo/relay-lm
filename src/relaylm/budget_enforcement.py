from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from relaylm.budget import TotalBudgetConfig
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

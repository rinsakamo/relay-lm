from __future__ import annotations

from dataclasses import dataclass


def _require_token_count(name: str, value: int, *, positive: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer token count")
    minimum = 1 if positive else 0
    if value < minimum:
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{name} must be {qualifier}")


@dataclass(frozen=True, slots=True)
class TotalBudgetConfig:
    """Explicit hard context capacity and output reservation for one turn."""

    model_context_window: int
    reserved_output_tokens: int

    def __post_init__(self) -> None:
        _require_token_count(
            "model_context_window",
            self.model_context_window,
            positive=True,
        )
        _require_token_count("reserved_output_tokens", self.reserved_output_tokens)

    @property
    def serialized_input_capacity(self) -> int:
        """Maximum serialized provider-input tokens after output reservation."""

        return max(0, self.model_context_window - self.reserved_output_tokens)


@dataclass(frozen=True, slots=True)
class ProtectedAnchorTokenCounts:
    """Explicit token accounting for required framing and protected anchors."""

    required_input_framing: int
    identity: int
    current_event: int

    def __post_init__(self) -> None:
        _require_token_count("required_input_framing", self.required_input_framing)
        _require_token_count("identity", self.identity)
        _require_token_count("current_event", self.current_event)

    @property
    def protected_cognitive_input_tokens(self) -> int:
        return self.identity + self.current_event

    @property
    def protected_serialized_input_tokens(self) -> int:
        return self.required_input_framing + self.protected_cognitive_input_tokens


@dataclass(frozen=True, slots=True)
class TotalBudgetAccounting:
    """Provider-neutral arithmetic boundary for hard total-turn capacity.

    The accounting surface does not choose semantic content. It only records how
    much of the configured model context is consumed by output reserve, required
    framing, Identity, and Current Event before any degradable layer is admitted.
    Negative ``remaining_after_*`` values intentionally expose impossible floors;
    runtime fail-before-generation enforcement is a later orchestration step.
    """

    config: TotalBudgetConfig
    protected: ProtectedAnchorTokenCounts

    @property
    def remaining_after_output_reserve(self) -> int:
        return self.config.model_context_window - self.config.reserved_output_tokens

    @property
    def remaining_after_framing(self) -> int:
        return self.remaining_after_output_reserve - self.protected.required_input_framing

    @property
    def cognitive_input_capacity(self) -> int:
        """Room for all CognitiveInput payload after framing and output reserve."""

        return max(0, self.remaining_after_framing)

    @property
    def remaining_after_protected_anchors(self) -> int:
        return self.remaining_after_framing - self.protected.protected_cognitive_input_tokens

    @property
    def degradable_cognitive_input_capacity(self) -> int:
        """Room left for non-protected layers when the protected floor fits."""

        return max(0, self.remaining_after_protected_anchors)

    @property
    def protected_floor_tokens(self) -> int:
        return (
            self.protected.protected_serialized_input_tokens
            + self.config.reserved_output_tokens
        )

    @property
    def protected_floor_fits(self) -> bool:
        return self.protected_floor_tokens <= self.config.model_context_window

    @property
    def protected_floor_overflow_tokens(self) -> int:
        return max(0, self.protected_floor_tokens - self.config.model_context_window)

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


def _require_token_count(name: str, value: int, *, positive: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer token count")
    minimum = 1 if positive else 0
    if value < minimum:
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{name} must be {qualifier}")


def _require_non_negative_count(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


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


@dataclass(frozen=True, slots=True)
class CountEnvelope:
    """Explicit owner-control envelope and protected floor in item units."""

    max_items: int
    floor_items: int

    def __post_init__(self) -> None:
        _require_non_negative_count("max_items", self.max_items)
        _require_non_negative_count("floor_items", self.floor_items)
        if self.floor_items > self.max_items:
            raise ValueError("floor_items must not exceed max_items")

    @property
    def at_floor(self) -> bool:
        return self.max_items == self.floor_items


@dataclass(frozen=True, slots=True)
class CountCharacterEnvelope:
    """Explicit owner-control envelope and floor in item and character units."""

    max_items: int
    floor_items: int
    max_chars: int
    floor_chars: int

    def __post_init__(self) -> None:
        _require_non_negative_count("max_items", self.max_items)
        _require_non_negative_count("floor_items", self.floor_items)
        _require_non_negative_count("max_chars", self.max_chars)
        _require_non_negative_count("floor_chars", self.floor_chars)
        if self.floor_items > self.max_items:
            raise ValueError("floor_items must not exceed max_items")
        if self.floor_chars > self.max_chars:
            raise ValueError("floor_chars must not exceed max_chars")

    @property
    def at_floor(self) -> bool:
        return self.max_items == self.floor_items and self.max_chars == self.floor_chars


class BudgetLayer(str, Enum):
    """Budget-managed layers whose semantic selectors already expose owner controls."""

    PACKAGE_KNOWLEDGE = "package_knowledge"
    RETRIEVED_MEMORY = "retrieved_memory"
    EVENT_EVIDENCE = "event_evidence"
    WORKING_CONTEXT = "working_context"
    CANONICAL_STATE = "canonical_state"

    @property
    def tier(self) -> int:
        if self in {
            self.PACKAGE_KNOWLEDGE,
            self.RETRIEVED_MEMORY,
            self.EVENT_EVIDENCE,
        }:
            return 3
        if self is self.WORKING_CONTEXT:
            return 2
        return 1


LayerEnvelope = CountEnvelope | CountCharacterEnvelope
LayerEnvelope = CountEnvelope | CountCharacterEnvelope


@dataclass(frozen=True, slots=True)
class BudgetPlan:
    """Explicit layer envelopes without cross-layer semantic ranking.

    Accepted Continuity is intentionally absent until its semantic owner exposes a
    deterministic pressure-selection control. Package KNOWLEDGE is an independent
    optional Tier-3 reference layer with a zero compatibility floor unless the
    caller explicitly allocates it room.
    """

    canonical_state: CountEnvelope
    working_context: CountCharacterEnvelope
    retrieved_memory: CountCharacterEnvelope
    event_evidence: CountCharacterEnvelope
    package_knowledge: CountCharacterEnvelope = field(
        default_factory=lambda: CountCharacterEnvelope(0, 0, 0, 0)
    )

    def envelope_for(self, layer: BudgetLayer) -> LayerEnvelope:
        if layer is BudgetLayer.CANONICAL_STATE:
            return self.canonical_state
        if layer is BudgetLayer.WORKING_CONTEXT:
            return self.working_context
        if layer is BudgetLayer.RETRIEVED_MEMORY:
            return self.retrieved_memory
        if layer is BudgetLayer.PACKAGE_KNOWLEDGE:
            return self.package_knowledge
        return self.event_evidence

    def with_envelope(self, layer: BudgetLayer, envelope: LayerEnvelope) -> BudgetPlan:
        expected_type = type(self.envelope_for(layer))
        if type(envelope) is not expected_type:
            raise TypeError(f"{layer.value} requires {expected_type.__name__}")
        values = {
            "canonical_state": self.canonical_state,
            "working_context": self.working_context,
            "retrieved_memory": self.retrieved_memory,
            "event_evidence": self.event_evidence,
            "package_knowledge": self.package_knowledge,
        }
        if layer is BudgetLayer.CANONICAL_STATE:
            values["canonical_state"] = envelope
        elif layer is BudgetLayer.WORKING_CONTEXT:
            values["working_context"] = envelope
        elif layer is BudgetLayer.RETRIEVED_MEMORY:
            values["retrieved_memory"] = envelope
        elif layer is BudgetLayer.PACKAGE_KNOWLEDGE:
            values["package_knowledge"] = envelope
        else:
            values["event_evidence"] = envelope
        return BudgetPlan(**values)  # type: ignore[arg-type]

    def lower_protection_tiers_at_floor(self, *, before_tier: int) -> bool:
        return all(
            self.envelope_for(layer).at_floor
            for layer in BudgetLayer
            if layer.tier > before_tier
        )


@dataclass(frozen=True, slots=True)
class BudgetDegradationStep:
    """One explicit layer-envelope reduction chosen without semantic payload."""

    layer: BudgetLayer
    target: LayerEnvelope

    @property
    def tier(self) -> int:
        return self.layer.tier


@dataclass(frozen=True, slots=True)
class BudgetDegradationPolicy:
    """Caller-supplied deterministic tier-ordered envelope reductions.

    The policy validates order and monotonic reduction; it does not inspect State,
    Continuity, dialogue, MEMORY, or Event content and does not choose reduction
    amounts. Exact reduction targets are explicit caller policy inputs.
    """

    initial_plan: BudgetPlan
    steps: tuple[BudgetDegradationStep, ...]

    def __post_init__(self) -> None:
        current = self.initial_plan
        previous_tier: int | None = None
        for index, step in enumerate(self.steps):
            if previous_tier is not None and step.tier > previous_tier:
                raise ValueError(
                    "degradation cannot return to a lower-protection tier"
                )
            if not current.lower_protection_tiers_at_floor(before_tier=step.tier):
                raise ValueError(
                    f"step {index} cannot reduce tier {step.tier} before lower-protection tiers reach floors"
                )
            current = _apply_degradation_step(current, step, index=index)
            previous_tier = step.tier

    def plan_after_steps(self, count: int) -> BudgetPlan:
        _require_non_negative_count("count", count)
        if count > len(self.steps):
            raise ValueError("count must not exceed the configured degradation steps")
        current = self.initial_plan
        for index, step in enumerate(self.steps[:count]):
            current = _apply_degradation_step(current, step, index=index)
        return current

    @property
    def final_plan(self) -> BudgetPlan:
        return self.plan_after_steps(len(self.steps))


def _apply_degradation_step(
    plan: BudgetPlan,
    step: BudgetDegradationStep,
    *,
    index: int,
) -> BudgetPlan:
    current = plan.envelope_for(step.layer)
    target = step.target
    if type(target) is not type(current):
        raise TypeError(
            f"step {index} {step.layer.value} target must be {type(current).__name__}"
        )

    if isinstance(current, CountEnvelope):
        assert isinstance(target, CountEnvelope)
        if target.floor_items != current.floor_items:
            raise ValueError(f"step {index} must preserve the configured item floor")
        if target.max_items >= current.max_items:
            raise ValueError(f"step {index} must strictly reduce the layer envelope")
    else:
        assert isinstance(current, CountCharacterEnvelope)
        assert isinstance(target, CountCharacterEnvelope)
        if (
            target.floor_items != current.floor_items
            or target.floor_chars != current.floor_chars
        ):
            raise ValueError(f"step {index} must preserve configured layer floors")
        if target.max_items > current.max_items or target.max_chars > current.max_chars:
            raise ValueError(f"step {index} must not expand a layer envelope")
        if target.max_items == current.max_items and target.max_chars == current.max_chars:
            raise ValueError(f"step {index} must strictly reduce the layer envelope")

    return plan.with_envelope(step.layer, target)

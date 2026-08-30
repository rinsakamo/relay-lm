from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any, Literal

from relaylm.actual_model_evaluation import (
    ActualModelEvidence,
    ProductQualityObservation,
)

QUALITY_RUBRIC_VERSION = "actual-model-quality-v1"
PROPOSAL_EVALUATOR_VERSION = "actual-model-proposal-evaluator-v3"
QualityAxis = Literal[
    "response_coherence",
    "persona_continuity",
    "correctness",
    "unsupported_recall",
    "continuity_usefulness",
    "state_proposal_quality",
    "continuity_proposal_quality",
]
ProposalChannelScoring = Literal["scored", "unscored"]

_FAMILY_AXES: dict[str, tuple[QualityAxis, ...]] = {
    "response_persona_continuity": (
        "response_coherence",
        "persona_continuity",
        "correctness",
        "unsupported_recall",
    ),
    "continuity_proposal_quality": (
        "response_coherence",
        "continuity_usefulness",
        "continuity_proposal_quality",
    ),
    "state_candidate_quality": (
        "response_coherence",
        "state_proposal_quality",
    ),
    "cognitive_pressure_robustness": (
        "response_coherence",
        "persona_continuity",
        "correctness",
        "unsupported_recall",
        "state_proposal_quality",
        "continuity_proposal_quality",
    ),
    "restart_quality": (
        "response_coherence",
        "persona_continuity",
        "correctness",
        "continuity_usefulness",
    ),
}


@dataclass(frozen=True, slots=True)
class ProposalScoring:
    """Scenario-owned declaration of which proposal channels are evaluated."""

    state: ProposalChannelScoring = "scored"
    continuity: ProposalChannelScoring = "scored"

    def __post_init__(self) -> None:
        for name in ("state", "continuity"):
            value = getattr(self, name)
            if value not in {"scored", "unscored"}:
                raise ValueError(f"unsupported {name} proposal scoring mode: {value}")

    def to_mapping(self) -> dict[str, str]:
        return {"state": self.state, "continuity": self.continuity}


@dataclass(frozen=True, slots=True)
class TurnQualityRating:
    turn_index: int
    observations: tuple[ProductQualityObservation, ...]

    def __post_init__(self) -> None:
        if isinstance(self.turn_index, bool) or not isinstance(self.turn_index, int):
            raise TypeError("turn_index must be an integer")
        if self.turn_index <= 0:
            raise ValueError("turn_index must be positive")
        axes = tuple(item.axis for item in self.observations)
        if len(set(axes)) != len(axes):
            raise ValueError("product-quality axes must not be duplicated within a turn")


@dataclass(frozen=True, slots=True)
class StateProposalLabel:
    state_class: str
    key: str
    op: Literal["set", "remove"]
    match_value: bool = False
    value: Any = None

    def __post_init__(self) -> None:
        if not self.state_class.strip() or not self.key.strip():
            raise ValueError("State proposal labels require non-empty state_class and key")
        if self.op not in {"set", "remove"}:
            raise ValueError(f"unsupported State proposal op: {self.op}")
        if self.match_value and self.op != "set":
            raise ValueError("value matching is only valid for State set labels")
        _validate_json_value(self.value)


@dataclass(frozen=True, slots=True)
class ContinuityProposalLabel:
    kind: str
    key: str
    op: Literal["set", "resolve"]
    match_value: bool = False
    value: Any = None

    def __post_init__(self) -> None:
        if not self.kind.strip() or not self.key.strip():
            raise ValueError("Continuity proposal labels require non-empty kind and key")
        if self.op not in {"set", "resolve"}:
            raise ValueError(f"unsupported Continuity proposal op: {self.op}")
        if self.match_value and self.op != "set":
            raise ValueError("value matching is only valid for Continuity set labels")
        _validate_json_value(self.value)


@dataclass(frozen=True, slots=True)
class TurnProposalLabels:
    turn_index: int
    state: tuple[StateProposalLabel, ...] = ()
    continuity: tuple[ContinuityProposalLabel, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.turn_index, bool) or not isinstance(self.turn_index, int):
            raise TypeError("turn_index must be an integer")
        if self.turn_index <= 0:
            raise ValueError("turn_index must be positive")


@dataclass(frozen=True, slots=True)
class ProposalChannelMetrics:
    expected_count: int
    observed_count: int
    true_positive_count: int
    false_positive_count: int
    false_negative_count: int
    precision: float | None
    recall: float | None
    scored: bool = True

    def __post_init__(self) -> None:
        if not self.scored and any(
            (
                self.expected_count,
                self.observed_count,
                self.true_positive_count,
                self.false_positive_count,
                self.false_negative_count,
            )
        ):
            raise ValueError("unscored proposal metrics cannot carry scored counts")
        if not self.scored and (self.precision is not None or self.recall is not None):
            raise ValueError("unscored proposal metrics cannot carry precision/recall")

    def to_mapping(self) -> dict[str, object]:
        return {
            "scored": self.scored,
            "expected_count": self.expected_count,
            "observed_count": self.observed_count,
            "true_positive_count": self.true_positive_count,
            "false_positive_count": self.false_positive_count,
            "false_negative_count": self.false_negative_count,
            "precision": self.precision,
            "recall": self.recall,
        }


@dataclass(frozen=True, slots=True)
class LabeledProposalMetrics:
    state: ProposalChannelMetrics
    continuity: ProposalChannelMetrics
    evaluator_version: str = PROPOSAL_EVALUATOR_VERSION

    def __post_init__(self) -> None:
        if self.evaluator_version != PROPOSAL_EVALUATOR_VERSION:
            raise ValueError("proposal metrics must pin the current evaluator version")

    def to_mapping(self) -> dict[str, object]:
        return {
            "evaluator_version": self.evaluator_version,
            "state": self.state.to_mapping(),
            "continuity": self.continuity.to_mapping(),
        }


def required_quality_axes(scenario_family: str) -> tuple[QualityAxis, ...]:
    try:
        return _FAMILY_AXES[scenario_family]
    except KeyError as exc:
        raise ValueError(f"unsupported actual-model scenario family: {scenario_family}") from exc


def apply_product_quality_ratings(
    *,
    evidence: ActualModelEvidence,
    ratings: tuple[TurnQualityRating, ...],
) -> ActualModelEvidence:
    """Attach bounded human ratings without modifying raw or deterministic evidence."""

    required_axes = required_quality_axes(evidence.scenario.family)
    by_turn = {rating.turn_index: rating for rating in ratings}
    if len(by_turn) != len(ratings):
        raise ValueError("product-quality ratings must not duplicate turn_index")
    expected_turns = {turn.turn_index for turn in evidence.turns}
    if set(by_turn) != expected_turns:
        raise ValueError("product-quality ratings must cover every evidence turn exactly once")

    rated_turns = []
    for turn in evidence.turns:
        rating = by_turn[turn.turn_index]
        axes = tuple(item.axis for item in rating.observations)
        if set(axes) != set(required_axes) or len(axes) != len(required_axes):
            raise ValueError(
                f"turn {turn.turn_index} must rate exactly these axes for "
                f"{evidence.scenario.family}: {', '.join(required_axes)}"
            )
        ordered = tuple(
            next(item for item in rating.observations if item.axis == axis)
            for axis in required_axes
        )
        rated_turns.append(replace(turn, product_quality=ordered))
    return replace(evidence, turns=tuple(rated_turns))


def evaluate_labeled_proposals(
    *,
    evidence: ActualModelEvidence,
    labels: tuple[TurnProposalLabels, ...],
    scoring: ProposalScoring,
) -> LabeledProposalMetrics:
    """Score only scenario-declared proposal channels against raw model output.

    ``scored`` with an empty label collection means exactly zero proposals are
    expected and observed proposals are false positives. ``unscored`` preserves
    the raw execution evidence but excludes that channel from proposal metrics.

    State labels retain exact canonical class/key matching. A Continuity label key is
    fixture-local lifecycle identity: its first expected ``set`` may bind to a
    different non-empty model key only when deterministic runtime evidence accepted
    that candidate as a new item. Later transitions for that fixture lifecycle must
    reuse the bound model key exactly.
    """

    if not isinstance(scoring, ProposalScoring):
        raise TypeError("scoring must be ProposalScoring")
    by_turn = {item.turn_index: item for item in labels}
    if len(by_turn) != len(labels):
        raise ValueError("proposal labels must not duplicate turn_index")
    evidence_turns = {turn.turn_index for turn in evidence.turns}
    if not set(by_turn).issubset(evidence_turns):
        raise ValueError("proposal labels reference a turn that is absent from evidence")

    state_turn_metrics: list[ProposalChannelMetrics] = []
    continuity_turn_metrics: list[ProposalChannelMetrics] = []
    continuity_key_bindings: dict[str, str] = {}
    for turn in evidence.turns:
        turn_labels = by_turn.get(turn.turn_index)
        if turn_labels is None:
            continue
        if scoring.state == "scored":
            state_turn_metrics.append(
                _match_channel(
                    expected=list(turn_labels.state),
                    observed=list(turn.raw_model.state_candidates),
                    matcher=_state_matches,
                )
            )
        if scoring.continuity == "scored":
            continuity_turn_metrics.append(
                _match_continuity_channel(
                    expected=list(turn_labels.continuity),
                    observed=list(turn.raw_model.continuity_candidates),
                    decisions=list(turn.deterministic.continuity_decisions),
                    key_bindings=continuity_key_bindings,
                )
            )

    return LabeledProposalMetrics(
        state=_aggregate_channel_metrics(
            state_turn_metrics,
            scored=scoring.state == "scored",
        ),
        continuity=_aggregate_channel_metrics(
            continuity_turn_metrics,
            scored=scoring.continuity == "scored",
        ),
    )


def _aggregate_channel_metrics(
    metrics: list[ProposalChannelMetrics],
    *,
    scored: bool,
) -> ProposalChannelMetrics:
    if not scored:
        return ProposalChannelMetrics(
            expected_count=0,
            observed_count=0,
            true_positive_count=0,
            false_positive_count=0,
            false_negative_count=0,
            precision=None,
            recall=None,
            scored=False,
        )
    expected_count = sum(item.expected_count for item in metrics)
    observed_count = sum(item.observed_count for item in metrics)
    true_positive_count = sum(item.true_positive_count for item in metrics)
    false_positive_count = sum(item.false_positive_count for item in metrics)
    false_negative_count = sum(item.false_negative_count for item in metrics)
    precision = true_positive_count / observed_count if observed_count else None
    recall = true_positive_count / expected_count if expected_count else None
    return ProposalChannelMetrics(
        expected_count=expected_count,
        observed_count=observed_count,
        true_positive_count=true_positive_count,
        false_positive_count=false_positive_count,
        false_negative_count=false_negative_count,
        precision=precision,
        recall=recall,
        scored=True,
    )


def _match_channel(*, expected: list[Any], observed: list[dict[str, object]], matcher) -> ProposalChannelMetrics:
    unmatched_observed = list(range(len(observed)))
    true_positive_count = 0
    for label in expected:
        match_index = next(
            (
                index
                for index in unmatched_observed
                if matcher(label, observed[index])
            ),
            None,
        )
        if match_index is not None:
            unmatched_observed.remove(match_index)
            true_positive_count += 1

    return _channel_metrics(
        expected_count=len(expected),
        observed_count=len(observed),
        true_positive_count=true_positive_count,
        false_positive_count=len(unmatched_observed),
    )


def _match_continuity_channel(
    *,
    expected: list[ContinuityProposalLabel],
    observed: list[dict[str, object]],
    decisions: list[dict[str, object]],
    key_bindings: dict[str, str],
) -> ProposalChannelMetrics:
    unmatched_observed = list(range(len(observed)))
    true_positive_count = 0

    for label in expected:
        bound_key = key_bindings.get(label.key)
        if bound_key is None:
            match_index = next(
                (
                    index
                    for index in unmatched_observed
                    if _continuity_first_introduction_matches(
                        label,
                        observed[index],
                        decisions[index] if index < len(decisions) else None,
                    )
                ),
                None,
            )
            if match_index is not None:
                actual_key = observed[match_index].get("key")
                assert isinstance(actual_key, str) and actual_key.strip()
                key_bindings[label.key] = actual_key
        else:
            match_index = next(
                (
                    index
                    for index in unmatched_observed
                    if _continuity_matches(
                        label,
                        observed[index],
                        expected_key=bound_key,
                    )
                ),
                None,
            )

        if match_index is None:
            continue
        unmatched_observed.remove(match_index)
        true_positive_count += 1
        if label.op == "resolve":
            key_bindings.pop(label.key, None)

    return _channel_metrics(
        expected_count=len(expected),
        observed_count=len(observed),
        true_positive_count=true_positive_count,
        false_positive_count=len(unmatched_observed),
    )


def _channel_metrics(
    *,
    expected_count: int,
    observed_count: int,
    true_positive_count: int,
    false_positive_count: int,
) -> ProposalChannelMetrics:
    false_negative_count = expected_count - true_positive_count
    precision = true_positive_count / observed_count if observed_count else None
    recall = true_positive_count / expected_count if expected_count else None
    return ProposalChannelMetrics(
        expected_count=expected_count,
        observed_count=observed_count,
        true_positive_count=true_positive_count,
        false_positive_count=false_positive_count,
        false_negative_count=false_negative_count,
        precision=precision,
        recall=recall,
    )


def _state_matches(label: StateProposalLabel, observed: dict[str, object]) -> bool:
    if (
        observed.get("state_class") != label.state_class
        or observed.get("key") != label.key
        or observed.get("op") != label.op
    ):
        return False
    return not label.match_value or _json_equal(observed.get("value"), label.value)


def _continuity_first_introduction_matches(
    label: ContinuityProposalLabel,
    observed: dict[str, object],
    decision: dict[str, object] | None,
) -> bool:
    actual_key = observed.get("key")
    if (
        label.op != "set"
        or not isinstance(actual_key, str)
        or not actual_key.strip()
        or decision is None
        or not _json_equal(decision.get("candidate"), observed)
        or decision.get("status") != "accepted"
        or decision.get("action") != "admit"
    ):
        return False
    return _continuity_matches(label, observed, expected_key=actual_key)


def _continuity_matches(
    label: ContinuityProposalLabel,
    observed: dict[str, object],
    *,
    expected_key: str,
) -> bool:
    if (
        observed.get("kind") != label.kind
        or observed.get("key") != expected_key
        or observed.get("op") != label.op
    ):
        return False
    return not label.match_value or _json_equal(observed.get("value"), label.value)


def _json_equal(left: Any, right: Any) -> bool:
    return json.dumps(left, ensure_ascii=False, allow_nan=False, sort_keys=True) == json.dumps(
        right,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
    )


def _validate_json_value(value: Any) -> None:
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError("proposal label value must be JSON-serializable and finite") from exc

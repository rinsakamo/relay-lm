from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any, Literal

from relaylm.actual_model_evaluation import (
    ActualModelEvidence,
    ProductQualityObservation,
)

QUALITY_RUBRIC_VERSION = "actual-model-quality-v1"
QualityAxis = Literal[
    "response_coherence",
    "persona_continuity",
    "correctness",
    "unsupported_recall",
    "continuity_usefulness",
    "state_proposal_quality",
    "continuity_proposal_quality",
]

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
    op: Literal["set", "remove"]
    match_value: bool = False
    value: Any = None

    def __post_init__(self) -> None:
        if not self.kind.strip() or not self.key.strip():
            raise ValueError("Continuity proposal labels require non-empty kind and key")
        if self.op not in {"set", "remove"}:
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

    def to_mapping(self) -> dict[str, object]:
        return {
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

    def to_mapping(self) -> dict[str, object]:
        return {
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
) -> LabeledProposalMetrics:
    """Compute raw-proposal precision/recall where the semantic fixture is labeled."""

    by_turn = {item.turn_index: item for item in labels}
    if len(by_turn) != len(labels):
        raise ValueError("proposal labels must not duplicate turn_index")
    evidence_turns = {turn.turn_index for turn in evidence.turns}
    if not set(by_turn).issubset(evidence_turns):
        raise ValueError("proposal labels reference a turn that is absent from evidence")

    expected_state: list[StateProposalLabel] = []
    observed_state: list[dict[str, object]] = []
    expected_continuity: list[ContinuityProposalLabel] = []
    observed_continuity: list[dict[str, object]] = []
    for turn in evidence.turns:
        turn_labels = by_turn.get(turn.turn_index)
        if turn_labels is None:
            continue
        expected_state.extend(turn_labels.state)
        observed_state.extend(turn.raw_model.state_candidates)
        expected_continuity.extend(turn_labels.continuity)
        observed_continuity.extend(turn.raw_model.continuity_candidates)

    return LabeledProposalMetrics(
        state=_match_channel(
            expected=expected_state,
            observed=observed_state,
            matcher=_state_matches,
        ),
        continuity=_match_channel(
            expected=expected_continuity,
            observed=observed_continuity,
            matcher=_continuity_matches,
        ),
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

    false_positive_count = len(unmatched_observed)
    false_negative_count = len(expected) - true_positive_count
    precision = (
        true_positive_count / len(observed)
        if observed
        else None
    )
    recall = (
        true_positive_count / len(expected)
        if expected
        else None
    )
    return ProposalChannelMetrics(
        expected_count=len(expected),
        observed_count=len(observed),
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


def _continuity_matches(
    label: ContinuityProposalLabel, observed: dict[str, object]
) -> bool:
    if (
        observed.get("kind") != label.kind
        or observed.get("key") != label.key
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

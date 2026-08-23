from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from relaylm.actual_model_evaluation import ActualModelEvidence
from relaylm.actual_model_execution import ActualModelScenarioExecutionResult
from relaylm.actual_model_execution_artifacts import (
    ActualModelExecutionArtifactError,
    validate_actual_model_execution_result,
)
from relaylm.actual_model_quality import (
    QUALITY_RUBRIC_VERSION,
    LabeledProposalMetrics,
    TurnQualityRating,
    apply_product_quality_ratings,
    evaluate_labeled_proposals,
)
from relaylm.actual_model_restart import ActualModelRestartEvidence

LEGACY_ACTUAL_MODEL_REVIEW_FORMAT_VERSION = 2
LEGACY_STAGE_R_REVIEW_PROTOCOL_VERSION = "actual-model-stage-r-review-v1"
ACTUAL_MODEL_REVIEW_FORMAT_VERSION = 3
STAGE_R_REVIEW_PROTOCOL_VERSION = "actual-model-stage-r-review-v2"
StageRReviewDimension = Literal[
    "relevance_correctness",
    "naturalness",
    "persona_style_consistency",
    "coherence",
    "governed_context_continuity",
    "verbosity_fit",
    "language_preservation",
    "multilingual_code_switch_robustness",
    "unsupported_recall",
    "protocol_schema_validity",
    "semantic_precision_recall",
    "grounding",
    "source_subject_attribution",
    "assistant_to_user_contamination",
    "correction_supersession",
    "negation_polarity",
    "uncertainty_preservation",
    "comparative_degree_preservation",
    "transient_durable_classification",
    "canonical_class_key_reuse",
    "noop_correctness",
    "proposal_churn",
    "hallucinated_proposals",
    "source_event_validity",
]
StageRReviewOutcome = Literal["pass", "fail", "not_rated"]
CharacterRealizationOutcome = Literal[
    "normal",
    "odd_but_character_plausible",
    "out_of_character",
    "system_defect",
]

_STAGE_R_REVIEW_DIMENSIONS: tuple[StageRReviewDimension, ...] = (
    "relevance_correctness",
    "naturalness",
    "persona_style_consistency",
    "coherence",
    "governed_context_continuity",
    "verbosity_fit",
    "language_preservation",
    "multilingual_code_switch_robustness",
    "unsupported_recall",
    "protocol_schema_validity",
    "semantic_precision_recall",
    "grounding",
    "source_subject_attribution",
    "assistant_to_user_contamination",
    "correction_supersession",
    "negation_polarity",
    "uncertainty_preservation",
    "comparative_degree_preservation",
    "transient_durable_classification",
    "canonical_class_key_reuse",
    "noop_correctness",
    "proposal_churn",
    "hallucinated_proposals",
    "source_event_validity",
)
_CHARACTER_REALIZATION_OUTCOMES: tuple[CharacterRealizationOutcome, ...] = (
    "normal",
    "odd_but_character_plausible",
    "out_of_character",
    "system_defect",
)


class ActualModelExecutionReviewError(RuntimeError):
    """A product-quality review or review artifact is malformed or conflicting."""


@dataclass(frozen=True, slots=True)
class StageRReviewObservation:
    """One independent Stage R product-quality observation."""

    dimension: StageRReviewDimension
    outcome: StageRReviewOutcome
    note: str | None = None

    def __post_init__(self) -> None:
        if self.dimension not in _STAGE_R_REVIEW_DIMENSIONS:
            raise ValueError(f"unsupported Stage R review dimension: {self.dimension}")
        if self.outcome not in {"pass", "fail", "not_rated"}:
            raise ValueError(f"unsupported Stage R review outcome: {self.outcome}")

    def to_mapping(self) -> dict[str, object]:
        return {
            "dimension": self.dimension,
            "outcome": self.outcome,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class CharacterRealizationObservation:
    """One turn-local Character-realization classification for Stage R review."""

    turn_index: int
    outcome: CharacterRealizationOutcome
    note: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.turn_index, bool) or not isinstance(self.turn_index, int):
            raise TypeError("Character realization turn_index must be int")
        if self.turn_index <= 0:
            raise ValueError("Character realization turn_index must be positive")
        if self.outcome not in _CHARACTER_REALIZATION_OUTCOMES:
            raise ValueError(
                f"unsupported Character realization outcome: {self.outcome}"
            )

    def to_mapping(self) -> dict[str, object]:
        return {
            "turn_index": self.turn_index,
            "outcome": self.outcome,
            "note": self.note,
        }


def required_stage_r_review_dimensions() -> tuple[StageRReviewDimension, ...]:
    """Return the independent Stage R dimensions required by current #1386 authority."""

    return _STAGE_R_REVIEW_DIMENSIONS


def normalize_stage_r_review_observations(
    observations: tuple[StageRReviewObservation, ...],
) -> tuple[StageRReviewObservation, ...]:
    """Require exact Stage R dimension coverage and return canonical ordering."""

    if not all(isinstance(item, StageRReviewObservation) for item in observations):
        raise TypeError("Stage R review observations must be StageRReviewObservation values")
    dimensions = tuple(item.dimension for item in observations)
    if len(set(dimensions)) != len(dimensions):
        raise ValueError("Stage R review observations must not duplicate dimensions")
    if set(dimensions) != set(_STAGE_R_REVIEW_DIMENSIONS):
        raise ValueError("Stage R review observations must cover every required Stage R review dimension")
    by_dimension = {item.dimension: item for item in observations}
    return tuple(by_dimension[dimension] for dimension in _STAGE_R_REVIEW_DIMENSIONS)


def normalize_character_realization_observations(
    observations: tuple[CharacterRealizationObservation, ...],
    *,
    turn_count: int,
) -> tuple[CharacterRealizationObservation, ...]:
    """Require exactly one Character-realization classification per evidence turn."""

    if isinstance(turn_count, bool) or not isinstance(turn_count, int):
        raise TypeError("Character realization turn_count must be int")
    if turn_count <= 0:
        raise ValueError("Character realization turn_count must be positive")
    if not all(isinstance(item, CharacterRealizationObservation) for item in observations):
        raise TypeError(
            "Character realization observations must be CharacterRealizationObservation values"
        )
    turns = tuple(item.turn_index for item in observations)
    if len(set(turns)) != len(turns):
        raise ValueError("Character realization observations must not duplicate turns")
    expected_turns = set(range(1, turn_count + 1))
    if set(turns) != expected_turns:
        raise ValueError(
            "Character realization observations must cover every evidence turn exactly once"
        )
    by_turn = {item.turn_index: item for item in observations}
    return tuple(by_turn[turn_index] for turn_index in range(1, turn_count + 1))


def _unrated_stage_r_review_observations() -> tuple[StageRReviewObservation, ...]:
    return tuple(
        StageRReviewObservation(dimension=dimension, outcome="not_rated")
        for dimension in _STAGE_R_REVIEW_DIMENSIONS
    )


@dataclass(frozen=True, slots=True)
class ActualModelExecutionReview:
    """Citable human/product-quality sidecar for one immutable execution result."""

    review_id: str
    execution_id: str
    run_id: str
    scenario_set_revision: str
    scenario_id: str
    scenario_family: str
    reviewer_identity: str
    turn_ratings: tuple[TurnQualityRating, ...]
    proposal_metrics: LabeledProposalMetrics
    stage_r_observations: tuple[StageRReviewObservation, ...]
    character_realization_observations: tuple[CharacterRealizationObservation, ...]
    quality_rubric_version: str = QUALITY_RUBRIC_VERSION
    stage_r_review_protocol_version: str = STAGE_R_REVIEW_PROTOCOL_VERSION
    format_version: int = ACTUAL_MODEL_REVIEW_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_REVIEW_FORMAT_VERSION:
            raise ValueError(
                f"unsupported actual-model review format_version: {self.format_version}"
            )
        if self.quality_rubric_version != QUALITY_RUBRIC_VERSION:
            raise ValueError("review must pin the current actual-model quality rubric")
        if self.stage_r_review_protocol_version != STAGE_R_REVIEW_PROTOCOL_VERSION:
            raise ValueError("review must pin the current Stage R review protocol")
        normalized = normalize_stage_r_review_observations(self.stage_r_observations)
        if normalized != self.stage_r_observations:
            raise ValueError("Stage R review observations must use canonical dimension order")
        if not self.character_realization_observations:
            raise ValueError("current review requires Character realization observations")
        normalized_character = normalize_character_realization_observations(
            self.character_realization_observations,
            turn_count=max(
                item.turn_index for item in self.character_realization_observations
            ),
        )
        if normalized_character != self.character_realization_observations:
            raise ValueError(
                "Character realization observations must use canonical turn order"
            )
        if self.turn_ratings:
            rating_turns = tuple(rating.turn_index for rating in self.turn_ratings)
            realization_turns = tuple(
                item.turn_index for item in self.character_realization_observations
            )
            if rating_turns != realization_turns:
                raise ValueError(
                    "Character realization observations must match reviewed turn indexes"
                )
        for name in (
            "review_id",
            "execution_id",
            "run_id",
            "scenario_set_revision",
            "scenario_id",
            "scenario_family",
            "reviewer_identity",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "review_id": self.review_id,
            "execution_id": self.execution_id,
            "run_id": self.run_id,
            "scenario_set_revision": self.scenario_set_revision,
            "scenario_id": self.scenario_id,
            "scenario_family": self.scenario_family,
            "reviewer_identity": self.reviewer_identity,
            "quality_rubric_version": self.quality_rubric_version,
            "turn_ratings": [
                {
                    "turn_index": rating.turn_index,
                    "observations": [
                        observation.to_mapping()
                        for observation in rating.observations
                    ],
                }
                for rating in self.turn_ratings
            ],
            "proposal_metrics": self.proposal_metrics.to_mapping(),
            "stage_r_review": {
                "protocol_version": self.stage_r_review_protocol_version,
                "observations": [
                    observation.to_mapping()
                    for observation in self.stage_r_observations
                ],
            },
            "character_realization": {
                "observations": [
                    observation.to_mapping()
                    for observation in self.character_realization_observations
                ],
            },
            "score": None,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )


def review_actual_model_execution(
    *,
    result: ActualModelScenarioExecutionResult,
    reviewer_identity: str,
    ratings: tuple[TurnQualityRating, ...],
    character_realization_observations: tuple[CharacterRealizationObservation, ...],
    stage_r_observations: tuple[StageRReviewObservation, ...] | None = None,
) -> ActualModelExecutionReview:
    """Validate bounded human ratings and fixture-owned proposal metrics together."""

    if not reviewer_identity.strip():
        raise ValueError("reviewer_identity must not be empty")
    try:
        validate_actual_model_execution_result(result)
    except (ActualModelExecutionArtifactError, TypeError) as exc:
        raise ActualModelExecutionReviewError(
            f"source execution is not citable: {exc}"
        ) from exc

    evidence = _review_evidence_view(result)
    rated = apply_product_quality_ratings(evidence=evidence, ratings=ratings)
    normalized_ratings = tuple(
        TurnQualityRating(
            turn_index=turn.turn_index,
            observations=turn.product_quality,
        )
        for turn in rated.turns
    )
    proposal_metrics = evaluate_labeled_proposals(
        evidence=evidence,
        labels=result.plan.definition.proposal_labels,
    )
    normalized_stage_r = normalize_stage_r_review_observations(
        _unrated_stage_r_review_observations()
        if stage_r_observations is None
        else stage_r_observations
    )
    normalized_character_realization = normalize_character_realization_observations(
        character_realization_observations,
        turn_count=len(evidence.turns),
    )
    identity = {
        "format_version": ACTUAL_MODEL_REVIEW_FORMAT_VERSION,
        "execution_id": result.execution_id,
        "run_id": result.run_id,
        "scenario_set_revision": result.plan.scenario_set_revision,
        "scenario_id": result.plan.definition.scenario.scenario_id,
        "scenario_family": result.plan.definition.scenario.family,
        "reviewer_identity": reviewer_identity,
        "quality_rubric_version": QUALITY_RUBRIC_VERSION,
        "turn_ratings": [
            {
                "turn_index": rating.turn_index,
                "observations": [
                    observation.to_mapping()
                    for observation in rating.observations
                ],
            }
            for rating in normalized_ratings
        ],
        "proposal_metrics": proposal_metrics.to_mapping(),
        "stage_r_review": {
            "protocol_version": STAGE_R_REVIEW_PROTOCOL_VERSION,
            "observations": [
                observation.to_mapping()
                for observation in normalized_stage_r
            ],
        },
        "character_realization": {
            "observations": [
                observation.to_mapping()
                for observation in normalized_character_realization
            ],
        },
    }
    review_id = _stable_review_id(identity)
    return ActualModelExecutionReview(
        review_id=review_id,
        execution_id=result.execution_id,
        run_id=result.run_id,
        scenario_set_revision=result.plan.scenario_set_revision,
        scenario_id=result.plan.definition.scenario.scenario_id,
        scenario_family=result.plan.definition.scenario.family,
        reviewer_identity=reviewer_identity,
        turn_ratings=normalized_ratings,
        proposal_metrics=proposal_metrics,
        stage_r_observations=normalized_stage_r,
        character_realization_observations=normalized_character_realization,
    )


def write_actual_model_execution_review(
    *,
    review: ActualModelExecutionReview,
    artifact_root: str | Path,
) -> Path:
    """Persist one immutable review sidecar without mutating raw execution evidence."""

    identity = review.to_mapping()
    identity.pop("review_id")
    identity.pop("score")
    if review.review_id != _stable_review_id(identity):
        raise ActualModelExecutionReviewError(
            "review_id does not match review evidence"
        )

    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{review.review_id}.review.json"
    payload = review.to_json() + "\n"
    if path.exists():
        return _resolve_existing_review(path=path, payload=payload)

    temporary = root / f".{review.review_id}.{os.getpid()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return _resolve_existing_review(path=path, payload=payload)
    except OSError as exc:
        raise ActualModelExecutionReviewError(
            f"cannot persist actual-model execution review: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def load_actual_model_execution_review_mapping(
    path: str | Path,
) -> dict[str, object]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActualModelExecutionReviewError(
            f"cannot load actual-model execution review: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise ActualModelExecutionReviewError(
            "actual-model execution review root must be a JSON object"
        )
    return raw


def _review_evidence_view(
    result: ActualModelScenarioExecutionResult,
) -> ActualModelEvidence:
    evidence = result.evidence
    if isinstance(evidence, ActualModelEvidence):
        return evidence
    if not isinstance(evidence, ActualModelRestartEvidence):
        raise TypeError("unsupported actual-model execution evidence type")

    definition = result.plan.definition
    split = evidence.manifest.restart_after_turn_count
    if definition.restart_after_turn_count != split:
        raise ValueError(
            "restart evidence boundary does not match scenario definition"
        )
    original = definition.scenario
    if len(evidence.before_restart.turns) != split:
        raise ValueError("restart evidence before phase does not match its boundary")
    expected_after_count = len(original.turns) - split
    if len(evidence.after_restart.turns) != expected_after_count:
        raise ValueError("restart evidence after phase does not match its boundary")

    turns = [
        replace(
            turn,
            turn_index=index,
            input=original.turns[index - 1],
            product_quality=(),
        )
        for index, turn in enumerate(evidence.before_restart.turns, start=1)
    ]
    turns.extend(
        replace(
            turn,
            turn_index=split + local_index,
            input=original.turns[split + local_index - 1],
            product_quality=(),
        )
        for local_index, turn in enumerate(evidence.after_restart.turns, start=1)
    )
    return ActualModelEvidence(
        run_id=evidence.run_id,
        manifest=evidence.manifest.base,
        scenario=original,
        turns=tuple(turns),
    )


def _stable_review_id(identity: dict[str, object]) -> str:
    payload = json.dumps(
        identity,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"amv-{hashlib.sha256(payload).hexdigest()}"


def _resolve_existing_review(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelExecutionReviewError(
            f"cannot read existing actual-model execution review: {exc}"
        ) from exc
    if existing == payload:
        return path
    raise ActualModelExecutionReviewError(
        "review ID already exists with different review evidence"
    )

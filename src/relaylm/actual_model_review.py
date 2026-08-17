from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, replace
from pathlib import Path

from relaylm.actual_model_evaluation import (
    ActualModelEvidence,
    ProductQualityObservation,
)
from relaylm.actual_model_execution import ActualModelScenarioExecutionResult
from relaylm.actual_model_quality import (
    QUALITY_RUBRIC_VERSION,
    LabeledProposalMetrics,
    TurnQualityRating,
    apply_product_quality_ratings,
    evaluate_labeled_proposals,
)
from relaylm.actual_model_restart import ActualModelRestartEvidence

ACTUAL_MODEL_REVIEW_FORMAT_VERSION = 1


class ActualModelExecutionReviewError(RuntimeError):
    """A product-quality review or review artifact is malformed or conflicting."""


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
    quality_rubric_version: str = QUALITY_RUBRIC_VERSION
    format_version: int = ACTUAL_MODEL_REVIEW_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_REVIEW_FORMAT_VERSION:
            raise ValueError(
                f"unsupported actual-model review format_version: {self.format_version}"
            )
        if self.quality_rubric_version != QUALITY_RUBRIC_VERSION:
            raise ValueError("review must pin the current actual-model quality rubric")
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
) -> ActualModelExecutionReview:
    """Validate bounded human ratings and fixture-owned proposal metrics together."""

    if not reviewer_identity.strip():
        raise ValueError("reviewer_identity must not be empty")

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
    )


def write_actual_model_execution_review(
    *,
    review: ActualModelExecutionReview,
    artifact_root: str | Path,
) -> Path:
    """Persist one immutable review sidecar without mutating raw execution evidence."""

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

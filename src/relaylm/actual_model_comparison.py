from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from relaylm.actual_model_artifacts import run_actual_model_fixture
from relaylm.actual_model_evaluation import (
    ActualModelEvidence,
    ActualModelRunManifest,
    ActualModelScenario,
)
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveProvider


@dataclass(frozen=True, slots=True)
class ProposalObservationSummary:
    """Boundary-level counts only; this is not a product-quality score."""

    turn_count: int
    response_character_count: int
    state_candidate_count: int
    rejected_state_candidate_count: int
    continuity_candidate_count: int
    rejected_continuity_candidate_count: int
    bounded_budget_failure_count: int

    def to_mapping(self) -> dict[str, int]:
        return {
            "turn_count": self.turn_count,
            "response_character_count": self.response_character_count,
            "state_candidate_count": self.state_candidate_count,
            "rejected_state_candidate_count": self.rejected_state_candidate_count,
            "continuity_candidate_count": self.continuity_candidate_count,
            "rejected_continuity_candidate_count": self.rejected_continuity_candidate_count,
            "bounded_budget_failure_count": self.bounded_budget_failure_count,
        }


@dataclass(frozen=True, slots=True)
class ProposalObservationDelta:
    """Pressure minus baseline counts; positive is not defined as better or worse."""

    response_character_count: int
    state_candidate_count: int
    rejected_state_candidate_count: int
    continuity_candidate_count: int
    rejected_continuity_candidate_count: int
    bounded_budget_failure_count: int

    def to_mapping(self) -> dict[str, int]:
        return {
            "response_character_count": self.response_character_count,
            "state_candidate_count": self.state_candidate_count,
            "rejected_state_candidate_count": self.rejected_state_candidate_count,
            "continuity_candidate_count": self.continuity_candidate_count,
            "rejected_continuity_candidate_count": self.rejected_continuity_candidate_count,
            "bounded_budget_failure_count": self.bounded_budget_failure_count,
        }


@dataclass(frozen=True, slots=True)
class ActualModelConditionComparisonEvidence:
    comparison_id: str
    scenario: ActualModelScenario
    baseline: ActualModelEvidence
    pressure: ActualModelEvidence
    baseline_summary: ProposalObservationSummary
    pressure_summary: ProposalObservationSummary
    pressure_minus_baseline: ProposalObservationDelta

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": 1,
            "comparison_id": self.comparison_id,
            "scenario": self.scenario.to_mapping(),
            "baseline": self.baseline.to_mapping(),
            "pressure": self.pressure.to_mapping(),
            "baseline_summary": self.baseline_summary.to_mapping(),
            "pressure_summary": self.pressure_summary.to_mapping(),
            "pressure_minus_baseline": self.pressure_minus_baseline.to_mapping(),
            "score": None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_mapping(), ensure_ascii=False, allow_nan=False, indent=2)


async def run_actual_model_condition_comparison(
    *,
    fixture_root: str | Path,
    workspace_root: str | Path,
    baseline_provider: CognitiveProvider,
    pressure_provider: CognitiveProvider,
    baseline_manifest: ActualModelRunManifest,
    pressure_manifest: ActualModelRunManifest,
    scenario: ActualModelScenario,
    baseline_cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
    pressure_cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
) -> ActualModelConditionComparisonEvidence:
    """Run the identical semantic fixture under two explicit budget conditions."""

    if scenario.family != "cognitive_pressure_robustness":
        raise ValueError(
            "condition comparison requires scenario.family='cognitive_pressure_robustness'"
        )
    _validate_comparable_manifests(
        baseline=baseline_manifest,
        pressure=pressure_manifest,
    )

    root = Path(workspace_root)
    baseline = await run_actual_model_fixture(
        fixture_root=fixture_root,
        workspace_root=root / "baseline",
        provider=baseline_provider,
        manifest=baseline_manifest,
        scenario=scenario,
        cognitive_budget=baseline_cognitive_budget,
    )
    pressure = await run_actual_model_fixture(
        fixture_root=fixture_root,
        workspace_root=root / "pressure",
        provider=pressure_provider,
        manifest=pressure_manifest,
        scenario=scenario,
        cognitive_budget=pressure_cognitive_budget,
    )
    baseline_summary = summarize_proposal_observations(baseline)
    pressure_summary = summarize_proposal_observations(pressure)
    return ActualModelConditionComparisonEvidence(
        comparison_id=stable_condition_comparison_id(
            baseline_manifest=baseline_manifest,
            pressure_manifest=pressure_manifest,
            scenario=scenario,
        ),
        scenario=scenario,
        baseline=baseline,
        pressure=pressure,
        baseline_summary=baseline_summary,
        pressure_summary=pressure_summary,
        pressure_minus_baseline=_delta(
            baseline=baseline_summary,
            pressure=pressure_summary,
        ),
    )


def summarize_proposal_observations(evidence: ActualModelEvidence) -> ProposalObservationSummary:
    return ProposalObservationSummary(
        turn_count=len(evidence.turns),
        response_character_count=sum(len(turn.raw_model.response) for turn in evidence.turns),
        state_candidate_count=sum(
            len(turn.raw_model.state_candidates) for turn in evidence.turns
        ),
        rejected_state_candidate_count=sum(
            decision["status"] == "rejected"
            for turn in evidence.turns
            for decision in turn.deterministic.state_decisions
        ),
        continuity_candidate_count=sum(
            len(turn.raw_model.continuity_candidates) for turn in evidence.turns
        ),
        rejected_continuity_candidate_count=sum(
            decision["status"] == "rejected"
            for turn in evidence.turns
            for decision in turn.deterministic.continuity_decisions
        ),
        bounded_budget_failure_count=int(evidence.bounded_failure is not None),
    )


def stable_condition_comparison_id(
    *,
    baseline_manifest: ActualModelRunManifest,
    pressure_manifest: ActualModelRunManifest,
    scenario: ActualModelScenario,
) -> str:
    _validate_comparable_manifests(
        baseline=baseline_manifest,
        pressure=pressure_manifest,
    )
    payload = json.dumps(
        {
            "baseline_manifest": baseline_manifest.to_mapping(),
            "pressure_manifest": pressure_manifest.to_mapping(),
            "scenario": scenario.to_mapping(),
        },
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"amc-{hashlib.sha256(payload).hexdigest()}"


def _validate_comparable_manifests(
    *, baseline: ActualModelRunManifest, pressure: ActualModelRunManifest
) -> None:
    if baseline.condition_id == pressure.condition_id:
        raise ValueError("baseline and pressure condition_id values must differ")

    baseline_total_budget = baseline.cognitive_budget is not None
    pressure_total_budget = pressure.cognitive_budget is not None
    if baseline_total_budget != pressure_total_budget:
        raise ValueError(
            "baseline and pressure must use the same budget-control mode"
        )
    if baseline_total_budget:
        if baseline.cognitive_budget == pressure.cognitive_budget:
            raise ValueError(
                "baseline and pressure cognitive budget configurations must differ"
            )
    elif baseline.budgets == pressure.budgets:
        raise ValueError("baseline and pressure explicit budget configurations must differ")

    baseline_identity = baseline.to_mapping()
    pressure_identity = pressure.to_mapping()
    for mapping in (baseline_identity, pressure_identity):
        mapping.pop("condition_id")
        mapping.pop("budgets")
        mapping.pop("cognitive_budget")
    if baseline_identity != pressure_identity:
        raise ValueError(
            "baseline and pressure runs may differ only by condition_id and explicit budgets"
        )


def _delta(
    *, baseline: ProposalObservationSummary, pressure: ProposalObservationSummary
) -> ProposalObservationDelta:
    return ProposalObservationDelta(
        response_character_count=(
            pressure.response_character_count - baseline.response_character_count
        ),
        state_candidate_count=pressure.state_candidate_count - baseline.state_candidate_count,
        rejected_state_candidate_count=(
            pressure.rejected_state_candidate_count - baseline.rejected_state_candidate_count
        ),
        continuity_candidate_count=(
            pressure.continuity_candidate_count - baseline.continuity_candidate_count
        ),
        rejected_continuity_candidate_count=(
            pressure.rejected_continuity_candidate_count
            - baseline.rejected_continuity_candidate_count
        ),
        bounded_budget_failure_count=(
            pressure.bounded_budget_failure_count
            - baseline.bounded_budget_failure_count
        ),
    )

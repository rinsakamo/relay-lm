from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from relaylm.actual_model_comparison import (
    ActualModelConditionComparisonEvidence,
    run_actual_model_condition_comparison,
    stable_condition_comparison_id,
    summarize_proposal_observations,
)
from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    stable_actual_model_run_id,
)
from relaylm.actual_model_execution import (
    ActualModelScenarioExecutionPlan,
    _stable_plan_id,
    plan_actual_model_scenario_execution,
)
from relaylm.actual_model_execution_artifacts import (
    ActualModelExecutionArtifactError,
    validate_actual_model_execution_plan,
)
from relaylm.actual_model_scenarios import (
    ActualModelScenarioDefinition,
    ActualModelScenarioSet,
)
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveProvider

ACTUAL_MODEL_PRESSURE_FORMAT_VERSION = 1


class ActualModelPressureArtifactError(RuntimeError):
    """A scenario-bound pressure comparison artifact is malformed or conflicting."""


@dataclass(frozen=True, slots=True)
class ActualModelScenarioPressureComparison:
    """Citable baseline/pressure evidence bound to one full scenario-set definition."""

    pressure_comparison_id: str
    scenario_set_version: str
    scenario_set_revision: str
    definition: ActualModelScenarioDefinition
    baseline_plan: ActualModelScenarioExecutionPlan
    pressure_plan: ActualModelScenarioExecutionPlan
    comparison: ActualModelConditionComparisonEvidence
    format_version: int = ACTUAL_MODEL_PRESSURE_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_PRESSURE_FORMAT_VERSION:
            raise ValueError(
                f"unsupported actual-model pressure format_version: {self.format_version}"
            )
        if not self.pressure_comparison_id.strip():
            raise ValueError("pressure_comparison_id must not be empty")
        if self.definition.scenario.family != "cognitive_pressure_robustness":
            raise ValueError("scenario-bound pressure comparison requires pressure family")
        if self.baseline_plan.definition != self.definition:
            raise ValueError("baseline plan definition does not match pressure definition")
        if self.pressure_plan.definition != self.definition:
            raise ValueError("pressure plan definition does not match pressure definition")
        if self.comparison.scenario != self.definition.scenario:
            raise ValueError("condition comparison scenario does not match pressure definition")

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "pressure_comparison_id": self.pressure_comparison_id,
            "scenario_set": {
                "version": self.scenario_set_version,
                "revision": self.scenario_set_revision,
            },
            "scenario_definition": self.definition.to_mapping(),
            "baseline_plan": self.baseline_plan.to_mapping(),
            "pressure_plan": self.pressure_plan.to_mapping(),
            "comparison": self.comparison.to_mapping(),
            "score": None,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )


async def run_actual_model_scenario_pressure_comparison(
    *,
    scenario_set: ActualModelScenarioSet,
    scenario_id: str,
    fixture_root: str | Path,
    workspace_root: str | Path,
    baseline_provider: CognitiveProvider,
    pressure_provider: CognitiveProvider,
    baseline_manifest: ActualModelRunManifest,
    pressure_manifest: ActualModelRunManifest,
    baseline_cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
    pressure_cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
) -> ActualModelScenarioPressureComparison:
    """Run a preflighted same-definition comparison under explicit budget conditions."""

    try:
        definition = scenario_set.scenario(scenario_id)
    except KeyError as exc:
        raise ValueError(f"scenario is not present in scenario set: {scenario_id}") from exc
    if definition.scenario.family != "cognitive_pressure_robustness":
        raise ValueError(
            "scenario-bound condition comparison requires "
            "family='cognitive_pressure_robustness'"
        )

    # Preflight both conditions before any model call or mutable workspace creation.
    baseline_plan = plan_actual_model_scenario_execution(
        scenario_set=scenario_set,
        scenario_id=scenario_id,
        fixture_root=fixture_root,
        manifest=baseline_manifest,
    )
    pressure_plan = plan_actual_model_scenario_execution(
        scenario_set=scenario_set,
        scenario_id=scenario_id,
        fixture_root=fixture_root,
        manifest=pressure_manifest,
    )
    for label, provider, manifest in (
        ("baseline", baseline_provider, baseline_manifest),
        ("pressure", pressure_provider, pressure_manifest),
    ):
        if manifest.execution_path == "streaming" and not callable(
            getattr(provider, "stream_generate", None)
        ):
            raise ValueError(
                f"{label} provider declares streaming execution but has no "
                "stream_generate implementation"
            )

    comparison = await run_actual_model_condition_comparison(
        fixture_root=fixture_root,
        workspace_root=workspace_root,
        baseline_provider=baseline_provider,
        pressure_provider=pressure_provider,
        baseline_manifest=baseline_manifest,
        pressure_manifest=pressure_manifest,
        scenario=definition.scenario,
        baseline_cognitive_budget=baseline_cognitive_budget,
        pressure_cognitive_budget=pressure_cognitive_budget,
    )
    identity = _pressure_comparison_identity(
        format_version=ACTUAL_MODEL_PRESSURE_FORMAT_VERSION,
        scenario_set_version=scenario_set.scenario_set_version,
        scenario_set_revision=scenario_set.revision,
        definition=definition,
        baseline_plan=baseline_plan,
        pressure_plan=pressure_plan,
        comparison=comparison,
    )
    return ActualModelScenarioPressureComparison(
        pressure_comparison_id=_stable_pressure_id(identity),
        scenario_set_version=scenario_set.scenario_set_version,
        scenario_set_revision=scenario_set.revision,
        definition=definition,
        baseline_plan=baseline_plan,
        pressure_plan=pressure_plan,
        comparison=comparison,
    )


def write_actual_model_scenario_pressure_comparison(
    *,
    comparison: ActualModelScenarioPressureComparison,
    artifact_root: str | Path,
) -> Path:
    """Persist one immutable scenario-bound pressure comparison artifact."""

    _validate_pressure_scenario_set_envelope(comparison)
    _validate_pressure_plan_ids(comparison)
    _validate_pressure_plan_metadata(comparison)
    _validate_condition_comparison_binding(comparison)
    _validate_derived_observations(comparison.comparison)
    identity = _pressure_comparison_identity(
        format_version=comparison.format_version,
        scenario_set_version=comparison.scenario_set_version,
        scenario_set_revision=comparison.scenario_set_revision,
        definition=comparison.definition,
        baseline_plan=comparison.baseline_plan,
        pressure_plan=comparison.pressure_plan,
        comparison=comparison.comparison,
    )
    if comparison.pressure_comparison_id != _stable_pressure_id(identity):
        raise ActualModelPressureArtifactError(
            "pressure_comparison_id does not match pressure evidence"
        )

    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{comparison.pressure_comparison_id}.pressure.json"
    payload = comparison.to_json() + "\n"
    if path.exists():
        return _resolve_existing(path=path, payload=payload)

    temporary = root / f".{comparison.pressure_comparison_id}.{os.getpid()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return _resolve_existing(path=path, payload=payload)
    except OSError as exc:
        raise ActualModelPressureArtifactError(
            f"cannot persist actual-model pressure comparison: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def load_actual_model_scenario_pressure_mapping(path: str | Path) -> dict[str, object]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActualModelPressureArtifactError(
            f"cannot load actual-model pressure comparison: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise ActualModelPressureArtifactError(
            "actual-model pressure comparison root must be a JSON object"
        )
    return raw


def _validate_pressure_scenario_set_envelope(
    pressure: ActualModelScenarioPressureComparison,
) -> None:
    for plan in (pressure.baseline_plan, pressure.pressure_plan):
        if (
            plan.scenario_set_version != pressure.scenario_set_version
            or plan.scenario_set_revision != pressure.scenario_set_revision
        ):
            raise ActualModelPressureArtifactError(
                "pressure scenario-set envelope does not match embedded plans"
            )


def _validate_pressure_plan_ids(
    pressure: ActualModelScenarioPressureComparison,
) -> None:
    for plan in (pressure.baseline_plan, pressure.pressure_plan):
        expected_plan_id = _stable_plan_id(
            scenario_set_version=plan.scenario_set_version,
            scenario_set_revision=plan.scenario_set_revision,
            character_fixture_id=plan.character_fixture_id,
            character_fixture_revision=plan.character_fixture_revision,
            definition=plan.definition,
            manifest=plan.manifest,
        )
        if plan.plan_id != expected_plan_id:
            raise ActualModelPressureArtifactError(
                "plan_id does not match pressure plan evidence"
            )


def _validate_pressure_plan_metadata(
    pressure: ActualModelScenarioPressureComparison,
) -> None:
    for plan in (pressure.baseline_plan, pressure.pressure_plan):
        try:
            validate_actual_model_execution_plan(plan)
        except ActualModelExecutionArtifactError as exc:
            raise ActualModelPressureArtifactError(
                "pressure plan metadata does not match run manifest"
            ) from exc


def _validate_condition_comparison_binding(
    pressure: ActualModelScenarioPressureComparison,
) -> None:
    comparison = pressure.comparison
    scenario = pressure.definition.scenario
    baseline_manifest = pressure.baseline_plan.manifest
    pressure_manifest = pressure.pressure_plan.manifest
    expected_comparison_id = stable_condition_comparison_id(
        baseline_manifest=baseline_manifest,
        pressure_manifest=pressure_manifest,
        scenario=scenario,
    )
    if (
        comparison.scenario != scenario
        or comparison.baseline.manifest != baseline_manifest
        or comparison.pressure.manifest != pressure_manifest
        or comparison.baseline.scenario != scenario
        or comparison.pressure.scenario != scenario
        or comparison.comparison_id != expected_comparison_id
        or comparison.baseline.run_id
        != stable_actual_model_run_id(manifest=baseline_manifest, scenario=scenario)
        or comparison.pressure.run_id
        != stable_actual_model_run_id(manifest=pressure_manifest, scenario=scenario)
    ):
        raise ActualModelPressureArtifactError(
            "condition comparison does not match pressure plans"
        )


def _validate_derived_observations(
    comparison: ActualModelConditionComparisonEvidence,
) -> None:
    baseline_summary = summarize_proposal_observations(comparison.baseline)
    pressure_summary = summarize_proposal_observations(comparison.pressure)
    expected_delta = {
        "response_character_count": (
            pressure_summary.response_character_count
            - baseline_summary.response_character_count
        ),
        "state_candidate_count": (
            pressure_summary.state_candidate_count - baseline_summary.state_candidate_count
        ),
        "rejected_state_candidate_count": (
            pressure_summary.rejected_state_candidate_count
            - baseline_summary.rejected_state_candidate_count
        ),
        "continuity_candidate_count": (
            pressure_summary.continuity_candidate_count
            - baseline_summary.continuity_candidate_count
        ),
        "rejected_continuity_candidate_count": (
            pressure_summary.rejected_continuity_candidate_count
            - baseline_summary.rejected_continuity_candidate_count
        ),
        "bounded_budget_failure_count": (
            pressure_summary.bounded_budget_failure_count
            - baseline_summary.bounded_budget_failure_count
        ),
    }
    if (
        comparison.baseline_summary != baseline_summary
        or comparison.pressure_summary != pressure_summary
        or comparison.pressure_minus_baseline.to_mapping() != expected_delta
    ):
        raise ActualModelPressureArtifactError(
            "derived observations do not match embedded evidence"
        )


def _pressure_comparison_identity(
    *,
    format_version: int,
    scenario_set_version: str,
    scenario_set_revision: str,
    definition: ActualModelScenarioDefinition,
    baseline_plan: ActualModelScenarioExecutionPlan,
    pressure_plan: ActualModelScenarioExecutionPlan,
    comparison: ActualModelConditionComparisonEvidence,
) -> dict[str, object]:
    return {
        "format_version": format_version,
        "scenario_set_version": scenario_set_version,
        "scenario_set_revision": scenario_set_revision,
        "scenario_definition": definition.to_mapping(),
        "baseline_plan_id": baseline_plan.plan_id,
        "pressure_plan_id": pressure_plan.plan_id,
        "comparison_id": comparison.comparison_id,
    }


def _stable_pressure_id(identity: dict[str, object]) -> str:
    payload = json.dumps(
        identity,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"ampc-{hashlib.sha256(payload).hexdigest()}"


def _resolve_existing(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelPressureArtifactError(
            f"cannot read existing actual-model pressure comparison: {exc}"
        ) from exc
    if existing == payload:
        return path
    raise ActualModelPressureArtifactError(
        "pressure comparison ID already exists with different evidence"
    )

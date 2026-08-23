from __future__ import annotations

import json
import os
from pathlib import Path

from relaylm.actual_model_evaluation import (
    ActualModelEvidence,
    stable_actual_model_run_id,
)
from relaylm.actual_model_execution import (
    ActualModelScenarioExecutionPlan,
    ActualModelScenarioExecutionResult,
    _stable_execution_id,
    _stable_plan_id,
)
from relaylm.actual_model_restart import (
    ActualModelRestartEvidence,
    _phase_scenario,
    stable_actual_model_restart_run_id,
)


class ActualModelExecutionArtifactError(RuntimeError):
    """An execution artifact violated immutable actual-model evidence rules."""


def validate_actual_model_execution_plan(
    plan: ActualModelScenarioExecutionPlan,
) -> None:
    """Admit one execution plan as internally citable run metadata."""

    expected_plan_id = _stable_plan_id(
        scenario_set_version=plan.scenario_set_version,
        scenario_set_revision=plan.scenario_set_revision,
        character_fixture_id=plan.character_fixture_id,
        character_fixture_revision=plan.character_fixture_revision,
        definition=plan.definition,
        manifest=plan.manifest,
    )
    if plan.plan_id != expected_plan_id:
        raise ActualModelExecutionArtifactError(
            "plan_id does not match execution plan"
        )

    if (
        plan.scenario_set_version != plan.manifest.scenario_set_version
        or plan.character_fixture_id != plan.manifest.character_fixture_id
        or plan.character_fixture_revision != plan.manifest.character_fixture_revision
    ):
        raise ActualModelExecutionArtifactError(
            "execution plan metadata does not match run manifest"
        )


def validate_actual_model_execution_result(
    result: ActualModelScenarioExecutionResult,
) -> None:
    """Admit one generic scenario execution as internally citable evidence."""

    validate_actual_model_execution_plan(result.plan)

    if isinstance(result.evidence, ActualModelEvidence):
        expected_run_id = stable_actual_model_run_id(
            manifest=result.evidence.manifest,
            scenario=result.evidence.scenario,
        )
    elif isinstance(result.evidence, ActualModelRestartEvidence):
        expected_run_id = stable_actual_model_restart_run_id(
            manifest=result.evidence.manifest,
            scenario=result.evidence.scenario,
        )
    else:
        raise TypeError(
            "execution evidence must be ActualModelEvidence or ActualModelRestartEvidence"
        )
    if result.run_id != expected_run_id:
        raise ActualModelExecutionArtifactError(
            "run_id does not match execution evidence"
        )

    _validate_execution_plan_evidence_binding(result)

    expected_execution_id = _stable_execution_id(
        plan=result.plan,
        run_id=result.run_id,
    )
    if result.execution_id != expected_execution_id:
        raise ActualModelExecutionArtifactError(
            "execution_id does not match execution evidence"
        )


def write_actual_model_execution_result(
    *,
    result: ActualModelScenarioExecutionResult,
    artifact_root: str | Path,
) -> Path:
    """Persist one complete execution result as an immutable citable JSON artifact."""

    validate_actual_model_execution_result(result)

    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{result.execution_id}.json"
    payload = result.to_json() + "\n"

    if path.exists():
        return _resolve_existing_execution(path=path, payload=payload)

    temporary = root / f".{result.execution_id}.{os.getpid()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return _resolve_existing_execution(path=path, payload=payload)
    except OSError as exc:
        raise ActualModelExecutionArtifactError(
            f"cannot persist actual-model execution artifact: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def load_actual_model_execution_mapping(path: str | Path) -> dict[str, object]:
    """Load one execution artifact without reconstructing runtime/provider objects."""

    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActualModelExecutionArtifactError(
            f"cannot load actual-model execution artifact: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise ActualModelExecutionArtifactError(
            "actual-model execution artifact root must be a JSON object"
        )
    return raw


def _validate_execution_plan_evidence_binding(
    result: ActualModelScenarioExecutionResult,
) -> None:
    plan = result.plan
    evidence = result.evidence
    scenario = plan.definition.scenario

    if isinstance(evidence, ActualModelEvidence):
        if (
            scenario.family == "restart_quality"
            or evidence.manifest != plan.manifest
            or evidence.scenario != scenario
        ):
            raise ActualModelExecutionArtifactError(
                "execution evidence does not match execution plan"
            )
        return

    if isinstance(evidence, ActualModelRestartEvidence):
        continuity = plan.manifest.continuity_runtime
        restart_after_turn_count = plan.definition.restart_after_turn_count
        if (
            scenario.family != "restart_quality"
            or continuity is None
            or restart_after_turn_count is None
            or evidence.scenario != scenario
            or evidence.manifest.base != plan.manifest
            or evidence.manifest.restart_after_turn_count != restart_after_turn_count
            or evidence.manifest.continuity_max_items != continuity.max_items
            or evidence.manifest.continuity_lifetime_revisions
            != continuity.lifetime_revisions
        ):
            raise ActualModelExecutionArtifactError(
                "execution evidence does not match execution plan"
            )
        _validate_restart_phase_evidence(evidence)
        return

    raise TypeError(
        "execution evidence must be ActualModelEvidence or ActualModelRestartEvidence"
    )


def _validate_restart_phase_evidence(evidence: ActualModelRestartEvidence) -> None:
    split = evidence.manifest.restart_after_turn_count
    expected_phases = (
        (
            evidence.before_restart,
            _phase_scenario(
                scenario=evidence.scenario,
                phase="before_restart",
                turns=evidence.scenario.turns[:split],
            ),
        ),
        (
            evidence.after_restart,
            _phase_scenario(
                scenario=evidence.scenario,
                phase="after_restart",
                turns=evidence.scenario.turns[split:],
            ),
        ),
    )
    for phase, expected_scenario in expected_phases:
        expected_run_id = stable_actual_model_run_id(
            manifest=phase.manifest,
            scenario=phase.scenario,
        )
        if (
            phase.manifest != evidence.manifest.base
            or phase.scenario != expected_scenario
            or phase.run_id != expected_run_id
        ):
            raise ActualModelExecutionArtifactError(
                "restart phase evidence does not match restart envelope"
            )


def _resolve_existing_execution(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelExecutionArtifactError(
            f"cannot read existing actual-model execution artifact: {exc}"
        ) from exc
    if existing == payload:
        return path
    raise ActualModelExecutionArtifactError(
        "execution ID already exists with different evidence; use a distinct replicate_id"
    )

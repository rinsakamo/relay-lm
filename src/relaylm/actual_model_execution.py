from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from relaylm.actual_model_artifacts import (
    ActualModelArtifactError,
    character_fixture_revision,
    prepare_character_fixture_workspace,
    run_actual_model_fixture,
)
from relaylm.actual_model_cognitive_budget import (
    validate_cognitive_budget_runtime_identity,
)
from relaylm.actual_model_evaluation import (
    ActualModelEvidence,
    ActualModelRunManifest,
    stable_actual_model_run_id,
)
from relaylm.actual_model_restart import (
    ActualModelRestartEvidence,
    ActualModelRestartRunManifest,
    run_actual_model_restart_scenario,
    stable_actual_model_restart_run_id,
)
from relaylm.actual_model_scenarios import (
    ActualModelScenarioDefinition,
    ActualModelScenarioSet,
)
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveProvider
from relaylm.storage.filesystem import CharacterDirectory

ACTUAL_MODEL_EXECUTION_FORMAT_VERSION = 1
ActualModelExecutedEvidence: TypeAlias = ActualModelEvidence | ActualModelRestartEvidence


class ActualModelScenarioExecutionError(ValueError):
    """A scenario set cannot be executed under the supplied reproducible run identity."""


@dataclass(frozen=True, slots=True)
class ActualModelScenarioExecutionPlan:
    """Machine-readable preflight binding between one scenario definition and one run."""

    plan_id: str
    scenario_set_version: str
    scenario_set_revision: str
    character_fixture_id: str
    character_fixture_revision: str
    definition: ActualModelScenarioDefinition
    manifest: ActualModelRunManifest
    format_version: int = ACTUAL_MODEL_EXECUTION_FORMAT_VERSION

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "plan_id": self.plan_id,
            "scenario_set": {
                "version": self.scenario_set_version,
                "revision": self.scenario_set_revision,
            },
            "character_fixture": {
                "id": self.character_fixture_id,
                "revision": self.character_fixture_revision,
            },
            "scenario_definition": self.definition.to_mapping(),
            "manifest": self.manifest.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class ActualModelScenarioExecutionResult:
    """One preflight-bound execution plus its existing ordinary/restart evidence."""

    execution_id: str
    plan: ActualModelScenarioExecutionPlan
    evidence: ActualModelExecutedEvidence
    format_version: int = ACTUAL_MODEL_EXECUTION_FORMAT_VERSION

    @property
    def run_id(self) -> str:
        return self.evidence.run_id

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "execution_id": self.execution_id,
            "plan": self.plan.to_mapping(),
            "evidence": self.evidence.to_mapping(),
            "score": None,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )


def plan_actual_model_scenario_execution(
    *,
    scenario_set: ActualModelScenarioSet,
    scenario_id: str,
    fixture_root: str | Path,
    manifest: ActualModelRunManifest,
) -> ActualModelScenarioExecutionPlan:
    """Fail closed on fixture/config/capability drift before any model generation."""

    try:
        definition = scenario_set.scenario(scenario_id)
    except KeyError as exc:
        raise ActualModelScenarioExecutionError(
            f"scenario is not present in the supplied scenario set: {scenario_id}"
        ) from exc

    if manifest.scenario_set_version != scenario_set.scenario_set_version:
        raise ActualModelScenarioExecutionError(
            "run manifest scenario_set_version does not match the loaded scenario set"
        )
    if manifest.character_fixture_id != scenario_set.character_fixture_id:
        raise ActualModelScenarioExecutionError(
            "run manifest character_fixture_id does not match the scenario set"
        )

    fixture = Path(fixture_root)
    try:
        observed_revision = character_fixture_revision(fixture)
        observed_character_id = CharacterDirectory(fixture).load_config().character_id
    except (ActualModelArtifactError, OSError, TypeError, ValueError) as exc:
        raise ActualModelScenarioExecutionError(
            f"cannot verify actual-model character fixture: {exc}"
        ) from exc

    if observed_character_id != scenario_set.character_fixture_id:
        raise ActualModelScenarioExecutionError(
            "Character Package id does not match the scenario-set character_fixture_id"
        )
    if manifest.character_fixture_revision != observed_revision:
        raise ActualModelScenarioExecutionError(
            "run manifest character fixture revision does not match the loaded fixture"
        )

    declared_capabilities = set(manifest.provider_capabilities)
    required_capabilities = set(definition.required_provider_capabilities)
    missing = sorted(required_capabilities - declared_capabilities)
    if missing:
        raise ActualModelScenarioExecutionError(
            "run manifest is missing scenario-required provider capabilities: "
            + ", ".join(missing)
        )

    if (
        "continuity_candidates" in declared_capabilities
        and manifest.continuity_runtime is None
    ):
        raise ActualModelScenarioExecutionError(
            "providers declaring continuity_candidates require explicit "
            "Continuity Runtime identity"
        )
    if manifest.execution_path == "streaming" and "streaming" not in declared_capabilities:
        raise ActualModelScenarioExecutionError(
            "streaming execution requires provider capability 'streaming'"
        )
    if definition.scenario.family == "restart_quality":
        if definition.restart_after_turn_count is None:
            raise ActualModelScenarioExecutionError(
                "restart scenario definition is missing its restart boundary"
            )
        if manifest.restart_boundary != "none":
            raise ActualModelScenarioExecutionError(
                "restart scenario definition owns the restart boundary; "
                "base manifest restart_boundary must be 'none'"
            )
        if manifest.continuity_runtime is None:
            raise ActualModelScenarioExecutionError(
                "restart scenarios require explicit Continuity Runtime identity"
            )
        if manifest.cognitive_budget is not None:
            raise ActualModelScenarioExecutionError(
                "restart scenarios do not support total cognitive-budget evidence "
                "in the ordinary-turn evidence bridge"
            )
        if manifest.cognition_pass_requests is not None:
            raise ActualModelScenarioExecutionError(
                "restart scenarios do not support cognition pass request evidence "
                "until the restart evidence bridge carries the same resolved requests"
            )

    plan_id = _stable_plan_id(
        scenario_set_version=scenario_set.scenario_set_version,
        scenario_set_revision=scenario_set.revision,
        character_fixture_id=scenario_set.character_fixture_id,
        character_fixture_revision=observed_revision,
        definition=definition,
        manifest=manifest,
    )
    return ActualModelScenarioExecutionPlan(
        plan_id=plan_id,
        scenario_set_version=scenario_set.scenario_set_version,
        scenario_set_revision=scenario_set.revision,
        character_fixture_id=scenario_set.character_fixture_id,
        character_fixture_revision=observed_revision,
        definition=definition,
        manifest=manifest,
    )


async def run_actual_model_scenario_definition(
    *,
    scenario_set: ActualModelScenarioSet,
    scenario_id: str,
    fixture_root: str | Path,
    workspace_root: str | Path,
    provider: CognitiveProvider,
    manifest: ActualModelRunManifest,
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
) -> ActualModelScenarioExecutionResult:
    """Execute a loaded scenario definition through the existing real RelayLM path."""

    plan = plan_actual_model_scenario_execution(
        scenario_set=scenario_set,
        scenario_id=scenario_id,
        fixture_root=fixture_root,
        manifest=manifest,
    )
    validate_cognitive_budget_runtime_identity(
        declared=manifest.cognitive_budget,
        runtime=cognitive_budget,
        effective_context_window=manifest.effective_context_window,
    )
    if manifest.execution_path == "streaming" and not callable(
        getattr(provider, "stream_generate", None)
    ):
        raise ActualModelScenarioExecutionError(
            "provider declares streaming execution but has no stream_generate implementation"
        )

    definition = plan.definition
    if definition.scenario.family == "restart_quality":
        continuity = manifest.continuity_runtime
        split = definition.restart_after_turn_count
        assert continuity is not None
        assert split is not None
        restart_manifest = ActualModelRestartRunManifest(
            base=manifest,
            restart_after_turn_count=split,
            continuity_max_items=continuity.max_items,
            continuity_lifetime_revisions=continuity.lifetime_revisions,
        )
        restart_run_id = stable_actual_model_restart_run_id(
            manifest=restart_manifest,
            scenario=definition.scenario,
        )
        execution_id = _stable_execution_id(plan=plan, run_id=restart_run_id)
        character = prepare_character_fixture_workspace(
            fixture_root=fixture_root,
            workspace_root=workspace_root,
            manifest=manifest,
        )
        evidence: ActualModelExecutedEvidence = await run_actual_model_restart_scenario(
            character=character,
            provider=provider,
            manifest=restart_manifest,
            scenario=definition.scenario,
            execution_id=execution_id,
            scenario_revision=plan.scenario_set_revision,
        )
    else:
        run_id = stable_actual_model_run_id(
            manifest=manifest,
            scenario=definition.scenario,
        )
        execution_id = _stable_execution_id(plan=plan, run_id=run_id)
        evidence = await run_actual_model_fixture(
            fixture_root=fixture_root,
            workspace_root=workspace_root,
            provider=provider,
            manifest=manifest,
            scenario=definition.scenario,
            cognitive_budget=cognitive_budget,
            execution_id=execution_id,
            scenario_revision=plan.scenario_set_revision,
        )

    return ActualModelScenarioExecutionResult(
        execution_id=_stable_execution_id(plan=plan, run_id=evidence.run_id),
        plan=plan,
        evidence=evidence,
    )


def _stable_plan_id(
    *,
    scenario_set_version: str,
    scenario_set_revision: str,
    character_fixture_id: str,
    character_fixture_revision: str,
    definition: ActualModelScenarioDefinition,
    manifest: ActualModelRunManifest,
) -> str:
    return _stable_id(
        prefix="amp",
        payload={
            "scenario_set_version": scenario_set_version,
            "scenario_set_revision": scenario_set_revision,
            "character_fixture_id": character_fixture_id,
            "character_fixture_revision": character_fixture_revision,
            "scenario_definition": definition.to_mapping(),
            "manifest": manifest.to_mapping(),
        },
    )


def _stable_execution_id(
    *,
    plan: ActualModelScenarioExecutionPlan,
    run_id: str,
) -> str:
    return _stable_id(
        prefix="amx",
        payload={
            "plan": plan.to_mapping(),
            "run_id": run_id,
        },
    )


def _stable_id(*, prefix: str, payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(encoded).hexdigest()}"

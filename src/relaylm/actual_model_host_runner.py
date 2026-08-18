from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_boundary import (
    evaluate_actual_model_deterministic_boundary,
    write_actual_model_deterministic_boundary_verdict,
)
from relaylm.actual_model_evaluation import (
    ActualModelRunManifest,
    ExplicitBudgetConfiguration,
    ExplicitContinuityRuntimeConfiguration,
)
from relaylm.actual_model_lm_studio import (
    LMStudioExecutionEnvironment,
    run_lm_studio_actual_model_scenario_definition,
    write_lm_studio_actual_model_execution_result,
)
from relaylm.actual_model_scenarios import (
    ActualModelScenarioSet,
    load_actual_model_scenario_set,
)
from relaylm.actual_model_targets import (
    ActualModelArtifactTarget,
    ActualModelArtifactVerification,
    load_actual_model_target,
    verify_actual_model_artifact,
)
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_identity import (
    describe_openai_compatible_provider,
)

ACTUAL_MODEL_HOST_CONDITION_FORMAT_VERSION = 2
CANONICAL_TARGET_PATHS = {
    "gemma-4-12b-it-q4-k-m-v1": Path(
        "evaluation/actual_model/targets/gemma-4-12b-it-q4-k-m-v1.json"
    ),
    "gemma-4-12b-it-q4-k-m-lmstudio-community-v1": Path(
        "evaluation/actual_model/targets/"
        "gemma-4-12b-it-q4-k-m-lmstudio-community-v1.json"
    ),
}
CANONICAL_SCENARIO_SET_PATH = Path(
    "evaluation/actual_model/scenario_sets/foundation-v2.json"
)
CANONICAL_FIXTURE_PATH = Path("evaluation/actual_model/characters/foundation-v1")
CANONICAL_STRUCTURED_OUTPUT_SCHEMA_VERSION = "relaylm-cognitive-output-v1"


class ActualModelHostRunnerError(ValueError):
    """Host-local actual-model execution cannot satisfy the citable run contract."""


@dataclass(frozen=True, slots=True)
class HostLegacyBudgetCondition:
    memory_max_chunks: int | None
    memory_max_chars: int | None
    event_max_events: int | None
    event_max_chars: int | None

    def to_runtime(self) -> ExplicitBudgetConfiguration:
        return ExplicitBudgetConfiguration(
            memory_max_chunks=self.memory_max_chunks,
            memory_max_chars=self.memory_max_chars,
            event_max_events=self.event_max_events,
            event_max_chars=self.event_max_chars,
        )


@dataclass(frozen=True, slots=True)
class HostContinuityCondition:
    max_items: int
    lifetime_revisions: int

    def to_runtime_identity(self) -> ExplicitContinuityRuntimeConfiguration:
        return ExplicitContinuityRuntimeConfiguration(
            max_items=self.max_items,
            lifetime_revisions=self.lifetime_revisions,
        )


@dataclass(frozen=True, slots=True)
class ActualModelHostCondition:
    target_id: str
    relaylm_commit: str
    lm_studio_version: str
    lm_studio_build: str
    deployment_identity: str
    base_url: str
    request_model: str
    api_key_env: str | None
    effective_context_window: int
    temperature: int | float | None
    top_p: int | float | None
    seed: int | None
    supported_decoding_controls: tuple[str, ...]
    execution_path: str
    continuity: HostContinuityCondition | None
    budgets: HostLegacyBudgetCondition
    condition_id: str
    replicate_id: str
    scenario_ids: tuple[str, ...]
    format_version: int = ACTUAL_MODEL_HOST_CONDITION_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_HOST_CONDITION_FORMAT_VERSION:
            raise ActualModelHostRunnerError(
                f"unsupported host condition format_version: {self.format_version}"
            )
        if len(self.relaylm_commit) != 40 or any(
            char not in "0123456789abcdef" for char in self.relaylm_commit
        ):
            raise ActualModelHostRunnerError(
                "relaylm_commit must be an exact lowercase 40-character Git SHA"
            )
        for name in (
            "target_id",
            "lm_studio_version",
            "lm_studio_build",
            "deployment_identity",
            "base_url",
            "request_model",
            "condition_id",
            "replicate_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ActualModelHostRunnerError(f"{name} must be a non-empty string")
        if self.api_key_env is not None and (
            not isinstance(self.api_key_env, str) or not self.api_key_env.strip()
        ):
            raise ActualModelHostRunnerError(
                "api_key_env must be null or a non-empty environment-variable name"
            )
        if isinstance(self.effective_context_window, bool) or not isinstance(
            self.effective_context_window, int
        ):
            raise ActualModelHostRunnerError(
                "effective_context_window must be an integer"
            )
        if self.effective_context_window <= 0:
            raise ActualModelHostRunnerError(
                "effective_context_window must be positive"
            )
        if self.execution_path not in {"buffered", "streaming"}:
            raise ActualModelHostRunnerError(
                "execution_path must be 'buffered' or 'streaming'"
            )
        if not self.scenario_ids:
            raise ActualModelHostRunnerError("scenario_ids must not be empty")
        if len(set(self.scenario_ids)) != len(self.scenario_ids):
            raise ActualModelHostRunnerError("scenario_ids must not contain duplicates")
        if not all(isinstance(item, str) and item.strip() for item in self.scenario_ids):
            raise ActualModelHostRunnerError(
                "scenario_ids must contain non-empty strings"
            )
        if len(set(self.supported_decoding_controls)) != len(
            self.supported_decoding_controls
        ):
            raise ActualModelHostRunnerError(
                "supported_decoding_controls must not contain duplicates"
            )

    @property
    def decoding_config(self) -> OpenAICompatibleDecodingConfig:
        return OpenAICompatibleDecodingConfig(
            temperature=self.temperature,
            top_p=self.top_p,
            seed=self.seed,
        )

    @property
    def decoding_capabilities(self) -> OpenAICompatibleDecodingCapabilities:
        return OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset(self.supported_decoding_controls)
        )

    @property
    def environment(self) -> LMStudioExecutionEnvironment:
        return LMStudioExecutionEnvironment(
            version=self.lm_studio_version,
            build=self.lm_studio_build,
            deployment_identity=self.deployment_identity,
            request_model=self.request_model,
        )


@dataclass(frozen=True, slots=True)
class PreparedActualModelHostRun:
    condition: ActualModelHostCondition
    target: ActualModelArtifactTarget
    artifact_verification: ActualModelArtifactVerification
    scenario_set: ActualModelScenarioSet
    fixture_root: Path
    provider: OpenAICompatibleProvider
    manifest: ActualModelRunManifest


@dataclass(frozen=True, slots=True)
class ActualModelHostRunArtifact:
    scenario_id: str
    execution_id: str
    run_id: str
    artifact_path: str
    boundary_verdict_id: str
    boundary_outcome: str
    boundary_artifact_path: str

    def to_mapping(self) -> dict[str, str]:
        return {
            "scenario_id": self.scenario_id,
            "execution_id": self.execution_id,
            "run_id": self.run_id,
            "artifact_path": self.artifact_path,
            "boundary_verdict_id": self.boundary_verdict_id,
            "boundary_outcome": self.boundary_outcome,
            "boundary_artifact_path": self.boundary_artifact_path,
        }


def load_actual_model_host_condition(path: str | Path) -> ActualModelHostCondition:
    source = Path(path)
    try:
        raw = json.loads(
            source.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActualModelHostRunnerError(
            f"cannot load actual-model host condition: {exc}"
        ) from exc
    mapping = _require_mapping(raw, "host condition")
    _require_exact_keys(
        mapping,
        {
            "format_version",
            "target_id",
            "relaylm_commit",
            "lm_studio",
            "effective_context_window",
            "decoding",
            "supported_decoding_controls",
            "execution_path",
            "continuity_runtime",
            "budgets",
            "condition_id",
            "replicate_id",
            "scenario_ids",
        },
        "host condition",
    )
    lm_studio = _require_mapping(mapping["lm_studio"], "lm_studio")
    _require_exact_keys(
        lm_studio,
        {
            "version",
            "build",
            "deployment_identity",
            "base_url",
            "request_model",
            "api_key_env",
        },
        "lm_studio",
    )
    decoding = _require_mapping(mapping["decoding"], "decoding")
    _require_exact_keys(decoding, {"temperature", "top_p", "seed"}, "decoding")
    budgets = _require_mapping(mapping["budgets"], "budgets")
    _require_exact_keys(
        budgets,
        {
            "memory_max_chunks",
            "memory_max_chars",
            "event_max_events",
            "event_max_chars",
        },
        "budgets",
    )
    continuity_raw = mapping["continuity_runtime"]
    continuity = None
    if continuity_raw is not None:
        continuity_map = _require_mapping(continuity_raw, "continuity_runtime")
        _require_exact_keys(
            continuity_map,
            {"max_items", "lifetime_revisions"},
            "continuity_runtime",
        )
        continuity = HostContinuityCondition(
            max_items=_require_int(continuity_map["max_items"], "continuity_runtime.max_items"),
            lifetime_revisions=_require_int(
                continuity_map["lifetime_revisions"],
                "continuity_runtime.lifetime_revisions",
            ),
        )
    scenario_ids = _require_list(mapping["scenario_ids"], "scenario_ids")
    controls = _require_list(
        mapping["supported_decoding_controls"],
        "supported_decoding_controls",
    )
    try:
        return ActualModelHostCondition(
            format_version=_require_int(mapping["format_version"], "format_version"),
            target_id=_require_string(mapping["target_id"], "target_id"),
            relaylm_commit=_require_string(mapping["relaylm_commit"], "relaylm_commit"),
            lm_studio_version=_require_string(lm_studio["version"], "lm_studio.version"),
            lm_studio_build=_require_string(lm_studio["build"], "lm_studio.build"),
            deployment_identity=_require_string(
                lm_studio["deployment_identity"], "lm_studio.deployment_identity"
            ),
            base_url=_require_string(lm_studio["base_url"], "lm_studio.base_url"),
            request_model=_require_string(
                lm_studio["request_model"], "lm_studio.request_model"
            ),
            api_key_env=_optional_string(lm_studio["api_key_env"], "lm_studio.api_key_env"),
            effective_context_window=_require_int(
                mapping["effective_context_window"], "effective_context_window"
            ),
            temperature=_optional_number(decoding["temperature"], "decoding.temperature"),
            top_p=_optional_number(decoding["top_p"], "decoding.top_p"),
            seed=_optional_int(decoding["seed"], "decoding.seed"),
            supported_decoding_controls=tuple(
                _require_string(item, f"supported_decoding_controls[{index}]")
                for index, item in enumerate(controls, start=1)
            ),
            execution_path=_require_string(mapping["execution_path"], "execution_path"),
            continuity=continuity,
            budgets=HostLegacyBudgetCondition(
                memory_max_chunks=_optional_int(
                    budgets["memory_max_chunks"], "budgets.memory_max_chunks"
                ),
                memory_max_chars=_optional_int(
                    budgets["memory_max_chars"], "budgets.memory_max_chars"
                ),
                event_max_events=_optional_int(
                    budgets["event_max_events"], "budgets.event_max_events"
                ),
                event_max_chars=_optional_int(
                    budgets["event_max_chars"], "budgets.event_max_chars"
                ),
            ),
            condition_id=_require_string(mapping["condition_id"], "condition_id"),
            replicate_id=_require_string(mapping["replicate_id"], "replicate_id"),
            scenario_ids=tuple(
                _require_string(item, f"scenario_ids[{index}]")
                for index, item in enumerate(scenario_ids, start=1)
            ),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ActualModelHostRunnerError):
            raise
        raise ActualModelHostRunnerError(str(exc)) from exc


def prepare_actual_model_host_run(
    *,
    condition: ActualModelHostCondition,
    repo_root: str | Path,
    model_artifact_path: str | Path,
) -> PreparedActualModelHostRun:
    root = Path(repo_root).resolve()
    _verify_clean_exact_repo(root=root, expected_commit=condition.relaylm_commit)

    target_path = CANONICAL_TARGET_PATHS.get(condition.target_id)
    if target_path is None:
        raise ActualModelHostRunnerError(
            f"target_id is not an allowed actual-model target: {condition.target_id}"
        )
    target = load_actual_model_target(root / target_path)
    if target.target_id != condition.target_id:
        raise ActualModelHostRunnerError(
            "selected target metadata does not match host condition target_id"
        )
    artifact_verification = verify_actual_model_artifact(
        target=target,
        artifact_path=model_artifact_path,
    )
    scenario_set = load_actual_model_scenario_set(root / CANONICAL_SCENARIO_SET_PATH)
    fixture_root = root / CANONICAL_FIXTURE_PATH
    fixture_revision = character_fixture_revision(fixture_root)

    missing_scenarios = [
        scenario_id
        for scenario_id in condition.scenario_ids
        if not _scenario_exists(scenario_set, scenario_id)
    ]
    if missing_scenarios:
        raise ActualModelHostRunnerError(
            "condition references scenarios outside canonical foundation-v2: "
            + ", ".join(missing_scenarios)
        )
    if any(
        "continuity_candidates"
        in scenario_set.scenario(scenario_id).required_provider_capabilities
        for scenario_id in condition.scenario_ids
    ) and condition.continuity is None:
        raise ActualModelHostRunnerError(
            "selected foundation-v2 scenarios require explicit continuity_runtime"
        )

    api_key = None
    if condition.api_key_env is not None:
        api_key = os.environ.get(condition.api_key_env)
        if api_key is None:
            raise ActualModelHostRunnerError(
                f"required API key environment variable is not set: {condition.api_key_env}"
            )
    provider = OpenAICompatibleProvider(
        base_url=condition.base_url,
        model=condition.request_model,
        api_key=api_key,
        decoding_config=condition.decoding_config,
        decoding_capabilities=condition.decoding_capabilities,
    )
    identity = describe_openai_compatible_provider(provider)
    manifest = ActualModelRunManifest(
        relaylm_commit=condition.relaylm_commit,
        character_fixture_id=scenario_set.character_fixture_id,
        character_fixture_revision=fixture_revision,
        provider_identity=condition.environment.manifest_provider_identity,
        adapter_identity=identity.adapter_identity,
        model_artifact=target.model_artifact_identity,
        tokenizer_identity=target.tokenizer_identity,
        effective_context_window=condition.effective_context_window,
        decoding_configuration=tuple(
            sorted(identity.effective_decoding_configuration.items())
        ),
        structured_output_schema_version=CANONICAL_STRUCTURED_OUTPUT_SCHEMA_VERSION,
        scenario_set_version=scenario_set.scenario_set_version,
        condition_id=condition.condition_id,
        budgets=condition.budgets.to_runtime(),
        continuity_runtime=(
            condition.continuity.to_runtime_identity()
            if condition.continuity is not None
            else None
        ),
        execution_path=condition.execution_path,  # type: ignore[arg-type]
        restart_boundary="none",
        seed=condition.seed,
        provider_capabilities=identity.provider_capabilities,
        replicate_id=condition.replicate_id,
    )
    return PreparedActualModelHostRun(
        condition=condition,
        target=target,
        artifact_verification=artifact_verification,
        scenario_set=scenario_set,
        fixture_root=fixture_root,
        provider=provider,
        manifest=manifest,
    )


async def execute_actual_model_host_run(
    *,
    prepared: PreparedActualModelHostRun,
    workspace_root: str | Path,
    artifact_root: str | Path,
) -> tuple[ActualModelHostRunArtifact, ...]:
    workspace_base = Path(workspace_root)
    artifact_base = Path(artifact_root)
    results: list[ActualModelHostRunArtifact] = []
    try:
        for scenario_id in prepared.condition.scenario_ids:
            result = await run_lm_studio_actual_model_scenario_definition(
                environment=prepared.condition.environment,
                target=prepared.target,
                artifact_verification=prepared.artifact_verification,
                configured_context_window=prepared.condition.effective_context_window,
                scenario_set=prepared.scenario_set,
                scenario_id=scenario_id,
                fixture_root=prepared.fixture_root,
                workspace_root=(
                    workspace_base
                    / prepared.condition.condition_id
                    / prepared.condition.replicate_id
                    / scenario_id
                ),
                provider=prepared.provider,
                manifest=prepared.manifest,
            )
            path = write_lm_studio_actual_model_execution_result(
                result=result,
                artifact_root=artifact_base,
            )
            verdict = evaluate_actual_model_deterministic_boundary(
                result=result.execution,
            )
            boundary_path = write_actual_model_deterministic_boundary_verdict(
                verdict=verdict,
                artifact_root=artifact_base,
            )
            results.append(
                ActualModelHostRunArtifact(
                    scenario_id=scenario_id,
                    execution_id=result.execution_id,
                    run_id=result.run_id,
                    artifact_path=str(path),
                    boundary_verdict_id=verdict.verdict_id,
                    boundary_outcome=verdict.outcome,
                    boundary_artifact_path=str(boundary_path),
                )
            )
    finally:
        await prepared.provider.aclose()
    return tuple(results)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run canonical foundation-v2 actual-model evidence against an explicitly "
            "selected verified Gemma 4 12B IT Q4_K_M target through LM Studio."
        )
    )
    parser.add_argument("--condition", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--model-artifact", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--artifact-root", required=True)
    args = parser.parse_args(argv)

    condition = load_actual_model_host_condition(args.condition)
    prepared = prepare_actual_model_host_run(
        condition=condition,
        repo_root=args.repo_root,
        model_artifact_path=args.model_artifact,
    )
    results = asyncio.run(
        execute_actual_model_host_run(
            prepared=prepared,
            workspace_root=args.workspace_root,
            artifact_root=args.artifact_root,
        )
    )
    print(
        json.dumps(
            {
                "format_version": 1,
                "suite": "actual-model-foundation-v2-lm-studio",
                "relaylm_commit": condition.relaylm_commit,
                "target_id": condition.target_id,
                "condition_id": condition.condition_id,
                "replicate_id": condition.replicate_id,
                "results": [item.to_mapping() for item in results],
                "score": None,
            },
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )
    )
    return 0


def _verify_clean_exact_repo(*, root: Path, expected_commit: str) -> None:
    if not root.is_dir():
        raise ActualModelHostRunnerError("repo_root must be an existing directory")
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ActualModelHostRunnerError(
            f"cannot verify host repository snapshot: {exc}"
        ) from exc
    if head != expected_commit:
        raise ActualModelHostRunnerError(
            f"host repository HEAD does not match relaylm_commit: {head}"
        )
    if status:
        raise ActualModelHostRunnerError(
            "host repository must be clean, including untracked files, before evidence execution"
        )


def _scenario_exists(scenario_set: ActualModelScenarioSet, scenario_id: str) -> bool:
    try:
        scenario_set.scenario(scenario_id)
    except KeyError:
        return False
    return True


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ActualModelHostRunnerError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ActualModelHostRunnerError(f"{label} must be a JSON object")
    return value


def _require_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ActualModelHostRunnerError(f"{label} must be a JSON array")
    return value


def _require_exact_keys(
    mapping: Mapping[str, object], expected: set[str], label: str
) -> None:
    observed = set(mapping)
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    if missing:
        raise ActualModelHostRunnerError(
            f"{label} is missing fields: " + ", ".join(missing)
        )
    if unknown:
        raise ActualModelHostRunnerError(
            f"{label} has unknown fields: " + ", ".join(unknown)
        )


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActualModelHostRunnerError(f"{label} must be a non-empty string")
    return value


def _optional_string(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, label)


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ActualModelHostRunnerError(f"{label} must be an integer")
    return value


def _optional_int(value: object, label: str) -> int | None:
    if value is None:
        return None
    return _require_int(value, label)


def _optional_number(value: object, label: str) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActualModelHostRunnerError(f"{label} must be a number or null")
    return value


if __name__ == "__main__":
    raise SystemExit(main())

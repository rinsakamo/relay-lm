from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from relaylm.actual_model_artifacts import (
    ActualModelArtifactError,
    character_fixture_revision,
    prepare_character_fixture_workspace,
)
from relaylm.actual_model_crystallization import (
    ActualModelCrystallizationCase,
    ActualModelCrystallizationManifest,
    run_actual_model_crystallization,
    write_actual_model_crystallization_evidence,
)
from relaylm.actual_model_host_runner import (
    CANONICAL_TARGET_PATHS,
    _verify_clean_exact_repo,
)
from relaylm.actual_model_lm_studio import LMStudioExecutionEnvironment
from relaylm.actual_model_lm_studio_counter import (
    LMStudioCounterError,
    build_lm_studio_counter_capabilities,
)
from relaylm.actual_model_targets import (
    ActualModelArtifactTarget,
    ActualModelArtifactVerification,
    load_actual_model_target,
    verify_actual_model_artifact,
)
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_crystallization import OpenAICompatibleCrystallizer
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)

ACTUAL_MODEL_CRYSTALLIZATION_HOST_FORMAT_VERSION = 1
CRYSTALLIZATION_ADAPTER_IDENTITY = "relaylm.providers.OpenAICompatibleCrystallizer:v1"
CRYSTALLIZATION_STRUCTURED_OUTPUT_SCHEMA_VERSION = "relaylm_crystallization_output:v1"
CRYSTALLIZATION_EVALUATION_CONTRACT_VERSION = "actual-model-crystallization-v1"
LM_STUDIO_SERVING_PROOF_IDENTITY_PREFIX = "lm-studio-serving-proof:sha256:"


class ActualModelCrystallizationHostRunnerError(ValueError):
    """Host-local crystallization evidence cannot satisfy its citable run contract."""


@dataclass(frozen=True, slots=True)
class ActualModelCrystallizationHostCondition:
    """Strict host-only condition for one off-turn crystallization evidence run."""

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
    fixture_id: str
    fixture_path: Path
    fixture_revision: str
    case: ActualModelCrystallizationCase
    max_events: int
    condition_id: str
    replicate_id: str
    format_version: int = ACTUAL_MODEL_CRYSTALLIZATION_HOST_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_CRYSTALLIZATION_HOST_FORMAT_VERSION:
            raise ActualModelCrystallizationHostRunnerError(
                "unsupported crystallization host condition format_version: "
                f"{self.format_version}"
            )
        if len(self.relaylm_commit) != 40 or any(
            char not in "0123456789abcdef" for char in self.relaylm_commit
        ):
            raise ActualModelCrystallizationHostRunnerError(
                "relaylm_commit must be an exact lowercase 40-character Git SHA"
            )
        for name in (
            "target_id",
            "lm_studio_version",
            "lm_studio_build",
            "deployment_identity",
            "base_url",
            "request_model",
            "fixture_id",
            "fixture_revision",
            "condition_id",
            "replicate_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ActualModelCrystallizationHostRunnerError(
                    f"{name} must be a non-empty string"
                )
        if self.api_key_env is not None and (
            not isinstance(self.api_key_env, str) or not self.api_key_env.strip()
        ):
            raise ActualModelCrystallizationHostRunnerError(
                "api_key_env must be null or a non-empty environment-variable name"
            )
        if isinstance(self.effective_context_window, bool) or not isinstance(
            self.effective_context_window, int
        ):
            raise ActualModelCrystallizationHostRunnerError(
                "effective_context_window must be an integer"
            )
        if self.effective_context_window <= 0:
            raise ActualModelCrystallizationHostRunnerError(
                "effective_context_window must be positive"
            )
        if isinstance(self.max_events, bool) or not isinstance(self.max_events, int):
            raise ActualModelCrystallizationHostRunnerError("max_events must be an integer")
        if self.max_events < 0:
            raise ActualModelCrystallizationHostRunnerError(
                "max_events must not be negative"
            )
        if self.seed is not None and (
            isinstance(self.seed, bool) or not isinstance(self.seed, int)
        ):
            raise ActualModelCrystallizationHostRunnerError(
                "decoding.seed must be an integer or null"
            )
        if not isinstance(self.fixture_path, Path):
            raise TypeError("fixture_path must be a pathlib.Path")
        if self.fixture_path.is_absolute() or ".." in self.fixture_path.parts:
            raise ActualModelCrystallizationHostRunnerError(
                "character fixture path must be a repository-relative path"
            )
        if "\\" in self.fixture_path.as_posix():
            raise ActualModelCrystallizationHostRunnerError(
                "character fixture path must use repository-relative POSIX components"
            )
        if not self.fixture_path.parts:
            raise ActualModelCrystallizationHostRunnerError(
                "character fixture path must not be empty"
            )
        if not isinstance(self.case, ActualModelCrystallizationCase):
            raise TypeError("case must be ActualModelCrystallizationCase")
        if not self.supported_decoding_controls or not all(
            isinstance(item, str) and item.strip()
            for item in self.supported_decoding_controls
        ):
            raise ActualModelCrystallizationHostRunnerError(
                "supported_decoding_controls must contain non-empty strings"
            )
        if len(set(self.supported_decoding_controls)) != len(
            self.supported_decoding_controls
        ):
            raise ActualModelCrystallizationHostRunnerError(
                "supported_decoding_controls must not contain duplicates"
            )
        try:
            self.decoding_capabilities.require(self.decoding_config)
        except (TypeError, ValueError) as exc:
            raise ActualModelCrystallizationHostRunnerError(str(exc)) from exc

    @property
    def environment(self) -> LMStudioExecutionEnvironment:
        return LMStudioExecutionEnvironment(
            version=self.lm_studio_version,
            build=self.lm_studio_build,
            deployment_identity=self.deployment_identity,
            request_model=self.request_model,
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

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "execution_kind": "off_turn_crystallization",
            "target_id": self.target_id,
            "relaylm_commit": self.relaylm_commit,
            "lm_studio": {
                "version": self.lm_studio_version,
                "build": self.lm_studio_build,
                "deployment_identity": self.deployment_identity,
                "base_url": self.base_url,
                "request_model": self.request_model,
                "api_key_env": self.api_key_env,
            },
            "effective_context_window": self.effective_context_window,
            "decoding": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "seed": self.seed,
            },
            "supported_decoding_controls": list(self.supported_decoding_controls),
            "character_fixture": {
                "id": self.fixture_id,
                "path": self.fixture_path.as_posix(),
                "revision": self.fixture_revision,
            },
            "case": self.case.to_mapping(),
            "max_events": self.max_events,
            "condition_id": self.condition_id,
            "replicate_id": self.replicate_id,
        }


@dataclass(frozen=True, slots=True)
class PreparedActualModelCrystallizationHostRun:
    condition: ActualModelCrystallizationHostCondition
    target: ActualModelArtifactTarget
    artifact_verification: ActualModelArtifactVerification
    fixture_root: Path
    serving_attestation_identity: str
    crystallizer: OpenAICompatibleCrystallizer
    manifest: ActualModelCrystallizationManifest
    case: ActualModelCrystallizationCase


@dataclass(frozen=True, slots=True)
class ActualModelCrystallizationHostRunArtifact:
    case_id: str
    run_id: str
    artifact_path: str

    def to_mapping(self) -> dict[str, str]:
        return {
            "case_id": self.case_id,
            "run_id": self.run_id,
            "artifact_path": self.artifact_path,
        }


def load_actual_model_crystallization_host_condition(
    path: str | Path,
) -> ActualModelCrystallizationHostCondition:
    source = Path(path)
    try:
        raw = json.loads(
            source.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActualModelCrystallizationHostRunnerError(
            f"cannot load crystallization host condition: {exc}"
        ) from exc

    mapping = _require_mapping(raw, "crystallization host condition")
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
            "character_fixture",
            "case",
            "max_events",
            "condition_id",
            "replicate_id",
        },
        "crystallization host condition",
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
    fixture = _require_mapping(mapping["character_fixture"], "character_fixture")
    _require_exact_keys(fixture, {"id", "path", "revision"}, "character_fixture")
    case_mapping = _require_mapping(mapping["case"], "case")
    _require_exact_keys(case_mapping, {"id", "version"}, "case")
    controls = _require_list(
        mapping["supported_decoding_controls"],
        "supported_decoding_controls",
    )

    try:
        return ActualModelCrystallizationHostCondition(
            format_version=_require_int(mapping["format_version"], "format_version"),
            target_id=_require_string(mapping["target_id"], "target_id"),
            relaylm_commit=_require_string(mapping["relaylm_commit"], "relaylm_commit"),
            lm_studio_version=_require_string(
                lm_studio["version"], "lm_studio.version"
            ),
            lm_studio_build=_require_string(lm_studio["build"], "lm_studio.build"),
            deployment_identity=_require_string(
                lm_studio["deployment_identity"], "lm_studio.deployment_identity"
            ),
            base_url=_require_string(lm_studio["base_url"], "lm_studio.base_url"),
            request_model=_require_string(
                lm_studio["request_model"], "lm_studio.request_model"
            ),
            api_key_env=_optional_string(
                lm_studio["api_key_env"], "lm_studio.api_key_env"
            ),
            effective_context_window=_require_int(
                mapping["effective_context_window"], "effective_context_window"
            ),
            temperature=_optional_number(
                decoding["temperature"], "decoding.temperature"
            ),
            top_p=_optional_number(decoding["top_p"], "decoding.top_p"),
            seed=_optional_int(decoding["seed"], "decoding.seed"),
            supported_decoding_controls=tuple(
                _require_string(item, f"supported_decoding_controls[{index}]")
                for index, item in enumerate(controls)
            ),
            fixture_id=_require_string(fixture["id"], "character_fixture.id"),
            fixture_path=Path(
                _require_string(fixture["path"], "character_fixture.path")
            ),
            fixture_revision=_require_string(
                fixture["revision"], "character_fixture.revision"
            ),
            case=ActualModelCrystallizationCase(
                case_id=_require_string(case_mapping["id"], "case.id"),
                version=_require_string(case_mapping["version"], "case.version"),
            ),
            max_events=_require_int(mapping["max_events"], "max_events"),
            condition_id=_require_string(mapping["condition_id"], "condition_id"),
            replicate_id=_require_string(mapping["replicate_id"], "replicate_id"),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ActualModelCrystallizationHostRunnerError):
            raise
        raise ActualModelCrystallizationHostRunnerError(str(exc)) from exc


def prepare_actual_model_crystallization_host_run(
    *,
    condition: ActualModelCrystallizationHostCondition,
    repo_root: str | Path,
    model_artifact_path: str | Path,
    serving_proof_path: str | Path,
    node_path: str | Path | None = None,
    sdk_root: str | Path | None = None,
) -> PreparedActualModelCrystallizationHostRun:
    root = Path(repo_root).resolve()
    _verify_clean_exact_repo(root=root, expected_commit=condition.relaylm_commit)

    target_path = CANONICAL_TARGET_PATHS.get(condition.target_id)
    if target_path is None:
        raise ActualModelCrystallizationHostRunnerError(
            f"target_id is not an allowed actual-model target: {condition.target_id}"
        )
    try:
        target = load_actual_model_target(root / target_path)
        artifact_verification = verify_actual_model_artifact(
            target=target,
            artifact_path=model_artifact_path,
        )
    except (OSError, ValueError) as exc:
        raise ActualModelCrystallizationHostRunnerError(
            f"cannot verify crystallization model target: {exc}"
        ) from exc
    if target.target_id != condition.target_id:
        raise ActualModelCrystallizationHostRunnerError(
            "loaded actual-model target does not match crystallization host condition"
        )

    fixture_root = _resolve_fixture_root(root=root, relative=condition.fixture_path)
    try:
        observed_fixture_revision = character_fixture_revision(fixture_root)
    except (OSError, ActualModelArtifactError) as exc:
        raise ActualModelCrystallizationHostRunnerError(
            f"cannot verify character fixture: {exc}"
        ) from exc
    if observed_fixture_revision != condition.fixture_revision:
        raise ActualModelCrystallizationHostRunnerError(
            "character fixture revision does not match crystallization host condition: "
            f"expected {condition.fixture_revision}, observed {observed_fixture_revision}"
        )

    serving_attestation_identity = _attest_lm_studio_serving_target(
        condition=condition,
        target=target,
        artifact_path=model_artifact_path,
        proof_path=serving_proof_path,
        node_path=node_path,
        sdk_root=sdk_root,
    )

    api_key = None
    if condition.api_key_env is not None:
        api_key = os.environ.get(condition.api_key_env)
        if api_key is None:
            raise ActualModelCrystallizationHostRunnerError(
                "required API key environment variable is not set: "
                f"{condition.api_key_env}"
            )

    decoding_config = condition.decoding_config
    decoding_capabilities = condition.decoding_capabilities
    manifest = ActualModelCrystallizationManifest(
        relaylm_commit=condition.relaylm_commit,
        character_fixture_id=condition.fixture_id,
        character_fixture_revision=condition.fixture_revision,
        provider_identity=(
            condition.environment.manifest_provider_identity
            + "|"
            + serving_attestation_identity
        ),
        adapter_identity=CRYSTALLIZATION_ADAPTER_IDENTITY,
        model_artifact=target.model_artifact_identity,
        tokenizer_identity=target.tokenizer_identity,
        effective_context_window=condition.effective_context_window,
        decoding_configuration=tuple(sorted(decoding_config.to_mapping().items())),
        seed=condition.seed,
        structured_output_schema_version=CRYSTALLIZATION_STRUCTURED_OUTPUT_SCHEMA_VERSION,
        evaluation_contract_version=CRYSTALLIZATION_EVALUATION_CONTRACT_VERSION,
        condition_id=condition.condition_id,
        max_events=condition.max_events,
        replicate_id=condition.replicate_id,
    )
    crystallizer = OpenAICompatibleCrystallizer(
        base_url=condition.base_url,
        model=condition.request_model,
        api_key=api_key,
        decoding_config=decoding_config,
        decoding_capabilities=decoding_capabilities,
    )
    if crystallizer.model != condition.environment.request_model:
        raise ActualModelCrystallizationHostRunnerError(
            "constructed crystallizer model does not match attested LM Studio request_model"
        )
    if crystallizer.effective_decoding_configuration != dict(
        manifest.decoding_configuration
    ):
        raise ActualModelCrystallizationHostRunnerError(
            "constructed crystallizer decoding controls do not match evidence manifest"
        )

    return PreparedActualModelCrystallizationHostRun(
        condition=condition,
        target=target,
        artifact_verification=artifact_verification,
        fixture_root=fixture_root,
        serving_attestation_identity=serving_attestation_identity,
        crystallizer=crystallizer,
        manifest=manifest,
        case=condition.case,
    )


async def execute_actual_model_crystallization_host_run(
    *,
    prepared: PreparedActualModelCrystallizationHostRun,
    workspace_root: str | Path,
    artifact_root: str | Path,
) -> ActualModelCrystallizationHostRunArtifact:
    workspace = (
        Path(workspace_root)
        / prepared.condition.condition_id
        / prepared.condition.replicate_id
        / prepared.case.case_id
    )
    try:
        character = prepare_character_fixture_workspace(
            fixture_root=prepared.fixture_root,
            workspace_root=workspace,
            manifest=prepared.manifest,  # type: ignore[arg-type]
        )
        evidence = await run_actual_model_crystallization(
            character=character,
            crystallizer=prepared.crystallizer,
            manifest=prepared.manifest,
            case=prepared.case,
        )
        path = write_actual_model_crystallization_evidence(
            evidence=evidence,
            artifact_root=artifact_root,
        )
        return ActualModelCrystallizationHostRunArtifact(
            case_id=prepared.case.case_id,
            run_id=evidence.run_id,
            artifact_path=str(path),
        )
    finally:
        await prepared.crystallizer.aclose()


def _attest_lm_studio_serving_target(
    *,
    condition: ActualModelCrystallizationHostCondition,
    target: ActualModelArtifactTarget,
    artifact_path: str | Path,
    proof_path: str | Path,
    node_path: str | Path | None,
    sdk_root: str | Path | None,
) -> str:
    proof = Path(proof_path)
    try:
        build_lm_studio_counter_capabilities(
            condition=condition,
            target=target,
            artifact_path=artifact_path,
            proof_path=proof,
            node_path=node_path,
            sdk_root=sdk_root,
        )
        digest = hashlib.sha256(proof.read_bytes()).hexdigest()
    except (OSError, LMStudioCounterError, ValueError) as exc:
        raise ActualModelCrystallizationHostRunnerError(
            f"LM Studio serving target attestation failed: {exc}"
        ) from exc
    return LM_STUDIO_SERVING_PROOF_IDENTITY_PREFIX + digest


def _resolve_fixture_root(*, root: Path, relative: Path) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ActualModelCrystallizationHostRunnerError(
            "character fixture path resolves outside repo_root"
        ) from exc
    if not candidate.is_dir():
        raise ActualModelCrystallizationHostRunnerError(
            "character fixture path must resolve to an existing directory"
        )
    return candidate


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one citable off-turn crystallization evidence pass against an "
            "explicitly attested LM Studio target."
        )
    )
    parser.add_argument("--condition", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--model-artifact", required=True)
    parser.add_argument("--serving-proof", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--lmstudio-node")
    parser.add_argument("--lmstudio-sdk-root")
    args = parser.parse_args(argv)

    try:
        condition = load_actual_model_crystallization_host_condition(args.condition)
        prepared = prepare_actual_model_crystallization_host_run(
            condition=condition,
            repo_root=args.repo_root,
            model_artifact_path=args.model_artifact,
            serving_proof_path=args.serving_proof,
            node_path=args.lmstudio_node,
            sdk_root=args.lmstudio_sdk_root,
        )
        artifact = asyncio.run(
            execute_actual_model_crystallization_host_run(
                prepared=prepared,
                workspace_root=args.workspace_root,
                artifact_root=args.artifact_root,
            )
        )
    except (
        ActualModelCrystallizationHostRunnerError,
        ActualModelArtifactError,
        LMStudioCounterError,
        ProviderProtocolError,
        OSError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "format_version": 1,
                "suite": "actual-model-crystallization-lm-studio-v1",
                "relaylm_commit": condition.relaylm_commit,
                "target_id": condition.target_id,
                "condition_id": condition.condition_id,
                "replicate_id": condition.replicate_id,
                "result": artifact.to_mapping(),
                "score": None,
            },
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )
    )
    return 0


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ActualModelCrystallizationHostRunnerError(
                f"duplicate JSON key: {key}"
            )
        result[key] = value
    return result


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ActualModelCrystallizationHostRunnerError(
            f"{label} must be a JSON object"
        )
    return value


def _require_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ActualModelCrystallizationHostRunnerError(
            f"{label} must be a JSON array"
        )
    return value


def _require_exact_keys(
    mapping: Mapping[str, object], expected: set[str], label: str
) -> None:
    observed = set(mapping)
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    if missing:
        raise ActualModelCrystallizationHostRunnerError(
            f"{label} is missing fields: " + ", ".join(missing)
        )
    if unknown:
        raise ActualModelCrystallizationHostRunnerError(
            f"{label} has unknown fields: " + ", ".join(unknown)
        )


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActualModelCrystallizationHostRunnerError(
            f"{label} must be a non-empty string"
        )
    return value


def _optional_string(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, label)


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ActualModelCrystallizationHostRunnerError(
            f"{label} must be an integer"
        )
    return value


def _optional_int(value: object, label: str) -> int | None:
    if value is None:
        return None
    return _require_int(value, label)


def _optional_number(value: object, label: str) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActualModelCrystallizationHostRunnerError(
            f"{label} must be a number or null"
        )
    return value


if __name__ == "__main__":
    raise SystemExit(main())

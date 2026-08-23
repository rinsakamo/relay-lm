from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from relaylm.actual_model_execution import (
    ActualModelScenarioExecutionResult,
    _stable_execution_id,
    run_actual_model_scenario_definition,
)
from relaylm.actual_model_execution_artifacts import (
    ActualModelExecutionArtifactError,
    validate_actual_model_execution_result,
)
from relaylm.actual_model_evaluation import ActualModelRunManifest
from relaylm.actual_model_scenarios import ActualModelScenarioSet
from relaylm.actual_model_targets import (
    ActualModelArtifactTarget,
    ActualModelArtifactVerification,
)
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_identity import (
    OpenAICompatibleProviderIdentity,
    describe_openai_compatible_provider,
)

ACTUAL_MODEL_LM_STUDIO_BINDING_FORMAT_VERSION = 1
LM_STUDIO_MANIFEST_PROVIDER_IDENTITY_PREFIX = "actual-model-lm-studio-v1:"


class ActualModelLMStudioBindingError(ValueError):
    """The declared citable LM Studio condition does not match executable authority."""


class LMStudioOpenAICompatibleProvider(Protocol):
    """OpenAI-compatible provider surface consumed by the binding preflight."""

    model: str
    decoding_config: OpenAICompatibleDecodingConfig
    decoding_capabilities: OpenAICompatibleDecodingCapabilities

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput: ...


@dataclass(frozen=True, slots=True)
class LMStudioExecutionEnvironment:
    """Externally observed, secret-free LM Studio runtime identity for one evidence run."""

    version: str
    build: str
    deployment_identity: str
    request_model: str
    format_version: int = ACTUAL_MODEL_LM_STUDIO_BINDING_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_LM_STUDIO_BINDING_FORMAT_VERSION:
            raise ActualModelLMStudioBindingError(
                f"unsupported LM Studio environment format_version: {self.format_version}"
            )
        for name in ("version", "build", "deployment_identity", "request_model"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ActualModelLMStudioBindingError(f"{name} must be a non-empty string")

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "implementation": "lm_studio",
            "version": self.version,
            "build": self.build,
            "deployment_identity": self.deployment_identity,
            "request_model": self.request_model,
        }

    @property
    def manifest_provider_identity(self) -> str:
        """Canonical value stored in ActualModelRunManifest.provider_identity."""

        encoded = json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return LM_STUDIO_MANIFEST_PROVIDER_IDENTITY_PREFIX + encoded

    @property
    def environment_id(self) -> str:
        encoded = json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"amlse-{hashlib.sha256(encoded).hexdigest()}"


@dataclass(frozen=True, slots=True)
class ActualModelLMStudioExecutionBinding:
    """Fail-before-generation proof that runtime, provider, target, and manifest agree."""

    binding_id: str
    environment: LMStudioExecutionEnvironment
    target_id: str
    target_revision: str
    artifact_verification: ActualModelArtifactVerification
    provider_identity: OpenAICompatibleProviderIdentity
    configured_context_window: int
    manifest: ActualModelRunManifest
    format_version: int = ACTUAL_MODEL_LM_STUDIO_BINDING_FORMAT_VERSION

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "binding_id": self.binding_id,
            "environment": self.environment.to_mapping(),
            "target": {
                "id": self.target_id,
                "revision": self.target_revision,
            },
            "artifact_verification": self.artifact_verification.to_mapping(),
            "provider_identity": self.provider_identity.to_mapping(),
            "configured_context_window": self.configured_context_window,
            "manifest": self.manifest.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class ActualModelLMStudioExecutionResult:
    """Existing scenario execution wrapped with its verified LM Studio condition."""

    execution_id: str
    binding: ActualModelLMStudioExecutionBinding
    execution: ActualModelScenarioExecutionResult
    format_version: int = ACTUAL_MODEL_LM_STUDIO_BINDING_FORMAT_VERSION

    @property
    def run_id(self) -> str:
        return self.execution.run_id

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "execution_id": self.execution_id,
            "binding": self.binding.to_mapping(),
            "execution": self.execution.to_mapping(),
            "score": None,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )


def bind_lm_studio_execution_condition(
    *,
    environment: LMStudioExecutionEnvironment,
    target: ActualModelArtifactTarget,
    artifact_verification: ActualModelArtifactVerification,
    provider: LMStudioOpenAICompatibleProvider,
    manifest: ActualModelRunManifest,
    configured_context_window: int,
) -> ActualModelLMStudioExecutionBinding:
    """Bind only values proved by target verification or the constructed provider."""

    if not isinstance(environment, LMStudioExecutionEnvironment):
        raise TypeError("environment must be LMStudioExecutionEnvironment")
    if not isinstance(target, ActualModelArtifactTarget):
        raise TypeError("target must be ActualModelArtifactTarget")
    if not isinstance(artifact_verification, ActualModelArtifactVerification):
        raise TypeError("artifact_verification must be ActualModelArtifactVerification")
    if not isinstance(manifest, ActualModelRunManifest):
        raise TypeError("manifest must be ActualModelRunManifest")
    if isinstance(configured_context_window, bool) or not isinstance(
        configured_context_window, int
    ):
        raise TypeError("configured_context_window must be an integer")
    if configured_context_window <= 0:
        raise ActualModelLMStudioBindingError(
            "configured_context_window must be positive"
        )

    _validate_artifact_verification(
        target=target,
        artifact_verification=artifact_verification,
    )
    provider_identity = describe_openai_compatible_provider(provider)

    if environment.request_model != provider_identity.model:
        raise ActualModelLMStudioBindingError(
            "LM Studio request_model does not match the constructed provider"
        )
    if manifest.provider_identity != environment.manifest_provider_identity:
        raise ActualModelLMStudioBindingError(
            "manifest provider_identity does not match the LM Studio environment"
        )
    if manifest.adapter_identity != provider_identity.adapter_identity:
        raise ActualModelLMStudioBindingError(
            "manifest adapter_identity does not match provider-owned identity"
        )
    if manifest.model_artifact != target.model_artifact_identity:
        raise ActualModelLMStudioBindingError(
            "manifest model_artifact does not match the verified frozen target"
        )
    if manifest.tokenizer_identity != target.tokenizer_identity:
        raise ActualModelLMStudioBindingError(
            "manifest tokenizer_identity does not match the verified GGUF tokenizer"
        )
    if manifest.effective_context_window != configured_context_window:
        raise ActualModelLMStudioBindingError(
            "manifest effective_context_window does not match LM Studio configuration"
        )

    expected_decoding = tuple(
        sorted(provider_identity.effective_decoding_configuration.items())
    )
    if tuple(sorted(manifest.decoding_configuration)) != expected_decoding:
        raise ActualModelLMStudioBindingError(
            "manifest decoding_configuration does not match applied provider request controls"
        )

    expected_capabilities = provider_identity.provider_capabilities
    if tuple(sorted(manifest.provider_capabilities)) != expected_capabilities:
        raise ActualModelLMStudioBindingError(
            "manifest provider_capabilities do not match provider-owned capabilities"
        )

    applied_seed = provider_identity.effective_decoding_configuration.get("seed")
    if manifest.seed != applied_seed:
        raise ActualModelLMStudioBindingError(
            "manifest seed does not match the seed actually carried by the provider"
        )

    binding_id = _stable_lm_studio_binding_id(
        environment=environment,
        target_id=target.target_id,
        target_revision=target.revision,
        artifact_verification=artifact_verification,
        provider_identity=provider_identity,
        configured_context_window=configured_context_window,
        manifest=manifest,
    )
    return ActualModelLMStudioExecutionBinding(
        binding_id=binding_id,
        environment=environment,
        target_id=target.target_id,
        target_revision=target.revision,
        artifact_verification=artifact_verification,
        provider_identity=provider_identity,
        configured_context_window=configured_context_window,
        manifest=manifest,
    )


async def run_lm_studio_actual_model_scenario_definition(
    *,
    environment: LMStudioExecutionEnvironment,
    target: ActualModelArtifactTarget,
    artifact_verification: ActualModelArtifactVerification,
    configured_context_window: int,
    scenario_set: ActualModelScenarioSet,
    scenario_id: str,
    fixture_root: str | Path,
    workspace_root: str | Path,
    provider: LMStudioOpenAICompatibleProvider,
    manifest: ActualModelRunManifest,
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
) -> ActualModelLMStudioExecutionResult:
    """Execute only after the citable LM Studio condition is bound fail-closed."""

    binding = bind_lm_studio_execution_condition(
        environment=environment,
        target=target,
        artifact_verification=artifact_verification,
        provider=provider,
        manifest=manifest,
        configured_context_window=configured_context_window,
    )
    execution = await run_actual_model_scenario_definition(
        scenario_set=scenario_set,
        scenario_id=scenario_id,
        fixture_root=fixture_root,
        workspace_root=workspace_root,
        provider=provider,
        manifest=manifest,
        cognitive_budget=cognitive_budget,
    )
    return ActualModelLMStudioExecutionResult(
        execution_id=_stable_lm_studio_execution_id(
            binding_id=binding.binding_id,
            scenario_execution_id=execution.execution_id,
        ),
        binding=binding,
        execution=execution,
    )


def write_lm_studio_actual_model_execution_result(
    *,
    result: ActualModelLMStudioExecutionResult,
    artifact_root: str | Path,
) -> Path:
    """Persist one condition-bound result without allowing same-ID evidence replacement."""

    if not isinstance(result, ActualModelLMStudioExecutionResult):
        raise TypeError("result must be ActualModelLMStudioExecutionResult")

    expected_binding_id = _stable_lm_studio_binding_id(
        environment=result.binding.environment,
        target_id=result.binding.target_id,
        target_revision=result.binding.target_revision,
        artifact_verification=result.binding.artifact_verification,
        provider_identity=result.binding.provider_identity,
        configured_context_window=result.binding.configured_context_window,
        manifest=result.binding.manifest,
    )
    if result.binding.binding_id != expected_binding_id:
        raise ActualModelLMStudioBindingError(
            "binding_id does not match LM Studio binding evidence"
        )

    expected_scenario_execution_id = _stable_execution_id(
        plan=result.execution.plan,
        run_id=result.execution.run_id,
    )
    if result.execution.execution_id != expected_scenario_execution_id:
        raise ActualModelLMStudioBindingError(
            "scenario execution_id does not match execution evidence"
        )

    try:
        validate_actual_model_execution_result(result.execution)
    except (ActualModelExecutionArtifactError, TypeError) as exc:
        raise ActualModelLMStudioBindingError(
            f"scenario execution is not citable: {exc}"
        ) from exc
    if result.binding.manifest != result.execution.plan.manifest:
        raise ActualModelLMStudioBindingError(
            "binding manifest does not match scenario execution plan"
        )

    expected_execution_id = _stable_lm_studio_execution_id(
        binding_id=result.binding.binding_id,
        scenario_execution_id=result.execution.execution_id,
    )
    if result.execution_id != expected_execution_id:
        raise ActualModelLMStudioBindingError(
            "execution_id does not match LM Studio execution evidence"
        )

    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{result.execution_id}.lm-studio.json"
    payload = result.to_json() + "\n"

    if path.exists():
        return _resolve_existing(path=path, payload=payload)

    temporary = root / f".{result.execution_id}.{os.getpid()}.tmp"
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
        raise ActualModelLMStudioBindingError(
            f"cannot persist LM Studio actual-model execution artifact: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def _stable_lm_studio_binding_id(
    *,
    environment: LMStudioExecutionEnvironment,
    target_id: str,
    target_revision: str,
    artifact_verification: ActualModelArtifactVerification,
    provider_identity: OpenAICompatibleProviderIdentity,
    configured_context_window: int,
    manifest: ActualModelRunManifest,
) -> str:
    return _stable_id(
        prefix="amlsb",
        payload={
            "environment": environment.to_mapping(),
            "target": {
                "id": target_id,
                "revision": target_revision,
            },
            "artifact_verification": artifact_verification.to_mapping(),
            "provider_identity": provider_identity.to_mapping(),
            "configured_context_window": configured_context_window,
            "manifest": manifest.to_mapping(),
        },
    )


def _stable_lm_studio_execution_id(
    *,
    binding_id: str,
    scenario_execution_id: str,
) -> str:
    return _stable_id(
        prefix="amlsx",
        payload={
            "binding_id": binding_id,
            "scenario_execution_id": scenario_execution_id,
        },
    )


def _validate_artifact_verification(
    *,
    target: ActualModelArtifactTarget,
    artifact_verification: ActualModelArtifactVerification,
) -> None:
    if artifact_verification.target_id != target.target_id:
        raise ActualModelLMStudioBindingError(
            "artifact verification target_id does not match the frozen target"
        )
    if artifact_verification.target_revision != target.revision:
        raise ActualModelLMStudioBindingError(
            "artifact verification target_revision does not match the frozen target"
        )
    if artifact_verification.artifact_size_bytes != target.artifact_size_bytes:
        raise ActualModelLMStudioBindingError(
            "artifact verification size does not match the frozen target"
        )
    if artifact_verification.artifact_sha256 != target.artifact_sha256:
        raise ActualModelLMStudioBindingError(
            "artifact verification SHA256 does not match the frozen target"
        )


def _resolve_existing(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelLMStudioBindingError(
            f"cannot read existing LM Studio execution artifact: {exc}"
        ) from exc
    if existing == payload:
        return path
    raise ActualModelLMStudioBindingError(
        "LM Studio execution ID already exists with different evidence; "
        "use a distinct replicate_id"
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

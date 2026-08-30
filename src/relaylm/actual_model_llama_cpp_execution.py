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
from relaylm.actual_model_llama_cpp import LlamaCppRuntimeIdentity
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


ACTUAL_MODEL_LLAMA_CPP_BINDING_FORMAT_VERSION = 1
LLAMA_CPP_MANIFEST_PROVIDER_IDENTITY_PREFIX = "actual-model-llama-cpp-v1:"


class ActualModelLlamaCppBindingError(ValueError):
    """The declared citable llama.cpp condition does not match executable authority."""


class LlamaCppOpenAICompatibleProvider(Protocol):
    """OpenAI-compatible provider surface consumed by the llama.cpp binding."""

    model: str
    decoding_config: OpenAICompatibleDecodingConfig
    decoding_capabilities: OpenAICompatibleDecodingCapabilities

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput: ...


def llama_cpp_manifest_provider_identity(
    runtime_identity: LlamaCppRuntimeIdentity,
) -> str:
    """Return the canonical secret-free provider identity stored in run manifests."""

    if not isinstance(runtime_identity, LlamaCppRuntimeIdentity):
        raise TypeError("runtime_identity must be LlamaCppRuntimeIdentity")
    encoded = json.dumps(
        _runtime_identity_mapping(runtime_identity),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return LLAMA_CPP_MANIFEST_PROVIDER_IDENTITY_PREFIX + encoded


@dataclass(frozen=True, slots=True)
class ActualModelLlamaCppExecutionBinding:
    """Fail-before-generation proof that llama.cpp, target, provider, and manifest agree."""

    binding_id: str
    runtime_identity: LlamaCppRuntimeIdentity
    target_id: str
    target_revision: str
    artifact_verification: ActualModelArtifactVerification
    provider_identity: OpenAICompatibleProviderIdentity
    manifest: ActualModelRunManifest
    format_version: int = ACTUAL_MODEL_LLAMA_CPP_BINDING_FORMAT_VERSION

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "binding_id": self.binding_id,
            "runtime_identity": _runtime_identity_mapping(self.runtime_identity),
            "target": {
                "id": self.target_id,
                "revision": self.target_revision,
            },
            "artifact_verification": self.artifact_verification.to_mapping(),
            "provider_identity": self.provider_identity.to_mapping(),
            "manifest": self.manifest.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class ActualModelLlamaCppExecutionResult:
    """Existing scenario execution wrapped with its verified llama.cpp condition."""

    execution_id: str
    binding: ActualModelLlamaCppExecutionBinding
    execution: ActualModelScenarioExecutionResult
    format_version: int = ACTUAL_MODEL_LLAMA_CPP_BINDING_FORMAT_VERSION

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


def bind_llama_cpp_execution_condition(
    *,
    runtime_identity: LlamaCppRuntimeIdentity,
    target: ActualModelArtifactTarget,
    artifact_verification: ActualModelArtifactVerification,
    provider: LlamaCppOpenAICompatibleProvider,
    manifest: ActualModelRunManifest,
) -> ActualModelLlamaCppExecutionBinding:
    """Bind only values proved by live llama.cpp attestation or frozen target authority."""

    if not isinstance(runtime_identity, LlamaCppRuntimeIdentity):
        raise TypeError("runtime_identity must be LlamaCppRuntimeIdentity")
    if not isinstance(target, ActualModelArtifactTarget):
        raise TypeError("target must be ActualModelArtifactTarget")
    if not isinstance(artifact_verification, ActualModelArtifactVerification):
        raise TypeError("artifact_verification must be ActualModelArtifactVerification")
    if not isinstance(manifest, ActualModelRunManifest):
        raise TypeError("manifest must be ActualModelRunManifest")

    _validate_artifact_verification(
        target=target,
        artifact_verification=artifact_verification,
    )
    if runtime_identity.context_shift_enabled:
        raise ActualModelLlamaCppBindingError(
            "llama.cpp context shift must be disabled for citable execution"
        )
    if runtime_identity.artifact_sha256 != target.artifact_sha256:
        raise ActualModelLlamaCppBindingError(
            "runtime artifact_sha256 does not match the frozen GGUF target"
        )
    if runtime_identity.model_ftype != target.quantization:
        raise ActualModelLlamaCppBindingError(
            "runtime model_ftype does not match the frozen GGUF quantization"
        )

    provider_identity = describe_openai_compatible_provider(provider)
    if runtime_identity.model_alias != provider_identity.model:
        raise ActualModelLlamaCppBindingError(
            "llama.cpp model alias does not match the constructed provider model"
        )

    expected_manifest_provider_identity = llama_cpp_manifest_provider_identity(
        runtime_identity
    )
    if manifest.provider_identity != expected_manifest_provider_identity:
        raise ActualModelLlamaCppBindingError(
            "manifest provider_identity does not match the llama.cpp runtime identity"
        )
    if manifest.adapter_identity != provider_identity.adapter_identity:
        raise ActualModelLlamaCppBindingError(
            "manifest adapter_identity does not match provider-owned identity"
        )
    if manifest.model_artifact != target.model_artifact_identity:
        raise ActualModelLlamaCppBindingError(
            "manifest model_artifact does not match the verified frozen target"
        )
    if manifest.tokenizer_identity != target.tokenizer_identity:
        raise ActualModelLlamaCppBindingError(
            "manifest tokenizer_identity does not match the verified GGUF tokenizer"
        )
    if manifest.effective_context_window != runtime_identity.context_limit:
        raise ActualModelLlamaCppBindingError(
            "manifest effective_context_window does not match the attested llama.cpp context"
        )

    expected_decoding = tuple(
        sorted(provider_identity.effective_decoding_configuration.items())
    )
    if tuple(sorted(manifest.decoding_configuration)) != expected_decoding:
        raise ActualModelLlamaCppBindingError(
            "manifest decoding_configuration does not match applied provider request controls"
        )
    if tuple(sorted(manifest.provider_capabilities)) != provider_identity.provider_capabilities:
        raise ActualModelLlamaCppBindingError(
            "manifest provider_capabilities do not match provider-owned capabilities"
        )
    applied_seed = provider_identity.effective_decoding_configuration.get("seed")
    if manifest.seed != applied_seed:
        raise ActualModelLlamaCppBindingError(
            "manifest seed does not match the seed actually carried by the provider"
        )

    binding_id = _stable_llama_cpp_binding_id(
        runtime_identity=runtime_identity,
        target_id=target.target_id,
        target_revision=target.revision,
        artifact_verification=artifact_verification,
        provider_identity=provider_identity,
        manifest=manifest,
    )
    return ActualModelLlamaCppExecutionBinding(
        binding_id=binding_id,
        runtime_identity=runtime_identity,
        target_id=target.target_id,
        target_revision=target.revision,
        artifact_verification=artifact_verification,
        provider_identity=provider_identity,
        manifest=manifest,
    )


async def run_llama_cpp_actual_model_scenario_definition(
    *,
    runtime_identity: LlamaCppRuntimeIdentity,
    target: ActualModelArtifactTarget,
    artifact_verification: ActualModelArtifactVerification,
    scenario_set: ActualModelScenarioSet,
    scenario_id: str,
    fixture_root: str | Path,
    workspace_root: str | Path,
    provider: LlamaCppOpenAICompatibleProvider,
    manifest: ActualModelRunManifest,
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
) -> ActualModelLlamaCppExecutionResult:
    """Execute existing scenario semantics only after the llama.cpp condition is bound."""

    binding = bind_llama_cpp_execution_condition(
        runtime_identity=runtime_identity,
        target=target,
        artifact_verification=artifact_verification,
        provider=provider,
        manifest=manifest,
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
    return ActualModelLlamaCppExecutionResult(
        execution_id=_stable_llama_cpp_execution_id(
            binding_id=binding.binding_id,
            scenario_execution_id=execution.execution_id,
        ),
        binding=binding,
        execution=execution,
    )


def write_llama_cpp_actual_model_execution_result(
    *,
    result: ActualModelLlamaCppExecutionResult,
    artifact_root: str | Path,
) -> Path:
    """Persist one llama.cpp-bound result without allowing same-ID evidence replacement."""

    if not isinstance(result, ActualModelLlamaCppExecutionResult):
        raise TypeError("result must be ActualModelLlamaCppExecutionResult")

    expected_binding_id = _stable_llama_cpp_binding_id(
        runtime_identity=result.binding.runtime_identity,
        target_id=result.binding.target_id,
        target_revision=result.binding.target_revision,
        artifact_verification=result.binding.artifact_verification,
        provider_identity=result.binding.provider_identity,
        manifest=result.binding.manifest,
    )
    if result.binding.binding_id != expected_binding_id:
        raise ActualModelLlamaCppBindingError(
            "binding_id does not match llama.cpp binding evidence"
        )

    expected_scenario_execution_id = _stable_execution_id(
        plan=result.execution.plan,
        run_id=result.execution.run_id,
    )
    if result.execution.execution_id != expected_scenario_execution_id:
        raise ActualModelLlamaCppBindingError(
            "scenario execution_id does not match execution evidence"
        )

    try:
        validate_actual_model_execution_result(result.execution)
    except (ActualModelExecutionArtifactError, TypeError) as exc:
        raise ActualModelLlamaCppBindingError(
            f"scenario execution is not citable: {exc}"
        ) from exc
    if result.binding.manifest != result.execution.plan.manifest:
        raise ActualModelLlamaCppBindingError(
            "binding manifest does not match scenario execution plan"
        )

    expected_execution_id = _stable_llama_cpp_execution_id(
        binding_id=result.binding.binding_id,
        scenario_execution_id=result.execution.execution_id,
    )
    if result.execution_id != expected_execution_id:
        raise ActualModelLlamaCppBindingError(
            "execution_id does not match llama.cpp execution evidence"
        )

    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{result.execution_id}.llama-cpp.json"
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
        raise ActualModelLlamaCppBindingError(
            f"cannot persist llama.cpp actual-model execution artifact: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def _runtime_identity_mapping(
    runtime_identity: LlamaCppRuntimeIdentity,
) -> dict[str, object]:
    return {
        "format_version": ACTUAL_MODEL_LLAMA_CPP_BINDING_FORMAT_VERSION,
        "implementation": "llama_cpp",
        "upstream_revision": runtime_identity.upstream_revision,
        "build_info": runtime_identity.build_info,
        "model_alias": runtime_identity.model_alias,
        "model_path": runtime_identity.model_path,
        "model_ftype": runtime_identity.model_ftype,
        "artifact_sha256": runtime_identity.artifact_sha256,
        "chat_template_sha256": runtime_identity.chat_template_sha256,
        "context_limit": runtime_identity.context_limit,
        "total_slots": runtime_identity.total_slots,
        "context_shift_enabled": runtime_identity.context_shift_enabled,
    }


def _stable_llama_cpp_binding_id(
    *,
    runtime_identity: LlamaCppRuntimeIdentity,
    target_id: str,
    target_revision: str,
    artifact_verification: ActualModelArtifactVerification,
    provider_identity: OpenAICompatibleProviderIdentity,
    manifest: ActualModelRunManifest,
) -> str:
    return _stable_id(
        prefix="amlcb",
        payload={
            "runtime_identity": _runtime_identity_mapping(runtime_identity),
            "target": {
                "id": target_id,
                "revision": target_revision,
            },
            "artifact_verification": artifact_verification.to_mapping(),
            "provider_identity": provider_identity.to_mapping(),
            "manifest": manifest.to_mapping(),
        },
    )


def _stable_llama_cpp_execution_id(
    *,
    binding_id: str,
    scenario_execution_id: str,
) -> str:
    return _stable_id(
        prefix="amlcx",
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
        raise ActualModelLlamaCppBindingError(
            "artifact verification target_id does not match the frozen target"
        )
    if artifact_verification.target_revision != target.revision:
        raise ActualModelLlamaCppBindingError(
            "artifact verification target_revision does not match the frozen target"
        )
    if artifact_verification.artifact_size_bytes != target.artifact_size_bytes:
        raise ActualModelLlamaCppBindingError(
            "artifact verification size does not match the frozen target"
        )
    if artifact_verification.artifact_sha256 != target.artifact_sha256:
        raise ActualModelLlamaCppBindingError(
            "artifact verification artifact_sha256 does not match the frozen target"
        )


def _resolve_existing(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelLlamaCppBindingError(
            f"cannot read existing llama.cpp execution artifact: {exc}"
        ) from exc
    if existing == payload:
        return path
    raise ActualModelLlamaCppBindingError(
        "llama.cpp execution ID already exists with different evidence; "
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

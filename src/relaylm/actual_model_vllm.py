from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from relaylm.actual_model_evaluation import ActualModelRunManifest
from relaylm.actual_model_execution import (
    ActualModelScenarioExecutionResult,
    _stable_execution_id,
    run_actual_model_scenario_definition,
)
from relaylm.actual_model_scenarios import ActualModelScenarioSet
from relaylm.actual_model_targets import (
    ActualModelRepositorySnapshotTarget,
    ActualModelRepositorySnapshotVerification,
)
from relaylm.budget_runtime import CognitiveBudgetRuntimeConfig
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_identity import (
    OpenAICompatibleProviderIdentity,
    describe_openai_compatible_provider,
)
from relaylm.providers.vllm_reasoning_capability import (
    VLLMReasoningCapabilityAttestation,
    VLLMReasoningCapabilityStatus,
)


ACTUAL_MODEL_VLLM_BINDING_FORMAT_VERSION = 1
VLLM_MANIFEST_PROVIDER_IDENTITY_PREFIX = "actual-model-vllm-v1:"


class ActualModelVLLMBindingError(ValueError):
    """The declared citable vLLM condition does not match executable authority."""


@dataclass(frozen=True, slots=True)
class ActualModelVLLMExecutionBinding:
    """Fail-before-generation proof that vLLM runtime, target, provider, and manifest agree."""

    binding_id: str
    target_id: str
    target_revision: str
    snapshot_verification: ActualModelRepositorySnapshotVerification
    snapshot_root: str
    reasoning_capability: VLLMReasoningCapabilityAttestation
    provider_identity: OpenAICompatibleProviderIdentity
    configured_context_window: int
    manifest: ActualModelRunManifest
    format_version: int = ACTUAL_MODEL_VLLM_BINDING_FORMAT_VERSION

    def to_mapping(self) -> dict[str, object]:
        capability = self.reasoning_capability
        return {
            "format_version": self.format_version,
            "binding_id": self.binding_id,
            "runtime": capability.to_mapping(),
            "target": {
                "id": self.target_id,
                "revision": self.target_revision,
                "snapshot_root": self.snapshot_root,
            },
            "snapshot_verification": self.snapshot_verification.to_mapping(),
            "provider_identity": self.provider_identity.to_mapping(),
            "configured_context_window": self.configured_context_window,
            "manifest": self.manifest.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class ActualModelVLLMExecutionResult:
    """Existing #1386 scenario execution wrapped with its verified vLLM condition."""

    execution_id: str
    binding: ActualModelVLLMExecutionBinding
    execution: ActualModelScenarioExecutionResult
    format_version: int = ACTUAL_MODEL_VLLM_BINDING_FORMAT_VERSION

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


def vllm_manifest_provider_identity(
    capability: VLLMReasoningCapabilityAttestation,
) -> str:
    """Canonical secret-free provider/runtime identity stored in #1386 run manifests."""

    if not isinstance(capability, VLLMReasoningCapabilityAttestation):
        raise TypeError("capability must be VLLMReasoningCapabilityAttestation")
    encoded = json.dumps(
        capability.to_mapping(),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return VLLM_MANIFEST_PROVIDER_IDENTITY_PREFIX + encoded


def bind_vllm_execution_condition(
    *,
    target: ActualModelRepositorySnapshotTarget,
    snapshot_verification: ActualModelRepositorySnapshotVerification,
    snapshot_root: str | Path,
    reasoning_capability: VLLMReasoningCapabilityAttestation,
    provider: OpenAICompatibleProvider,
    manifest: ActualModelRunManifest,
    configured_context_window: int,
) -> ActualModelVLLMExecutionBinding:
    """Bind only runtime facts already proved by frozen target and live attestation."""

    if not isinstance(target, ActualModelRepositorySnapshotTarget):
        raise TypeError("target must be ActualModelRepositorySnapshotTarget")
    if not isinstance(
        snapshot_verification,
        ActualModelRepositorySnapshotVerification,
    ):
        raise TypeError(
            "snapshot_verification must be ActualModelRepositorySnapshotVerification"
        )
    if not isinstance(reasoning_capability, VLLMReasoningCapabilityAttestation):
        raise TypeError("reasoning_capability must be VLLMReasoningCapabilityAttestation")
    if not isinstance(provider, OpenAICompatibleProvider):
        raise TypeError("provider must be OpenAICompatibleProvider")
    if not isinstance(manifest, ActualModelRunManifest):
        raise TypeError("manifest must be ActualModelRunManifest")
    if isinstance(configured_context_window, bool) or not isinstance(
        configured_context_window, int
    ):
        raise TypeError("configured_context_window must be an integer")
    if configured_context_window <= 0:
        raise ActualModelVLLMBindingError(
            "configured_context_window must be positive"
        )

    root = Path(snapshot_root).resolve()
    _validate_snapshot_verification(
        target=target,
        snapshot_verification=snapshot_verification,
    )
    _validate_reasoning_capability(target=target, capability=reasoning_capability)

    backend = reasoning_capability.backend_attestation
    if backend.model_root is None:
        raise ActualModelVLLMBindingError(
            "vLLM backend attestation must expose model_root for citable host binding"
        )
    if Path(backend.model_root).resolve() != root:
        raise ActualModelVLLMBindingError(
            "vLLM model_root does not match the verified snapshot root"
        )
    if backend.max_model_len is None:
        raise ActualModelVLLMBindingError(
            "vLLM backend attestation must expose max_model_len for citable host binding"
        )
    if backend.max_model_len != configured_context_window:
        raise ActualModelVLLMBindingError(
            "vLLM max_model_len does not match configured_context_window"
        )

    if provider.vllm_reasoning_capability != reasoning_capability:
        raise ActualModelVLLMBindingError(
            "provider reasoning capability does not match the bound vLLM attestation"
        )
    provider_identity = describe_openai_compatible_provider(provider)
    if provider_identity.model != reasoning_capability.request_model:
        raise ActualModelVLLMBindingError(
            "provider model does not match the attested vLLM request model"
        )

    expected_provider_identity = vllm_manifest_provider_identity(reasoning_capability)
    if manifest.provider_identity != expected_provider_identity:
        raise ActualModelVLLMBindingError(
            "manifest provider_identity does not match the vLLM runtime attestation"
        )
    if manifest.adapter_identity != provider_identity.adapter_identity:
        raise ActualModelVLLMBindingError(
            "manifest adapter_identity does not match provider-owned identity"
        )
    if manifest.model_artifact != target.model_artifact_identity:
        raise ActualModelVLLMBindingError(
            "manifest model_artifact does not match the verified frozen snapshot"
        )
    if manifest.tokenizer_identity != target.tokenizer_identity:
        raise ActualModelVLLMBindingError(
            "manifest tokenizer_identity does not match the frozen serving tokenizer"
        )
    if manifest.effective_context_window != configured_context_window:
        raise ActualModelVLLMBindingError(
            "manifest effective_context_window does not match vLLM configuration"
        )
    if manifest.cognition_pass_requests is None:
        raise ActualModelVLLMBindingError(
            "vLLM COGP5 binding requires explicit cognition pass request evidence"
        )
    if manifest.execution_path != "buffered":
        raise ActualModelVLLMBindingError(
            "vLLM COGP5 pass-request evidence currently requires buffered execution"
        )

    expected_decoding = tuple(
        sorted(provider_identity.effective_decoding_configuration.items())
    )
    if tuple(sorted(manifest.decoding_configuration)) != expected_decoding:
        raise ActualModelVLLMBindingError(
            "manifest decoding_configuration does not match provider request controls"
        )
    if tuple(sorted(manifest.provider_capabilities)) != provider_identity.provider_capabilities:
        raise ActualModelVLLMBindingError(
            "manifest provider_capabilities do not match provider-owned capabilities"
        )
    applied_seed = provider_identity.effective_decoding_configuration.get("seed")
    if manifest.seed != applied_seed:
        raise ActualModelVLLMBindingError(
            "manifest seed does not match the seed carried by the provider"
        )

    binding_id = _stable_vllm_binding_id(
        target_id=target.target_id,
        target_revision=target.revision,
        snapshot_verification=snapshot_verification,
        snapshot_root=str(root),
        reasoning_capability=reasoning_capability,
        provider_identity=provider_identity,
        configured_context_window=configured_context_window,
        manifest=manifest,
    )
    return ActualModelVLLMExecutionBinding(
        binding_id=binding_id,
        target_id=target.target_id,
        target_revision=target.revision,
        snapshot_verification=snapshot_verification,
        snapshot_root=str(root),
        reasoning_capability=reasoning_capability,
        provider_identity=provider_identity,
        configured_context_window=configured_context_window,
        manifest=manifest,
    )


async def run_vllm_actual_model_scenario_definition(
    *,
    target: ActualModelRepositorySnapshotTarget,
    snapshot_verification: ActualModelRepositorySnapshotVerification,
    snapshot_root: str | Path,
    reasoning_capability: VLLMReasoningCapabilityAttestation,
    configured_context_window: int,
    scenario_set: ActualModelScenarioSet,
    scenario_id: str,
    fixture_root: str | Path,
    workspace_root: str | Path,
    provider: OpenAICompatibleProvider,
    manifest: ActualModelRunManifest,
    cognitive_budget: CognitiveBudgetRuntimeConfig | None = None,
) -> ActualModelVLLMExecutionResult:
    """Run the existing scenario harness only after the vLLM condition is bound."""

    binding = bind_vllm_execution_condition(
        target=target,
        snapshot_verification=snapshot_verification,
        snapshot_root=snapshot_root,
        reasoning_capability=reasoning_capability,
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
    return ActualModelVLLMExecutionResult(
        execution_id=_stable_vllm_execution_id(
            binding_id=binding.binding_id,
            scenario_execution_id=execution.execution_id,
        ),
        binding=binding,
        execution=execution,
    )


def write_vllm_actual_model_execution_result(
    *,
    result: ActualModelVLLMExecutionResult,
    artifact_root: str | Path,
) -> Path:
    """Persist one condition-bound vLLM result without evidence replacement."""

    if not isinstance(result, ActualModelVLLMExecutionResult):
        raise TypeError("result must be ActualModelVLLMExecutionResult")

    expected_binding_id = _stable_vllm_binding_id(
        target_id=result.binding.target_id,
        target_revision=result.binding.target_revision,
        snapshot_verification=result.binding.snapshot_verification,
        snapshot_root=result.binding.snapshot_root,
        reasoning_capability=result.binding.reasoning_capability,
        provider_identity=result.binding.provider_identity,
        configured_context_window=result.binding.configured_context_window,
        manifest=result.binding.manifest,
    )
    if result.binding.binding_id != expected_binding_id:
        raise ActualModelVLLMBindingError(
            "binding_id does not match vLLM binding evidence"
        )

    expected_scenario_execution_id = _stable_execution_id(
        plan=result.execution.plan,
        run_id=result.execution.run_id,
    )
    if result.execution.execution_id != expected_scenario_execution_id:
        raise ActualModelVLLMBindingError(
            "scenario execution_id does not match execution evidence"
        )

    expected_execution_id = _stable_vllm_execution_id(
        binding_id=result.binding.binding_id,
        scenario_execution_id=result.execution.execution_id,
    )
    if result.execution_id != expected_execution_id:
        raise ActualModelVLLMBindingError(
            "execution_id does not match vLLM execution evidence"
        )

    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{result.execution_id}.vllm.json"
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
        raise ActualModelVLLMBindingError(
            f"cannot persist vLLM actual-model execution artifact: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def _stable_vllm_binding_id(
    *,
    target_id: str,
    target_revision: str,
    snapshot_verification: ActualModelRepositorySnapshotVerification,
    snapshot_root: str,
    reasoning_capability: VLLMReasoningCapabilityAttestation,
    provider_identity: OpenAICompatibleProviderIdentity,
    configured_context_window: int,
    manifest: ActualModelRunManifest,
) -> str:
    return _stable_id(
        prefix="amvb",
        payload={
            "runtime": reasoning_capability.to_mapping(),
            "target": {
                "id": target_id,
                "revision": target_revision,
                "snapshot_root": snapshot_root,
            },
            "snapshot_verification": snapshot_verification.to_mapping(),
            "provider_identity": provider_identity.to_mapping(),
            "configured_context_window": configured_context_window,
            "manifest": manifest.to_mapping(),
        },
    )


def _stable_vllm_execution_id(
    *,
    binding_id: str,
    scenario_execution_id: str,
) -> str:
    return _stable_id(
        prefix="amvx",
        payload={
            "binding_id": binding_id,
            "scenario_execution_id": scenario_execution_id,
        },
    )


def _validate_snapshot_verification(
    *,
    target: ActualModelRepositorySnapshotTarget,
    snapshot_verification: ActualModelRepositorySnapshotVerification,
) -> None:
    if snapshot_verification.target_id != target.target_id:
        raise ActualModelVLLMBindingError(
            "snapshot verification target_id does not match the frozen target"
        )
    if snapshot_verification.target_revision != target.revision:
        raise ActualModelVLLMBindingError(
            "snapshot verification target_revision does not match the frozen target"
        )
    if snapshot_verification.verified_file_count != len(target.files):
        raise ActualModelVLLMBindingError(
            "snapshot verification verified file count does not match the frozen target"
        )


def _validate_reasoning_capability(
    *,
    target: ActualModelRepositorySnapshotTarget,
    capability: VLLMReasoningCapabilityAttestation,
) -> None:
    if capability.target_id != target.target_id:
        raise ActualModelVLLMBindingError(
            "vLLM reasoning capability target_id does not match the frozen target"
        )
    if capability.target_revision != target.revision:
        raise ActualModelVLLMBindingError(
            "vLLM reasoning capability target_revision does not match the frozen target"
        )
    if capability.model_artifact_identity != target.model_artifact_identity:
        raise ActualModelVLLMBindingError(
            "vLLM reasoning capability model artifact does not match the frozen target"
        )
    if capability.artifact_repository_revision != target.artifact_repository_revision:
        raise ActualModelVLLMBindingError(
            "vLLM reasoning capability repository revision does not match the frozen target"
        )
    if capability.reasoning_parser is None:
        raise ActualModelVLLMBindingError(
            "vLLM reasoning capability requires an explicit reasoning parser"
        )
    if capability.template_thinking_control is None:
        raise ActualModelVLLMBindingError(
            "vLLM reasoning capability requires an explicit template thinking control"
        )
    if (
        capability.reasoning_off.status
        is not VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
    ):
        raise ActualModelVLLMBindingError(
            "vLLM OFF reasoning capability is not semantically attested"
        )
    if (
        capability.reasoning_bounded.status
        is not VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
    ):
        raise ActualModelVLLMBindingError(
            "vLLM bounded reasoning capability is not semantically attested"
        )


def _resolve_existing(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelVLLMBindingError(
            f"cannot read existing vLLM execution artifact: {exc}"
        ) from exc
    if existing == payload:
        return path
    raise ActualModelVLLMBindingError(
        "vLLM execution ID already exists with different evidence; use a distinct replicate_id"
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

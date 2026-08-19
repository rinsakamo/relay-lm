from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from relaylm.actual_model_targets import (
    ActualModelArtifactTarget,
)
from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.providers.openai_compatible_budget import (
    OpenAICompatibleSerializedInputCounter,
    SerializedInputCounterIdentity,
)


LM_STUDIO_GEMMA4_COUNTER_CAPABILITY = (
    "lmstudio.gemma4.loaded-sdk.serialized-input.v1"
)
LM_STUDIO_COUNTER_IMPLEMENTATION = "lmstudio-js-loaded-model-counter"
LM_STUDIO_COUNTER_VERSION = "2"
LM_STUDIO_SDK_PACKAGE = "@lmstudio/sdk"
LM_STUDIO_PROMPT_METHOD = "loaded-model.applyPromptTemplate->countTokens"
LM_STUDIO_FRAMING_METHOD = "empty-user-message-baseline-v1"
LM_STUDIO_ARTIFACT_LINK_METHOD = "lmstudio-model-index-cache-entrypoint-v1"
LM_STUDIO_STRUCTURED_OUTPUT_EFFECT = "server-prompt-tokens-equal-sdk-messages-only"
LM_STUDIO_CHAT_MAPPING = "request-messages-role-content-lossless-v1"
LM_STUDIO_MODEL_BINDING_METHOD = "openai-request-model-to-loaded-instance-proof-v1"
LM_STUDIO_PROMPT_PARITY_METHOD = "sdk-template-count-vs-server-usage-probe-v1"
LM_STUDIO_REQUIRED_PROBE_IDS = frozenset(
    {
        "minimal-identity-current-event",
        "japanese-input",
        "ascii-input",
        "accepted-state",
        "working-context",
        "retrieved-memory",
        "event-evidence",
        "larger-mixed",
    }
)


class LMStudioCounterError(ValueError):
    """The host-local LM Studio counter cannot prove its declared behavior."""


@dataclass(frozen=True, slots=True)
class LMStudioCounterProof:
    """Secret-free attestation produced by the host validation probe."""

    format_version: int
    attestation: str
    capability: str
    implementation: str
    version: str
    relaylm_commit: str
    target_id: str
    request_model: str
    lm_studio_version: str
    lm_studio_build: str
    deployment_identity: str
    model_key: str
    model_path: str
    artifact_model_key: str
    artifact_path: str
    quantization: str
    loaded_size_bytes: int
    artifact_size_bytes: int
    artifact_sha256: str
    instance_reference_sha256: str
    sdk_package: str
    sdk_version: str
    probe_count: int
    structured_output_verdict: str
    structured_output_with_schema_tokens: int
    structured_output_without_schema_tokens: int
    framing_accounting_verdict: str
    sdk_framing_tokens: int
    server_framing_tokens: int
    server_prompt_token_offset: int


def build_lm_studio_counter_capabilities(
    *,
    condition: Any,
    target: ActualModelArtifactTarget,
    artifact_path: str | Path,
    proof_path: str | Path | None,
    node_path: str | Path | None = None,
    sdk_root: str | Path | None = None,
) -> Mapping[str, Any]:
    """Build the allowlisted exact capability for the frozen LM Studio target.

    The import of ``HostTokenCounterCapability`` is intentionally local. This
    module is a host-only boundary and must not become a dependency of the
    ordinary RelayLM runtime or create an import cycle with the host runner.
    """

    if condition.target_id != target.target_id:
        raise LMStudioCounterError(
            "LM Studio counter target does not match the host condition"
        )
    if target.target_id != "gemma-4-12b-it-q4-k-m-lmstudio-community-v1":
        raise LMStudioCounterError(
            "LM Studio SDK counter is allowlisted only for the frozen Community Gemma target"
        )
    if proof_path is None:
        raise LMStudioCounterError(
            "an exact LM Studio counter proof artifact is required for v3 execution"
        )

    proof = load_lm_studio_counter_proof(proof_path)
    _validate_proof_against_condition(
        proof=proof,
        condition=condition,
        target=target,
        artifact_path=artifact_path,
    )

    transport = _LMStudioSdkTransport(
        base_url=condition.base_url,
        request_model=condition.request_model,
        expected_model_key=proof.model_key,
        artifact_path=artifact_path,
        expected_artifact_size=target.artifact_size_bytes,
        node_path=node_path,
        sdk_root=sdk_root,
        server_prompt_token_offset=proof.server_prompt_token_offset,
    )
    loaded_identity = transport.attest()
    _validate_loaded_identity(
        loaded_identity=loaded_identity,
        proof=proof,
        target=target,
        artifact_path=artifact_path,
    )

    identity = SerializedInputCounterIdentity(
        capability=LM_STUDIO_GEMMA4_COUNTER_CAPABILITY,
        implementation=LM_STUDIO_COUNTER_IMPLEMENTATION,
        version=LM_STUDIO_COUNTER_VERSION,
        mode=TokenCountMode.EXACT,
        tokenizer_identity=target.tokenizer_identity,
        parameters=tuple(
            sorted(
                {
                    "chat_mapping": LM_STUDIO_CHAT_MAPPING,
                    "framing_method": LM_STUDIO_FRAMING_METHOD,
                    "prompt_method": LM_STUDIO_PROMPT_METHOD,
                    "server_prompt_offset": proof.server_prompt_token_offset,
                    "sdk_package": proof.sdk_package,
                    "sdk_version": proof.sdk_version,
                    "structured_effect": LM_STUDIO_STRUCTURED_OUTPUT_EFFECT,
                    "vocab_source": "loaded-gguf-serving-instance",
                }.items()
            )
        ),
    )

    from relaylm.actual_model_host_runner import HostTokenCounterCapability

    def factory(host_condition: Any, provider: Any) -> OpenAICompatibleSerializedInputCounter:
        if host_condition.request_model != condition.request_model:
            raise LMStudioCounterError(
                "LM Studio counter condition request_model drifted during construction"
            )
        if provider.model != condition.request_model:
            raise LMStudioCounterError(
                "LM Studio counter provider model does not match the attested model"
            )
        return OpenAICompatibleSerializedInputCounter(
            model=provider.model,
            count_input=transport.count_input,
            decoding_config=provider.decoding_config,
            evidence_identity=identity,
        )

    return {
        LM_STUDIO_GEMMA4_COUNTER_CAPABILITY: HostTokenCounterCapability(
            factory=factory,
            exact_behavior_demonstrated=True,
            conservative_bound_demonstrated=False,
        )
    }


def load_lm_studio_counter_proof(path: str | Path) -> LMStudioCounterProof:
    source = Path(path)
    try:
        raw = json.loads(
            source.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LMStudioCounterError(f"cannot load LM Studio counter proof: {exc}") from exc

    mapping = _require_mapping(raw, "LM Studio counter proof")
    _require_exact_keys(
        mapping,
        {
            "format_version",
            "attestation",
            "capability",
            "implementation",
            "version",
            "relaylm_commit",
            "target_id",
            "request_model",
            "lm_studio",
            "loaded_model",
            "sdk",
            "probe_matrix",
            "model_binding",
            "prompt_template_parity",
            "structured_output",
            "artifact_linkage",
            "framing_accounting",
        },
        "LM Studio counter proof",
    )
    lm_studio = _require_mapping(mapping["lm_studio"], "proof.lm_studio")
    _require_exact_keys(
        lm_studio,
        {"version", "build", "deployment_identity"},
        "proof.lm_studio",
    )
    loaded_model = _require_mapping(mapping["loaded_model"], "proof.loaded_model")
    _require_exact_keys(
        loaded_model,
        {
            "model_key",
            "path",
            "artifact_model_key",
            "artifact_path",
            "quantization",
            "size_bytes",
            "artifact_size_bytes",
            "sha256",
            "instance_reference_sha256",
        },
        "proof.loaded_model",
    )
    sdk = _require_mapping(mapping["sdk"], "proof.sdk")
    _require_exact_keys(
        sdk,
        {"package", "version", "prompt_template_method", "tokenizer_method"},
        "proof.sdk",
    )
    framing = _require_mapping(mapping["framing_accounting"], "proof.framing_accounting")
    _require_exact_keys(
        framing,
        {
            "method",
            "sdk_framing_tokens",
            "server_framing_tokens",
            "server_prompt_token_offset",
            "verdict",
        },
        "proof.framing_accounting",
    )
    if _require_string(framing["method"], "proof.framing_accounting.method") != (
        LM_STUDIO_FRAMING_METHOD
    ):
        raise LMStudioCounterError(
            "LM Studio required-input framing accounting method is unsupported"
        )
    sdk_framing_tokens = _require_int(
        framing["sdk_framing_tokens"],
        "proof.framing_accounting.sdk_framing_tokens",
    )
    server_framing_tokens = _require_int(
        framing["server_framing_tokens"],
        "proof.framing_accounting.server_framing_tokens",
    )
    server_prompt_token_offset = _require_int(
        framing["server_prompt_token_offset"],
        "proof.framing_accounting.server_prompt_token_offset",
    )
    if (
        sdk_framing_tokens < 0
        or server_framing_tokens < 0
        or server_prompt_token_offset < 0
    ):
        raise LMStudioCounterError(
            "LM Studio framing token values must be non-negative"
        )
    if server_framing_tokens != sdk_framing_tokens + server_prompt_token_offset:
        raise LMStudioCounterError(
            "LM Studio framing baseline does not reproduce the server offset"
        )
    probes = _require_list(mapping["probe_matrix"], "proof.probe_matrix")
    if len(probes) < 8:
        raise LMStudioCounterError(
            "LM Studio counter proof requires at least eight validation probes"
        )
    probe_ids: set[str] = set()
    for index, probe in enumerate(probes, start=1):
        probe_map = _require_mapping(probe, f"proof.probe_matrix[{index}]")
        _require_exact_keys(
            probe_map,
            {
                "probe_id",
                "request_sha256",
                "sdk_prompt_tokens",
                "server_prompt_tokens",
                "accounted_prompt_tokens",
                "raw_equal",
                "equal",
            },
            f"proof.probe_matrix[{index}]",
        )
        probe_id = _require_string(
            probe_map["probe_id"], f"proof.probe_matrix[{index}].probe_id"
        )
        if probe_id in probe_ids:
            raise LMStudioCounterError("LM Studio counter proof probe IDs must be unique")
        probe_ids.add(probe_id)
        _require_digest(
            probe_map["request_sha256"],
            f"proof.probe_matrix[{index}].request_sha256",
        )
        sdk_count = _require_int(
            probe_map["sdk_prompt_tokens"],
            f"proof.probe_matrix[{index}].sdk_prompt_tokens",
        )
        server_count = _require_int(
            probe_map["server_prompt_tokens"],
            f"proof.probe_matrix[{index}].server_prompt_tokens",
        )
        accounted_count = _require_int(
            probe_map["accounted_prompt_tokens"],
            f"proof.probe_matrix[{index}].accounted_prompt_tokens",
        )
        raw_equal = probe_map["raw_equal"]
        equal = probe_map["equal"]
        if not isinstance(raw_equal, bool) or not isinstance(equal, bool):
            raise LMStudioCounterError(
                f"LM Studio counter proof equality fields must be boolean for probe {probe_id}"
            )
        if sdk_count < 0 or server_count < 0 or accounted_count < 0:
            raise LMStudioCounterError("LM Studio counter proof token counts must be non-negative")
        if raw_equal is not (sdk_count == server_count):
            raise LMStudioCounterError(
                f"LM Studio counter proof raw equality flag is wrong for probe {probe_id}"
            )
        if accounted_count != sdk_count + server_prompt_token_offset:
            raise LMStudioCounterError(
                f"LM Studio counter proof accounted count is wrong for probe {probe_id}"
            )
        if equal is not (accounted_count == server_count):
            raise LMStudioCounterError(
                f"LM Studio counter proof accounted equality flag is wrong for probe {probe_id}"
            )
    missing_probe_ids = sorted(LM_STUDIO_REQUIRED_PROBE_IDS - probe_ids)
    if missing_probe_ids:
        raise LMStudioCounterError(
            "LM Studio counter proof is missing required probes: "
            + ", ".join(missing_probe_ids)
        )
    artifact_linkage = _require_mapping(
        mapping["artifact_linkage"], "proof.artifact_linkage"
    )
    _require_exact_keys(
        artifact_linkage,
        {"method", "verdict"},
        "proof.artifact_linkage",
    )
    if _require_string(
        artifact_linkage["method"], "proof.artifact_linkage.method"
    ) != LM_STUDIO_ARTIFACT_LINK_METHOD or _require_string(
        artifact_linkage["verdict"], "proof.artifact_linkage.verdict"
    ) != "same-frozen-entrypoint":
        raise LMStudioCounterError(
            "LM Studio loaded instance to frozen artifact linkage is not proven"
        )
    model_binding = _require_mapping(
        mapping["model_binding"], "proof.model_binding"
    )
    _require_exact_keys(
        model_binding,
        {"method", "verdict"},
        "proof.model_binding",
    )
    if _require_string(model_binding["method"], "proof.model_binding.method") != (
        LM_STUDIO_MODEL_BINDING_METHOD
    ) or _require_string(model_binding["verdict"], "proof.model_binding.verdict") != (
        "same-loaded-instance"
    ):
        raise LMStudioCounterError(
            "LM Studio request-model to loaded-instance binding is not proven"
        )
    prompt_template_parity = _require_mapping(
        mapping["prompt_template_parity"], "proof.prompt_template_parity"
    )
    _require_exact_keys(
        prompt_template_parity,
        {"method", "verdict"},
        "proof.prompt_template_parity",
    )
    if _require_string(
        prompt_template_parity["method"], "proof.prompt_template_parity.method"
    ) != LM_STUDIO_PROMPT_PARITY_METHOD or _require_string(
        prompt_template_parity["verdict"], "proof.prompt_template_parity.verdict"
    ) != "all-required-probes-accounted-equal":
        raise LMStudioCounterError(
            "LM Studio prompt-template parity is not proven"
        )
    structured = _require_mapping(
        mapping["structured_output"], "proof.structured_output"
    )
    _require_exact_keys(
        structured,
        {
            "comparison",
            "with_schema_prompt_tokens",
            "without_schema_prompt_tokens",
            "schema_token_delta",
            "verdict",
        },
        "proof.structured_output",
    )
    if _require_string(structured["comparison"], "proof.structured_output.comparison") != (
        "response_format-json-schema-vs-messages-only"
    ):
        raise LMStudioCounterError(
            "LM Studio structured-output comparison method is unsupported"
        )
    structured_with_schema = _require_int(
        structured["with_schema_prompt_tokens"],
        "proof.structured_output.with_schema_prompt_tokens",
    )
    structured_without_schema = _require_int(
        structured["without_schema_prompt_tokens"],
        "proof.structured_output.without_schema_prompt_tokens",
    )
    structured_delta = _require_int(
        structured["schema_token_delta"], "proof.structured_output.schema_token_delta"
    )
    if (
        structured_with_schema < 0
        or structured_without_schema < 0
        or structured_delta != structured_with_schema - structured_without_schema
    ):
        raise LMStudioCounterError(
            "LM Studio structured-output proof has inconsistent prompt-token counts"
        )
    if structured_delta != 0:
        raise LMStudioCounterError(
            "LM Studio structured-output proof reports token-bearing schema framing"
        )
    if _require_string(structured["verdict"], "proof.structured_output.verdict") != (
        "no-token-bearing-prompt-delta"
    ):
        raise LMStudioCounterError(
            "LM Studio structured-output behavior is not proven messages-only"
        )
    if _require_string(framing["verdict"], "proof.framing_accounting.verdict") != (
        "reproducible"
    ):
        raise LMStudioCounterError(
            "LM Studio required-input framing accounting is not proven"
        )

    try:
        proof = LMStudioCounterProof(
            format_version=_require_int(mapping["format_version"], "proof.format_version"),
            attestation=_require_string(mapping["attestation"], "proof.attestation"),
            capability=_require_string(mapping["capability"], "proof.capability"),
            implementation=_require_string(
                mapping["implementation"], "proof.implementation"
            ),
            version=_require_string(mapping["version"], "proof.version"),
            relaylm_commit=_require_string(
                mapping["relaylm_commit"], "proof.relaylm_commit"
            ),
            target_id=_require_string(mapping["target_id"], "proof.target_id"),
            request_model=_require_string(
                mapping["request_model"], "proof.request_model"
            ),
            lm_studio_version=_require_string(
                lm_studio["version"], "proof.lm_studio.version"
            ),
            lm_studio_build=_require_string(lm_studio["build"], "proof.lm_studio.build"),
            deployment_identity=_require_string(
                lm_studio["deployment_identity"],
                "proof.lm_studio.deployment_identity",
            ),
            model_key=_require_string(loaded_model["model_key"], "proof.loaded_model.model_key"),
            model_path=_require_string(loaded_model["path"], "proof.loaded_model.path"),
            artifact_model_key=_require_string(
                loaded_model["artifact_model_key"],
                "proof.loaded_model.artifact_model_key",
            ),
            artifact_path=_require_string(
                loaded_model["artifact_path"],
                "proof.loaded_model.artifact_path",
            ),
            quantization=_require_string(
                loaded_model["quantization"], "proof.loaded_model.quantization"
            ),
            loaded_size_bytes=_require_int(
                loaded_model["size_bytes"], "proof.loaded_model.size_bytes"
            ),
            artifact_size_bytes=_require_int(
                loaded_model["artifact_size_bytes"],
                "proof.loaded_model.artifact_size_bytes",
            ),
            artifact_sha256=_require_digest(
                loaded_model["sha256"], "proof.loaded_model.sha256"
            ),
            instance_reference_sha256=_require_digest(
                loaded_model["instance_reference_sha256"],
                "proof.loaded_model.instance_reference_sha256",
            ),
            sdk_package=_require_string(sdk["package"], "proof.sdk.package"),
            sdk_version=_require_string(sdk["version"], "proof.sdk.version"),
            probe_count=len(probes),
            structured_output_verdict=_require_string(
                structured["verdict"], "proof.structured_output.verdict"
            ),
            structured_output_with_schema_tokens=structured_with_schema,
            structured_output_without_schema_tokens=structured_without_schema,
            framing_accounting_verdict=_require_string(
                framing["verdict"], "proof.framing_accounting.verdict"
            ),
            sdk_framing_tokens=sdk_framing_tokens,
            server_framing_tokens=server_framing_tokens,
            server_prompt_token_offset=server_prompt_token_offset,
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, LMStudioCounterError):
            raise
        raise LMStudioCounterError(f"invalid LM Studio counter proof: {exc}") from exc

    if proof.format_version != 2:
        raise LMStudioCounterError(
            f"unsupported LM Studio counter proof format_version: {proof.format_version}"
        )
    if proof.attestation != "exact":
        raise LMStudioCounterError(
            "LM Studio counter proof is not an exact attestation"
        )
    if proof.capability != LM_STUDIO_GEMMA4_COUNTER_CAPABILITY:
        raise LMStudioCounterError("LM Studio counter proof capability is not allowlisted")
    if proof.implementation != LM_STUDIO_COUNTER_IMPLEMENTATION:
        raise LMStudioCounterError(
            "LM Studio counter proof implementation is not allowlisted"
        )
    if proof.version != LM_STUDIO_COUNTER_VERSION:
        raise LMStudioCounterError("LM Studio counter proof version is unsupported")
    if proof.sdk_package != LM_STUDIO_SDK_PACKAGE:
        raise LMStudioCounterError("LM Studio counter proof SDK package is unsupported")
    if proof.sdk_version != _require_string(
        sdk["version"], "proof.sdk.version"
    ):
        raise LMStudioCounterError("LM Studio counter proof SDK version is inconsistent")
    if sdk["prompt_template_method"] != LM_STUDIO_PROMPT_METHOD:
        raise LMStudioCounterError(
            "LM Studio counter proof prompt-template method is unsupported"
        )
    if sdk["tokenizer_method"] != "loaded-model.countTokens":
        raise LMStudioCounterError(
            "LM Studio counter proof tokenizer method is unsupported"
        )
    return proof


def _validate_proof_against_condition(
    *,
    proof: LMStudioCounterProof,
    condition: Any,
    target: ActualModelArtifactTarget,
    artifact_path: str | Path,
) -> None:
    expected_artifact_model_key = f"{target.artifact_repository}/{target.artifact_filename}"
    checks = (
        (proof.relaylm_commit, condition.relaylm_commit, "RelayLM commit"),
        (proof.target_id, target.target_id, "target"),
        (proof.request_model, condition.request_model, "request model"),
        (proof.model_key, proof.request_model, "loaded request model key"),
        (proof.lm_studio_version, condition.lm_studio_version, "LM Studio version"),
        (proof.lm_studio_build, condition.lm_studio_build, "LM Studio build"),
        (proof.deployment_identity, condition.deployment_identity, "deployment identity"),
        (proof.artifact_model_key, expected_artifact_model_key, "artifact model key"),
        (proof.quantization, target.quantization, "quantization"),
        (proof.artifact_size_bytes, target.artifact_size_bytes, "artifact size"),
        (proof.artifact_sha256, target.artifact_sha256, "artifact SHA256"),
        (proof.sdk_package, LM_STUDIO_SDK_PACKAGE, "SDK package"),
    )
    for observed, expected, label in checks:
        if observed != expected:
            raise LMStudioCounterError(
                f"LM Studio counter proof {label} does not match current authority"
            )
    if proof.sdk_version.strip() == "":
        raise LMStudioCounterError("LM Studio counter proof SDK version is empty")
    if not _paths_equivalent(proof.artifact_path, artifact_path):
        raise LMStudioCounterError(
            "LM Studio counter proof artifact path does not match the selected artifact"
        )


def _validate_loaded_identity(
    *,
    loaded_identity: Mapping[str, object],
    proof: LMStudioCounterProof,
    target: ActualModelArtifactTarget,
    artifact_path: str | Path,
) -> None:
    expected = {
        "model_key": proof.model_key,
        "path": proof.model_path,
        "size_bytes": proof.loaded_size_bytes,
        "quantization": target.quantization,
        "instance_reference_sha256": proof.instance_reference_sha256,
    }
    for name, expected_value in expected.items():
        observed = loaded_identity.get(name)
        if observed != expected_value:
            raise LMStudioCounterError(
                f"loaded LM Studio model {name} does not match the frozen target"
            )
    if not _paths_equivalent(proof.artifact_path, artifact_path):
        raise LMStudioCounterError(
            "loaded LMStudio proof artifact path does not match the selected artifact"
        )
    sdk_version = loaded_identity.get("sdk_version")
    if sdk_version != proof.sdk_version:
        raise LMStudioCounterError("loaded LM Studio SDK version drifted from proof")


@dataclass(frozen=True, slots=True)
class _LMStudioSdkTransport:
    base_url: str
    request_model: str
    expected_model_key: str
    artifact_path: str | Path
    expected_artifact_size: int
    node_path: str | Path | None
    sdk_root: str | Path | None
    server_prompt_token_offset: int

    def attest(self) -> Mapping[str, object]:
        return self._invoke({"operation": "attest"})

    def count_input(self, model_input: Mapping[str, Any]) -> SerializedInputTokenCount:
        result = self._invoke(
            {
                "operation": "count",
                "model_input": model_input,
            }
        )
        total = _require_int(result.get("total_input_tokens"), "counter.total_input_tokens")
        framing = _require_int(
            result.get("required_input_framing_tokens"),
            "counter.required_input_framing_tokens",
        )
        total += self.server_prompt_token_offset
        framing += self.server_prompt_token_offset
        if total < 0 or framing < 0:
            raise LMStudioCounterError("LM Studio SDK returned a negative token count")
        if result.get("mode") != TokenCountMode.EXACT.value:
            raise LMStudioCounterError("LM Studio SDK counter returned a non-exact mode")
        return SerializedInputTokenCount(
            total_input_tokens=total,
            required_input_framing_tokens=framing,
            mode=TokenCountMode.EXACT,
        )

    def _invoke(self, payload: Mapping[str, object]) -> Mapping[str, object]:
        node = _resolve_node_path(self.node_path)
        modules = _resolve_sdk_root(self.sdk_root)
        native_base_url = _native_sdk_base_url(self.base_url)
        request = {
            "native_base_url": native_base_url,
            "request_model": self.request_model,
            "expected_model_key": self.expected_model_key,
            "artifact_path": str(self.artifact_path),
            "expected_artifact_size": self.expected_artifact_size,
            **payload,
        }
        environment = os.environ.copy()
        existing_node_path = environment.get("NODE_PATH")
        environment["NODE_PATH"] = (
            str(modules)
            if not existing_node_path
            else str(modules) + os.pathsep + existing_node_path
        )
        try:
            completed = subprocess.run(
                [node, "-e", _NODE_WORKER_SOURCE],
                input=json.dumps(request, ensure_ascii=False),
                capture_output=True,
                text=True,
                env=environment,
                check=False,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LMStudioCounterError(
                "LM Studio SDK counter process was unavailable"
            ) from exc
        if completed.returncode != 0:
            raise LMStudioCounterError(
                "LM Studio SDK counter process failed; refusing to count input"
            )
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if len(lines) != 1:
            raise LMStudioCounterError(
                "LM Studio SDK counter returned an invalid response"
            )
        try:
            result = json.loads(lines[0])
        except json.JSONDecodeError as exc:
            raise LMStudioCounterError(
                "LM Studio SDK counter returned non-JSON output"
            ) from exc
        return _require_mapping(result, "LM Studio SDK counter response")


def _resolve_node_path(value: str | Path | None) -> str:
    candidate = str(value) if value is not None else os.environ.get("RELAYLM_LMSTUDIO_NODE")
    if candidate:
        if Path(candidate).is_file():
            return candidate
        discovered = shutil.which(candidate)
        if discovered is not None:
            return discovered
        raise LMStudioCounterError(
            "configured LM Studio SDK node executable is unavailable"
        )
    discovered = shutil.which("node")
    if discovered is None:
        raise LMStudioCounterError(
            "LM Studio SDK counter requires an optional Node.js executable"
        )
    return discovered


def _resolve_sdk_root(value: str | Path | None) -> Path:
    raw = str(value) if value is not None else os.environ.get("RELAYLM_LMSTUDIO_SDK_ROOT")
    if not raw:
        raise LMStudioCounterError(
            "LM Studio SDK counter requires an explicit @lmstudio/sdk module root"
        )
    candidate = Path(raw)
    if (candidate / "@lmstudio" / "sdk" / "package.json").is_file():
        return candidate
    if (candidate / "package.json").is_file() and candidate.name == "sdk":
        node_modules = candidate.parent.parent
        if (node_modules / "@lmstudio" / "sdk" / "package.json").is_file():
            return node_modules
    raise LMStudioCounterError(
        "configured LM Studio SDK module root does not contain @lmstudio/sdk"
    )


def _native_sdk_base_url(base_url: str) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LMStudioCounterError("LM Studio base_url must be an HTTP(S) URL")
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}"


def _paths_equivalent(left: object, right: object) -> bool:
    if not isinstance(left, str) or not isinstance(right, (str, Path)):
        return False
    return _path_key(left) == _path_key(str(right))


def _path_key(value: str) -> str:
    normalized = value.replace("\\", "/").casefold()
    if normalized.startswith("\\\\?\\"):
        normalized = normalized[4:]
    if len(normalized) >= 3 and normalized[1:3] == ":/":
        normalized = "/mnt/" + normalized[0] + normalized[2:]
    return str(Path(normalized).as_posix()).rstrip("/")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LMStudioCounterError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise LMStudioCounterError(f"{label} must be a JSON object")
    return value


def _require_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise LMStudioCounterError(f"{label} must be a JSON array")
    return value


def _require_exact_keys(
    mapping: Mapping[str, object],
    expected: set[str],
    label: str,
) -> None:
    observed = set(mapping)
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    if missing:
        raise LMStudioCounterError(f"{label} is missing fields: {', '.join(missing)}")
    if unknown:
        raise LMStudioCounterError(f"{label} has unknown fields: {', '.join(unknown)}")


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LMStudioCounterError(f"{label} must be a non-empty string")
    return value


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LMStudioCounterError(f"{label} must be an integer")
    return value


def _require_digest(value: object, label: str) -> str:
    digest = _require_string(value, label)
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise LMStudioCounterError(f"{label} must be a lowercase SHA256 digest")
    return digest


_NODE_WORKER_SOURCE = r'''
const fs = require("fs");
const crypto = require("crypto");
const { LMStudioClient } = require("@lmstudio/sdk");

function scalar(value) {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return value;
  }
  if (value && typeof value === "object") {
    if (typeof value.name === "string") return value.name;
    if (typeof value.label === "string") return value.label;
    if (typeof value.type === "string") return value.type;
  }
  return String(value ?? "");
}

function fail(message) {
  process.stderr.write(message);
  process.exit(1);
}

async function closeClient(client) {
  const dispose = client && client[Symbol.asyncDispose];
  if (typeof dispose === "function") {
    await dispose.call(client);
  }
}

async function main() {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  const packagePath = require.resolve("@lmstudio/sdk");
  const packageJson = JSON.parse(fs.readFileSync(require("path").join(require("path").dirname(packagePath), "..", "package.json"), "utf8"));
  const logger = { info() {}, error() {}, warn() {}, debug() {} };
  const client = new LMStudioClient({ baseUrl: input.native_base_url, logger });
  try {
    const loaded = await client.llm.listLoaded();
    const candidates = [];
    for (const model of loaded) {
      const info = await model.getModelInfo();
      candidates.push({ model, info });
    }
    const exactKey = candidates.filter(({ info }) => info.modelKey === input.expected_model_key);
    if (exactKey.length !== 1) {
      fail("expected exactly one loaded LM Studio model instance for the frozen model key");
    }
    const selected = exactKey[0];
    const info = selected.info;
    const identity = {
      model_key: String(info.modelKey),
      path: String(info.path),
      size_bytes: Number(info.sizeBytes),
      quantization: scalar(info.quantization),
      sdk_version: String(packageJson.version),
      instance_reference_sha256: crypto.createHash("sha256").update(String(info.instanceReference)).digest("hex"),
    };
    if (input.operation === "attest") {
      process.stdout.write(JSON.stringify(identity));
      return;
    }
    if (input.operation !== "count") {
      fail("unsupported LM Studio SDK counter operation");
    }
    const body = input.model_input;
    if (!body || body.model !== input.request_model || !Array.isArray(body.messages)) {
      fail("counter input is not the canonical OpenAI-compatible request shape");
    }
    if (!body.response_format || body.response_format.type !== "json_schema" ||
        !body.response_format.json_schema || body.response_format.json_schema.strict !== true ||
        body.response_format.json_schema.name !== "relaylm_cognitive_output") {
      fail("counter input is missing the canonical structured-output schema");
    }
    const messages = body.messages.map(message => {
      if (!message || Object.keys(message).sort().join(",") !== "content,role" ||
          !["system", "user", "assistant"].includes(message.role) ||
          typeof message.content !== "string") {
        fail("counter input contains a non-lossless chat message");
      }
      return { role: message.role, content: message.content };
    });
    const formatted = await selected.model.applyPromptTemplate(messages);
    const framingMessages = messages.map(message =>
      message.role === "user" ? { role: message.role, content: "" } : message
    );
    const framingFormatted = await selected.model.applyPromptTemplate(framingMessages);
    const total = await selected.model.countTokens(formatted);
    const framing = await selected.model.countTokens(framingFormatted);
    process.stdout.write(JSON.stringify({
      ...identity,
      total_input_tokens: Number(total),
      required_input_framing_tokens: Number(framing),
      mode: "exact",
    }));
  } finally {
    await closeClient(client);
  }
}

main().catch(error => fail(String(error && error.message ? error.message : error)));
'''

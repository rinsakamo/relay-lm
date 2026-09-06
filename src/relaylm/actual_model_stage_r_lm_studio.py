from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_boundary import (
    evaluate_actual_model_deterministic_boundary,
    write_actual_model_deterministic_boundary_verdict,
)
from relaylm.actual_model_evaluation import ActualModelRunManifest
from relaylm.actual_model_execution import run_actual_model_scenario_definition
from relaylm.actual_model_execution_artifacts import write_actual_model_execution_result
from relaylm.actual_model_stage_r_semantics import (
    CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH,
    StageRSemanticAuthority,
    load_current_stage_r_scenario_set,
    load_stage_r_semantic_authority,
)
from relaylm.cognition_execution import CognitionReasoningMode
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_identity import (
    describe_openai_compatible_provider,
)
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider


CANONICAL_FIXTURE_PATH = Path("evaluation/actual_model/characters/foundation-v1")
OBSERVED_LM_STUDIO_STAGE_R_FORMAT_VERSION = 1


class LMStudioStageRError(ValueError):
    """The observed LM Studio condition cannot run current Stage R truthfully."""


@dataclass(frozen=True, slots=True)
class ObservedLMStudioModel:
    request_model: str
    loaded_instance_id: str
    display_name: str
    params_string: str | None
    quantization: str
    size_bytes: int
    context_length: int
    flash_attention: bool | None
    offload_kv_cache_to_gpu: bool | None
    reasoning_default: str | None
    reasoning_allowed_options: tuple[str, ...]
    format_version: int = OBSERVED_LM_STUDIO_STAGE_R_FORMAT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "request_model",
            "loaded_instance_id",
            "display_name",
            "quantization",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise LMStudioStageRError(f"{name} must be a non-empty string")
        if self.params_string is not None and (
            not isinstance(self.params_string, str) or not self.params_string.strip()
        ):
            raise LMStudioStageRError("params_string must be non-empty or null")
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int):
            raise LMStudioStageRError("size_bytes must be an integer")
        if self.size_bytes <= 0:
            raise LMStudioStageRError("size_bytes must be positive")
        if isinstance(self.context_length, bool) or not isinstance(
            self.context_length, int
        ):
            raise LMStudioStageRError("context_length must be an integer")
        if self.context_length <= 0:
            raise LMStudioStageRError("context_length must be positive")
        if self.flash_attention is not None and not isinstance(
            self.flash_attention, bool
        ):
            raise LMStudioStageRError("flash_attention must be bool or null")
        if self.offload_kv_cache_to_gpu is not None and not isinstance(
            self.offload_kv_cache_to_gpu, bool
        ):
            raise LMStudioStageRError(
                "offload_kv_cache_to_gpu must be bool or null"
            )
        if self.reasoning_default is not None and (
            not isinstance(self.reasoning_default, str)
            or not self.reasoning_default.strip()
        ):
            raise LMStudioStageRError("reasoning_default must be non-empty or null")
        if tuple(sorted(self.reasoning_allowed_options)) != self.reasoning_allowed_options:
            raise LMStudioStageRError("reasoning_allowed_options must be sorted")
        if len(set(self.reasoning_allowed_options)) != len(
            self.reasoning_allowed_options
        ):
            raise LMStudioStageRError(
                "reasoning_allowed_options must not contain duplicates"
            )

    @property
    def reasoning_condition(self) -> str:
        if self.reasoning_default is None:
            return "omitted_default_unknown"
        return f"omitted_default_{self.reasoning_default}"

    @property
    def observed_identity(self) -> str:
        payload = json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return "lmstudio-observed:sha256:" + hashlib.sha256(payload).hexdigest()

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "request_model": self.request_model,
            "loaded_instance_id": self.loaded_instance_id,
            "display_name": self.display_name,
            "params_string": self.params_string,
            "quantization": self.quantization,
            "size_bytes": self.size_bytes,
            "context_length": self.context_length,
            "flash_attention": self.flash_attention,
            "offload_kv_cache_to_gpu": self.offload_kv_cache_to_gpu,
            "reasoning": {
                "default": self.reasoning_default,
                "allowed_options": list(self.reasoning_allowed_options),
                "wire_control": "omitted",
            },
        }


def observe_compatible_lm_studio_model(
    *,
    models_response: Mapping[str, object],
    request_model: str,
    loaded_instance_id: str | None = None,
) -> ObservedLMStudioModel:
    models = models_response.get("models")
    if not isinstance(models, list):
        raise LMStudioStageRError("LM Studio models response must contain models array")
    matches = [
        item
        for item in models
        if isinstance(item, Mapping) and item.get("key") == request_model
    ]
    if len(matches) != 1:
        raise LMStudioStageRError(
            "LM Studio request model must resolve to exactly one model card"
        )
    model = matches[0]
    if model.get("type") != "llm":
        raise LMStudioStageRError("selected LM Studio model must be an LLM")

    display_name = _string(model.get("display_name") or request_model, "display_name")
    params_string = model.get("params_string")
    if params_string is not None:
        params_string = _string(params_string, "params_string")
    _require_gemma_4_12b(
        request_model=request_model,
        display_name=display_name,
        params_string=params_string,
    )

    quantization = _mapping(model.get("quantization"), "quantization")
    quantization_name = _string(quantization.get("name"), "quantization.name")
    if not quantization_name.casefold().startswith("q4"):
        raise LMStudioStageRError(
            "selected LM Studio model must use Q4-class quantization"
        )
    size_bytes = _integer(model.get("size_bytes"), "size_bytes")

    loaded = model.get("loaded_instances")
    if not isinstance(loaded, list) or not loaded:
        raise LMStudioStageRError("selected LM Studio model is not loaded")
    candidates = [item for item in loaded if isinstance(item, Mapping)]
    if loaded_instance_id is not None:
        candidates = [item for item in candidates if item.get("id") == loaded_instance_id]
    if len(candidates) != 1:
        raise LMStudioStageRError(
            "selected LM Studio request routing is ambiguous; specify one loaded instance"
        )
    instance = candidates[0]
    instance_id = _string(instance.get("id"), "loaded instance id")
    config = _mapping(instance.get("config"), "loaded instance config")
    context_length = _integer(config.get("context_length"), "context_length")

    capabilities = model.get("capabilities")
    reasoning_default: str | None = None
    reasoning_allowed: tuple[str, ...] = ()
    if isinstance(capabilities, Mapping):
        reasoning = capabilities.get("reasoning")
        if isinstance(reasoning, Mapping):
            allowed = reasoning.get("allowed_options")
            default = reasoning.get("default")
            if isinstance(allowed, list) and all(
                isinstance(item, str) and item.strip() for item in allowed
            ):
                reasoning_allowed = tuple(sorted(allowed))
            if isinstance(default, str) and default.strip():
                reasoning_default = default

    return ObservedLMStudioModel(
        request_model=request_model,
        loaded_instance_id=instance_id,
        display_name=display_name,
        params_string=params_string,
        quantization=quantization_name,
        size_bytes=size_bytes,
        context_length=context_length,
        flash_attention=_optional_bool(config.get("flash_attention"), "flash_attention"),
        offload_kv_cache_to_gpu=_optional_bool(
            config.get("offload_kv_cache_to_gpu"),
            "offload_kv_cache_to_gpu",
        ),
        reasoning_default=reasoning_default,
        reasoning_allowed_options=reasoning_allowed,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the provider-neutral current Stage R semantic fixture against an "
            "observed compatible LM Studio Gemma-4 12B Q4 condition."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--provider-base-url", required=True)
    parser.add_argument("--request-model", required=True)
    parser.add_argument("--loaded-instance-id")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--provider-api-key-env")
    parser.add_argument("--replicate-id", default="0")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    repo_root = Path(args.repo_root).resolve()
    provider_base_url = _require_openai_api_base(args.provider_base_url)
    artifact_root = Path(args.artifact_root).resolve()
    workspace_root = Path(args.workspace_root).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)
    workspace_root.mkdir(parents=True, exist_ok=True)

    authority = load_stage_r_semantic_authority(
        repo_root / CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH
    )
    scenario_set = load_current_stage_r_scenario_set(
        repo_root=repo_root,
        authority=authority,
    )
    models_response = _fetch_models(
        provider_base_url=provider_base_url,
        api_key_env=args.provider_api_key_env,
    )
    observed = observe_compatible_lm_studio_model(
        models_response=models_response,
        request_model=args.request_model,
        loaded_instance_id=args.loaded_instance_id,
    )
    _write_json_create_once(
        artifact_root / "lm-studio-model-observation.json",
        observed.to_mapping(),
    )

    result = asyncio.run(
        _run_stage_r(
            repo_root=repo_root,
            provider_base_url=provider_base_url,
            request_model=args.request_model,
            workspace_root=workspace_root,
            artifact_root=artifact_root,
            replicate_id=args.replicate_id,
            api_key_env=args.provider_api_key_env,
            authority=authority,
            scenario_set=scenario_set,
            observed=observed,
        )
    )
    _write_json_create_once(
        artifact_root / "stage-r-lm-studio-summary.json",
        result,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


async def _run_stage_r(
    *,
    repo_root: Path,
    provider_base_url: str,
    request_model: str,
    workspace_root: Path,
    artifact_root: Path,
    replicate_id: str,
    api_key_env: str | None,
    authority: StageRSemanticAuthority,
    scenario_set: Any,
    observed: ObservedLMStudioModel,
) -> dict[str, object]:
    api_key = os.environ.get(api_key_env) if api_key_env else None
    decoding = OpenAICompatibleDecodingConfig(
        temperature=authority.temperature,
        top_p=authority.top_p,
        seed=authority.seed,
    )
    provider = OpenAICompatibleTwoPassProvider(
        base_url=provider_base_url,
        model=request_model,
        api_key=api_key,
        decoding_config=decoding,
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset({"temperature", "top_p"})
        ),
    )
    identity = describe_openai_compatible_provider(provider)
    fixture_root = repo_root / CANONICAL_FIXTURE_PATH
    pass_requests = authority.pass_requests(reasoning_mode=None)
    manifest = ActualModelRunManifest(
        relaylm_commit=_git_head(repo_root),
        character_fixture_id=scenario_set.character_fixture_id,
        character_fixture_revision=character_fixture_revision(fixture_root),
        provider_identity=(
            "lm_studio_observed:"
            f"{request_model}:{observed.loaded_instance_id}:"
            f"{observed.reasoning_condition}"
        ),
        adapter_identity=identity.adapter_identity,
        model_artifact=observed.observed_identity,
        tokenizer_identity="lmstudio-observed:tokenizer-unreported",
        effective_context_window=observed.context_length,
        decoding_configuration=tuple(
            sorted(identity.effective_decoding_configuration.items())
        ),
        structured_output_schema_version="relaylm-cognitive-output-v1",
        scenario_set_version=scenario_set.scenario_set_version,
        condition_id="stage-r-lm-studio-observed-v1",
        continuity_runtime=authority.continuity_runtime,
        execution_path=authority.execution_path,
        seed=authority.seed,
        provider_capabilities=identity.provider_capabilities,
        replicate_id=replicate_id,
        cognition_execution=authority.cognition_execution,
        cognition_pass_requests=pass_requests,
    )

    executions: list[dict[str, object]] = []
    try:
        for scenario_id in authority.scenario_ids:
            result = await run_actual_model_scenario_definition(
                scenario_set=scenario_set,
                scenario_id=scenario_id,
                fixture_root=fixture_root,
                workspace_root=workspace_root / scenario_id,
                provider=provider,
                manifest=manifest,
            )
            execution_path = write_actual_model_execution_result(
                result=result,
                artifact_root=artifact_root,
            )
            verdict = evaluate_actual_model_deterministic_boundary(result=result)
            boundary_path = write_actual_model_deterministic_boundary_verdict(
                verdict=verdict,
                artifact_root=artifact_root,
            )
            executions.append(
                {
                    "scenario_id": scenario_id,
                    "execution_id": result.execution_id,
                    "run_id": result.run_id,
                    "execution_artifact": str(execution_path),
                    "boundary_verdict": verdict.outcome,
                    "boundary_artifact": str(boundary_path),
                }
            )
    finally:
        await provider.aclose()

    return {
        "format_version": OBSERVED_LM_STUDIO_STAGE_R_FORMAT_VERSION,
        "semantic_authority_id": authority.authority_id,
        "scenario_set_revision": authority.scenario_set_revision,
        "model": observed.to_mapping(),
        "model_observed_identity": observed.observed_identity,
        "reasoning_preference": authority.reasoning_preference,
        "reasoning_realization": observed.reasoning_condition,
        "reasoning_wire_control": "omitted",
        "executions": executions,
    }


def _fetch_models(
    *,
    provider_base_url: str,
    api_key_env: str | None,
) -> Mapping[str, object]:
    parsed = urlsplit(provider_base_url)
    origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    request = urllib.request.Request(
        origin + "/api/v1/models",
        headers={"Accept": "application/json"},
    )
    if api_key_env:
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise LMStudioStageRError(
                f"provider API key environment variable is empty: {api_key_env}"
            )
        request.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(request, timeout=15.0) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, urllib.error.URLError) as exc:
        raise LMStudioStageRError(
            f"cannot fetch LM Studio model inventory: {exc}"
        ) from exc
    if not isinstance(raw, Mapping):
        raise LMStudioStageRError("LM Studio model inventory must be a JSON object")
    return raw


def _require_openai_api_base(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise LMStudioStageRError(
            "LM Studio provider base URL must be a non-empty HTTP(S) URL ending in /v1"
        )
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LMStudioStageRError(
            "LM Studio provider base URL must be an HTTP(S) URL ending in /v1"
        )
    if parsed.query or parsed.fragment or parsed.path.rstrip("/") != "/v1":
        raise LMStudioStageRError(
            "LM Studio provider base URL must use the OpenAI API base path /v1"
        )
    return base_url.rstrip("/")


def _require_gemma_4_12b(
    *, request_model: str, display_name: str, params_string: str | None
) -> None:
    names = " ".join((request_model, display_name)).casefold().replace("_", "-")
    if "gemma-4" not in names and "gemma 4" not in names:
        raise LMStudioStageRError("selected LM Studio model must be Gemma-4")
    size_identity = (params_string or names).casefold().replace(" ", "")
    if "12b" not in size_identity:
        raise LMStudioStageRError("selected LM Studio model must be the 12B class")


def _git_head(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    head = completed.stdout.strip()
    if completed.returncode != 0 or len(head) != 40:
        raise LMStudioStageRError("cannot determine exact RelayLM checkout HEAD")
    return head


def _write_json_create_once(path: Path, value: object) -> None:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
    ) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != payload:
            raise LMStudioStageRError(
                f"artifact already exists with different content: {path}"
            )


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise LMStudioStageRError(f"{label} must be an object")
    return value


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LMStudioStageRError(f"{label} must be a non-empty string")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LMStudioStageRError(f"{label} must be an integer")
    if value <= 0:
        raise LMStudioStageRError(f"{label} must be positive")
    return value


def _optional_bool(value: object, label: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise LMStudioStageRError(f"{label} must be bool or null")
    return value


if __name__ == "__main__":
    raise SystemExit(main())

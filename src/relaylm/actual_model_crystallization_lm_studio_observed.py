from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

from relaylm.actual_model_artifacts import (
    character_fixture_revision,
    prepare_character_fixture_workspace,
)
from relaylm.actual_model_crystallization import (
    ActualModelCrystallizationCase,
    ActualModelCrystallizationManifest,
    ActualModelCrystallizationReasoningIdentity,
    run_actual_model_crystallization,
    write_actual_model_crystallization_evidence,
)
from relaylm.actual_model_stage_r_lm_studio import (
    ObservedLMStudioModel,
    observe_compatible_lm_studio_model,
)
from relaylm.providers.lm_studio_reasoning import (
    LMStudioReasoningCapabilityAttestation,
    LMStudioReasoningCapabilityError,
    attest_lm_studio_reasoning_capabilities,
)
from relaylm.providers.openai_compatible_crystallization import OpenAICompatibleCrystallizer
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.providers.openai_compatible_reasoning import OpenAICompatibleReasoningRequest


OBSERVED_CRYSTALLIZATION_FORMAT_VERSION = 1
FIXTURE_ID = "actual-model-crystallization-quality-v1"
FIXTURE_PATH = Path("evaluation/actual_model/characters/crystallization-quality-v1")
FIXTURE_REVISION_PATH = Path(
    "evaluation/actual_model/characters/crystallization-quality-v1.revision.txt"
)
CASE_ID = "crystallization-consolidation-quality-v1"
CASE_VERSION = "1"
MAX_EVENTS = 7
CONDITION_ID = "crystallization-lm-studio-observed-v1"
ADAPTER_IDENTITY = "relaylm.providers.OpenAICompatibleCrystallizer:v2"
STRUCTURED_OUTPUT_SCHEMA_VERSION = "relaylm_crystallization_output:v2"
EVALUATION_CONTRACT_VERSION = "actual-model-crystallization-v2"


class ObservedLMStudioCrystallizationError(ValueError):
    """Observed LM Studio condition cannot run canonical crystallization truthfully."""


def observed_reasoning_identity(
    observed: ObservedLMStudioModel,
    capability: LMStudioReasoningCapabilityAttestation,
) -> ActualModelCrystallizationReasoningIdentity:
    """Represent the explicit request-time OFF condition used by this path."""

    if capability.request_model != observed.request_model:
        raise ObservedLMStudioCrystallizationError(
            "reasoning capability request model does not match observed model"
        )
    if capability.loaded_instance_id != observed.loaded_instance_id:
        raise ObservedLMStudioCrystallizationError(
            "reasoning capability loaded instance does not match observed model"
        )
    if "off" not in capability.allowed_options:
        raise ObservedLMStudioCrystallizationError(
            "canonical crystallization requires explicit LM Studio reasoning option off"
        )
    live_default = capability.default or "unknown"
    return ActualModelCrystallizationReasoningIdentity(
        required_setting="off",
        effective_setting="off",
        allowed_options=capability.allowed_options,
        live_default=live_default,
        control_source="lmstudio_chat_completions_reasoning_effort",
        control_mode="explicit_request",
    )


def build_observed_manifest(
    *,
    relaylm_commit: str,
    fixture_revision: str,
    observed: ObservedLMStudioModel,
    reasoning_capability: LMStudioReasoningCapabilityAttestation,
    replicate_id: str,
) -> ActualModelCrystallizationManifest:
    decoding = OpenAICompatibleDecodingConfig(temperature=0, top_p=1, seed=None)
    return ActualModelCrystallizationManifest(
        relaylm_commit=relaylm_commit,
        character_fixture_id=FIXTURE_ID,
        character_fixture_revision=fixture_revision,
        provider_identity=(
            "lm_studio_observed:"
            f"{observed.request_model}:{observed.loaded_instance_id}:"
            f"{observed.observed_identity}:reasoning_effort=none"
        ),
        adapter_identity=ADAPTER_IDENTITY,
        model_artifact=observed.observed_identity,
        tokenizer_identity="lmstudio-observed:tokenizer-unreported",
        effective_context_window=observed.context_length,
        decoding_configuration=tuple(sorted(decoding.to_mapping().items())),
        reasoning_identity=observed_reasoning_identity(
            observed,
            reasoning_capability,
        ),
        structured_output_schema_version=STRUCTURED_OUTPUT_SCHEMA_VERSION,
        evaluation_contract_version=EVALUATION_CONTRACT_VERSION,
        condition_id=CONDITION_ID,
        max_events=MAX_EVENTS,
        seed=None,
        replicate_id=replicate_id,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run canonical off-turn crystallization against an observed compatible "
            "LM Studio Gemma-4 12B Q4 condition without frozen-artifact proof."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--provider-base-url", required=True)
    parser.add_argument("--request-model", required=True)
    parser.add_argument("--loaded-instance-id")
    parser.add_argument("--expected-model-observed-identity")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--provider-api-key-env")
    parser.add_argument("--replicate-id", default="0")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    repo_root = Path(args.repo_root).resolve()
    relaylm_commit = _verify_clean_repo(repo_root)
    provider_base_url = _require_openai_api_base(args.provider_base_url)
    api_key = _api_key(args.provider_api_key_env)

    fixture_root = (repo_root / FIXTURE_PATH).resolve()
    expected_fixture_revision = _read_expected_fixture_revision(repo_root)
    observed_fixture_revision = character_fixture_revision(fixture_root)
    if observed_fixture_revision != expected_fixture_revision:
        raise ObservedLMStudioCrystallizationError(
            "canonical crystallization fixture revision does not match its repository authority"
        )

    models_response = _fetch_models(
        provider_base_url=provider_base_url,
        api_key=api_key,
    )
    observed = observe_compatible_lm_studio_model(
        models_response=models_response,
        request_model=args.request_model,
        loaded_instance_id=args.loaded_instance_id,
    )
    if (
        args.expected_model_observed_identity is not None
        and observed.observed_identity != args.expected_model_observed_identity
    ):
        raise ObservedLMStudioCrystallizationError(
            "live LM Studio model identity changed from the expected Phase A observation"
        )
    try:
        reasoning_capability = attest_lm_studio_reasoning_capabilities(
            models_response=models_response,
            request_model=observed.request_model,
            loaded_instance_id=observed.loaded_instance_id,
        )
    except LMStudioReasoningCapabilityError as exc:
        raise ObservedLMStudioCrystallizationError(
            f"cannot attest LM Studio reasoning capability: {exc}"
        ) from exc
    if "off" not in reasoning_capability.allowed_options:
        raise ObservedLMStudioCrystallizationError(
            "canonical crystallization requires explicit LM Studio reasoning option off"
        )

    artifact_root = Path(args.artifact_root).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)
    _write_json_create_once(
        artifact_root / "lm-studio-crystallization-model-observation.json",
        {
            "format_version": OBSERVED_CRYSTALLIZATION_FORMAT_VERSION,
            "observed_identity": observed.observed_identity,
            "model": observed.to_mapping(),
            "reasoning_capability": reasoning_capability.to_mapping(),
        },
    )

    result = asyncio.run(
        _execute(
            repo_root=repo_root,
            provider_base_url=provider_base_url,
            api_key=api_key,
            workspace_root=Path(args.workspace_root).resolve(),
            artifact_root=artifact_root,
            relaylm_commit=relaylm_commit,
            fixture_revision=observed_fixture_revision,
            observed=observed,
            reasoning_capability=reasoning_capability,
            replicate_id=args.replicate_id,
        )
    )
    _write_json_create_once(
        artifact_root / "crystallization-lm-studio-observed-summary.json",
        result,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


async def _execute(
    *,
    repo_root: Path,
    provider_base_url: str,
    api_key: str | None,
    workspace_root: Path,
    artifact_root: Path,
    relaylm_commit: str,
    fixture_revision: str,
    observed: ObservedLMStudioModel,
    reasoning_capability: LMStudioReasoningCapabilityAttestation,
    replicate_id: str,
) -> dict[str, object]:
    manifest = build_observed_manifest(
        relaylm_commit=relaylm_commit,
        fixture_revision=fixture_revision,
        observed=observed,
        reasoning_capability=reasoning_capability,
        replicate_id=replicate_id,
    )
    case = ActualModelCrystallizationCase(case_id=CASE_ID, version=CASE_VERSION)
    decoding = OpenAICompatibleDecodingConfig(temperature=0, top_p=1, seed=None)
    crystallizer = OpenAICompatibleCrystallizer(
        base_url=provider_base_url,
        model=observed.request_model,
        api_key=api_key,
        decoding_config=decoding,
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset({"temperature", "top_p"})
        ),
        reasoning_request=OpenAICompatibleReasoningRequest(mode="off"),
        lm_studio_reasoning_capability=reasoning_capability,
    )
    workspace = workspace_root / CONDITION_ID / replicate_id / CASE_ID
    try:
        character = prepare_character_fixture_workspace(
            fixture_root=repo_root / FIXTURE_PATH,
            workspace_root=workspace,
            manifest=manifest,  # type: ignore[arg-type]
        )
        evidence = await run_actual_model_crystallization(
            character=character,
            crystallizer=crystallizer,
            manifest=manifest,
            case=case,
        )
        evidence_path = write_actual_model_crystallization_evidence(
            evidence=evidence,
            artifact_root=artifact_root,
        )
    finally:
        await crystallizer.aclose()

    return {
        "format_version": OBSERVED_CRYSTALLIZATION_FORMAT_VERSION,
        "suite": "actual-model-crystallization-lm-studio-observed-v1",
        "relaylm_commit": relaylm_commit,
        "condition_id": CONDITION_ID,
        "replicate_id": replicate_id,
        "model_observed_identity": observed.observed_identity,
        "model": observed.to_mapping(),
        "reasoning_realization": "explicit_off",
        "reasoning_wire_control": "reasoning_effort=none",
        "reasoning_capability": reasoning_capability.to_mapping(),
        "result": {
            "case_id": CASE_ID,
            "run_id": evidence.run_id,
            "artifact_path": str(evidence_path),
        },
        "score": None,
    }


def _verify_clean_repo(repo_root: Path) -> str:
    head = _git(repo_root, "rev-parse", "HEAD")
    if len(head) != 40:
        raise ObservedLMStudioCrystallizationError("cannot determine exact repository HEAD")
    status = _git(repo_root, "status", "--porcelain")
    if status:
        raise ObservedLMStudioCrystallizationError(
            "observed-condition crystallization requires a clean repository checkout"
        )
    return head


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise ObservedLMStudioCrystallizationError(
            "cannot inspect repository identity: " + completed.stderr.strip()
        )
    return completed.stdout.strip()


def _read_expected_fixture_revision(repo_root: Path) -> str:
    try:
        value = (repo_root / FIXTURE_REVISION_PATH).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise ObservedLMStudioCrystallizationError(
            f"cannot read canonical crystallization fixture revision: {exc}"
        ) from exc
    if not value.startswith("sha256:") or len(value) != 71:
        raise ObservedLMStudioCrystallizationError(
            "canonical crystallization fixture revision is malformed"
        )
    return value


def _fetch_models(
    *,
    provider_base_url: str,
    api_key: str | None,
) -> Mapping[str, object]:
    parsed = urlsplit(provider_base_url)
    origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    headers = {"Accept": "application/json"}
    if api_key is not None:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(origin + "/api/v1/models", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15.0) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, urllib.error.URLError) as exc:
        raise ObservedLMStudioCrystallizationError(
            f"cannot fetch LM Studio model inventory: {exc}"
        ) from exc
    if not isinstance(raw, Mapping):
        raise ObservedLMStudioCrystallizationError(
            "LM Studio model inventory must be a JSON object"
        )
    return raw


def _require_openai_api_base(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise ObservedLMStudioCrystallizationError(
            "LM Studio provider base URL must be non-empty"
        )
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ObservedLMStudioCrystallizationError(
            "LM Studio provider base URL must be HTTP(S)"
        )
    if parsed.query or parsed.fragment or parsed.path.rstrip("/") != "/v1":
        raise ObservedLMStudioCrystallizationError(
            "LM Studio provider base URL must use the OpenAI API base path /v1"
        )
    return base_url.rstrip("/")


def _api_key(api_key_env: str | None) -> str | None:
    if api_key_env is None:
        return None
    value = os.environ.get(api_key_env)
    if not value:
        raise ObservedLMStudioCrystallizationError(
            f"provider API key environment variable is empty: {api_key_env}"
        )
    return value


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
            raise ObservedLMStudioCrystallizationError(
                f"artifact already exists with different content: {path}"
            )


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import shlex
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx

from relaylm.actual_model_artifacts import (
    ActualModelArtifactError,
    character_fixture_revision,
    prepare_character_fixture_workspace,
)
from relaylm.actual_model_crystallization import (
    ActualModelCrystallizationCase,
    ActualModelCrystallizationEvidence,
    ActualModelCrystallizationManifest,
    ActualModelCrystallizationReasoningIdentity,
    run_actual_model_crystallization,
    write_actual_model_crystallization_evidence,
)
from relaylm.actual_model_llama_cpp import attest_llama_cpp_runtime
from relaylm.actual_model_llama_cpp_thinking import (
    LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS,
    LlamaCppThinkingChatInputCounter,
)
from relaylm.actual_model_targets import (
    ActualModelArtifactTarget,
    ActualModelArtifactVerification,
    load_actual_model_target,
    verify_actual_model_artifact,
)
from relaylm.providers.llama_cpp_crystallization import (
    LLAMA_CPP_CRYSTALLIZATION_ADAPTER_IDENTITY,
    LlamaCppOpenAICompatibleCrystallizer,
)
from relaylm.providers.llama_cpp_reasoning import (
    LlamaCppReasoningCapabilityAttestation,
)
from relaylm.providers.openai_compatible_crystallization import WIRE_SCHEMA
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from tools.repository_authority import load_declarations, qualification_fingerprint


HOST_FORMAT_VERSION = 1
FIXTURE_ID = "actual-model-crystallization-quality-v1"
FIXTURE_PATH = Path("evaluation/actual_model/characters/crystallization-quality-v1")
FIXTURE_REVISION_PATH = Path(
    "evaluation/actual_model/characters/crystallization-quality-v1.revision.txt"
)
CASE_ID = "crystallization-consolidation-quality-v1"
CASE_VERSION = "1"
MAX_EVENTS = 7
CONDITION_ID = "crystallization-llama-cpp-reference-v1"
TARGET_ID = "gemma-4-12b-it-q4-k-m-lmstudio-community-v1"
TARGET_PATH = Path(
    "evaluation/actual_model/targets/"
    "gemma-4-12b-it-q4-k-m-lmstudio-community-v1.json"
)
EXPECTED_ORIGIN = "http://127.0.0.1:1234"
EXPECTED_API_BASE = f"{EXPECTED_ORIGIN}/v1"
EXPECTED_CONTEXT_WINDOW = 8192
EXPECTED_SLOTS = 1
GPU_OFFLOAD_ARGS = "-ngl 999"
STRUCTURED_OUTPUT_SCHEMA_VERSION = "relaylm_crystallization_output:v2"
EVALUATION_CONTRACT_VERSION = "actual-model-crystallization-v2"
_DECODING_CONFIG = OpenAICompatibleDecodingConfig(temperature=0, top_p=1, seed=None)
_DECODING_CAPABILITIES = OpenAICompatibleDecodingCapabilities(
    supported_controls=frozenset({"temperature", "top_p"})
)
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class LlamaCppCrystallizationHostError(ValueError):
    """The current llama.cpp off-turn crystallization condition is invalid."""


@dataclass(frozen=True, slots=True)
class LlamaCppCrystallizationArtifact:
    case_id: str
    run_id: str
    artifact_path: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "run_id": self.run_id,
            "artifact_path": self.artifact_path,
        }


@dataclass(frozen=True, slots=True)
class PreparedLlamaCppCrystallizationHostRun:
    relaylm_commit: str
    relaylm_tree: str
    core_fingerprint: str
    target: ActualModelArtifactTarget
    artifact_verification: ActualModelArtifactVerification
    fixture_root: Path
    fixture_revision: str
    runtime: object
    runtime_identity: str
    counter: LlamaCppThinkingChatInputCounter
    reasoning_capability: LlamaCppReasoningCapabilityAttestation
    crystallizer: LlamaCppOpenAICompatibleCrystallizer
    http_client: httpx.AsyncClient
    manifest: ActualModelCrystallizationManifest
    case: ActualModelCrystallizationCase
    workspace_root: Path
    artifact_root: Path
    launch_evidence: dict[str, object]


def prepare_llama_cpp_crystallization_host_run(
    *,
    repo_root: str | Path,
    provider_base_url: str,
    request_model: str,
    artifact_path: str | Path,
    target_path: str | Path = TARGET_PATH,
    llama_upstream_revision: str,
    llama_version: str,
    expected_build_number: int,
    expected_context_window: int,
    expected_slots: int,
    context_shift_disabled: bool,
    gpu_identity: str,
    gpu_offload_args: str,
    launch_args: str,
    server_log_path: str | Path,
    workspace_root: str | Path,
    artifact_root: str | Path,
    replicate_id: str = "0",
) -> PreparedLlamaCppCrystallizationHostRun:
    root = Path(repo_root).resolve()
    relaylm_commit, relaylm_tree = _verify_clean_exact_repo(root)
    core_fingerprint = _frozen_core_fingerprint(root)
    base_url = _require_local_llama_api_base(provider_base_url)
    _require_positive(expected_build_number, "expected_build_number")
    if expected_context_window != EXPECTED_CONTEXT_WINDOW:
        raise LlamaCppCrystallizationHostError(
            "current llama.cpp crystallization requires context window 8192"
        )
    if expected_slots != EXPECTED_SLOTS:
        raise LlamaCppCrystallizationHostError(
            "current llama.cpp crystallization requires exactly one slot"
        )
    if not context_shift_disabled:
        raise LlamaCppCrystallizationHostError(
            "current llama.cpp crystallization requires context shift disabled"
        )
    if not isinstance(llama_version, str) or not llama_version.strip():
        raise LlamaCppCrystallizationHostError("llama_version must be non-empty")
    if not re.search(rf"\bbuild\s+{expected_build_number}\b", llama_version, re.I):
        raise LlamaCppCrystallizationHostError(
            "llama_version does not carry the expected llama-server build number"
        )
    _require_non_empty(gpu_identity, "gpu_identity")
    if gpu_offload_args != GPU_OFFLOAD_ARGS:
        raise LlamaCppCrystallizationHostError(
            "llama.cpp crystallization requires the attested -ngl 999 offload control"
        )
    launch_evidence = _attest_launch(
        launch_args=launch_args,
        artifact_path=Path(artifact_path).resolve(),
        server_log_path=Path(server_log_path).resolve(),
        artifact_root=Path(artifact_root).resolve(),
    )

    canonical_target_path = (root / TARGET_PATH).resolve()
    selected_target_path = Path(target_path)
    if not selected_target_path.is_absolute():
        selected_target_path = root / selected_target_path
    if selected_target_path.resolve() != canonical_target_path:
        raise LlamaCppCrystallizationHostError(
            "llama.cpp crystallization must use the canonical current GGUF target"
        )
    try:
        target = load_actual_model_target(canonical_target_path)
        artifact_verification = verify_actual_model_artifact(
            target=target,
            artifact_path=artifact_path,
        )
    except (OSError, ValueError) as exc:
        raise LlamaCppCrystallizationHostError(
            f"cannot verify current llama.cpp crystallization target: {exc}"
        ) from exc
    if target.target_id != TARGET_ID:
        raise LlamaCppCrystallizationHostError(
            "current llama.cpp crystallization target ID changed unexpectedly"
        )
    if (
        artifact_verification.target_id != target.target_id
        or artifact_verification.target_revision != target.revision
        or artifact_verification.artifact_size_bytes != target.artifact_size_bytes
        or artifact_verification.artifact_sha256 != target.artifact_sha256
    ):
        raise LlamaCppCrystallizationHostError(
            "artifact verification does not match the canonical current target"
        )
    if request_model.strip() == "":
        raise LlamaCppCrystallizationHostError("request_model must be non-empty")

    fixture_root = (root / FIXTURE_PATH).resolve()
    fixture_revision = _read_fixture_revision(root)
    try:
        observed_fixture_revision = character_fixture_revision(fixture_root)
    except (OSError, ActualModelArtifactError) as exc:
        raise LlamaCppCrystallizationHostError(
            f"cannot verify current crystallization fixture: {exc}"
        ) from exc
    if observed_fixture_revision != fixture_revision:
        raise LlamaCppCrystallizationHostError(
            "canonical crystallization fixture revision does not match repository authority"
        )
    _require_path_component(replicate_id, "replicate_id")

    origin = _origin_from_api_base(base_url)
    try:
        with httpx.Client(
            timeout=20.0,
            trust_env=False,
            headers={"Accept": "application/json"},
        ) as client:
            health = _get_json(client, f"{origin}/health", "health")
            models = _get_json(client, f"{base_url}/models", "models")
            props = _get_json(client, f"{origin}/props", "props")
            slots = _get_json(client, f"{origin}/slots", "slots")
    except LlamaCppCrystallizationHostError:
        raise

    if not isinstance(health, dict) or health.get("status") != "ok":
        raise LlamaCppCrystallizationHostError("llama-server /health is not ok")
    model_ids = _model_ids(models)
    if model_ids != (request_model,):
        raise LlamaCppCrystallizationHostError(
            "llama-server must expose exactly the requested single model alias"
        )
    if not isinstance(props, dict):
        raise LlamaCppCrystallizationHostError("llama-server /props must be an object")
    if not isinstance(slots, list):
        raise LlamaCppCrystallizationHostError("llama-server /slots must be an array")
    build_info = props.get("build_info")
    if not isinstance(build_info, str) or str(expected_build_number) not in build_info:
        raise LlamaCppCrystallizationHostError(
            "llama-server build_info does not contain the expected build number"
        )
    try:
        runtime = attest_llama_cpp_runtime(
            props=props,
            slots=slots,
            upstream_revision=llama_upstream_revision,
            expected_build_info=build_info,
            expected_model_alias=request_model,
            expected_model_path=str(Path(artifact_path).resolve()),
            artifact_sha256=artifact_verification.artifact_sha256,
            context_shift_enabled=False,
        )
    except (TypeError, ValueError) as exc:
        raise LlamaCppCrystallizationHostError(
            f"llama.cpp runtime attestation failed: {exc}"
        ) from exc
    if runtime.context_limit != expected_context_window:
        raise LlamaCppCrystallizationHostError(
            "attested llama.cpp context does not match expected context"
        )
    if runtime.total_slots != expected_slots:
        raise LlamaCppCrystallizationHostError(
            "attested llama.cpp slots do not match expected slots"
        )
    runtime_identity = _runtime_identity_digest(
        runtime=runtime,
        llama_version=llama_version,
        expected_build_number=expected_build_number,
        gpu_identity=gpu_identity,
    )

    counter = LlamaCppThinkingChatInputCounter(
        base_url=base_url,
        runtime_identity=runtime,
    )
    reasoning_capability = LlamaCppReasoningCapabilityAttestation(
        request_model=request_model,
        enable_thinking_supported=True,
    )
    reasoning_identity = ActualModelCrystallizationReasoningIdentity(
        required_setting="off",
        effective_setting="off",
        allowed_options=("off",),
        live_default="off",
        control_source="llama_cpp_reasoning_effort",
        control_mode="explicit_request",
    )
    decoding = _DECODING_CONFIG
    manifest = ActualModelCrystallizationManifest(
        relaylm_commit=relaylm_commit,
        character_fixture_id=FIXTURE_ID,
        character_fixture_revision=fixture_revision,
        provider_identity=(
            "llama_cpp:"
            f"{runtime.upstream_revision}:{request_model}:"
            f"build={expected_build_number}:runtime={runtime_identity}:"
            "reasoning_effort=none"
        ),
        adapter_identity=LLAMA_CPP_CRYSTALLIZATION_ADAPTER_IDENTITY,
        model_artifact=target.model_artifact_identity,
        tokenizer_identity=target.tokenizer_identity,
        effective_context_window=runtime.context_limit,
        decoding_configuration=tuple(sorted(decoding.to_mapping().items())),
        reasoning_identity=reasoning_identity,
        structured_output_schema_version=STRUCTURED_OUTPUT_SCHEMA_VERSION,
        evaluation_contract_version=EVALUATION_CONTRACT_VERSION,
        condition_id=CONDITION_ID,
        max_events=MAX_EVENTS,
        seed=None,
        replicate_id=replicate_id,
    )
    http_client = httpx.AsyncClient(
        timeout=LLAMA_CPP_QUALIFICATION_REQUEST_TIMEOUT_SECONDS,
        trust_env=False,
    )
    crystallizer = LlamaCppOpenAICompatibleCrystallizer(
        base_url=base_url,
        model=request_model,
        decoding_config=decoding,
        decoding_capabilities=_DECODING_CAPABILITIES,
        input_counter=counter,
        llama_cpp_reasoning_capability=reasoning_capability,
        http_client=http_client,
        observation_root=Path(artifact_root)
        / "llama-cpp-crystallization-request-observations",
    )
    case = ActualModelCrystallizationCase(case_id=CASE_ID, version=CASE_VERSION)
    artifact_root_path = Path(artifact_root).resolve()
    artifact_root_path.mkdir(parents=True, exist_ok=True)
    _write_json_create_once(
        artifact_root_path / "llama-cpp-crystallization-binding.json",
        {
            "format_version": HOST_FORMAT_VERSION,
            "execution_kind": "off_turn_crystallization",
            "endpoint": base_url,
            "target": target.to_mapping(),
            "artifact": {
                "canonical_local_path": str(Path(artifact_path).resolve()),
                "verification": artifact_verification.to_mapping(),
            },
            "fixture": {
                "id": FIXTURE_ID,
                "path": FIXTURE_PATH.as_posix(),
                "revision": fixture_revision,
            },
            "runtime": _runtime_mapping(runtime),
            "runtime_identity": runtime_identity,
            "runtime_version": llama_version,
            "build_number": expected_build_number,
            "launch": launch_evidence,
            "gpu_identity": gpu_identity,
            "gpu_offload_args": gpu_offload_args,
            "counter_identity": counter.evidence_identity.to_mapping(),
            "reasoning": {
                "capability": reasoning_capability.to_mapping(),
                "requested": "off",
                "wire": {"reasoning_effort": "none"},
            },
            "native_structured_output": {
                "required": True,
                "schema_name": "relaylm_crystallization_output",
                "schema_sha256": _schema_digest(),
                "fallback": "forbidden",
            },
            "non_generative_preflight_request_count": 4,
        },
    )
    return PreparedLlamaCppCrystallizationHostRun(
        relaylm_commit=relaylm_commit,
        relaylm_tree=relaylm_tree,
        core_fingerprint=core_fingerprint,
        target=target,
        artifact_verification=artifact_verification,
        fixture_root=fixture_root,
        fixture_revision=fixture_revision,
        runtime=runtime,
        runtime_identity=runtime_identity,
        counter=counter,
        reasoning_capability=reasoning_capability,
        crystallizer=crystallizer,
        http_client=http_client,
        manifest=manifest,
        case=case,
        workspace_root=Path(workspace_root).resolve(),
        artifact_root=artifact_root_path,
        launch_evidence=launch_evidence,
    )


async def execute_llama_cpp_crystallization_host_run(
    *,
    prepared: PreparedLlamaCppCrystallizationHostRun,
) -> LlamaCppCrystallizationArtifact:
    workspace = (
        prepared.workspace_root
        / CONDITION_ID
        / prepared.manifest.replicate_id
        / CASE_ID
    )
    source_revision = character_fixture_revision(prepared.fixture_root)
    evidence: ActualModelCrystallizationEvidence | None = None
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
        evidence_path = write_actual_model_crystallization_evidence(
            evidence=evidence,
            artifact_root=prepared.artifact_root,
        )
    finally:
        if character_fixture_revision(prepared.fixture_root) != source_revision:
            raise LlamaCppCrystallizationHostError(
                "canonical crystallization fixture source changed during execution"
            )
        await prepared.crystallizer.aclose()
        await prepared.http_client.aclose()
    assert evidence is not None
    return LlamaCppCrystallizationArtifact(
        case_id=prepared.case.case_id,
        run_id=evidence.run_id,
        artifact_path=str(evidence_path),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one off-turn crystallization operation against the current "
            "attested llama.cpp physical reference."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--provider-base-url", required=True)
    parser.add_argument("--request-model", required=True)
    parser.add_argument("--artifact-path", required=True)
    parser.add_argument("--target-path", default=str(TARGET_PATH))
    parser.add_argument("--llama-upstream-revision", required=True)
    parser.add_argument("--llama-version", required=True)
    parser.add_argument("--expected-build-number", required=True, type=int)
    parser.add_argument("--expected-context-window", required=True, type=int)
    parser.add_argument("--expected-slots", required=True, type=int)
    parser.add_argument("--context-shift-disabled", action="store_true")
    parser.add_argument("--gpu-identity", required=True)
    parser.add_argument("--gpu-offload-args", required=True)
    parser.add_argument("--launch-args", required=True)
    parser.add_argument("--server-log-path", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--replicate-id", default="0")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    workspace_root = Path(args.workspace_root).resolve()
    artifact_root = Path(args.artifact_root).resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    artifact_root.mkdir(parents=True, exist_ok=True)
    summary_path = artifact_root / "crystallization-llama-cpp-summary.json"
    head: str | None = None
    tree: str | None = None
    core: str | None = None
    prepared: PreparedLlamaCppCrystallizationHostRun | None = None
    try:
        head, tree = _verify_clean_exact_repo(Path(args.repo_root).resolve())
        core = _frozen_core_fingerprint(Path(args.repo_root).resolve())
        prepared = prepare_llama_cpp_crystallization_host_run(
            repo_root=args.repo_root,
            provider_base_url=args.provider_base_url,
            request_model=args.request_model,
            artifact_path=args.artifact_path,
            target_path=args.target_path,
            llama_upstream_revision=args.llama_upstream_revision,
            llama_version=args.llama_version,
            expected_build_number=args.expected_build_number,
            expected_context_window=args.expected_context_window,
            expected_slots=args.expected_slots,
            context_shift_disabled=args.context_shift_disabled,
            gpu_identity=args.gpu_identity,
            gpu_offload_args=args.gpu_offload_args,
            launch_args=args.launch_args,
            server_log_path=args.server_log_path,
            workspace_root=workspace_root,
            artifact_root=artifact_root,
            replicate_id=args.replicate_id,
        )
    except Exception as exc:
        summary = _summary(
            classification="INFRA_INVALID",
            phase="physical_preflight",
            head=head,
            tree=tree,
            core=core,
            provider_request_count=0,
            input_counter_request_count=0,
            error=exc,
        )
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

    try:
        result = asyncio.run(
            execute_llama_cpp_crystallization_host_run(prepared=prepared)
        )
    except Exception as exc:
        summary = _summary(
            classification="INFRA_INVALID",
            phase="crystallization_transport",
            head=head,
            tree=tree,
            core=core,
            provider_request_count=prepared.crystallizer.generation_request_count,
            input_counter_request_count=prepared.crystallizer.input_counter_request_count,
            error=exc,
        )
        _write_json_create_once(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 2

    summary = _summary(
        classification="EVIDENCE_RECORDED",
        phase="complete",
        head=prepared.relaylm_commit,
        tree=prepared.relaylm_tree,
        core=prepared.core_fingerprint,
        provider_request_count=prepared.crystallizer.generation_request_count,
        input_counter_request_count=prepared.crystallizer.input_counter_request_count,
        error=None,
    )
    summary.update(
        {
            "target_id": prepared.target.target_id,
            "provider_base_url": EXPECTED_API_BASE,
            "target": prepared.target.to_mapping(),
            "artifact_verification": prepared.artifact_verification.to_mapping(),
            "runtime": _runtime_mapping(prepared.runtime),
            "runtime_identity": prepared.runtime_identity,
            "launch": prepared.launch_evidence,
            "counter_identity": prepared.counter.evidence_identity.to_mapping(),
            "reasoning": {
                "requested": "off",
                "wire": {"reasoning_effort": "none"},
                "capability": prepared.reasoning_capability.to_mapping(),
            },
            "result": result.to_mapping(),
            "product_quality_review": "not_run_by_host",
        }
    )
    _write_json_create_once(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def _summary(
    *,
    classification: str,
    phase: str,
    head: str | None,
    tree: str | None,
    core: str | None,
    provider_request_count: int,
    input_counter_request_count: int,
    error: Exception | None,
) -> dict[str, object]:
    summary: dict[str, object] = {
        "format_version": HOST_FORMAT_VERSION,
        "suite": "actual-model-crystallization-llama-cpp-v1",
        "execution_kind": "off_turn_crystallization",
        "classification": classification,
        "phase": phase,
        "relaylm": {
            "head": head,
            "tree": tree,
            "core_semantic_fingerprint": core,
        },
        "target_id": TARGET_ID,
        "server_launch_count": 0,
        "host_invocation_count": 1,
        "provider_request_count": provider_request_count,
        "crystallization_generation_count": provider_request_count,
        "input_counter_request_count": input_counter_request_count,
        "semantic_retry_count": 0,
        "fallback_count": 0,
        "stage_r_generation_count": 0,
        "lm_studio_contact_count": 0,
        "product_quality_review": "not_run_by_host",
    }
    if error is not None:
        summary["error"] = f"{type(error).__name__}: {error}"
    return summary


def _verify_clean_exact_repo(root: Path) -> tuple[str, str]:
    if not (root / ".git").exists():
        raise LlamaCppCrystallizationHostError(f"repo-root is not a git checkout: {root}")
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0 or completed.stdout.strip():
        raise LlamaCppCrystallizationHostError(
            "llama.cpp crystallization requires a clean exact RelayLM checkout"
        )
    values = []
    for revision in ("HEAD", "HEAD^{tree}"):
        identity = subprocess.run(
            ["git", "rev-parse", revision],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        value = identity.stdout.strip()
        if identity.returncode != 0 or len(value) != 40:
            raise LlamaCppCrystallizationHostError(
                f"cannot determine exact RelayLM identity for {revision}"
            )
        values.append(value)
    return values[0], values[1]


def _frozen_core_fingerprint(root: Path) -> str:
    path = root / "evaluation/actual_model/qualifications/core-semantic-v1.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LlamaCppCrystallizationHostError(
            f"cannot read frozen Core semantic identity: {exc}"
        ) from exc
    expected = document.get("expected_fingerprint") if isinstance(document, dict) else None
    roots = document.get("roots") if isinstance(document, dict) else None
    if not isinstance(expected, str) or not _SHA256_RE.fullmatch(expected):
        raise LlamaCppCrystallizationHostError(
            "frozen Core expected fingerprint is malformed"
        )
    if not isinstance(roots, list) or not all(isinstance(item, str) for item in roots):
        raise LlamaCppCrystallizationHostError("frozen Core roots are malformed")
    try:
        derived = qualification_fingerprint(
            root,
            load_declarations(root),
            roots=tuple(roots),
        )
    except (OSError, ValueError) as exc:
        raise LlamaCppCrystallizationHostError(
            f"cannot derive Core semantic fingerprint: {exc}"
        ) from exc
    if derived != expected:
        raise LlamaCppCrystallizationHostError(
            f"Core expected/derived fingerprint mismatch: {expected} != {derived}"
        )
    return derived


def _read_fixture_revision(root: Path) -> str:
    try:
        value = (root / FIXTURE_REVISION_PATH).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise LlamaCppCrystallizationHostError(
            f"cannot read crystallization fixture revision: {exc}"
        ) from exc
    if not _SHA256_RE.fullmatch(value):
        raise LlamaCppCrystallizationHostError(
            "crystallization fixture revision is not a lowercase sha256 digest"
        )
    return value


def _require_local_llama_api_base(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LlamaCppCrystallizationHostError("provider base URL must be non-empty")
    normalized = value.rstrip("/")
    try:
        parsed = urlsplit(normalized)
        valid = (
            parsed.scheme == "http"
            and parsed.hostname == "127.0.0.1"
            and parsed.port == 1234
            and parsed.path == "/v1"
            and not parsed.query
            and not parsed.fragment
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        valid = False
    if not valid:
        raise LlamaCppCrystallizationHostError(
            f"current llama.cpp crystallization endpoint must be {EXPECTED_API_BASE}"
        )
    return normalized


def _origin_from_api_base(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")


def _attest_launch(
    *,
    launch_args: str,
    artifact_path: Path,
    server_log_path: Path,
    artifact_root: Path,
) -> dict[str, object]:
    if not isinstance(launch_args, str) or not launch_args.strip():
        raise LlamaCppCrystallizationHostError("launch_args must be non-empty")
    try:
        tokens = shlex.split(launch_args)
    except ValueError as exc:
        raise LlamaCppCrystallizationHostError(
            f"launch_args are not valid shell words: {exc}"
        ) from exc
    if not tokens:
        raise LlamaCppCrystallizationHostError("launch_args must contain llama-server")
    if Path(tokens[0]).name != "llama-server":
        raise LlamaCppCrystallizationHostError(
            "launch_args must invoke the current llama-server binary"
        )
    expected = {
        "-m": str(artifact_path),
        "--host": "127.0.0.1",
        "--port": "1234",
        "-ngl": "999",
        "-c": str(EXPECTED_CONTEXT_WINDOW),
        "-np": str(EXPECTED_SLOTS),
        "-lv": "4",
        "--log-file": str(server_log_path),
    }
    for option, expected_value in expected.items():
        values = _option_values(tokens, option)
        if values != [expected_value]:
            raise LlamaCppCrystallizationHostError(
                f"launch_args {option} does not match current llama.cpp condition"
            )
    if tokens.count("--no-context-shift") != 1:
        raise LlamaCppCrystallizationHostError(
            "launch_args must carry exactly one --no-context-shift"
        )
    if tokens.count("--log-timestamps") != 1:
        raise LlamaCppCrystallizationHostError(
            "launch_args must carry exactly one --log-timestamps"
        )
    if not server_log_path.is_file():
        raise LlamaCppCrystallizationHostError(
            "transaction-owned llama-server log is missing"
        )
    if not artifact_root.is_dir() or not server_log_path.is_relative_to(artifact_root):
        raise LlamaCppCrystallizationHostError(
            "transaction-owned server log must remain inside artifact root"
        )
    return {
        "launch_args": launch_args,
        "context_window": EXPECTED_CONTEXT_WINDOW,
        "slots": EXPECTED_SLOTS,
        "context_shift_disabled": True,
        "gpu_offload_args": GPU_OFFLOAD_ARGS,
        "server_log_path": str(server_log_path),
    }


def _option_values(tokens: list[str], option: str) -> list[str]:
    values: list[str] = []
    for index, token in enumerate(tokens):
        if token == option:
            if index + 1 >= len(tokens):
                return []
            values.append(tokens[index + 1])
    return values


def _get_json(client: httpx.Client, url: str, label: str) -> object:
    try:
        response = client.get(url)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LlamaCppCrystallizationHostError(
            f"llama-server {label} request failed: {exc}"
        ) from exc


def _model_ids(document: object) -> tuple[str, ...]:
    if not isinstance(document, dict) or not isinstance(document.get("data"), list):
        raise LlamaCppCrystallizationHostError(
            "llama-server /v1/models response is malformed"
        )
    ids = tuple(
        item["id"]
        for item in document["data"]
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item["id"].strip()
    )
    if not ids:
        raise LlamaCppCrystallizationHostError(
            "llama-server /v1/models exposes no model alias"
        )
    return ids


def _runtime_mapping(runtime: object) -> dict[str, object]:
    return {
        "upstream_revision": runtime.upstream_revision,
        "build_info": runtime.build_info,
        "model_alias": runtime.model_alias,
        "model_path": runtime.model_path,
        "model_ftype": runtime.model_ftype,
        "artifact_sha256": runtime.artifact_sha256,
        "chat_template_sha256": runtime.chat_template_sha256,
        "context_limit": runtime.context_limit,
        "total_slots": runtime.total_slots,
        "context_shift_enabled": runtime.context_shift_enabled,
    }


def _runtime_identity_digest(
    *,
    runtime: object,
    llama_version: str,
    expected_build_number: int,
    gpu_identity: str,
) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            {
                "runtime": _runtime_mapping(runtime),
                "llama_version": llama_version,
                "expected_build_number": expected_build_number,
                "gpu_identity": gpu_identity,
            },
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _schema_digest() -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            WIRE_SCHEMA,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _require_non_empty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LlamaCppCrystallizationHostError(f"{label} must be non-empty")
    return value


def _require_positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LlamaCppCrystallizationHostError(f"{label} must be positive")
    return value


def _require_path_component(value: str, label: str) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or Path(value).name != value
        or value in {".", ".."}
    ):
        raise LlamaCppCrystallizationHostError(
            f"{label} must be one safe non-empty path component"
        )


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
            raise LlamaCppCrystallizationHostError(
                f"artifact already exists with different content: {path}"
            )


if __name__ == "__main__":
    raise SystemExit(main())

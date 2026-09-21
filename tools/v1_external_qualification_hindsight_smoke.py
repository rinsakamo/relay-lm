"""Repeatable non-citable smoke for the repaired Hindsight comparator route.

This diagnostic intentionally sits outside the scientific campaign transaction.
It uses repository-owned synthetic text only, never opens a ScientificSpendLedger,
and never writes into a scientific owner's durable roots.  Its purpose is to
exercise the live retain -> consolidation -> recall transport repaired for
#2985 before a one-shot external-qualification campaign consumes benchmark
work.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from tools.v1_external_qualification_llama_cpp_campaign import (
    CampaignCarriageError,
    HindsightDeploymentSession,
    HindsightHealthAttestation,
    HindsightHistorySession,
    HindsightLifecycleSpec,
    HINDSIGHT_CONSOLIDATION_LLM_REASONING_EFFORT,
    HINDSIGHT_FAIL_ON_EXTRACTION_ERRORS,
    HINDSIGHT_LLM_MAX_CONCURRENT,
    HINDSIGHT_LLM_SUPPORTS_STRING_PATTERN,
    HINDSIGHT_RETAIN_LLM_REASONING_EFFORT,
    HINDSIGHT_RETAIN_MAX_COMPLETION_TOKENS,
    LlamaCppLaunchSpec,
    LiveLaunchSession,
    _hindsight_axis_bank_id,
    _hindsight_owner_deployment_id,
    _hindsight_retrieved_memories,
    _write_json_fsync,
    start_llama_cpp_session,
    verify_hindsight_health,
)
from tools.v1_external_qualification_synthetic_capture import (
    SyntheticLlamaCaptureProxy,
)


SMOKE_TARGET = "v1:hindsight-comparator-synthetic-smoke"
SMOKE_FORMAT_VERSION = 1
_STRESS_PROFILES = {"single", "post2986"}

# Persistent qualification material pins.  These are engineering-diagnostic
# inputs, not benchmark authority, and intentionally survive host reboot.
_DIAGNOSTIC_LLAMA_CPP_REVISION = "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"
_DIAGNOSTIC_LLAMA_CPP_BUILD_INFO = "b10874-e2d2c0d6a"
_DIAGNOSTIC_LLAMA_CPP_MODEL_SHA256 = (
    "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
)
_DIAGNOSTIC_LLAMA_CPP_CONTEXT = 8192
_DIAGNOSTIC_LLAMA_CPP_SLOTS = 1
_DIAGNOSTIC_LLAMA_CPP_GPU_LAYERS = 999
_DIAGNOSTIC_GPU_IDENTITY = {
    "name": "NVIDIA GeForce RTX 3060",
    "driver_version": "591.44",
    "memory_total_mib": "12288",
}

_DIAGNOSTIC_HINDSIGHT_VERSION = "v0.10.0"
_DIAGNOSTIC_HINDSIGHT_SOURCE_REVISION = (
    "5d46f9c8c8eb4fb96f549aa63abe1191b82a7840"
)
_DIAGNOSTIC_HINDSIGHT_SOURCE_TREE = (
    "91f1531dfc615dcd940d6b13f139bd0f85335d1f"
)
_DIAGNOSTIC_HINDSIGHT_DEPENDENCY_FINGERPRINT = (
    "sha256:b99ab626d249fe027631db742ebe275469b5a1de4c01b96835bbe0ff1e848846"
)
_DIAGNOSTIC_HINDSIGHT_ONNX_SHA256 = (
    "ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665"
)
_DIAGNOSTIC_HINDSIGHT_TOKENIZER_TREE_SHA256 = (
    "c084a47ff0e32d3c2874b69a72044eea19abded1824d1627da0a8fdd13822d22"
)
_DIAGNOSTIC_HINDSIGHT_WHEEL_SHA256 = {
    "hindsight-all": "adcf529524c22dc13ebe0c788c9dbfcaf3e489c476c958677e50be2cce42a560",
    "hindsight-api-slim": "6f7a11fb43735bcc8164d3bee84622690bfa081ca02aaa88e3b88ef72ef3eca3",
    "hindsight-client": "b16ac3f8b13fc2c35f92ed57129021e53c548a26ee0354015f9ef1394f678e06",
    "hindsight-embed": "2831ce2d1d7c927c55646f748bb0113342fdf5a2bea9dcb15273d29f64326502",
}
_POST2986_WARMUP_EXCHANGES = 40
_POST2986_STRESS_EXCHANGES = 45
_SYNTHETIC_SESSION_ID = "synthetic-session-0001"
_SYNTHETIC_TIMESTAMP = "2025-01-02T00:00:00+00:00"
_SYNTHETIC_QUERY_TIMESTAMP = "2025-01-02T12:00:00+00:00"
_SYNTHETIC_QUESTION = "Where is the copper token stored?"
_SYNTHETIC_ITEMS: tuple[Mapping[str, str | None], ...] = (
    {
        "role": "user",
        "content": "The copper token is stored in drawer seven.",
        "timestamp": _SYNTHETIC_TIMESTAMP,
    },
    {
        "role": "assistant",
        "content": "Understood; the copper token is in drawer seven.",
        "timestamp": _SYNTHETIC_TIMESTAMP,
    },
)


@dataclass(frozen=True, slots=True)
class CurrentHostMaterial:
    llama_cpp_root: Path
    model_path: Path
    onnx_model_path: Path
    onnx_tokenizer_path: Path
    llama_port: int
    hindsight_port: int


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_file_tree(path: Path) -> str:
    if not path.is_dir():
        raise CampaignCarriageError(
            f"diagnostic tokenizer path is not a directory: {path}"
        )
    entries: list[dict[str, str]] = []
    try:
        children = sorted(item for item in path.rglob("*") if item.is_file())
    except OSError as exc:
        raise CampaignCarriageError(
            f"cannot enumerate diagnostic tokenizer path {path}: {exc}"
        ) from exc
    for child in children:
        if child.is_symlink():
            raise CampaignCarriageError(
                f"diagnostic tokenizer path contains a symlink: {child}"
            )
        entries.append(
            {
                "path": child.relative_to(path).as_posix(),
                "sha256": _sha256_file(child),
            }
        )
    if not entries:
        raise CampaignCarriageError(
            f"diagnostic tokenizer path is empty: {path}"
        )
    encoded = json.dumps(
        entries,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _installed_hindsight_wheel_hashes() -> dict[str, str]:
    observed: dict[str, str] = {}
    for name, expected in _DIAGNOSTIC_HINDSIGHT_WHEEL_SHA256.items():
        try:
            distribution = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise CampaignCarriageError(
                f"required Hindsight distribution is absent: {name}"
            ) from exc
        direct_url = distribution.read_text("direct_url.json")
        if direct_url is None:
            raise CampaignCarriageError(
                f"Hindsight distribution has no exact direct_url.json: {name}"
            )
        try:
            direct = json.loads(direct_url)
        except json.JSONDecodeError as exc:
            raise CampaignCarriageError(
                f"Hindsight direct_url.json is invalid: {name}"
            ) from exc
        archive_info = direct.get("archive_info")
        digest = (
            archive_info.get("hashes", {}).get("sha256")
            if isinstance(archive_info, Mapping)
            else None
        )
        if digest != expected:
            raise CampaignCarriageError(
                f"Hindsight wheel hash drifted for {name}: "
                f"expected {expected}, observed {digest}"
            )
        observed[name] = expected
    if importlib.metadata.version("hindsight-all") != "0.10.0":
        raise CampaignCarriageError(
            "installed Hindsight version drifted from v0.10.0"
        )
    return observed


def _require_current_host_material(material: CurrentHostMaterial) -> None:
    for label, path, kind in (
        ("llama.cpp root", material.llama_cpp_root, "dir"),
        ("GGUF", material.model_path, "file"),
        ("Hindsight ONNX model", material.onnx_model_path, "file"),
        ("Hindsight ONNX tokenizer", material.onnx_tokenizer_path, "dir"),
    ):
        valid = path.is_dir() if kind == "dir" else path.is_file()
        if not valid:
            raise CampaignCarriageError(
                f"current-host diagnostic {label} is unavailable: {path}"
            )
    if not 1 <= material.llama_port <= 65535:
        raise CampaignCarriageError("diagnostic llama port is invalid")
    if not 1 <= material.hindsight_port <= 65535:
        raise CampaignCarriageError("diagnostic Hindsight port is invalid")
    source = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=material.llama_cpp_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if (
        source.returncode != 0
        or source.stdout.strip() != _DIAGNOSTIC_LLAMA_CPP_REVISION
    ):
        raise CampaignCarriageError(
            "current-host llama.cpp revision drifted from diagnostic pin"
        )
    clean = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=material.llama_cpp_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if clean.returncode != 0 or clean.stdout.strip():
        raise CampaignCarriageError(
            "current-host llama.cpp checkout is not clean"
        )
    if _sha256_file(material.model_path) != _DIAGNOSTIC_LLAMA_CPP_MODEL_SHA256:
        raise CampaignCarriageError(
            "current-host GGUF hash drifted from diagnostic pin"
        )
    if _sha256_file(material.onnx_model_path) != _DIAGNOSTIC_HINDSIGHT_ONNX_SHA256:
        raise CampaignCarriageError(
            "current-host Hindsight ONNX model hash drifted from diagnostic pin"
        )
    if (
        _sha256_file_tree(material.onnx_tokenizer_path)
        != _DIAGNOSTIC_HINDSIGHT_TOKENIZER_TREE_SHA256
    ):
        raise CampaignCarriageError(
            "current-host Hindsight tokenizer tree drifted from diagnostic pin"
        )
    _installed_hindsight_wheel_hashes()


def _derive_current_host_bindings(
    material: CurrentHostMaterial,
    *,
    diagnostic_owner_id: str,
) -> tuple[LlamaCppLaunchSpec, HindsightLifecycleSpec, HindsightHealthAttestation]:
    """Derive the synthetic comparator from persistent exact host material."""

    _require_current_host_material(material)
    runtime_python = Path(sys.executable).resolve()
    deployment_id = _hindsight_owner_deployment_id(diagnostic_owner_id)
    model_path = material.model_path.resolve()

    llama = LlamaCppLaunchSpec.from_mapping(
        {
            "llama_cpp_root": str(material.llama_cpp_root.resolve()),
            "artifact_path": str(model_path),
            "upstream_revision": _DIAGNOSTIC_LLAMA_CPP_REVISION,
            "expected_build_info": _DIAGNOSTIC_LLAMA_CPP_BUILD_INFO,
            # Pinned llama.cpp defaults model_alias to common_params_model::get_name(),
            # which is the local model path when launched with -m.
            "expected_model_alias": str(model_path),
            "artifact_sha256": _DIAGNOSTIC_LLAMA_CPP_MODEL_SHA256,
            "runtime": "llama.cpp-0.4.0-dev",
            "model_runner": "llama-server-build-10874-e2d2c0d6aa",
            "context": _DIAGNOSTIC_LLAMA_CPP_CONTEXT,
            "slots": _DIAGNOSTIC_LLAMA_CPP_SLOTS,
            "port": material.llama_port,
            "gpu_layers": _DIAGNOSTIC_LLAMA_CPP_GPU_LAYERS,
            "effective_gpu_reservation": 1.0,
            "capacity_evidence": {
                "gpu_identity": dict(_DIAGNOSTIC_GPU_IDENTITY),
            },
        }
    )

    lifecycle = HindsightLifecycleSpec.from_mapping(
        {
            "mode": "owned_local",
            "base_url": f"http://127.0.0.1:{material.hindsight_port}",
            "health_path": "/health",
            "deployment_id": deployment_id,
            "dependency_fingerprint": _DIAGNOSTIC_HINDSIGHT_DEPENDENCY_FINGERPRINT,
            "cleanup_path": "/cleanup",
            "start_path": "/start",
            "runtime_python": str(runtime_python),
            "runtime_version": _DIAGNOSTIC_HINDSIGHT_VERSION,
            "source_revision": _DIAGNOSTIC_HINDSIGHT_SOURCE_REVISION,
            "source_tree": _DIAGNOSTIC_HINDSIGHT_SOURCE_TREE,
            "database_profile": diagnostic_owner_id,
            "llm_model": str(model_path),
            "llm_base_url": f"http://127.0.0.1:{material.llama_port}/v1",
            "retain_max_completion_tokens": HINDSIGHT_RETAIN_MAX_COMPLETION_TOKENS,
            "fail_on_extraction_errors": HINDSIGHT_FAIL_ON_EXTRACTION_ERRORS,
            "llm_supports_string_pattern": HINDSIGHT_LLM_SUPPORTS_STRING_PATTERN,
            "retain_llm_reasoning_effort": HINDSIGHT_RETAIN_LLM_REASONING_EFFORT,
            "consolidation_llm_reasoning_effort": HINDSIGHT_CONSOLIDATION_LLM_REASONING_EFFORT,
            "llm_max_concurrent": HINDSIGHT_LLM_MAX_CONCURRENT,
            "embeddings_provider": "onnx",
            "reranker_provider": "rrf",
            "embeddings_onnx_model_path": str(material.onnx_model_path.resolve()),
            "embeddings_onnx_model_sha256": _DIAGNOSTIC_HINDSIGHT_ONNX_SHA256,
            "embeddings_onnx_tokenizer_path": str(
                material.onnx_tokenizer_path.resolve()
            ),
            "embeddings_onnx_tokenizer_tree_sha256": (
                _DIAGNOSTIC_HINDSIGHT_TOKENIZER_TREE_SHA256
            ),
            "package_wheel_sha256": dict(_DIAGNOSTIC_HINDSIGHT_WHEEL_SHA256),
            "port": material.hindsight_port,
        }
    )

    health = HindsightHealthAttestation.from_mapping(
        {
            "implementation": "hindsight",
            "source_revision": lifecycle.source_revision,
            "version": lifecycle.runtime_version,
            "license": "MIT",
            "deployment": {
                "deployment_id": lifecycle.deployment_id,
                "dependency_fingerprint": lifecycle.dependency_fingerprint,
                "import_status": "passed",
                "llm_connection_verification": "skipped_zero_semantic_policy",
                "process_health_status": "passed",
                "capability_status": "passed",
            },
            "semantic_operations_called": [],
            "semantic_generation_count": 0,
            "benchmark_question_count": 0,
            "answer_model_generation_count": 0,
            "judge_call_count": 0,
        }
    )
    return llama, lifecycle, health


def _synthetic_stress_session(
    *,
    session_id: str,
    exchange_count: int,
    offset: int,
    include_copper_fact: bool,
) -> HindsightHistorySession:
    if exchange_count <= 0:
        raise CampaignCarriageError("synthetic stress exchange_count must be positive")
    base = datetime(2025, 1, 2, tzinfo=timezone.utc)
    items: list[Mapping[str, str | None]] = []
    for index in range(exchange_count):
        ordinal = offset + index
        timestamp = (base + timedelta(minutes=ordinal)).isoformat()
        if include_copper_fact and index == 0:
            user_content = "The copper token is stored in drawer seven."
            assistant_content = "Understood; the copper token is in drawer seven."
        else:
            user_content = (
                f"Synthetic memory item {ordinal:03d}: "
                f"the diagnostic marker is value-{ordinal:03d}."
            )
            assistant_content = (
                f"Recorded synthetic marker value-{ordinal:03d} for diagnostics."
            )
        items.extend(
            (
                {
                    "role": "user",
                    "content": user_content,
                    "timestamp": timestamp,
                },
                {
                    "role": "assistant",
                    "content": assistant_content,
                    "timestamp": timestamp,
                },
            )
        )
    return HindsightHistorySession(
        session_id=session_id,
        order=offset,
        items=tuple(items),
    )


def _synthetic_sessions(profile: str) -> tuple[HindsightHistorySession, ...]:
    if profile == "single":
        return (
            HindsightHistorySession(
                session_id=_SYNTHETIC_SESSION_ID,
                order=0,
                items=_SYNTHETIC_ITEMS,
            ),
        )
    if profile == "post2986":
        return (
            _synthetic_stress_session(
                session_id="synthetic-warmup-0040",
                exchange_count=_POST2986_WARMUP_EXCHANGES,
                offset=0,
                include_copper_fact=True,
            ),
            _synthetic_stress_session(
                session_id="synthetic-stress-0045",
                exchange_count=_POST2986_STRESS_EXCHANGES,
                offset=_POST2986_WARMUP_EXCHANGES,
                include_copper_fact=False,
            ),
        )
    raise CampaignCarriageError(f"unsupported synthetic stress profile: {profile}")


def _mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CampaignCarriageError(f"{label} must be an object")
    return value


def _load_source_descriptor(path: Path) -> Mapping[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CampaignCarriageError(f"cannot read source descriptor: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CampaignCarriageError("source descriptor is not valid JSON") from exc
    return _mapping(raw, label="source descriptor")


def _derive_diagnostic_bindings(
    source: Mapping[str, Any],
    *,
    diagnostic_owner_id: str,
) -> tuple[LlamaCppLaunchSpec, HindsightLifecycleSpec, HindsightHealthAttestation]:
    """Copy only operational identities and replace owner-local Hindsight state."""

    llama = LlamaCppLaunchSpec.from_mapping(
        _mapping(source.get("llama_cpp"), label="source descriptor llama_cpp")
    )

    lifecycle_raw = dict(
        _mapping(
            source.get("hindsight_lifecycle"),
            label="source descriptor hindsight_lifecycle",
        )
    )
    lifecycle_raw["deployment_id"] = _hindsight_owner_deployment_id(
        diagnostic_owner_id
    )
    lifecycle_raw["database_profile"] = diagnostic_owner_id
    # Diagnostic runs are derived from current repository apparatus authority,
    # not from historical descriptor copies of repairable runtime policy.
    lifecycle_raw["retain_max_completion_tokens"] = (
        HINDSIGHT_RETAIN_MAX_COMPLETION_TOKENS
    )
    lifecycle_raw["fail_on_extraction_errors"] = HINDSIGHT_FAIL_ON_EXTRACTION_ERRORS
    lifecycle_raw["llm_supports_string_pattern"] = HINDSIGHT_LLM_SUPPORTS_STRING_PATTERN
    lifecycle_raw["retain_llm_reasoning_effort"] = HINDSIGHT_RETAIN_LLM_REASONING_EFFORT
    lifecycle_raw["consolidation_llm_reasoning_effort"] = (
        HINDSIGHT_CONSOLIDATION_LLM_REASONING_EFFORT
    )
    lifecycle_raw["llm_max_concurrent"] = HINDSIGHT_LLM_MAX_CONCURRENT
    lifecycle = HindsightLifecycleSpec.from_mapping(lifecycle_raw)

    source_health = _mapping(
        source.get("hindsight_health"),
        label="source descriptor hindsight_health",
    )
    license_name = source_health.get("license")
    if not isinstance(license_name, str) or not license_name.strip():
        raise CampaignCarriageError(
            "source descriptor hindsight_health.license must be non-empty"
        )
    health = HindsightHealthAttestation.from_mapping(
        {
            "implementation": "hindsight",
            "source_revision": lifecycle.source_revision,
            "version": lifecycle.runtime_version,
            "license": license_name,
            "deployment": {
                "deployment_id": lifecycle.deployment_id,
                "dependency_fingerprint": lifecycle.dependency_fingerprint,
                "import_status": "passed",
                "llm_connection_verification": "skipped_zero_semantic_policy",
                "process_health_status": "passed",
                "capability_status": "passed",
            },
            "semantic_operations_called": [],
            "semantic_generation_count": 0,
            "benchmark_question_count": 0,
            "answer_model_generation_count": 0,
            "judge_call_count": 0,
        }
    )
    return llama, lifecycle, health


def _llama_cpp_chat_smoke(spec: LlamaCppLaunchSpec) -> Mapping[str, object]:
    payload = {
        "model": spec.expected_model_alias,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Synthetic infrastructure diagnostic. "
                    "Reply briefly that the local model endpoint is reachable."
                ),
            }
        ],
        "temperature": 0,
        "stream": False,
    }
    try:
        with httpx.Client(timeout=120.0, trust_env=False) as client:
            response = client.post(
                f"http://127.0.0.1:{spec.port}/v1/chat/completions",
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise CampaignCarriageError(
            "synthetic llama.cpp chat diagnostic request failed"
        ) from exc
    if response.status_code != 200:
        raise CampaignCarriageError(
            "synthetic llama.cpp chat diagnostic returned "
            f"HTTP {response.status_code}"
        )
    try:
        body = response.json()
    except ValueError as exc:
        raise CampaignCarriageError(
            "synthetic llama.cpp chat diagnostic response was not JSON"
        ) from exc
    if not isinstance(body, Mapping):
        raise CampaignCarriageError(
            "synthetic llama.cpp chat diagnostic response was not an object"
        )
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise CampaignCarriageError(
            "synthetic llama.cpp chat diagnostic response had no choices"
        )
    return {
        "endpoint": "/v1/chat/completions",
        "status_code": response.status_code,
        "response_keys": sorted(str(key) for key in body),
        "choice_count": len(choices),
    }


def run_synthetic_hindsight_smoke(
    *,
    source_descriptor: Mapping[str, Any] | None,
    diagnostic_owner_id: str,
    repo_root: Path,
    artifact_root: Path,
    stress_profile: str = "single",
    current_host_material: CurrentHostMaterial | None = None,
) -> Mapping[str, Any]:
    """Run one isolated synthetic live comparator diagnostic.

    The function deliberately has no benchmark inputs and no scientific ledger
    parameter.  A new artifact root is required for every invocation so failed
    diagnostics remain inspectable without contaminating a later retry.
    """

    if not repo_root.is_absolute():
        raise CampaignCarriageError("repo_root must be absolute")
    if not artifact_root.is_absolute():
        raise CampaignCarriageError("artifact_root must be absolute")
    if artifact_root.exists():
        raise CampaignCarriageError("synthetic smoke artifact_root must be fresh")
    if stress_profile not in _STRESS_PROFILES:
        raise CampaignCarriageError(
            f"unsupported synthetic stress profile: {stress_profile}"
        )

    if (source_descriptor is None) == (current_host_material is None):
        raise CampaignCarriageError(
            "synthetic smoke requires exactly one operational source: "
            "source_descriptor or current_host_material"
        )
    if current_host_material is not None:
        llama_spec, lifecycle_spec, expected_health = _derive_current_host_bindings(
            current_host_material,
            diagnostic_owner_id=diagnostic_owner_id,
        )
        operational_source: dict[str, object] = {
            "mode": "current_host_material",
            "llama_cpp_root": str(current_host_material.llama_cpp_root.resolve()),
            "model_path": str(current_host_material.model_path.resolve()),
            "model_sha256": _DIAGNOSTIC_LLAMA_CPP_MODEL_SHA256,
            "onnx_model_path": str(current_host_material.onnx_model_path.resolve()),
            "onnx_model_sha256": _DIAGNOSTIC_HINDSIGHT_ONNX_SHA256,
            "onnx_tokenizer_path": str(
                current_host_material.onnx_tokenizer_path.resolve()
            ),
            "onnx_tokenizer_tree_sha256": (
                _DIAGNOSTIC_HINDSIGHT_TOKENIZER_TREE_SHA256
            ),
            "llama_cpp_revision": _DIAGNOSTIC_LLAMA_CPP_REVISION,
            "hindsight_source_revision": _DIAGNOSTIC_HINDSIGHT_SOURCE_REVISION,
            "hindsight_source_tree": _DIAGNOSTIC_HINDSIGHT_SOURCE_TREE,
            "hindsight_dependency_fingerprint": (
                _DIAGNOSTIC_HINDSIGHT_DEPENDENCY_FINGERPRINT
            ),
            "hindsight_wheel_sha256": dict(_DIAGNOSTIC_HINDSIGHT_WHEEL_SHA256),
            "llm_max_concurrent": HINDSIGHT_LLM_MAX_CONCURRENT,
        }
    else:
        assert source_descriptor is not None
        llama_spec, lifecycle_spec, expected_health = _derive_diagnostic_bindings(
            source_descriptor,
            diagnostic_owner_id=diagnostic_owner_id,
        )
        operational_source = {
            "mode": "source_descriptor",
        }

    artifact_root.mkdir(parents=True, exist_ok=False)
    bank_id = _hindsight_axis_bank_id(
        lifecycle_spec.database_profile,
        "synthetic-smoke",
    )
    histories = _synthetic_sessions(stress_profile)

    capture_proxy = SyntheticLlamaCaptureProxy(
        upstream_base_url=f"http://127.0.0.1:{llama_spec.port}/v1",
        artifact_root=artifact_root / "llama-capture",
    )
    lifecycle_spec = replace(lifecycle_spec, llm_base_url=capture_proxy.base_url)
    lifecycle: HindsightDeploymentSession | None = None
    live_session: LiveLaunchSession | None = None
    lifecycle_cleanup: Mapping[str, Any] | None = None
    live_cleanup: Mapping[str, Any] | None = None
    capture_cleanup: Mapping[str, Any] | None = None
    result: dict[str, Any] | None = None
    failure: BaseException | None = None
    retain_response: Mapping[str, Any] | None = None
    recall_response_shape: Mapping[str, object] | None = None
    phase = "startup"
    retained_exchange_count = 0
    consolidation_receipts: list[dict[str, object]] = []

    try:
        capture_proxy.start()
        lifecycle = HindsightDeploymentSession(
            lifecycle_spec,
            expected_health,
            repo_root=repo_root,
            evidence_root=artifact_root / "hindsight",
        )
        lifecycle.start()
        observed_health = verify_hindsight_health(expected_health, lifecycle)
        live_session = start_llama_cpp_session(
            llama_spec,
            artifact_root / "llama-cpp",
        )
        live_attestation = live_session.attest()

        for session_index, history in enumerate(histories):
            phase = f"retain:{history.session_id}"
            pre_existing_pending = lifecycle.consolidation_pending_ids(
                bank_id=bank_id,
                allow_missing_bank=session_index == 0,
            )
            session_retain_count = 0
            for exchange_index, _exchange in enumerate(history.exchanges()):
                retain_request = history.to_retain_request(
                    bank_id=bank_id,
                    context_label="MemConflict",
                    exchange_index=exchange_index,
                )
                retain_response = lifecycle.retain(
                    bank_id=bank_id,
                    items=(retain_request,),
                )
                retained_exchange_count += 1
                session_retain_count += 1
            phase = f"consolidation:{history.session_id}"
            consolidation = lifecycle.wait_for_consolidation(
                bank_id=bank_id,
                pre_existing_pending_ids=pre_existing_pending,
            )
            consolidation_receipts.append(
                {
                    "session_id": history.session_id,
                    "retain_count": session_retain_count,
                    **dict(consolidation),
                }
            )
        phase = "recall"
        recalled = lifecycle.recall(
            _SYNTHETIC_QUESTION,
            bank_id=bank_id,
            query_timestamp=_SYNTHETIC_QUERY_TIMESTAMP,
        )
        recalled_results = recalled.get("results")
        recall_response_shape = {
            "keys": sorted(str(key) for key in recalled),
            "result_count": (
                len(recalled_results) if isinstance(recalled_results, list) else None
            ),
        }
        retrieved = _hindsight_retrieved_memories(recalled)
        if not retrieved:
            raise CampaignCarriageError(
                "synthetic Hindsight recall returned no mapped memories"
            )
        llama_chat = _llama_cpp_chat_smoke(llama_spec)

        result = {
            "format_version": SMOKE_FORMAT_VERSION,
            "target": SMOKE_TARGET,
            "status": "NON_CITABLE_DIAGNOSTIC_PASS",
            "citable": False,
            "scientific_spend": "NOT_OPENED",
            "benchmark_text_used": False,
            "benchmark_question_count": 0,
            "judge_call_count": 0,
            "diagnostic_owner_id": diagnostic_owner_id,
            "operational_source": operational_source,
            "bank_id": bank_id,
            "hindsight_health_fingerprint": observed_health.fingerprint,
            "hindsight_semantic_operation_count": lifecycle.semantic_operation_count,
            "retain_response": dict(retain_response),
            "retain_count": retained_exchange_count,
            "recall_response_shape": dict(recall_response_shape),
            "retrieved_memory_count": len(retrieved),
            "consolidation": dict(consolidation),
            "consolidation_receipts": consolidation_receipts,
            "llama_cpp_launch_count": live_session.launch_count,
            "llama_cpp_live_attestation_fingerprint": live_attestation.fingerprint,
            "llama_cpp_chat": dict(llama_chat),
            "synthetic_contract": {
                "session_id": _SYNTHETIC_SESSION_ID,
                "question": _SYNTHETIC_QUESTION,
                "query_timestamp": _SYNTHETIC_QUERY_TIMESTAMP,
                "retain_context": "MemConflict",
                "stress_profile": stress_profile,
                "session_count": len(histories),
                "exchange_count": sum(len(history.exchanges()) for history in histories),
                "post2986_shape": (
                    {
                        "warmup_completed_shape": _POST2986_WARMUP_EXCHANGES,
                        "stress_burst_shape": _POST2986_STRESS_EXCHANGES,
                    }
                    if stress_profile == "post2986"
                    else None
                ),
            },
        }
    except BaseException as exc:
        failure = exc
    finally:
        if lifecycle is not None:
            try:
                lifecycle_cleanup = lifecycle.cleanup()
            except BaseException as exc:
                lifecycle_cleanup = {
                    "all_owned_processes_terminated": False,
                    "external_processes_touched": 0,
                    "errors": [f"Hindsight cleanup raised {type(exc).__name__}"],
                }
                if failure is None:
                    failure = exc
        try:
            capture_cleanup = capture_proxy.cleanup()
        except BaseException as exc:
            capture_cleanup = {
                "all_owned_processes_terminated": False,
                "external_processes_touched": 0,
                "errors": [f"capture proxy cleanup raised {type(exc).__name__}"],
            }
            if failure is None:
                failure = exc
        if live_session is not None:
            try:
                live_cleanup = live_session.cleanup()
            except BaseException as exc:
                live_cleanup = {
                    "all_owned_processes_terminated": False,
                    "external_processes_touched": 0,
                    "errors": [f"llama cleanup raised {type(exc).__name__}"],
                }
                if failure is None:
                    failure = exc

    if result is None:
        result = {
            "format_version": SMOKE_FORMAT_VERSION,
            "target": SMOKE_TARGET,
            "status": "NON_CITABLE_DIAGNOSTIC_FAIL",
            "citable": False,
            "scientific_spend": "NOT_OPENED",
            "benchmark_text_used": False,
            "benchmark_question_count": 0,
            "judge_call_count": 0,
            "diagnostic_owner_id": diagnostic_owner_id,
            "operational_source": operational_source,
            "bank_id": bank_id,
            "stress_profile": stress_profile,
            "phase": phase,
            "retain_count": retained_exchange_count,
            "consolidation_receipts": consolidation_receipts,
            "failure": None
            if failure is None
            else {
                "type": type(failure).__name__,
                "message": str(failure),
            },
            "retain_response": (
                None if retain_response is None else dict(retain_response)
            ),
            "recall_response_shape": (
                None
                if recall_response_shape is None
                else dict(recall_response_shape)
            ),
        }

    result["llama_capture"] = (
        None if capture_cleanup is None else dict(capture_cleanup)
    )
    result["cleanup"] = {
        "llama_cpp": None if live_cleanup is None else dict(live_cleanup),
        "hindsight": (
            None if lifecycle_cleanup is None else dict(lifecycle_cleanup)
        ),
        "capture_proxy": (
            None if capture_cleanup is None else {
                "all_owned_processes_terminated": capture_cleanup.get(
                    "all_owned_processes_terminated"
                ),
                "external_processes_touched": capture_cleanup.get(
                    "external_processes_touched"
                ),
                "errors": capture_cleanup.get("errors"),
                "proxy_port": capture_cleanup.get("proxy_port"),
            }
        ),
    }
    _write_json_fsync(
        artifact_root / "synthetic-hindsight-smoke.json",
        result,
    )

    if failure is not None:
        raise failure
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a non-citable synthetic Hindsight comparator smoke."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-descriptor", type=Path)
    source.add_argument(
        "--current-host-material",
        action="store_true",
        help=(
            "derive the diagnostic operational binding from persistent current-host "
            "llama.cpp/GGUF/Hindsight/ONNX material instead of a campaign descriptor"
        ),
    )
    parser.add_argument("--llama-cpp-root", type=Path)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--onnx-model-path", type=Path)
    parser.add_argument("--onnx-tokenizer-path", type=Path)
    parser.add_argument("--llama-port", type=int, default=1234)
    parser.add_argument("--hindsight-port", type=int, default=18096)
    parser.add_argument("--diagnostic-owner-id", required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument(
        "--stress-profile",
        choices=tuple(sorted(_STRESS_PROFILES)),
        default="single",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    source: Mapping[str, Any] | None
    host_material: CurrentHostMaterial | None
    if args.current_host_material:
        required_paths = {
            "llama_cpp_root": args.llama_cpp_root,
            "model_path": args.model_path,
            "onnx_model_path": args.onnx_model_path,
            "onnx_tokenizer_path": args.onnx_tokenizer_path,
        }
        missing = sorted(name for name, value in required_paths.items() if value is None)
        if missing:
            raise CampaignCarriageError(
                "current-host diagnostic source requires paths: "
                + ", ".join(missing)
            )
        assert args.llama_cpp_root is not None
        assert args.model_path is not None
        assert args.onnx_model_path is not None
        assert args.onnx_tokenizer_path is not None
        source = None
        host_material = CurrentHostMaterial(
            llama_cpp_root=args.llama_cpp_root.resolve(),
            model_path=args.model_path.resolve(),
            onnx_model_path=args.onnx_model_path.resolve(),
            onnx_tokenizer_path=args.onnx_tokenizer_path.resolve(),
            llama_port=args.llama_port,
            hindsight_port=args.hindsight_port,
        )
    else:
        assert args.source_descriptor is not None
        source = _load_source_descriptor(args.source_descriptor.resolve())
        host_material = None
    result = run_synthetic_hindsight_smoke(
        source_descriptor=source,
        diagnostic_owner_id=args.diagnostic_owner_id,
        repo_root=args.repo_root.resolve(),
        artifact_root=args.artifact_root.resolve(),
        stress_profile=args.stress_profile,
        current_host_material=host_material,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

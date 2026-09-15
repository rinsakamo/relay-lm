"""One-shot installed RelayLM + llama.cpp release-path proof harness.

This module is an evaluation-only transaction controller.  It deliberately
does not add a provider, prompt, parser, or production runtime path.  The
future physical owner invokes it through the registered public physical runner;
the RelayLM product under test is the wheel installed into the transaction
venv, while the existing Stage-R module supplies only the llama-server
laboratory lifecycle helpers.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import http.client
import http.server
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import sysconfig
import tempfile
from threading import RLock, Thread
import time
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

import httpx
import yaml

from relaylm.actual_model_llama_cpp import attest_llama_cpp_runtime
from relaylm.actual_model_scenarios import load_actual_model_scenario_set
from relaylm.actual_model_targets import (
    ActualModelArtifactTarget,
    load_actual_model_target,
    verify_actual_model_artifact,
)
from relaylm.providers.llama_cpp_backend import (
    LLAMA_CPP_CACHE_POLICY_DISABLED,
    LLAMA_CPP_CHAT_COUNTER_CAPABILITY,
    LLAMA_CPP_CHAT_COUNTER_IMPLEMENTATION,
    LLAMA_CPP_CHAT_COUNTER_VERSION,
    LLAMA_CPP_FRAMING_METHOD,
    LLAMA_CPP_RENDERER_METHOD,
    LlamaCppCapabilityAttestation,
    LlamaCppRuntimeIdentity,
    build_llama_cpp_capability,
)
from relaylm.providers.openai_compatible_extraction_projection import (
    ExtractionProjectionMode,
    extraction_schema_name,
    extraction_wire_schema,
)
from relaylm.actual_model_stage_r_llama_cpp_transaction import (
    DEFAULT_SLOTS,
    _collect_gpu_identity,
    _collect_llama_identity,
    _model_ids,
    _port_is_free,
    _start_server,
    _terminate_owned_process,
    _wait_until_ready,
)
from tools.repository_authority import load_declarations, qualification_fingerprint


TRANSACTION_FORMAT_VERSION = 1
TARGET_NAME = "v1:installed-llama-cpp"
DEFAULT_TARGET_PATH = Path(
    "evaluation/actual_model/targets/"
    "gemma-4-12b-it-q4-k-m-lmstudio-community-v1.json"
)
CANONICAL_FIXTURE_PATH = Path("evaluation/actual_model/characters/foundation-v1")
CURRENT_STAGE_R_AUTHORITY_PATH = Path(
    "evaluation/actual_model/screenings/stage-r-current-v1.json"
)
CANONICAL_SCENARIO_ID = "continuity-lifecycle-v1"
DEFAULT_LLAMACPP_ORIGIN = "http://127.0.0.1:1234"
DEFAULT_LLAMACPP_PORT = 1234
DEFAULT_RELAY_PORT = 18090
REQUEST_TIMEOUT_SECONDS = 600.0
READINESS_TIMEOUT_SECONDS = 120.0
READINESS_POLL_SECONDS = 0.5
PASS2_OUTPUT_TOKENS = 256
MAX_RESPONSE_EXCERPT = 1024
MAX_ERROR_TEXT = 2048
PROXY_PATHS = frozenset({"/v1/chat/completions", "/v1/chat/completions/input_tokens"})
PHYSICAL_EVIDENCE_DISPOSITION = "EVIDENCE_RECORDED"
PHYSICAL_INVALID_DISPOSITION = "PHYSICAL_INVALID"
EXECUTION_OBSERVATION_STATE = "observed_unvalidated"
EXECUTION_VALIDATION_STATE = "validated_success"

COUNTER_ENDPOINT_ROLES = ("full", "framing")
PASS1_LOGICAL_ROLES = ("protected_floor", "selected_plan")
PASS2_LOGICAL_ROLES = ("extraction",)
CANONICAL_TWO_TURN_TOPOLOGY = (
    ("buffered_pass1", PASS1_LOGICAL_ROLES),
    ("buffered_pass2", PASS2_LOGICAL_ROLES),
    ("streaming_pass1", PASS1_LOGICAL_ROLES),
    ("streaming_pass2", PASS2_LOGICAL_ROLES),
)


@dataclass(frozen=True, slots=True)
class LogicalInputCountOperationSpec:
    """One canonical full/framing pair before its upcoming generation."""

    logical_operation_index: int
    generation_index: int
    generation_phase: str
    budget_role: str
    endpoint_calls: int


def _expand_canonical_logical_operations() -> tuple[LogicalInputCountOperationSpec, ...]:
    operations: list[LogicalInputCountOperationSpec] = []
    logical_operation_index = 0
    for generation_index, (generation_phase, budget_roles) in enumerate(
        CANONICAL_TWO_TURN_TOPOLOGY,
        start=1,
    ):
        for budget_role in budget_roles:
            logical_operation_index += 1
            operations.append(
                LogicalInputCountOperationSpec(
                    logical_operation_index=logical_operation_index,
                    generation_index=generation_index,
                    generation_phase=generation_phase,
                    budget_role=budget_role,
                    endpoint_calls=len(COUNTER_ENDPOINT_ROLES),
                )
            )
    return tuple(operations)


CANONICAL_LOGICAL_OPERATION_SPECS = _expand_canonical_logical_operations()
CANONICAL_GENERATION_PHASES = tuple(
    generation_phase for generation_phase, _ in CANONICAL_TWO_TURN_TOPOLOGY
)
CANONICAL_PUBLIC_EXECUTION_KINDS = tuple(
    dict.fromkeys(phase.split("_", 1)[0] for phase in CANONICAL_GENERATION_PHASES)
)
CANONICAL_GENERATION_COUNTS_BY_EXECUTION = {
    execution: sum(
        phase.startswith(f"{execution}_") for phase in CANONICAL_GENERATION_PHASES
    )
    for execution in CANONICAL_PUBLIC_EXECUTION_KINDS
}
SEMANTIC_GENERATION_CEILING = len(CANONICAL_GENERATION_PHASES)
EXPECTED_LOGICAL_OPERATION_COUNT = len(CANONICAL_LOGICAL_OPERATION_SPECS)
EXPECTED_INPUT_ENDPOINT_CALL_COUNT = sum(
    spec.endpoint_calls for spec in CANONICAL_LOGICAL_OPERATION_SPECS
)


def _canonical_provider_sequence() -> tuple[tuple[str, int, str | None], ...]:
    full_role, framing_role = COUNTER_ENDPOINT_ROLES
    sequence: list[tuple[str, int, str | None]] = []
    for index, spec in enumerate(CANONICAL_LOGICAL_OPERATION_SPECS):
        sequence.extend(
            (
                ("input_token_count", spec.generation_index, full_role),
                ("input_token_count", spec.generation_index, framing_role),
            )
        )
        next_spec = CANONICAL_LOGICAL_OPERATION_SPECS[index + 1] if index + 1 < len(
            CANONICAL_LOGICAL_OPERATION_SPECS
        ) else None
        if next_spec is None or next_spec.generation_index != spec.generation_index:
            sequence.append(("generation", spec.generation_index, None))
    return tuple(sequence)


CANONICAL_PROVIDER_SEQUENCE = _canonical_provider_sequence()
MINIMUM_EVIDENCE_FILENAMES = (
    "binding.json",
    "transaction-summary.json",
    "installed-artifact.json",
    "runtime-config.yaml",
    "runtime-config.sha256",
    "doctor.json",
    "relaylm-serve.log",
    "llama-server.log",
    "runtime-attestation.json",
    "provider-request-ledger.json",
    "input-count-ledger.json",
    "buffered-execution.json",
    "streaming-execution.json",
    "state-continuity-before-after.json",
    "cleanup.json",
)


class InstalledLlamaCppTransactionError(RuntimeError):
    """The installed-path transaction cannot make a truthful claim."""


class RequestLedgerError(InstalledLlamaCppTransactionError):
    """The model-facing proxy observed an impossible request sequence."""


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    evidence_root = _new_root(args.evidence_root, prefix="relaylm-installed-llama-cpp-")
    return _run_transaction(args, evidence_root=evidence_root)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one bounded installed RelayLM release-path proof around one "
            "transaction-owned llama-server lifetime."
        )
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--llama-cpp-root",
        default=str(Path.home() / "src" / "llama.cpp"),
    )
    parser.add_argument("--target-path", default=str(DEFAULT_TARGET_PATH))
    parser.add_argument("--artifact-path")
    parser.add_argument("--evidence-root")
    parser.add_argument("--llama-port", type=int, default=DEFAULT_LLAMACPP_PORT)
    parser.add_argument("--relay-port", type=int, default=DEFAULT_RELAY_PORT)
    parser.add_argument("--scenario-id", default=CANONICAL_SCENARIO_ID)
    return parser


def _run_transaction(args: argparse.Namespace, *, evidence_root: Path) -> int:
    repo_root = Path(args.repo_root).expanduser().resolve()
    llama_cpp_root = Path(args.llama_cpp_root).expanduser().resolve()
    server_process: subprocess.Popen[str] | None = None
    relay_process: subprocess.Popen[str] | None = None
    proxy: _ForwardingProxy | None = None
    ledger: RequestLedger | None = None
    fixture: dict[str, Any] | None = None
    buffered: dict[str, Any] | None = None
    streaming: dict[str, Any] | None = None
    snapshots: dict[str, Any] = {}
    summary: dict[str, Any] = {
        "format_version": TRANSACTION_FORMAT_VERSION,
        "target": TARGET_NAME,
        "evidence_root": str(evidence_root),
        "disposition": None,
        "classification": None,
        "phase": "created",
        "server_launch_count": 0,
        "relay_serve_launch_count": 0,
        "semantic_generation_count": 0,
        "semantic_generation_ceiling": SEMANTIC_GENERATION_CEILING,
        "semantic_retry_count": 0,
        "replay_count": 0,
        "reseed_count": 0,
        "fallback_count": 0,
        "repair_generation_count": 0,
        "repository_mutation_count": 0,
        "fastcal_count": 0,
        "lm_studio_contact_count": 0,
        "vllm_contact_count": 0,
    }
    return_code = 2
    (evidence_root / "relaylm-serve.log").touch()
    (evidence_root / "llama-server.log").touch()

    try:
        evidence_root = evidence_root.resolve()
        summary["phase"] = "repository_binding"
        binding = _bind_repository(repo_root=repo_root, evidence_root=evidence_root)
        _write_json(evidence_root / "binding.json", binding)
        summary["relaylm"] = binding["relaylm"]

        summary["phase"] = "target_verification"
        target_path = _resolve_target_path(repo_root, args.target_path)
        target = _load_artifact_target(target_path)
        artifact_path = _resolve_artifact_path(target, args.artifact_path)
        verification = verify_actual_model_artifact(
            target=target,
            artifact_path=artifact_path,
        )
        summary["target"] = target.to_mapping()
        summary["artifact_verification"] = verification.to_mapping()

        summary["phase"] = "wheel_build"
        package_version = _source_package_version()
        wheel_path = _build_exact_wheel(
            repo_root=repo_root,
            build_root=evidence_root / "wheel-build",
        )
        _verify_repository_binding(repo_root=repo_root, binding=binding)

        summary["phase"] = "non_editable_install"
        installed = _install_exact_wheel(
            wheel_path=wheel_path,
            package_version=package_version,
            transaction_root=evidence_root / "installed-runtime",
            evidence_root=evidence_root,
            repo_root=repo_root,
        )
        _write_json(evidence_root / "installed-artifact.json", installed)
        _verify_repository_binding(repo_root=repo_root, binding=binding)

        summary["phase"] = "server_laboratory"
        _require_llama_port(args.llama_port)
        server_binary = llama_cpp_root / "build" / "bin" / "llama-server"
        revision, version, build_number = _collect_llama_identity(
            llama_cpp_root=llama_cpp_root,
            server_binary=server_binary,
        )
        gpu_identity = _collect_gpu_identity()
        if not _port_is_free("127.0.0.1", args.llama_port):
            raise InstalledLlamaCppTransactionError(
                f"llama.cpp port is occupied: 127.0.0.1:{args.llama_port}"
            )
        server_process, launch_command = _start_server(
            server_binary=server_binary,
            artifact_path=artifact_path,
            port=args.llama_port,
            log_path=evidence_root / "llama-server.log",
        )
        summary["server_launch_count"] = 1
        summary["server"] = {
            "pid": server_process.pid,
            "binary": str(server_binary),
            "llama_cpp_root": str(llama_cpp_root),
            "revision": revision,
            "version": version,
            "build_number": build_number,
            "launch_command": _shell_join(launch_command),
            "log_path": str(evidence_root / "llama-server.log"),
            "gpu_identity": gpu_identity,
        }
        _wait_until_ready(
            process=server_process,
            origin=f"http://127.0.0.1:{args.llama_port}",
        )
        probe = _probe_server(
            origin=f"http://127.0.0.1:{args.llama_port}",
            expected_slots=DEFAULT_SLOTS,
        )
        request_model = probe["request_model"]
        runtime_identity, capability = _attest_runtime(
            probe=probe,
            revision=revision,
            version=version,
            build_number=build_number,
            request_model=request_model,
            artifact_path=artifact_path,
            verification=verification,
            target=target,
        )
        _write_json(
            evidence_root / "runtime-attestation.json",
            _runtime_attestation_evidence(
                probe=probe,
                revision=revision,
                version=version,
                build_number=build_number,
                request_model=request_model,
                artifact_path=artifact_path,
                verification=verification,
                target=target,
                runtime_identity=runtime_identity,
                capability=capability,
            ),
        )

        summary["phase"] = "fixture_and_config"
        fixture = _materialize_fixture(
            repo_root=repo_root,
            evidence_root=evidence_root,
            scenario_id=args.scenario_id,
        )
        relay_port = _resolve_relay_port(args.relay_port)
        ledger = RequestLedger(expected_model=request_model)
        proxy = _ForwardingProxy(
            origin=f"http://127.0.0.1:{args.llama_port}",
            ledger=ledger,
        )
        proxy.start()
        config_path = evidence_root / "runtime-config.yaml"
        config = _write_runtime_config(
            config_path=config_path,
            fixture=fixture,
            proxy_base_url=proxy.base_url,
            relay_port=relay_port,
            request_model=request_model,
            artifact_path=artifact_path,
            runtime_identity=runtime_identity,
            capability=capability,
        )
        config_sha = _sha256_file(config_path)
        (evidence_root / "runtime-config.sha256").write_text(
            f"sha256:{config_sha}  runtime-config.yaml\n",
            encoding="utf-8",
        )
        summary["runtime_config"] = {
            "path": str(config_path),
            "sha256": f"sha256:{config_sha}",
            "mapping": config,
        }

        summary["phase"] = "installed_doctor"
        doctor = _run_installed_doctor(
            installed=installed,
            config_path=config_path,
            cwd=evidence_root,
        )
        _write_json(evidence_root / "doctor.json", doctor)

        summary["phase"] = "installed_serve"
        relay_process = _start_installed_serve(
            installed=installed,
            config_path=config_path,
            cwd=evidence_root,
            log_path=evidence_root / "relaylm-serve.log",
        )
        summary["relay_serve_launch_count"] = 1
        summary["relay_server"] = {
            "pid": relay_process.pid,
            "command": _shell_join(
                [installed["console_path"], "serve", "--config", str(config_path)]
            ),
            "log_path": str(evidence_root / "relaylm-serve.log"),
            "installed_package_path": installed["module_path"],
        }
        relay_origin = f"http://127.0.0.1:{relay_port}"
        _wait_http_health(relay_process, relay_origin)
        relay_models = _get_json(f"{relay_origin}/v1/models")
        expected_public_ids = ["installed-buffered", "installed-streaming"]
        if _model_ids(relay_models) != expected_public_ids:
            raise InstalledLlamaCppTransactionError(
                "installed RelayLM public Cognitive Profile IDs are not canonical"
            )
        summary["public_cognitive_profiles"] = relay_models

        snapshots["before"] = _snapshot_packages(fixture)
        summary["phase"] = "buffered_request"
        buffered = _run_public_buffered(
            relay_origin=relay_origin,
            prompt=fixture["prompt"],
        )
        _wait_generation_batch(
            ledger,
            expected_count=CANONICAL_GENERATION_COUNTS_BY_EXECUTION["buffered"],
        )
        snapshots["after_buffered"] = _snapshot_packages(fixture)

        summary["phase"] = "streaming_request"
        streaming = _run_public_streaming(
            relay_origin=relay_origin,
            prompt=fixture["prompt"],
        )
        _wait_generation_batch(
            ledger,
            expected_count=SEMANTIC_GENERATION_CEILING,
        )
        snapshots["after_streaming"] = _snapshot_packages(fixture)

        _write_json(
            evidence_root / "buffered-execution.json",
            _execution_evidence(
                kind="buffered",
                public_request=buffered,
                ledger=ledger,
                validation_state=EXECUTION_OBSERVATION_STATE,
            ),
        )
        _write_json(
            evidence_root / "streaming-execution.json",
            _execution_evidence(
                kind="streaming",
                public_request=streaming,
                ledger=ledger,
                validation_state=EXECUTION_OBSERVATION_STATE,
            ),
        )
        _validate_successful_ledger(ledger)
        _write_json(evidence_root / "provider-request-ledger.json", ledger.provider_evidence())
        _write_json(evidence_root / "input-count-ledger.json", ledger.input_evidence())
        _write_json(
            evidence_root / "buffered-execution.json",
            _execution_evidence(
                kind="buffered",
                public_request=buffered,
                ledger=ledger,
                validation_state=EXECUTION_VALIDATION_STATE,
            ),
        )
        _write_json(
            evidence_root / "streaming-execution.json",
            _execution_evidence(
                kind="streaming",
                public_request=streaming,
                ledger=ledger,
                validation_state=EXECUTION_VALIDATION_STATE,
            ),
        )
        _write_json(
            evidence_root / "state-continuity-before-after.json",
            {
                "format_version": 1,
                "fixture": fixture["evidence_identity"],
                "continuity_runtime": fixture["continuity_runtime"],
                "continuity_runtime_source": fixture["continuity_runtime_source"],
                "response_first": {
                    "buffered": "pass1_visible_response_returned_by_public_api; pass2 retained separately",
                    "streaming": "pass1_stream_completed_by_public_api; pass2 retained separately",
                },
                "snapshots": snapshots,
                "product_quality": "not_declared_by_harness",
            },
        )
        missing_evidence = [
            name
            for name in MINIMUM_EVIDENCE_FILENAMES
            if name not in {"transaction-summary.json", "cleanup.json"}
            and not (evidence_root / name).is_file()
        ]
        if missing_evidence:
            raise InstalledLlamaCppTransactionError(
                "successful installed proof is missing required evidence: "
                + ", ".join(missing_evidence)
            )
        summary["required_evidence_files"] = list(MINIMUM_EVIDENCE_FILENAMES)
        summary["semantic_generation_count"] = len(ledger.generation_entries())
        summary["input_count_logical_operations"] = len(ledger.input_operations())
        summary["input_count_endpoint_calls"] = len(ledger.input_entries())
        summary["phase"] = "evidence_recorded"
        summary["disposition"] = PHYSICAL_EVIDENCE_DISPOSITION
        summary["classification"] = PHYSICAL_EVIDENCE_DISPOSITION
        summary["product_quality_review"] = "not_run_by_harness"
        return_code = 0
    except Exception as exc:
        summary["disposition"] = PHYSICAL_INVALID_DISPOSITION
        summary["classification"] = PHYSICAL_INVALID_DISPOSITION
        summary["phase"] = summary.get("phase") or "failed"
        summary["failure"] = _bounded_error(exc)
        if ledger is not None:
            summary["semantic_generation_count"] = len(ledger.generation_entries())
            summary["input_count_logical_operations"] = len(ledger.input_operations())
            summary["input_count_endpoint_calls"] = len(ledger.input_entries())
        return_code = 2
    finally:
        cleanup = _cleanup(
            relay_process=relay_process,
            proxy=proxy,
            server_process=server_process,
            evidence_root=evidence_root,
        )
        _write_json(evidence_root / "cleanup.json", cleanup)
        summary["cleanup"] = cleanup
        if summary["disposition"] == PHYSICAL_EVIDENCE_DISPOSITION and (
            not cleanup["all_owned_processes_terminated"]
            or not cleanup["proxy_closed"]
            or cleanup["errors"]
        ):
            summary["disposition"] = PHYSICAL_INVALID_DISPOSITION
            summary["classification"] = PHYSICAL_INVALID_DISPOSITION
            summary["failure"] = {
                "type": "CleanupError",
                "message": "transaction-owned cleanup did not complete cleanly",
            }
            return_code = 2
        if ledger is not None:
            if not (evidence_root / "provider-request-ledger.json").exists():
                _write_json(evidence_root / "provider-request-ledger.json", ledger.provider_evidence())
            if not (evidence_root / "input-count-ledger.json").exists():
                _write_json(evidence_root / "input-count-ledger.json", ledger.input_evidence())
            if buffered is not None and not (evidence_root / "buffered-execution.json").exists():
                _write_json(
                    evidence_root / "buffered-execution.json",
                    _execution_evidence(
                        kind="buffered",
                        public_request=buffered,
                        ledger=ledger,
                        validation_state=EXECUTION_OBSERVATION_STATE,
                    ),
                )
            if streaming is not None and not (evidence_root / "streaming-execution.json").exists():
                _write_json(
                    evidence_root / "streaming-execution.json",
                    _execution_evidence(
                        kind="streaming",
                        public_request=streaming,
                        ledger=ledger,
                        validation_state=EXECUTION_OBSERVATION_STATE,
                    ),
                )
        if fixture is not None and not (evidence_root / "state-continuity-before-after.json").exists():
            _write_json(
                evidence_root / "state-continuity-before-after.json",
                {
                    "format_version": 1,
                    "fixture": fixture["evidence_identity"],
                    "continuity_runtime": fixture["continuity_runtime"],
                    "continuity_runtime_source": fixture["continuity_runtime_source"],
                    "snapshots": snapshots,
                    "product_quality": "not_declared_by_harness",
                },
            )
        summary["evidence_files"] = _evidence_file_receipts(evidence_root)
        _write_json(evidence_root / "transaction-summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return return_code


def _new_root(value: str | None, *, prefix: str) -> Path:
    if value:
        path = Path(value).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=False)
        return path
    return Path(tempfile.mkdtemp(prefix=prefix)).resolve()


def _bind_repository(*, repo_root: Path, evidence_root: Path) -> dict[str, Any]:
    _require_clean_checkout(repo_root)
    head, tree = _git_identity(repo_root)
    declarations = load_declarations(repo_root)
    derived_core = qualification_fingerprint(
        repo_root,
        declarations,
        roots=("crystallization", "runtime_configuration"),
    )
    expected_core = _expected_core(repo_root)
    if expected_core != derived_core:
        raise InstalledLlamaCppTransactionError(
            "expected and derived Core differ; installed-path transaction is blocked"
        )
    return {
        "format_version": 1,
        "owner": 2903,
        "parent": 1992,
        "target": TARGET_NAME,
        "evidence_root": str(evidence_root),
        "relaylm": {
            "head": head,
            "tree": tree,
            "core_expected": expected_core,
            "core_derived": derived_core,
            "expected_equals_derived": True,
            "post_core": expected_core,
            "core_unchanged": True,
        },
        "physical_execution": {
            "provider_request_count": 0,
            "live_input_token_request_count": 0,
            "llama_server_launch_count": 0,
            "relaylm_serve_launch_count": 0,
            "gpu_scientific_execution_count": 0,
            "semantic_generation_count": 0,
        },
    }


def _verify_repository_binding(
    *,
    repo_root: Path,
    binding: Mapping[str, Any],
) -> None:
    _require_clean_checkout(repo_root)
    head, tree = _git_identity(repo_root)
    relaylm = binding.get("relaylm")
    if not isinstance(relaylm, Mapping):
        raise InstalledLlamaCppTransactionError("repository binding is malformed")
    if head != relaylm.get("head") or tree != relaylm.get("tree"):
        raise InstalledLlamaCppTransactionError(
            "exact RelayLM checkout identity changed during installed proof"
        )
    declarations = load_declarations(repo_root)
    derived_core = qualification_fingerprint(
        repo_root,
        declarations,
        roots=("crystallization", "runtime_configuration"),
    )
    expected_core = _expected_core(repo_root)
    if expected_core != derived_core or expected_core != relaylm.get("core_expected"):
        raise InstalledLlamaCppTransactionError(
            "repository Core changed or expected/derived Core diverged"
        )


def _expected_core(repo_root: Path) -> str:
    path = repo_root / "evaluation/actual_model/qualifications/core-semantic-v1.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        value = payload["expected_fingerprint"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise InstalledLlamaCppTransactionError(
            "cannot read expected Core fingerprint"
        ) from exc
    if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise InstalledLlamaCppTransactionError("expected Core fingerprint is malformed")
    return value


def _require_clean_checkout(repo_root: Path) -> None:
    if not (repo_root / ".git").exists():
        raise InstalledLlamaCppTransactionError(f"not a git checkout: {repo_root}")
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0 or completed.stdout.strip():
        raise InstalledLlamaCppTransactionError(
            "installed-path proof requires a clean exact RelayLM checkout"
        )


def _git_identity(repo_root: Path) -> tuple[str, str]:
    values: list[str] = []
    for revision in ("HEAD", "HEAD^{tree}"):
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", revision],
            text=True,
            capture_output=True,
            check=False,
        )
        value = completed.stdout.strip()
        if completed.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", value):
            raise InstalledLlamaCppTransactionError(
                f"cannot determine exact RelayLM identity for {revision}"
            )
        values.append(value)
    return values[0], values[1]


def _resolve_target_path(repo_root: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    path = candidate if candidate.is_absolute() else repo_root / candidate
    path = path.resolve()
    try:
        path.relative_to(repo_root)
    except ValueError as exc:
        raise InstalledLlamaCppTransactionError(
            "actual-model target descriptor must be inside the exact checkout"
        ) from exc
    return path


def _load_artifact_target(path: Path) -> ActualModelArtifactTarget:
    target = load_actual_model_target(path)
    if not isinstance(target, ActualModelArtifactTarget):
        raise InstalledLlamaCppTransactionError(
            "installed llama.cpp target requires a frozen GGUF artifact descriptor"
        )
    return target


def _resolve_artifact_path(target: ActualModelArtifactTarget, value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return (Path.home() / "models" / "gguf" / target.artifact_filename).resolve()


def _source_package_version() -> str:
    try:
        from relaylm import __version__
    except ImportError as exc:
        raise InstalledLlamaCppTransactionError(
            "exact checkout source package cannot be imported for release identity"
        ) from exc
    if not isinstance(__version__, str) or not __version__.strip():
        raise InstalledLlamaCppTransactionError("source package version is empty")
    return __version__


def _build_exact_wheel(*, repo_root: Path, build_root: Path) -> Path:
    if importlib.util.find_spec("build") is None:
        raise InstalledLlamaCppTransactionError(
            "controlled build frontend 'build' is absent; refusing network installation"
        )
    build_root.mkdir(parents=True, exist_ok=False)
    command = [
        sys.executable,
        "-m",
        "build",
        "--wheel",
        "--no-isolation",
        "--outdir",
        str(build_root),
        str(repo_root),
    ]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise InstalledLlamaCppTransactionError(
            "exact wheel build failed: " + _bounded_text(completed.stderr or completed.stdout)
        )
    wheels = sorted(build_root.glob("relaylm-*.whl"))
    if len(wheels) != 1:
        raise InstalledLlamaCppTransactionError(
            f"exact wheel build produced {len(wheels)} RelayLM wheels; expected one"
        )
    return wheels[0].resolve()


def _install_exact_wheel(
    *,
    wheel_path: Path,
    package_version: str,
    transaction_root: Path,
    evidence_root: Path,
    repo_root: Path,
) -> dict[str, Any]:
    transaction_root.mkdir(parents=True, exist_ok=False)
    venv_root = transaction_root / "venv"
    home = transaction_root / "home"
    home.mkdir()
    dependency_overlay = _prepare_dependency_overlay(
        transaction_root / "controlled-dependencies"
    )
    completed = subprocess.run(
        [sys.executable, "-m", "venv", "--system-site-packages", str(venv_root)],
        cwd=evidence_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise InstalledLlamaCppTransactionError(
            "transaction venv creation failed: " + _bounded_text(completed.stderr)
        )
    python_path = _venv_binary(venv_root, "python")
    pip_path = [str(python_path), "-m", "pip"]
    environment = _installed_environment(
        home,
        dependency_overlay=Path(dependency_overlay["path"]),
    )
    before = _installed_import_identity(
        python_path=python_path,
        cwd=evidence_root,
        env=environment,
        allow_missing=True,
    )
    if before is not None:
        raise InstalledLlamaCppTransactionError(
            "fresh transaction venv already exposes RelayLM before wheel installation"
        )
    install = subprocess.run(
        [*pip_path, "install", "--no-index", "--no-deps", str(wheel_path)],
        cwd=evidence_root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if install.returncode != 0:
        raise InstalledLlamaCppTransactionError(
            "non-editable wheel installation failed without network: "
            + _bounded_text(install.stderr or install.stdout)
        )
    check = subprocess.run(
        [*pip_path, "check"],
        cwd=evidence_root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if check.returncode != 0:
        raise InstalledLlamaCppTransactionError(
            "installed transaction dependency check failed: "
            + _bounded_text(check.stdout or check.stderr)
        )
    identity = _installed_import_identity(
        python_path=python_path,
        cwd=evidence_root,
        env=environment,
        allow_missing=False,
    )
    assert identity is not None
    module_path = Path(identity["module_path"]).resolve()
    if module_path == repo_root or repo_root in module_path.parents:
        raise InstalledLlamaCppTransactionError(
            "installed RelayLM import resolves to the source checkout"
        )
    if identity["version"] != package_version:
        raise InstalledLlamaCppTransactionError(
            "installed RelayLM version does not match exact source release identity"
        )
    if identity["editable"]:
        raise InstalledLlamaCppTransactionError(
            "transaction RelayLM installation is editable"
        )
    return {
        "format_version": 1,
        "method": "wheel-from-exact-checkout-to-fresh-venv",
        "wheel": {
            "path": str(wheel_path),
            "sha256": f"sha256:{_sha256_file(wheel_path)}",
        },
        "source_checkout": {
            "head": _git_identity(repo_root)[0],
            "tree": _git_identity(repo_root)[1],
        },
        "package_version": package_version,
        "transaction_root": str(transaction_root),
        "venv_root": str(venv_root),
        "console_path": str(_venv_binary(venv_root, "relaylm")),
        "python_path": str(python_path),
        "module_path": identity["module_path"],
        "import_identity": identity,
        "non_editable": True,
        "network_install": False,
        "source_import_leakage_rejected": True,
        "controlled_dependency_overlay": dependency_overlay,
    }


def _venv_binary(venv_root: Path, name: str) -> Path:
    relative = Path("Scripts" if os.name == "nt" else "bin")
    suffix = ".exe" if os.name == "nt" and name in {"python", "relaylm"} else ""
    path = venv_root / relative / f"{name}{suffix}"
    if not path.is_file():
        raise InstalledLlamaCppTransactionError(f"transaction venv binary is absent: {path}")
    # Preserve the venv launcher symlink. Resolving ``bin/python`` to the base
    # interpreter would make pip treat the transaction as a system install and
    # bypass the fresh environment boundary.
    return path.absolute()


def _prepare_dependency_overlay(destination: Path) -> dict[str, Any]:
    source = Path(sysconfig.get_paths()["purelib"]).resolve()
    if not source.is_dir():
        raise InstalledLlamaCppTransactionError(
            f"persistent Python dependency source is unavailable: {source}"
        )
    destination.mkdir(parents=True, exist_ok=False)
    copied_files = 0
    excluded: list[str] = []
    for item in sorted(source.iterdir(), key=lambda path: path.name):
        normalized = item.name.lower()
        if (
            normalized == "relaylm"
            or normalized.startswith("relaylm-")
            or normalized.startswith("relaylm_")
            or normalized.startswith("__editable__.relaylm")
            or item.suffix == ".pth"
        ):
            excluded.append(item.name)
            continue
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, symlinks=True, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
        if target.is_file():
            copied_files += 1
        else:
            copied_files += sum(1 for path in target.rglob("*") if path.is_file())
    if not copied_files:
        raise InstalledLlamaCppTransactionError(
            "controlled dependency overlay is empty"
        )
    return {
        "path": str(destination.resolve()),
        "source": str(source),
        "sha256": f"sha256:{_directory_sha256(destination)}",
        "copied_file_count": copied_files,
        "excluded_relaylm_entries": excluded,
        "network": False,
    }


def _installed_environment(
    home: Path,
    *,
    dependency_overlay: Path | None = None,
) -> dict[str, str]:
    environment = os.environ.copy()
    for name in (
        "PYTHONPATH",
        "PYTHONHOME",
        "RELAYLM_CONFIG",
        "RELAYLM_PROVIDER_BASE_URL",
        "RELAYLM_PROVIDER_MODEL",
        "RELAYLM_PROFILE_ROOT",
        "RELAYLM_PROFILE_NAME",
    ):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["HOME"] = str(home)
    if dependency_overlay is not None:
        environment["PYTHONPATH"] = str(dependency_overlay.resolve())
    return environment


def _installed_import_identity(
    *,
    python_path: Path,
    cwd: Path,
    env: Mapping[str, str],
    allow_missing: bool,
) -> dict[str, Any] | None:
    script = """
import importlib.metadata as metadata
import json
import pathlib
import sys

try:
    import relaylm
except ModuleNotFoundError:
    print(json.dumps({"missing": True}, sort_keys=True))
    raise SystemExit(0)

distribution = metadata.distribution("relaylm")
try:
    direct_url = distribution.read_text("direct_url.json")
except Exception:
    direct_url = None

print(json.dumps({
    "missing": False,
    "version": distribution.version,
    "module_path": str(pathlib.Path(relaylm.__file__).resolve()),
    "prefix": str(pathlib.Path(sys.prefix).resolve()),
    "editable": bool(direct_url and '\"editable\": true' in direct_url),
}, sort_keys=True))
"""
    completed = subprocess.run(
        [str(python_path), "-c", script],
        cwd=cwd,
        env=dict(env),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise InstalledLlamaCppTransactionError(
            "cannot inspect installed RelayLM identity: "
            + _bounded_text(completed.stderr or completed.stdout)
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise InstalledLlamaCppTransactionError(
            "installed RelayLM identity is not JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise InstalledLlamaCppTransactionError("installed RelayLM identity is malformed")
    if payload.get("missing"):
        if allow_missing:
            return None
        raise InstalledLlamaCppTransactionError("installed RelayLM distribution is absent")
    return payload


def _require_llama_port(port: int) -> None:
    if port != DEFAULT_LLAMACPP_PORT:
        raise InstalledLlamaCppTransactionError(
            f"shared llama.cpp laboratory port must be {DEFAULT_LLAMACPP_PORT}"
        )


def _probe_server(*, origin: str, expected_slots: int) -> dict[str, Any]:
    health = _get_json(f"{origin}/health")
    models = _get_json(f"{origin}/v1/models")
    props = _get_json(f"{origin}/props")
    slots = _get_json(f"{origin}/slots")
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise InstalledLlamaCppTransactionError("llama-server health is not ready")
    model_ids = _model_ids(models)
    if len(model_ids) != 1:
        raise InstalledLlamaCppTransactionError(
            "llama-server must expose exactly one physical request model"
        )
    if not isinstance(props, dict) or not isinstance(slots, list):
        raise InstalledLlamaCppTransactionError(
            "llama-server /props and /slots responses are malformed"
        )
    if len(slots) != expected_slots:
        raise InstalledLlamaCppTransactionError(
            f"llama-server must expose exactly {expected_slots} slot"
        )
    return {
        "health": health,
        "models": models,
        "props": props,
        "slots": slots,
        "request_model": model_ids[0],
        "management_endpoint_calls": 4,
    }


def _attest_runtime(
    *,
    probe: Mapping[str, Any],
    revision: str,
    version: str,
    build_number: int,
    request_model: str,
    artifact_path: Path,
    verification: Any,
    target: ActualModelArtifactTarget,
) -> tuple[LlamaCppRuntimeIdentity, LlamaCppCapabilityAttestation]:
    props = probe["props"]
    slots = probe["slots"]
    if not isinstance(props, Mapping) or not isinstance(slots, list):
        raise InstalledLlamaCppTransactionError("runtime attestation probe payload is malformed")
    build_info = props.get("build_info")
    if not isinstance(build_info, str) or str(build_number) not in build_info:
        raise InstalledLlamaCppTransactionError(
            "llama-server --version build does not match /props build_info"
        )
    observed = attest_llama_cpp_runtime(
        props=props,
        slots=slots,
        upstream_revision=revision,
        expected_build_info=build_info,
        expected_model_alias=request_model,
        expected_model_path=str(artifact_path),
        artifact_sha256=verification.artifact_sha256,
        context_shift_enabled=False,
    )
    runtime_identity = LlamaCppRuntimeIdentity(
        upstream_revision=observed.upstream_revision,
        build_info=observed.build_info,
        model_alias=observed.model_alias,
        model_path=observed.model_path,
        model_ftype=observed.model_ftype,
        artifact_sha256=observed.artifact_sha256,
        chat_template_sha256=observed.chat_template_sha256,
        context_limit=observed.context_limit,
        total_slots=observed.total_slots,
        context_shift_enabled=observed.context_shift_enabled,
    )
    capability = build_llama_cpp_capability(
        upstream_revision=runtime_identity.upstream_revision,
        build_info=runtime_identity.build_info,
        model_alias=runtime_identity.model_alias,
        model_path=runtime_identity.model_path,
        model_ftype=runtime_identity.model_ftype,
        artifact_sha256=runtime_identity.artifact_sha256,
        chat_template_sha256=runtime_identity.chat_template_sha256,
        context_limit=runtime_identity.context_limit,
        total_slots=runtime_identity.total_slots,
        context_shift_enabled=False,
        reasoning_effort_none_supported=True,
        native_structured_output_supported=True,
        streaming_supported=True,
        decoding_controls=frozenset({"temperature", "top_p", "max_output_tokens"}),
        cache_policy=LLAMA_CPP_CACHE_POLICY_DISABLED,
    )
    if target.model_family.strip() == "":
        raise InstalledLlamaCppTransactionError("target model family is empty")
    return runtime_identity, capability


def _runtime_attestation_evidence(
    *,
    probe: Mapping[str, Any],
    revision: str,
    version: str,
    build_number: int,
    request_model: str,
    artifact_path: Path,
    verification: Any,
    target: ActualModelArtifactTarget,
    runtime_identity: LlamaCppRuntimeIdentity,
    capability: LlamaCppCapabilityAttestation,
) -> dict[str, Any]:
    schema = extraction_wire_schema(ExtractionProjectionMode.PRODUCTION)
    schema_name = extraction_schema_name(ExtractionProjectionMode.PRODUCTION)
    return {
        "format_version": 1,
        "observation_kind": "non_generating_live_runtime_attestation",
        "management_endpoints": [
            {"method": "GET", "path": "/health", "purpose": "readiness"},
            {"method": "GET", "path": "/v1/models", "purpose": "request_model"},
            {"method": "GET", "path": "/props", "purpose": "runtime_identity"},
            {"method": "GET", "path": "/slots", "purpose": "slot_identity"},
        ],
        "management_endpoint_call_count": probe["management_endpoint_calls"],
        "observations": {
            "health": probe["health"],
            "models": probe["models"],
            "props": probe["props"],
            "slots": probe["slots"],
        },
        "llama_cpp": {
            "upstream_revision": revision,
            "server_version": version,
            "build_number": build_number,
            "build_info": runtime_identity.build_info,
            "request_model": request_model,
            "gguf": {
                "target": target.to_mapping(),
                "path": str(artifact_path),
                "verification": verification.to_mapping(),
            },
            "model_ftype": runtime_identity.model_ftype,
            "chat_template_sha256": f"sha256:{runtime_identity.chat_template_sha256}",
            "tokenizer_identity": {
                "upstream_snapshot_sha256": f"sha256:{target.upstream_tokenizer_sha256}",
                "serving_embedded_gguf": f"sha256:{runtime_identity.artifact_sha256}",
            },
            "effective_context": runtime_identity.context_limit,
            "slots": runtime_identity.total_slots,
            "context_shift": "disabled",
        },
        "release_capability_contract": capability.to_mapping(),
        "reasoning": {
            "wire_condition": "reasoning_effort=none",
            "supported": capability.reasoning_effort_none_supported,
            "observation": "exercised by ordinary installed requests; no probe generation",
        },
        "structured_output": {
            "pass1": "ordinary",
            "pass2": "native",
            "schema_name": schema_name,
            "schema_sha256": f"sha256:{_sha256_json(schema)}",
        },
        "streaming": {
            "supported": capability.streaming_supported,
            "observation": "exercised by one ordinary installed streaming request",
        },
        "cache_policy": LLAMA_CPP_CACHE_POLICY_DISABLED,
        "product_quality": "not_declared_by_harness",
    }


def _materialize_fixture(
    *,
    repo_root: Path,
    evidence_root: Path,
    scenario_id: str,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    evidence_root = evidence_root.resolve()
    authority_path = repo_root / CURRENT_STAGE_R_AUTHORITY_PATH
    authority = _read_json_object(authority_path)
    scenario_relative = authority.get("scenario_set_path")
    scenario_revision = authority.get("scenario_set_revision")
    if not isinstance(scenario_relative, str) or not isinstance(scenario_revision, str):
        raise InstalledLlamaCppTransactionError("current Stage-R scenario authority is malformed")
    scenario_path = (repo_root / scenario_relative).resolve()
    try:
        scenario_path.relative_to(repo_root)
    except ValueError as exc:
        raise InstalledLlamaCppTransactionError(
            "current Stage-R scenario-set path must remain inside the exact checkout"
        ) from exc
    scenario_set = load_actual_model_scenario_set(scenario_path)
    if scenario_set.revision != scenario_revision:
        raise InstalledLlamaCppTransactionError(
            "current Stage-R scenario-set revision does not match authority"
        )
    try:
        selected = scenario_set.scenario(scenario_id)
    except KeyError as exc:
        raise InstalledLlamaCppTransactionError(
            f"canonical scenario is unavailable: {scenario_id}"
        ) from exc
    if not selected.scenario.turns or not isinstance(selected.scenario.turns[0], str):
        raise InstalledLlamaCppTransactionError("canonical scenario has no first turn")
    source_fixture = (repo_root / CANONICAL_FIXTURE_PATH).resolve()
    if not source_fixture.is_dir():
        raise InstalledLlamaCppTransactionError("canonical foundation fixture is absent")
    buffered_root = evidence_root / "fixtures" / "buffered"
    streaming_root = evidence_root / "fixtures" / "streaming"
    buffered_root.parent.mkdir(parents=True, exist_ok=False)
    shutil.copytree(source_fixture, buffered_root)
    shutil.copytree(source_fixture, streaming_root)
    fixture = {
        "format_version": 1,
        "scenario_id": scenario_id,
        "turn_index": 1,
        "prompt": selected.scenario.turns[0],
        "evidence_identity": {
            "scenario_set_path": scenario_relative,
            "scenario_set_revision": scenario_revision,
            "scenario_id": scenario_id,
            "turn_index": 1,
            "prompt_sha256": f"sha256:{hashlib.sha256(selected.scenario.turns[0].encode('utf-8')).hexdigest()}",
            "character_fixture_path": str(CANONICAL_FIXTURE_PATH),
            "character_fixture_sha256": f"sha256:{_directory_sha256(source_fixture)}",
        },
        "profile_roots": {
            "installed-buffered": str(buffered_root),
            "installed-streaming": str(streaming_root),
        },
        "continuity_runtime": {"max_items": 8, "lifetime_revisions": 4},
        "continuity_runtime_source": "current Stage-R semantic authority",
    }
    return fixture


def _write_runtime_config(
    *,
    config_path: Path,
    fixture: Mapping[str, Any],
    proxy_base_url: str,
    relay_port: int,
    request_model: str,
    artifact_path: Path,
    runtime_identity: LlamaCppRuntimeIdentity,
    capability: LlamaCppCapabilityAttestation,
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "format_version": 1,
        "profiles": [
            {"name": "installed-buffered", "root": fixture["profile_roots"]["installed-buffered"]},
            {"name": "installed-streaming", "root": fixture["profile_roots"]["installed-streaming"]},
        ],
        "provider": {
            "adapter": "openai_compatible",
            "backend": "llama_cpp",
            "base_url": proxy_base_url,
            "model": request_model,
            "llama_cpp": {
                "upstream_revision": runtime_identity.upstream_revision,
                "build_info": runtime_identity.build_info,
                "model_alias": runtime_identity.model_alias,
                "model_path": str(artifact_path),
                "model_ftype": runtime_identity.model_ftype,
                "artifact_sha256": runtime_identity.artifact_sha256,
                "chat_template_sha256": runtime_identity.chat_template_sha256,
                "context_limit": runtime_identity.context_limit,
                "total_slots": runtime_identity.total_slots,
                "context_shift_enabled": False,
                "reasoning_effort_none_supported": capability.reasoning_effort_none_supported,
                "native_structured_output_supported": capability.native_structured_output_supported,
                "streaming_supported": capability.streaming_supported,
                "decoding_controls": sorted(capability.decoding_controls),
                "cache_policy": LLAMA_CPP_CACHE_POLICY_DISABLED,
            },
        },
        "server": {"host": "127.0.0.1", "port": relay_port},
        "runtime": {
            "cognition": {
                "mode": "two_pass",
                "pass1": {
                    "reasoning_mode": "off",
                    "temperature": 0,
                    "top_p": 1,
                    "max_output_tokens": PASS2_OUTPUT_TOKENS,
                },
                "pass2": {
                    "reasoning_mode": "off",
                    "temperature": 0,
                    "top_p": 1,
                    "max_output_tokens": PASS2_OUTPUT_TOKENS,
                    "structured_output_mode": "native",
                },
            },
            "continuity": fixture["continuity_runtime"],
            "cognitive_budget": {
                "total": {
                    "model_context_window": runtime_identity.context_limit,
                    "reserved_output_tokens": PASS2_OUTPUT_TOKENS,
                },
                "policy": {
                    "initial_plan": {
                        "canonical_state": {"max_items": 8, "floor_items": 2},
                        "working_context": {
                            "max_items": 4,
                            "floor_items": 1,
                            "max_chars": 2000,
                            "floor_chars": 500,
                        },
                        "retrieved_memory": {
                            "max_items": 4,
                            "floor_items": 0,
                            "max_chars": 1600,
                            "floor_chars": 0,
                        },
                        "event_evidence": {
                            "max_items": 4,
                            "floor_items": 0,
                            "max_chars": 1600,
                            "floor_chars": 0,
                        },
                    },
                    "steps": [],
                },
                "token_counter": {
                    "capability": LLAMA_CPP_CHAT_COUNTER_CAPABILITY,
                    "mode": "exact",
                },
            },
        },
    }
    config_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return config


def _run_installed_doctor(
    *,
    installed: Mapping[str, Any],
    config_path: Path,
    cwd: Path,
) -> dict[str, Any]:
    command = [installed["console_path"], "doctor", "--config", str(config_path), "--json"]
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=_installed_environment(
            Path(installed["transaction_root"]) / "home",
            dependency_overlay=Path(installed["controlled_dependency_overlay"]["path"]),
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise InstalledLlamaCppTransactionError(
            "installed relaylm doctor failed: "
            + _bounded_text(completed.stderr or completed.stdout)
        )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise InstalledLlamaCppTransactionError("installed doctor did not emit JSON") from exc
    if not isinstance(report, dict) or report.get("status") != "ok":
        raise InstalledLlamaCppTransactionError("installed doctor did not report status=ok")
    capabilities = report.get("provider_capabilities")
    if not isinstance(capabilities, dict) or capabilities.get("backend") != "llama_cpp":
        raise InstalledLlamaCppTransactionError(
            "installed doctor did not assemble the production llama_cpp backend"
        )
    return {
        "format_version": 1,
        "non_generative": True,
        "provider_contact_count": 0,
        "command": _shell_join(command),
        "exit_code": completed.returncode,
        "report": report,
        "stdout_sha256": f"sha256:{hashlib.sha256(completed.stdout.encode('utf-8')).hexdigest()}",
        "stderr_sha256": f"sha256:{hashlib.sha256(completed.stderr.encode('utf-8')).hexdigest()}",
    }


def _start_installed_serve(
    *,
    installed: Mapping[str, Any],
    config_path: Path,
    cwd: Path,
    log_path: Path,
) -> subprocess.Popen[str]:
    command = [installed["console_path"], "serve", "--config", str(config_path)]
    environment = _installed_environment(
        Path(installed["transaction_root"]) / "home",
        dependency_overlay=Path(installed["controlled_dependency_overlay"]["path"]),
    )
    with log_path.open("a", encoding="utf-8") as log:
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError as exc:
            raise InstalledLlamaCppTransactionError(
                "installed relaylm serve could not start"
            ) from exc
    return process


def _resolve_relay_port(requested: int) -> int:
    if requested == 0:
        return _find_free_port()
    if requested < 1 or requested > 65535:
        raise InstalledLlamaCppTransactionError("RelayLM server port is invalid")
    if not _port_is_free("127.0.0.1", requested):
        raise InstalledLlamaCppTransactionError(
            f"RelayLM server port is occupied: 127.0.0.1:{requested}"
        )
    return requested


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_http_health(process: subprocess.Popen[str], origin: str) -> None:
    deadline = time.monotonic() + READINESS_TIMEOUT_SECONDS
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise InstalledLlamaCppTransactionError(
                f"installed relaylm serve exited before readiness: {process.returncode}"
            )
        try:
            health = _get_json(f"{origin}/health")
            if isinstance(health, dict) and health.get("status") == "ok":
                return
        except Exception as exc:
            last_error = exc
        time.sleep(READINESS_POLL_SECONDS)
    detail = f": {last_error}" if last_error else ""
    raise InstalledLlamaCppTransactionError(
        "installed relaylm serve did not become ready" + detail
    )


def _run_public_buffered(*, relay_origin: str, prompt: str) -> dict[str, Any]:
    request = {
        "model": "installed-buffered",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, trust_env=False) as client:
            response = client.post(f"{relay_origin}/v1/chat/completions", json=request)
    except httpx.HTTPError as exc:
        raise InstalledLlamaCppTransactionError("buffered public request failed") from exc
    if response.status_code != 200:
        raise InstalledLlamaCppTransactionError(
            f"buffered public request returned HTTP {response.status_code}"
        )
    return _public_response_evidence(kind="buffered", request=request, body=response.content)


def _run_public_streaming(*, relay_origin: str, prompt: str) -> dict[str, Any]:
    request = {
        "model": "installed-streaming",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, trust_env=False) as client:
            with client.stream(
                "POST",
                f"{relay_origin}/v1/chat/completions",
                json=request,
            ) as response:
                body = response.read()
                status_code = response.status_code
    except httpx.HTTPError as exc:
        raise InstalledLlamaCppTransactionError("streaming public request failed") from exc
    if status_code != 200:
        raise InstalledLlamaCppTransactionError(
            f"streaming public request returned HTTP {status_code}"
        )
    return _public_response_evidence(kind="streaming", request=request, body=body)


def _public_response_evidence(*, kind: str, request: Mapping[str, Any], body: bytes) -> dict[str, Any]:
    if not body:
        raise InstalledLlamaCppTransactionError(f"{kind} public response is empty")
    return {
        "format_version": 1,
        "kind": kind,
        "request": _public_request_evidence(request),
        "http_status": 200,
        "response_sha256": f"sha256:{hashlib.sha256(body).hexdigest()}",
        "response_bytes": len(body),
        "bounded_response_excerpt": _bounded_text(
            body.decode("utf-8", errors="replace"), MAX_RESPONSE_EXCERPT
        ),
        "response_first": True,
        "pass2": "retained at model-facing proxy and validated separately",
    }


def _public_request_evidence(request: Mapping[str, Any]) -> dict[str, Any]:
    messages = request.get("messages")
    message_evidence = []
    if isinstance(messages, list):
        for item in messages:
            if isinstance(item, Mapping) and isinstance(item.get("content"), str):
                content = item["content"]
                message_evidence.append(
                    {
                        "role": item.get("role"),
                        "content_length": len(content),
                        "content_sha256": f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}",
                    }
                )
    return {
        "model": request.get("model"),
        "stream": request.get("stream"),
        "messages": message_evidence,
    }


def _wait_generation_batch(ledger: "RequestLedger", *, expected_count: int) -> None:
    deadline = time.monotonic() + REQUEST_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if ledger.rejections():
            raise RequestLedgerError(ledger.rejections()[0]["reason"])
        entries = ledger.generation_entries()
        if len(entries) > expected_count:
            raise RequestLedgerError("semantic generation count exceeded bounded batch")
        if len(entries) == expected_count and all(
            entry.get("response", {}).get("completed") is True for entry in entries
        ):
            if any(entry.get("response", {}).get("status") != 200 for entry in entries):
                raise RequestLedgerError("ordinary generation returned a non-success status")
            return
        time.sleep(0.05)
    raise RequestLedgerError(
        f"ordinary generation batch did not complete within {REQUEST_TIMEOUT_SECONDS:g}s"
    )


def _validate_successful_ledger(ledger: "RequestLedger") -> None:
    calls = ledger.calls()
    generations = ledger.generation_entries()
    if len(generations) != SEMANTIC_GENERATION_CEILING:
        raise RequestLedgerError("installed proof did not produce exactly four ordinary generations")
    if tuple(entry["phase"] for entry in generations) != CANONICAL_GENERATION_PHASES:
        raise RequestLedgerError("ordinary generation phase sequence is not canonical")
    if ledger.rejections():
        raise RequestLedgerError("model-facing proxy rejected a request")
    if ledger.pending_input_operation() is not None:
        raise RequestLedgerError("input-token ledger ended with an unmatched full count")
    operations = ledger.input_operations()
    inputs = ledger.input_entries()
    if len(inputs) != EXPECTED_INPUT_ENDPOINT_CALL_COUNT or len(operations) != EXPECTED_LOGICAL_OPERATION_COUNT:
        raise RequestLedgerError(
            "exact counter must retain six logical operations and twelve endpoint calls"
        )
    expected_operation_metadata = tuple(
        (
            spec.logical_operation_index,
            spec.generation_index,
            spec.generation_phase,
            spec.budget_role,
            spec.endpoint_calls,
        )
        for spec in CANONICAL_LOGICAL_OPERATION_SPECS
    )
    observed_operation_metadata = tuple(
        (
            operation.get("logical_operation_index"),
            operation.get("generation_index"),
            operation.get("generation_phase"),
            operation.get("budget_role"),
            operation.get("endpoint_calls"),
        )
        for operation in operations
    )
    if observed_operation_metadata != expected_operation_metadata:
        raise RequestLedgerError(
            "input-token logical operation role/order is not canonical"
        )
    calls_by_index = {call["call_index"]: call for call in calls}
    for operation in operations:
        full = calls_by_index.get(operation.get("full_call_index"))
        framing = calls_by_index.get(operation.get("framing_call_index"))
        if (
            full is None
            or framing is None
            or full.get("framing_role") != COUNTER_ENDPOINT_ROLES[0]
            or framing.get("framing_role") != COUNTER_ENDPOINT_ROLES[1]
            or framing.get("call_index") != full.get("call_index", 0) + 1
        ):
            raise RequestLedgerError(
                "exact counter logical operation is not a complete full/framing pair"
            )
    expected_sequence = list(CANONICAL_PROVIDER_SEQUENCE)
    observed_sequence = [
        (call["kind"], call.get("generation_index"), call.get("framing_role"))
        for call in calls
    ]
    if observed_sequence != expected_sequence:
        raise RequestLedgerError(
            "provider request ledger is not full-count/framing/generation ordered"
        )
    for entry in generations:
        response = entry["response"]
        if response.get("status") != 200 or not response.get("completed"):
            raise RequestLedgerError("ordinary generation did not complete successfully")
        controls = entry["controls"]
        if controls.get("cache_prompt") is not False:
            raise RequestLedgerError("generation omitted cache_prompt=false")
        if controls.get("reasoning_effort") != "none":
            raise RequestLedgerError("generation omitted reasoning_effort=none")
        expected_stream = entry["phase"] == "streaming_pass1"
        if controls.get("stream") is not expected_stream:
            raise RequestLedgerError("generation streaming control is not canonical")
        is_pass2 = entry["phase"].endswith("pass2")
        response_format = controls.get("response_format")
        if is_pass2:
            if not isinstance(response_format, dict) or response_format.get("type") != "json_schema":
                raise RequestLedgerError("Pass 2 did not carry native structured output")
            if response_format.get("strict") is not True:
                raise RequestLedgerError("Pass 2 structured output was not strict")
        elif response_format is not None:
            raise RequestLedgerError("Pass 1 carried structured output")
    for entry in inputs:
        response = entry["response"]
        if (
            response.get("status") != 200
            or not response.get("completed")
            or "input_tokens" not in response
        ):
            raise RequestLedgerError("exact count did not complete successfully")
        controls = entry["controls"]
        if controls.get("cache_prompt") is not False:
            raise RequestLedgerError("exact count omitted cache_prompt=false")
        if controls.get("reasoning_effort") != "none":
            raise RequestLedgerError("exact count omitted reasoning_effort=none")
    if ledger.retry_count != 0 or ledger.replay_count != 0 or ledger.reseed_count != 0:
        raise RequestLedgerError("harness request ledger recorded an automatic retry/replay/reseed")


def _execution_evidence(
    *,
    kind: str,
    public_request: Mapping[str, Any],
    ledger: "RequestLedger",
    validation_state: str,
) -> dict[str, Any]:
    prefix = f"{kind}_"
    entries = [
        entry
        for entry in ledger.generation_entries()
        if entry["phase"].startswith(prefix)
    ]
    return {
        "format_version": 1,
        "execution": kind,
        "validation_state": validation_state,
        "semantic_generation_ceiling": CANONICAL_GENERATION_COUNTS_BY_EXECUTION[kind],
        "semantic_generation_count": len(entries),
        "semantic_retry_count": 0,
        "replay_count": 0,
        "reseed_count": 0,
        "fallback_count": 0,
        "repair_generation_count": 0,
        "public_response": dict(public_request),
        "provider_generations": [
            {
                "phase": entry["phase"],
                "generation_index": entry["generation_index"],
                "request_body_sha256": entry["body_sha256"],
                "controls": entry["controls"],
                "response": entry["response"],
            }
            for entry in entries
        ],
        "pass2_review_inputs": [
            {
                "phase": entry["phase"],
                "raw_response": entry["response"].get("raw_response"),
                "normalized_response": entry["response"].get("normalized_response"),
                "accepted": "deferred_to_zero_generation_review",
            }
            for entry in entries
            if entry["phase"].endswith("pass2")
        ],
        "product_quality": "not_declared_by_harness",
    }


class RequestLedger:
    """Thread-safe sanitized ledger at the installed provider boundary."""

    def __init__(self, *, expected_model: str) -> None:
        self.expected_model = expected_model
        self._lock = RLock()
        self._calls: list[dict[str, Any]] = []
        self._input_operations: list[dict[str, Any]] = []
        self._pending_full: dict[str, Any] | None = None
        self._rejections: list[dict[str, Any]] = []
        self.retry_count = 0
        self.replay_count = 0
        self.reseed_count = 0

    def begin(self, *, path: str, body: bytes) -> dict[str, Any]:
        payload = _parse_json_object(body, "provider request")
        controls = _wire_controls(payload)
        with self._lock:
            if controls.get("model") != self.expected_model:
                raise RequestLedgerError(
                    "provider request model does not match the attested physical model"
                )
            if path == "/v1/chat/completions/input_tokens":
                return self._begin_input(payload, controls, body)
            if path == "/v1/chat/completions":
                return self._begin_generation(payload, controls, body)
        raise RequestLedgerError(f"unsupported proxy path: {path}")

    def reject(self, *, path: str, body: bytes, reason: str) -> None:
        with self._lock:
            self._rejections.append(
                {
                    "path": path,
                    "body_sha256": f"sha256:{hashlib.sha256(body).hexdigest()}",
                    "reason": _bounded_text(reason),
                }
            )

    def complete(
        self,
        entry: dict[str, Any],
        *,
        status: int,
        body: bytes,
        streaming: bool,
        body_truncated: bool = False,
        body_sha256: str | None = None,
    ) -> None:
        with self._lock:
            entry["response"] = {
                "status": status,
                "completed": True,
                "streaming": streaming,
                "body_sha256": body_sha256
                or f"sha256:{hashlib.sha256(body).hexdigest()}",
                "body_bytes": len(body),
                "body_truncated_for_parser": body_truncated,
            }
            if entry["kind"] == "input_token_count":
                if status == 200:
                    payload = _parse_json_object(body, "input-token response")
                    count = payload.get("input_tokens")
                    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                        raise RequestLedgerError("input-token response count is invalid")
                    entry["response"]["input_tokens"] = count
                else:
                    entry["response"]["bounded_excerpt"] = _bounded_text(
                        body.decode("utf-8", errors="replace")
                    )
            else:
                entry["response"].update(_response_wire_evidence(body, streaming=streaming))

    def fail(self, entry: dict[str, Any], *, reason: str) -> None:
        with self._lock:
            entry["response"] = {
                "status": None,
                "completed": True,
                "streaming": False,
                "error": _bounded_text(reason),
            }

    def _begin_input(
        self,
        payload: Mapping[str, Any],
        controls: dict[str, Any],
        body: bytes,
    ) -> dict[str, Any]:
        framing = _is_framing_payload(payload)
        if framing:
            if self._pending_full is None:
                raise RequestLedgerError("framing count arrived without a full count")
            operation = self._pending_full
            operation_index = operation["logical_operation_index"] - 1
            if not 0 <= operation_index < len(CANONICAL_LOGICAL_OPERATION_SPECS):
                raise RequestLedgerError("input-token ledger has an invalid logical operation")
            spec = CANONICAL_LOGICAL_OPERATION_SPECS[operation_index]
            self._require_upcoming_generation(spec)
            self._pending_full = None
            role = COUNTER_ENDPOINT_ROLES[1]
        else:
            if self._pending_full is not None:
                raise RequestLedgerError("full count arrived before prior framing count")
            operation_index = len(self._input_operations)
            if operation_index >= len(CANONICAL_LOGICAL_OPERATION_SPECS):
                raise RequestLedgerError("input-token ledger has an extra logical operation")
            spec = CANONICAL_LOGICAL_OPERATION_SPECS[operation_index]
            self._require_upcoming_generation(spec)
            call_index = len(self._calls) + 1
            operation = {
                "logical_operation_index": spec.logical_operation_index,
                "upcoming_generation_index": spec.generation_index,
                "generation_index": spec.generation_index,
                "generation_phase": spec.generation_phase,
                "budget_role": spec.budget_role,
                "endpoint_calls": spec.endpoint_calls,
                "endpoint_roles": list(COUNTER_ENDPOINT_ROLES),
                "full_call_index": call_index,
            }
            self._input_operations.append(operation)
            self._pending_full = operation
            role = COUNTER_ENDPOINT_ROLES[0]
        call_index = len(self._calls) + 1
        if role == COUNTER_ENDPOINT_ROLES[1]:
            operation["framing_call_index"] = call_index
        call = {
            "call_index": call_index,
            "kind": "input_token_count",
            "logical_operation_index": operation["logical_operation_index"],
            "generation_index": operation["generation_index"],
            "upcoming_generation_index": operation["upcoming_generation_index"],
            "generation_phase": operation["generation_phase"],
            "budget_role": operation["budget_role"],
            "endpoint_calls": operation["endpoint_calls"],
            "framing_role": role,
            "path": "/v1/chat/completions/input_tokens",
            "body_sha256": f"sha256:{hashlib.sha256(body).hexdigest()}",
            "body_bytes": len(body),
            "controls": controls,
            "response": {"completed": False},
        }
        self._calls.append(call)
        return call

    def _begin_generation(
        self,
        payload: Mapping[str, Any],
        controls: dict[str, Any],
        body: bytes,
    ) -> dict[str, Any]:
        generation_index = len(self.generation_entries()) + 1
        if generation_index > SEMANTIC_GENERATION_CEILING:
            raise RequestLedgerError("semantic generation ceiling exceeded")
        if self._pending_full is not None:
            raise RequestLedgerError(
                "generation emitted before the pending full count was framed"
            )
        required_operation_count = sum(
            spec.generation_index <= generation_index
            for spec in CANONICAL_LOGICAL_OPERATION_SPECS
        )
        observed_operation_count = len(self._input_operations)
        if observed_operation_count != required_operation_count:
            if observed_operation_count < required_operation_count:
                raise RequestLedgerError(
                    "generation emitted before required count topology complete"
                )
            raise RequestLedgerError(
                "input-token ledger has an extra logical operation before generation"
            )
        observed_operation_metadata = tuple(
            (
                operation.get("logical_operation_index"),
                operation.get("generation_index"),
                operation.get("generation_phase"),
                operation.get("budget_role"),
                operation.get("endpoint_calls"),
            )
            for operation in self._input_operations
        )
        expected_operation_metadata = tuple(
            (
                spec.logical_operation_index,
                spec.generation_index,
                spec.generation_phase,
                spec.budget_role,
                spec.endpoint_calls,
            )
            for spec in CANONICAL_LOGICAL_OPERATION_SPECS[:observed_operation_count]
        )
        if observed_operation_metadata != expected_operation_metadata:
            raise RequestLedgerError(
                "input-token logical operation role/order is not canonical"
            )
        phase = CANONICAL_GENERATION_PHASES[generation_index - 1]
        call = {
            "call_index": len(self._calls) + 1,
            "kind": "generation",
            "generation_index": generation_index,
            "phase": phase,
            "generation_phase": phase,
            "path": "/v1/chat/completions",
            "body_sha256": f"sha256:{hashlib.sha256(body).hexdigest()}",
            "body_bytes": len(body),
            "controls": controls,
            "response": {"completed": False},
        }
        self._calls.append(call)
        return call

    def _require_upcoming_generation(
        self,
        spec: LogicalInputCountOperationSpec,
    ) -> None:
        observed_generation_count = len(self.generation_entries())
        expected_generation_count = spec.generation_index - 1
        if observed_generation_count != expected_generation_count:
            raise RequestLedgerError(
                "input-token count has the wrong upcoming generation"
            )

    def calls(self) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._calls)

    def generation_entries(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                copy.deepcopy(entry)
                for entry in self._calls
                if entry["kind"] == "generation"
            ]

    def input_entries(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                copy.deepcopy(entry)
                for entry in self._calls
                if entry["kind"] == "input_token_count"
            ]

    def input_operations(self) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._input_operations)

    def pending_input_operation(self) -> dict[str, Any] | None:
        with self._lock:
            return copy.deepcopy(self._pending_full)

    def rejections(self) -> list[dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._rejections)

    def provider_evidence(self) -> dict[str, Any]:
        return {
            "format_version": 1,
            "boundary": "installed RelayLM production provider -> transaction proxy -> llama.cpp",
            "expected_physical_model": self.expected_model,
            "calls": self.calls(),
            "rejections": self.rejections(),
            "semantic_generation_ceiling": SEMANTIC_GENERATION_CEILING,
            "semantic_generation_count": len(self.generation_entries()),
            "semantic_retry_count": self.retry_count,
            "replay_count": self.replay_count,
            "reseed_count": self.reseed_count,
            "fallback_count": 0,
            "repair_generation_count": 0,
            "body_policy": "sanitized controls, hashes, lengths, and bounded response evidence; no indiscriminate semantic payload log",
            "product_quality": "not_declared_by_harness",
        }

    def input_evidence(self) -> dict[str, Any]:
        operations = self.input_operations()
        input_entries = self.input_entries()
        calls_by_index = {entry["call_index"]: entry for entry in input_entries}

        def call_evidence(call_index: int | None) -> dict[str, Any] | None:
            if call_index is None:
                return None
            entry = calls_by_index.get(call_index)
            if entry is None:
                return None
            return {
                "call_index": entry["call_index"],
                "framing_role": entry["framing_role"],
                "body_sha256": entry["body_sha256"],
                "body_bytes": entry["body_bytes"],
                "controls": entry["controls"],
                "response": entry["response"],
            }

        logical_operations = [
            {
                "logical_operation_index": operation["logical_operation_index"],
                "upcoming_generation_index": operation["upcoming_generation_index"],
                "generation_index": operation["generation_index"],
                "generation_phase": operation["generation_phase"],
                "budget_role": operation["budget_role"],
                "endpoint_calls": operation["endpoint_calls"],
                "endpoint_roles": operation["endpoint_roles"],
                "full": call_evidence(operation.get("full_call_index")),
                "framing": call_evidence(operation.get("framing_call_index")),
            }
            for operation in operations
        ]
        return {
            "format_version": 1,
            "counter_capability": LLAMA_CPP_CHAT_COUNTER_CAPABILITY,
            "counter_evidence_identity": {
                "capability": LLAMA_CPP_CHAT_COUNTER_CAPABILITY,
                "implementation": LLAMA_CPP_CHAT_COUNTER_IMPLEMENTATION,
                "version": LLAMA_CPP_CHAT_COUNTER_VERSION,
                "mode": "exact",
            },
            "counter_method": LLAMA_CPP_RENDERER_METHOD,
            "framing_method": LLAMA_CPP_FRAMING_METHOD,
            "mode": "exact",
            "logical_count_operations": len(operations),
            "endpoint_calls": len(input_entries),
            "canonical_topology": [
                {
                    "generation_index": generation_index,
                    "generation_phase": generation_phase,
                    "budget_roles": list(budget_roles),
                }
                for generation_index, (generation_phase, budget_roles) in enumerate(
                    CANONICAL_TWO_TURN_TOPOLOGY,
                    start=1,
                )
            ],
            "logical_operations": logical_operations,
            "logical_operation_generation_mapping": [
                operation["generation_index"] for operation in operations
            ],
            "endpoint_generation_mapping": [
                entry["generation_index"] for entry in input_entries
            ],
            "logical_operation_roles": [
                operation["budget_role"] for operation in operations
            ],
            "endpoint_call_classification": [
                {
                    "call_index": entry["call_index"],
                    "logical_operation_index": entry["logical_operation_index"],
                    "framing_role": entry["framing_role"],
                    "body_sha256": entry["body_sha256"],
                    "controls": entry["controls"],
                    "response": entry["response"],
                }
                for entry in input_entries
            ],
            "full_and_framing_are_one_logical_operation": True,
            "product_quality": "not_declared_by_harness",
        }


class _ForwardingProxy:
    def __init__(self, *, origin: str, ledger: RequestLedger) -> None:
        self.origin = origin.rstrip("/")
        self.ledger = ledger
        self.server = _ProxyServer(("127.0.0.1", 0), origin=self.origin, ledger=ledger)
        self.thread: Thread | None = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/v1"

    def start(self) -> None:
        self.thread = Thread(target=self.server.serve_forever, name="relaylm-proof-proxy", daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5.0)


class _ProxyServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], *, origin: str, ledger: RequestLedger) -> None:
        self.origin = origin
        self.ledger = ledger
        super().__init__(address, _ProxyRequestHandler)


class _ProxyRequestHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        if self.path not in PROXY_PATHS:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if length < 0 or length > 8 * 1024 * 1024:
            self.send_error(413)
            return
        body = self.rfile.read(length)
        ledger = self.server.ledger  # type: ignore[attr-defined]
        try:
            entry = ledger.begin(path=self.path, body=body)
        except Exception as exc:
            ledger.reject(path=self.path, body=body, reason=str(exc))
            self._send_json_error(400, str(exc))
            return
        parsed_origin = urlsplit(self.server.origin)  # type: ignore[attr-defined]
        connection: http.client.HTTPConnection | None = None
        try:
            connection = http.client.HTTPConnection(
                parsed_origin.hostname,
                parsed_origin.port,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            headers = {
                "Accept": self.headers.get("Accept", "application/json"),
                "Content-Type": self.headers.get("Content-Type", "application/json"),
                "Content-Length": str(len(body)),
            }
            authorization = self.headers.get("Authorization")
            if authorization:
                headers["Authorization"] = authorization
            connection.request(
                "POST",
                f"{parsed_origin.path.rstrip('/')}{self.path}",
                body=body,
                headers=headers,
            )
            upstream = connection.getresponse()
            streaming = bool(_parse_json_object(body, "provider request").get("stream"))
            if streaming:
                self._forward_stream(upstream, entry, ledger)
            else:
                response_body = upstream.read()
                ledger.complete(
                    entry,
                    status=upstream.status,
                    body=response_body,
                    streaming=False,
                )
                self.send_response(upstream.status)
                self.send_header(
                    "Content-Type",
                    upstream.getheader("Content-Type", "application/json"),
                )
                self.send_header("Content-Length", str(len(response_body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(response_body)
                self.close_connection = True
        except Exception as exc:
            ledger.fail(entry, reason=str(exc))
            self._send_json_error(502, "transaction proxy forwarding failed")
        finally:
            if connection is not None:
                connection.close()

    def _forward_stream(self, upstream: http.client.HTTPResponse, entry: dict[str, Any], ledger: RequestLedger) -> None:
        self.send_response(upstream.status)
        self.send_header("Content-Type", upstream.getheader("Content-Type", "text/event-stream"))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        captured = bytearray()
        digest = hashlib.sha256()
        truncated = False
        try:
            while True:
                chunk = upstream.read(8192)
                if not chunk:
                    break
                digest.update(chunk)
                if len(captured) < 1024 * 1024:
                    captured.extend(chunk[: 1024 * 1024 - len(captured)])
                else:
                    truncated = True
                self.wfile.write(f"{len(chunk):X}\r\n".encode("ascii"))
                self.wfile.write(chunk)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
            ledger.complete(
                entry,
                status=upstream.status,
                body=bytes(captured),
                streaming=True,
                body_truncated=truncated,
                body_sha256=f"sha256:{digest.hexdigest()}",
            )
        except Exception:
            ledger.fail(entry, reason="stream forwarding failed")
            raise
        finally:
            self.close_connection = True

    def _send_json_error(self, status: int, detail: str) -> None:
        body = json.dumps({"error": {"message": _bounded_text(detail)}}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def log_message(self, format: str, *args: object) -> None:
        del format, args


def _wire_controls(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("model") is not None and not isinstance(payload.get("model"), str):
        raise RequestLedgerError("provider model control is malformed")
    messages = payload.get("messages")
    if not isinstance(messages, list):
        raise RequestLedgerError("provider messages control is malformed")
    message_controls = []
    for message in messages:
        if not isinstance(message, Mapping) or not isinstance(message.get("content"), str):
            raise RequestLedgerError("provider message control is malformed")
        content = message["content"]
        message_controls.append(
            {
                "role": message.get("role"),
                "content_length": len(content),
                "content_sha256": f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}",
            }
        )
    response_format = payload.get("response_format")
    response_format_evidence = None
    if isinstance(response_format, Mapping):
        schema = response_format.get("json_schema")
        response_format_evidence = {
            "type": response_format.get("type"),
            "name": schema.get("name") if isinstance(schema, Mapping) else None,
            "strict": schema.get("strict") if isinstance(schema, Mapping) else None,
            "schema_sha256": (
                f"sha256:{_sha256_json(schema.get('schema'))}"
                if isinstance(schema, Mapping) and isinstance(schema.get("schema"), Mapping)
                else None
            ),
        }
    return {
        "model": payload.get("model"),
        "stream": payload["stream"] if "stream" in payload else "absent",
        "cache_prompt": payload.get("cache_prompt", "absent"),
        "reasoning_effort": payload.get("reasoning_effort", "absent"),
        "temperature": payload.get("temperature", "absent"),
        "top_p": payload.get("top_p", "absent"),
        "max_tokens": payload.get("max_tokens", "absent"),
        "response_format": response_format_evidence,
        "messages": message_controls,
    }


def _is_framing_payload(payload: Mapping[str, Any]) -> bool:
    messages = payload.get("messages")
    return isinstance(messages, list) and bool(messages) and all(
        isinstance(message, Mapping) and message.get("content") == ""
        for message in messages
    )


def _response_wire_evidence(body: bytes, *, streaming: bool) -> dict[str, Any]:
    if streaming:
        text = body.decode("utf-8", errors="replace")
        content_parts: list[str] = []
        event_count = 0
        for line in text.splitlines():
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                continue
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            event_count += 1
            choices = event.get("choices") if isinstance(event, dict) else None
            if isinstance(choices, list) and choices and isinstance(choices[0], Mapping):
                delta = choices[0].get("delta")
                if isinstance(delta, Mapping) and isinstance(delta.get("content"), str):
                    content_parts.append(delta["content"])
        content = "".join(content_parts)
        return {
            "event_count": event_count,
            "content_length": len(content),
            "content_sha256": f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}",
            "content_excerpt": _bounded_text(content),
        }
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return {
            "bounded_excerpt": _bounded_text(
                body.decode("utf-8", errors="replace"), MAX_RESPONSE_EXCERPT
            )
        }
    choices = payload.get("choices") if isinstance(payload, dict) else None
    choice = choices[0] if isinstance(choices, list) and choices else None
    message = choice.get("message") if isinstance(choice, Mapping) else None
    content = message.get("content") if isinstance(message, Mapping) else None
    evidence: dict[str, Any] = {
        "choices": len(choices) if isinstance(choices, list) else None,
        "finish_reason": choice.get("finish_reason") if isinstance(choice, Mapping) else None,
        "bounded_excerpt": _bounded_text(
            body.decode("utf-8", errors="replace"), MAX_RESPONSE_EXCERPT
        ),
    }
    if isinstance(content, str):
        normalized = _normalize_extraction_content(content)
        evidence["content_length"] = len(content)
        evidence["content_sha256"] = f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"
        evidence["content_excerpt"] = _bounded_text(content, MAX_RESPONSE_EXCERPT)
        evidence["raw_response"] = {
            "sha256": f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}",
            "bytes": len(content.encode("utf-8")),
        }
        evidence["normalized_response"] = {
            "sha256": f"sha256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}",
            "bytes": len(normalized.encode("utf-8")),
        }
        try:
            wire = json.loads(normalized)
        except json.JSONDecodeError:
            wire = None
        if isinstance(wire, dict):
            evidence["wire_keys"] = sorted(wire)
            evidence["state_candidate_count"] = _bounded_collection_count(wire.get("state_candidates"))
            evidence["continuity_candidate_count"] = _bounded_collection_count(
                wire.get("continuity_candidates")
            )
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if isinstance(usage, Mapping):
        evidence["usage"] = {
            key: usage[key]
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
            if isinstance(usage.get(key), int) and not isinstance(usage.get(key), bool)
        }
    return evidence


def _normalize_extraction_content(content: str) -> str:
    if content.startswith("```json\n") and content.endswith("\n```"):
        return content[len("```json\n") : -len("\n```")]
    return content


def _bounded_collection_count(value: object) -> int | None:
    if not isinstance(value, list):
        return None
    return len(value)


def _get_json(url: str) -> Any:
    try:
        with httpx.Client(timeout=20.0, trust_env=False) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise InstalledLlamaCppTransactionError(f"GET {url} failed") from exc


def _parse_json_object(body: bytes, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RequestLedgerError(f"{label} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise RequestLedgerError(f"{label} must be a JSON object")
    return payload


def _snapshot_packages(fixture: Mapping[str, Any]) -> dict[str, Any]:
    profiles: dict[str, Any] = {}
    for name, raw_root in fixture["profile_roots"].items():
        root = Path(raw_root)
        files: dict[str, Any] = {}
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            payload = path.read_bytes()
            files[relative] = {
                "bytes": len(payload),
                "sha256": f"sha256:{hashlib.sha256(payload).hexdigest()}",
            }
        profiles[name] = {
            "root": str(root),
            "directory_sha256": f"sha256:{_directory_sha256(root)}",
            "files": files,
            "state_record_count": _state_record_count(root / "memory" / "state.json"),
            "event_record_count": _event_record_count(root / "memory" / "events.jsonl"),
            "continuity": {
                "configured": True,
                "runtime_is_in_process": True,
                "private_context_payload_retained": False,
            },
        }
    return {"profiles": profiles}


def _state_record_count(path: Path) -> int | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    states = payload.get("states") if isinstance(payload, dict) else None
    return len(states) if isinstance(states, list) else None


def _event_record_count(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except (OSError, UnicodeError):
        return 0


def _cleanup(
    *,
    relay_process: subprocess.Popen[str] | None,
    proxy: _ForwardingProxy | None,
    server_process: subprocess.Popen[str] | None,
    evidence_root: Path,
) -> dict[str, Any]:
    relay_exit = None
    proxy_closed = False
    server_exit = None
    errors: list[dict[str, str]] = []
    if relay_process is not None:
        try:
            relay_exit = _terminate_owned_process(relay_process)
        except Exception as exc:
            errors.append({"resource": "relaylm-serve", **_bounded_error(exc)})
    if proxy is not None:
        try:
            proxy.close()
            proxy_closed = True
        except Exception as exc:
            errors.append({"resource": "transaction-proxy", **_bounded_error(exc)})
    if server_process is not None:
        try:
            server_exit = _terminate_owned_process(server_process)
        except Exception as exc:
            errors.append({"resource": "llama-server", **_bounded_error(exc)})
    process_states: list[bool] = []
    for process in (relay_process, server_process):
        if process is None:
            continue
        try:
            process_states.append(process.poll() is not None)
        except Exception as exc:
            errors.append({"resource": "owned-process-state", **_bounded_error(exc)})
            process_states.append(False)
    return {
        "format_version": 1,
        "ownership": {
            "relaylm_serve_pid": None if relay_process is None else relay_process.pid,
            "llama_server_pid": None if server_process is None else server_process.pid,
            "proxy_transaction_owned": proxy is not None,
        },
        "relaylm_serve_exit_code": relay_exit,
        "proxy_closed": proxy_closed,
        "llama_server_exit_code": server_exit,
        "all_owned_processes_terminated": all(process_states),
        "evidence_root_retained": evidence_root.is_dir(),
        "external_processes_killed": 0,
        "errors": errors,
    }


def _evidence_file_receipts(root: Path) -> dict[str, Any]:
    receipts: dict[str, Any] = {}
    for path in sorted(root.iterdir()):
        if path.is_file() and path.name != "transaction-summary.json":
            receipts[path.name] = {
                "path": str(path),
                "sha256": f"sha256:{_sha256_file(path)}",
                "bytes": path.stat().st_size,
            }
    return receipts


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InstalledLlamaCppTransactionError(f"cannot read JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise InstalledLlamaCppTransactionError(f"JSON object required: {path}")
    return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _directory_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _sha256_json(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _shell_join(command: Sequence[object]) -> str:
    import shlex

    return shlex.join([str(item) for item in command])


def _bounded_text(value: str, limit: int = MAX_ERROR_TEXT) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "...[truncated]"


def _bounded_error(exc: Exception) -> dict[str, str]:
    return {"type": type(exc).__name__, "message": _bounded_text(str(exc))}


if __name__ == "__main__":
    raise SystemExit(main())

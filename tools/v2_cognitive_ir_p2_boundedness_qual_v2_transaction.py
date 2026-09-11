from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from typing import Any, TextIO

from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import (
    P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
    P2_BOUNDEDNESS_HARD_MAX_WORDS,
    P2_BOUNDEDNESS_MAX_OUTPUT_TOKENS,
    P2_BOUNDEDNESS_QUAL_V2_CLAIM,
    P2_BOUNDEDNESS_QUAL_V2_INCOMPLETE,
    P2_BOUNDEDNESS_QUAL_V2_LABEL,
    P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS,
    P2_BOUNDEDNESS_TARGET_MAX_WORDS,
    P2_BOUNDEDNESS_TARGET_MIN_WORDS,
    P2_BOUNDEDNESS_TOTAL_INPUT_TOKEN_REQUESTS,
    P2_BOUNDEDNESS_TOTAL_SEMANTIC_CALLS,
    build_margin_p2_formation_messages,
    generate_qualification_family_v2,
    qualification_call_plan_v2,
    validate_p2_boundedness_qualification_v2,
)
from relaylm.v2_transfer_actual_model import StructureProposalError
from tools.v2_cognitive_ir_p2_boundedness_qual_v2_llama_cpp import (
    P2BoundednessQualificationV2Client,
)
from tools.v2_cognitive_ir_s2_selected_llama_cpp import (
    S2_SELECTED_LLAMA_CPP_ENDPOINT,
    S2_SELECTED_LLAMA_CPP_REASONING_EFFORT,
    S2_SELECTED_LLAMA_CPP_TIMEOUT_SECONDS,
    probe_llama_cpp_selected_s2_binding,
)
from tools.v2_cognitive_ir_s2_selected_llama_cpp_transaction import (
    DEFAULT_ORIGIN,
    DEFAULT_PORT,
    SelectedS2TransactionError,
    _acquire_lifecycle_lock,
    _collect_gpu_identity,
    _collect_llama_identity,
    _controller_identity,
    _git_identity,
    _launch_command,
    _probe_server,
    _release_lifecycle_lock,
    _require_clean_repo,
    _require_server_flags,
    _sha256_file,
    _start_server,
    _terminate_owned_process,
    _verify_reasoning_effort_none_semantics,
    _wait_until_ready,
    _write_json,
)
from tools.v2_cognitive_ir_s3_llama_cpp_transaction import (
    DEFAULT_SHARED_LOCK_PATH,
    _lightweight_binding_check,
    _material_stat,
)
from tools.v2_cognitive_ir_s3_llama_cpp_transaction_listener_safe import (
    _port_has_no_listener,
)


TRANSACTION_FORMAT_VERSION = 1
QUALIFIED_CLASSIFICATION = "P2_BOUNDEDNESS_QUALIFIED_V2"
INCOMPLETE_CLASSIFICATION = "P2_BOUNDEDNESS_QUALIFICATION_V2_INCOMPLETE"


class P2BoundednessQualificationV2TransactionError(RuntimeError):
    """The frozen non-citable #2571 P2 boundedness qualification cannot proceed truthfully."""


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _fresh_artifact_root(value: str | None) -> Path:
    if value:
        path = Path(value).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=False)
        return path
    return Path(
        tempfile.mkdtemp(prefix="relaylm-v2-2211-p2-boundedness-qual-v2-artifacts-")
    ).resolve()


def _fingerprint(repo: Mapping[str, object], runtime: Mapping[str, object]) -> tuple[str, str]:
    payload = [
        "relaylm2-p2-boundedness-qualification-v2-identity-v1",
        P2_BOUNDEDNESS_QUAL_V2_LABEL,
        dict(repo),
        dict(runtime),
    ]
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}", f"p2bq2-{digest}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the frozen non-citable 12-call P2 boundedness qualification v2 exactly once."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--llama-cpp-root", default=str(Path.home() / "src" / "llama.cpp"))
    parser.add_argument(
        "--artifact-path",
        default=str(Path.home() / "models" / "gguf" / "gemma-4-12B-it-Q4_K_M.gguf"),
    )
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--artifact-root")
    parser.add_argument("--summary-path")
    parser.add_argument("--lock-path", default=str(DEFAULT_SHARED_LOCK_PATH))
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    repo_root = Path(args.repo_root).resolve()
    llama_cpp_root = Path(args.llama_cpp_root).expanduser().resolve()
    artifact_path = Path(args.artifact_path).expanduser().resolve()
    artifact_root = _fresh_artifact_root(args.artifact_root)
    summary_path = (
        Path(args.summary_path).expanduser().resolve()
        if args.summary_path
        else artifact_root / "p2-boundedness-qual-v2-summary.json"
    )
    lock_path = Path(args.lock_path).expanduser().resolve()
    log_path = Path.home() / "logs" / "relaylm-v2-2211-p2-boundedness-qual-v2.log"

    summary: dict[str, Any] = {
        "format_version": TRANSACTION_FORMAT_VERSION,
        "label": P2_BOUNDEDNESS_QUAL_V2_LABEL,
        "claim": P2_BOUNDEDNESS_QUAL_V2_INCOMPLETE,
        "classification": INCOMPLETE_CLASSIFICATION,
        "disposition": None,
        "citable": False,
        "architecture_consequence": "NONE",
        "artifact_root": str(artifact_root),
        "planned_semantic_calls": P2_BOUNDEDNESS_TOTAL_SEMANTIC_CALLS,
        "planned_input_token_requests": P2_BOUNDEDNESS_TOTAL_INPUT_TOKEN_REQUESTS,
        "target_margin": {
            "min_words": P2_BOUNDEDNESS_TARGET_MIN_WORDS,
            "max_words": P2_BOUNDEDNESS_TARGET_MAX_WORDS,
            "max_unicode_characters": P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS,
        },
        "hard_admission": {
            "max_words": P2_BOUNDEDNESS_HARD_MAX_WORDS,
            "max_unicode_characters": P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
        },
        "server_launch_count": 0,
        "host_count": 0,
        "full_material_attestation_count": 0,
        "lightweight_live_binding_check_count": 0,
        "provider_attempts": 0,
        "provider_completions": 0,
        "input_count_attempts": 0,
        "input_count_completions": 0,
        "qualification_admissions": 0,
        "retry_count": 0,
        "replay_count": 0,
        "reseed_count": 0,
        "fallback_count": 0,
        "lm_studio_contact_count": 0,
        "repository_mutation_count": 0,
        "efficacy_scoring_count": 0,
    }
    lock_handle: TextIO | None = None
    process: subprocess.Popen[str] | None = None
    client: P2BoundednessQualificationV2Client | None = None
    exit_code = 3

    try:
        validate_p2_boundedness_qualification_v2()
        _require_clean_repo(repo_root)
        head, tree = _git_identity(repo_root)
        repo_identity = {"commit": head, "tree": tree, "clean": True}
        summary["repository"] = repo_identity
        if args.origin.rstrip("/") != DEFAULT_ORIGIN or args.port != DEFAULT_PORT:
            raise P2BoundednessQualificationV2TransactionError(
                f"qualification endpoint must be exactly {DEFAULT_ORIGIN}/v1"
            )
        if S2_SELECTED_LLAMA_CPP_ENDPOINT != f"{DEFAULT_ORIGIN}/v1":
            raise P2BoundednessQualificationV2TransactionError("qualification transport endpoint drifted")
        if S2_SELECTED_LLAMA_CPP_REASONING_EFFORT != "none":
            raise P2BoundednessQualificationV2TransactionError("qualification reasoning control drifted")
        if not artifact_path.is_file():
            raise P2BoundednessQualificationV2TransactionError(
                f"canonical GGUF is not a file: {artifact_path}"
            )

        lock_handle = _acquire_lifecycle_lock(lock_path)
        summary["lock"] = {"path": str(lock_path), "acquired": True}
        if not _port_has_no_listener("127.0.0.1", args.port):
            raise P2BoundednessQualificationV2TransactionError(
                "127.0.0.1:1234 is occupied before qualification"
            )

        server_binary = llama_cpp_root / "build" / "bin" / "llama-server"
        revision, version = _collect_llama_identity(
            llama_cpp_root=llama_cpp_root,
            server_binary=server_binary,
        )
        _require_server_flags(server_binary)
        _verify_reasoning_effort_none_semantics(llama_cpp_root=llama_cpp_root, revision=revision)
        binary_sha256 = _sha256_file(server_binary)
        artifact_sha256 = _sha256_file(artifact_path)
        binary_stat = _material_stat(server_binary)
        artifact_stat = _material_stat(artifact_path)
        gpu_identity = _collect_gpu_identity()

        log_path.parent.mkdir(parents=True, exist_ok=True)
        if log_path.exists():
            log_path = log_path.with_name(f"{log_path.stem}-{head[:12]}.log")
        if log_path.exists():
            raise P2BoundednessQualificationV2TransactionError(
                f"fresh qualification log already exists: {log_path}"
            )
        launch_command = _launch_command(
            server_binary=server_binary,
            artifact_path=artifact_path,
            port=args.port,
            log_path=log_path,
        )
        process = _start_server(launch_command)
        summary["server_launch_count"] = 1
        summary["server_pid"] = process.pid
        summary["launch_command"] = shlex.join(launch_command)
        summary["log_path"] = str(log_path)
        _wait_until_ready(process=process, origin=DEFAULT_ORIGIN)
        probe = _probe_server(
            origin=DEFAULT_ORIGIN,
            api_base=S2_SELECTED_LLAMA_CPP_ENDPOINT,
            artifact_path=artifact_path,
        )
        controller = _controller_identity(
            revision=revision,
            build_info=str(probe["build_info"]),
            server_binary=server_binary,
            binary_sha256=binary_sha256,
            artifact_path=artifact_path,
            artifact_sha256=artifact_sha256,
            launch_command=launch_command,
            process=process,
            log_path=log_path,
            gpu_identity=gpu_identity,
            probe=probe,
        )
        request_model = str(probe["request_model"])
        start_binding = probe_llama_cpp_selected_s2_binding(
            base_url=S2_SELECTED_LLAMA_CPP_ENDPOINT,
            model=request_model,
            controller_identity=controller,
        )
        summary["full_material_attestation_count"] = 1
        attested = start_binding.get("runtime_attestation")
        if not isinstance(attested, Mapping):
            raise P2BoundednessQualificationV2TransactionError(
                "qualification runtime attestation is not an object"
            )

        runtime = {
            "llama_cpp_revision": revision,
            "llama_cpp_version": version,
            "binary_sha256": binary_sha256,
            "artifact_sha256": artifact_sha256,
            "gpu": dict(gpu_identity),
            "request_model": probe["request_model"],
            "build_info": probe["build_info"],
            "model_path": probe["model_path"],
            "model_ftype": probe.get("model_ftype"),
            "context": probe["context"],
            "slot_count": probe["slot_count"],
            "slot_contexts": probe["slot_contexts"],
            "runtime_attestation": dict(attested),
            "reasoning_effort": S2_SELECTED_LLAMA_CPP_REASONING_EFFORT,
            "temperature": 0.0,
            "seed": None,
            "max_output_tokens": P2_BOUNDEDNESS_MAX_OUTPUT_TOKENS,
            "timeout_seconds": S2_SELECTED_LLAMA_CPP_TIMEOUT_SECONDS,
        }
        summary["runtime_material"] = runtime
        fingerprint, run_id = _fingerprint(repo_identity, runtime)
        summary["identity_fingerprint"] = fingerprint
        summary["run_id"] = run_id

        plan = qualification_call_plan_v2()
        client = P2BoundednessQualificationV2Client(
            base_url=S2_SELECTED_LLAMA_CPP_ENDPOINT,
            model=request_model,
            call_plan=plan,
            timeout_seconds=S2_SELECTED_LLAMA_CPP_TIMEOUT_SECONDS,
            max_output_tokens=P2_BOUNDEDNESS_MAX_OUTPUT_TOKENS,
            temperature=0.0,
            seed=None,
        )
        summary["host_count"] = 1

        call_index = 0
        for regime in ("shared", "null", "mismatch", "shift"):
            for family_index in range(3):
                question_id = plan[call_index]
                family = generate_qualification_family_v2(regime, family_index)
                _lightweight_binding_check(
                    process=process,
                    expected_probe=probe,
                    server_binary=server_binary,
                    expected_binary_stat=binary_stat,
                    artifact_path=artifact_path,
                    expected_artifact_stat=artifact_stat,
                )
                summary["lightweight_live_binding_check_count"] += 1
                client.complete_named(
                    question_id,
                    build_margin_p2_formation_messages(family),
                    output_kind="text",
                )
                call_index += 1

        client.require_complete_qualification()
        end_binding = probe_llama_cpp_selected_s2_binding(
            base_url=S2_SELECTED_LLAMA_CPP_ENDPOINT,
            model=request_model,
            controller_identity=controller,
        )
        summary["full_material_attestation_count"] = 2
        if _canonical(end_binding) != _canonical(start_binding):
            raise P2BoundednessQualificationV2TransactionError(
                "runtime/material binding drifted during qualification"
            )
        if _material_stat(server_binary) != binary_stat or _material_stat(artifact_path) != artifact_stat:
            raise P2BoundednessQualificationV2TransactionError(
                "runtime material stat drifted during qualification"
            )

        if client.provider_attempts != P2_BOUNDEDNESS_TOTAL_SEMANTIC_CALLS:
            raise P2BoundednessQualificationV2TransactionError(
                "qualification semantic call total drifted"
            )
        if client.input_count_attempts != P2_BOUNDEDNESS_TOTAL_INPUT_TOKEN_REQUESTS:
            raise P2BoundednessQualificationV2TransactionError(
                "qualification input-token request total drifted"
            )
        if summary["lightweight_live_binding_check_count"] != P2_BOUNDEDNESS_TOTAL_SEMANTIC_CALLS:
            raise P2BoundednessQualificationV2TransactionError(
                "qualification live-binding check total drifted"
            )

        summary["claim"] = P2_BOUNDEDNESS_QUAL_V2_CLAIM
        summary["classification"] = QUALIFIED_CLASSIFICATION
        summary["disposition"] = "ALL_12_WITHIN_UNCHANGED_HARD_ENVELOPE"
        exit_code = 0
        return exit_code
    except (
        P2BoundednessQualificationV2TransactionError,
        SelectedS2TransactionError,
        StructureProposalError,
    ) as exc:
        summary["classification"] = INCOMPLETE_CLASSIFICATION
        summary["disposition"] = summary.get("disposition") or (
            "EXECUTION_BLOCKED" if summary["host_count"] == 0 else "STOPPED_ON_MECHANICAL_FAILURE"
        )
        summary["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 3 if summary["host_count"] == 0 else 2
        return exit_code
    except Exception as exc:  # pragma: no cover - terminal fail-closed boundary
        summary["classification"] = INCOMPLETE_CLASSIFICATION
        summary["disposition"] = "UNEXPECTED_FAILURE"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 3 if summary["host_count"] == 0 else 2
        return exit_code
    finally:
        if client is not None:
            summary["provider_attempts"] = client.provider_attempts
            summary["provider_completions"] = client.provider_completions
            summary["input_count_attempts"] = client.input_count_attempts
            summary["input_count_completions"] = client.input_count_completions
            summary["qualification_admissions"] = client.qualification_admissions
            summary["mechanical_records"] = list(client.mechanical_records)
            if client.last_failure_metadata is not None:
                summary["first_failure_metadata"] = dict(client.last_failure_metadata)
            else:
                failed = next(
                    (record for record in client.mechanical_records if not bool(record.get("admitted"))),
                    None,
                )
                if failed is not None:
                    summary["first_failure_metadata"] = dict(failed)
            client.close()
        if process is not None:
            summary["cleanup"] = _terminate_owned_process(process)
            try:
                summary["listener_released"] = _port_has_no_listener("127.0.0.1", args.port)
            except Exception as exc:  # pragma: no cover - host-specific fail-closed boundary
                summary["listener_released"] = False
                summary["cleanup_listener_error"] = f"{type(exc).__name__}: {exc}"
                if exit_code == 0:
                    summary["claim"] = P2_BOUNDEDNESS_QUAL_V2_INCOMPLETE
                    summary["classification"] = INCOMPLETE_CLASSIFICATION
                    summary["disposition"] = "CLEANUP_LISTENER_UNVERIFIED"
                    exit_code = 2
            if log_path.is_file():
                summary["log_sha256"] = _sha256_file(log_path)
                summary["log_bytes"] = log_path.stat().st_size
        summary["transaction_exit_code"] = exit_code
        _write_json(summary_path, summary)
        print(_canonical(summary))
        if lock_handle is not None:
            _release_lifecycle_lock(lock_handle)


if __name__ == "__main__":
    raise SystemExit(main())

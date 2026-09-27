from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

import tools.relay_physical_run as physical_runner
import tools.wsl_nvidia_runtime_closure_rehearsal as rehearsal
from tools import cache_correctness_repair_runtime as candidate_runtime


def _descriptor(tmp_path: Path) -> dict[str, object]:
    binary = str(rehearsal.EXPECTED_SERVER_BINARY)
    model = str(candidate_runtime.MODEL_PATH.resolve())
    roots = {
        "descriptor": str((tmp_path / "descriptor.json").resolve()),
        "receipt": str((tmp_path / "receipt.json").resolve()),
        "preflight": str((tmp_path / "preflight").resolve()),
        "output": str((tmp_path / "output").resolve()),
    }
    manifest = str((tmp_path / "manifest.json").resolve())
    return {
        "schema_version": 1,
        "status": rehearsal.PROPOSAL_STATUS,
        "owner_issue": 3018,
        "target_id": rehearsal.TARGET_ID,
        "attempt_id": rehearsal.ATTEMPT_ID,
        "repository": {
            "root": str(tmp_path.resolve()),
            "branch": "v1",
            "head": "1" * 40,
            "tree": "2" * 40,
        },
        "candidate": {
            "manifest_path": manifest,
            "manifest_sha256": "3" * 64,
            "server_binary": binary,
            "server_sha256": rehearsal.EXPECTED_SERVER_SHA256,
            "model_path": model,
            "model_sha256": candidate_runtime.MODEL_SHA256,
            "wsl_runtime_closure_sha256": "5" * 64,
        },
        "roots": roots,
        "server": {
            "argv": [
                binary,
                "-m",
                model,
                "--host",
                "127.0.0.1",
                "--port",
                "1234",
                "-ngl",
                "999",
                "-c",
                "8192",
                "-np",
                "1",
                "--no-context-shift",
                "-lv",
                "4",
                "--log-timestamps",
                "--log-file",
                str(Path(roots["output"]) / "llama-server.log"),
            ],
            "environment": {"PATH": "/usr/bin", "HOME": "/tmp"},
            "startup_timeout_seconds": rehearsal.STARTUP_TIMEOUT_SECONDS,
            "model_loaded_log_marker": rehearsal.MODEL_LOADED_MARKER,
        },
        "limits": {
            "maximum_server_launches": 1,
            "maximum_model_loads": 1,
            "maximum_model_facing_posts": 0,
            "generation_requests": 0,
            "input_count_requests": 0,
            "public_completions": 0,
        },
        "port": 1234,
        "closure_attestation": "complete-live-process-map-after-model-loaded",
        "execution_authority": rehearsal.PROPOSAL_STATUS,
    }


def _authority_body(descriptor: dict[str, object], descriptor_sha256: str) -> str:
    candidate = descriptor["candidate"]
    assert isinstance(candidate, dict)
    return "\n".join(
        (
            rehearsal.AUTHORIZATION_MARKER,
            descriptor_sha256,
            rehearsal.TARGET_ID,
            rehearsal.ATTEMPT_ID,
            candidate["server_sha256"],
            candidate["model_sha256"],
            candidate["wsl_runtime_closure_sha256"],
            "maximum_server_launches=1",
            "maximum_model_loads=1",
            "maximum_model_facing_posts=0",
            "generation_requests=0",
            "input_count_requests=0",
            "public_completions=0",
        )
    )


def test_target_is_registered_on_canonical_v1_physical_runner() -> None:
    targets = physical_runner._load_targets(Path(__file__).parents[2])
    target = targets[rehearsal.TARGET_ID]

    assert target.module == "tools.wsl_nvidia_runtime_closure_rehearsal"
    assert target.branch == "v1"
    assert target.required_distributions == ("build", "httpx")


def test_candidate_manifest_uses_static_closure_key_for_server_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_root = tmp_path / "candidate-build"
    binary = build_root / "bin" / "llama-server"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"server")
    binary.chmod(0o755)
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model")
    binary_sha256 = "a" * 64
    model_sha256 = "b" * 64
    binary_identity = {
        "device": 1,
        "inode": 2,
        "mode": 33261,
        "size": 6,
        "nlink": 1,
        "ctime_ns": 3,
        "mtime_ns": 4,
    }
    shared_libraries = {
        str(binary.resolve()): {
            "sha256": binary_sha256,
            "identity": binary_identity,
            "dependencies": {},
            "kernel_vdso_is_process_supplied": False,
        }
    }
    wsl_closure = {"contract": "wsl-nvidia-cuda-runtime-package-closure-v2"}
    monkeypatch.setattr(rehearsal, "EXPECTED_SERVER_BINARY", binary.resolve())
    monkeypatch.setattr(rehearsal, "EXPECTED_SERVER_SHA256", binary_sha256)
    monkeypatch.setattr(candidate_runtime, "MODEL_PATH", model.resolve())
    monkeypatch.setattr(candidate_runtime, "MODEL_SHA256", model_sha256)
    monkeypatch.setattr(
        rehearsal,
        "_sha256_file",
        lambda path: model_sha256 if Path(path).resolve() == model.resolve() else binary_sha256,
    )
    monkeypatch.setattr(
        candidate_runtime,
        "collect_static_library_closure",
        lambda root: shared_libraries,
    )
    monkeypatch.setattr(
        candidate_runtime,
        "collect_wsl_cuda_driver_closure",
        lambda libraries: wsl_closure,
    )
    monkeypatch.setattr(candidate_runtime, "run_text", lambda command: "gpu-identity")
    monkeypatch.setattr(
        candidate_runtime,
        "_sealed_file_record",
        lambda path, **kwargs: {
            "path": str(Path(path).resolve()),
            "realpath": str(Path(path).resolve()),
            "sha256": model_sha256,
            "identity": {**binary_identity, "inode": 5, "size": 5},
        },
    )

    manifest = rehearsal.collect_candidate_manifest(
        candidate_binary=binary,
        model_path=model,
    )

    assert manifest["server"] == {
        "path": str(binary.resolve()),
        "sha256": binary_sha256,
        "identity": binary_identity,
    }
    assert manifest["build"]["shared_libraries"] == shared_libraries
    assert manifest["build"]["wsl_cuda_driver_closure"] == wsl_closure


def test_proposal_descriptor_freezes_zero_request_limits(tmp_path: Path) -> None:
    descriptor = _descriptor(tmp_path)

    rehearsal._validate_descriptor(descriptor)

    assert descriptor["status"] == "PROPOSAL_ONLY_NOT_EXECUTION_AUTHORITY"
    assert descriptor["execution_authority"] == "PROPOSAL_ONLY_NOT_EXECUTION_AUTHORITY"
    assert descriptor["limits"]["maximum_model_facing_posts"] == 0
    assert descriptor["limits"]["generation_requests"] == 0
    assert descriptor["limits"]["input_count_requests"] == 0
    assert descriptor["limits"]["public_completions"] == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("maximum_model_facing_posts", 1),
        ("generation_requests", 1),
        ("input_count_requests", 1),
        ("public_completions", 1),
    ],
)
def test_proposal_descriptor_rejects_nonzero_request_ceilings(
    tmp_path: Path, field: str, value: int
) -> None:
    descriptor = _descriptor(tmp_path)
    descriptor["limits"][field] = value

    with pytest.raises(rehearsal.RehearsalError, match="zero requests"):
        rehearsal._validate_descriptor(descriptor)


def test_proposal_marker_and_attempt_b_comment_cannot_authorize_rehearsal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor = _descriptor(tmp_path)
    digest = "6" * 64
    monkeypatch.setattr(
        rehearsal,
        "_gh_json",
        lambda args: {
            "number": 3018,
            "state": "open",
            "user": {"login": "rinsakamo"},
        },
    )
    monkeypatch.setattr(
        rehearsal,
        "_gh_comments",
        lambda: [
            {
                "id": 5855287392,
                "created_at": "2026-09-27T00:00:00Z",
                "user": {"login": "rinsakamo"},
                "body": _authority_body(descriptor, digest)
                + "\nPROPOSAL_ONLY_NOT_EXECUTION_AUTHORITY",
            }
        ],
    )

    with pytest.raises(rehearsal.RehearsalError, match="does not bind"):
        rehearsal.verify_execution_authority(
            comment_id=5855287392,
            descriptor_sha256=digest,
            descriptor=descriptor,
        )


def test_exact_owner_authority_is_revoked_by_a_later_owner_comment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor = _descriptor(tmp_path)
    digest = "7" * 64
    monkeypatch.setattr(
        rehearsal,
        "_gh_json",
        lambda args: {
            "number": 3018,
            "state": "open",
            "user": {"login": "rinsakamo"},
        },
    )
    monkeypatch.setattr(
        rehearsal,
        "_gh_comments",
        lambda: [
            {
                "id": 600,
                "created_at": "2026-09-27T00:00:00Z",
                "user": {"login": "rinsakamo"},
                "body": _authority_body(descriptor, digest),
            },
            {
                "id": 601,
                "created_at": "2026-09-27T00:01:00Z",
                "user": {"login": "rinsakamo"},
                "body": rehearsal.REVOKE_MARKERS[0],
            },
        ],
    )

    with pytest.raises(rehearsal.RehearsalError, match="revoked"):
        rehearsal.verify_execution_authority(
            comment_id=600,
            descriptor_sha256=digest,
            descriptor=descriptor,
        )


def test_non_owner_cannot_authorize_rehearsal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor = _descriptor(tmp_path)
    digest = "8" * 64
    monkeypatch.setattr(
        rehearsal,
        "_gh_json",
        lambda args: {
            "number": 3018,
            "state": "open",
            "user": {"login": "rinsakamo"},
        },
    )
    monkeypatch.setattr(
        rehearsal,
        "_gh_comments",
        lambda: [
            {
                "id": 602,
                "created_at": "2026-09-27T00:00:00Z",
                "user": {"login": "someone-else"},
                "body": _authority_body(descriptor, digest),
            }
        ],
    )

    with pytest.raises(rehearsal.RehearsalError, match="authority is unavailable"):
        rehearsal.verify_execution_authority(
            comment_id=602,
            descriptor_sha256=digest,
            descriptor=descriptor,
        )


def test_complete_map_inventory_classifies_sealed_and_unknown_paths() -> None:
    server = "/candidate/bin/llama-server"
    ggml = "/candidate/bin/libggml-cuda.so"
    shim = "/usr/lib/wsl/lib/libcuda.so.1"
    payload = "/usr/lib/wsl/drivers/nvmdi.inf_amd64_47a93ea256b1ab85/libcuda.so.1.1"
    companion = "/usr/lib/wsl/drivers/nvmdi.inf_amd64_47a93ea256b1ab85/libnvdxgdmal.so.1"
    toolkit = "/usr/local/cuda-12.8/lib64/libcudart.so.12"
    system = "/usr/lib/x86_64-linux-gnu/libc.so.6"
    unknown = "/usr/lib/wsl/drivers/nvmdi.inf_amd64_47a93ea256b1ab85/libnvidia-ml.so.1"
    manifest = {
        "server": {"path": server},
        "build": {
            "shared_libraries": {
                server: {
                    "dependencies": {
                        "libggml-cuda.so": {"path": ggml},
                        "libcuda.so.1": {"path": shim},
                        "libcudart.so.12": {"path": toolkit},
                        "libc.so.6": {"path": system},
                    }
                },
                ggml: {"dependencies": {}},
            },
            "wsl_cuda_driver_closure": {
                "shim": {"aliases": [{"path": shim}]},
                "driver_package": {
                    "root": "/usr/lib/wsl/drivers/nvmdi.inf_amd64_47a93ea256b1ab85",
                    "runtime_objects": [{"path": payload}, {"path": companion}],
                },
            },
        },
    }
    lines = [
        f"1000-2000 r-xp 00000000 08:01 1 {server}",
        f"2000-3000 r-xp 00000000 08:01 2 {ggml}",
        f"3000-4000 r-xp 00000000 2c:04 3 {shim}",
        f"4000-5000 r-xp 00000000 24:09 4 {payload}",
        f"5000-6000 r-xp 00000000 24:09 5 {companion}",
        f"6000-7000 r-xp 00000000 08:01 6 {toolkit}",
        f"7000-8000 r-xp 00000000 08:01 7 {system}",
        f"8000-9000 r-xp 00000000 24:09 8 {unknown}",
        "9000-a000 rw-p 00000000 00:00 0 [heap]",
    ]

    inventory = rehearsal._mapped_file_inventory("\n".join(lines), manifest)

    assert [item["classification"] for item in inventory] == [
        "candidate-llama-or-ggml-library",
        "candidate-llama-or-ggml-library",
        "wsl-guest-cuda-shim",
        "nvidia-wsl-runtime-package-object",
        "nvidia-wsl-runtime-package-object",
        "cuda-toolkit-library",
        "ordinary-system-library",
        "other-nvidia-package-object",
        "anonymous-or-pseudo-mapping",
    ]


def test_zero_request_counter_audit_rejects_any_consumed_request() -> None:
    rehearsal._assert_zero_request_counters(
        {
            "model_facing_post_count": 0,
            "generation_request_count": 0,
            "input_count_request_count": 0,
            "public_completion_count": 0,
            "scientific_attempt_consumed": False,
        }
    )
    with pytest.raises(rehearsal.RehearsalError, match="model-facing request"):
        rehearsal._assert_zero_request_counters(
            {
                "model_facing_post_count": 1,
                "generation_request_count": 0,
                "input_count_request_count": 0,
                "public_completion_count": 0,
                "scientific_attempt_consumed": False,
            }
        )


def test_server_log_must_not_record_a_model_facing_post() -> None:
    rehearsal._assert_no_model_facing_post_log(
        "llama_server: model loaded\nserver listening at 127.0.0.1:1234\n"
    )
    with pytest.raises(rehearsal.RehearsalError, match="model-facing POST"):
        rehearsal._assert_no_model_facing_post_log(
            "llama_server: model loaded\nPOST /v1/chat/completions 200\n"
        )
    assert rehearsal._model_facing_post_log_lines(
        "POST /completion 200\nPOST /tokenize 200\n"
    ) == ["POST /completion 200", "POST /tokenize 200"]


def test_final_server_log_counts_requests_and_blocks_success() -> None:
    summary: dict[str, object] = {
        "model_facing_post_count": 0,
        "model_loaded_marker_count": 1,
        "failure": None,
    }

    terminal = rehearsal._apply_final_server_log_evidence(
        summary,
        rehearsal.PASS_TERMINAL,
        f"{rehearsal.MODEL_LOADED_MARKER}\nPOST /completion 200\n",
    )

    assert terminal == rehearsal.BLOCKED_TERMINAL
    assert summary["model_facing_post_count"] == 1
    assert summary["failure"] == {
        "type": "UnexpectedModelFacingPOST",
        "message": "server log recorded 1 POST request(s)",
    }


def test_two_map_snapshots_must_bind_the_same_process_start() -> None:
    first = {
        "pid": 123,
        "process_start_ticks": 456,
        "executable": "/candidate/bin/llama-server",
        "argv": ["/candidate/bin/llama-server", "-m", "/model.gguf"],
    }
    rehearsal._require_same_process_identity(first, dict(first))

    changed = {**first, "process_start_ticks": 457}
    with pytest.raises(rehearsal.RehearsalError, match="identity changed"):
        rehearsal._require_same_process_identity(first, changed)


def test_queue_receipt_must_bind_the_exact_running_child(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path.resolve()
    descriptor_path = (tmp_path / "descriptor.json").resolve()
    receipt_path = (tmp_path / "receipt.json").resolve()
    authority_comment_id = 603
    command = [
        sys.executable,
        "-m",
        "tools.wsl_nvidia_runtime_closure_rehearsal",
        "--descriptor",
        str(descriptor_path),
        "--authority-comment-id",
        str(authority_comment_id),
    ]
    receipt = {
        "schema_version": 2,
        "request_id": "a" * 32,
        "receipt_path": str(receipt_path),
        "target_label": rehearsal.TARGET_ID,
        "resource_key": rehearsal.RESOURCE_KEY,
        "command_executable": Path(sys.executable).name,
        "command_argv_sha256": hashlib.sha256(
            json.dumps(command, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "cwd": str(repo_root),
        "state": "RUNNING",
        "lease_state": "ACQUIRED",
    }
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    verified = rehearsal._verify_queue_receipt(
        receipt_path,
        repo_root=repo_root,
        descriptor_path=descriptor_path,
        authority_comment_id=authority_comment_id,
    )
    assert verified["request_id"] == "a" * 32

    receipt["state"] = "FINAL_PREFLIGHT"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(rehearsal.RehearsalError, match="queue receipt"):
        rehearsal._verify_queue_receipt(
            receipt_path,
            repo_root=repo_root,
            descriptor_path=descriptor_path,
            authority_comment_id=authority_comment_id,
        )

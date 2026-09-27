from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

import tools.cache_correctness_repair_runtime as runtime
import tools.relay_physical_run as physical_runner
import tools.v1_cache_correctness_qualification_serve as qualification_serve
import tools.v1_cache_correctness_repair_qualification as qualification


def _descriptor(tmp_path: Path) -> dict[str, object]:
    output = tmp_path / "attempt-output"
    preflight = tmp_path / "attempt-preflight"
    return {
        "format_version": 1,
        "authority_mode": "PROPOSAL_ONLY_NOT_EXECUTION_AUTHORITY",
        "repository": {
            "name": "rinsakamo/relay-lm",
            "execution_branch": "v1",
            "head": "d3dc8d89227cf9260ea750c08060eec435d2050a",
            "tree": "f4261871843a9049695b733f847fc9877634c812",
        },
        "owner_branch": qualification.OWNER_BRANCH,
        "attempt_id": qualification.ATTEMPT_ID,
        "target_id": qualification.TARGET_ID,
        "resource_key": qualification.QUEUE_RESOURCE,
        "source_manifest": {
            "path": str(tmp_path / "candidate-runtime.json"),
            "sha256": "sha256:" + "1" * 64,
        },
        "model": {
            "path": str(runtime.MODEL_PATH),
            "sha256": runtime.MODEL_SHA256,
        },
        "queue_receipt_path": str(tmp_path / "queue-receipt.json"),
        "roots": {
            "preflight": str(preflight),
            "output": str(output),
            "cold": str(output / "cold"),
            "reused": str(output / "reused"),
        },
        "ports": {"llama_cpp": 1234, "relaylm": 18090},
        "server_policy": {
            "fresh_process_per_arm": True,
            "slots": 1,
            "candidate_model_load_maximum": 2,
            "slot_state_within_arm": "retained-across-buffered-then-streaming-request-order",
            "between_arm_state": "separate-fresh-server-and-fresh-profile-copies-per-arm-no-state-shared",
            "context_tokens": 8192,
            "gpu_layers": 999,
            "swa_full": False,
            "checkpointing_disabled": False,
        },
        "request_policy": {
            "order": list(qualification.REQUEST_ORDER),
            "model_facing_request_order": [
                list(item) for item in qualification.MODEL_FACING_REQUEST_ORDER
            ],
            "cold_generation_cache_prompt": False,
            "reused_generation_cache_prompt": True,
            "count_endpoint_treatment": "byte-identical-cache_prompt-false",
            "product_cache_policy": "disabled",
            "reasoning_effort": "none",
            "temperature": 0,
            "top_p": 1,
            "seed_policy": "seed-field-omitted-backend-default",
            "max_tokens": 256,
            "generation_request_maximum": qualification.GENERATION_MAXIMUM,
            "input_count_request_maximum": qualification.INPUT_COUNT_MAXIMUM,
            "model_facing_post_maximum": qualification.MODEL_FACING_MAXIMUM,
            "public_completion_maximum": qualification.PUBLIC_COMPLETION_MAXIMUM,
            "dynamic_identity": "each-exact-body-fsynced-and-hashed-before-one-send",
        },
        "failure_policy": {
            "stop_on_first_failure": True,
            "retry": False,
            "replay": False,
            "reseed": False,
            "fallback": False,
            "alternate_port": False,
            "alternate_output_root": False,
            "manual_arm_completion": False,
            "new_attempt_after_preparation_failure": False,
        },
        "execution_authority_policy": {
            "required_issue": 3013,
            "required_author": "rinsakamo",
            "required_marker": "EXECUTION_AUTHORITY_GRANTED",
            "comment_must_name_descriptor_sha256": True,
            "comment_must_name_attempt_and_target": True,
            "fresh_issue_comment_check_before_each_model_facing_post": True,
            "fresh_v1_head_check_before_each_model_facing_post": True,
        },
    }


def _wire_body(*, cache_prompt: bool = False, stream: bool = False, content: str = "prompt") -> bytes:
    return json.dumps(
        {
            "model": "gemma-4-12B-it-Q4_K_M",
            "messages": [
                {"role": "system", "content": "fixed instruction"},
                {"role": "user", "content": content},
            ],
            "stream": stream,
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 256,
            "reasoning_effort": "none",
            "cache_prompt": cache_prompt,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def test_target_registry_uses_new_owner_target_and_canonical_resource() -> None:
    targets = physical_runner._load_targets(Path(__file__).parents[2])
    current = targets[qualification.TARGET_ID]

    assert current.module == "tools.v1_cache_correctness_repair_qualification"
    assert current.branch == "v1"
    assert current.required_distributions == ("build", "httpx")
    assert qualification.TARGET_ID not in {
        "diagnostic:3006-projection-provenance",
        "v1:llama-cpp-cache-correctness-reproducer",
    }


def test_runtime_trace_requires_explicit_first_empty_slot_record() -> None:
    parsed = qualification._parse_runtime_trace(
        """
[trace] 3013 reuse-decision task_id=1 slot_id=0 input_tokens=41 lcp=0 live_pos_min=-1 live_pos_max=-1 n_swa=128 pos_min_thold=0 n_past_before=0 restore_required=not-evaluated decision_state=empty-slot checkpoints=0
[trace] 3013 reuse-result task_id=1 slot_id=0 selected_checkpoint=NONE selected_index=-1 selected_pos_min=-1 selected_pos_max=-1 n_past_before=0 n_past_after=0 outcome=empty-slot-full-prompt
[trace] 3013 prompt-result task_id=1 slot_id=0 input_tokens=41 prompt_eval_tokens=41 cache_n=0 stop_type=0
"""
    )

    assert len(parsed["decisions"]) == len(parsed["results"]) == 1
    assert parsed["decisions"][0]["decision_state"] == "empty-slot"
    assert parsed["results"][0]["outcome"] == "empty-slot-full-prompt"
    assert parsed["prompt_results"][0]["prompt_eval_tokens"] == 41


def test_descriptor_schema_binds_attempt_owner_source_and_disabled_product_cache(
    tmp_path: Path,
) -> None:
    validated = qualification.validate_descriptor(_descriptor(tmp_path))

    assert validated["payload"]["attempt_id"] == "cache-correctness-repair-qualification-20260927-a"
    assert validated["payload"]["repository"]["execution_branch"] == "v1"
    assert validated["payload"]["request_policy"]["product_cache_policy"] == "disabled"
    assert validated["roots"]["cold"] == tmp_path / "attempt-output" / "cold"
    assert validated["payload"]["request_policy"]["model_facing_request_order"] == [
        list(item) for item in qualification.MODEL_FACING_REQUEST_ORDER
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("attempt_id", "cache-correctness-repair-qualification-20260927-b"),
        ("target_id", "diagnostic:3006-projection-provenance"),
        ("owner_branch", "main"),
        ("authority_mode", "EXECUTION_AUTHORITY_GRANTED"),
    ],
)
def test_descriptor_rejects_wrong_owner_target_attempt_and_authority(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    descriptor = _descriptor(tmp_path)
    descriptor[field] = value

    with pytest.raises(qualification.QualificationTargetError):
        qualification.validate_descriptor(descriptor)


def test_exact_execution_authority_requires_exact_owner_comment_and_detects_same_time_stop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    descriptor = tmp_path / "descriptor.json"
    descriptor.write_text("{}\n", encoding="utf-8")
    descriptor_hash = "sha256:" + "a" * 64
    created_at = "2026-09-27T01:02:03Z"
    grant_body = " ".join(
        (
            "EXECUTION_AUTHORITY_GRANTED",
            descriptor_hash,
            qualification.ATTEMPT_ID,
            qualification.TARGET_ID,
            runtime.BASE_REVISION,
            runtime.PRODUCTION_TREE,
            runtime.MODEL_SHA256,
        )
    )
    grant = {
        "id": 1001,
        "created_at": created_at,
        "user": {"login": "rinsakamo"},
        "body": grant_body,
    }

    def fake_api(
        pages: list[list[dict[str, object]]],
        *,
        issue_owner: str = "rinsakamo",
        issue_state: str = "open",
    ) -> None:
        def run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            if command[-1] == f"repos/rinsakamo/relay-lm/issues/{qualification.OWNER_ISSUE}":
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=json.dumps(
                        {
                            "number": qualification.OWNER_ISSUE,
                            "state": issue_state,
                            "user": {"login": issue_owner},
                        }
                    ),
                    stderr="",
                )
            assert command[-1].endswith(f"issues/{qualification.OWNER_ISSUE}/comments?per_page=100")
            assert "--paginate" in command
            assert "--slurp" not in command
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="\n".join(json.dumps(page) for page in pages),
                stderr="",
            )

        monkeypatch.setattr(qualification.subprocess, "run", run)

    fake_api([[grant]])
    observed = qualification.verify_exact_execution_authority(
        comment_id=1001,
        descriptor_path=descriptor,
        descriptor_sha256=descriptor_hash,
    )
    assert observed["fresh_lookup"] is True
    assert observed["comment_id"] == 1001
    assert observed["owner_issue_state"] == "open"

    stop = {
        "id": 1002,
        "created_at": created_at,
        "user": {"login": "rinsakamo"},
        "body": "STOP #3013",
    }
    fake_api([[grant], [stop]])
    with pytest.raises(qualification.QualificationTargetError, match="revoked"):
        qualification.verify_exact_execution_authority(
            comment_id=1001,
            descriptor_path=descriptor,
            descriptor_sha256=descriptor_hash,
        )

    fake_api([[grant]], issue_owner="different-owner")
    with pytest.raises(qualification.QualificationTargetError, match="owner or open-issue"):
        qualification.verify_exact_execution_authority(
            comment_id=1001,
            descriptor_path=descriptor,
            descriptor_sha256=descriptor_hash,
        )

    fake_api([[grant]], issue_state="closed")
    with pytest.raises(qualification.QualificationTargetError, match="owner or open-issue"):
        qualification.verify_exact_execution_authority(
            comment_id=1001,
            descriptor_path=descriptor,
            descriptor_sha256=descriptor_hash,
        )


def test_descriptor_rejects_model_and_runtime_control_substitution(tmp_path: Path) -> None:
    wrong_model = _descriptor(tmp_path)
    wrong_model["model"] = {"path": str(runtime.MODEL_PATH), "sha256": "0" * 64}
    with pytest.raises(qualification.QualificationTargetError):
        qualification.validate_descriptor(wrong_model)

    wrong_server = _descriptor(tmp_path)
    wrong_server["server_policy"]["swa_full"] = True  # type: ignore[index]
    with pytest.raises(qualification.QualificationTargetError):
        qualification.validate_descriptor(wrong_server)

    wrong_cache = _descriptor(tmp_path)
    wrong_cache["request_policy"]["product_cache_policy"] = "enabled"  # type: ignore[index]
    with pytest.raises(qualification.QualificationTargetError):
        qualification.validate_descriptor(wrong_cache)

    wrong_slot_lifetime = _descriptor(tmp_path)
    wrong_slot_lifetime["server_policy"]["slot_state_within_arm"] = "reset-every-request"  # type: ignore[index]
    with pytest.raises(qualification.QualificationTargetError):
        qualification.validate_descriptor(wrong_slot_lifetime)

    wrong_model_load_ceiling = _descriptor(tmp_path)
    wrong_model_load_ceiling["server_policy"]["candidate_model_load_maximum"] = 3  # type: ignore[index]
    with pytest.raises(qualification.QualificationTargetError):
        qualification.validate_descriptor(wrong_model_load_ceiling)


def test_production_patch_identity_and_cuda_geometry_are_frozen() -> None:
    hashes = runtime.verify_patch_hashes()

    assert hashes["production_patch_sha256"] == (
        "e054a1a6e02567eaa72d56fb3ca4fe29c5f59f6fdd07d7b7618bbb21ba137e18"
    )
    assert runtime.BASE_REVISION == "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"
    assert runtime.PRODUCTION_TREE == "84cf2ff7781a3228e7ff65ec95083a4de6534cec"
    assert hashes["observability_patch_sha256"] == runtime.OBSERVABILITY_PATCH_SHA256
    assert runtime.OBSERVABILITY_TREE == "e05cb0eef33743c73ead9eb0185fb2e1f846a6f5"
    assert "-DGGML_CUDA=ON" in runtime.CMAKE_ARGS
    assert "-DCUDAToolkit_ROOT=/usr/local/cuda-12.8" in runtime.CMAKE_ARGS
    assert "-DCMAKE_CUDA_ARCHITECTURES=86" in runtime.CMAKE_ARGS
    assert "-DGGML_NATIVE=OFF" in runtime.CMAKE_ARGS


def test_candidate_source_and_model_pins_fail_closed() -> None:
    patch_hashes = runtime.verify_patch_hashes()
    source = {
        "revision": runtime.BASE_REVISION,
        "base_tree": runtime.BASE_TREE,
        "production_patch_sha256": runtime.PRODUCTION_PATCH_SHA256,
        "production_repair_tree": runtime.PRODUCTION_TREE,
        "observability_patch_sha256": patch_hashes["observability_patch_sha256"],
        "qualification_observability_tree": runtime.OBSERVABILITY_TREE,
    }
    qualification._validate_candidate_source_identity(source, patch_hashes)

    changed = dict(source)
    changed["production_repair_tree"] = "0" * 40
    with pytest.raises(qualification.QualificationTargetError):
        qualification._validate_candidate_source_identity(changed, patch_hashes)

    runtime.validate_model_identity(model_path=runtime.MODEL_PATH, observed_sha256=runtime.MODEL_SHA256)
    with pytest.raises(runtime.RuntimePinError):
        runtime.validate_model_identity(model_path=runtime.MODEL_PATH, observed_sha256="0" * 64)
    with pytest.raises(runtime.RuntimePinError):
        runtime.validate_model_identity(model_path=Path("/tmp/substitute.gguf"), observed_sha256=runtime.MODEL_SHA256)


def test_cuda_build_configuration_rejects_wrong_toolchain_or_architecture() -> None:
    settings = {
        "CMAKE_BUILD_TYPE": "Release",
        "CMAKE_GENERATOR": "Unix Makefiles",
        "CMAKE_C_COMPILER": "/usr/bin/cc",
        "CMAKE_CUDA_ARCHITECTURES": "86",
        "CMAKE_CUDA_COMPILER": "/usr/local/cuda-12.8/bin/nvcc",
        "CMAKE_CXX_COMPILER": "/usr/bin/c++",
        "CUDAToolkit_ROOT": "/usr/local/cuda-12.8",
        "CUDAToolkit_BIN_DIR": "/usr/local/cuda-12.8/bin",
        "CUDAToolkit_NVCC_EXECUTABLE": "/usr/local/cuda-12.8/bin/nvcc",
        "GGML_CUDA": "ON",
        "GGML_CUDA_FA": "ON",
        "GGML_CUDA_NCCL": "OFF",
        "GGML_CUDA_FA_ALL_QUANTS": "OFF",
        "GGML_CUDA_GRAPHS": "ON",
        "GGML_NATIVE": "OFF",
        "GGML_BACKEND_DL": "OFF",
        "GGML_OPENMP": "OFF",
        "GGML_BLAS": "OFF",
        "LLAMA_BUILD_SERVER": "ON",
        "LLAMA_BUILD_TESTS": "ON",
        "LLAMA_BUILD_EXAMPLES": "OFF",
        "LLAMA_BUILD_UI": "OFF",
        "LLAMA_USE_PREBUILT_UI": "OFF",
        "LLAMA_BUILD_MTMD": "OFF",
        "BUILD_SHARED_LIBS": "ON",
    }
    runtime._validate_cmake_configuration(settings)
    runtime._validate_cuda_architecture_flags(
        'CUDA_FLAGS = "--generate-code=arch=compute_86,code=[compute_86,sm_86]"'
    )
    with pytest.raises(runtime.RuntimePinError):
        runtime._validate_cuda_architecture_flags(
            'CUDA_FLAGS = "--generate-code=arch=compute_89,code=[compute_89,sm_89]"'
        )
    changed = {**settings, "CMAKE_CUDA_ARCHITECTURES": "89"}
    with pytest.raises(runtime.RuntimePinError):
        runtime._validate_cmake_configuration(changed)
    changed_toolkit = {**settings, "CUDAToolkit_ROOT": "/mnt/c/Program Files/CUDA"}
    with pytest.raises(runtime.RuntimePinError):
        runtime._validate_cmake_configuration(changed_toolkit)


def test_candidate_build_environment_excludes_windows_cuda_and_unpinned_flags() -> None:
    environment = runtime.candidate_build_environment(
        {
            "PATH": "/usr/bin:/mnt/c/Program Files/NVIDIA Corporation/CUDA/bin",
            "CUDACXX": "/usr/bin/nvcc",
            "CUDA_HOME": "/tmp/cuda",
            "CMAKE_TOOLCHAIN_FILE": "/tmp/toolchain.cmake",
            "CMAKE_PREFIX_PATH": "/tmp/prefix",
            "CXXFLAGS": "-march=native",
            "LD_LIBRARY_PATH": "/tmp/old-ggml",
            "LD_PRELOAD": "/tmp/preload.so",
            "LD_AUDIT": "/tmp/audit.so",
            "LD_DEBUG": "libs",
            "LD_DEBUG_OUTPUT": "/tmp/loader.log",
            "CPATH": "/tmp/headers",
            "CUDAARCHS": "90",
            "CMAKE_FIND_ROOT_PATH": "/tmp/sysroot",
        }
    )

    assert environment["PATH"].split(":") == [
        "/usr/local/cuda-12.8/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        "/usr/local/sbin",
        "/usr/sbin",
        "/sbin",
    ]
    assert environment["CUDACXX"] == "/usr/local/cuda-12.8/bin/nvcc"
    assert environment["CUDA_HOME"] == "/usr/local/cuda-12.8"
    assert environment["CUDAToolkit_ROOT"] == "/usr/local/cuda-12.8"
    assert "CMAKE_TOOLCHAIN_FILE" not in environment
    assert "CMAKE_PREFIX_PATH" not in environment
    assert "CXXFLAGS" not in environment
    assert "LD_LIBRARY_PATH" not in environment
    assert "LD_PRELOAD" not in environment
    assert "LD_AUDIT" not in environment
    assert "LD_DEBUG" not in environment
    assert "LD_DEBUG_OUTPUT" not in environment
    assert "CPATH" not in environment
    assert "CUDAARCHS" not in environment
    assert "CMAKE_FIND_ROOT_PATH" not in environment


def test_cold_and_reused_treatment_delta_is_exact_and_product_stays_cache_off() -> None:
    body = _wire_body()
    cold, cold_evidence = qualification._prepare_arm_request(
        arm="cold", path="/v1/chat/completions", body=body
    )
    reused, reused_evidence = qualification._prepare_arm_request(
        arm="reused", path="/v1/chat/completions", body=body
    )
    count, count_evidence = qualification._prepare_arm_request(
        arm="reused", path="/v1/chat/completions/input_tokens", body=body
    )

    assert cold == body
    assert cold_evidence["applied"] is False
    assert count == body
    assert count_evidence["applied"] is False
    assert json.loads(body)["cache_prompt"] is False
    reused_payload = json.loads(reused)
    assert reused_payload["cache_prompt"] is True
    assert {key for key in json.loads(body) if json.loads(body)[key] != reused_payload[key]} == {
        "cache_prompt"
    }
    assert reused_evidence["normalized_delta"]["changed_keys"] == ["cache_prompt"]
    qualification._verify_request_treatment(
        arm="cold",
        path="/v1/chat/completions",
        product_body=body,
        upstream_body=cold,
        treatment=cold_evidence,
    )
    qualification._verify_request_treatment(
        arm="reused",
        path="/v1/chat/completions",
        product_body=body,
        upstream_body=reused,
        treatment=reused_evidence,
    )
    altered = json.loads(reused)
    altered["temperature"] = 0.5
    with pytest.raises(qualification.QualificationTargetError):
        qualification._verify_request_treatment(
            arm="reused",
            path="/v1/chat/completions",
            product_body=body,
            upstream_body=json.dumps(altered).encode(),
            treatment=reused_evidence,
        )


def test_pass2_matching_allows_only_the_explicit_pass1_response_dependency() -> None:
    def pass2(response: str, *, fixed_content: str = "constant") -> bytes:
        user = (
            "prefix\n<PASS_1_RESPONSE_JSON>\n"
            + json.dumps({"content": response}, separators=(",", ":"))
            + "\n</PASS_1_RESPONSE_JSON>\n"
            + fixed_content
        )
        return json.dumps(
            {
                "model": "gemma",
                "messages": [
                    {"role": "system", "content": "fixed system"},
                    {"role": "user", "content": user},
                ],
                "cache_prompt": False,
            },
            separators=(",", ":"),
        ).encode()

    left = pass2("first natural language output")
    right = pass2("different natural language output")
    changed_fixed_input = pass2("different natural language output", fixed_content="changed")

    assert qualification._normalize_dynamic_pass2(left, "buffered_pass2") == (
        qualification._normalize_dynamic_pass2(right, "buffered_pass2")
    )
    assert qualification._normalize_dynamic_pass2(left, "buffered_pass2") != (
        qualification._normalize_dynamic_pass2(changed_fixed_input, "buffered_pass2")
    )


def test_pass2_framing_count_is_dynamic_free_and_remains_byte_identical() -> None:
    body = json.dumps(
        {"messages": [{"role": "user", "content": ""}], "cache_prompt": False}
    ).encode()

    normalized = qualification._normalize_dynamic_pass2(body, "buffered_pass2")
    assert json.loads(normalized) == json.loads(body)


def test_provider_request_order_and_required_history_restore_control_are_frozen() -> None:
    expected = list(qualification.transaction.CANONICAL_PROVIDER_SEQUENCE)
    qualification._validate_provider_request_order(expected)
    with pytest.raises(qualification.QualificationTargetError):
        qualification._validate_provider_request_order([*expected[1:], expected[0]])

    markers = qualification._validate_required_history_restore_control(
        "next=8 min=1 swa=16 new=1 restore=1\n"
        "next=24 min=9 swa=16 new=1 restore=1\n"
    )
    assert len(markers) == 2
    with pytest.raises(qualification.QualificationTargetError):
        qualification._validate_required_history_restore_control("restore=0")


def test_loaded_cuda_library_gate_requires_candidate_and_cuda_runtime_paths() -> None:
    qualification._require_cuda_library_set(
        [
            "/candidate/bin/libggml-cuda.so.0",
            "/usr/local/cuda-12.8/lib64/libcudart.so.12",
            "/usr/local/cuda-12.8/lib64/libcublas.so.12",
            "/usr/lib/wsl/lib/libcuda.so.1",
        ]
    )
    with pytest.raises(qualification.QualificationTargetError):
        qualification._require_cuda_library_set(["/candidate/bin/libggml.so.0"])


def test_process_map_parser_preserves_live_device_and_inode_identity(tmp_path: Path) -> None:
    library = tmp_path / "libggml-cuda.so"
    library.write_bytes(b"candidate library")
    record = qualification._parse_mapped_file_record(
        f"7f000000-7f001000 r-xp 00000000 08:2a 12345 {library}"
    )
    assert record == (str(library.resolve()), (8, 42, 12345), False)

    deleted = qualification._parse_mapped_file_record(
        f"7f000000-7f001000 r-xp 00000000 08:2a 12345 {library} (deleted)"
    )
    assert deleted == (str(library.resolve()), (8, 42, 12345), True)
    assert qualification._parse_mapped_file_record(
        "7f000000-7f001000 rw-p 00000000 00:00 0 [heap]"
    ) is None


def _sealed_map_line(path: Path, *, identity: tuple[int, int, int] | None = None, deleted: bool = False) -> str:
    info = path.stat()
    major, minor, inode = identity or (os.major(info.st_dev), os.minor(info.st_dev), info.st_ino)
    suffix = " (deleted)" if deleted else ""
    return f"7f000000-7f001000 r-xp 00000000 {major:x}:{minor:x} {inode} {path}{suffix}"


def _closure_gate_fixture(tmp_path: Path, *, wsl: bool = True) -> tuple[dict[str, object], dict[str, Path]]:
    build = tmp_path / "candidate-build"
    binary_root = build / "bin"
    binary_root.mkdir(parents=True)
    binary = binary_root / "llama-server"
    binary.write_bytes(b"frozen candidate server")
    candidate_lib = binary_root / "libggml-cuda.so.0.23.0"
    candidate_lib.write_bytes(b"frozen candidate ggml cuda")
    llama_lib = binary_root / "libllama.so.0.4.0"
    llama_lib.write_bytes(b"frozen candidate llama")
    cuda_runtime = tmp_path / "cuda" / "libcudart.so.12.8.90"
    cuda_runtime.parent.mkdir()
    cuda_runtime.write_bytes(b"frozen CUDA toolkit runtime")
    cublas = tmp_path / "cuda" / "libcublas.so.12.8.5.5"
    cublas.write_bytes(b"frozen CUDA toolkit cuBLAS")

    objects: dict[str, Path] = {
        "binary": binary,
        "ggml": candidate_lib,
        "llama": llama_lib,
        "cudart": cuda_runtime,
        "cublas": cublas,
    }
    dependencies: dict[str, object] = {
        path.name: runtime._sealed_file_record(path)
        for path in (candidate_lib, llama_lib, cuda_runtime, cublas)
    }
    wsl_closure: dict[str, object] | None = None
    if wsl:
        wsl_lib = tmp_path / "usr" / "lib" / "wsl" / "lib"
        wsl_lib.mkdir(parents=True)
        shim = wsl_lib / "libcuda.so"
        shim.write_bytes(b"wsl CUDA guest shim")
        os.link(shim, wsl_lib / "libcuda.so.1")
        os.link(shim, wsl_lib / "libcuda.so.1.1")
        driver_root = tmp_path / "usr" / "lib" / "wsl" / "drivers"
        package = driver_root / "nvmdi.inf_amd64_0123456789abcdef"
        package.mkdir(parents=True)
        loader_copy = package / "libcuda_loader.so"
        loader_copy.write_bytes(shim.read_bytes())
        driver_payload = package / "libcuda.so.1.1"
        driver_payload.write_bytes(b"distinct host NVIDIA CUDA driver payload")
        objects.update(
            {
                "shim": wsl_lib / "libcuda.so.1",
                "loader_copy": loader_copy,
                "driver_payload": driver_payload,
            }
        )
        dependencies["libcuda.so.1"] = runtime._sealed_file_record(wsl_lib / "libcuda.so.1")
        shim_aliases = [runtime._sealed_file_record(path) for path in sorted(wsl_lib.glob("libcuda.so*"))]
        accepted = [
            {
                **record,
                "role": "wsl-cuda-shim-alias",
                "relation": "same-device-inode-hardlink-alias",
            }
            for record in shim_aliases
        ]
        payload_record = runtime._sealed_file_record(driver_payload)
        accepted.append(
            {
                **payload_record,
                "role": "nvidia-wsl-user-mode-driver-payload",
                "relation": "distinct-driver-payload-in-the-sealed-wsl-package",
            }
        )
        wsl_closure = {
            "schema_version": 1,
            "contract": "wsl-cuda-driver-shim-and-package-payload-v1",
            "logical_dependency": "libcuda.so.1",
            "driver_package": {"payload": {**payload_record, "soname": "libcuda.so.1"}},
            "accepted_mapped_objects": accepted,
        }

    root_record = runtime._sealed_file_record(binary)
    libraries = {
        str(binary.resolve()): {
            "sha256": root_record["sha256"],
            "identity": root_record["identity"],
            "dependencies": dependencies,
        }
    }
    manifest: dict[str, object] = {
        "server": {"sha256": root_record["sha256"], "identity": root_record["identity"]},
        "build": {
            "shared_libraries": libraries,
            "wsl_cuda_driver_closure": wsl_closure,
        },
    }
    return manifest, objects


def _verify_fixture_maps(
    monkeypatch: pytest.MonkeyPatch,
    manifest: dict[str, object],
    objects: dict[str, Path],
    mapped_paths: list[Path],
    *,
    require_cuda: bool = False,
    previous_attestation: dict[str, object] | None = None,
    overrides: dict[Path, tuple[int, int, int]] | None = None,
    deleted: set[Path] | None = None,
) -> dict[str, object]:
    pid = 424242
    maps_path = Path(f"/proc/{pid}/maps")
    lines = [
        _sealed_map_line(
            path,
            identity=(overrides or {}).get(path),
            deleted=path in (deleted or set()),
        )
        for path in mapped_paths
    ]
    maps_text = "\n".join(lines) + "\n"
    original_is_file = Path.is_file
    original_read_text = Path.read_text

    def fake_is_file(path: Path) -> bool:
        return True if path == maps_path else original_is_file(path)

    def fake_read_text(path: Path, *args: object, **kwargs: object) -> str:
        return maps_text if path == maps_path else original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "is_file", fake_is_file)
    monkeypatch.setattr(Path, "read_text", fake_read_text)
    monkeypatch.setattr(qualification, "_process_start_ticks", lambda observed_pid: 77)
    return qualification._verify_loaded_library_closure(
        process=SimpleNamespace(pid=pid),
        binary=objects["binary"],
        manifest=manifest,
        require_cuda=require_cuda,
        previous_attestation=previous_attestation,
    )


def test_wsl_cuda_driver_closure_records_the_observed_two_object_topology(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    lib_root = tmp_path / "usr" / "lib" / "wsl" / "lib"
    lib_root.mkdir(parents=True)
    shim = lib_root / "libcuda.so"
    shim.write_bytes(b"wsl shim bytes")
    os.link(shim, lib_root / "libcuda.so.1")
    os.link(shim, lib_root / "libcuda.so.1.1")
    driver_root = tmp_path / "usr" / "lib" / "wsl" / "drivers"
    package = driver_root / "nvmdi.inf_amd64_0123456789abcdef"
    package.mkdir(parents=True)
    loader_copy = package / "libcuda_loader.so"
    loader_copy.write_bytes(shim.read_bytes())
    payload = package / "libcuda.so.1.1"
    payload.write_bytes(b"different driver payload bytes")
    (package / "nvmdi.inf").write_text(
        "[Version]\nDriverVer=12/02/2025,32.0.15.9144\n", encoding="utf-8"
    )
    mountinfo = tmp_path / "mountinfo"
    mountinfo.write_text(
        f"58 62 0:36 / {driver_root} ro,nosuid,nodev - 9p drivers ro,access=client\n"
        f"67 62 0:41 / {lib_root} rw,nosuid,nodev - overlay none rw,lowerdir=/gpu_lib_packaged\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        runtime,
        "run_text",
        lambda *args, **kwargs: "0x000000000000000e (SONAME) Library soname: [libcuda.so.1]",
    )
    real_stat_identity = runtime._stat_identity

    def observed_wsl_identity(path: Path) -> dict[str, int]:
        identity = real_stat_identity(path)
        if path.parent == lib_root:
            identity["device"] = 44
            identity["inode"] = 5348024557713090
            identity["links"] = 4
        elif path == loader_copy:
            identity["device"] = 36
            identity["inode"] = 5348024557713090
            identity["links"] = 4
        elif path == payload:
            identity["device"] = 36
            identity["inode"] = 6755399441257569
            identity["links"] = 1
        return identity

    monkeypatch.setattr(runtime, "_stat_identity", observed_wsl_identity)
    closure_input = {
        "/candidate/libggml-cuda.so": {
            "dependencies": {
                "libcuda.so.1": runtime._sealed_file_record(lib_root / "libcuda.so.1")
            }
        }
    }

    sealed = runtime.collect_wsl_cuda_driver_closure(
        closure_input,
        wsl_lib_root=lib_root,
        wsl_driver_root=driver_root,
        mountinfo_path=mountinfo,
    )

    assert sealed is not None
    assert sealed["contract"] == "wsl-cuda-driver-shim-and-package-payload-v1"
    assert sealed["driver_package"]["inf"]["driver_version"] == "32.0.15.9144"
    assert sealed["driver_package"]["payload"]["soname"] == "libcuda.so.1"
    assert sealed["shim"]["identity"]["device"] == 44
    assert sealed["driver_package"]["loader_copy"]["identity"]["device"] == 36
    assert sealed["driver_package"]["loader_copy"]["identity"]["inode"] == sealed["shim"]["identity"]["inode"]
    assert sealed["driver_package"]["payload"]["identity"]["device"] == 36
    assert sealed["driver_package"]["payload"]["identity"]["inode"] == 6755399441257569
    assert len(sealed["shim"]["aliases"]) == 3
    assert sealed["shim"]["sha256"] == runtime.sha256_file(loader_copy)
    assert sealed["driver_package"]["payload"]["sha256"] != sealed["shim"]["sha256"]
    assert sealed["driver_package"]["payload"]["identity"]["inode"] != sealed["shim"]["identity"]["inode"]
    assert {item["path"] for item in sealed["accepted_mapped_objects"]} == {
        str(lib_root / "libcuda.so"),
        str(lib_root / "libcuda.so.1"),
        str(lib_root / "libcuda.so.1.1"),
        str(payload),
    }

    ambiguous_package = driver_root / "nvmdi.inf_amd64_fedcba9876543210"
    ambiguous_package.mkdir()
    (ambiguous_package / "libcuda.so.1.1").write_bytes(b"second driver payload")
    with pytest.raises(runtime.RuntimePinError, match="ambiguous libcuda payload"):
        runtime.collect_wsl_cuda_driver_closure(
            closure_input,
            wsl_lib_root=lib_root,
            wsl_driver_root=driver_root,
            mountinfo_path=mountinfo,
        )


def test_loaded_closure_accepts_only_exact_sealed_wsl_objects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest, objects = _closure_gate_fixture(tmp_path)
    paths = [objects[name] for name in ("binary", "ggml", "llama", "cudart", "cublas", "shim", "driver_payload")]

    result = _verify_fixture_maps(monkeypatch, manifest, objects, paths, require_cuda=True)

    assert result["loaded_closure_matches_manifest"] is True
    assert str(objects["driver_payload"]) in result["wsl_cuda_driver_objects"]
    assert str(objects["driver_payload"]) in result["loaded_libraries"]


@pytest.mark.parametrize("copy_identical", [False, True])
def test_same_basename_or_identical_copy_at_unsealed_path_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    copy_identical: bool,
) -> None:
    manifest, objects = _closure_gate_fixture(tmp_path)
    original = objects["driver_payload"]
    unsealed = tmp_path / "unsealed" / "libcuda.so.1.1"
    unsealed.parent.mkdir()
    unsealed.write_bytes(original.read_bytes() if copy_identical else b"other driver revision")

    with pytest.raises(qualification.QualificationTargetError, match="undeclared library"):
        _verify_fixture_maps(monkeypatch, manifest, objects, [objects["binary"], unsealed])


def test_unobserved_package_loader_copy_is_not_an_accepted_runtime_alias(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest, objects = _closure_gate_fixture(tmp_path)

    with pytest.raises(qualification.QualificationTargetError, match="undeclared library"):
        _verify_fixture_maps(
            monkeypatch,
            manifest,
            objects,
            [objects["binary"], objects["loader_copy"]],
        )


def test_loaded_closure_rejects_changed_digest_and_changed_sealed_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest, objects = _closure_gate_fixture(tmp_path)
    payload = objects["driver_payload"]
    payload.write_bytes(b"mutated driver payload with same path")
    with pytest.raises(qualification.QualificationTargetError, match="object identity changed"):
        _verify_fixture_maps(monkeypatch, manifest, objects, [objects["binary"], payload])

    manifest, objects = _closure_gate_fixture(tmp_path / "digest")
    payload = objects["driver_payload"]
    payload.write_bytes(b"changed digest while preserving the sealed path")
    changed_identity = runtime._stat_identity(payload)
    wsl_closure = manifest["build"]["wsl_cuda_driver_closure"]
    for item in wsl_closure["accepted_mapped_objects"]:
        if item["path"] == str(payload):
            item["identity"] = changed_identity
    wsl_closure["driver_package"]["payload"]["identity"] = changed_identity
    with pytest.raises(qualification.QualificationTargetError, match="digest is outside"):
        _verify_fixture_maps(monkeypatch, manifest, objects, [objects["binary"], payload])

    manifest, objects = _closure_gate_fixture(tmp_path / "second")
    payload = objects["driver_payload"]
    replacement = payload.with_suffix(".replacement")
    replacement.write_bytes(payload.read_bytes())
    payload.unlink()
    replacement.rename(payload)
    with pytest.raises(qualification.QualificationTargetError, match="object identity changed"):
        _verify_fixture_maps(monkeypatch, manifest, objects, [objects["binary"], payload])


def test_loaded_closure_rejects_map_inode_device_drift_and_deleted_mapping(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest, objects = _closure_gate_fixture(tmp_path)
    payload = objects["driver_payload"]
    info = payload.stat()
    wrong_identity = (os.major(info.st_dev) + 1, os.minor(info.st_dev), info.st_ino)
    with pytest.raises(qualification.QualificationTargetError, match="mapping no longer names"):
        _verify_fixture_maps(
            monkeypatch,
            manifest,
            objects,
            [objects["binary"], payload],
            overrides={payload: wrong_identity},
        )
    with pytest.raises(qualification.QualificationTargetError, match="deleted executable or library"):
        _verify_fixture_maps(
            monkeypatch,
            manifest,
            objects,
            [objects["binary"], payload],
            deleted={payload},
        )


def test_previous_process_map_attestation_rejects_deleted_driver_mapping(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest, objects = _closure_gate_fixture(tmp_path)
    first_paths = [objects[name] for name in ("binary", "ggml", "llama", "cudart", "cublas", "shim", "driver_payload")]
    first = _verify_fixture_maps(monkeypatch, manifest, objects, first_paths, require_cuda=True)
    second_paths = [path for path in first_paths if path != objects["driver_payload"]]

    with pytest.raises(qualification.QualificationTargetError, match="mapping changed after attestation"):
        _verify_fixture_maps(
            monkeypatch,
            manifest,
            objects,
            second_paths,
            require_cuda=True,
            previous_attestation=first,
        )


def test_unsealed_candidate_shared_object_and_mixed_build_paths_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest, objects = _closure_gate_fixture(tmp_path)
    rogue_ggml = tmp_path / "other-build" / "libggml-cuda.so.0.23.0"
    rogue_ggml.parent.mkdir()
    rogue_ggml.write_bytes(objects["ggml"].read_bytes())
    with pytest.raises(qualification.QualificationTargetError, match="undeclared library"):
        _verify_fixture_maps(
            monkeypatch,
            manifest,
            objects,
            [objects["binary"], objects["ggml"], rogue_ggml],
        )
    rogue_llama = tmp_path / "other-build" / "libllama.so.0.4.0"
    rogue_llama.write_bytes(objects["llama"].read_bytes())
    with pytest.raises(qualification.QualificationTargetError, match="undeclared library"):
        _verify_fixture_maps(
            monkeypatch,
            manifest,
            objects,
            [objects["binary"], objects["llama"], rogue_llama],
        )


def test_non_wsl_closure_keeps_exact_path_behavior(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest, objects = _closure_gate_fixture(tmp_path, wsl=False)
    normal_cuda = tmp_path / "native" / "libcuda.so.1"
    normal_cuda.parent.mkdir()
    normal_cuda.write_bytes(b"native Linux CUDA driver")
    root = manifest["build"]["shared_libraries"]
    root[str(objects["binary"].resolve())]["dependencies"]["libcuda.so.1"] = runtime._sealed_file_record(normal_cuda)
    native_paths = [
        objects["binary"],
        objects["ggml"],
        objects["llama"],
        objects["cudart"],
        objects["cublas"],
        normal_cuda,
    ]

    result = _verify_fixture_maps(monkeypatch, manifest, objects, native_paths, require_cuda=True)
    assert result["loaded_closure_matches_manifest"] is True

    alias = tmp_path / "native-alias" / "libcuda.so.1"
    alias.parent.mkdir()
    os.link(normal_cuda, alias)
    with pytest.raises(qualification.QualificationTargetError, match="undeclared library"):
        _verify_fixture_maps(monkeypatch, manifest, objects, [objects["binary"], alias])


def test_wsl_manifest_collection_rejects_symlink_alias(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    lib_root = tmp_path / "usr" / "lib" / "wsl" / "lib"
    lib_root.mkdir(parents=True)
    target = lib_root / "libcuda.real"
    target.write_bytes(b"shim")
    (lib_root / "libcuda.so.1").symlink_to(target)
    driver_root = tmp_path / "usr" / "lib" / "wsl" / "drivers"
    package = driver_root / "nvmdi.inf_amd64_0123456789abcdef"
    package.mkdir(parents=True)
    (package / "libcuda_loader.so").write_bytes(b"shim")
    payload = package / "libcuda.so.1.1"
    payload.write_bytes(b"payload")
    (package / "nvmdi.inf").write_text("DriverVer=1/1/2026,1.0\n", encoding="utf-8")
    mountinfo = tmp_path / "mountinfo"
    mountinfo.write_text(
        f"1 0 0:1 / {driver_root} ro - 9p drivers ro\n2 0 0:2 / {lib_root} rw - overlay none rw\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime, "run_text", lambda *args, **kwargs: "SONAME [libcuda.so.1]")
    closure_input = {
        "/candidate/libggml-cuda.so": {
            "dependencies": {"libcuda.so.1": runtime._sealed_file_record(lib_root / "libcuda.so.1")}
        }
    }
    with pytest.raises(runtime.RuntimePinError, match="regular path"):
        runtime.collect_wsl_cuda_driver_closure(
            closure_input,
            wsl_lib_root=lib_root,
            wsl_driver_root=driver_root,
            mountinfo_path=mountinfo,
        )


def test_sealed_wsl_path_replaced_by_symlink_fails_even_when_target_is_same_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest, objects = _closure_gate_fixture(tmp_path)
    payload = objects["driver_payload"]
    alias = tmp_path / "same-object-alias" / payload.name
    alias.parent.mkdir()
    os.link(payload, alias)
    payload.unlink()
    payload.symlink_to(alias)

    with pytest.raises(
        qualification.QualificationTargetError,
        match="not canonical|no longer a direct regular file",
    ):
        _verify_fixture_maps(
            monkeypatch,
            manifest,
            objects,
            [objects["binary"], payload],
            require_cuda=True,
        )


def test_process_map_symlink_alias_path_is_not_canonicalized_into_sealed_membership(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest, objects = _closure_gate_fixture(tmp_path)
    alias = tmp_path / "runtime-only-alias" / "libcuda.so.1.1"
    alias.parent.mkdir()
    alias.symlink_to(objects["driver_payload"])

    with pytest.raises(qualification.QualificationTargetError, match="undeclared library"):
        _verify_fixture_maps(
            monkeypatch,
            manifest,
            objects,
            [objects["binary"], alias],
            require_cuda=True,
        )


def test_symlink_target_change_after_sealing_cannot_match_old_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest, objects = _closure_gate_fixture(tmp_path)
    alias = tmp_path / "mapped-libcuda.so.1.1"
    alias.symlink_to(objects["driver_payload"])
    second_target = tmp_path / "other-driver.so.1.1"
    second_target.write_bytes(b"different payload")
    alias.unlink()
    alias.symlink_to(second_target)
    with pytest.raises(qualification.QualificationTargetError, match="undeclared library"):
        _verify_fixture_maps(monkeypatch, manifest, objects, [objects["binary"], alias])


def test_bind_visible_hardlink_alias_cannot_evade_sealed_path_membership(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest, objects = _closure_gate_fixture(tmp_path)
    alias = tmp_path / "bind-visible" / "libcuda.so.1.1"
    alias.parent.mkdir()
    os.link(objects["driver_payload"], alias)
    assert alias.stat().st_dev == objects["driver_payload"].stat().st_dev
    assert alias.stat().st_ino == objects["driver_payload"].stat().st_ino

    with pytest.raises(qualification.QualificationTargetError, match="undeclared library"):
        _verify_fixture_maps(monkeypatch, manifest, objects, [objects["binary"], alias])


def test_candidate_source_regression_binaries_are_hash_pinned(tmp_path: Path) -> None:
    build_root = tmp_path / "build"
    binary_root = build_root / "bin"
    binary_root.mkdir(parents=True)
    test_binaries: dict[str, dict[str, str]] = {}
    for name in runtime.BUILD_TARGETS[1:]:
        path = binary_root / name
        path.write_bytes(f"pinned:{name}".encode())
        path.chmod(0o700)
        test_binaries[name] = {"path": str(path.resolve()), "sha256": runtime.sha256_file(path)}

    manifest = {"build": {"build_root": str(build_root), "test_binaries": test_binaries}}
    qualification._verify_candidate_test_binaries(manifest)
    (binary_root / "test-chat").write_bytes(b"changed regression binary")

    with pytest.raises(qualification.QualificationTargetError, match="binary changed"):
        qualification._verify_candidate_test_binaries(manifest)


def test_live_gpu_identity_is_matched_to_candidate_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = "NVIDIA GeForce RTX 3060, GPU-test, 591.44, 12288 MiB, 8.6"
    monkeypatch.setattr(runtime, "run_text", lambda *_args, **_kwargs: expected)
    qualification._verify_live_gpu_identity({"build": {"gpu": expected}})

    monkeypatch.setattr(runtime, "run_text", lambda *_args, **_kwargs: "different GPU")
    with pytest.raises(qualification.QualificationTargetError, match="identity differs"):
        qualification._verify_live_gpu_identity({"build": {"gpu": expected}})


def test_startup_argv_freezes_one_slot_full_context_and_checkpointing() -> None:
    manifest = {
        "server": {
            "startup_argv_template": [
                "/candidate/bin/llama-server",
                "-m",
                str(runtime.MODEL_PATH),
                "--host",
                "127.0.0.1",
                "--port",
                "<descriptor-port>",
                "-ngl",
                "999",
                "-c",
                "8192",
                "-np",
                "1",
                "--no-context-shift",
                "-lv",
                "4",
                "--log-file",
                "<arm-evidence-root>/llama-server.log",
            ]
        }
    }
    argv = qualification._expected_server_argv(
        manifest=manifest,
        port=1234,
        arm_root=Path("/tmp/cold").resolve(),
    )
    assert argv[argv.index("--port") + 1] == "1234"
    assert argv[argv.index("-np") + 1] == "1"
    assert "--no-context-shift" in argv
    assert "--swa-full" not in argv
    assert "--no-checkpoints" not in argv


def test_durable_request_record_is_fsynced_consumes_one_request_and_stops_after_error(
    tmp_path: Path,
) -> None:
    gate_calls: list[str] = []
    journal = qualification.DurableRequestJournal(
        root=tmp_path / "journal",
        arm="cold",
        before_send=lambda: gate_calls.append("fresh-authority-checked"),
    )
    body = _wire_body()
    entry = {
        "call_index": 1,
        "kind": "generation",
        "generation_index": 1,
        "phase": "buffered_pass1",
    }
    record = journal.durable_record(
        entry=entry,
        path="/v1/chat/completions",
        product_body=body,
        upstream_body=body,
        treatment={"applied": False},
    )

    assert gate_calls == ["fresh-authority-checked"]
    assert journal.attempt_consumed is True
    assert Path(record["product_body_path"]).read_bytes() == body
    assert Path(record["upstream_body_path"]).read_bytes() == body
    assert json.loads((Path(record["product_body_path"]).parent / "durable-record.json").read_text())[
        "durable_before_send"
    ] is True
    journal.mark_send_attempted(record)
    journal.stop(reason="upstream socket failure", request_id=record["request_id"])
    with pytest.raises(qualification.QualificationTargetError):
        journal.ensure_send_allowed()

    evidence = journal.evidence()
    assert evidence["durable_request_count"] == 1
    assert evidence["attempt_consumed"] is True
    assert evidence["first_failure"]["automatic_retry"] is False
    assert evidence["first_failure"]["later_arm_started"] is False


def test_pre_send_authority_failure_does_not_consume_a_model_facing_request(
    tmp_path: Path,
) -> None:
    journal = qualification.DurableRequestJournal(
        root=tmp_path / "journal",
        arm="cold",
        before_send=lambda: (_ for _ in ()).throw(
            qualification.QualificationTargetError("authority unavailable")
        ),
    )
    with pytest.raises(qualification.QualificationTargetError):
        journal.durable_record(
            entry={"call_index": 1, "kind": "generation"},
            path="/v1/chat/completions",
            product_body=_wire_body(),
            upstream_body=_wire_body(),
            treatment={"applied": False},
        )

    journal.stop(reason="authority unavailable")
    assert journal.attempt_consumed is False
    assert journal.evidence()["durable_request_count"] == 0


def test_failure_after_durable_record_consumes_once_and_blocks_next_request(
    tmp_path: Path,
) -> None:
    checks = 0

    def gate() -> None:
        nonlocal checks
        checks += 1
        if checks == 2:
            raise qualification.QualificationTargetError("fresh authority changed before send")

    journal = qualification.DurableRequestJournal(
        root=tmp_path / "journal",
        arm="cold",
        before_send=gate,
    )
    record = journal.durable_record(
        entry={"call_index": 1, "kind": "generation", "phase": "buffered_pass1"},
        path="/v1/chat/completions",
        product_body=_wire_body(),
        upstream_body=_wire_body(),
        treatment={"applied": False},
    )
    journal.mark_send_attempted(record)
    with pytest.raises(qualification.QualificationTargetError):
        journal.recheck_before_send()
    journal.stop(reason="authority changed before send", request_id=record["request_id"])

    assert journal.attempt_consumed is True
    assert journal.evidence()["durable_request_count"] == 1
    assert journal.evidence()["first_failure"]["automatic_retry"] is False
    with pytest.raises(qualification.QualificationTargetError):
        journal.durable_record(
            entry={"call_index": 2, "kind": "generation"},
            path="/v1/chat/completions",
            product_body=_wire_body(),
            upstream_body=_wire_body(),
            treatment={"applied": False},
        )


@pytest.mark.parametrize(
    ("path", "headers", "expected_status"),
    [
        ("/unexpected", {}, 404),
        ("/v1/chat/completions", {"Content-Length": "-1"}, 413),
    ],
)
def test_malformed_proxy_request_stops_the_arm_without_consuming_a_post(
    tmp_path: Path,
    path: str,
    headers: dict[str, str],
    expected_status: int,
) -> None:
    class RejectLedger:
        def __init__(self) -> None:
            self.rejections: list[dict[str, object]] = []

        def reject(self, *, path: str, body: bytes, reason: str) -> None:
            self.rejections.append({"path": path, "body": body, "reason": reason})

    journal = qualification.DurableRequestJournal(
        root=tmp_path / "journal",
        arm="cold",
        before_send=lambda: None,
    )
    ledger = RejectLedger()
    handler = object.__new__(qualification._DurableTreatmentHandler)
    handler.server = SimpleNamespace(journal=journal, ledger=ledger)
    handler.path = path
    handler.headers = headers
    observed_status: list[int] = []
    handler.send_error = observed_status.append

    handler.do_POST()

    assert observed_status == [expected_status]
    assert len(ledger.rejections) == 1
    assert journal.stopped is True
    assert journal.attempt_consumed is False
    assert journal.evidence()["durable_request_count"] == 0


def test_candidate_server_environment_strips_inherited_llama_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LLAMA_ARG_SWA_FULL", "1")
    monkeypatch.setenv("GGML_CUDA_ENABLE_UNIFIED_MEMORY", "1")
    monkeypatch.setenv("LD_PRELOAD", "/tmp/old-runtime.so")
    environment = qualification._candidate_server_environment(
        {"build": {"build_root": str(tmp_path), "gpu": "RTX 3060, GPU-frozen"}}
    )

    assert "LLAMA_ARG_SWA_FULL" not in environment
    assert "GGML_CUDA_ENABLE_UNIFIED_MEMORY" not in environment
    assert "LD_PRELOAD" not in environment
    assert environment["CUDA_VISIBLE_DEVICES"] == "GPU-frozen"
    assert environment["LD_LIBRARY_PATH"].split(qualification.os.pathsep)[0] == str(
        (tmp_path / "bin").resolve()
    )


def test_failure_and_attempt_identifiers_cannot_replay_retry_reseed_or_fallback() -> None:
    assert qualification.ATTEMPT_ID.endswith("-20260927-a")
    assert qualification.GENERATION_MAXIMUM == 8
    assert qualification.INPUT_COUNT_MAXIMUM == 24
    assert qualification.MODEL_FACING_MAXIMUM == 32
    assert qualification.FORBIDDEN_IDENTIFIERS >= {
        "diagnostic:3006-projection-provenance",
        "v1:llama-cpp-cache-correctness-reproducer",
        "relay-self:#259",
    }


def test_shared_library_closure_parser_fails_on_unresolved_dependency() -> None:
    parsed = runtime.parse_ldd_closure(
        "libllama.so => /opt/candidate/libllama.so (0x1234)\n"
        "libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0xabcd)\n"
        "linux-vdso.so.1 (0x9876)\n"
    )
    assert parsed["libllama.so"] == "/opt/candidate/libllama.so"
    with pytest.raises(runtime.RuntimePinError):
        runtime.parse_ldd_closure("libold.so => not found\n")


def test_evidence_seal_detects_tampering(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    root.mkdir()
    (root / "record.json").write_text('{"sealed":true}\n', encoding="utf-8")

    qualification._seal_directory(root)
    verified = qualification.verify_evidence_manifest(root)
    assert verified["file_count"] == 1

    (root / "record.json").write_text('{"sealed":false}\n', encoding="utf-8")
    with pytest.raises(qualification.QualificationTargetError):
        qualification.verify_evidence_manifest(root)


def test_materialization_observer_validates_full_state_schema_without_payloads(
    tmp_path: Path,
) -> None:
    profile_root = tmp_path / "profile"
    memory_root = profile_root / "memory"
    memory_root.mkdir(parents=True)
    (memory_root / "state.json").write_text(
        '{"format_version":1,"states":[]}', encoding="utf-8"
    )
    profile = SimpleNamespace(
        name="installed-buffered",
        package=SimpleNamespace(root=profile_root),
        continuity_runtime=None,
    )
    observer = qualification_serve._MaterializationObserver(
        app=None,
        profiles=SimpleNamespace(profiles=[profile]),
        output_path=tmp_path / "observer.json",
    )

    observed = observer._profile_observations()["installed-buffered"]
    assert observed["state_file_present"] is True
    assert observed["state_schema_valid"] is True
    assert observed["state_record_count"] == 0
    assert "states" not in observer.output_path.read_text(encoding="utf-8")

    (memory_root / "state.json").write_text(
        '{"format_version":2,"states":[]}', encoding="utf-8"
    )
    observed = observer._profile_observations()["installed-buffered"]
    assert observed["state_schema_valid"] is False

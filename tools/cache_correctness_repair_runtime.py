"""Pinned CUDA build and runtime identity for the #3013 candidate.

The builder uses a fresh private clone of an exact clean llama.cpp source
checkout, applies the frozen #3006 production patch and the #3013 trace-only
observability patch, then builds the CUDA server. It never starts the server or
loads a model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from typing import Any


BASE_REVISION = "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"
BASE_TREE = "6d39fd93dc91fc0a4bc86dffe9782d4f26318004"
PRODUCTION_PATCH_SHA256 = "e054a1a6e02567eaa72d56fb3ca4fe29c5f59f6fdd07d7b7618bbb21ba137e18"
PRODUCTION_TREE = "84cf2ff7781a3228e7ff65ec95083a4de6534cec"
OBSERVABILITY_PATCH_SHA256 = "84df09168eea2299bbb1c73be051a08f426a866b1428b95a6a1f0416050c54e3"
OBSERVABILITY_TREE = "e05cb0eef33743c73ead9eb0185fb2e1f846a6f5"
MODEL_PATH = Path("/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf")
MODEL_SHA256 = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
UPSTREAM_REPOSITORY = "https://github.com/ggml-org/llama.cpp.git"
GPU_QUERY_COMMAND = (
    "/usr/lib/wsl/lib/nvidia-smi",
    "--query-gpu=name,uuid,driver_version,memory.total,compute_cap",
    "--format=csv,noheader",
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_PATCH_PATH = REPOSITORY_ROOT / "tools/patches/cache-correctness/relaylm-3006-frozen-repair.patch"
OBSERVABILITY_PATCH_PATH = REPOSITORY_ROOT / "tools/patches/cache-correctness/relaylm-3013-trace-observability.patch"

CMAKE_ARGS = (
    "-DCMAKE_BUILD_TYPE=Release",
    "-DCMAKE_C_COMPILER=/usr/bin/cc",
    "-DCMAKE_CXX_COMPILER=/usr/bin/c++",
    "-DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.8/bin/nvcc",
    "-DCMAKE_CUDA_ARCHITECTURES=86",
    "-DCUDAToolkit_ROOT=/usr/local/cuda-12.8",
    "-DBUILD_SHARED_LIBS=ON",
    "-DGGML_CUDA=ON",
    "-DGGML_CUDA_NCCL=OFF",
    "-DGGML_CUDA_FA=ON",
    "-DGGML_CUDA_FA_ALL_QUANTS=OFF",
    "-DGGML_CUDA_GRAPHS=ON",
    "-DGGML_NATIVE=OFF",
    "-DGGML_BACKEND_DL=OFF",
    "-DGGML_OPENMP=OFF",
    "-DGGML_BLAS=OFF",
    "-DLLAMA_OPENSSL=OFF",
    "-DLLAMA_BUILD_TESTS=ON",
    "-DLLAMA_BUILD_SERVER=ON",
    "-DLLAMA_BUILD_EXAMPLES=OFF",
    "-DLLAMA_BUILD_UI=OFF",
    "-DLLAMA_USE_PREBUILT_UI=OFF",
    "-DLLAMA_BUILD_MTMD=OFF",
)
BUILD_TARGETS = ("llama-server", "test-chat", "test-batch-alloc", "test-arg-parser")
PATCHED_SOURCE_PATHS = (
    "tests/test-chat.cpp",
    "tools/server/server-common.h",
    "tools/server/server-context.cpp",
)


class RuntimePinError(RuntimeError):
    """The exact patched CUDA candidate cannot be identified safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_model_identity(*, model_path: Path, observed_sha256: str) -> None:
    if model_path.expanduser().resolve() != MODEL_PATH.resolve():
        raise RuntimePinError("candidate build must use the exact #3013 Gemma 4 Q4_K_M model path")
    if observed_sha256 != MODEL_SHA256:
        raise RuntimePinError("canonical Gemma 4 model SHA256 mismatch")


def run_text(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=None if env is None else dict(env),
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimePinError(f"command failed: {shlex.join(command)}: {detail}")
    return (completed.stdout or completed.stderr).strip()


def git_value(source_root: Path, *args: str) -> str:
    return run_text(["git", "-C", str(source_root), *args])


def verify_patch_hashes(
    *,
    production_patch: Path = PRODUCTION_PATCH_PATH,
    observability_patch: Path = OBSERVABILITY_PATCH_PATH,
) -> dict[str, str]:
    production_hash = sha256_file(production_patch)
    if production_hash != PRODUCTION_PATCH_SHA256:
        raise RuntimePinError("frozen #3006 production repair patch hash mismatch")
    observability_hash = sha256_file(observability_patch)
    if observability_hash != OBSERVABILITY_PATCH_SHA256:
        raise RuntimePinError("#3013 runtime observability patch hash mismatch")
    return {
        "production_patch_sha256": production_hash,
        "observability_patch_sha256": observability_hash,
    }


def verify_clean_base(source_root: Path) -> dict[str, str]:
    revision = git_value(source_root, "rev-parse", "HEAD")
    tree = git_value(source_root, "rev-parse", "HEAD^{tree}")
    status = git_value(source_root, "status", "--porcelain")
    if revision != BASE_REVISION or tree != BASE_TREE or status:
        raise RuntimePinError("source checkout is not a clean exact #3006 frozen base")
    return {"revision": revision, "tree": tree}


def verify_qualification_source_tree(source_root: Path) -> dict[str, str]:
    revision = git_value(source_root, "rev-parse", "HEAD")
    tree = git_value(source_root, "write-tree")
    status = git_value(source_root, "status", "--porcelain")
    staged_paths = tuple(git_value(source_root, "diff", "--cached", "--name-only").splitlines())
    expected_status = tuple(f"M  {path}" for path in PATCHED_SOURCE_PATHS)
    if (
        revision != BASE_REVISION
        or tree != OBSERVABILITY_TREE
        or git_value(source_root, "diff")
        or staged_paths != PATCHED_SOURCE_PATHS
        or tuple(status.splitlines()) != expected_status
    ):
        raise RuntimePinError("patched source checkout has drifted from the frozen qualification tree")
    return {"revision": revision, "tree": tree}


def cmake_configure_command(source_root: Path, build_root: Path) -> list[str]:
    return [
        "cmake",
        "-G",
        "Unix Makefiles",
        "-S",
        str(source_root),
        "-B",
        str(build_root),
        *CMAKE_ARGS,
    ]


def candidate_build_environment(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Pin CUDA discovery to the Linux toolkit, excluding Windows PATH entries."""
    source = os.environ if environ is None else environ
    environment = dict(source)
    environment["PATH"] = os.pathsep.join(
        (
            "/usr/local/cuda-12.8/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/local/sbin",
            "/usr/sbin",
            "/sbin",
        )
    )
    environment["CC"] = "/usr/bin/cc"
    environment["CXX"] = "/usr/bin/c++"
    environment["CUDACXX"] = "/usr/local/cuda-12.8/bin/nvcc"
    environment["CUDA_HOME"] = "/usr/local/cuda-12.8"
    environment["CUDA_PATH"] = "/usr/local/cuda-12.8"
    environment["CUDAToolkit_ROOT"] = "/usr/local/cuda-12.8"
    for name in (
        "CMAKE_PREFIX_PATH",
        "CMAKE_GENERATOR",
        "CMAKE_GENERATOR_PLATFORM",
        "CMAKE_GENERATOR_TOOLSET",
        "CMAKE_GENERATOR_INSTANCE",
        "CMAKE_TOOLCHAIN_FILE",
        "CMAKE_FIND_ROOT_PATH",
        "CFLAGS",
        "CXXFLAGS",
        "LDFLAGS",
        "CUDAFLAGS",
        "NVCC_PREPEND_FLAGS",
        "NVCC_APPEND_FLAGS",
        "MAKEFLAGS",
        "CMAKE_BUILD_PARALLEL_LEVEL",
        "LD_LIBRARY_PATH",
        "LD_PRELOAD",
        "LD_AUDIT",
        "LD_DEBUG",
        "LD_DEBUG_OUTPUT",
        "LD_PROFILE",
        "LD_PROFILE_OUTPUT",
        "PKG_CONFIG_PATH",
        "OMP_NUM_THREADS",
        "CUDAARCHS",
        "CPATH",
        "C_INCLUDE_PATH",
        "CPLUS_INCLUDE_PATH",
        "LIBRARY_PATH",
        "CMAKE_INCLUDE_PATH",
        "CMAKE_LIBRARY_PATH",
        "CMAKE_PROGRAM_PATH",
        "CMAKE_FRAMEWORK_PATH",
    ):
        environment.pop(name, None)
    return environment


def parse_ldd_closure(output: str) -> dict[str, str | None]:
    closure: dict[str, str | None] = {}
    for line in output.splitlines():
        match = re.match(r"\s*(\S+)\s+=>\s+(\S+)", line)
        if match:
            name, resolved = match.groups()
            if resolved == "not":
                raise RuntimePinError(f"unresolved shared library in ldd output: {line}")
            if resolved != "not":
                if resolved == "found":
                    raise RuntimePinError(f"unresolved shared library in ldd output: {line}")
                closure[name] = str(Path(resolved).resolve())
            continue
        direct = re.match(r"\s*(/\S+)\s+\(0x[0-9a-fA-F]+\)", line)
        if direct:
            path = str(Path(direct.group(1)).resolve())
            closure[Path(path).name] = path
            continue
        if "not found" in line:
            raise RuntimePinError(f"unresolved shared library in ldd output: {line}")
    return closure


def collect_static_library_closure(build_root: Path) -> dict[str, dict[str, Any]]:
    bin_root = build_root / "bin"
    roots = [bin_root / "llama-server"]
    roots.extend(sorted(bin_root.glob("libllama.so*")))
    roots.extend(sorted(bin_root.glob("libggml*.so*")))
    if not roots[0].is_file():
        raise RuntimePinError("candidate llama-server is missing")
    closure: dict[str, dict[str, Any]] = {}
    loader_env = candidate_build_environment()
    loader_env["LD_LIBRARY_PATH"] = os.pathsep.join(
        [str(bin_root.resolve()), "/usr/local/cuda-12.8/lib64", "/usr/lib/wsl/lib"]
    )
    for binary in roots:
        completed = subprocess.run(
            ["ldd", str(binary)],
            text=True,
            capture_output=True,
            check=False,
            env=loader_env,
        )
        if completed.returncode != 0:
            raise RuntimePinError(f"ldd failed for candidate dependency: {binary}")
        output = completed.stdout or completed.stderr
        dependencies = parse_ldd_closure(output)
        closure[str(binary.resolve())] = {
            "sha256": sha256_file(binary),
            "dependencies": {
                name: {
                    "path": path,
                    "sha256": sha256_file(Path(path)),
                }
                for name, path in sorted(dependencies.items())
                if path is not None
            },
            "kernel_vdso_is_process_supplied": "linux-vdso.so.1" in output,
        }
    return closure


def relevant_environment(environ: Mapping[str, str] | None = None) -> dict[str, str | None]:
    source = os.environ if environ is None else environ
    names = (
        "PATH",
        "CC",
        "CXX",
        "CFLAGS",
        "CXXFLAGS",
        "LDFLAGS",
        "CUDACXX",
        "CUDAHOSTCXX",
        "CUDAFLAGS",
        "CUDA_HOME",
        "CUDA_PATH",
        "CUDA_VISIBLE_DEVICES",
        "CUDAARCHS",
        "NVCC_PREPEND_FLAGS",
        "NVCC_APPEND_FLAGS",
        "CMAKE_PREFIX_PATH",
        "CMAKE_GENERATOR",
        "CMAKE_TOOLCHAIN_FILE",
        "CMAKE_BUILD_PARALLEL_LEVEL",
        "PKG_CONFIG_PATH",
        "MAKEFLAGS",
        "LD_LIBRARY_PATH",
        "OMP_NUM_THREADS",
        "CUDAToolkit_ROOT",
        "CMAKE_FIND_ROOT_PATH",
        "LD_PRELOAD",
        "LD_AUDIT",
        "LD_DEBUG",
        "LD_DEBUG_OUTPUT",
        "LD_PROFILE",
        "LD_PROFILE_OUTPUT",
        "CUDAARCHS",
        "CPATH",
        "C_INCLUDE_PATH",
        "CPLUS_INCLUDE_PATH",
        "LIBRARY_PATH",
        "CMAKE_INCLUDE_PATH",
        "CMAKE_LIBRARY_PATH",
        "CMAKE_PROGRAM_PATH",
        "CMAKE_FRAMEWORK_PATH",
    )
    return {name: source.get(name) for name in names}


def read_cmake_cache(build_root: Path) -> dict[str, str]:
    cache_path = build_root / "CMakeCache.txt"
    if not cache_path.is_file():
        raise RuntimePinError("CMakeCache.txt is missing from the candidate build")
    values: dict[str, str] = {}
    for line in cache_path.read_text(encoding="utf-8", errors="strict").splitlines():
        if line.startswith("//") or line.startswith("#") or not line:
            continue
        left, separator, value = line.partition("=")
        if not separator:
            continue
        key, type_separator, _kind = left.partition(":")
        if type_separator:
            values[key] = value
    return values


def _validate_cmake_configuration(values: Mapping[str, str]) -> None:
    expected = {
        "CMAKE_BUILD_TYPE": "Release",
        "CMAKE_GENERATOR": "Unix Makefiles",
        "CMAKE_C_COMPILER": "/usr/bin/cc",
        "CMAKE_CXX_COMPILER": "/usr/bin/c++",
        "CMAKE_CUDA_ARCHITECTURES": "86",
        "CUDAToolkit_ROOT": "/usr/local/cuda-12.8",
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
    mismatches = {
        name: {"expected": expected_value, "observed": values.get(name)}
        for name, expected_value in expected.items()
        if values.get(name, "").upper() != expected_value.upper()
    }
    if mismatches:
        raise RuntimePinError(f"candidate CMake configuration differs from the frozen CUDA build: {mismatches}")
    if Path(values.get("CMAKE_CUDA_COMPILER", "")).resolve() != Path(
        "/usr/local/cuda-12.8/bin/nvcc"
    ).resolve():
        raise RuntimePinError("candidate CMake cache selected a different CUDA compiler")
    if Path(values.get("CUDAToolkit_BIN_DIR", "")).resolve() != Path(
        "/usr/local/cuda-12.8/bin"
    ).resolve():
        raise RuntimePinError("candidate CMake cache discovered a different CUDA toolkit")
    if Path(values.get("CUDAToolkit_NVCC_EXECUTABLE", "")).resolve() != Path(
        "/usr/local/cuda-12.8/bin/nvcc"
    ).resolve():
        raise RuntimePinError("candidate CMake toolkit metadata selected a different NVCC")


def _cuda_architecture_flags(build_root: Path) -> tuple[str, str]:
    matches = sorted(build_root.rglob("ggml-cuda.dir/flags.make"))
    if len(matches) != 1:
        raise RuntimePinError("candidate CUDA compilation flags are missing or ambiguous")
    flags = matches[0].read_text(encoding="utf-8", errors="strict")
    _validate_cuda_architecture_flags(flags)
    return str(matches[0].resolve()), hashlib.sha256(flags.encode("utf-8")).hexdigest()


def _validate_cuda_architecture_flags(flags: str) -> None:
    expected = "--generate-code=arch=compute_86,code=[compute_86,sm_86]"
    if expected not in flags or re.search(r"compute_(?!86\b)|sm_(?!86\b)", flags):
        raise RuntimePinError("candidate CUDA compilation did not target only the RTX 3060 architecture")


def collect_manifest(
    *,
    source_root: Path,
    build_root: Path,
    model_path: Path = MODEL_PATH,
    production_tree: str = PRODUCTION_TREE,
    trace_tree: str,
    build_environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    validate_model_identity(model_path=model_path, observed_sha256=sha256_file(model_path))
    cmake_cache = read_cmake_cache(build_root)
    _validate_cmake_configuration(cmake_cache)
    cuda_flags_path, cuda_flags_hash = _cuda_architecture_flags(build_root)
    if production_tree != PRODUCTION_TREE:
        raise RuntimePinError("repaired production source tree mismatch")
    trace_tree_observed = git_value(source_root, "write-tree")
    if trace_tree_observed != trace_tree or trace_tree_observed != OBSERVABILITY_TREE:
        raise RuntimePinError("qualification-observed source tree mismatch")
    verify_qualification_source_tree(source_root)
    binary = (build_root / "bin" / "llama-server").resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise RuntimePinError("candidate llama-server is absent or not executable")
    patch_hashes = verify_patch_hashes()
    test_binaries = {
        name: str((build_root / "bin" / name).resolve())
        for name in BUILD_TARGETS[1:]
    }
    for path in test_binaries.values():
        if not Path(path).is_file() or not os.access(path, os.X_OK):
            raise RuntimePinError("one of the deterministic candidate test binaries is missing")
    closure = collect_static_library_closure(build_root)
    return {
        "format_version": 1,
        "kind": "relaylm-3013-repaired-cuda-candidate",
        "source": {
            "repository": UPSTREAM_REPOSITORY,
            "revision": BASE_REVISION,
            "base_tree": BASE_TREE,
            **patch_hashes,
            "production_repair_tree": production_tree,
            "qualification_observability_tree": trace_tree_observed,
        },
        "build": {
            "build_root": str(build_root.resolve()),
            "cmake_arguments": list(CMAKE_ARGS),
            "targets": list(BUILD_TARGETS),
            "compiler": {
                "path": cmake_cache["CMAKE_CXX_COMPILER"],
                "version": run_text([cmake_cache["CMAKE_CXX_COMPILER"], "--version"]).splitlines()[0],
            },
            "cuda_compiler": {
                "path": cmake_cache["CMAKE_CUDA_COMPILER"],
                "version": run_text([cmake_cache["CMAKE_CUDA_COMPILER"], "--version"]),
            },
            "cmake": run_text(["cmake", "--version"]).splitlines()[0],
            "cuda_toolkit": "12.8",
            "cuda_architectures": [86],
            "build_type": "Release",
            "cmake_cache_sha256": f"sha256:{sha256_file(build_root / 'CMakeCache.txt')}",
            "cmake_cache_settings": {
                key: cmake_cache[key]
                for key in sorted(cmake_cache)
                if key in {
                    "BUILD_SHARED_LIBS",
                    "CMAKE_BUILD_TYPE",
                    "CMAKE_C_COMPILER",
                    "CMAKE_CUDA_ARCHITECTURES",
                    "CMAKE_CUDA_COMPILER",
                    "CMAKE_CXX_COMPILER",
                    "CMAKE_GENERATOR",
                    "CUDAToolkit_BIN_DIR",
                    "CUDAToolkit_NVCC_EXECUTABLE",
                    "CUDAToolkit_ROOT",
                    "GGML_BACKEND_DL",
                    "GGML_BLAS",
                    "GGML_CUDA",
                    "GGML_CUDA_FA",
                    "GGML_CUDA_FA_ALL_QUANTS",
                    "GGML_CUDA_GRAPHS",
                    "GGML_CUDA_NCCL",
                    "GGML_NATIVE",
                    "GGML_OPENMP",
                    "LLAMA_BUILD_EXAMPLES",
                    "LLAMA_BUILD_MTMD",
                    "LLAMA_BUILD_SERVER",
                    "LLAMA_BUILD_TESTS",
                    "LLAMA_BUILD_UI",
                    "LLAMA_USE_PREBUILT_UI",
                    "BUILD_SHARED_LIBS",
                }
            },
            "cuda_architecture_flags": {
                "path": cuda_flags_path,
                "sha256": f"sha256:{cuda_flags_hash}",
                "effective_architectures": [86],
            },
            "host": run_text(["uname", "-a"]),
            "gpu": run_text(GPU_QUERY_COMMAND),
            "shared_libraries": closure,
            "test_binaries": {
                name: {"path": path, "sha256": sha256_file(Path(path))}
                for name, path in test_binaries.items()
            },
            "relevant_environment": relevant_environment(build_environ),
        },
        "server": {
            "path": str(binary),
            "sha256": sha256_file(binary),
            "startup_argv_template": [
                str(binary),
                "-m",
                str(model_path),
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
                "--log-timestamps",
                "--log-file",
                "<arm-evidence-root>/llama-server.log",
            ],
            "swa_full": False,
            "checkpointing_disabled": False,
            "server_slots": 1,
        },
        "model": {"path": str(model_path.resolve()), "sha256": MODEL_SHA256},
        "qualification_counters": {
            "candidate_server_launches": 0,
            "model_loads": 0,
            "generation_requests": 0,
            "input_count_requests": 0,
        },
    }


def build_candidate(
    *,
    source_checkout: Path,
    source_output: Path,
    build_root: Path,
    model_path: Path = MODEL_PATH,
    manifest_path: Path,
) -> dict[str, Any]:
    source_checkout = source_checkout.expanduser().resolve()
    source_output = source_output.expanduser().resolve()
    build_root = build_root.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    if source_output.exists() or build_root.exists() or manifest_path.exists():
        raise RuntimePinError("candidate output paths must all be fresh")
    validate_model_identity(model_path=model_path, observed_sha256=sha256_file(model_path))
    verify_clean_base(source_checkout)
    verify_patch_hashes()
    source_output.parent.mkdir(parents=True, exist_ok=True)
    build_root.parent.mkdir(parents=True, exist_ok=True)
    run_text(["git", "clone", "--no-hardlinks", "--no-checkout", str(source_checkout), str(source_output)])
    run_text(["git", "-C", str(source_output), "checkout", "--detach", BASE_REVISION])
    verify_clean_base(source_output)

    production_patch = PRODUCTION_PATCH_PATH
    observability_patch = OBSERVABILITY_PATCH_PATH
    run_text(["git", "-C", str(source_output), "apply", "--check", str(production_patch)])
    run_text(["git", "-C", str(source_output), "apply", str(production_patch)])
    run_text(["git", "-C", str(source_output), "add", "--all"])
    production_tree = git_value(source_output, "write-tree")
    if production_tree != PRODUCTION_TREE:
        raise RuntimePinError("applying the frozen repair did not reproduce its tree")
    run_text(["git", "-C", str(source_output), "apply", "--check", str(observability_patch)])
    run_text(["git", "-C", str(source_output), "apply", str(observability_patch)])
    run_text(["git", "-C", str(source_output), "add", "--all"])
    trace_tree = git_value(source_output, "write-tree")
    verify_qualification_source_tree(source_output)

    build_environment = candidate_build_environment()
    configure = cmake_configure_command(source_output, build_root)
    configure_log = run_text(configure, env=build_environment)
    build_command = [
        "cmake",
        "--build",
        str(build_root),
        "--target",
        *BUILD_TARGETS,
        "--parallel",
        "2",
    ]
    build_log = run_text(build_command, env=build_environment)
    manifest = collect_manifest(
        source_root=source_output,
        build_root=build_root,
        model_path=model_path,
        production_tree=production_tree,
        trace_tree=trace_tree,
        build_environ=build_environment,
    )
    manifest["build"]["configure_command"] = configure
    manifest["build"]["build_command"] = build_command
    manifest["build"]["configure_log_sha256"] = f"sha256:{hashlib.sha256(configure_log.encode()).hexdigest()}"
    manifest["build"]["build_log_sha256"] = f"sha256:{hashlib.sha256(build_log.encode()).hexdigest()}"
    manifest["build"]["source_output"] = str(source_output)
    _atomic_json(manifest_path, manifest)
    return manifest


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
        temporary = Path(stream.name)
        os.chmod(temporary, 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
        parent_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-checkout", required=True, type=Path)
    parser.add_argument("--source-output", required=True, type=Path)
    parser.add_argument("--build-root", required=True, type=Path)
    parser.add_argument("--model-path", type=Path, default=MODEL_PATH)
    parser.add_argument("--manifest-path", required=True, type=Path)
    args = parser.parse_args(argv)
    manifest = build_candidate(
        source_checkout=args.source_checkout,
        source_output=args.source_output,
        build_root=args.build_root,
        model_path=args.model_path,
        manifest_path=args.manifest_path,
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

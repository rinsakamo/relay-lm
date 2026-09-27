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
import stat
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


def _stat_identity(path: Path) -> dict[str, int]:
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise RuntimePinError(f"shared-library identity is not a regular file: {path}")
    return {
        "device": info.st_dev,
        "inode": info.st_ino,
        "mode": info.st_mode,
        "size": info.st_size,
        "links": info.st_nlink,
        "ctime_ns": info.st_ctime_ns,
        "mtime_ns": info.st_mtime_ns,
    }


def _sealed_file_record(path: Path, *, require_regular_lexical_path: bool = False) -> dict[str, Any]:
    lexical_path = Path(os.path.abspath(path))
    try:
        lexical_stat = lexical_path.lstat()
        canonical_path = lexical_path.resolve(strict=True)
    except OSError as exc:
        raise RuntimePinError(f"shared-library path is unavailable: {lexical_path}") from exc
    if require_regular_lexical_path and not stat.S_ISREG(lexical_stat.st_mode):
        raise RuntimePinError(f"sealed WSL CUDA object must be a regular path: {lexical_path}")
    try:
        before = _stat_identity(canonical_path)
        digest = sha256_file(canonical_path)
        after = _stat_identity(canonical_path)
    except OSError as exc:
        raise RuntimePinError(f"shared-library object is unavailable: {canonical_path}") from exc
    if before != after:
        raise RuntimePinError(f"shared-library object changed while it was being sealed: {canonical_path}")
    return {
        "path": str(lexical_path),
        "realpath": str(canonical_path),
        "sha256": digest,
        "identity": after,
    }


def _decode_mount_field(value: str) -> str:
    return re.sub(
        r"\\([0-7]{3})",
        lambda match: chr(int(match.group(1), 8)),
        value,
    )


def _mount_record(mountinfo_path: Path, mountpoint: Path) -> dict[str, str]:
    expected = str(mountpoint)
    try:
        lines = mountinfo_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimePinError("WSL CUDA mount topology is unavailable") from exc
    matches: list[dict[str, str]] = []
    for line in lines:
        if " - " not in line:
            continue
        before, after = line.split(" - ", maxsplit=1)
        left = before.split()
        right = after.split()
        if len(left) < 6 or len(right) < 3:
            continue
        observed_mountpoint = _decode_mount_field(left[4])
        if observed_mountpoint != expected:
            continue
        matches.append(
            {
                "mountpoint": observed_mountpoint,
                "filesystem": right[0],
                "source": _decode_mount_field(right[1]),
                "mount_options": left[5],
                "super_options": ",".join(right[2:]),
            }
        )
    if len(matches) != 1:
        raise RuntimePinError(f"WSL CUDA mountpoint is missing or ambiguous: {expected}")
    return matches[0]


def _driver_version_from_inf(path: Path) -> tuple[str, str]:
    try:
        content = path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise RuntimePinError("WSL NVIDIA driver INF is unavailable") from exc
    match = re.search(
        r"(?im)^\s*DriverVer\s*=\s*([^,\r\n]+)\s*,\s*([^\r\n]+)",
        content,
    )
    if match is None:
        raise RuntimePinError("WSL NVIDIA driver INF has no DriverVer identity")
    return match.group(1).strip(), match.group(2).strip()


def _elf_soname(path: Path) -> str:
    try:
        output = run_text(["readelf", "-d", str(path)])
    except RuntimePinError as exc:
        raise RuntimePinError("cannot inspect WSL CUDA driver ELF identity") from exc
    match = re.search(r"\(SONAME\).*\[([^\]]+)\]", output)
    if match is None:
        raise RuntimePinError("WSL CUDA driver payload has no ELF SONAME")
    return match.group(1)


def collect_wsl_cuda_driver_closure(
    shared_libraries: Mapping[str, Mapping[str, Any]],
    *,
    wsl_lib_root: Path = Path("/usr/lib/wsl/lib"),
    wsl_driver_root: Path = Path("/usr/lib/wsl/drivers"),
    mountinfo_path: Path = Path("/proc/self/mountinfo"),
) -> dict[str, Any] | None:
    """Seal the observed WSL CUDA shim and its exact mapped driver package.

    This is a two-object WSL dispatch contract, not a path or byte alias:
    ldd resolves the guest shim under ``/usr/lib/wsl/lib`` while CUDA maps the
    distinct NVIDIA user-mode payload from the read-only 9p driver package.
    Ordinary Linux closures return ``None`` and retain exact-path matching.
    """
    wsl_lib_root = Path(os.path.abspath(wsl_lib_root))
    wsl_driver_root = Path(os.path.abspath(wsl_driver_root))
    logical_dependencies: dict[str, list[Mapping[str, Any]]] = {}
    for record in shared_libraries.values():
        dependencies = record.get("dependencies")
        if not isinstance(dependencies, Mapping):
            continue
        dependency = dependencies.get("libcuda.so.1")
        if isinstance(dependency, Mapping) and isinstance(dependency.get("path"), str):
            dependency_path = str(Path(dependency["path"]).resolve())
            logical_dependencies.setdefault(dependency_path, []).append(dependency)

    exact_wsl_stub_paths = {
        str((wsl_lib_root / name).resolve())
        for name in ("libcuda.so", "libcuda.so.1", "libcuda.so.1.1")
    }
    wsl_stub_paths = set(logical_dependencies).intersection(exact_wsl_stub_paths)
    if not wsl_stub_paths:
        return None
    if len(wsl_stub_paths) != 1 or set(logical_dependencies) != wsl_stub_paths:
        raise RuntimePinError("candidate resolves libcuda.so.1 through ambiguous WSL shim paths")
    stub_path = Path(next(iter(wsl_stub_paths)))

    lib_mount = _mount_record(mountinfo_path, wsl_lib_root)
    if lib_mount["filesystem"] != "overlay":
        raise RuntimePinError("WSL CUDA shim is not on the observed WSL lib overlay")
    driver_mount = _mount_record(mountinfo_path, wsl_driver_root)
    if (
        driver_mount["filesystem"] != "9p"
        or driver_mount["source"] != "drivers"
        or "ro" not in driver_mount["mount_options"].split(",")
    ):
        raise RuntimePinError("WSL CUDA driver package is not on the read-only WSL drivers mount")

    local_candidates = sorted(wsl_lib_root.glob("libcuda.so*"))
    supported_local_names = {"libcuda.so", "libcuda.so.1", "libcuda.so.1.1"}
    if {path.name for path in local_candidates} - supported_local_names:
        raise RuntimePinError("WSL CUDA shim directory has an unrecognized libcuda.so alias")
    shim_record = _sealed_file_record(stub_path, require_regular_lexical_path=True)
    if shim_record["path"] != shim_record["realpath"]:
        raise RuntimePinError("WSL CUDA shim path resolves through an unsealed symlink")
    for dependency in logical_dependencies[str(stub_path)]:
        if (
            dependency.get("sha256") != shim_record["sha256"]
            or dependency.get("identity") != shim_record["identity"]
        ):
            raise RuntimePinError("WSL CUDA shim changed while the static closure was being sealed")
    shim_aliases: list[dict[str, Any]] = []
    for alias_path in local_candidates:
        alias = _sealed_file_record(alias_path, require_regular_lexical_path=True)
        if (
            alias["path"] != alias["realpath"]
            or alias["identity"]["device"] != shim_record["identity"]["device"]
            or alias["identity"]["inode"] != shim_record["identity"]["inode"]
            or alias["sha256"] != shim_record["sha256"]
        ):
            raise RuntimePinError("WSL CUDA shim aliases do not identify one sealed file object")
        shim_aliases.append(alias)
    if not any(record["path"] == str(stub_path) for record in shim_aliases):
        raise RuntimePinError("the ldd-resolved WSL CUDA shim path is absent")

    payload_candidates = sorted(wsl_driver_root.glob("*/libcuda.so*"))
    if len(payload_candidates) != 1:
        raise RuntimePinError("WSL NVIDIA driver package has a missing or ambiguous libcuda payload")
    payload_path = payload_candidates[0]
    package_root = payload_path.parent
    if re.fullmatch(r"nvmdi\.inf_amd64_[0-9a-f]+", package_root.name, flags=re.IGNORECASE) is None:
        raise RuntimePinError("WSL CUDA payload is outside the sealed NVIDIA driver package layout")
    if payload_path.name != "libcuda.so.1.1":
        raise RuntimePinError("WSL NVIDIA driver payload has an unexpected mapped filename")
    payload = _sealed_file_record(payload_path, require_regular_lexical_path=True)
    if payload["path"] != payload["realpath"] or _elf_soname(payload_path) != "libcuda.so.1":
        raise RuntimePinError("WSL NVIDIA driver payload ELF identity is invalid")

    loader_path = package_root / "libcuda_loader.so"
    loader_copy = _sealed_file_record(loader_path, require_regular_lexical_path=True)
    if (
        loader_copy["path"] != loader_copy["realpath"]
        or loader_copy["sha256"] != shim_record["sha256"]
        or (
            loader_copy["identity"]["device"], loader_copy["identity"]["inode"]
        ) == (shim_record["identity"]["device"], shim_record["identity"]["inode"])
    ):
        raise RuntimePinError("WSL NVIDIA package loader does not match the sealed WSL CUDA shim bytes")
    if (
        payload["sha256"] == shim_record["sha256"]
        or (payload["identity"]["device"], payload["identity"]["inode"])
        == (shim_record["identity"]["device"], shim_record["identity"]["inode"])
    ):
        raise RuntimePinError("WSL NVIDIA driver payload is not a distinct mapped driver object")
    inf_path = package_root / "nvmdi.inf"
    inf_date, inf_version = _driver_version_from_inf(inf_path)
    inf_record = _sealed_file_record(inf_path, require_regular_lexical_path=True)

    accepted: list[dict[str, Any]] = []
    for alias in shim_aliases:
        accepted.append(
            {
                **alias,
                "role": "wsl-cuda-shim-alias",
                "relation": "same-device-inode-hardlink-alias",
            }
        )
    accepted.append(
        {
            **payload,
            "role": "nvidia-wsl-user-mode-driver-payload",
            "relation": "distinct-driver-payload-in-the-sealed-wsl-package",
        }
    )
    return {
        "schema_version": 1,
        "contract": "wsl-cuda-driver-shim-and-package-payload-v1",
        "logical_dependency": "libcuda.so.1",
        "shim_mount": lib_mount,
        "driver_mount": driver_mount,
        "shim": {**shim_record, "aliases": shim_aliases},
        "driver_package": {
            "root": str(package_root),
            "name": package_root.name,
            "inf": {**inf_record, "driver_date": inf_date, "driver_version": inf_version},
            "loader_copy": loader_copy,
            "loader_relation": "same-bytes-distinct-mounted-object",
            "payload": {**payload, "soname": "libcuda.so.1"},
            "payload_relation": "distinct-object-distinct-bytes",
        },
        "accepted_mapped_objects": accepted,
    }


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
        root_record = _sealed_file_record(binary)
        closure[str(binary.resolve())] = {
            "sha256": root_record["sha256"],
            "identity": root_record["identity"],
            "dependencies": {
                name: _sealed_file_record(Path(path))
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
    wsl_cuda_driver_closure = collect_wsl_cuda_driver_closure(closure)
    server_record = closure[str(binary)]
    return {
        "format_version": 2,
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
            "wsl_cuda_driver_closure": wsl_cuda_driver_closure,
            "test_binaries": {
                name: {"path": path, "sha256": sha256_file(Path(path))}
                for name, path in test_binaries.items()
            },
            "relevant_environment": relevant_environment(build_environ),
        },
        "server": {
            "path": str(binary),
            "sha256": server_record["sha256"],
            "identity": server_record["identity"],
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

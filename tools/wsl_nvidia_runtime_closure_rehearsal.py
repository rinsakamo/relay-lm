"""One-shot zero-request WSL NVIDIA runtime-closure rehearsal for #3018.

This target loads the frozen candidate model once, reads the complete server
process map, and terminates. It does not send HTTP requests or call RelayLM.
Execution requires a later exact owner comment that authorizes the frozen
proposal descriptor; the proposal marker itself is never execution authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from typing import Any

from tools import cache_correctness_repair_runtime as candidate_runtime
from tools import v1_cache_correctness_repair_qualification as qualification


OWNER_ISSUE = 3018
TARGET_ID = "diagnostic:3018-wsl-nvidia-runtime-closure-rehearsal"
ATTEMPT_ID = "wsl-nvidia-runtime-closure-rehearsal-20260927-a"
PROPOSAL_STATUS = "PROPOSAL_ONLY_NOT_EXECUTION_AUTHORITY"
AUTHORIZATION_MARKER = "WSL_NVIDIA_RUNTIME_LIBRARY_CLOSURE_REHEARSAL_AUTHORIZED"
REVOKE_MARKERS = (
    "WSL_NVIDIA_RUNTIME_LIBRARY_CLOSURE_REHEARSAL_REVOKED",
    "STOP EXACT REHEARSAL",
    "EXECUTION_AUTHORITY_REVOKED",
)
PASS_TERMINAL = "WSL_NVIDIA_RUNTIME_LIBRARY_CLOSURE_REHEARSAL_PASSED"
BLOCKED_TERMINAL = "WSL_NVIDIA_RUNTIME_LIBRARY_CLOSURE_REHEARSAL_BLOCKED"
RESOURCE_KEY = "llama-cpp:local-gpu"
PORT = 1234
STARTUP_TIMEOUT_SECONDS = 600
MODEL_LOADED_MARKER = "llama_server: model loaded"
EVIDENCE_ROOT = Path("/home/rinsa/relaylm-evidence")
EXPECTED_SERVER_BINARY = Path(
    "/home/rinsa/work/llama-cpp-3013-repair-build-clean-20260927-b/bin/llama-server"
)
EXPECTED_SERVER_SHA256 = "4a928435ae6e57217fe471fb318fefb7861d3508de3166c02ca5a2adee995cc9"


class RehearsalError(RuntimeError):
    """The exact zero-request rehearsal cannot proceed safely."""


def _canonical_json(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return candidate_runtime.sha256_file(path)
    except (OSError, candidate_runtime.RuntimePinError) as exc:
        raise RehearsalError(f"rehearsal input is unavailable: {path}") from exc


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RehearsalError(f"rehearsal JSON input is invalid: {path}") from exc
    if not isinstance(payload, dict):
        raise RehearsalError(f"rehearsal JSON object required: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any], *, exclusive: bool = False) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    body = _canonical_json(payload)
    if exclusive:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(fd, "wb", closefd=False) as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            os.close(fd)
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(fd)
    try:
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RehearsalError(f"repository identity lookup failed: {detail}")
    return completed.stdout.strip()


def _verify_repository(repo_root: Path, expected: Mapping[str, Any]) -> None:
    repo_root = repo_root.expanduser().resolve()
    if (
        _git(repo_root, "branch", "--show-current") != "v1"
        or _git(repo_root, "status", "--porcelain")
        or _git(repo_root, "rev-parse", "HEAD") != expected.get("head")
        or _git(repo_root, "rev-parse", "HEAD^{tree}") != expected.get("tree")
    ):
        raise RehearsalError("local v1 repository identity changed after proposal freeze")
    output = subprocess.run(
        ["git", "-C", str(repo_root), "ls-remote", "--heads", "origin", "refs/heads/v1"],
        text=True,
        capture_output=True,
        check=False,
    )
    entries = [line.split("\t", 1) for line in output.stdout.splitlines() if line.strip()]
    if (
        output.returncode != 0
        or len(entries) != 1
        or len(entries[0]) != 2
        or entries[0][1] != "refs/heads/v1"
        or entries[0][0] != expected.get("head")
    ):
        raise RehearsalError("fresh origin/v1 no longer matches the frozen rehearsal head")


def runtime_closure_digest(closure: Mapping[str, Any]) -> str:
    return _sha256_bytes(_canonical_json(closure).rstrip(b"\n"))


def collect_candidate_manifest(*, candidate_binary: Path, model_path: Path) -> dict[str, Any]:
    """Collect a fresh sealed manifest without starting a process or loading a model."""

    binary = candidate_binary.expanduser().resolve(strict=True)
    expected_binary = (binary.parent.parent / "bin" / "llama-server").resolve()
    if (
        binary != expected_binary
        or binary != EXPECTED_SERVER_BINARY
        or not os.access(binary, os.X_OK)
    ):
        raise RehearsalError("candidate binary is not the exact build-root llama-server")
    model = model_path.expanduser().resolve(strict=True)
    if model != candidate_runtime.MODEL_PATH.resolve():
        raise RehearsalError("rehearsal model path differs from the frozen #3013 model")
    model_hash = _sha256_file(model)
    if model_hash != candidate_runtime.MODEL_SHA256:
        raise RehearsalError("rehearsal model digest differs from the frozen #3013 model")

    build_root = binary.parent.parent
    try:
        libraries = candidate_runtime.collect_static_library_closure(build_root)
        wsl_closure = candidate_runtime.collect_wsl_cuda_driver_closure(libraries)
        if wsl_closure is None:
            raise RehearsalError("candidate does not resolve CUDA through the WSL guest shim")
        gpu = candidate_runtime.run_text(candidate_runtime.GPU_QUERY_COMMAND)
        server_record = libraries.get(str(binary))
    except candidate_runtime.RuntimePinError as exc:
        raise RehearsalError("candidate static runtime closure is not sealable") from exc
    model_record = candidate_runtime._sealed_file_record(model, require_regular_lexical_path=True)
    if not isinstance(server_record, Mapping):
        raise RehearsalError("candidate library closure omitted the exact server binary")
    if not isinstance(server_record.get("identity"), Mapping):
        raise RehearsalError("candidate library closure omitted the exact server file identity")
    if server_record.get("sha256") != EXPECTED_SERVER_SHA256:
        raise RehearsalError("candidate binary digest differs from the preserved attempt-B artifact")
    return {
        "format_version": 1,
        "kind": "relaylm-3018-wsl-nvidia-runtime-closure-rehearsal-candidate",
        "server": {
            "path": str(binary),
            "sha256": server_record["sha256"],
            "identity": server_record["identity"],
        },
        "build": {
            "build_root": str(build_root),
            "gpu": gpu,
            "shared_libraries": libraries,
            "wsl_cuda_driver_closure": wsl_closure,
        },
        "model": {**model_record},
    }


def _server_environment(manifest: Mapping[str, Any]) -> dict[str, str]:
    try:
        environment = qualification._candidate_server_environment(dict(manifest))
    except (KeyError, TypeError, IndexError) as exc:
        raise RehearsalError("candidate server environment cannot be frozen") from exc
    if any("TOKEN" in name.upper() or "KEY" in name.upper() for name in environment):
        raise RehearsalError("server environment unexpectedly includes a credential name")
    return environment


def _expected_argv(manifest: Mapping[str, Any], output_root: Path) -> list[str]:
    server = manifest["server"]
    model = manifest["model"]
    if not isinstance(server, Mapping) or not isinstance(model, Mapping):
        raise RehearsalError("candidate manifest server/model records are malformed")
    return [
        str(server["path"]),
        "-m",
        str(model["path"]),
        "--host",
        "127.0.0.1",
        "--port",
        str(PORT),
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
        str(output_root / "llama-server.log"),
    ]


def _proposal_paths(evidence_root: Path) -> dict[str, Path]:
    return {
        "candidate_manifest": evidence_root / f"{ATTEMPT_ID}-candidate-manifest.json",
        "descriptor": evidence_root / f"{ATTEMPT_ID}-descriptor.json",
        "receipt": evidence_root / f"{ATTEMPT_ID}-queue-receipt.json",
        "preflight": evidence_root / f"{ATTEMPT_ID}-preflight",
        "output": evidence_root / ATTEMPT_ID,
    }


def _build_descriptor(
    *,
    repo_root: Path,
    manifest: Mapping[str, Any],
    manifest_path: Path,
    manifest_sha256: str,
    descriptor_path: Path,
    roots: Mapping[str, Path],
) -> dict[str, Any]:
    closure = manifest["build"]["wsl_cuda_driver_closure"]
    output_root = roots["output"]
    return {
        "schema_version": 1,
        "status": PROPOSAL_STATUS,
        "owner_issue": OWNER_ISSUE,
        "target_id": TARGET_ID,
        "attempt_id": ATTEMPT_ID,
        "repository": {
            "root": str(repo_root.resolve()),
            "branch": "v1",
            "head": _git(repo_root, "rev-parse", "HEAD"),
            "tree": _git(repo_root, "rev-parse", "HEAD^{tree}"),
        },
        "candidate": {
            "manifest_path": str(manifest_path.resolve()),
            "manifest_sha256": manifest_sha256,
            "server_binary": manifest["server"]["path"],
            "server_sha256": manifest["server"]["sha256"],
            "model_path": manifest["model"]["path"],
            "model_sha256": manifest["model"]["sha256"],
            "wsl_runtime_closure_sha256": runtime_closure_digest(closure),
        },
        "roots": {
            "descriptor": str(descriptor_path.resolve()),
            "receipt": str(roots["receipt"].resolve()),
            "preflight": str(roots["preflight"].resolve()),
            "output": str(output_root.resolve()),
        },
        "server": {
            "argv": _expected_argv(manifest, output_root),
            "environment": _server_environment(manifest),
            "startup_timeout_seconds": STARTUP_TIMEOUT_SECONDS,
            "model_loaded_log_marker": MODEL_LOADED_MARKER,
        },
        "limits": {
            "maximum_server_launches": 1,
            "maximum_model_loads": 1,
            "maximum_model_facing_posts": 0,
            "generation_requests": 0,
            "input_count_requests": 0,
            "public_completions": 0,
        },
        "port": PORT,
        "closure_attestation": "complete-live-process-map-after-model-loaded",
        "execution_authority": PROPOSAL_STATUS,
    }


def prepare_proposal(
    *,
    repo_root: Path,
    candidate_binary: Path,
    model_path: Path,
    evidence_root: Path = EVIDENCE_ROOT,
) -> dict[str, Any]:
    """Create the candidate manifest and proposal descriptor only; never launch."""

    repo_root = repo_root.expanduser().resolve()
    evidence_root = evidence_root.expanduser().resolve()
    if _git(repo_root, "branch", "--show-current") != "v1" or _git(repo_root, "status", "--porcelain"):
        raise RehearsalError("proposal preparation requires a clean exact v1 checkout")
    repository_identity = {
        "head": _git(repo_root, "rev-parse", "HEAD"),
        "tree": _git(repo_root, "rev-parse", "HEAD^{tree}"),
    }
    _verify_repository(repo_root, repository_identity)
    paths = _proposal_paths(evidence_root)
    if any(path.exists() for path in paths.values()):
        raise RehearsalError("a frozen rehearsal proposal path already exists")
    manifest = collect_candidate_manifest(candidate_binary=candidate_binary, model_path=model_path)
    manifest_body = _canonical_json(manifest)
    manifest_sha256 = _sha256_bytes(manifest_body)
    descriptor = _build_descriptor(
        repo_root=repo_root,
        manifest=manifest,
        manifest_path=paths["candidate_manifest"],
        manifest_sha256=manifest_sha256,
        descriptor_path=paths["descriptor"],
        roots=paths,
    )
    _verify_repository(repo_root, descriptor["repository"])
    _validate_descriptor(descriptor)
    _write_json(paths["candidate_manifest"], manifest, exclusive=True)
    _write_json(paths["descriptor"], descriptor, exclusive=True)
    return {
        "status": PROPOSAL_STATUS,
        "target_id": TARGET_ID,
        "attempt_id": ATTEMPT_ID,
        "descriptor_path": str(paths["descriptor"]),
        "descriptor_sha256": _sha256_file(paths["descriptor"]),
        "candidate_manifest_path": str(paths["candidate_manifest"]),
        "candidate_manifest_sha256": _sha256_file(paths["candidate_manifest"]),
        "wsl_runtime_closure_sha256": descriptor["candidate"]["wsl_runtime_closure_sha256"],
        "receipt_path": str(paths["receipt"]),
        "preflight_root": str(paths["preflight"]),
        "output_root": str(paths["output"]),
    }


def _validate_descriptor(descriptor: Mapping[str, Any]) -> None:
    if (
        descriptor.get("schema_version") != 1
        or descriptor.get("status") != PROPOSAL_STATUS
        or descriptor.get("execution_authority") != PROPOSAL_STATUS
        or descriptor.get("owner_issue") != OWNER_ISSUE
        or descriptor.get("target_id") != TARGET_ID
        or descriptor.get("attempt_id") != ATTEMPT_ID
    ):
        raise RehearsalError("proposal descriptor identity or status is invalid")
    limits = descriptor.get("limits")
    if limits != {
        "maximum_server_launches": 1,
        "maximum_model_loads": 1,
        "maximum_model_facing_posts": 0,
        "generation_requests": 0,
        "input_count_requests": 0,
        "public_completions": 0,
    }:
        raise RehearsalError("rehearsal limits must freeze one server/model load and zero requests")
    if descriptor.get("port") != PORT:
        raise RehearsalError("rehearsal port differs from its frozen queue port")
    repository = descriptor.get("repository")
    candidate = descriptor.get("candidate")
    roots = descriptor.get("roots")
    server = descriptor.get("server")
    if not all(isinstance(value, Mapping) for value in (repository, candidate, roots, server)):
        raise RehearsalError("proposal descriptor is missing a frozen identity record")
    if repository.get("branch") != "v1" or not re.fullmatch(r"[0-9a-f]{40}", str(repository.get("head", ""))):
        raise RehearsalError("proposal descriptor does not bind an exact v1 head")
    if not re.fullmatch(r"[0-9a-f]{40}", str(repository.get("tree", ""))):
        raise RehearsalError("proposal descriptor does not bind an exact v1 tree")
    root_paths = [Path(str(roots.get(name, ""))).resolve() for name in ("descriptor", "receipt", "preflight", "output")]
    if any(not str(path).startswith("/") for path in root_paths) or len(set(root_paths)) != 4:
        raise RehearsalError("rehearsal evidence paths are incomplete or overlap")
    candidate_manifest = Path(str(candidate.get("manifest_path", ""))).resolve()
    if candidate_manifest in set(root_paths):
        raise RehearsalError("candidate manifest path overlaps a rehearsal evidence root")
    if (
        candidate.get("model_path") != str(candidate_runtime.MODEL_PATH.resolve())
        or candidate.get("model_sha256") != candidate_runtime.MODEL_SHA256
    ):
        raise RehearsalError("proposal descriptor changed the frozen #3013 model")
    if (
        candidate.get("server_binary") != str(EXPECTED_SERVER_BINARY)
        or candidate.get("server_sha256") != EXPECTED_SERVER_SHA256
    ):
        raise RehearsalError("proposal descriptor changed the preserved #3013 candidate binary")
    argv = server.get("argv")
    environment = server.get("environment")
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        raise RehearsalError("proposal server argv is malformed")
    if not isinstance(environment, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in environment.items()
    ):
        raise RehearsalError("proposal server environment is malformed")
    if any("TOKEN" in name.upper() or "KEY" in name.upper() for name in environment):
        raise RehearsalError("proposal descriptor must not include credentials")
    if (
        server.get("startup_timeout_seconds") != STARTUP_TIMEOUT_SECONDS
        or server.get("model_loaded_log_marker") != MODEL_LOADED_MARKER
        or argv != [
            str(candidate.get("server_binary")),
            "-m",
            str(candidate.get("model_path")),
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
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
            str(Path(str(roots["output"])) / "llama-server.log"),
        ]
    ):
        raise RehearsalError("proposal server startup contract is invalid")


def _verify_descriptor_runtime(
    *,
    descriptor_path: Path,
    repo_root: Path,
    descriptor: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], str]:
    _validate_descriptor(descriptor)
    descriptor_path = descriptor_path.expanduser().resolve(strict=True)
    if descriptor["roots"]["descriptor"] != str(descriptor_path):
        raise RehearsalError("descriptor path changed after proposal freeze")
    descriptor_sha256 = _sha256_file(descriptor_path)
    _verify_repository(repo_root, descriptor["repository"])

    candidate = descriptor["candidate"]
    manifest_path = Path(candidate["manifest_path"]).expanduser().resolve(strict=True)
    if _sha256_file(manifest_path) != candidate.get("manifest_sha256"):
        raise RehearsalError("candidate manifest digest changed after proposal freeze")
    manifest = _read_json_object(manifest_path)
    try:
        closure = manifest["build"]["wsl_cuda_driver_closure"]
        build_root = Path(manifest["build"]["build_root"]).resolve(strict=True)
        server_path = Path(manifest["server"]["path"]).resolve(strict=True)
        model_path = Path(manifest["model"]["path"]).resolve(strict=True)
    except (KeyError, TypeError, OSError) as exc:
        raise RehearsalError("candidate manifest omitted runtime closure identity") from exc
    if (
        str(server_path) != candidate.get("server_binary")
        or manifest["server"].get("sha256") != candidate.get("server_sha256")
        or str(model_path) != candidate.get("model_path")
        or manifest["model"].get("sha256") != candidate.get("model_sha256")
        or runtime_closure_digest(closure) != candidate.get("wsl_runtime_closure_sha256")
    ):
        raise RehearsalError("candidate identity or complete WSL closure digest changed")
    if _sha256_file(server_path) != candidate.get("server_sha256"):
        raise RehearsalError("candidate llama-server binary changed after proposal freeze")
    if _sha256_file(model_path) != candidate.get("model_sha256"):
        raise RehearsalError("candidate model changed after proposal freeze")

    try:
        live_libraries = candidate_runtime.collect_static_library_closure(build_root)
        live_wsl_closure = candidate_runtime.collect_wsl_cuda_driver_closure(live_libraries)
        live_gpu = candidate_runtime.run_text(candidate_runtime.GPU_QUERY_COMMAND)
    except candidate_runtime.RuntimePinError as exc:
        raise RehearsalError("candidate static runtime identity could not be re-attested") from exc
    if (
        live_libraries != manifest["build"].get("shared_libraries")
        or live_wsl_closure != closure
        or live_gpu != manifest["build"].get("gpu")
    ):
        raise RehearsalError("candidate static library or WSL NVIDIA package closure drifted")
    expected_environment = _server_environment(manifest)
    if descriptor["server"].get("environment") != expected_environment:
        raise RehearsalError("candidate server environment changed after proposal freeze")
    expected_argv = _expected_argv(manifest, Path(descriptor["roots"]["output"]))
    if descriptor["server"].get("argv") != expected_argv:
        raise RehearsalError("candidate server argv changed after proposal freeze")
    for name in ("preflight", "output"):
        if Path(descriptor["roots"][name]).exists():
            raise RehearsalError(f"frozen {name} root already exists")
    return manifest, dict(descriptor["roots"]), descriptor_sha256


def _gh_json(args: Sequence[str]) -> Any:
    completed = subprocess.run(
        ["gh", "api", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RehearsalError("fresh #3018 owner authority lookup failed")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RehearsalError("fresh #3018 owner response is malformed") from exc


def _gh_comments() -> list[dict[str, Any]]:
    completed = subprocess.run(
        [
            "gh",
            "api",
            "--paginate",
            f"repos/rinsakamo/relay-lm/issues/{OWNER_ISSUE}/comments?per_page=100",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RehearsalError("fresh #3018 execution comment lookup failed")
    decoder = json.JSONDecoder()
    pages: list[dict[str, Any]] = []
    offset = 0
    while offset < len(completed.stdout):
        while offset < len(completed.stdout) and completed.stdout[offset].isspace():
            offset += 1
        if offset >= len(completed.stdout):
            break
        try:
            page, offset = decoder.raw_decode(completed.stdout, offset)
        except json.JSONDecodeError as exc:
            raise RehearsalError("#3018 comment pagination response is malformed") from exc
        if isinstance(page, list):
            pages.extend(item for item in page if isinstance(item, dict))
        elif isinstance(page, dict):
            pages.append(page)
        else:
            raise RehearsalError("#3018 comment pagination response is malformed")
    return pages


def verify_execution_authority(
    *,
    comment_id: int,
    descriptor_sha256: str,
    descriptor: Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(comment_id, bool) or not isinstance(comment_id, int) or comment_id <= 0:
        raise RehearsalError("an exact #3018 rehearsal-authority comment id is required")
    issue = _gh_json([f"repos/rinsakamo/relay-lm/issues/{OWNER_ISSUE}"])
    if (
        not isinstance(issue, dict)
        or issue.get("number") != OWNER_ISSUE
        or issue.get("state") != "open"
        or not isinstance(issue.get("user"), dict)
        or issue["user"].get("login") != "rinsakamo"
    ):
        raise RehearsalError("#3018 owner or open-issue identity changed")
    comments = _gh_comments()
    selected = next((item for item in comments if item.get("id") == comment_id), None)
    if (
        not isinstance(selected, dict)
        or not isinstance(selected.get("user"), dict)
        or selected["user"].get("login") != "rinsakamo"
        or not isinstance(selected.get("body"), str)
    ):
        raise RehearsalError("exact #3018 rehearsal authority is unavailable")
    body = selected["body"]
    candidate = descriptor["candidate"]
    required = (
        AUTHORIZATION_MARKER,
        descriptor_sha256,
        TARGET_ID,
        ATTEMPT_ID,
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
    if any(value not in body for value in required) or PROPOSAL_STATUS in body:
        raise RehearsalError("#3018 authority does not bind this exact zero-request proposal")
    selected_id = int(selected["id"])
    selected_time = str(selected.get("created_at", ""))
    for comment in comments:
        if (
            not isinstance(comment.get("user"), dict)
            or comment["user"].get("login") != "rinsakamo"
        ):
            continue
        later_id = comment.get("id")
        if (
            (
                isinstance(later_id, int)
                and not isinstance(later_id, bool)
                and later_id > selected_id
            )
            or str(comment.get("created_at", "")) > selected_time
        ):
            later_body = comment.get("body")
            if isinstance(later_body, str) and any(marker in later_body for marker in REVOKE_MARKERS):
                raise RehearsalError("a later #3018 owner comment revoked the exact rehearsal")
    return {
        "comment_id": comment_id,
        "author": "rinsakamo",
        "owner_issue": OWNER_ISSUE,
        "owner_issue_state": "open",
        "descriptor_sha256": descriptor_sha256,
        "target_id": TARGET_ID,
        "attempt_id": ATTEMPT_ID,
        "fresh_lookup": True,
    }


def _verify_queue_receipt(
    path: Path,
    *,
    repo_root: Path,
    descriptor_path: Path,
    authority_comment_id: int,
) -> dict[str, Any]:
    receipt = _read_json_object(path)
    expected_command = [
        sys.executable,
        "-m",
        "tools.wsl_nvidia_runtime_closure_rehearsal",
        "--descriptor",
        str(descriptor_path.resolve()),
        "--authority-comment-id",
        str(authority_comment_id),
    ]
    expected_command_hash = _sha256_bytes(
        json.dumps(
            expected_command,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    )
    if (
        receipt.get("schema_version") != 2
        or not isinstance(receipt.get("request_id"), str)
        or re.fullmatch(r"[0-9a-f]{32}", receipt["request_id"]) is None
        or receipt.get("receipt_path") != str(path.resolve())
        or receipt.get("target_label") != TARGET_ID
        or receipt.get("resource_key") != RESOURCE_KEY
        or receipt.get("command_executable") != Path(sys.executable).name
        or receipt.get("command_argv_sha256") != expected_command_hash
        or receipt.get("cwd") != str(repo_root.resolve())
        or receipt.get("state") != "RUNNING"
        or receipt.get("lease_state") != "ACQUIRED"
    ):
        raise RehearsalError("canonical physical queue receipt does not bind this rehearsal")
    return receipt


def _verify_server_process_identity(
    process: subprocess.Popen[str],
    *,
    binary: Path,
    binary_sha256: str,
    expected_argv: Sequence[str],
    expected_environment: Mapping[str, str],
) -> dict[str, Any]:
    if process.poll() is not None:
        raise RehearsalError("candidate server exited before closure attestation")
    pid = process.pid
    try:
        executable = Path(f"/proc/{pid}/exe").resolve(strict=True)
        command_line = [
            token.decode("utf-8", errors="strict")
            for token in Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
            if token
        ]
        raw_environment = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
        live_environment = {
            key.decode("utf-8", errors="strict"): value.decode("utf-8", errors="strict")
            for key, separator, value in (entry.partition(b"=") for entry in raw_environment if b"=" in entry)
            if separator
        }
        start_ticks = qualification._process_start_ticks(pid)
    except (OSError, UnicodeError, qualification.QualificationTargetError) as exc:
        raise RehearsalError("candidate server process identity is unavailable") from exc
    if executable != binary.resolve() or command_line != list(expected_argv):
        raise RehearsalError("candidate server executable or argv differs from the proposal")
    if live_environment != dict(expected_environment):
        raise RehearsalError("candidate server environment differs from the proposal")
    if _sha256_file(binary) != binary_sha256:
        raise RehearsalError("candidate server binary changed during process attestation")
    return {
        "pid": pid,
        "process_start_ticks": start_ticks,
        "executable": str(executable),
        "argv": command_line,
    }


def _wait_for_model_loaded(log_path: Path, process: subprocess.Popen[str], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RehearsalError("candidate server exited before loading the exact model")
        try:
            log = log_path.read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            log = ""
        marker_count = log.count(MODEL_LOADED_MARKER)
        if marker_count > 1:
            raise RehearsalError("candidate server reported more than one model load")
        if marker_count == 1:
            return
        time.sleep(0.25)
    raise RehearsalError("candidate server did not reach the frozen model-loaded marker")


def _terminate_owned_process(process: subprocess.Popen[str] | None) -> dict[str, Any]:
    if process is None:
        return {"terminated": True, "exit_code": None, "method": "not-started"}
    if process.poll() is None:
        process.terminate()
        try:
            code = process.wait(timeout=30)
            method = "terminate"
        except subprocess.TimeoutExpired:
            process.kill()
            code = process.wait(timeout=30)
            method = "kill-owned-process-after-terminate-timeout"
    else:
        code = process.poll()
        method = "already-exited"
    return {"terminated": process.poll() is not None, "exit_code": code, "method": method}


def _seal_directory(root: Path) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if path == root / "evidence-manifest.json":
            continue
        if path.is_symlink():
            raise RehearsalError(f"rehearsal evidence must not contain symlinks: {path}")
        if path.is_file():
            files[str(path.relative_to(root))] = {
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
    manifest = {"format_version": 1, "file_count": len(files), "files": files}
    _write_json(root / "evidence-manifest.json", manifest, exclusive=True)
    return manifest


def _copy_exact(source: Path, destination: Path) -> None:
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with source.open("rb") as source_handle, destination.open("xb") as destination_handle:
        while chunk := source_handle.read(1024 * 1024):
            destination_handle.write(chunk)
        destination_handle.flush()
        os.fsync(destination_handle.fileno())


def _mapped_file_inventory(map_text: str, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    build = manifest.get("build")
    server = manifest.get("server")
    if not isinstance(build, Mapping) or not isinstance(server, Mapping):
        raise RehearsalError("candidate manifest cannot classify the process map")
    shared = build.get("shared_libraries")
    wsl = build.get("wsl_cuda_driver_closure")
    if not isinstance(shared, Mapping) or not isinstance(wsl, Mapping):
        raise RehearsalError("candidate manifest omitted the exact WSL runtime closure")

    candidate_paths = {str(server.get("path", ""))}
    ordinary_paths: set[str] = set()
    for root, record in shared.items():
        if not isinstance(root, str) or not isinstance(record, Mapping):
            raise RehearsalError("candidate shared-library closure is malformed")
        candidate_paths.add(root)
        dependencies = record.get("dependencies")
        if not isinstance(dependencies, Mapping):
            raise RehearsalError("candidate dependency closure is malformed")
        for dependency in dependencies.values():
            if isinstance(dependency, Mapping) and isinstance(dependency.get("path"), str):
                ordinary_paths.add(dependency["path"])

    shim = wsl.get("shim")
    package = wsl.get("driver_package")
    aliases = shim.get("aliases") if isinstance(shim, Mapping) else None
    runtime_objects = package.get("runtime_objects") if isinstance(package, Mapping) else None
    package_root = package.get("root") if isinstance(package, Mapping) else None
    if not isinstance(aliases, list) or not isinstance(runtime_objects, list) or not isinstance(package_root, str):
        raise RehearsalError("candidate WSL runtime role set is malformed")
    shim_paths = {
        item.get("path") for item in aliases if isinstance(item, Mapping) and isinstance(item.get("path"), str)
    }
    package_runtime_paths = {
        item.get("path")
        for item in runtime_objects
        if isinstance(item, Mapping) and isinstance(item.get("path"), str)
    }
    entries: list[dict[str, Any]] = []
    for line_number, line in enumerate(map_text.splitlines(), start=1):
        mapped = qualification._parse_mapped_file_record(line)
        if mapped is None:
            entries.append(
                {"line_number": line_number, "path": None, "classification": "anonymous-or-pseudo-mapping"}
            )
            continue
        path, map_identity, deleted = mapped
        if deleted:
            classification = "deleted-file-mapping"
        elif path in candidate_paths:
            classification = "candidate-llama-or-ggml-library"
        elif path in shim_paths:
            classification = "wsl-guest-cuda-shim"
        elif path in package_runtime_paths:
            classification = "nvidia-wsl-runtime-package-object"
        elif path.startswith("/usr/local/cuda-12.8/"):
            classification = "cuda-toolkit-library"
        elif path in ordinary_paths:
            classification = "ordinary-system-library"
        elif path.startswith(package_root + "/"):
            classification = "other-nvidia-package-object"
        elif path.startswith("/usr/lib/wsl/lib/"):
            classification = "other-wsl-guest-object"
        elif ".so" in Path(path).name:
            classification = "other-mapped-library"
        else:
            classification = "other-mapped-file"
        entries.append(
            {
                "line_number": line_number,
                "path": path,
                "map_device_major": map_identity[0],
                "map_device_minor": map_identity[1],
                "map_inode": map_identity[2],
                "deleted": deleted,
                "classification": classification,
            }
        )
    return entries


def _assert_zero_request_counters(summary: Mapping[str, Any]) -> None:
    counter_names = (
        "model_facing_post_count",
        "generation_request_count",
        "input_count_request_count",
        "public_completion_count",
    )
    if any(summary.get(name) != 0 for name in counter_names):
        raise RehearsalError("zero-request rehearsal recorded a model-facing request")
    if summary.get("scientific_attempt_consumed") is not False:
        raise RehearsalError("zero-request rehearsal consumed scientific authority")


def _assert_no_model_facing_post_log(log_text: str) -> None:
    if _model_facing_post_log_lines(log_text):
        raise RehearsalError("candidate server log records a model-facing POST")


def _model_facing_post_log_lines(log_text: str) -> list[str]:
    return [
        line
        for line in log_text.splitlines()
        if re.search(r"\bPOST\s+/", line, flags=re.IGNORECASE)
    ]


def _require_same_process_identity(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> None:
    if (
        first.get("pid") != second.get("pid")
        or first.get("process_start_ticks") != second.get("process_start_ticks")
        or first.get("executable") != second.get("executable")
        or first.get("argv") != second.get("argv")
    ):
        raise RehearsalError("candidate server process identity changed between map snapshots")


def _apply_final_server_log_evidence(
    summary: dict[str, Any], terminal: str, log_text: str
) -> str:
    post_lines = _model_facing_post_log_lines(log_text)
    marker_count = log_text.count(MODEL_LOADED_MARKER)
    summary["model_facing_post_count"] = len(post_lines)
    summary["model_loaded_marker_count"] = marker_count
    if post_lines:
        summary["failure"] = {
            "type": "UnexpectedModelFacingPOST",
            "message": f"server log recorded {len(post_lines)} POST request(s)",
        }
        return BLOCKED_TERMINAL
    if marker_count != 1 and terminal == PASS_TERMINAL:
        summary["failure"] = {
            "type": "ModelLoadEvidenceError",
            "message": "final server log did not contain exactly one model-loaded marker",
        }
        return BLOCKED_TERMINAL
    return terminal


def run_target(
    *,
    descriptor_path: Path,
    repo_root: Path,
    authority_comment_id: int,
) -> int:
    descriptor_path = descriptor_path.expanduser().resolve(strict=True)
    repo_root = repo_root.expanduser().resolve()
    descriptor = _read_json_object(descriptor_path)
    manifest, roots, descriptor_sha256 = _verify_descriptor_runtime(
        descriptor_path=descriptor_path,
        repo_root=repo_root,
        descriptor=descriptor,
    )
    authority = verify_execution_authority(
        comment_id=authority_comment_id,
        descriptor_sha256=descriptor_sha256,
        descriptor=descriptor,
    )
    receipt = _verify_queue_receipt(
        Path(roots["receipt"]),
        repo_root=repo_root,
        descriptor_path=descriptor_path,
        authority_comment_id=authority_comment_id,
    )
    preflight_root = Path(roots["preflight"])
    output_root = Path(roots["output"])
    preflight_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    _copy_exact(descriptor_path, preflight_root / "descriptor.json")
    _copy_exact(Path(descriptor["candidate"]["manifest_path"]), preflight_root / "candidate-manifest.json")
    preflight = {
        "format_version": 1,
        "state": "preflight_passed",
        "target_id": TARGET_ID,
        "attempt_id": ATTEMPT_ID,
        "descriptor_sha256": descriptor_sha256,
        "candidate_manifest_sha256": descriptor["candidate"]["manifest_sha256"],
        "wsl_runtime_closure_sha256": descriptor["candidate"]["wsl_runtime_closure_sha256"],
        "authority": authority,
        "queue_receipt": receipt,
        "candidate_model_load_attempts": 0,
        "server_launch_count": 0,
        "model_facing_post_count": 0,
        "generation_request_count": 0,
        "input_count_request_count": 0,
        "public_completion_count": 0,
        "scientific_attempt_consumed": False,
    }
    _write_json(preflight_root / "preflight.json", preflight, exclusive=True)
    _seal_directory(preflight_root)

    output_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    attempt_summary: dict[str, Any] = {
        "format_version": 1,
        "target_id": TARGET_ID,
        "attempt_id": ATTEMPT_ID,
        "descriptor_sha256": descriptor_sha256,
        "candidate_manifest_sha256": descriptor["candidate"]["manifest_sha256"],
        "wsl_runtime_closure_sha256": descriptor["candidate"]["wsl_runtime_closure_sha256"],
        "state": "running",
        "terminal": None,
        "authority": authority,
        "queue_receipt": receipt,
        "server_launch_count": 0,
        "candidate_model_load_attempts": 0,
        "generation_request_count": 0,
        "input_count_request_count": 0,
        "model_facing_post_count": 0,
        "public_completion_count": 0,
        "scientific_attempt_consumed": False,
        "closure_attestations": [],
        "failure": None,
        "cleanup": None,
    }
    _write_json(output_root / "attempt-summary.json", attempt_summary, exclusive=True)
    process: subprocess.Popen[str] | None = None
    terminal = BLOCKED_TERMINAL
    console_handle: Any = None
    try:
        server = descriptor["server"]
        binary = Path(descriptor["candidate"]["server_binary"])
        argv = list(server["argv"])
        console_handle = (output_root / "server-console.log").open("xb")
        attempt_summary["server_launch_count"] = 1
        attempt_summary["candidate_model_load_attempts"] = 1
        _write_json(output_root / "attempt-summary.json", attempt_summary)
        process = subprocess.Popen(
            argv,
            cwd=str(binary.parent),
            env=dict(server["environment"]),
            stdin=subprocess.DEVNULL,
            stdout=console_handle,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        _wait_for_model_loaded(
            output_root / "llama-server.log",
            process,
            float(server["startup_timeout_seconds"]),
        )
        _verify_repository(repo_root, descriptor["repository"])
        authority = verify_execution_authority(
            comment_id=authority_comment_id,
            descriptor_sha256=descriptor_sha256,
            descriptor=descriptor,
        )
        attempt_summary["authority"] = authority
        process_identity = _verify_server_process_identity(
            process,
            binary=binary,
            binary_sha256=descriptor["candidate"]["server_sha256"],
            expected_argv=argv,
            expected_environment=server["environment"],
        )
        maps_path = Path(f"/proc/{process.pid}/maps")
        first_maps = maps_path.read_text(encoding="utf-8")
        _write_json(
            output_root / "process-maps-first.json",
            {
                "pid": process.pid,
                "sha256": _sha256_bytes(first_maps.encode("utf-8")),
                "line_count": len(first_maps.splitlines()),
                "complete_snapshot": True,
                "mapped_file_inventory": _mapped_file_inventory(first_maps, manifest),
                "content": first_maps,
            },
            exclusive=True,
        )
        first = qualification._verify_loaded_library_closure(
            process=process,
            binary=binary,
            manifest=manifest,
            require_cuda=True,
        )
        attempt_summary["closure_attestations"].append(
            {"process_identity": process_identity, "closure": first}
        )
        time.sleep(0.25)
        second_identity = _verify_server_process_identity(
            process,
            binary=binary,
            binary_sha256=descriptor["candidate"]["server_sha256"],
            expected_argv=argv,
            expected_environment=server["environment"],
        )
        _require_same_process_identity(process_identity, second_identity)
        second_maps = maps_path.read_text(encoding="utf-8")
        _write_json(
            output_root / "process-maps-second.json",
            {
                "pid": process.pid,
                "sha256": _sha256_bytes(second_maps.encode("utf-8")),
                "line_count": len(second_maps.splitlines()),
                "complete_snapshot": True,
                "mapped_file_inventory": _mapped_file_inventory(second_maps, manifest),
                "content": second_maps,
            },
            exclusive=True,
        )
        if first_maps != second_maps:
            raise RehearsalError("complete process map changed during closure attestation")
        second = qualification._verify_loaded_library_closure(
            process=process,
            binary=binary,
            manifest=manifest,
            require_cuda=True,
            previous_attestation=first,
        )
        attempt_summary["closure_attestations"].append(
            {"process_identity": second_identity, "closure": second}
        )
        log_text = (output_root / "llama-server.log").read_text(
            encoding="utf-8", errors="replace"
        )
        marker_count = log_text.count(MODEL_LOADED_MARKER)
        if marker_count != 1:
            raise RehearsalError("candidate server did not prove exactly one model load")
        _assert_no_model_facing_post_log(log_text)
        attempt_summary["model_loaded_marker_count"] = marker_count
        _assert_zero_request_counters(attempt_summary)
        terminal = PASS_TERMINAL
    except Exception as exc:
        attempt_summary["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc)[:1000],
        }
    finally:
        cleanup = _terminate_owned_process(process)
        attempt_summary["cleanup"] = cleanup
        if console_handle is not None:
            console_handle.flush()
            os.fsync(console_handle.fileno())
            console_handle.close()
        if not cleanup.get("terminated"):
            terminal = BLOCKED_TERMINAL
            attempt_summary["failure"] = {
                "type": "ProcessCleanupError",
                "message": "owned candidate server did not terminate",
            }
        try:
            final_log = (output_root / "llama-server.log").read_text(
                encoding="utf-8", errors="replace"
            )
            terminal = _apply_final_server_log_evidence(
                attempt_summary, terminal, final_log
            )
        except OSError as exc:
            if terminal == PASS_TERMINAL:
                terminal = BLOCKED_TERMINAL
                attempt_summary["failure"] = {
                    "type": "ServerLogEvidenceError",
                    "message": f"final server log could not be read: {type(exc).__name__}",
                }
        if terminal == PASS_TERMINAL:
            try:
                _assert_zero_request_counters(attempt_summary)
            except RehearsalError as exc:
                terminal = BLOCKED_TERMINAL
                attempt_summary["failure"] = {
                    "type": type(exc).__name__,
                    "message": str(exc)[:1000],
                }
        attempt_summary["terminal"] = terminal
        attempt_summary["state"] = terminal
        _write_json(output_root / "attempt-summary.json", attempt_summary)
        _seal_directory(output_root)
    return 0 if terminal == PASS_TERMINAL else 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Zero-request live WSL NVIDIA runtime-closure rehearsal for #3018."
    )
    parser.add_argument("--prepare-proposal", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--candidate-binary", type=Path)
    parser.add_argument("--model", type=Path, default=candidate_runtime.MODEL_PATH)
    parser.add_argument("--descriptor", type=Path)
    parser.add_argument("--authority-comment-id", type=int)
    parser.add_argument("--evidence-root", type=Path, default=EVIDENCE_ROOT)
    args = parser.parse_args(argv)
    try:
        if args.prepare_proposal:
            if args.candidate_binary is None:
                parser.error("--candidate-binary is required with --prepare-proposal")
            result = prepare_proposal(
                repo_root=args.repo_root,
                candidate_binary=args.candidate_binary,
                model_path=args.model,
                evidence_root=args.evidence_root,
            )
            print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
            return 0
        if args.descriptor is None or args.authority_comment_id is None:
            parser.error("execution requires --descriptor and --authority-comment-id")
        return run_target(
            descriptor_path=args.descriptor,
            repo_root=args.repo_root,
            authority_comment_id=args.authority_comment_id,
        )
    except RehearsalError as exc:
        print(f"WSL runtime rehearsal blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

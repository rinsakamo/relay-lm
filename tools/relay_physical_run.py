from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from tools.physical_execution_queue import (
    DEFAULT_RESOURCE_KEY,
    PreInvokeBlocked,
    QueueConfig,
    run_queued_command,
)
from tools.relay_physical_env import (
    PhysicalEnvironmentIdentity,
    RelayPhysicalEnvironmentError,
    _exact_pythonpath,
    reexec_into_environment,
    verify_current_environment,
)


TARGETS_PATH = Path(".ai/physical/llama_cpp_targets.json")
TARGET_REGISTRY_SCHEMA_VERSION = 1
ENGINE = "llama.cpp"
DEFAULT_REQUIRED_DISTRIBUTIONS = ("httpx",)


class RelayPhysicalRunError(RuntimeError):
    pass


@dataclass(frozen=True)
class TargetSpec:
    name: str
    module: str
    branch: str
    description: str
    required_distributions: tuple[str, ...] = DEFAULT_REQUIRED_DISTRIBUTIONS


@dataclass(frozen=True)
class PreparedRun:
    target: TargetSpec
    repo_root: Path
    head: str
    tree: str
    checkout_branch: str
    base_remote_head: str
    checkout_remote_head: str | None
    python_executable: str
    environment_manifest: str
    environment_policy_sha256: str
    environment_fingerprint: str
    module_origin: str
    target_args: tuple[str, ...]

    def command(self) -> list[str]:
        return [self.python_executable, "-m", self.target.module, *self.target_args]


def _run_text(command: Sequence[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RelayPhysicalRunError(
            f"preparation command failed: {' '.join(command)}: {detail}"
        )
    return completed.stdout.strip()


def _repo_identity(repo_root: Path) -> tuple[str, str]:
    if not (repo_root / ".git").exists():
        raise RelayPhysicalRunError(f"not a git checkout: {repo_root}")
    status = _run_text(["git", "status", "--porcelain"], cwd=repo_root)
    if status:
        raise RelayPhysicalRunError("one-shot physical run requires a clean checkout")
    return (
        _run_text(["git", "rev-parse", "HEAD"], cwd=repo_root),
        _run_text(["git", "rev-parse", "HEAD^{tree}"], cwd=repo_root),
    )


def _current_branch(repo_root: Path) -> str:
    return _run_text(["git", "branch", "--show-current"], cwd=repo_root)


def _remote_head(repo_root: Path, branch: str, *, required: bool) -> str | None:
    completed = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RelayPhysicalRunError(
            f"fresh remote authority lookup failed for {branch}: {detail}"
        )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        if required:
            raise RelayPhysicalRunError(
                f"required remote authority ref is unavailable: origin/{branch}"
            )
        return None
    if len(lines) != 1:
        raise RelayPhysicalRunError(
            f"remote authority lookup was ambiguous for origin/{branch}"
        )
    sha, _, ref = lines[0].partition("\t")
    if ref != f"refs/heads/{branch}" or len(sha) != 40:
        raise RelayPhysicalRunError(
            f"malformed remote authority response for origin/{branch}"
        )
    return sha


def _require_base_is_ancestor(repo_root: Path, base_head: str) -> None:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base_head, "HEAD"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode == 0:
        return
    if completed.returncode == 1:
        raise RelayPhysicalRunError(
            "exact checkout is not based on the current protected branch head"
        )
    detail = completed.stderr.decode(errors="replace").strip()
    raise RelayPhysicalRunError(
        "cannot prove protected branch ancestry without mutating the checkout: "
        + detail
    )


def _load_targets(repo_root: Path) -> dict[str, TargetSpec]:
    path = repo_root / TARGETS_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RelayPhysicalRunError(
            f"cannot load llama.cpp target registry: {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise RelayPhysicalRunError("target registry root must be an object")
    if payload.get("schema_version") != TARGET_REGISTRY_SCHEMA_VERSION:
        raise RelayPhysicalRunError(
            "target registry schema_version must be exactly "
            f"{TARGET_REGISTRY_SCHEMA_VERSION}"
        )
    if payload.get("engine") != ENGINE:
        raise RelayPhysicalRunError(
            f"target registry engine must be exactly {ENGINE!r}"
        )
    if payload.get("resource_key") != DEFAULT_RESOURCE_KEY:
        raise RelayPhysicalRunError(
            "target registry resource_key must be exactly "
            f"{DEFAULT_RESOURCE_KEY!r}"
        )
    raw_targets = payload.get("targets")
    if not isinstance(raw_targets, dict) or not raw_targets:
        raise RelayPhysicalRunError("target registry must contain targets")
    targets: dict[str, TargetSpec] = {}
    for name, raw in raw_targets.items():
        if not isinstance(name, str) or not isinstance(raw, dict):
            raise RelayPhysicalRunError("invalid target registry entry")
        module = raw.get("module")
        branch = raw.get("branch")
        description = raw.get("description", "")
        required = raw.get(
            "required_distributions", list(DEFAULT_REQUIRED_DISTRIBUTIONS)
        )
        if (
            not isinstance(module, str)
            or not module
            or not isinstance(branch, str)
            or not branch
            or not isinstance(description, str)
            or not isinstance(required, list)
            or not all(isinstance(item, str) and item for item in required)
        ):
            raise RelayPhysicalRunError(f"invalid target registry entry: {name}")
        targets[name] = TargetSpec(
            name=name,
            module=module,
            branch=branch,
            description=description,
            required_distributions=tuple(required),
        )
    return targets


def _module_origin(module_name: str, repo_root: Path) -> str:
    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, AttributeError, ValueError) as exc:
        raise RelayPhysicalRunError(
            f"target module lookup failed: {module_name}: {exc}"
        ) from exc
    if spec is None or not isinstance(spec.origin, str):
        raise RelayPhysicalRunError(f"target module is unavailable: {module_name}")
    origin = Path(spec.origin).resolve()
    if origin != repo_root and repo_root not in origin.parents:
        raise RelayPhysicalRunError(
            f"target module is not from the exact checkout: {origin}"
        )
    return str(origin)


def _require_distributions(names: Sequence[str]) -> None:
    missing: list[str] = []
    for name in names:
        try:
            importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            missing.append(name)
    if missing:
        raise RelayPhysicalRunError(
            "required runtime distributions are missing: "
            + ", ".join(sorted(missing))
        )


def _normalize_target_args(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise RelayPhysicalRunError("target args must be a sequence of strings")
    normalized = tuple(values)
    if not all(
        isinstance(value, str) and "\x00" not in value for value in normalized
    ):
        raise RelayPhysicalRunError(
            "target args must contain strings without NUL bytes"
        )
    return normalized


def _environment_identity(repo_root: Path) -> PhysicalEnvironmentIdentity:
    try:
        return verify_current_environment(repo_root=repo_root)
    except RelayPhysicalEnvironmentError as exc:
        raise RelayPhysicalRunError(str(exc)) from exc


def prepare_run(
    *,
    repo_root: Path,
    target_name: str,
    target_args: Sequence[str] = (),
) -> PreparedRun:
    repo_root = repo_root.resolve()
    environment = _environment_identity(repo_root)
    targets = _load_targets(repo_root)
    try:
        target = targets[target_name]
    except KeyError as exc:
        raise RelayPhysicalRunError(
            f"unknown llama.cpp physical target: {target_name}"
        ) from exc
    python_executable = environment.python_executable
    if not Path(python_executable).is_file():
        raise RelayPhysicalRunError(
            f"persistent Python executable is unavailable: {python_executable}"
        )
    head, tree = _repo_identity(repo_root)
    checkout_branch = _current_branch(repo_root)
    base_remote_head = _remote_head(repo_root, target.branch, required=True)
    assert base_remote_head is not None
    _require_base_is_ancestor(repo_root, base_remote_head)
    checkout_remote_head = (
        _remote_head(repo_root, checkout_branch, required=False)
        if checkout_branch
        else None
    )
    if checkout_remote_head is not None and checkout_remote_head != head:
        raise RelayPhysicalRunError(
            "local checkout does not match its fresh remote branch head"
        )
    _require_distributions(target.required_distributions)
    module_origin = _module_origin(target.module, repo_root)
    return PreparedRun(
        target=target,
        repo_root=repo_root,
        head=head,
        tree=tree,
        checkout_branch=checkout_branch,
        base_remote_head=base_remote_head,
        checkout_remote_head=checkout_remote_head,
        python_executable=python_executable,
        environment_manifest=str(environment.manifest_path),
        environment_policy_sha256=environment.policy_sha256,
        environment_fingerprint=environment.distribution_fingerprint,
        module_origin=module_origin,
        target_args=_normalize_target_args(target_args),
    )


def final_pre_invoke_gate(prepared: PreparedRun) -> None:
    environment = _environment_identity(prepared.repo_root)
    if environment.python_executable != prepared.python_executable:
        raise RelayPhysicalRunError(
            "persistent Python executable drifted while waiting"
        )
    if environment.policy_sha256 != prepared.environment_policy_sha256:
        raise RelayPhysicalRunError(
            "persistent Python policy drifted while waiting"
        )
    if environment.distribution_fingerprint != prepared.environment_fingerprint:
        raise RelayPhysicalRunError(
            "persistent Python distributions drifted while waiting"
        )
    head, tree = _repo_identity(prepared.repo_root)
    if head != prepared.head or tree != prepared.tree:
        raise RelayPhysicalRunError(
            "exact checkout changed while waiting; rebuild under fresh authority"
        )
    fresh_base = _remote_head(
        prepared.repo_root, prepared.target.branch, required=True
    )
    if fresh_base != prepared.base_remote_head:
        raise RelayPhysicalRunError(
            f"protected {prepared.target.branch} advanced while waiting; "
            "release, reprepare, and requeue without spending the target"
        )
    if prepared.checkout_remote_head is not None and prepared.checkout_branch:
        fresh_checkout = _remote_head(
            prepared.repo_root, prepared.checkout_branch, required=True
        )
        if fresh_checkout != prepared.checkout_remote_head or fresh_checkout != head:
            raise RelayPhysicalRunError(
                "target branch advanced while waiting; release, reprepare, and requeue"
            )
    _require_distributions(prepared.target.required_distributions)
    origin = _module_origin(prepared.target.module, prepared.repo_root)
    if origin != prepared.module_origin:
        raise RelayPhysicalRunError(
            f"target module origin drifted while waiting: {origin}"
        )


def _argv_sha256(values: Sequence[str]) -> str:
    return hashlib.sha256(
        json.dumps(
            list(values),
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "One-shot RelayLM physical runner. The inference engine and shared "
            "resource are fixed to local llama.cpp."
        )
    )
    parser.add_argument("--target")
    parser.add_argument("--list-targets", action="store_true")
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument(
        "target_args",
        nargs=argparse.REMAINDER,
        help=(
            "Target-owned arguments after --; no arbitrary executable is accepted."
        ),
    )
    args = parser.parse_args(argv)
    if args.target_args and args.target_args[0] == "--":
        args.target_args = args.target_args[1:]
    if not args.list_targets and not args.target:
        parser.error("--target is required unless --list-targets is used")
    return args


def _prepare_child_environment(repo_root: Path) -> None:
    os.environ["PYTHONPATH"] = _exact_pythonpath(repo_root)
    os.environ["PYTHONNOUSERSITE"] = "1"


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = _parse_args(raw_argv)
    repo_root = (
        args.repo_root.resolve()
        if args.repo_root is not None
        else Path(__file__).resolve().parents[1]
    )
    targets = _load_targets(repo_root)
    if args.list_targets:
        for name in sorted(targets):
            spec = targets[name]
            print(f"{name}\t{spec.branch}\t{spec.description}")
        return 0

    try:
        reexec_into_environment(repo_root=repo_root, argv=raw_argv)
    except RelayPhysicalEnvironmentError as exc:
        print(
            "relay physical environment blocked: "
            f"{exc}. Prepare it once with "
            "`python3.12 -m tools.relay_physical_env --prepare`.",
            file=sys.stderr,
        )
        return 2

    _prepare_child_environment(repo_root)
    try:
        prepared = prepare_run(
            repo_root=repo_root,
            target_name=args.target,
            target_args=args.target_args,
        )
    except RelayPhysicalRunError as exc:
        print(f"relay physical prepare blocked: {exc}", file=sys.stderr)
        return 2

    command = prepared.command()
    print(
        json.dumps(
            {
                "engine": ENGINE,
                "resource_key": DEFAULT_RESOURCE_KEY,
                "target": prepared.target.name,
                "head": prepared.head,
                "tree": prepared.tree,
                "python": prepared.python_executable,
                "python_environment_manifest": prepared.environment_manifest,
                "python_environment_policy_sha256": prepared.environment_policy_sha256,
                "python_environment_fingerprint": prepared.environment_fingerprint,
                "module": prepared.target.module,
                "target_argv_sha256": _argv_sha256(command),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )

    config = QueueConfig(
        resource_key=DEFAULT_RESOURCE_KEY,
        receipt_path=args.receipt,
        target_label=prepared.target.name,
        cwd=prepared.repo_root,
    )
    try:
        return run_queued_command(
            config,
            command,
            pre_invoke_gate=lambda: final_pre_invoke_gate(prepared),
        )
    except PreInvokeBlocked as exc:
        print(
            f"relay physical final preflight blocked: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

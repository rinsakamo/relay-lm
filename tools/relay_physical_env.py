from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence


POLICY_PATH = Path(".ai/physical/python_environment_policy.json")
DEFAULT_PHYSICAL_HOME = Path.home() / ".local" / "share" / "relaylm" / "physical"
LOCAL_MANIFEST_NAME = "python-environment.json"
VENV_DIRNAME = "venv"


class RelayPhysicalEnvironmentError(RuntimeError):
    pass


@dataclass(frozen=True)
class PhysicalEnvironmentIdentity:
    home: Path
    manifest_path: Path
    python_executable: str
    python_version: str
    implementation: str
    policy_sha256: str
    distribution_fingerprint: str


def physical_home() -> Path:
    configured = os.environ.get("RELAYLM_PHYSICAL_HOME")
    return (
        Path(configured).expanduser().absolute()
        if configured
        else DEFAULT_PHYSICAL_HOME.expanduser().absolute()
    )


def venv_python(home: Path | None = None) -> Path:
    root = physical_home() if home is None else home
    if os.name == "nt":
        return root / VENV_DIRNAME / "Scripts" / "python.exe"
    return root / VENV_DIRNAME / "bin" / "python"


def _canonical_json(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _load_policy(repo_root: Path) -> dict[str, object]:
    path = repo_root / POLICY_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RelayPhysicalEnvironmentError(
            f"cannot load physical Python policy: {path}: {exc}"
        ) from exc
    if payload.get("schema_version") != 1:
        raise RelayPhysicalEnvironmentError(
            "physical Python policy schema_version must be 1"
        )
    python_policy = payload.get("python")
    requirements = payload.get("requirements")
    if (
        not isinstance(python_policy, dict)
        or python_policy.get("implementation") != "CPython"
        or not isinstance(python_policy.get("major"), int)
        or not isinstance(python_policy.get("minor"), int)
        or not isinstance(requirements, list)
        or not requirements
        or not all(isinstance(item, str) and item for item in requirements)
    ):
        raise RelayPhysicalEnvironmentError("invalid physical Python policy")
    return payload


def _policy_sha256(repo_root: Path) -> str:
    return _sha256(_load_policy(repo_root))


def _distribution_map() -> dict[str, str]:
    values: dict[str, str] = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name")
        if not isinstance(name, str) or not name:
            continue
        key = name.strip().lower().replace("_", "-")
        values[key] = dist.version
    return dict(sorted(values.items()))


def _distribution_fingerprint(distributions: Mapping[str, str]) -> str:
    return _sha256(dict(sorted(distributions.items())))


def _runtime_payload() -> dict[str, object]:
    distributions = _distribution_map()
    return {
        "python_executable": str(Path(sys.executable).absolute()),
        "python_version": sys.version,
        "implementation": sys.implementation.name,
        "prefix": str(Path(sys.prefix).absolute()),
        "base_prefix": str(Path(sys.base_prefix).absolute()),
        "distributions": distributions,
        "distribution_fingerprint": _distribution_fingerprint(distributions),
    }


_RUNTIME_SCRIPT = (
    "import json; "
    "from tools.relay_physical_env import _runtime_payload; "
    "print(json.dumps(_runtime_payload(), sort_keys=True))"
)


def _exact_pythonpath(repo_root: Path) -> str:
    return os.pathsep.join((str(repo_root), str(repo_root / "src")))


def _capture_runtime(python_executable: Path, *, repo_root: Path) -> dict[str, object]:
    env = os.environ.copy()
    env["PYTHONPATH"] = _exact_pythonpath(repo_root)
    env["PYTHONNOUSERSITE"] = "1"
    completed = subprocess.run(
        [str(python_executable), "-c", _RUNTIME_SCRIPT],
        cwd=repo_root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RelayPhysicalEnvironmentError(
            f"cannot inspect persistent physical Python: {detail}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RelayPhysicalEnvironmentError(
            "persistent physical Python returned invalid runtime identity"
        ) from exc
    if not isinstance(payload, dict):
        raise RelayPhysicalEnvironmentError(
            "persistent physical Python returned invalid runtime identity"
        )
    return payload


def _load_local_manifest(home: Path) -> dict[str, object]:
    path = home / LOCAL_MANIFEST_NAME
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RelayPhysicalEnvironmentError(
            f"persistent physical Python manifest is unavailable: {path}: {exc}"
        ) from exc
    if payload.get("schema_version") != 1:
        raise RelayPhysicalEnvironmentError(
            "persistent physical Python manifest schema_version must be 1"
        )
    return payload


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def _require_policy_python(policy: Mapping[str, object]) -> None:
    python_policy = policy["python"]
    assert isinstance(python_policy, dict)
    required = (
        python_policy["implementation"],
        python_policy["major"],
        python_policy["minor"],
    )
    actual = (
        "CPython" if sys.implementation.name == "cpython" else sys.implementation.name,
        sys.version_info.major,
        sys.version_info.minor,
    )
    if actual != required:
        raise RelayPhysicalEnvironmentError(
            "physical environment bootstrap requires exactly "
            f"{required[0]} {required[1]}.{required[2]}; current is "
            f"{actual[0]} {actual[1]}.{actual[2]}"
        )


def verify_environment(
    *,
    repo_root: Path,
    home: Path | None = None,
) -> PhysicalEnvironmentIdentity:
    repo_root = repo_root.resolve()
    home = physical_home() if home is None else home.absolute()
    policy_sha = _policy_sha256(repo_root)
    manifest = _load_local_manifest(home)
    if manifest.get("policy_sha256") != policy_sha:
        raise RelayPhysicalEnvironmentError(
            "persistent physical Python policy changed; explicit rebuild is required"
        )
    python_path = venv_python(home).absolute()
    if not python_path.is_file():
        raise RelayPhysicalEnvironmentError(
            f"persistent physical Python executable is unavailable: {python_path}"
        )
    runtime = _capture_runtime(python_path, repo_root=repo_root)
    expected_python = str(python_path)
    if runtime.get("python_executable") != expected_python:
        raise RelayPhysicalEnvironmentError(
            "persistent physical Python executable identity drifted"
        )
    if runtime.get("prefix") != str((home / VENV_DIRNAME).absolute()):
        raise RelayPhysicalEnvironmentError(
            "persistent physical Python is not running from the expected venv"
        )
    if runtime.get("base_prefix") == runtime.get("prefix"):
        raise RelayPhysicalEnvironmentError(
            "persistent physical Python is not an isolated venv"
        )
    for key in (
        "python_executable",
        "python_version",
        "implementation",
        "distribution_fingerprint",
    ):
        if runtime.get(key) != manifest.get(key):
            raise RelayPhysicalEnvironmentError(
                f"persistent physical Python {key} drifted; explicit rebuild is required"
            )
    return PhysicalEnvironmentIdentity(
        home=home,
        manifest_path=home / LOCAL_MANIFEST_NAME,
        python_executable=expected_python,
        python_version=str(runtime["python_version"]),
        implementation=str(runtime["implementation"]),
        policy_sha256=policy_sha,
        distribution_fingerprint=str(runtime["distribution_fingerprint"]),
    )


def verify_current_environment(
    *,
    repo_root: Path,
    home: Path | None = None,
) -> PhysicalEnvironmentIdentity:
    identity = verify_environment(repo_root=repo_root, home=home)
    current = str(Path(sys.executable).absolute())
    if current != identity.python_executable:
        raise RelayPhysicalEnvironmentError(
            "one-shot runner is not executing from the persistent physical venv"
        )
    return identity


def prepare_environment(
    *,
    repo_root: Path,
    home: Path | None = None,
    rebuild: bool = False,
) -> PhysicalEnvironmentIdentity:
    repo_root = repo_root.resolve()
    home = physical_home() if home is None else home.absolute()
    policy = _load_policy(repo_root)
    _require_policy_python(policy)
    manifest_path = home / LOCAL_MANIFEST_NAME
    venv_root = home / VENV_DIRNAME

    if rebuild:
        if venv_root.exists():
            shutil.rmtree(venv_root)
        manifest_path.unlink(missing_ok=True)
    elif venv_root.exists() or manifest_path.exists():
        try:
            return verify_environment(repo_root=repo_root, home=home)
        except RelayPhysicalEnvironmentError as exc:
            raise RelayPhysicalEnvironmentError(
                f"{exc}; run explicit --rebuild to replace the persistent environment"
            ) from exc

    home.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [sys.executable, "-m", "venv", str(venv_root)],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RelayPhysicalEnvironmentError(
            f"cannot create persistent physical venv: {detail}"
        )

    python_path = venv_python(home).absolute()
    requirements = policy["requirements"]
    assert isinstance(requirements, list)
    completed = subprocess.run(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            *requirements,
        ],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RelayPhysicalEnvironmentError(
            f"cannot populate persistent physical venv: {detail}"
        )

    runtime = _capture_runtime(python_path, repo_root=repo_root)
    manifest = {
        "schema_version": 1,
        "policy_sha256": _sha256(policy),
        "python_executable": runtime["python_executable"],
        "python_version": runtime["python_version"],
        "implementation": runtime["implementation"],
        "distribution_fingerprint": runtime["distribution_fingerprint"],
        "distributions": runtime["distributions"],
    }
    _atomic_write_json(manifest_path, manifest)
    return verify_environment(repo_root=repo_root, home=home)


def reexec_into_environment(
    *,
    repo_root: Path,
    argv: Sequence[str],
) -> PhysicalEnvironmentIdentity:
    identity = verify_environment(repo_root=repo_root)
    current = str(Path(sys.executable).absolute())
    if current == identity.python_executable:
        return identity
    env = os.environ.copy()
    env["PYTHONPATH"] = _exact_pythonpath(repo_root)
    env["PYTHONNOUSERSITE"] = "1"
    os.execve(
        identity.python_executable,
        [
            identity.python_executable,
            "-m",
            "tools.relay_physical_run",
            *argv,
        ],
        env,
    )
    raise AssertionError("os.execve returned unexpectedly")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare or verify the persistent RelayLM physical Python environment."
    )
    parser.add_argument("--repo-root", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--rebuild", action="store_true")
    mode.add_argument("--status", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = (
        args.repo_root.resolve()
        if args.repo_root is not None
        else Path(__file__).resolve().parents[1]
    )
    try:
        if args.status:
            identity = verify_environment(repo_root=repo_root)
            action = "verified"
        else:
            identity = prepare_environment(
                repo_root=repo_root,
                rebuild=bool(args.rebuild),
            )
            action = "prepared"
    except RelayPhysicalEnvironmentError as exc:
        print(f"relay physical environment blocked: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "action": action,
                "home": str(identity.home),
                "manifest": str(identity.manifest_path),
                "python": identity.python_executable,
                "python_version": identity.python_version,
                "policy_sha256": identity.policy_sha256,
                "distribution_fingerprint": identity.distribution_fingerprint,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

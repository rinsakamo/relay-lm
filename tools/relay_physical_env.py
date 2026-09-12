from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import uuid
from collections.abc import Iterator, Sequence
from dataclasses import dataclass


POLICY_PATH = Path(".ai/physical/python_environment_policy.json")
DEFAULT_PHYSICAL_HOME = Path.home() / ".local" / "share" / "relaylm" / "physical"
ENVIRONMENTS_DIRNAME = "environments"
INSTANCES_DIRNAME = "instances"
LOCKS_DIRNAME = "locks"
CURRENT_POINTER_NAME = "current.json"
VENV_DIRNAME = "venv"
LOCAL_MANIFEST_NAME = "python-environment.json"
POINTER_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 1


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
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_PHYSICAL_HOME.expanduser().resolve()


def venv_python(home: Path) -> Path:
    if os.name == "nt":
        return home / VENV_DIRNAME / "Scripts" / "python.exe"
    return home / VENV_DIRNAME / "bin" / "python"


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def _load_policy(repo_root: Path) -> dict[str, object]:
    path = repo_root / POLICY_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RelayPhysicalEnvironmentError(
            f"cannot load physical Python policy: {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise RelayPhysicalEnvironmentError("physical Python policy root must be an object")
    if payload.get("schema_version") != 1:
        raise RelayPhysicalEnvironmentError("physical Python policy schema_version must be 1")
    python = payload.get("python")
    requirements = payload.get("requirements")
    if (
        not isinstance(python, dict)
        or python.get("implementation") != "CPython"
        or not isinstance(python.get("major"), int)
        or not isinstance(python.get("minor"), int)
        or not isinstance(requirements, list)
        or not requirements
        or not all(isinstance(item, str) and item for item in requirements)
    ):
        raise RelayPhysicalEnvironmentError("invalid physical Python policy")
    return payload


def _policy_sha256(repo_root: Path) -> str:
    return hashlib.sha256(_canonical_json_bytes(_load_policy(repo_root))).hexdigest()


def _distribution_fingerprint(distributions: dict[str, str]) -> str:
    return hashlib.sha256(_canonical_json_bytes(distributions)).hexdigest()


def _exact_pythonpath(repo_root: Path) -> str:
    return os.pathsep.join((str(repo_root.resolve()), str((repo_root / "src").resolve())))


def _capture_runtime(python_executable: Path, repo_root: Path) -> dict[str, object]:
    script = "\n".join(
        [
            "import hashlib, importlib.metadata, json, sys",
            "items = {}",
            "for distribution in importlib.metadata.distributions():",
            "    name = distribution.metadata.get('Name')",
            "    if isinstance(name, str):",
            "        key = name.strip().lower().replace('_', '-')",
            "        if key:",
            "            items[key] = distribution.version",
            "raw = json.dumps(items, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode('utf-8')",
            "print(json.dumps({",
            "    'python_executable': sys.executable,",
            "    'python_version': sys.version,",
            "    'implementation': sys.implementation.name,",
            "    'prefix': sys.prefix,",
            "    'base_prefix': sys.base_prefix,",
            "    'distributions': items,",
            "    'distribution_fingerprint': hashlib.sha256(raw).hexdigest(),",
            "}, sort_keys=True))",
        ]
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = _exact_pythonpath(repo_root)
    environment["PYTHONNOUSERSITE"] = "1"
    completed = subprocess.run(
        [str(python_executable), "-c", script],
        cwd=repo_root,
        env=environment,
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
            "persistent physical Python returned invalid identity JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise RelayPhysicalEnvironmentError("invalid persistent Python identity")
    return payload


def _require_policy_python(policy: dict[str, object]) -> None:
    python = policy["python"]
    assert isinstance(python, dict)
    expected_implementation = python["implementation"]
    expected_major = python["major"]
    expected_minor = python["minor"]
    actual_implementation = platform.python_implementation()
    if (
        expected_implementation != actual_implementation
        or expected_major != sys.version_info.major
        or expected_minor != sys.version_info.minor
    ):
        raise RelayPhysicalEnvironmentError(
            "physical Python bootstrap must match policy: "
            f"expected {expected_implementation} {expected_major}.{expected_minor}, "
            f"got {actual_implementation} {sys.version_info.major}.{sys.version_info.minor}"
        )


def _environment_namespace(root: Path, policy_sha256: str) -> Path:
    return root / ENVIRONMENTS_DIRNAME / policy_sha256


def _instances_root(root: Path, policy_sha256: str) -> Path:
    return _environment_namespace(root, policy_sha256) / INSTANCES_DIRNAME


def _current_pointer_path(root: Path, policy_sha256: str) -> Path:
    return _environment_namespace(root, policy_sha256) / CURRENT_POINTER_NAME


def _prepare_lock_path(root: Path, policy_sha256: str) -> Path:
    return root / LOCKS_DIRNAME / f"python-env-{policy_sha256}.lock"


def _valid_instance_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 32
        and all(character in "0123456789abcdef" for character in value)
    )


def _load_current_pointer(root: Path, policy_sha256: str) -> dict[str, object]:
    path = _current_pointer_path(root, policy_sha256)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RelayPhysicalEnvironmentError(
            f"persistent physical Python environment is not prepared for policy {policy_sha256}"
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RelayPhysicalEnvironmentError(
            f"cannot load persistent physical Python pointer: {path}: {exc}"
        ) from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != POINTER_SCHEMA_VERSION
        or payload.get("policy_sha256") != policy_sha256
        or not _valid_instance_id(payload.get("instance_id"))
    ):
        raise RelayPhysicalEnvironmentError(
            f"invalid persistent physical Python pointer: {path}"
        )
    return payload


def _current_instance_home(root: Path, policy_sha256: str) -> Path:
    pointer = _load_current_pointer(root, policy_sha256)
    instance_id = pointer["instance_id"]
    assert isinstance(instance_id, str)
    return _instances_root(root, policy_sha256) / instance_id


@contextmanager
def _policy_prepare_lock(root: Path, policy_sha256: str) -> Iterator[None]:
    path = _prepare_lock_path(root, policy_sha256)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _load_local_manifest(instance_home: Path) -> dict[str, object]:
    path = instance_home / LOCAL_MANIFEST_NAME
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RelayPhysicalEnvironmentError(
            f"cannot load persistent physical Python manifest: {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise RelayPhysicalEnvironmentError(
            "persistent physical Python manifest schema_version must be 1"
        )
    return payload


def _verify_instance(
    *,
    repo_root: Path,
    instance_home: Path,
    policy_sha256: str,
) -> PhysicalEnvironmentIdentity:
    manifest = _load_local_manifest(instance_home)
    if manifest.get("policy_sha256") != policy_sha256:
        raise RelayPhysicalEnvironmentError(
            "persistent physical Python policy hash drifted"
        )
    if manifest.get("instance_id") != instance_home.name:
        raise RelayPhysicalEnvironmentError(
            "persistent physical Python instance identity drifted"
        )
    python_path = venv_python(instance_home).absolute()
    if not python_path.is_file():
        raise RelayPhysicalEnvironmentError(
            f"persistent physical Python executable is unavailable: {python_path}"
        )
    runtime = _capture_runtime(python_path, repo_root)
    expected_prefix = str((instance_home / VENV_DIRNAME).absolute())
    checks = {
        "python_executable": str(python_path),
        "python_version": manifest.get("python_version"),
        "implementation": manifest.get("implementation"),
        "prefix": expected_prefix,
        "distribution_fingerprint": manifest.get("distribution_fingerprint"),
    }
    for key, expected in checks.items():
        if runtime.get(key) != expected:
            raise RelayPhysicalEnvironmentError(
                f"persistent physical Python {key} drifted: "
                f"expected {expected!r}, got {runtime.get(key)!r}"
            )
    if runtime.get("base_prefix") == runtime.get("prefix"):
        raise RelayPhysicalEnvironmentError(
            "persistent physical Python is not an isolated venv"
        )
    manifest_distributions = manifest.get("distributions")
    if not isinstance(manifest_distributions, dict):
        raise RelayPhysicalEnvironmentError(
            "persistent physical Python manifest distributions are invalid"
        )
    if runtime.get("distributions") != manifest_distributions:
        raise RelayPhysicalEnvironmentError(
            "persistent physical Python installed distributions drifted"
        )
    return PhysicalEnvironmentIdentity(
        home=instance_home,
        manifest_path=instance_home / LOCAL_MANIFEST_NAME,
        python_executable=str(python_path),
        python_version=str(runtime["python_version"]),
        implementation=str(runtime["implementation"]),
        policy_sha256=policy_sha256,
        distribution_fingerprint=str(runtime["distribution_fingerprint"]),
    )


def verify_environment(
    *,
    repo_root: Path,
    home: Path | None = None,
) -> PhysicalEnvironmentIdentity:
    repo_root = repo_root.resolve()
    root = physical_home() if home is None else home.expanduser().resolve()
    policy_sha256 = _policy_sha256(repo_root)
    instance_home = _current_instance_home(root, policy_sha256)
    return _verify_instance(
        repo_root=repo_root,
        instance_home=instance_home,
        policy_sha256=policy_sha256,
    )


def verify_current_environment(
    *,
    repo_root: Path,
    home: Path | None = None,
) -> PhysicalEnvironmentIdentity:
    identity = verify_environment(repo_root=repo_root, home=home)
    if Path(sys.executable).resolve() != Path(identity.python_executable).resolve():
        raise RelayPhysicalEnvironmentError(
            "physical runner is not executing inside the selected persistent Python"
        )
    return identity


def _create_environment_instance(
    *,
    repo_root: Path,
    root: Path,
    policy: dict[str, object],
    policy_sha256: str,
) -> PhysicalEnvironmentIdentity:
    instance_id = uuid.uuid4().hex
    instance_home = _instances_root(root, policy_sha256) / instance_id
    instance_home.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(instance_home / VENV_DIRNAME)],
            cwd=repo_root,
            check=True,
        )
        python_path = venv_python(instance_home)
        requirements = policy["requirements"]
        assert isinstance(requirements, list)
        subprocess.run(
            [
                str(python_path),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                *requirements,
            ],
            cwd=repo_root,
            check=True,
        )
        runtime = _capture_runtime(python_path, repo_root)
        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "instance_id": instance_id,
            "policy_sha256": policy_sha256,
            "python_executable": runtime["python_executable"],
            "python_version": runtime["python_version"],
            "implementation": runtime["implementation"],
            "distribution_fingerprint": runtime["distribution_fingerprint"],
            "distributions": runtime["distributions"],
        }
        _atomic_write_json(instance_home / LOCAL_MANIFEST_NAME, manifest)
        return _verify_instance(
            repo_root=repo_root,
            instance_home=instance_home,
            policy_sha256=policy_sha256,
        )
    except BaseException:
        shutil.rmtree(instance_home, ignore_errors=True)
        raise


def _select_current_instance(
    *,
    root: Path,
    policy_sha256: str,
    identity: PhysicalEnvironmentIdentity,
) -> None:
    pointer = {
        "schema_version": POINTER_SCHEMA_VERSION,
        "policy_sha256": policy_sha256,
        "instance_id": identity.home.name,
    }
    try:
        _atomic_write_json(_current_pointer_path(root, policy_sha256), pointer)
    except OSError as exc:
        shutil.rmtree(identity.home, ignore_errors=True)
        raise RelayPhysicalEnvironmentError(
            f"cannot publish persistent physical Python pointer: {exc}"
        ) from exc


def prepare_environment(
    *,
    repo_root: Path,
    home: Path | None = None,
    rebuild: bool = False,
) -> PhysicalEnvironmentIdentity:
    repo_root = repo_root.resolve()
    root = physical_home() if home is None else home.expanduser().resolve()
    policy = _load_policy(repo_root)
    _require_policy_python(policy)
    policy_sha256 = hashlib.sha256(_canonical_json_bytes(policy)).hexdigest()

    with _policy_prepare_lock(root, policy_sha256):
        pointer_path = _current_pointer_path(root, policy_sha256)
        if pointer_path.exists() and not rebuild:
            try:
                return verify_environment(repo_root=repo_root, home=root)
            except RelayPhysicalEnvironmentError as exc:
                raise RelayPhysicalEnvironmentError(
                    f"persistent physical Python drifted: {exc}; "
                    "use explicit --rebuild outside a physical transaction"
                ) from exc

        identity = _create_environment_instance(
            repo_root=repo_root,
            root=root,
            policy=policy,
            policy_sha256=policy_sha256,
        )
        _select_current_instance(
            root=root,
            policy_sha256=policy_sha256,
            identity=identity,
        )
        return identity


def reexec_into_environment(*, repo_root: Path, argv: Sequence[str]) -> None:
    identity = verify_environment(repo_root=repo_root)
    target = Path(identity.python_executable).resolve()
    if Path(sys.executable).resolve() == target:
        return
    environment = dict(os.environ)
    environment["PYTHONPATH"] = _exact_pythonpath(repo_root)
    environment["PYTHONNOUSERSITE"] = "1"
    os.execve(
        str(target),
        [str(target), "-m", "tools.relay_physical_run", *argv],
        environment,
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare or inspect the persistent local Python used by RelayLM "
            "llama.cpp physical execution."
        )
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--status", action="store_true")
    action.add_argument("--rebuild", action="store_true")
    parser.add_argument("--repo-root", type=Path)
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
        else:
            identity = prepare_environment(
                repo_root=repo_root,
                rebuild=bool(args.rebuild),
            )
    except (RelayPhysicalEnvironmentError, subprocess.CalledProcessError) as exc:
        print(f"relay physical Python blocked: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "physical_root": str(physical_home()),
                "home": str(identity.home),
                "manifest": str(identity.manifest_path),
                "python": identity.python_executable,
                "python_version": identity.python_version,
                "implementation": identity.implementation,
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

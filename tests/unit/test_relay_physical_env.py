from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

import tools.relay_physical_env as envtool


def _write_policy(repo_root: Path, *, requirement: str = "httpx>=0.28") -> None:
    path = repo_root / envtool.POLICY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "python": {
                    "implementation": "CPython",
                    "major": 3,
                    "minor": 12,
                },
                "requirements": [requirement],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _install_fake_runtime_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    def capture(python_executable: Path, repo_root: Path) -> dict[str, object]:
        del repo_root
        instance_home = python_executable.parents[2]
        manifest = json.loads(
            (instance_home / envtool.LOCAL_MANIFEST_NAME).read_text(encoding="utf-8")
        )
        return {
            "python_executable": str(python_executable.absolute()),
            "python_version": manifest["python_version"],
            "implementation": manifest["implementation"],
            "prefix": str((instance_home / envtool.VENV_DIRNAME).absolute()),
            "base_prefix": "/usr",
            "distributions": manifest["distributions"],
            "distribution_fingerprint": manifest["distribution_fingerprint"],
        }

    monkeypatch.setattr(envtool, "_capture_runtime", capture)


def _write_fake_instance(
    *,
    root: Path,
    policy_sha256: str,
    instance_id: str,
) -> envtool.PhysicalEnvironmentIdentity:
    instance_home = envtool._instances_root(root, policy_sha256) / instance_id
    python = envtool.venv_python(instance_home)
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text("fake-python", encoding="utf-8")
    distributions = {"httpx": "0.28.1", "pyyaml": "6.0.2"}
    fingerprint = envtool._distribution_fingerprint(distributions)
    manifest = {
        "schema_version": envtool.MANIFEST_SCHEMA_VERSION,
        "instance_id": instance_id,
        "policy_sha256": policy_sha256,
        "python_executable": str(python.absolute()),
        "python_version": "3.12.10",
        "implementation": "cpython",
        "distribution_fingerprint": fingerprint,
        "distributions": distributions,
    }
    envtool._atomic_write_json(instance_home / envtool.LOCAL_MANIFEST_NAME, manifest)
    return envtool.PhysicalEnvironmentIdentity(
        home=instance_home,
        manifest_path=instance_home / envtool.LOCAL_MANIFEST_NAME,
        python_executable=str(python.absolute()),
        python_version="3.12.10",
        implementation="cpython",
        policy_sha256=policy_sha256,
        distribution_fingerprint=fingerprint,
    )


def _install_fake_builder(
    monkeypatch: pytest.MonkeyPatch,
    *,
    created: list[envtool.PhysicalEnvironmentIdentity],
) -> None:
    def create(
        *,
        repo_root: Path,
        root: Path,
        policy: dict[str, object],
        policy_sha256: str,
    ) -> envtool.PhysicalEnvironmentIdentity:
        del repo_root, policy
        identity = _write_fake_instance(
            root=root,
            policy_sha256=policy_sha256,
            instance_id=f"{len(created) + 1:032x}",
        )
        created.append(identity)
        return identity

    monkeypatch.setattr(envtool, "_create_environment_instance", create)


def test_distribution_fingerprint_is_order_independent() -> None:
    left = envtool._distribution_fingerprint({"b": "2", "a": "1"})
    right = envtool._distribution_fingerprint({"a": "1", "b": "2"})
    assert left == right


def test_policy_rejects_empty_requirements(tmp_path: Path) -> None:
    path = tmp_path / envtool.POLICY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "python": {
                    "implementation": "CPython",
                    "major": 3,
                    "minor": 12,
                },
                "requirements": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(envtool.RelayPhysicalEnvironmentError, match="invalid"):
        envtool._load_policy(tmp_path)


def test_policy_rejects_non_cpython_identity(tmp_path: Path) -> None:
    path = tmp_path / envtool.POLICY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "python": {
                    "implementation": "PyPy",
                    "major": 3,
                    "minor": 12,
                },
                "requirements": ["httpx>=0.28"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(envtool.RelayPhysicalEnvironmentError, match="invalid"):
        envtool._load_policy(tmp_path)


def test_verify_environment_accepts_frozen_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_policy(tmp_path)
    root = tmp_path / "physical"
    policy_sha256 = envtool._policy_sha256(tmp_path)
    _install_fake_runtime_capture(monkeypatch)
    identity = _write_fake_instance(
        root=root,
        policy_sha256=policy_sha256,
        instance_id="1" * 32,
    )
    envtool._select_current_instance(
        root=root,
        policy_sha256=policy_sha256,
        identity=identity,
    )

    verified = envtool.verify_environment(repo_root=tmp_path, home=root)

    assert verified == identity


def test_verify_environment_rejects_non_isolated_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_policy(tmp_path)
    root = tmp_path / "physical"
    policy_sha256 = envtool._policy_sha256(tmp_path)
    identity = _write_fake_instance(
        root=root,
        policy_sha256=policy_sha256,
        instance_id="4" * 32,
    )
    envtool._select_current_instance(
        root=root,
        policy_sha256=policy_sha256,
        identity=identity,
    )

    def non_isolated_capture(
        python_executable: Path,
        repo_root: Path,
    ) -> dict[str, object]:
        del repo_root
        manifest = json.loads(identity.manifest_path.read_text(encoding="utf-8"))
        prefix = str((identity.home / envtool.VENV_DIRNAME).absolute())
        return {
            "python_executable": str(python_executable.absolute()),
            "python_version": manifest["python_version"],
            "implementation": manifest["implementation"],
            "prefix": prefix,
            "base_prefix": prefix,
            "distributions": manifest["distributions"],
            "distribution_fingerprint": manifest["distribution_fingerprint"],
        }

    monkeypatch.setattr(envtool, "_capture_runtime", non_isolated_capture)
    with pytest.raises(
        envtool.RelayPhysicalEnvironmentError,
        match="not an isolated venv",
    ):
        envtool.verify_environment(repo_root=tmp_path, home=root)


def test_verify_environment_rejects_distribution_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_policy(tmp_path)
    root = tmp_path / "physical"
    policy_sha256 = envtool._policy_sha256(tmp_path)
    identity = _write_fake_instance(
        root=root,
        policy_sha256=policy_sha256,
        instance_id="2" * 32,
    )
    envtool._select_current_instance(
        root=root,
        policy_sha256=policy_sha256,
        identity=identity,
    )

    def drifted_capture(
        python_executable: Path,
        repo_root: Path,
    ) -> dict[str, object]:
        del repo_root
        return {
            "python_executable": str(python_executable.absolute()),
            "python_version": "3.12.10",
            "implementation": "cpython",
            "prefix": str((identity.home / envtool.VENV_DIRNAME).absolute()),
            "base_prefix": "/usr",
            "distributions": {"httpx": "0.29.0"},
            "distribution_fingerprint": envtool._distribution_fingerprint(
                {"httpx": "0.29.0"}
            ),
        }

    monkeypatch.setattr(envtool, "_capture_runtime", drifted_capture)
    with pytest.raises(
        envtool.RelayPhysicalEnvironmentError,
        match="distribution_fingerprint drifted",
    ):
        envtool.verify_environment(repo_root=tmp_path, home=root)


def test_prepare_reuses_matching_current_instance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_policy(tmp_path)
    root = tmp_path / "physical"
    policy_sha256 = envtool._policy_sha256(tmp_path)
    _install_fake_runtime_capture(monkeypatch)
    identity = _write_fake_instance(
        root=root,
        policy_sha256=policy_sha256,
        instance_id="3" * 32,
    )
    envtool._select_current_instance(
        root=root,
        policy_sha256=policy_sha256,
        identity=identity,
    )
    monkeypatch.setattr(envtool, "_require_policy_python", lambda policy: None)

    def forbidden_create(**kwargs):
        del kwargs
        raise AssertionError("matching environment must be reused")

    monkeypatch.setattr(envtool, "_create_environment_instance", forbidden_create)

    prepared = envtool.prepare_environment(repo_root=tmp_path, home=root)

    assert prepared == identity


def test_different_policy_identities_coexist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "physical"
    created: list[envtool.PhysicalEnvironmentIdentity] = []
    monkeypatch.setattr(envtool, "_require_policy_python", lambda policy: None)
    _install_fake_runtime_capture(monkeypatch)
    _install_fake_builder(monkeypatch, created=created)

    _write_policy(tmp_path, requirement="httpx>=0.28")
    first = envtool.prepare_environment(repo_root=tmp_path, home=root)
    first_pointer = envtool._current_pointer_path(root, first.policy_sha256)

    _write_policy(tmp_path, requirement="httpx>=0.29")
    second = envtool.prepare_environment(repo_root=tmp_path, home=root)
    second_pointer = envtool._current_pointer_path(root, second.policy_sha256)

    assert first.policy_sha256 != second.policy_sha256
    assert first.home != second.home
    assert first_pointer.is_file()
    assert second_pointer.is_file()
    assert Path(first.python_executable).is_file()
    assert Path(second.python_executable).is_file()
    assert len(created) == 2

    _write_policy(tmp_path, requirement="httpx>=0.28")
    first_again = envtool.prepare_environment(repo_root=tmp_path, home=root)
    assert first_again.home == first.home
    assert len(created) == 2


def test_rebuild_switches_pointer_without_destroying_previous_instance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_policy(tmp_path)
    root = tmp_path / "physical"
    created: list[envtool.PhysicalEnvironmentIdentity] = []
    monkeypatch.setattr(envtool, "_require_policy_python", lambda policy: None)
    _install_fake_runtime_capture(monkeypatch)
    _install_fake_builder(monkeypatch, created=created)

    first = envtool.prepare_environment(repo_root=tmp_path, home=root)
    second = envtool.prepare_environment(repo_root=tmp_path, home=root, rebuild=True)

    assert first.home != second.home
    assert Path(first.python_executable).is_file()
    assert first.manifest_path.is_file()
    assert Path(second.python_executable).is_file()
    assert envtool.verify_environment(repo_root=tmp_path, home=root) == second


def test_policy_prepare_lock_serializes_cross_process_creation(tmp_path: Path) -> None:
    root = tmp_path / "physical"
    policy_sha256 = "a" * 64
    lock_path = envtool._prepare_lock_path(root, policy_sha256)
    ready_marker = tmp_path / "ready"
    acquired_marker = tmp_path / "acquired"
    helper_code = "\n".join(
        [
            "import fcntl, sys",
            "from pathlib import Path",
            "lock_path = Path(sys.argv[1])",
            "ready = Path(sys.argv[2])",
            "acquired = Path(sys.argv[3])",
            "handle = lock_path.open('a+')",
            "ready.write_text('ready')",
            "fcntl.flock(handle.fileno(), fcntl.LOCK_EX)",
            "acquired.write_text('acquired')",
            "fcntl.flock(handle.fileno(), fcntl.LOCK_UN)",
            "handle.close()",
        ]
    )

    with envtool._policy_prepare_lock(root, policy_sha256):
        helper = subprocess.Popen(
            [
                sys.executable,
                "-c",
                helper_code,
                str(lock_path),
                str(ready_marker),
                str(acquired_marker),
            ]
        )
        deadline = time.monotonic() + 2.0
        while not ready_marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready_marker.read_text(encoding="utf-8") == "ready"
        assert helper.poll() is None
        assert acquired_marker.exists() is False

    assert helper.wait(timeout=2) == 0
    assert acquired_marker.read_text(encoding="utf-8") == "acquired"

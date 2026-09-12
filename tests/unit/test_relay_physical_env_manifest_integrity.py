from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.relay_physical_env as envtool


def _write_policy(
    root: Path,
    *,
    schema_version: object = 1,
    major: object = 3,
    minor: object = 12,
) -> None:
    path = root / envtool.POLICY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": schema_version,
                "python": {
                    "implementation": "CPython",
                    "major": major,
                    "minor": minor,
                },
                "requirements": ["httpx>=0.28"],
            }
        ),
        encoding="utf-8",
    )


def test_policy_rejects_boolean_schema_version(tmp_path: Path) -> None:
    _write_policy(tmp_path, schema_version=True)
    with pytest.raises(
        envtool.RelayPhysicalEnvironmentError,
        match="schema_version must be integer 1",
    ):
        envtool._load_policy(tmp_path)


def test_policy_rejects_boolean_python_version_components(tmp_path: Path) -> None:
    _write_policy(tmp_path, major=True)
    with pytest.raises(envtool.RelayPhysicalEnvironmentError, match="invalid physical Python policy"):
        envtool._load_policy(tmp_path)

    _write_policy(tmp_path, minor=False)
    with pytest.raises(envtool.RelayPhysicalEnvironmentError, match="invalid physical Python policy"):
        envtool._load_policy(tmp_path)


def test_local_pointer_and_manifest_reject_boolean_schema_versions(
    tmp_path: Path,
) -> None:
    physical_root = tmp_path / "physical"
    policy_sha256 = "a" * 64
    instance_id = "1" * 32

    envtool._atomic_write_json(
        envtool._current_pointer_path(physical_root, policy_sha256),
        {
            "schema_version": True,
            "policy_sha256": policy_sha256,
            "instance_id": instance_id,
        },
    )
    with pytest.raises(
        envtool.RelayPhysicalEnvironmentError,
        match="invalid persistent physical Python pointer",
    ):
        envtool._load_current_pointer(physical_root, policy_sha256)

    instance_home = envtool._instances_root(physical_root, policy_sha256) / instance_id
    envtool._atomic_write_json(
        instance_home / envtool.LOCAL_MANIFEST_NAME,
        {"schema_version": True},
    )
    with pytest.raises(
        envtool.RelayPhysicalEnvironmentError,
        match="schema_version must be integer 1",
    ):
        envtool._load_local_manifest(instance_home)


def test_manifest_python_executable_drift_is_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_policy(tmp_path)
    physical_root = tmp_path / "physical"
    policy_sha256 = envtool._policy_sha256(tmp_path)
    instance_id = "1" * 32
    instance_home = envtool._instances_root(physical_root, policy_sha256) / instance_id
    python_path = envtool.venv_python(instance_home).absolute()
    python_path.parent.mkdir(parents=True, exist_ok=True)
    python_path.write_text("", encoding="utf-8")

    distributions = {"httpx": "0.28.1"}
    fingerprint = envtool._distribution_fingerprint(distributions)
    runtime = {
        "python_executable": str(python_path),
        "python_version": "3.12-test",
        "implementation": "cpython",
        "prefix": str((instance_home / envtool.VENV_DIRNAME).absolute()),
        "base_prefix": "/base-python",
        "distributions": distributions,
        "distribution_fingerprint": fingerprint,
    }
    manifest = {
        "schema_version": envtool.MANIFEST_SCHEMA_VERSION,
        "instance_id": instance_id,
        "policy_sha256": policy_sha256,
        "python_executable": "/tampered/python",
        "python_version": runtime["python_version"],
        "implementation": runtime["implementation"],
        "distribution_fingerprint": fingerprint,
        "distributions": distributions,
    }
    envtool._atomic_write_json(instance_home / envtool.LOCAL_MANIFEST_NAME, manifest)
    envtool._atomic_write_json(
        envtool._current_pointer_path(physical_root, policy_sha256),
        {
            "schema_version": envtool.POINTER_SCHEMA_VERSION,
            "policy_sha256": policy_sha256,
            "instance_id": instance_id,
        },
    )
    monkeypatch.setattr(envtool, "_capture_runtime", lambda *_args: runtime)

    with pytest.raises(
        envtool.RelayPhysicalEnvironmentError,
        match="manifest executable identity drifted",
    ):
        envtool.verify_environment(repo_root=tmp_path, home=physical_root)

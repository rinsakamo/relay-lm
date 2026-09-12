from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.relay_physical_env as envtool


def _write_policy(root: Path) -> None:
    path = root / envtool.POLICY_PATH
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "python": {
                    "implementation": "CPython",
                    "major": 3,
                    "minor": 12,
                },
                "requirements": [
                    "httpx>=0.28",
                ],
            }
        ),
        encoding="utf-8",
    )


def _runtime(python: Path, home: Path, *, fingerprint: str = "fp") -> dict[str, object]:
    return {
        "python_executable": str(python.absolute()),
        "python_version": "3.12.test",
        "implementation": "cpython",
        "prefix": str((home / envtool.VENV_DIRNAME).absolute()),
        "base_prefix": "/usr",
        "distributions": {"httpx": "0.28.1"},
        "distribution_fingerprint": fingerprint,
    }


def test_distribution_fingerprint_is_order_independent() -> None:
    left = envtool._distribution_fingerprint({"httpx": "1", "pydantic": "2"})
    right = envtool._distribution_fingerprint({"pydantic": "2", "httpx": "1"})
    assert left == right


def test_verify_environment_accepts_frozen_local_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_policy(tmp_path)
    home = tmp_path / "physical"
    python = envtool.venv_python(home)
    python.parent.mkdir(parents=True)
    python.write_text("# placeholder", encoding="utf-8")
    runtime = _runtime(python, home)
    manifest = {
        "schema_version": 1,
        "policy_sha256": envtool._policy_sha256(tmp_path),
        "python_executable": runtime["python_executable"],
        "python_version": runtime["python_version"],
        "implementation": runtime["implementation"],
        "distribution_fingerprint": runtime["distribution_fingerprint"],
        "distributions": runtime["distributions"],
    }
    (home / envtool.LOCAL_MANIFEST_NAME).write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        envtool,
        "_capture_runtime",
        lambda python_executable, repo_root: runtime,
    )

    identity = envtool.verify_environment(repo_root=tmp_path, home=home)

    assert identity.python_executable == str(python.absolute())
    assert identity.distribution_fingerprint == "fp"


def test_verify_environment_rejects_distribution_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_policy(tmp_path)
    home = tmp_path / "physical"
    python = envtool.venv_python(home)
    python.parent.mkdir(parents=True)
    python.write_text("# placeholder", encoding="utf-8")
    runtime = _runtime(python, home, fingerprint="new")
    manifest = {
        "schema_version": 1,
        "policy_sha256": envtool._policy_sha256(tmp_path),
        "python_executable": runtime["python_executable"],
        "python_version": runtime["python_version"],
        "implementation": runtime["implementation"],
        "distribution_fingerprint": "old",
        "distributions": runtime["distributions"],
    }
    (home / envtool.LOCAL_MANIFEST_NAME).write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        envtool,
        "_capture_runtime",
        lambda python_executable, repo_root: runtime,
    )

    with pytest.raises(
        envtool.RelayPhysicalEnvironmentError,
        match="distribution_fingerprint drifted",
    ):
        envtool.verify_environment(repo_root=tmp_path, home=home)


def test_prepare_reuses_verified_environment_without_reinstall(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_policy(tmp_path)
    home = tmp_path / "physical"
    (home / envtool.VENV_DIRNAME).mkdir(parents=True)
    expected = envtool.PhysicalEnvironmentIdentity(
        home=home,
        manifest_path=home / envtool.LOCAL_MANIFEST_NAME,
        python_executable=str(envtool.venv_python(home).absolute()),
        python_version="3.12.test",
        implementation="cpython",
        policy_sha256="policy",
        distribution_fingerprint="fp",
    )
    monkeypatch.setattr(envtool, "_require_policy_python", lambda policy: None)
    monkeypatch.setattr(
        envtool,
        "verify_environment",
        lambda repo_root, home=None: expected,
    )

    identity = envtool.prepare_environment(repo_root=tmp_path, home=home)

    assert identity is expected

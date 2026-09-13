from __future__ import annotations

import os
from pathlib import Path

import pytest

import tools.relay_physical_env as envtool


def _identity(tmp_path: Path) -> envtool.PhysicalEnvironmentIdentity:
    home = tmp_path / "instance"
    python = envtool.venv_python(home)
    python.parent.mkdir(parents=True, exist_ok=True)
    base = tmp_path / "base-python"
    base.write_text("base", encoding="utf-8")
    python.symlink_to(base)
    manifest = home / envtool.LOCAL_MANIFEST_NAME
    manifest.write_text("{}", encoding="utf-8")
    return envtool.PhysicalEnvironmentIdentity(
        home=home,
        manifest_path=manifest,
        python_executable=str(python.absolute()),
        python_version="3.12.test",
        implementation="cpython",
        policy_sha256="a" * 64,
        distribution_fingerprint="b" * 64,
    )


def _bootstrap_for(identity: envtool.PhysicalEnvironmentIdentity, tmp_path: Path) -> Path:
    bootstrap = tmp_path / "usr" / "bin" / "python3.12"
    bootstrap.parent.mkdir(parents=True, exist_ok=True)
    bootstrap.symlink_to(Path(identity.python_executable).resolve())
    assert bootstrap.resolve() == Path(identity.python_executable).resolve()
    assert bootstrap.absolute() != Path(identity.python_executable).absolute()
    return bootstrap


def test_current_environment_rejects_bootstrap_even_when_resolved_binary_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = _identity(tmp_path)
    bootstrap = _bootstrap_for(identity, tmp_path)
    monkeypatch.setattr(envtool, "verify_environment", lambda **kwargs: identity)
    monkeypatch.setattr(envtool.sys, "executable", str(bootstrap.absolute()))
    monkeypatch.setattr(envtool.sys, "prefix", str((tmp_path / "usr").absolute()))

    with pytest.raises(
        envtool.RelayPhysicalEnvironmentError,
        match="not executing inside the selected persistent Python",
    ):
        envtool.verify_current_environment(repo_root=tmp_path)


def test_reexec_uses_selected_venv_launcher_without_resolving_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = _identity(tmp_path)
    bootstrap = _bootstrap_for(identity, tmp_path)
    monkeypatch.setattr(envtool, "verify_environment", lambda **kwargs: identity)
    monkeypatch.setattr(envtool.sys, "executable", str(bootstrap.absolute()))
    monkeypatch.setattr(envtool.sys, "prefix", str((tmp_path / "usr").absolute()))
    captured: dict[str, object] = {}

    def fake_execve(path: str, argv: list[str], environment: dict[str, str]) -> None:
        captured["path"] = path
        captured["argv"] = argv
        captured["environment"] = environment
        raise RuntimeError("execve intercepted")

    monkeypatch.setattr(envtool.os, "execve", fake_execve)

    with pytest.raises(RuntimeError, match="execve intercepted"):
        envtool.reexec_into_environment(repo_root=tmp_path, argv=("--target", "demo"))

    expected = str(Path(identity.python_executable).absolute())
    assert captured["path"] == expected
    assert captured["argv"] == [
        expected,
        "-m",
        "tools.relay_physical_run",
        "--target",
        "demo",
    ]
    environment = captured["environment"]
    assert isinstance(environment, dict)
    assert environment["PYTHONPATH"] == os.pathsep.join(
        (str(tmp_path.resolve()), str((tmp_path / "src").resolve()))
    )
    assert environment["PYTHONNOUSERSITE"] == "1"


def test_selected_venv_identity_is_accepted_without_reexec_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = _identity(tmp_path)
    monkeypatch.setattr(envtool, "verify_environment", lambda **kwargs: identity)
    monkeypatch.setattr(
        envtool.sys,
        "executable",
        str(Path(identity.python_executable).absolute()),
    )
    monkeypatch.setattr(
        envtool.sys,
        "prefix",
        str((identity.home / envtool.VENV_DIRNAME).absolute()),
    )

    def forbidden_execve(*args, **kwargs):
        del args, kwargs
        raise AssertionError("selected venv must not reexec itself")

    monkeypatch.setattr(envtool.os, "execve", forbidden_execve)

    verified = envtool.verify_current_environment(repo_root=tmp_path)
    envtool.reexec_into_environment(repo_root=tmp_path, argv=("--target", "demo"))

    assert verified == identity

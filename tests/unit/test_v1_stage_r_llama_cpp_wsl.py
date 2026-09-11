from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

import tools.v1_stage_r_llama_cpp_wsl as wrapper


def test_wrapper_creates_fresh_runtime_and_invokes_inner_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    operator_home = tmp_path / "operator-home"
    operator_home.mkdir()
    inherited_pythonpath = os.pathsep.join(("/inherited/one", "/inherited/two"))
    monkeypatch.setenv("HOME", str(operator_home))
    monkeypatch.setenv("PYTHONPATH", inherited_pythonpath)

    observed: list[dict[str, object]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        workspace = Path(command[command.index("--workspace-root") + 1])
        artifacts = Path(command[command.index("--artifact-root") + 1])
        runtime_home = Path(env["HOME"])
        log_root = runtime_home / "logs"
        assert log_root.is_dir()
        assert os.access(log_root, os.W_OK)
        observed.append(
            {
                "command": command,
                "cwd": cwd,
                "env": env,
                "workspace": workspace,
                "artifacts": artifacts,
                "check": check,
            }
        )
        assert not workspace.exists()
        assert not artifacts.exists()
        return subprocess.CompletedProcess(command, 37)

    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)

    result = wrapper.main([])

    assert result == 37
    assert len(observed) == 1
    invocation = observed[0]
    command = invocation["command"]
    assert isinstance(command, list)
    assert command[0] == wrapper.sys.executable
    assert command[1:3] == ["-m", wrapper.INNER_TRANSACTION]
    assert invocation["check"] is False

    repo_root = Path(wrapper.__file__).resolve().parents[1]
    assert invocation["cwd"] == repo_root
    assert command[command.index("--repo-root") + 1] == str(repo_root)
    assert command[command.index("--llama-cpp-root") + 1] == str(
        operator_home / "src" / "llama.cpp"
    )
    assert command[command.index("--artifact-path") + 1] == str(
        operator_home / "models" / "gguf" / "gemma-4-12B-it-Q4_K_M.gguf"
    )

    environment = invocation["env"]
    assert isinstance(environment, dict)
    runtime_home = Path(environment["HOME"])
    runtime_root = runtime_home.parent
    assert runtime_root.is_relative_to(Path("/tmp"))
    assert runtime_root.is_dir()
    assert runtime_home.is_dir()
    assert os.access(runtime_home, os.W_OK)
    assert (runtime_home / "logs").is_dir()
    assert os.access(runtime_home / "logs", os.W_OK)
    assert invocation["workspace"].parent == runtime_root
    assert invocation["artifacts"].parent == runtime_root
    assert not invocation["workspace"].exists()
    assert not invocation["artifacts"].exists()

    pythonpath = environment["PYTHONPATH"].split(os.pathsep)
    assert pythonpath[0] == str(repo_root / "src")
    assert pythonpath[1:] == inherited_pythonpath.split(os.pathsep)

    shutil.rmtree(runtime_root)


def test_wrapper_refuses_inner_when_runtime_log_directory_is_not_ready(
    tmp_path: Path,
    monkeypatch,
) -> None:
    operator_home = tmp_path / "operator-home"
    operator_home.mkdir()
    monkeypatch.setenv("HOME", str(operator_home))

    runtime_root = tmp_path / "runtime-root"

    def fake_mkdtemp(*, prefix: str, dir: Path) -> str:
        assert prefix == "relaylm-v1-stage-r-llama-cpp-"
        assert Path(dir) == wrapper.RUNTIME_ROOT_PARENT
        runtime_root.mkdir()
        return str(runtime_root)

    observed_probes: list[tuple[Path, str]] = []

    def fake_probe(path: Path, *, label: str) -> None:
        observed_probes.append((path, label))
        if label == "runtime HOME log directory":
            raise RuntimeError("simulated log directory sandbox denial")

    def forbidden_inner(*args, **kwargs):
        raise AssertionError("inner transaction must not run without log readiness")

    monkeypatch.setattr(wrapper.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(wrapper, "_prove_runtime_directory_writable", fake_probe)
    monkeypatch.setattr(wrapper.subprocess, "run", forbidden_inner)

    with pytest.raises(RuntimeError, match="simulated log directory sandbox denial"):
        wrapper.main([])

    assert len(observed_probes) == 2
    assert observed_probes[0] == (runtime_root / "home", "runtime HOME")
    assert observed_probes[1] == (
        runtime_root / "home" / "logs",
        "runtime HOME log directory",
    )
    assert (runtime_root / "home" / "logs").is_dir()
    assert not (runtime_root / "workspace").exists()
    assert not (runtime_root / "artifacts").exists()


def test_wrapper_has_no_server_provider_or_model_calls(monkeypatch) -> None:
    calls = {"inner": 0, "server": 0, "provider": 0, "model": 0}
    runtime_root: Path | None = None

    def fake_run(command, *, cwd, env, check):
        nonlocal runtime_root
        calls["inner"] += 1
        assert command[1:3] == ["-m", wrapper.INNER_TRANSACTION]
        assert "llama-server" not in command
        assert "/chat/completions" not in command
        runtime_root = Path(env["HOME"]).parent
        assert (Path(env["HOME"]) / "logs").is_dir()
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)

    try:
        result = wrapper.main([])
    finally:
        if runtime_root is not None:
            shutil.rmtree(runtime_root)

    assert result == 0
    assert calls == {"inner": 1, "server": 0, "provider": 0, "model": 0}

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import tools.v2_cognitive_ir_s2_selected_llama_cpp_wsl as wsl


def test_inner_command_preserves_real_runtime_paths_and_shared_lock(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    llama = tmp_path / "operator" / "src" / "llama.cpp"
    model = tmp_path / "operator" / "models" / "gguf" / "model.gguf"
    lock = Path("/tmp/relaylm/locks/llama-server-127.0.0.1-1234.lock")

    command = wsl._inner_command(
        repo_root=repo,
        llama_cpp_root=llama,
        artifact_path=model,
        lock_path=lock,
    )

    assert command[0] == wsl.sys.executable
    assert command[1:3] == ["-m", wsl.INNER_TRANSACTION_MODULE]
    assert command.count(wsl.INNER_TRANSACTION_MODULE) == 1
    assert command[command.index("--repo-root") + 1] == str(repo)
    assert command[command.index("--llama-cpp-root") + 1] == str(llama)
    assert command[command.index("--artifact-path") + 1] == str(model)
    assert command[command.index("--lock-path") + 1] == str(lock)


def test_launcher_uses_fresh_writable_home_and_invokes_inner_once(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    operator_home = tmp_path / "operator-home"
    operator_home.mkdir()
    runtime_root = tmp_path / "runtime-root"
    shared_lock = tmp_path / "shared" / "llama-server.lock"

    def fake_mkdtemp(*, prefix: str) -> str:
        assert prefix == "relaylm-v2-2211-s2-wsl-runtime-"
        runtime_root.mkdir()
        return str(runtime_root)

    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(command, *, env, check):
        assert check is False
        calls.append((list(command), dict(env)))
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(wsl.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(wsl.subprocess, "run", fake_run)
    monkeypatch.setattr(wsl, "DEFAULT_SHARED_LOCK_PATH", shared_lock)

    code = wsl.main(
        [
            "--repo-root",
            str(repo),
            "--operator-home",
            str(operator_home),
        ]
    )

    assert code == 7
    assert len(calls) == 1
    command, child_env = calls[0]
    assert child_env["HOME"] == str(runtime_root / "home")
    assert Path(child_env["HOME"]).is_dir()
    assert not Path(child_env["HOME"]).is_relative_to(repo.resolve())
    assert shared_lock.parent.is_dir()
    assert command.count(wsl.INNER_TRANSACTION_MODULE) == 1
    assert command[command.index("--llama-cpp-root") + 1] == str(
        operator_home / "src" / "llama.cpp"
    )
    assert command[command.index("--artifact-path") + 1] == str(
        operator_home
        / "models"
        / "gguf"
        / "gemma-4-12B-it-Q4_K_M.gguf"
    )
    assert command[command.index("--lock-path") + 1] == str(shared_lock)
    assert os.environ.get("HOME") != child_env["HOME"]


def test_default_shared_lock_is_under_writable_wsl_tmp_namespace() -> None:
    assert wsl.DEFAULT_SHARED_LOCK_PATH == Path(
        "/tmp/relaylm/locks/llama-server-127.0.0.1-1234.lock"
    )

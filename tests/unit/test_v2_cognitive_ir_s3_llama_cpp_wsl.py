from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import tools.v2_cognitive_ir_s3_llama_cpp_wsl as wsl


def test_s3_wsl_inner_command_preserves_runtime_paths() -> None:
    repo = Path("/tmp/repo")
    operator = Path("/home/operator")
    command = wsl._inner_command(
        repo_root=repo,
        llama_cpp_root=operator / "src" / "llama.cpp",
        artifact_path=operator / "models" / "gguf" / "model.gguf",
        lock_path=Path("/tmp/relaylm/locks/test.lock"),
    )
    assert command[0] == wsl.sys.executable
    assert command[1:3] == ["-m", wsl.INNER_TRANSACTION_MODULE]
    assert command.count(wsl.INNER_TRANSACTION_MODULE) == 1
    assert command[command.index("--repo-root") + 1] == str(repo)
    assert command[command.index("--lock-path") + 1].startswith("/tmp/relaylm/locks/")


def test_s3_wsl_launcher_sets_exact_cwd_src_pythonpath_and_fresh_home(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    operator = tmp_path / "operator"
    operator.mkdir()
    runtime_root = tmp_path / "runtime"
    lock_path = tmp_path / "locks" / "server.lock"

    def fake_mkdtemp(*, prefix: str) -> str:
        assert prefix == "relaylm-v2-2211-s3-wsl-runtime-"
        runtime_root.mkdir()
        return str(runtime_root)

    calls: list[tuple[list[str], Path, dict[str, str]]] = []

    def fake_run(command, *, cwd, env, check):
        assert check is False
        calls.append((list(command), Path(cwd), dict(env)))
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(wsl.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(wsl.subprocess, "run", fake_run)
    monkeypatch.setattr(wsl, "DEFAULT_SHARED_LOCK_PATH", lock_path)
    monkeypatch.setenv("PYTHONPATH", "/existing/path")

    code = wsl.main(
        ["--repo-root", str(repo), "--operator-home", str(operator)]
    )

    assert code == 7
    assert len(calls) == 1
    command, cwd, env = calls[0]
    assert cwd == repo.resolve()
    assert env["HOME"] == str(runtime_root / "home")
    assert Path(env["HOME"]).is_dir()
    assert env["PYTHONPATH"].split(os.pathsep) == [
        str((repo / "src").resolve()),
        "/existing/path",
    ]
    assert command.count(wsl.INNER_TRANSACTION_MODULE) == 1
    assert command[command.index("--llama-cpp-root") + 1] == str(
        operator / "src" / "llama.cpp"
    )
    assert command[command.index("--artifact-path") + 1] == str(
        operator / "models" / "gguf" / "gemma-4-12B-it-Q4_K_M.gguf"
    )

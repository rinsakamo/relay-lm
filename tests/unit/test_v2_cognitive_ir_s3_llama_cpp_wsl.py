from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import tools.v2_cognitive_ir_s3_llama_cpp_wsl as wsl


def test_s3_wsl_inner_command_preserves_runtime_paths() -> None:
    repo = Path("/tmp/repo")
    operator = Path("/home/operator")
    artifact_root = Path("/tmp/runtime/artifacts")
    summary_path = artifact_root / "s3-llama-cpp-transaction-summary.json"
    command = wsl._inner_command(
        repo_root=repo,
        llama_cpp_root=operator / "src" / "llama.cpp",
        artifact_path=operator / "models" / "gguf" / "model.gguf",
        lock_path=Path("/tmp/relaylm/locks/test.lock"),
        artifact_root=artifact_root,
        summary_path=summary_path,
    )
    assert command[0] == wsl.sys.executable
    assert command[1:3] == ["-m", wsl.INNER_TRANSACTION_MODULE]
    assert command.count(wsl.INNER_TRANSACTION_MODULE) == 1
    assert command[command.index("--repo-root") + 1] == str(repo)
    assert command[command.index("--lock-path") + 1].startswith("/tmp/relaylm/locks/")
    assert command[command.index("--artifact-root") + 1] == str(artifact_root)
    assert command[command.index("--summary-path") + 1] == str(summary_path)


def test_s3_wsl_launcher_sets_exact_cwd_src_pythonpath_fresh_home_and_wall_time(
    monkeypatch,
    tmp_path: Path,
    capsys,
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
        summary_path = Path(command[command.index("--summary-path") + 1])
        summary_path.parent.mkdir(parents=True, exist_ok=False)
        summary_path.write_text('{"classification":"S3_INCOMPLETE"}\n', encoding="utf-8")
        return SimpleNamespace(returncode=7)

    monotonic_values = iter((10_000_000_000, 12_500_000_000))
    monkeypatch.setattr(wsl.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(wsl.subprocess, "run", fake_run)
    monkeypatch.setattr(wsl.time, "monotonic_ns", lambda: next(monotonic_values))
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
    artifact_root = runtime_root / "artifacts"
    assert command[command.index("--artifact-root") + 1] == str(artifact_root)
    summary_path = artifact_root / "s3-llama-cpp-transaction-summary.json"
    assert command[command.index("--summary-path") + 1] == str(summary_path)

    sidecar_path = artifact_root / "s3-wsl-wall-time.json"
    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert payload["schema"] == wsl.WALL_TIME_SCHEMA
    assert payload["measurement"] == "time.monotonic_ns"
    assert payload["scope"] == "one-command-wrapper-child-transaction"
    assert payload["wall_seconds"] == 2.5
    assert payload["child_return_code"] == 7
    assert payload["transaction_summary_path"] == str(summary_path)
    assert payload["transaction_summary_sha256"] == wsl._sha256_file(summary_path)

    rendered = json.loads(capsys.readouterr().out)
    assert rendered["s3_wsl_wall_time_path"] == str(sidecar_path)
    assert rendered["s3_wsl_wall_time_sha256"] == wsl._sha256_file(sidecar_path)
    assert rendered["wall_seconds"] == 2.5

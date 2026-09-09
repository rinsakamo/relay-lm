from __future__ import annotations

import json
from pathlib import Path

import relaylm.actual_model_stage_r_llama_cpp_transaction as tx


class FakeProcess:
    def __init__(self, pid: int = 4321) -> None:
        self.pid = pid
        self.returncode: int | None = None

    def poll(self) -> int | None:
        return self.returncode


def _argv(tmp_path: Path) -> list[str]:
    return [
        "--repo-root",
        str(tmp_path / "repo"),
        "--workspace-root",
        str(tmp_path / "workspace"),
        "--artifact-root",
        str(tmp_path / "artifacts"),
    ]


def _common_monkeypatch(monkeypatch) -> None:
    monkeypatch.setattr(tx, "_require_clean_repo", lambda repo_root: None)
    monkeypatch.setattr(tx, "_git_identity", lambda repo_root: ("h" * 40, "t" * 40))


def test_occupied_port_fails_closed_without_server_or_host(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _common_monkeypatch(monkeypatch)
    monkeypatch.setattr(tx, "_port_is_free", lambda host, port: False)
    monkeypatch.setattr(tx, "_listener_snapshot", lambda port: "existing listener")

    def forbidden(*args, **kwargs):
        raise AssertionError("server or host must not run while the port is occupied")

    monkeypatch.setattr(tx, "_start_server", forbidden)
    monkeypatch.setattr(tx, "_invoke_host", forbidden)

    rc = tx.main(_argv(tmp_path))

    summary = json.loads(
        (tmp_path / "artifacts" / "stage-r-llama-cpp-transaction-summary.json")
        .read_text(encoding="utf-8")
    )
    assert rc == 3
    assert summary["disposition"] == "MECHANICAL_PRECONDITION_BLOCKED"
    assert summary["server_launch_count"] == 0
    assert summary["host_invocation_count"] == 0
    assert summary["listener_snapshot"] == "existing listener"


def test_owned_server_lifecycle_passes_host_result_through(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _common_monkeypatch(monkeypatch)
    monkeypatch.setattr(tx, "_port_is_free", lambda host, port: True)
    monkeypatch.setattr(
        tx,
        "_collect_llama_identity",
        lambda **kwargs: ("a" * 40, "llama-server build 10874", 10874),
    )
    artifact = tmp_path / "model.gguf"
    artifact.write_bytes(b"gguf")
    monkeypatch.setattr(tx, "_collect_gpu_identity", lambda: "RTX 3060")
    log_path = tmp_path / "server.log"
    monkeypatch.setattr(tx, "_new_server_log_path", lambda: log_path)
    process = FakeProcess()

    def start_server(**kwargs):
        log_path.write_text("server log", encoding="utf-8")
        return process, ["llama-server", "-c", "8192", "-np", "1"]

    monkeypatch.setattr(tx, "_start_server", start_server)
    monkeypatch.setattr(tx, "_wait_until_ready", lambda **kwargs: None)
    monkeypatch.setattr(
        tx,
        "_probe_server",
        lambda **kwargs: {
            "request_model": "model-id",
            "health": {"status": "ok"},
            "props": {},
            "slot_count": 1,
            "non_generative_request_count": 4,
        },
    )
    monkeypatch.setattr(
        tx,
        "_invoke_host",
        lambda **kwargs: {
            "exit_code": 0,
            "command": "python -m host",
            "stdout_path": "stdout",
            "stderr_path": "stderr",
            "summary_path": "host-summary",
            "summary": {"classification": "PASS", "provider_request_count": 8},
        },
    )

    def terminate(owned_process):
        assert owned_process is process
        owned_process.returncode = 0
        return 0

    monkeypatch.setattr(tx, "_terminate_owned_process", terminate)

    argv = _argv(tmp_path) + ["--artifact-path", str(artifact)]
    rc = tx.main(argv)

    summary = json.loads(
        (tmp_path / "artifacts" / "stage-r-llama-cpp-transaction-summary.json")
        .read_text(encoding="utf-8")
    )
    assert rc == 0
    assert summary["classification"] == "PASS"
    assert summary["host"]["summary"]["classification"] == "PASS"
    assert summary["server_launch_count"] == 1
    assert summary["host_invocation_count"] == 1
    assert summary["server"]["pid"] == process.pid
    assert summary["server"]["terminated"] is True
    assert summary["server"]["log_sha256"].startswith("sha256:")


def test_semantic_fail_is_not_reinterpreted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _common_monkeypatch(monkeypatch)
    monkeypatch.setattr(tx, "_port_is_free", lambda host, port: True)
    monkeypatch.setattr(
        tx,
        "_collect_llama_identity",
        lambda **kwargs: ("a" * 40, "llama-server build 10874", 10874),
    )
    artifact = tmp_path / "model.gguf"
    artifact.write_bytes(b"gguf")
    monkeypatch.setattr(tx, "_collect_gpu_identity", lambda: "RTX 3060")
    log_path = tmp_path / "server.log"
    monkeypatch.setattr(tx, "_new_server_log_path", lambda: log_path)
    process = FakeProcess()

    def start_server(**kwargs):
        log_path.write_text("server log", encoding="utf-8")
        return process, ["llama-server"]

    monkeypatch.setattr(tx, "_start_server", start_server)
    monkeypatch.setattr(tx, "_wait_until_ready", lambda **kwargs: None)
    monkeypatch.setattr(
        tx,
        "_probe_server",
        lambda **kwargs: {
            "request_model": "model-id",
            "health": {"status": "ok"},
            "props": {},
            "slot_count": 1,
            "non_generative_request_count": 4,
        },
    )
    monkeypatch.setattr(
        tx,
        "_invoke_host",
        lambda **kwargs: {
            "exit_code": 1,
            "command": "python -m host",
            "stdout_path": "stdout",
            "stderr_path": "stderr",
            "summary_path": "host-summary",
            "summary": {"classification": "SEMANTIC_FAIL"},
        },
    )

    def terminate(owned_process):
        owned_process.returncode = 0
        return 0

    monkeypatch.setattr(tx, "_terminate_owned_process", terminate)

    rc = tx.main(_argv(tmp_path) + ["--artifact-path", str(artifact)])
    summary = json.loads(
        (tmp_path / "artifacts" / "stage-r-llama-cpp-transaction-summary.json")
        .read_text(encoding="utf-8")
    )
    assert rc == 1
    assert summary["classification"] == "SEMANTIC_FAIL"
    assert summary["semantic_retry_count"] == 0
    assert summary["fallback_count"] == 0


def test_pre_host_failure_still_terminates_owned_process(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _common_monkeypatch(monkeypatch)
    monkeypatch.setattr(tx, "_port_is_free", lambda host, port: True)
    monkeypatch.setattr(
        tx,
        "_collect_llama_identity",
        lambda **kwargs: ("a" * 40, "llama-server build 10874", 10874),
    )
    artifact = tmp_path / "model.gguf"
    artifact.write_bytes(b"gguf")
    monkeypatch.setattr(tx, "_collect_gpu_identity", lambda: "RTX 3060")
    log_path = tmp_path / "server.log"
    monkeypatch.setattr(tx, "_new_server_log_path", lambda: log_path)
    process = FakeProcess()

    def start_server(**kwargs):
        log_path.write_text("server log", encoding="utf-8")
        return process, ["llama-server"]

    monkeypatch.setattr(tx, "_start_server", start_server)
    monkeypatch.setattr(tx, "_wait_until_ready", lambda **kwargs: None)

    def fail_probe(**kwargs):
        raise tx.LlamaCppTransactionError("bad probe")

    monkeypatch.setattr(tx, "_probe_server", fail_probe)

    def forbidden_host(**kwargs):
        raise AssertionError("host must not be invoked after a pre-host failure")

    monkeypatch.setattr(tx, "_invoke_host", forbidden_host)
    terminated = []

    def terminate(owned_process):
        terminated.append(owned_process.pid)
        owned_process.returncode = 0
        return 0

    monkeypatch.setattr(tx, "_terminate_owned_process", terminate)

    rc = tx.main(_argv(tmp_path) + ["--artifact-path", str(artifact)])
    summary = json.loads(
        (tmp_path / "artifacts" / "stage-r-llama-cpp-transaction-summary.json")
        .read_text(encoding="utf-8")
    )
    assert rc == 3
    assert terminated == [process.pid]
    assert summary["host_invocation_count"] == 0
    assert summary["server"]["terminated"] is True
    assert summary["disposition"] == "MECHANICAL_PRECONDITION_BLOCKED"

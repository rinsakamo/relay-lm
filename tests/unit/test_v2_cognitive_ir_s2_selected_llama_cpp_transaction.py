from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.v2_cognitive_ir_s2_host import S2HostError
from tools.v2_cognitive_ir_s2_host_v2 import S2HostV2Result
import tools.v2_cognitive_ir_s2_selected_llama_cpp_transaction as tx


class _FakeProcess:
    def __init__(self) -> None:
        self.pid = 4242
        self.returncode = None
        self.signals: list[int] = []

    def poll(self):
        return self.returncode

    def send_signal(self, value: int) -> None:
        self.signals.append(value)
        self.returncode = 0

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    def terminate(self) -> None:
        raise AssertionError("SIGTERM must not be needed in normal cleanup")

    def kill(self) -> None:
        raise AssertionError("SIGKILL must not be needed in normal cleanup")


def test_launch_command_freezes_single_slot_8192_and_log_controls(
    tmp_path: Path,
) -> None:
    command = tx._launch_command(
        server_binary=tmp_path / "llama-server",
        artifact_path=tmp_path / "model.gguf",
        port=1234,
        log_path=tmp_path / "run.log",
    )
    joined = " ".join(command)
    assert "-ngl 999" in joined
    assert "-c 8192" in joined
    assert "-np 1" in joined
    assert "--no-context-shift" in command
    assert "-lv 4" in joined
    assert "--log-prefix" in command
    assert "--log-timestamps" in command
    assert "--log-file" in command


def test_reasoning_effort_none_semantics_are_verified_from_exact_revision(
    monkeypatch, tmp_path: Path
) -> None:
    source = '''
    if (reasoning_effort == "none") {
        inputs.enable_thinking = false;
        inputs.chat_template_kwargs.erase("reasoning_effort");
    }
    '''
    monkeypatch.setattr(tx, "_run_text", lambda *args, **kwargs: source)
    tx._verify_reasoning_effort_none_semantics(
        llama_cpp_root=tmp_path,
        revision="a" * 40,
    )


def test_reasoning_effort_none_semantics_fail_closed_when_mapping_is_absent(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        tx,
        "_run_text",
        lambda *args, **kwargs: (
            'if (reasoning_effort == "none") { /* no disable */ }'
        ),
    )
    with pytest.raises(tx.SelectedS2TransactionError, match="enable_thinking=false"):
        tx._verify_reasoning_effort_none_semantics(
            llama_cpp_root=tmp_path,
            revision="a" * 40,
        )


def test_occupied_port_blocks_before_server_or_host(
    monkeypatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    summary_path = tmp_path / "summary.json"
    monkeypatch.setattr(tx, "_require_clean_repo", lambda _: None)
    monkeypatch.setattr(tx, "_git_identity", lambda _: ("a" * 40, "b" * 40))
    monkeypatch.setattr(tx, "_port_is_free", lambda *_: False)
    monkeypatch.setattr(tx, "_listener_snapshot", lambda _: "LISTEN test")
    monkeypatch.setattr(
        tx,
        "_start_server",
        lambda *_: (_ for _ in ()).throw(
            AssertionError("server must not launch")
        ),
    )
    monkeypatch.setattr(
        tx,
        "run_llama_cpp_selected_s2_transaction",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("host must not run")
        ),
    )

    code = tx.main(
        [
            "--repo-root",
            str(repo),
            "--artifact-root",
            str(tmp_path / "artifacts"),
            "--summary-path",
            str(summary_path),
            "--lock-path",
            str(tmp_path / "lock"),
        ]
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert code == 3
    assert summary["classification"] == "EXECUTION_BLOCKED"
    assert summary["server_launch_count"] == 0
    assert summary["host_invocation_count"] == 0
    assert summary["provider_attempts"] == 0
    assert summary["lm_studio_contact_count"] == 0


def _prepare_success(monkeypatch, tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    llama_root = tmp_path / "llama.cpp"
    binary = llama_root / "build" / "bin" / "llama-server"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"server")
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model")
    log = tmp_path / "server.log"
    process = _FakeProcess()

    monkeypatch.setattr(tx, "_require_clean_repo", lambda _: None)
    monkeypatch.setattr(tx, "_git_identity", lambda _: ("a" * 40, "b" * 40))
    monkeypatch.setattr(tx, "_port_is_free", lambda *_: True)
    monkeypatch.setattr(
        tx,
        "_collect_llama_identity",
        lambda **_: ("c" * 40, "llama.cpp build 10874 ccccccc"),
    )
    monkeypatch.setattr(tx, "_require_server_flags", lambda _: None)
    monkeypatch.setattr(
        tx, "_verify_reasoning_effort_none_semantics", lambda **_: None
    )
    monkeypatch.setattr(
        tx,
        "_collect_gpu_identity",
        lambda: {
            "name": "RTX 3060",
            "uuid": "GPU-x",
            "driver": "591.44",
            "memory_mib": "12287",
        },
    )
    monkeypatch.setattr(tx, "_new_server_log_path", lambda: log)

    def start(command):
        log.write_text("server log\n", encoding="utf-8")
        return process

    monkeypatch.setattr(tx, "_start_server", start)
    monkeypatch.setattr(tx, "_wait_until_ready", lambda **_: None)
    monkeypatch.setattr(
        tx,
        "_probe_server",
        lambda **_: {
            "request_model": str(model.resolve()),
            "build_info": "llama.cpp build 10874 ccccccc",
            "model_path": str(model.resolve()),
            "model_ftype": "Q4_K_M",
            "context": 8192,
            "slot_count": 1,
            "slot_contexts": [8192],
            "non_generative_request_count": 4,
        },
    )
    return repo, llama_root, model, log, process


def test_completed_host_result_is_preserved_and_server_cleaned(
    monkeypatch, tmp_path: Path
) -> None:
    repo, llama_root, model, log, process = _prepare_success(
        monkeypatch, tmp_path
    )
    calls: list[dict[str, object]] = []

    def host(**kwargs):
        calls.append(kwargs)
        return S2HostV2Result(
            run_id="s2-test",
            identity_fingerprint="sha256:test",
            status="COMPLETED",
            claim_status="NON_CITABLE_S2_SMOKE",
            citable=False,
            provider_calls=10,
            provider_attempts=10,
            provider_completions=10,
            arm_correctness=(True, False, True, False, True, False, True),
            mechanical_classification="MECHANICALLY_DISCRIMINATING",
            typed_generic_semantic_equal=True,
        )

    monkeypatch.setattr(tx, "run_llama_cpp_selected_s2_transaction", host)
    summary_path = tmp_path / "summary.json"
    code = tx.main(
        [
            "--repo-root",
            str(repo),
            "--llama-cpp-root",
            str(llama_root),
            "--artifact-path",
            str(model),
            "--artifact-root",
            str(tmp_path / "artifacts"),
            "--summary-path",
            str(summary_path),
            "--lock-path",
            str(tmp_path / "lock"),
        ]
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert code == 0
    assert len(calls) == 1
    assert summary["server_launch_count"] == 1
    assert summary["host_invocation_count"] == 1
    assert summary["provider_attempts"] == 10
    assert summary["provider_completions"] == 10
    assert summary["classification"] == "MECHANICALLY_DISCRIMINATING"
    assert summary["host"]["run_id"] == "s2-test"
    assert summary["server"]["log_path"] == str(log)
    assert len(summary["server"]["log_sha256"]) == 64
    assert summary["server"]["cleanup"]["terminated"] is True
    assert summary["server"]["cleanup"]["forced"] is False
    assert process.signals
    controller = calls[0]["controller_identity"]
    assert set(controller) == {
        "upstream_revision",
        "build_info",
        "binary_path",
        "binary_sha256",
        "model_path",
        "artifact_sha256",
        "context_shift_enabled",
        "launch",
        "hardware",
        "capacity_evidence",
    }
    assert controller["launch"]["slots"] == 1
    assert controller["launch"]["context"] == 8192


def test_host_failure_after_entry_is_not_retried(
    monkeypatch, tmp_path: Path
) -> None:
    repo, llama_root, model, _, _ = _prepare_success(monkeypatch, tmp_path)
    calls = 0

    def host(**kwargs):
        nonlocal calls
        calls += 1
        raise S2HostError("provider failure")

    monkeypatch.setattr(tx, "run_llama_cpp_selected_s2_transaction", host)
    summary_path = tmp_path / "summary.json"
    code = tx.main(
        [
            "--repo-root",
            str(repo),
            "--llama-cpp-root",
            str(llama_root),
            "--artifact-path",
            str(model),
            "--artifact-root",
            str(tmp_path / "artifacts"),
            "--summary-path",
            str(summary_path),
            "--lock-path",
            str(tmp_path / "lock"),
        ]
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert code == 2
    assert calls == 1
    assert summary["host_invocation_count"] == 1
    assert summary["classification"] == "INCOMPLETE"
    assert summary["semantic_retry_count"] == 0
    assert summary["replay_count"] == 0
    assert summary["fallback_count"] == 0

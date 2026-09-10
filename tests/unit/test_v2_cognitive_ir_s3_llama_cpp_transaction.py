from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from relaylm.v2_transfer_actual_model import ExperimentCompletion
import tools.v2_cognitive_ir_s3_llama_cpp_transaction as tx
from tools.v2_cognitive_ir_s2_selected_llama_cpp_transaction import _launch_command


class _FakeInner:
    def __init__(self) -> None:
        self.provider_attempts = 0
        self.provider_completions = 0
        self.input_count_attempts = 0
        self.input_count_completions = 0
        self.calls: list[tuple[str, str]] = []

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        self.calls.append((question_id, output_kind))
        self.provider_attempts += 1
        self.provider_completions += 1
        self.input_count_attempts += 2
        self.input_count_completions += 2
        return ExperimentCompletion(content="[1,2,3,4]", input_tokens=7, output_tokens=5)


def test_bound_s3_client_uses_one_lightweight_check_per_semantic_call() -> None:
    inner = _FakeInner()
    checks: list[int] = []
    client = tx._BoundS3Client(
        inner=inner,  # type: ignore[arg-type]
        live_binding_probe=lambda: checks.append(1),
    )

    completion = client.complete_named(
        "q1",
        ({"role": "user", "content": "solve"},),
        output_kind="vector",
    )

    assert completion.content == "[1,2,3,4]"
    assert checks == [1]
    assert client.live_binding_checks == 1
    assert client.provider_attempts == client.provider_completions == 1
    assert client.input_count_attempts == client.input_count_completions == 2
    assert inner.calls == [("q1", "vector")]


def test_lightweight_binding_check_uses_live_probe_and_material_stat(
    monkeypatch,
    tmp_path: Path,
) -> None:
    server = tmp_path / "llama-server"
    model = tmp_path / "model.gguf"
    server.write_bytes(b"server")
    model.write_bytes(b"model")
    expected_probe = {
        "request_model": "model.gguf",
        "build_info": "build",
        "model_path": str(model.resolve()),
        "model_ftype": "Q4_K_M",
        "context": 8192,
        "slot_count": 1,
        "slot_contexts": [8192],
    }
    server_stat = tx._material_stat(server)
    model_stat = tx._material_stat(model)
    observed_calls: list[int] = []

    def fake_probe(**kwargs):
        observed_calls.append(1)
        assert kwargs["origin"] == "http://127.0.0.1:1234"
        assert kwargs["api_base"] == "http://127.0.0.1:1234/v1"
        assert kwargs["artifact_path"] == model
        return dict(expected_probe)

    monkeypatch.setattr(tx, "_probe_server", fake_probe)
    process = SimpleNamespace(poll=lambda: None)

    tx._lightweight_binding_check(
        process=process,  # type: ignore[arg-type]
        expected_probe=expected_probe,
        server_binary=server,
        expected_binary_stat=server_stat,
        artifact_path=model,
        expected_artifact_stat=model_stat,
    )
    assert observed_calls == [1]

    drifted = dict(expected_probe)
    drifted["context"] = 4096
    monkeypatch.setattr(tx, "_probe_server", lambda **kwargs: drifted)
    with pytest.raises(tx.S3TransactionError, match="context"):
        tx._lightweight_binding_check(
            process=process,  # type: ignore[arg-type]
            expected_probe=expected_probe,
            server_binary=server,
            expected_binary_stat=server_stat,
            artifact_path=model,
            expected_artifact_stat=model_stat,
        )


def test_s3_shared_launch_command_is_one_slot_8192_no_context_shift(tmp_path: Path) -> None:
    command = _launch_command(
        server_binary=tmp_path / "llama-server",
        artifact_path=tmp_path / "model.gguf",
        port=1234,
        log_path=tmp_path / "unique.log",
    )
    assert command[command.index("-c") + 1] == "8192"
    assert command[command.index("-np") + 1] == "1"
    assert "--no-context-shift" in command
    assert command[command.index("--log-file") + 1].endswith("unique.log")
    assert "--log-prefix" in command
    assert "--log-timestamps" in command

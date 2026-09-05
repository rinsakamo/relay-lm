from __future__ import annotations

import json
import os
import subprocess

import pytest

from relaylm.actual_model_vllm_capability_probe import (
    VLLMCapabilityProbeError,
    load_vllm_capability_probe_receipt,
    probe_vllm_capability_surface,
    write_vllm_capability_probe_receipt,
)


COMMAND = ("/prepared/runtime/bin/vllm", "serve", "--help=all")
HELP = """
usage: vllm serve [options]
  --max-model-len INTEGER
  --gpu-memory-utilization FLOAT
  --disable-log-requests
"""


class FakeProcess:
    def __init__(
        self,
        *,
        stdout: str = HELP,
        stderr: str = "",
        returncode: int = 0,
        timeout_once: bool = False,
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.timeout_once = timeout_once
        self.communicate_calls = 0
        self.terminated = False
        self.killed = False

    def communicate(self, *, timeout: float):
        self.communicate_calls += 1
        if self.timeout_once and self.communicate_calls == 1:
            self.returncode = None
            raise subprocess.TimeoutExpired(COMMAND, timeout)
        return self.stdout, self.stderr

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = -15

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    def poll(self):
        return self.returncode


class Factory:
    def __init__(self, process: FakeProcess) -> None:
        self.process = process
        self.command = None
        self.kwargs = None

    def __call__(self, command, **kwargs):
        self.command = command
        self.kwargs = kwargs
        return self.process


def test_probe_rejects_noncanonical_command_shape() -> None:
    with pytest.raises(VLLMCapabilityProbeError, match="exactly"):
        probe_vllm_capability_surface(("vllm", "--help=all"))
    with pytest.raises(VLLMCapabilityProbeError, match="basename"):
        probe_vllm_capability_surface(("python", "serve", "--help=all"))
    with pytest.raises(VLLMCapabilityProbeError, match="exactly"):
        probe_vllm_capability_surface(("vllm", "serve", "--help"))


def test_probe_runs_directly_with_explicit_process_local_env_only() -> None:
    before = os.environ.get("RELAYLM_PROBE_TEST")
    process = FakeProcess()
    factory = Factory(process)

    result = probe_vllm_capability_surface(
        COMMAND,
        environment={"RELAYLM_PROBE_TEST": "candidate-value"},
        popen_factory=factory,
    )

    assert result.status == "CAPABILITY_READY"
    assert factory.command == COMMAND
    assert factory.kwargs is not None
    assert factory.kwargs["shell"] is False
    assert factory.kwargs["text"] is True
    assert factory.kwargs["env"]["RELAYLM_PROBE_TEST"] == "candidate-value"
    assert result.environment_keys == ("RELAYLM_PROBE_TEST",)
    assert os.environ.get("RELAYLM_PROBE_TEST") == before
    assert "--max-model-len" in result.supported_flags
    assert "--gpu-memory-utilization" in result.supported_flags


def test_probe_receipt_never_serializes_environment_values(tmp_path) -> None:
    process = FakeProcess()
    result = probe_vllm_capability_surface(
        COMMAND,
        environment={"SECRET_TOKEN": "do-not-persist-this"},
        popen_factory=Factory(process),
    )

    path = write_vllm_capability_probe_receipt(result, artifact_root=tmp_path)
    encoded = path.read_text(encoding="utf-8")

    assert "SECRET_TOKEN" in encoded
    assert "do-not-persist-this" not in encoded
    assert load_vllm_capability_probe_receipt(path) == result


def test_probe_classifies_nonzero_exit_without_parsing_help() -> None:
    result = probe_vllm_capability_surface(
        COMMAND,
        popen_factory=Factory(
            FakeProcess(stdout="partial help", stderr="device failure", returncode=1)
        ),
    )

    assert result.status == "NONZERO_EXIT"
    assert result.returncode == 1
    assert result.help_digest is None
    assert result.supported_flags == ()
    assert result.failure_type == "NonZeroExit"


def test_probe_classifies_empty_help() -> None:
    result = probe_vllm_capability_surface(
        COMMAND,
        popen_factory=Factory(FakeProcess(stdout="\n", returncode=0)),
    )

    assert result.status == "EMPTY_HELP"
    assert result.returncode == 0
    assert result.supported_flags == ()
    assert result.failure_type == "EmptyHelpSurface"


def test_probe_timeout_terminates_only_probe_child() -> None:
    process = FakeProcess(timeout_once=True)
    result = probe_vllm_capability_surface(
        COMMAND,
        timeout_seconds=0.1,
        cleanup_timeout_seconds=0.1,
        popen_factory=Factory(process),
    )

    assert result.status == "TIMEOUT"
    assert result.timed_out is True
    assert result.cleanup_complete is True
    assert process.terminated is True
    assert process.killed is False
    assert process.communicate_calls == 2


def test_probe_classifies_spawn_error() -> None:
    def missing(*args, **kwargs):
        raise FileNotFoundError("missing")

    result = probe_vllm_capability_surface(COMMAND, popen_factory=missing)

    assert result.status == "SPAWN_ERROR"
    assert result.returncode is None
    assert result.failure_type == "FileNotFoundError"


def test_probe_receipt_is_content_addressed_and_rejects_tampering(tmp_path) -> None:
    result = probe_vllm_capability_surface(COMMAND, popen_factory=Factory(FakeProcess()))
    path = write_vllm_capability_probe_receipt(result, artifact_root=tmp_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["receipt_id"] == result.receipt_id

    raw["stdout_bytes"] += 1
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(VLLMCapabilityProbeError, match="receipt id mismatch"):
        load_vllm_capability_probe_receipt(path)


def test_receipt_writer_is_create_once(tmp_path) -> None:
    result = probe_vllm_capability_surface(COMMAND, popen_factory=Factory(FakeProcess()))
    write_vllm_capability_probe_receipt(result, artifact_root=tmp_path)
    with pytest.raises(VLLMCapabilityProbeError, match="already exists"):
        write_vllm_capability_probe_receipt(result, artifact_root=tmp_path)

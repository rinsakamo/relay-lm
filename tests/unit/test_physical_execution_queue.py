from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.physical_execution_queue import (
    PreInvokeBlocked,
    QueueConfig,
    _safe_resource_id,
    run_queued_command,
)


class Completed:
    def __init__(self, returncode: int):
        self.returncode = returncode


def test_waits_for_external_runtime_then_invokes_child_once(tmp_path: Path) -> None:
    receipt = tmp_path / "receipt.json"
    probes = iter(
        [
            ("process:llama-server",),
            ("listener:127.0.0.1:1234",),
            (),
            (),
        ]
    )
    sleeps: list[float] = []
    calls: list[tuple[list[str], str | None, tuple[int, ...]]] = []

    def runner(command, *, cwd, check, text, pass_fds):
        assert check is False
        assert text is True
        calls.append((command, cwd, pass_fds))
        return Completed(7)

    config = QueueConfig(
        lock_root=tmp_path / "locks",
        receipt_path=receipt,
        poll_seconds=0.01,
        idle_confirmations=2,
        target_label="v2:r6d",
        cwd=tmp_path,
    )

    exit_code = run_queued_command(
        config,
        ["python3", "-m", "tools.example"],
        busy_probe=lambda: next(probes),
        sleeper=sleeps.append,
        child_runner=runner,
    )

    assert exit_code == 7
    assert len(calls) == 1
    command, cwd, pass_fds = calls[0]
    assert command == ["python3", "-m", "tools.example"]
    assert cwd == str(tmp_path)
    assert len(pass_fds) == 1
    assert len(sleeps) == 3
    payload = json.loads(receipt.read_text())
    assert payload["state"] == "CHILD_EXITED"
    assert payload["lease_state"] == "RELEASED"
    assert payload["external_busy_polls"] == 2
    assert payload["child_exit_code"] == 7
    assert payload["pre_invoke_gate_passed_at"]
    assert payload["released_at"]


def test_quiescence_counter_resets_when_busy_returns(tmp_path: Path) -> None:
    probes = iter([(), ("process:llama-server",), (), ()])
    sleeps: list[float] = []
    calls: list[list[str]] = []

    def runner(command, *, cwd, check, text, pass_fds):
        calls.append(command)
        return Completed(0)

    result = run_queued_command(
        QueueConfig(
            lock_root=tmp_path / "locks",
            receipt_path=tmp_path / "receipt.json",
            poll_seconds=0.01,
            idle_confirmations=2,
        ),
        ["true"],
        busy_probe=lambda: next(probes),
        sleeper=sleeps.append,
        child_runner=runner,
    )

    assert result == 0
    assert calls == [["true"]]
    assert len(sleeps) == 3


def test_pre_invoke_gate_blocks_without_child_invocation(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(command, *, cwd, check, text, pass_fds):
        calls.append(command)
        return Completed(0)

    def gate() -> None:
        raise RuntimeError("authority advanced")

    receipt = tmp_path / "receipt.json"
    with pytest.raises(PreInvokeBlocked, match="authority advanced"):
        run_queued_command(
            QueueConfig(
                lock_root=tmp_path / "locks",
                receipt_path=receipt,
                poll_seconds=0.01,
                idle_confirmations=1,
            ),
            ["true"],
            pre_invoke_gate=gate,
            busy_probe=lambda: (),
            sleeper=lambda _: None,
            child_runner=runner,
        )

    assert calls == []
    payload = json.loads(receipt.read_text())
    assert payload["state"] == "PRE_INVOKE_BLOCKED"
    assert payload["lease_state"] == "RELEASED"
    assert payload["child_invoked_at"] is None
    assert payload["pre_invoke_error_type"] == "RuntimeError"


def test_controller_error_releases_lock_and_records_error(tmp_path: Path) -> None:
    receipt = tmp_path / "receipt.json"

    def broken_runner(*args, **kwargs):
        raise RuntimeError("boom")

    config = QueueConfig(
        lock_root=tmp_path / "locks",
        receipt_path=receipt,
        poll_seconds=0.01,
        idle_confirmations=1,
    )

    with pytest.raises(RuntimeError, match="boom"):
        run_queued_command(
            config,
            ["false"],
            busy_probe=lambda: (),
            sleeper=lambda _: None,
            child_runner=broken_runner,
        )

    payload = json.loads(receipt.read_text())
    assert payload["state"] == "CONTROLLER_ERROR"
    assert payload["lease_state"] == "RELEASED"
    assert payload["controller_error_type"] == "RuntimeError"
    assert payload["released_at"]

    calls = []

    def runner(command, *, cwd, check, text, pass_fds):
        calls.append(command)
        return Completed(0)

    assert (
        run_queued_command(
            QueueConfig(
                lock_root=tmp_path / "locks",
                receipt_path=tmp_path / "second.json",
                poll_seconds=0.01,
                idle_confirmations=1,
            ),
            ["true"],
            busy_probe=lambda: (),
            sleeper=lambda _: None,
            child_runner=runner,
        )
        == 0
    )
    assert calls == [["true"]]


def test_invalid_config_does_not_invoke_child(tmp_path: Path) -> None:
    called = False

    def runner(*args, **kwargs):
        nonlocal called
        called = True
        return Completed(0)

    with pytest.raises(Exception):
        run_queued_command(
            QueueConfig(
                lock_root=tmp_path / "locks",
                receipt_path=tmp_path / "receipt.json",
                poll_seconds=0,
            ),
            ["true"],
            child_runner=runner,
        )
    assert called is False


def test_empty_command_fails_before_queue(tmp_path: Path) -> None:
    with pytest.raises(Exception):
        run_queued_command(
            QueueConfig(
                lock_root=tmp_path / "locks",
                receipt_path=tmp_path / "receipt.json",
            ),
            [],
        )


def test_cooperative_lock_waits_then_runs(tmp_path: Path) -> None:
    import fcntl

    lock_root = tmp_path / "locks"
    lock_root.mkdir()
    lock_path = lock_root / _safe_resource_id("gpu-test")
    holder = lock_path.open("a+")
    fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    sleeps = []
    calls = []

    def sleeper(seconds: float) -> None:
        sleeps.append(seconds)
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN)

    def runner(command, *, cwd, check, text, pass_fds):
        calls.append(command)
        return Completed(0)

    try:
        result = run_queued_command(
            QueueConfig(
                resource_key="gpu-test",
                lock_root=lock_root,
                receipt_path=tmp_path / "receipt.json",
                poll_seconds=0.01,
                idle_confirmations=1,
            ),
            ["true"],
            busy_probe=lambda: (),
            sleeper=sleeper,
            child_runner=runner,
        )
    finally:
        holder.close()

    assert result == 0
    assert sleeps == [0.01]
    assert calls == [["true"]]
    payload = json.loads((tmp_path / "receipt.json").read_text())
    assert payload["lease_wait_polls"] == 1
    assert payload["state"] == "CHILD_EXITED"
    assert payload["lease_state"] == "RELEASED"

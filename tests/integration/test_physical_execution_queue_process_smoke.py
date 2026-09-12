from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tools.physical_execution_queue import (
    PreInvokeBlocked,
    QueueConfig,
    _safe_resource_id,
    run_queued_command,
)


fcntl = pytest.importorskip("fcntl")
REPO_ROOT = Path(__file__).resolve().parents[2]


def _wait_for_path(path: Path, *, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.01)
    raise AssertionError(f"timed out waiting for {path}")


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _queue_helper(
    *,
    resource_key: str,
    lock_root: Path,
    receipt: Path,
    child_code: str,
    child_args: list[Path],
) -> subprocess.Popen[str]:
    helper_code = "\n".join(
        [
            "import sys",
            "from pathlib import Path",
            "from tools.physical_execution_queue import QueueConfig, run_queued_command",
            f"child_code = {child_code!r}",
            f"child_args = {[str(path) for path in child_args]!r}",
            "config = QueueConfig(",
            f"    resource_key={resource_key!r},",
            f"    lock_root=Path({str(lock_root)!r}),",
            f"    receipt_path=Path({str(receipt)!r}),",
            "    poll_seconds=0.02,",
            "    idle_confirmations=1,",
            ")",
            "raise SystemExit(run_queued_command(",
            "    config,",
            "    [sys.executable, '-c', child_code, *child_args],",
            "    busy_probe=lambda: (),",
            "))",
        ]
    )
    return subprocess.Popen(
        [sys.executable, "-c", helper_code],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_real_process_cooperative_lock_serializes(tmp_path: Path) -> None:
    resource_key = "process-smoke:serialize"
    lock_root = tmp_path / "locks"
    first_ready = tmp_path / "first-ready"
    first_done = tmp_path / "first-done"
    second_marker = tmp_path / "second"
    child_code = (
        "from pathlib import Path; import sys,time; "
        "Path(sys.argv[1]).write_text('ready'); "
        "time.sleep(0.45); Path(sys.argv[2]).write_text('done')"
    )
    helper = _queue_helper(
        resource_key=resource_key,
        lock_root=lock_root,
        receipt=tmp_path / "first-receipt.json",
        child_code=child_code,
        child_args=[first_ready, first_done],
    )
    try:
        _wait_for_path(first_ready)
        result = run_queued_command(
            QueueConfig(
                resource_key=resource_key,
                lock_root=lock_root,
                receipt_path=tmp_path / "second-receipt.json",
                poll_seconds=0.02,
                idle_confirmations=1,
            ),
            [
                sys.executable,
                "-c",
                "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('ran')",
                str(second_marker),
            ],
            busy_probe=lambda: (),
        )
        assert result == 0
        assert helper.wait(timeout=3) == 0
    finally:
        if helper.poll() is None:
            helper.kill()
            helper.wait(timeout=2)

    payload = json.loads((tmp_path / "second-receipt.json").read_text())
    assert payload["lease_wait_polls"] >= 1
    assert payload["state"] == "CHILD_EXITED"
    assert payload["lease_state"] == "RELEASED"
    assert first_done.exists()
    assert second_marker.exists()


def test_external_llama_process_is_waited_out(tmp_path: Path) -> None:
    sleep_binary = shutil.which("sleep")
    if sleep_binary is None:
        pytest.skip("sleep executable is required for process-name smoke")
    fake_llama = tmp_path / "llama-server"
    shutil.copy2(sleep_binary, fake_llama)
    fake_llama.chmod(0o755)
    external = subprocess.Popen([str(fake_llama), "0.35"])
    try:
        time.sleep(0.03)
        marker = tmp_path / "child-ran"
        receipt = tmp_path / "receipt.json"
        result = run_queued_command(
            QueueConfig(
                resource_key="process-smoke:external",
                lock_root=tmp_path / "locks",
                receipt_path=receipt,
                port=_free_tcp_port(),
                poll_seconds=0.02,
                idle_confirmations=1,
                busy_process_names=("llama-server",),
            ),
            [
                sys.executable,
                "-c",
                "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('ran')",
                str(marker),
            ],
        )
        assert result == 0
        assert marker.exists()
    finally:
        external.wait(timeout=2)

    payload = json.loads(receipt.read_text())
    assert payload["external_busy_polls"] >= 1
    assert any(
        reason.startswith("process:llama-server")
        for reason in payload["external_busy_last_reasons"]
    )


def test_real_listener_is_waited_out_before_quiescence(tmp_path: Path) -> None:
    port = _free_tcp_port()
    ready = tmp_path / "listener-ready"
    listener_code = (
        "import socket,sys,time; from pathlib import Path; "
        "s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); "
        "s.bind(('127.0.0.1', int(sys.argv[1]))); s.listen(1); "
        "Path(sys.argv[2]).write_text('ready'); time.sleep(0.35); s.close()"
    )
    listener = subprocess.Popen(
        [sys.executable, "-c", listener_code, str(port), str(ready)]
    )
    try:
        _wait_for_path(ready)
        receipt = tmp_path / "receipt.json"
        marker = tmp_path / "child-ran"
        result = run_queued_command(
            QueueConfig(
                resource_key="process-smoke:listener",
                lock_root=tmp_path / "locks",
                receipt_path=receipt,
                port=port,
                poll_seconds=0.02,
                idle_confirmations=2,
                busy_process_names=(),
            ),
            [
                sys.executable,
                "-c",
                "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('ran')",
                str(marker),
            ],
        )
        assert result == 0
        assert marker.exists()
        assert listener.wait(timeout=2) == 0
    finally:
        if listener.poll() is None:
            listener.kill()
            listener.wait(timeout=2)

    payload = json.loads(receipt.read_text())
    assert payload["external_busy_polls"] >= 1
    assert f"listener:127.0.0.1:{port}" in payload["external_busy_last_reasons"]
    assert payload["quiescent_at"]


def test_parent_death_keeps_lease_until_inherited_child_exits(tmp_path: Path) -> None:
    resource_key = "process-smoke:parent-death"
    lock_root = tmp_path / "locks"
    child_pid = tmp_path / "child-pid"
    child_ready = tmp_path / "child-ready"
    child_done = tmp_path / "child-done"
    child_code = (
        "from pathlib import Path; import os,sys,time; "
        "Path(sys.argv[1]).write_text(str(os.getpid())); "
        "Path(sys.argv[2]).write_text('ready'); time.sleep(0.65); "
        "Path(sys.argv[3]).write_text('done')"
    )
    helper = _queue_helper(
        resource_key=resource_key,
        lock_root=lock_root,
        receipt=tmp_path / "receipt.json",
        child_code=child_code,
        child_args=[child_pid, child_ready, child_done],
    )
    orphan_pid: int | None = None
    lock_file = None
    try:
        _wait_for_path(child_ready)
        orphan_pid = int(child_pid.read_text())
        helper.terminate()
        helper.wait(timeout=2)

        lock_path = lock_root / _safe_resource_id(resource_key)
        lock_file = lock_path.open("a+")
        with pytest.raises(BlockingIOError):
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        _wait_for_path(child_done)
        deadline = time.monotonic() + 2.0
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise AssertionError("lease stayed locked after inherited child exit")
                time.sleep(0.01)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        if helper.poll() is None:
            helper.kill()
            helper.wait(timeout=2)
        if orphan_pid is not None and not child_done.exists():
            try:
                os.kill(orphan_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if lock_file is not None:
            lock_file.close()


def test_controller_sigint_keeps_lease_until_inherited_child_exits(
    tmp_path: Path,
) -> None:
    resource_key = "process-smoke:controller-sigint"
    lock_root = tmp_path / "locks"
    receipt = tmp_path / "receipt.json"
    child_pid = tmp_path / "child-pid"
    child_ready = tmp_path / "child-ready"
    child_done = tmp_path / "child-done"
    child_code = (
        "from pathlib import Path; import os,sys,time; "
        "Path(sys.argv[1]).write_text(str(os.getpid())); "
        "Path(sys.argv[2]).write_text('ready'); time.sleep(0.9); "
        "Path(sys.argv[3]).write_text('done')"
    )
    helper = _queue_helper(
        resource_key=resource_key,
        lock_root=lock_root,
        receipt=receipt,
        child_code=child_code,
        child_args=[child_pid, child_ready, child_done],
    )
    orphan_pid: int | None = None
    lock_file = None
    try:
        _wait_for_path(child_ready)
        orphan_pid = int(child_pid.read_text())
        helper.send_signal(signal.SIGINT)
        assert helper.wait(timeout=3) != 0

        lock_path = lock_root / _safe_resource_id(resource_key)
        lock_file = lock_path.open("a+")
        with pytest.raises(BlockingIOError):
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        payload = json.loads(receipt.read_text())
        assert payload["state"] == "CONTROLLER_ERROR"
        assert payload["child_invoked_at"]
        assert payload["child_exit_code"] is None
        assert payload["lease_state"] == "RELEASE_UNOBSERVED_AFTER_CHILD_START"
        assert payload["released_at"] is None
        assert payload["controller_lease_fd_closed_at"]

        _wait_for_path(child_done)
        deadline = time.monotonic() + 2.0
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise AssertionError("lease stayed locked after SIGINT child exit")
                time.sleep(0.01)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        if helper.poll() is None:
            helper.kill()
            helper.wait(timeout=2)
        if orphan_pid is not None and not child_done.exists():
            try:
                os.kill(orphan_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if lock_file is not None:
            lock_file.close()


def test_pre_invoke_block_never_starts_real_child(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-exist"
    receipt = tmp_path / "receipt.json"

    def block() -> None:
        raise RuntimeError("fresh authority moved")

    with pytest.raises(PreInvokeBlocked, match="fresh authority moved"):
        run_queued_command(
            QueueConfig(
                resource_key="process-smoke:pre-invoke",
                lock_root=tmp_path / "locks",
                receipt_path=receipt,
                poll_seconds=0.02,
                idle_confirmations=1,
            ),
            [
                sys.executable,
                "-c",
                "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('bad')",
                str(marker),
            ],
            pre_invoke_gate=block,
            busy_probe=lambda: (),
        )

    payload = json.loads(receipt.read_text())
    assert marker.exists() is False
    assert payload["state"] == "PRE_INVOKE_BLOCKED"
    assert payload["child_invoked_at"] is None
    assert payload["lease_state"] == "RELEASED"

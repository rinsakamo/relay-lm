from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Sequence


DEFAULT_LOCK_ROOT = Path("/tmp/relaylm/physical/locks")
DEFAULT_RECEIPT_ROOT = Path("/tmp/relaylm/physical/receipts")
DEFAULT_RESOURCE_KEY = "llama-cpp:local-gpu"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 1234
DEFAULT_POLL_SECONDS = 5.0
DEFAULT_IDLE_CONFIRMATIONS = 2
DEFAULT_BUSY_PROCESS_NAMES = ("llama-server", "llama-cli", "llama-run")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, path)


def _safe_resource_id(resource_key: str) -> str:
    digest = hashlib.sha256(resource_key.encode("utf-8")).hexdigest()[:16]
    return f"{digest}.lock"


def _process_executable_names(proc_root: Path = Path("/proc")) -> set[str]:
    names: set[str] = set()
    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return names
    for entry in entries:
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        exe = entry / "exe"
        try:
            names.add(Path(os.readlink(exe)).name)
            continue
        except OSError:
            pass
        try:
            raw = (entry / "cmdline").read_bytes().split(b"\0", 1)[0]
        except OSError:
            continue
        if raw:
            names.add(Path(os.fsdecode(raw)).name)
    return names


def port_is_bindable(host: str, port: int) -> bool:
    """Return whether the target can bind the configured listener right now.

    This intentionally matches the fail-closed target transaction contract rather
    than merely asking whether a process currently accepts TCP connections. A
    port can have no LISTEN socket yet still be temporarily unbindable, for
    example because of local TCP lifecycle state.
    """

    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _listener_busy(host: str, port: int) -> bool:
    """Compatibility name for the target-facing port-unavailable predicate."""

    return not port_is_bindable(host, port)


def probe_external_busy(
    *,
    host: str,
    port: int,
    busy_process_names: Iterable[str],
) -> tuple[str, ...]:
    reasons: list[str] = []
    process_names = _process_executable_names()
    matches = sorted(set(busy_process_names).intersection(process_names))
    if matches:
        reasons.append("process:" + ",".join(matches))
    if _listener_busy(host, port):
        reasons.append(f"port_unavailable:{host}:{port}")
    return tuple(reasons)


@dataclass(frozen=True)
class QueueConfig:
    resource_key: str = DEFAULT_RESOURCE_KEY
    lock_root: Path = DEFAULT_LOCK_ROOT
    receipt_path: Path | None = None
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    poll_seconds: float = DEFAULT_POLL_SECONDS
    idle_confirmations: int = DEFAULT_IDLE_CONFIRMATIONS
    busy_process_names: tuple[str, ...] = DEFAULT_BUSY_PROCESS_NAMES
    target_label: str = "unspecified"
    cwd: Path | None = None

    def resolved_receipt_path(self) -> Path:
        if self.receipt_path is not None:
            return self.receipt_path
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return DEFAULT_RECEIPT_ROOT / (
            f"{stamp}-{os.getpid()}-{uuid.uuid4().hex[:8]}.json"
        )


class PhysicalQueueError(RuntimeError):
    pass


class PreInvokeBlocked(PhysicalQueueError):
    """The restartable final gate blocked before the scientific child started."""


def run_queued_command(
    config: QueueConfig,
    command: Sequence[str],
    *,
    pre_invoke_gate: Callable[[], None] | None = None,
    busy_probe: Callable[[], tuple[str, ...]] | None = None,
    sleeper: Callable[[float], None] = time.sleep,
    child_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> int:
    if not command:
        raise PhysicalQueueError("child command must not be empty")
    if config.poll_seconds <= 0:
        raise PhysicalQueueError("poll_seconds must be > 0")
    if config.idle_confirmations < 1:
        raise PhysicalQueueError("idle_confirmations must be >= 1")

    receipt_path = config.resolved_receipt_path()
    request_id = uuid.uuid4().hex
    lock_path = config.lock_root / _safe_resource_id(config.resource_key)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    receipt: dict[str, object] = {
        "schema_version": 2,
        "request_id": request_id,
        "target_label": config.target_label,
        "resource_key": config.resource_key,
        "lock_path": str(lock_path),
        "receipt_path": str(receipt_path),
        "command_executable": Path(command[0]).name,
        "command_argv_sha256": hashlib.sha256(
            json.dumps(
                list(command),
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest(),
        "cwd": str(config.cwd) if config.cwd is not None else None,
        "queued_at": _utc_now(),
        "state": "QUEUED",
        "lease_state": "REQUESTED",
        "lease_wait_polls": 0,
        "external_busy_polls": 0,
        "invocation_boundary_busy_polls": 0,
        "external_busy_first_at": None,
        "external_busy_last_at": None,
        "external_busy_last_reasons": [],
        "lease_acquired_at": None,
        "quiescent_at": None,
        "pre_invoke_gate_attempts": 0,
        "pre_invoke_gate_started_at": None,
        "pre_invoke_gate_passed_at": None,
        "child_invoked_at": None,
        "child_exit_code": None,
        "released_at": None,
    }
    _atomic_write_json(receipt_path, receipt)

    if busy_probe is None:

        def default_busy_probe() -> tuple[str, ...]:
            return probe_external_busy(
                host=config.host,
                port=config.port,
                busy_process_names=config.busy_process_names,
            )

        busy_probe = default_busy_probe

    def record_external_busy(
        reasons: tuple[str, ...],
        *,
        invocation_boundary: bool,
    ) -> None:
        now = _utc_now()
        receipt["state"] = "WAITING_EXTERNAL_RUNTIME"
        receipt["external_busy_polls"] = int(receipt["external_busy_polls"]) + 1
        if invocation_boundary:
            receipt["invocation_boundary_busy_polls"] = (
                int(receipt["invocation_boundary_busy_polls"]) + 1
            )
        receipt["external_busy_first_at"] = (
            receipt["external_busy_first_at"] or now
        )
        receipt["external_busy_last_at"] = now
        receipt["external_busy_last_reasons"] = list(reasons)
        _atomic_write_json(receipt_path, receipt)

    lock_file = lock_path.open("a+", encoding="utf-8")
    locked = False
    try:
        while not locked:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except BlockingIOError:
                receipt["state"] = "WAITING_RESOURCE"
                receipt["lease_wait_polls"] = int(receipt["lease_wait_polls"]) + 1
                _atomic_write_json(receipt_path, receipt)
                sleeper(config.poll_seconds)

        receipt["state"] = "LEASE_ACQUIRED"
        receipt["lease_state"] = "ACQUIRED"
        receipt["lease_acquired_at"] = _utc_now()
        _atomic_write_json(receipt_path, receipt)

        while True:
            idle_count = 0
            while idle_count < config.idle_confirmations:
                reasons = busy_probe()
                if reasons:
                    idle_count = 0
                    record_external_busy(reasons, invocation_boundary=False)
                else:
                    idle_count += 1
                    receipt["state"] = "VERIFYING_QUIESCENCE"
                    _atomic_write_json(receipt_path, receipt)
                if idle_count < config.idle_confirmations:
                    sleeper(config.poll_seconds)

            receipt["state"] = "FINAL_PREFLIGHT"
            receipt["quiescent_at"] = _utc_now()
            receipt["pre_invoke_gate_started_at"] = _utc_now()
            receipt["pre_invoke_gate_attempts"] = (
                int(receipt["pre_invoke_gate_attempts"]) + 1
            )
            _atomic_write_json(receipt_path, receipt)

            if pre_invoke_gate is not None:
                try:
                    pre_invoke_gate()
                except BaseException as exc:
                    receipt["state"] = "PRE_INVOKE_BLOCKED"
                    receipt["pre_invoke_error_type"] = type(exc).__name__
                    receipt["pre_invoke_error"] = str(exc)
                    _atomic_write_json(receipt_path, receipt)
                    raise PreInvokeBlocked(str(exc)) from exc

            receipt["pre_invoke_gate_passed_at"] = _utc_now()
            receipt["state"] = "READY_TO_INVOKE"
            _atomic_write_json(receipt_path, receipt)

            # Recheck the exact target-facing port condition after the potentially
            # slow authority/environment gate. If external state changed during
            # final preflight, return to quiescence without invoking the child.
            reasons = busy_probe()
            if reasons:
                record_external_busy(reasons, invocation_boundary=True)
                sleeper(config.poll_seconds)
                continue
            break

        receipt["state"] = "RUNNING"
        receipt["child_invoked_at"] = _utc_now()
        _atomic_write_json(receipt_path, receipt)
        completed = child_runner(
            list(command),
            cwd=str(config.cwd) if config.cwd is not None else None,
            check=False,
            text=True,
            pass_fds=(lock_file.fileno(),),
        )
        exit_code = int(completed.returncode)
        receipt["child_exit_code"] = exit_code
        receipt["state"] = "CHILD_EXITED"
        _atomic_write_json(receipt_path, receipt)
        return exit_code
    except PreInvokeBlocked:
        raise
    except BaseException as exc:
        receipt["state"] = "CONTROLLER_ERROR"
        receipt["controller_error_type"] = type(exc).__name__
        receipt["controller_error"] = str(exc)
        _atomic_write_json(receipt_path, receipt)
        raise
    finally:
        if locked:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()
        receipt["lease_state"] = "RELEASED"
        receipt["released_at"] = _utc_now()
        _atomic_write_json(receipt_path, receipt)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Internal primitive: serialize one repository-owned llama.cpp physical "
            "command on the canonical local GPU lease."
        )
    )
    parser.add_argument("--resource-key", default=DEFAULT_RESOURCE_KEY)
    parser.add_argument("--lock-root", type=Path, default=DEFAULT_LOCK_ROOT)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS)
    parser.add_argument(
        "--idle-confirmations",
        type=int,
        default=DEFAULT_IDLE_CONFIRMATIONS,
    )
    parser.add_argument(
        "--busy-process-name",
        action="append",
        dest="busy_process_names",
        default=None,
        help="Executable basename that counts as external llama.cpp use; repeatable.",
    )
    parser.add_argument("--target-label", default="unspecified")
    parser.add_argument("--cwd", type=Path)
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Internal child command after --. Prefer tools.relay_physical_run.",
    )
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("a child command is required after --")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    config = QueueConfig(
        resource_key=args.resource_key,
        lock_root=args.lock_root,
        receipt_path=args.receipt,
        host=args.host,
        port=args.port,
        poll_seconds=args.poll_seconds,
        idle_confirmations=args.idle_confirmations,
        busy_process_names=tuple(
            args.busy_process_names or DEFAULT_BUSY_PROCESS_NAMES
        ),
        target_label=args.target_label,
        cwd=args.cwd,
    )
    receipt = config.resolved_receipt_path()
    if config.receipt_path is None:
        config = QueueConfig(**{**asdict(config), "receipt_path": receipt})
    print(f"physical queue receipt: {receipt}", flush=True)
    return run_queued_command(config, args.command)


if __name__ == "__main__":
    sys.exit(main())

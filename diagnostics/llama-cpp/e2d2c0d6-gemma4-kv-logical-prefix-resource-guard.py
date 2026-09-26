#!/usr/bin/env python3
import argparse
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import shutil
import sys
import time

RESOURCE_KEY = "llama-cpp:local-gpu"
LOCK_ROOT = Path("/tmp/relaylm/physical/locks")
BUSY_NAMES = {"llama-server", "llama-cli", "llama-run"}


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def safe_resource_id(resource_key: str) -> str:
    digest = hashlib.sha256(resource_key.encode("utf-8")).hexdigest()[:16]
    return f"{digest}.lock"


def process_executable_names():
    names = set()
    proc_root = Path("/proc")
    try:
        entries = list(proc_root.iterdir())
    except OSError as exc:
        raise RuntimeError(f"cannot inspect /proc for local GPU runtimes: {exc}") from exc
    for entry in entries:
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            names.add(Path(os.readlink(entry / "exe")).name)
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


def interpret_connect_ex(code: int) -> bool:
    if code == 0:
        return True
    if code == errno.ECONNREFUSED:
        return False
    raise RuntimeError(
        f"loopback listener probe inconclusive: connect_ex errno={code} "
        f"({os.strerror(code) if code > 0 else 'unknown'})"
    )


def listener_busy(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            code = sock.connect_ex((host, port))
    except (OSError, TimeoutError) as exc:
        raise RuntimeError(f"loopback listener probe failed: {type(exc).__name__}: {exc}") from exc
    return interpret_connect_ex(code)


def gpu_compute_processes():
    exe = shutil.which("nvidia-smi")
    if exe is None:
        raise RuntimeError("nvidia-smi unavailable for GPU quiescence check")
    cp = subprocess.run(
        [exe, "--query-compute-apps=pid,process_name", "--format=csv,noheader,nounits"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"nvidia-smi compute query failed rc={cp.returncode}: {cp.stderr.strip()}")
    rows = []
    for line in cp.stdout.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("no running"):
            continue
        parts = [x.strip() for x in line.split(",", 1)]
        if len(parts) != 2 or not parts[0].isdigit():
            raise RuntimeError(f"unparseable nvidia-smi compute row: {line!r}")
        rows.append({"pid": int(parts[0]), "process_name": parts[1]})
    return rows


def gpu_inventory():
    exe = shutil.which("nvidia-smi")
    if exe is None:
        raise RuntimeError("nvidia-smi unavailable for GPU inventory")
    cp = subprocess.run(
        [exe, "--query-gpu=index,uuid,name,driver_version,memory.total", "--format=csv,noheader,nounits"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"nvidia-smi inventory query failed rc={cp.returncode}: {cp.stderr.strip()}")
    rows = []
    for line in cp.stdout.splitlines():
        parts = [x.strip() for x in line.split(",", 4)]
        if len(parts) != 5 or not parts[0].isdigit() or not parts[4].isdigit():
            raise RuntimeError(f"unparseable nvidia-smi inventory row: {line!r}")
        rows.append({
            "index": int(parts[0]),
            "uuid": parts[1],
            "name": parts[2],
            "driver_version": parts[3],
            "memory_total_mib": int(parts[4]),
        })
    if not rows:
        raise RuntimeError("nvidia-smi returned no GPU inventory")
    return rows


def validate_expected_gpu_inventory(observed, expected_path: Path | None):
    if expected_path is None:
        return {"required": False, "match": None, "expected": None, "observed": observed}
    if not expected_path.is_file():
        raise RuntimeError(f"expected GPU inventory missing: {expected_path}")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    if not isinstance(expected, list) or not expected:
        raise RuntimeError("expected GPU inventory must be a non-empty list")
    return {
        "required": True,
        "match": observed == expected,
        "expected": expected,
        "observed": observed,
    }


def validate_inherited_lock_fd(fd: int, lock_path: Path):
    if fd <= 2:
        raise RuntimeError(f"invalid inherited queue lease fd: {fd}")
    proc_fd = Path(f"/proc/self/fd/{fd}")
    if not proc_fd.exists():
        raise RuntimeError(f"inherited queue lease fd unavailable: {fd}")
    target = os.readlink(proc_fd)
    if target != str(lock_path):
        raise RuntimeError(
            f"inherited queue lease fd path mismatch: {target!r} != {str(lock_path)!r}"
        )
    probe = lock_path.open("a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        else:
            fcntl.flock(probe.fileno(), fcntl.LOCK_UN)
            raise RuntimeError("inherited queue lease fd is not backed by a held flock")
    finally:
        probe.close()


def require_external_quiescence(evidence_root: Path):
    observations = []
    for index in range(2):
        names = process_executable_names()
        busy = sorted(BUSY_NAMES.intersection(names))
        default_listener_busy = listener_busy("127.0.0.1", 1234)
        compute = gpu_compute_processes()
        observation = {
            "observation": index + 1,
            "busy_processes": busy,
            "listener_127_0_0_1_1234": default_listener_busy,
            "gpu_compute_processes": compute,
        }
        observations.append(observation)
        write_json(evidence_root / "external-quiescence.json", observations)
        reasons = list(busy)
        if default_listener_busy:
            reasons.append("listener:127.0.0.1:1234")
        if compute:
            reasons.extend(f"gpu:{x['pid']}:{x['process_name']}" for x in compute)
        if reasons:
            raise RuntimeError(f"external local-GPU runtime busy: {','.join(reasons)}")
        if index == 0:
            time.sleep(5)
    return observations


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-root", type=Path, required=True)
    ap.add_argument("--expected-gpu-inventory", type=Path)
    ap.add_argument("--inherited-lock-fd", type=int)
    ap.add_argument("command", nargs=argparse.REMAINDER)
    args = ap.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        ap.error("child command is required after --")
    if args.evidence_root.exists():
        raise SystemExit(f"evidence root must not exist: {args.evidence_root}")

    args.evidence_root.mkdir(parents=True)
    observed_gpu_inventory = gpu_inventory()
    write_json(args.evidence_root / "gpu-inventory.json", observed_gpu_inventory)
    LOCK_ROOT.mkdir(parents=True, exist_ok=True)
    lock_path = LOCK_ROOT / safe_resource_id(RESOURCE_KEY)
    guard_path = args.evidence_root / "guard.json"

    guard = {
        "resource_key": RESOURCE_KEY,
        "lock_path": str(lock_path),
        "guard_state": "INITIALIZING",
        "lock_acquired": False,
        "child_invoked": False,
        "child_returncode": None,
        "failure": None,
        "campaign_queue_receipt_created": False,
        "campaign_queue_or_spend_artifact_touched": False,
        "gpu_identity_required": args.expected_gpu_inventory is not None,
        "gpu_identity_match": None,
        "lock_inherited": args.inherited_lock_fd is not None,
        "inherited_lock_fd": args.inherited_lock_fd,
    }
    write_json(guard_path, guard)

    try:
        gpu_identity = validate_expected_gpu_inventory(
            observed_gpu_inventory, args.expected_gpu_inventory
        )
    except Exception as exc:
        guard["guard_state"] = "GPU_IDENTITY_VALIDATION_FAILED"
        guard["failure"] = f"{type(exc).__name__}: {exc}"
        write_json(guard_path, guard)
        return 9
    write_json(args.evidence_root / "gpu-identity-comparison.json", gpu_identity)
    guard["gpu_identity_match"] = gpu_identity["match"]
    if gpu_identity["required"] and not gpu_identity["match"]:
        guard["guard_state"] = "GPU_IDENTITY_MISMATCH"
        guard["failure"] = "current GPU inventory differs from frozen preparation identity"
        write_json(guard_path, guard)
        return 9

    lock_file = None
    lock_fd = None
    owns_lock = False
    try:
        if args.inherited_lock_fd is not None:
            validate_inherited_lock_fd(args.inherited_lock_fd, lock_path)
            lock_fd = args.inherited_lock_fd
            guard["guard_state"] = "INHERITED_CANONICAL_QUEUE_FLOCK_VALIDATED"
            guard["lock_acquired"] = True
            write_json(guard_path, guard)
        else:
            lock_file = lock_path.open("a+", encoding="utf-8")
            lock_fd = lock_file.fileno()
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                guard["guard_state"] = "NOT_ACQUIRED_BUSY"
                guard["failure"] = "canonical local GPU flock is already held"
                write_json(guard_path, guard)
                return 6
            owns_lock = True
            guard["guard_state"] = "ACQUIRED_CANONICAL_DIAGNOSTIC_FLOCK"
            guard["lock_acquired"] = True
            write_json(guard_path, guard)

        try:
            require_external_quiescence(args.evidence_root)
        except Exception as exc:
            guard["failure"] = f"{type(exc).__name__}: {exc}"
            write_json(guard_path, guard)
            return 7

        write_json(args.evidence_root / "child.argv.json", command)
        guard["child_invoked"] = True
        write_json(guard_path, guard)

        assert lock_fd is not None
        run = subprocess.run(command, pass_fds=(lock_fd,))
        guard["child_returncode"] = run.returncode
        write_json(args.evidence_root / "child.exit.json", {"returncode": run.returncode})
        write_json(guard_path, guard)
        return run.returncode
    except Exception as exc:
        guard["failure"] = f"{type(exc).__name__}: {exc}"
        write_json(guard_path, guard)
        return 8
    finally:
        if owns_lock and lock_file is not None and guard.get("lock_acquired"):
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except OSError as exc:
                guard["failure"] = guard.get("failure") or f"unlock failed: {exc}"
                guard["guard_state"] = "RELEASE_FAILED_CANONICAL_DIAGNOSTIC_FLOCK"
            else:
                if guard.get("failure") is None:
                    guard["guard_state"] = "RELEASED_CANONICAL_DIAGNOSTIC_FLOCK"
                else:
                    guard["guard_state"] = "RELEASED_WITH_FAILURE_CANONICAL_DIAGNOSTIC_FLOCK"
            write_json(guard_path, guard)
        elif args.inherited_lock_fd is not None and guard.get("lock_acquired"):
            if guard.get("failure") is None:
                guard["guard_state"] = "INHERITED_CANONICAL_QUEUE_FLOCK_PRESERVED"
            else:
                guard["guard_state"] = "INHERITED_CANONICAL_QUEUE_FLOCK_PRESERVED_WITH_FAILURE"
            write_json(guard_path, guard)
        if lock_file is not None:
            lock_file.close()


if __name__ == "__main__":
    sys.exit(main())

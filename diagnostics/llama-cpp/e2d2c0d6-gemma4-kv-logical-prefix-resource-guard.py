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
        [exe, "--query-gpu=index,uuid,name", "--format=csv,noheader"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"nvidia-smi inventory query failed rc={cp.returncode}: {cp.stderr.strip()}")
    rows = []
    for line in cp.stdout.splitlines():
        parts = [x.strip() for x in line.split(",", 2)]
        if len(parts) != 3 or not parts[0].isdigit():
            raise RuntimeError(f"unparseable nvidia-smi inventory row: {line!r}")
        rows.append({"index": int(parts[0]), "uuid": parts[1], "name": parts[2]})
    if not rows:
        raise RuntimeError("nvidia-smi returned no GPU inventory")
    return rows


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
    write_json(args.evidence_root / "gpu-inventory.json", gpu_inventory())
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
    }
    write_json(guard_path, guard)

    lock_file = lock_path.open("a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            guard["guard_state"] = "NOT_ACQUIRED_BUSY"
            guard["failure"] = "canonical local GPU flock is already held"
            write_json(guard_path, guard)
            return 6

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

        run = subprocess.run(command, pass_fds=(lock_file.fileno(),))
        guard["child_returncode"] = run.returncode
        write_json(args.evidence_root / "child.exit.json", {"returncode": run.returncode})
        write_json(guard_path, guard)
        return run.returncode
    except Exception as exc:
        guard["failure"] = f"{type(exc).__name__}: {exc}"
        write_json(guard_path, guard)
        return 8
    finally:
        if guard.get("lock_acquired"):
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
        lock_file.close()


if __name__ == "__main__":
    sys.exit(main())

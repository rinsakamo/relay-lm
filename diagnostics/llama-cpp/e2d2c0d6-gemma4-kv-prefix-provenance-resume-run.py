#!/usr/bin/env python3
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

RESOURCE_KEY = "llama-cpp:local-gpu"
LOCK_ROOT = Path("/tmp/relaylm/physical/locks")
BUSY_NAMES = {"llama-server", "llama-cli", "llama-run"}


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_terminal(root: Path, *, stage: str, reason: str):
    write_json(root / "terminal.json", {
        "primary_classification": "PROBE_NOT_EXERCISED",
        "measured_l0_submitted": False,
        "stage": stage,
        "reason": reason,
    })


def safe_resource_id(resource_key: str) -> str:
    digest = hashlib.sha256(resource_key.encode("utf-8")).hexdigest()[:16]
    return f"{digest}.lock"


def process_executable_names():
    names = set()
    proc_root = Path("/proc")
    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return names
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


def listener_busy(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def require_external_quiescence(preflight_root: Path):
    observations = []
    for index in range(2):
        names = process_executable_names()
        busy = sorted(BUSY_NAMES.intersection(names))
        default_listener_busy = listener_busy("127.0.0.1", 1234)
        observations.append({
            "observation": index + 1,
            "busy_processes": busy,
            "listener_127_0_0_1_1234": default_listener_busy,
        })
        reasons = list(busy)
        if default_listener_busy:
            reasons.append("listener:127.0.0.1:1234")
        if reasons:
            write_json(preflight_root / "external-quiescence.json", observations)
            raise RuntimeError(f"external local-GPU runtime busy: {','.join(reasons)}")
        if index == 0:
            time.sleep(5)
    write_json(preflight_root / "external-quiescence.json", observations)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--search-root", action="append", type=Path, required=True)
    ap.add_argument("--preflight-root", type=Path, required=True)
    ap.add_argument("--server-bin", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--port-wr", type=int, required=True)
    ap.add_argument("--port-wr2", type=int, required=True)
    ap.add_argument("--port-c", type=int, required=True)
    args = ap.parse_args()

    if args.preflight_root.exists():
        raise SystemExit(f"preflight root must not exist: {args.preflight_root}")
    if args.out_root.exists():
        raise SystemExit(f"measured output root must not exist: {args.out_root}")

    args.preflight_root.mkdir(parents=True)

    here = Path(__file__).resolve().parent
    parser_selftest = here / "e2d2c0d6-gemma4-kv-startup-evidence-parser-selftest.py"
    selftest = subprocess.run(
        [sys.executable, str(parser_selftest)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (args.preflight_root / "startup-evidence-parser-selftest.json").write_bytes(selftest.stdout)
    (args.preflight_root / "startup-evidence-parser-selftest.stderr.txt").write_bytes(selftest.stderr)
    if selftest.returncode != 0:
        write_terminal(
            args.preflight_root,
            stage="startup_evidence_parser_selftest",
            reason="STARTUP_EVIDENCE_PARSER_SELFTEST_FAIL",
        )
        return 9
    try:
        selftest_obj = json.loads(selftest.stdout)
    except Exception as exc:
        write_terminal(
            args.preflight_root,
            stage="startup_evidence_parser_selftest",
            reason=f"invalid self-test JSON: {exc}",
        )
        return 9
    if selftest_obj.get("status") != "STARTUP_EVIDENCE_PARSER_SELFTEST_PASS":
        write_terminal(
            args.preflight_root,
            stage="startup_evidence_parser_selftest",
            reason=f"unexpected self-test status: {selftest_obj.get('status')}",
        )
        return 9

    # Cooperate with the repository's canonical shared local-GPU flock without
    # creating or mutating any #2965 campaign queue/receipt/spend artifact.
    LOCK_ROOT.mkdir(parents=True, exist_ok=True)
    lock_path = LOCK_ROOT / safe_resource_id(RESOURCE_KEY)
    lock_file = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        write_json(args.preflight_root / "shared-resource-guard.json", {
            "resource_key": RESOURCE_KEY,
            "lock_path": str(lock_path),
            "guard_state": "NOT_ACQUIRED_BUSY",
            "campaign_queue_receipt_created": False,
            "campaign_queue_or_spend_artifact_touched": False,
        })
        write_terminal(
            args.preflight_root,
            stage="shared_resource_guard",
            reason="canonical local GPU flock is already held",
        )
        lock_file.close()
        return 6

    guard_path = args.preflight_root / "shared-resource-guard.json"
    write_json(guard_path, {
        "resource_key": RESOURCE_KEY,
        "lock_path": str(lock_path),
        "guard_state": "ACQUIRED_CANONICAL_DIAGNOSTIC_FLOCK",
        "campaign_queue_receipt_created": False,
        "campaign_queue_or_spend_artifact_touched": False,
    })

    try:
        try:
            require_external_quiescence(args.preflight_root)
        except Exception as exc:
            write_terminal(
                args.preflight_root,
                stage="shared_resource_guard",
                reason=str(exc),
            )
            return 7

        locator = here / "e2d2c0d6-gemma4-kv-artifact-locator.py"
        runner = here / "e2d2c0d6-gemma4-kv-prefix-provenance-run.py"

        locator_json = args.preflight_root / "artifact-locator.json"
        locator_cmd = [
            sys.executable,
            str(locator),
            *[str(p) for p in args.search_root],
            "--out",
            str(locator_json),
        ]
        write_json(args.preflight_root / "artifact-locator.argv.json", locator_cmd)
        located = subprocess.run(locator_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (args.preflight_root / "artifact-locator.stdout.txt").write_bytes(located.stdout)
        (args.preflight_root / "artifact-locator.stderr.txt").write_bytes(located.stderr)

        if located.returncode != 0:
            write_terminal(
                args.preflight_root,
                stage="artifact_locator",
                reason="ARTIFACT_LOCATOR_FAIL",
            )
            return 2

        try:
            obj = json.loads(locator_json.read_text(encoding="utf-8"))
        except Exception as exc:
            write_terminal(
                args.preflight_root,
                stage="artifact_locator",
                reason=f"invalid locator JSON: {exc}",
            )
            return 3

        if obj.get("status") != "ARTIFACT_LOCATOR_PASS":
            write_terminal(
                args.preflight_root,
                stage="artifact_locator",
                reason=f"unexpected locator status: {obj.get('status')}",
            )
            return 3

        selected = obj.get("selected")
        if not isinstance(selected, dict):
            write_terminal(
                args.preflight_root,
                stage="artifact_locator",
                reason="locator selected block missing",
            )
            return 4

        required = ("warm_tokens", "target_tokens", "L0", "L1", "LC")
        missing = [name for name in required if name not in selected]
        if missing:
            write_terminal(
                args.preflight_root,
                stage="artifact_locator",
                reason=f"locator selected entries missing: {missing}",
            )
            return 4

        paths = {}
        for name in required:
            entry = selected[name]
            try:
                artifact = Path(entry["path"])
            except Exception:
                write_terminal(
                    args.preflight_root,
                    stage="artifact_locator",
                    reason=f"invalid selected artifact entry: {name}",
                )
                return 5
            if not artifact.is_file():
                write_terminal(
                    args.preflight_root,
                    stage="artifact_locator",
                    reason=f"selected artifact disappeared: {name}: {artifact}",
                )
                return 5
            paths[name] = artifact

        runner_cmd = [
            sys.executable,
            str(runner),
            "--server-bin", str(args.server_bin),
            "--model", str(args.model),
            "--warm-tokens", str(paths["warm_tokens"]),
            "--target-tokens", str(paths["target_tokens"]),
            "--l0-request", str(paths["L0"]),
            "--l1-request", str(paths["L1"]),
            "--lc-request", str(paths["LC"]),
            "--out-root", str(args.out_root),
            "--port-wr", str(args.port_wr),
            "--port-wr2", str(args.port_wr2),
            "--port-c", str(args.port_c),
        ]
        write_json(args.preflight_root / "measured-runner.argv.json", runner_cmd)
        write_json(args.preflight_root / "selected-artifacts.json", {
            name: {"path": str(paths[name]), "locator_entry": selected[name]}
            for name in required
        })

        # This is the only transition from artifact discovery into measured execution.
        run = subprocess.run(runner_cmd, pass_fds=(lock_file.fileno(),))
        write_json(args.preflight_root / "measured-runner.exit.json", {
            "returncode": run.returncode,
            "measured_output_root": str(args.out_root),
        })
        return run.returncode
    except Exception as exc:
        write_terminal(
            args.preflight_root,
            stage="resume_wrapper",
            reason=f"{type(exc).__name__}: {exc}",
        )
        return 8
    finally:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()
        guard = json.loads(guard_path.read_text(encoding="utf-8"))
        guard["guard_state"] = "RELEASED_CANONICAL_DIAGNOSTIC_FLOCK"
        write_json(guard_path, guard)


if __name__ == "__main__":
    sys.exit(main())

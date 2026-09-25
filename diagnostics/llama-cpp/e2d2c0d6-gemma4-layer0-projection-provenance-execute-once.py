#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ATTEMPT_ID = "layer0-projection-provenance-20260925-a"

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-measured-run.py"
RUNNER_SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-measured-run-selftest.py"
POSTHOC_SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-posthoc-selftest.py"
DIGEST_SELFTEST = HERE / "e2d2c0d6-gemma4-canonical-kv-directory-digest-selftest.py"
RESOURCE_GUARD = HERE / "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py"
RESOURCE_GUARD_SELFTEST = HERE / "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard-selftest.py"

def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def run_json(label: str, path: Path, preflight_root: Path, expected_status: str):
    cp = subprocess.run(
        [sys.executable, str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    (preflight_root / f"{label}.stdout").write_bytes(cp.stdout)
    (preflight_root / f"{label}.stderr").write_bytes(cp.stderr)
    if cp.returncode != 0:
        raise RuntimeError(f"{label} failed rc={cp.returncode}")
    obj = json.loads(cp.stdout)
    if obj.get("status") != expected_status:
        raise RuntimeError(f"{label}: unexpected status {obj.get('status')}")
    return obj

def reconcile(out_root: Path, child_rc: int):
    terminal_path = out_root / "terminal.json"
    w_record = out_root / "server-W" / "W.request.json"
    c_record = out_root / "server-C" / "C.request.json"

    if terminal_path.is_file():
        measured = json.loads(terminal_path.read_text(encoding="utf-8"))
        return {
            "primary_classification": measured.get("primary_classification"),
            "measured_terminal_present": True,
            "measured_attempt_consumed": True,
            "measured_w_submitted": True,
            "measured_c_submitted": True,
            "rerun_authorized": False,
            "child_returncode": child_rc,
            "measured_terminal": measured,
        }

    if w_record.is_file():
        return {
            "primary_classification": "LAYER0_PROJECTION_PROVENANCE_PROBE_EXERCISED_INCOMPLETE",
            "measured_terminal_present": False,
            "measured_attempt_consumed": True,
            "measured_w_submitted": True,
            "measured_c_submitted": c_record.is_file(),
            "rerun_authorized": False,
            "child_returncode": child_rc,
        }

    return {
        "primary_classification": "LAYER0_PROJECTION_PROVENANCE_PROBE_NOT_EXERCISED",
        "measured_terminal_present": False,
        "measured_attempt_consumed": False,
        "measured_w_submitted": False,
        "measured_c_submitted": False,
        "rerun_authorized": False,
        "child_returncode": child_rc,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--descriptor", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--preflight-root", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--port-w", type=int, required=True)
    ap.add_argument("--port-c", type=int, required=True)
    args = ap.parse_args()

    descriptor_sha = os.environ.get("RELAYLM_PROVENANCE_MEASURED_DESCRIPTOR_SHA256", "")
    if len(descriptor_sha) != 64:
        raise SystemExit("RELAYLM_PROVENANCE_MEASURED_DESCRIPTOR_SHA256 is required")
    if args.preflight_root.exists():
        raise SystemExit(f"preflight root must not exist: {args.preflight_root}")
    if args.out_root.exists():
        raise SystemExit(f"measured output root must not exist: {args.out_root}")
    args.preflight_root.mkdir(parents=True)

    required = [
        RUNNER, RUNNER_SELFTEST, POSTHOC_SELFTEST, DIGEST_SELFTEST,
        RESOURCE_GUARD, RESOURCE_GUARD_SELFTEST,
    ]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        write_json(args.preflight_root / "terminal.json", {
            "attempt_id": ATTEMPT_ID,
            "primary_classification": "LAYER0_PROJECTION_PROVENANCE_PROBE_NOT_EXERCISED",
            "stage": "helper_presence",
            "reason": f"missing helpers: {missing}",
            "measured_attempt_consumed": False,
            "rerun_authorized": False,
        })
        return 3

    for path in required:
        cp = subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if cp.returncode != 0:
            (args.preflight_root / "py_compile.stderr").write_bytes(cp.stderr)
            write_json(args.preflight_root / "terminal.json", {
                "attempt_id": ATTEMPT_ID,
                "primary_classification": "LAYER0_PROJECTION_PROVENANCE_PROBE_NOT_EXERCISED",
                "stage": "py_compile",
                "reason": f"compile failed: {path}",
                "measured_attempt_consumed": False,
                "rerun_authorized": False,
            })
            return 4

    try:
        run_json(
            "runner-selftest", RUNNER_SELFTEST, args.preflight_root,
            "LAYER0_PROJECTION_PROVENANCE_MEASURED_RUNNER_SELFTEST_PASS",
        )
        run_json(
            "digest-selftest", DIGEST_SELFTEST, args.preflight_root,
            "CANONICAL_KV_DIRECTORY_DIGEST_SELFTEST_PASS",
        )
        run_json(
            "resource-guard-selftest", RESOURCE_GUARD_SELFTEST, args.preflight_root,
            "LOGICAL_PREFIX_RESOURCE_GUARD_SELFTEST_PASS",
        )
        run_json(
            "posthoc-selftest", POSTHOC_SELFTEST, args.preflight_root,
            "LAYER0_PROJECTION_PROVENANCE_POSTHOC_SELFTEST_PASS",
        )

        preflight_cmd = [
            sys.executable, str(RUNNER),
            "--descriptor", str(args.descriptor),
            "--model", str(args.model),
            "--port-w", str(args.port_w),
            "--port-c", str(args.port_c),
            "--preflight-only",
        ]
        pf = subprocess.run(preflight_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        (args.preflight_root / "measured-runner-preflight.stdout.json").write_bytes(pf.stdout)
        (args.preflight_root / "measured-runner-preflight.stderr.txt").write_bytes(pf.stderr)
        if pf.returncode != 0:
            raise RuntimeError(f"measured runner preflight failed rc={pf.returncode}")
        pf_obj = json.loads(pf.stdout)
        if pf_obj.get("classification") != "LAYER0_PROJECTION_PROVENANCE_MEASURED_PREFLIGHT_PASS":
            raise RuntimeError("unexpected measured preflight classification")
        if pf_obj.get("descriptor_sha256") != descriptor_sha:
            raise RuntimeError("measured preflight descriptor SHA mismatch")
    except Exception as exc:
        write_json(args.preflight_root / "terminal.json", {
            "attempt_id": ATTEMPT_ID,
            "primary_classification": "LAYER0_PROJECTION_PROVENANCE_PROBE_NOT_EXERCISED",
            "stage": "static_preflight",
            "reason": f"{type(exc).__name__}: {exc}",
            "measured_attempt_consumed": False,
            "rerun_authorized": False,
        })
        return 5

    measured_cmd = [
        sys.executable, str(RUNNER),
        "--descriptor", str(args.descriptor),
        "--model", str(args.model),
        "--out-root", str(args.out_root),
        "--port-w", str(args.port_w),
        "--port-c", str(args.port_c),
    ]
    write_json(args.preflight_root / "measured-child.argv.json", measured_cmd)

    guard_root = args.preflight_root / "resource-guard"
    guard_cmd = [
        sys.executable, str(RESOURCE_GUARD),
        "--evidence-root", str(guard_root), "--",
        *measured_cmd,
    ]
    cp = subprocess.run(guard_cmd, check=False)
    result = reconcile(args.out_root, cp.returncode)

    try:
        guard = json.loads((guard_root / "guard.json").read_text(encoding="utf-8"))
        quiescence = json.loads((guard_root / "external-quiescence.json").read_text(encoding="utf-8"))
    except Exception:
        guard = None
        quiescence = None

    result.update({
        "attempt_id": ATTEMPT_ID,
        "descriptor_sha256": descriptor_sha,
        "resource_guard": guard,
        "external_quiescence": quiescence,
        "campaign_queue_receipt_created": False,
        "campaign_queue_or_spend_artifact_touched": False,
    })
    write_json(args.preflight_root / "terminal.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))

    if result["measured_terminal_present"]:
        return cp.returncode
    return 6 if result["measured_attempt_consumed"] else 7

if __name__ == "__main__":
    raise SystemExit(main())

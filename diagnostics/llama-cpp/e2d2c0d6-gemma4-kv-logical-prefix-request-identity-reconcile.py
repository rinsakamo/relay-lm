#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import subprocess
import sys

STATUS_PASS = "LOGICAL_PREFIX_REQUEST_IDENTITY_RECONCILED"


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--search-root", action="append", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    args = ap.parse_args()

    if args.out_root.exists():
        raise SystemExit(f"output root must not exist: {args.out_root}")
    args.out_root.mkdir(parents=True)

    here = Path(__file__).resolve().parent
    locator = here / "e2d2c0d6-gemma4-kv-artifact-locator.py"
    admission = here / "e2d2c0d6-gemma4-kv-request-admission.py"

    locator_json = args.out_root / "artifact-locator.json"
    locator_cmd = [
        sys.executable,
        str(locator),
        *[str(p) for p in args.search_root],
        "--out",
        str(locator_json),
    ]
    write_json(args.out_root / "artifact-locator.argv.json", locator_cmd)
    located = subprocess.run(locator_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (args.out_root / "artifact-locator.stdout.txt").write_bytes(located.stdout)
    (args.out_root / "artifact-locator.stderr.txt").write_bytes(located.stderr)
    if located.returncode != 0:
        write_json(args.out_root / "terminal.json", {
            "status": "LOGICAL_PREFIX_REQUEST_IDENTITY_NOT_RECONCILED",
            "stage": "artifact_locator",
            "generated_requests": 0,
            "model_loads": 0,
            "server_startups": 0,
            "measured_l0_submitted": False,
        })
        return 2

    locator_obj = json.loads(locator_json.read_text(encoding="utf-8"))
    if locator_obj.get("status") != "ARTIFACT_LOCATOR_PASS":
        raise SystemExit("artifact locator returned non-PASS status")

    selected = locator_obj.get("selected")
    if not isinstance(selected, dict):
        raise SystemExit("artifact locator selected block missing")

    required = ("warm_tokens", "target_tokens", "L0", "L1", "LC")
    missing = [name for name in required if name not in selected]
    if missing:
        raise SystemExit(f"selected identities missing: {missing}")

    paths = {name: Path(selected[name]["path"]) for name in required}
    for name, path in paths.items():
        if not path.is_file():
            raise SystemExit(f"selected artifact missing: {name}: {path}")

    admission_json = args.out_root / "request-admission.json"
    admission_cmd = [
        sys.executable,
        str(admission),
        "--warm-tokens", str(paths["warm_tokens"]),
        "--target-tokens", str(paths["target_tokens"]),
        "--l0", str(paths["L0"]),
        "--l1", str(paths["L1"]),
        "--lc", str(paths["LC"]),
        "--out", str(admission_json),
    ]
    write_json(args.out_root / "request-admission.argv.json", admission_cmd)
    admitted = subprocess.run(admission_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (args.out_root / "request-admission.stdout.txt").write_bytes(admitted.stdout)
    (args.out_root / "request-admission.stderr.txt").write_bytes(admitted.stderr)
    if admitted.returncode != 0:
        write_json(args.out_root / "terminal.json", {
            "status": "LOGICAL_PREFIX_REQUEST_IDENTITY_NOT_RECONCILED",
            "stage": "request_admission",
            "generated_requests": 0,
            "model_loads": 0,
            "server_startups": 0,
            "measured_l0_submitted": False,
        })
        return 3

    admission_obj = json.loads(admission_json.read_text(encoding="utf-8"))
    if admission_obj.get("status") != "REQUEST_ADMISSION_PASS":
        raise SystemExit("request admission returned non-PASS status")

    identities = {
        name: {
            "path": str(paths[name]),
            "sha256": selected[name]["sha256"],
        }
        for name in required
    }

    out = {
        "status": STATUS_PASS,
        "identities": identities,
        "request_rule": {
            "L0R": "send the exact L0 request bytes again on the fresh WR2 server",
        },
        "generated_requests": 0,
        "model_loads": 0,
        "server_startups": 0,
        "measured_l0_submitted": False,
        "measured_attempt_consumed": False,
        "measured_execution_authorized_by_this_result": False,
    }
    write_json(args.out_root / "terminal.json", out)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

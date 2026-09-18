#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import subprocess
import sys


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        write_json(args.preflight_root / "terminal.json", {
            "primary_classification": "PROBE_NOT_EXERCISED",
            "measured_l0_submitted": False,
            "stage": "artifact_locator",
            "reason": "ARTIFACT_LOCATOR_FAIL",
        })
        raise SystemExit(2)

    obj = json.loads(locator_json.read_text(encoding="utf-8"))
    if obj.get("status") != "ARTIFACT_LOCATOR_PASS":
        write_json(args.preflight_root / "terminal.json", {
            "primary_classification": "PROBE_NOT_EXERCISED",
            "measured_l0_submitted": False,
            "stage": "artifact_locator",
            "reason": f"unexpected locator status: {obj.get('status')}",
        })
        raise SystemExit(3)

    selected = obj.get("selected")
    if not isinstance(selected, dict):
        raise SystemExit("locator selected block missing")

    required = ("warm_tokens", "target_tokens", "L0", "L1", "LC")
    missing = [name for name in required if name not in selected]
    if missing:
        write_json(args.preflight_root / "terminal.json", {
            "primary_classification": "PROBE_NOT_EXERCISED",
            "measured_l0_submitted": False,
            "stage": "artifact_locator",
            "reason": f"locator selected entries missing: {missing}",
        })
        raise SystemExit(4)

    paths = {}
    for name in required:
        entry = selected[name]
        path = Path(entry["path"])
        if not path.is_file():
            write_json(args.preflight_root / "terminal.json", {
                "primary_classification": "PROBE_NOT_EXERCISED",
                "measured_l0_submitted": False,
                "stage": "artifact_locator",
                "reason": f"selected artifact disappeared: {name}: {path}",
            })
            raise SystemExit(5)
        paths[name] = path

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
    run = subprocess.run(runner_cmd)
    write_json(args.preflight_root / "measured-runner.exit.json", {
        "returncode": run.returncode,
        "measured_output_root": str(args.out_root),
    })

    # The measured runner owns its own terminal.json and exactly-once semantics.
    raise SystemExit(run.returncode)


if __name__ == "__main__":
    main()

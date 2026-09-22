#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import subprocess
import sys

ATTEMPT_ID = "layer0-projection-origin-20260922-a5d767da"
EXPECTED_CLASSIFICATION = "LAYER0_PREPROJECTION_DIFFERENCE_OBSERVED"
HERE = Path(__file__).resolve().parent
ANALYZER = HERE / "e2d2c0d6-gemma4-layer0-preprojection-relation-posthoc.py"
ANALYZER_SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-preprojection-relation-posthoc-selftest.py"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_candidate(root: Path):
    terminal = root / "terminal.json"
    identity = root / "identity.json"
    projection = root / "projection"
    if not terminal.is_file() or not identity.is_file() or not projection.is_dir():
        return None
    try:
        t = load_json(terminal)
        i = load_json(identity)
    except Exception:
        return None
    if t.get("attempt_id") != ATTEMPT_ID:
        return None
    if t.get("primary_classification") != EXPECTED_CLASSIFICATION:
        return None
    if t.get("measured_attempt_consumed") is not True:
        return None
    if t.get("measured_w_submitted") is not True or t.get("measured_c_submitted") is not True:
        return None
    if t.get("request_count") != 2 or t.get("request_order") != ["W", "C"]:
        return None
    required = [
        projection / "W-p0-370-w371",
        projection / "W-p371-878-w508",
        projection / "C-p0-511-w512",
    ]
    if not all(p.is_dir() for p in required):
        return None
    return {"root": root, "terminal": t, "identity": i}


def find_unique(search_root: Path):
    matches = []
    for terminal in search_root.glob("**/terminal.json"):
        root = terminal.parent
        candidate = validate_candidate(root)
        if candidate is not None:
            matches.append(candidate)
    unique = {}
    for m in matches:
        unique[str(m["root"].resolve())] = m
    matches = list(unique.values())
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one measured root for {ATTEMPT_ID}, found {len(matches)}: "
            f"{sorted(str(m['root']) for m in matches)}"
        )
    return matches[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--search-root", type=Path, default=Path("/tmp"))
    ap.add_argument("--out-root", type=Path, required=True)
    args = ap.parse_args()

    if args.out_root.exists():
        raise RuntimeError(f"refusing to overwrite output root: {args.out_root}")
    if not ANALYZER.is_file() or not ANALYZER_SELFTEST.is_file():
        raise RuntimeError("required zero-GPU analyzer/selftest missing")

    args.out_root.mkdir(parents=True)
    selftest = subprocess.run(
        [sys.executable, str(ANALYZER_SELFTEST)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    (args.out_root / "selftest.stdout.json").write_bytes(selftest.stdout)
    (args.out_root / "selftest.stderr.txt").write_bytes(selftest.stderr)
    if selftest.returncode != 0:
        raise RuntimeError(f"relation analyzer selftest failed rc={selftest.returncode}")
    try:
        selftest_obj = json.loads(selftest.stdout)
    except Exception as exc:
        raise RuntimeError(f"invalid selftest JSON: {exc}") from exc
    if selftest_obj.get("status") != "LAYER0_PREPROJECTION_RELATION_POSTHOC_SELFTEST_PASS":
        raise RuntimeError(f"unexpected selftest status: {selftest_obj.get('status')}")

    measured = find_unique(args.search_root)
    relation_out = args.out_root / "relation.json"
    run = subprocess.run(
        [
            sys.executable,
            str(ANALYZER),
            "--projection-root",
            str(measured["root"] / "projection"),
            "--out",
            str(relation_out),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    (args.out_root / "relation.stdout.json").write_bytes(run.stdout)
    (args.out_root / "relation.stderr.txt").write_bytes(run.stderr)
    if run.returncode != 0 or not relation_out.is_file():
        raise RuntimeError(f"relation analyzer failed rc={run.returncode}")

    relation = load_json(relation_out)
    terminal = {
        "classification": "LAYER0_PREPROJECTION_RELATION_ZERO_GPU_COMPLETE",
        "attempt_id": ATTEMPT_ID,
        "measured_root": str(measured["root"].resolve()),
        "measured_primary_classification": measured["terminal"]["primary_classification"],
        "relation_classification": relation.get("classification"),
        "physical_calls": 0,
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
        "measured_requests": 0,
    }
    (args.out_root / "terminal.json").write_text(
        json.dumps(terminal, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(terminal, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

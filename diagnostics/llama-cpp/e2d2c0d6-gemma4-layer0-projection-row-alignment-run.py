#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import subprocess
import sys

ATTEMPT_ID = "layer0-projection-origin-20260922-a5d767da"
EXPECTED_CLASSIFICATION = "LAYER0_PREPROJECTION_DIFFERENCE_OBSERVED"

HERE = Path(__file__).resolve().parent
ANALYZER = HERE / "e2d2c0d6-gemma4-layer0-projection-row-alignment-posthoc.py"
ANALYZER_SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-projection-row-alignment-posthoc-selftest.py"


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

    return {
        "root": root,
        "terminal": t,
        "identity": i,
    }


def find_unique(search_root: Path):
    matches = {}
    for terminal in search_root.glob("**/terminal.json"):
        candidate = validate_candidate(terminal.parent)
        if candidate is not None:
            matches[str(candidate["root"].resolve())] = candidate
    values = list(matches.values())
    if len(values) != 1:
        raise RuntimeError(
            f"expected exactly one measured root for {ATTEMPT_ID}, found {len(values)}: "
            f"{sorted(matches)}"
        )
    return values[0]


def classify(result):
    # This classifier is deliberately conservative. It only decides whether
    # Segment-B warm rows correlate more strongly with cold rows by logical
    # position or by local ubatch column.
    decisions = {}
    for name, tensor in result["tensors"].items():
        logical = tensor["segment_B_same_logical"]["mean"]
        local = tensor["segment_B_same_local_column"]["mean"]
        local_wins = tensor["segment_B_local_beats_logical_rows"]
        logical_wins = tensor["segment_B_logical_beats_local_rows"]

        if local > logical and local_wins > logical_wins:
            decision = "LOCAL_COLUMN_CORRESPONDENCE_STRONGER"
        elif logical > local and logical_wins > local_wins:
            decision = "LOGICAL_POSITION_CORRESPONDENCE_STRONGER"
        else:
            decision = "CORRESPONDENCE_AMBIGUOUS"

        decisions[name] = {
            "decision": decision,
            "segment_B_mean_cosine_same_logical": logical,
            "segment_B_mean_cosine_same_local_column": local,
            "local_beats_logical_rows": local_wins,
            "logical_beats_local_rows": logical_wins,
        }

    ds = {v["decision"] for v in decisions.values()}
    if ds == {"LOCAL_COLUMN_CORRESPONDENCE_STRONGER"}:
        primary = "ROW_ALIGNMENT_LOCAL_COLUMN_CORRESPONDENCE_SUPPORTED"
    elif ds == {"LOGICAL_POSITION_CORRESPONDENCE_STRONGER"}:
        primary = "ROW_ALIGNMENT_LOGICAL_POSITION_CORRESPONDENCE_SUPPORTED"
    else:
        primary = "ROW_ALIGNMENT_CORRESPONDENCE_MIXED_OR_AMBIGUOUS"

    return primary, decisions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--search-root", type=Path, default=Path("/tmp"))
    ap.add_argument("--out-root", type=Path, required=True)
    args = ap.parse_args()

    if args.out_root.exists():
        raise RuntimeError(f"refusing to overwrite output root: {args.out_root}")
    if not ANALYZER.is_file() or not ANALYZER_SELFTEST.is_file():
        raise RuntimeError("required row-alignment analyzer/selftest missing")

    args.out_root.mkdir(parents=True)

    st = subprocess.run(
        [sys.executable, str(ANALYZER_SELFTEST)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    (args.out_root / "selftest.stdout.json").write_bytes(st.stdout)
    (args.out_root / "selftest.stderr.txt").write_bytes(st.stderr)
    if st.returncode != 0:
        raise RuntimeError(f"row-alignment selftest failed rc={st.returncode}")
    st_obj = json.loads(st.stdout)
    if st_obj.get("status") != "LAYER0_PROJECTION_ROW_ALIGNMENT_POSTHOC_SELFTEST_PASS":
        raise RuntimeError(f"unexpected selftest status: {st_obj.get('status')}")

    measured = find_unique(args.search_root)
    analysis_out = args.out_root / "row-alignment.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ANALYZER),
            "--projection-root",
            str(measured["root"] / "projection"),
            "--out",
            str(analysis_out),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    (args.out_root / "row-alignment.stdout.json").write_bytes(cp.stdout)
    (args.out_root / "row-alignment.stderr.txt").write_bytes(cp.stderr)
    if cp.returncode != 0 or not analysis_out.is_file():
        raise RuntimeError(f"row-alignment analyzer failed rc={cp.returncode}")

    result = load_json(analysis_out)
    if result.get("classification") != "LAYER0_PROJECTION_ROW_ALIGNMENT_POSTHOC_COMPLETE":
        raise RuntimeError(f"unexpected analyzer classification: {result.get('classification')}")

    classification, decisions = classify(result)
    terminal = {
        "classification": "LAYER0_PROJECTION_ROW_ALIGNMENT_ZERO_GPU_COMPLETE",
        "scientific_classification": classification,
        "tensor_decisions": decisions,
        "attempt_id": ATTEMPT_ID,
        "measured_root": str(measured["root"].resolve()),
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

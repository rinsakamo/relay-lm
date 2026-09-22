#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-layer0-projection-row-alignment-run.py"

def load():
    spec = importlib.util.spec_from_file_location("row_align_run", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load row-alignment runner")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def make_candidate(root: Path, attempt_id: str, classification: str):
    root.mkdir(parents=True)
    terminal = {
        "attempt_id": attempt_id,
        "primary_classification": classification,
        "measured_attempt_consumed": True,
        "measured_w_submitted": True,
        "measured_c_submitted": True,
        "request_count": 2,
        "request_order": ["W", "C"],
    }
    (root / "terminal.json").write_text(json.dumps(terminal) + "\n", encoding="utf-8")
    (root / "identity.json").write_text("{}\n", encoding="utf-8")
    p = root / "projection"
    for name in ("W-p0-370-w371", "W-p371-878-w508", "C-p0-511-w512"):
        (p / name).mkdir(parents=True)

def tensor(logical, cold_local, prev_warm, exact=0):
    return {
        "segment_B_same_logical": {"mean": logical},
        "segment_B_same_cold_local_column": {"mean": cold_local},
        "segment_B_same_previous_warm_local_column": {"mean": prev_warm},
        "segment_B_exact_equal_previous_warm_rows": exact,
    }

def main():
    m = load()

    previous = {"tensors": {
        name: tensor(0.2, 0.4, 0.95, 3)
        for name in ("attn_norm-0", "Kcur-0", "Vcur-0")
    }}
    cls, _ = m.classify(previous)
    if cls != "ROW_ALIGNMENT_PREVIOUS_WARM_LOCAL_COLUMN_SUPPORTED":
        raise RuntimeError("previous-warm classifier mismatch")

    cold_local = {"tensors": {
        name: tensor(0.2, 0.95, 0.4)
        for name in ("attn_norm-0", "Kcur-0", "Vcur-0")
    }}
    cls, _ = m.classify(cold_local)
    if cls != "ROW_ALIGNMENT_COLD_LOCAL_COLUMN_SUPPORTED":
        raise RuntimeError("cold-local classifier mismatch")

    logical = {"tensors": {
        name: tensor(0.95, 0.2, 0.4)
        for name in ("attn_norm-0", "Kcur-0", "Vcur-0")
    }}
    cls, _ = m.classify(logical)
    if cls != "ROW_ALIGNMENT_LOGICAL_POSITION_SUPPORTED":
        raise RuntimeError("logical-position classifier mismatch")

    mixed = {"tensors": {
        "attn_norm-0": tensor(0.95, 0.2, 0.4),
        "Kcur-0": tensor(0.2, 0.95, 0.4),
        "Vcur-0": tensor(0.2, 0.4, 0.95),
    }}
    cls, _ = m.classify(mixed)
    if cls != "ROW_ALIGNMENT_CORRESPONDENCE_MIXED_OR_AMBIGUOUS":
        raise RuntimeError("mixed classifier mismatch")

    with tempfile.TemporaryDirectory(prefix="relaylm-row-align-run-selftest-") as td:
        base = Path(td)
        good = base / "one" / "output"
        make_candidate(good, m.ATTEMPT_ID, m.EXPECTED_CLASSIFICATION)
        found = m.find_unique(base)
        if found["root"].resolve() != good.resolve():
            raise RuntimeError("unique measured candidate not selected")

        duplicate = base / "two" / "output"
        make_candidate(duplicate, m.ATTEMPT_ID, m.EXPECTED_CLASSIFICATION)
        rejected = False
        try:
            m.find_unique(base)
        except RuntimeError:
            rejected = True
        if not rejected:
            raise RuntimeError("duplicate measured candidates were not rejected")

    print(json.dumps({
        "status": "LAYER0_PROJECTION_ROW_ALIGNMENT_RUN_SELFTEST_PASS",
        "physical_calls": 0,
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

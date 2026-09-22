#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-layer0-preprojection-relation-run.py"

def load():
    spec = importlib.util.spec_from_file_location("relation_run", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load relation runner")
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

def main():
    m = load()
    with tempfile.TemporaryDirectory(prefix="relaylm-preproj-rel-run-selftest-") as td:
        base = Path(td)
        good = base / "one" / "output"
        make_candidate(good, m.ATTEMPT_ID, m.EXPECTED_CLASSIFICATION)

        found = m.find_unique(base)
        if found["root"].resolve() != good.resolve():
            raise RuntimeError("unique candidate not selected")

        ignored = base / "ignored" / "output"
        make_candidate(ignored, "different-attempt", m.EXPECTED_CLASSIFICATION)
        found = m.find_unique(base)
        if found["root"].resolve() != good.resolve():
            raise RuntimeError("different attempt should be ignored")

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
        "status": "LAYER0_PREPROJECTION_RELATION_RUN_SELFTEST_PASS",
        "physical_calls": 0,
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

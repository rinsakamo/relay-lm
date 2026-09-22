#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-layer0-projection-origin-execute-once.py"


def load_module():
    spec = importlib.util.spec_from_file_location("projection_origin_wrapper", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load wrapper")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    m = load_module()
    with tempfile.TemporaryDirectory(prefix="relaylm-projection-wrapper-selftest-") as td:
        root = Path(td)

        absent = root / "absent"
        a = m.reconcile(absent, 9)
        if a["primary_classification"] != "LAYER0_PROJECTION_ORIGIN_PROBE_NOT_EXERCISED":
            raise RuntimeError("absent W record must be unexercised")
        if a["measured_attempt_consumed"] is not False:
            raise RuntimeError("unexercised case incorrectly consumed")

        partial = root / "partial"
        (partial / "server-W").mkdir(parents=True)
        (partial / "server-W" / "W.request.json").write_text("{}\n", encoding="utf-8")
        b = m.reconcile(partial, 8)
        if b["primary_classification"] != "LAYER0_PROJECTION_ORIGIN_PROBE_EXERCISED_INCOMPLETE":
            raise RuntimeError("W record must conservatively consume attempt")
        if b["measured_attempt_consumed"] is not True or b["rerun_authorized"] is not False:
            raise RuntimeError("consumed incomplete case has wrong flags")

        complete = root / "complete"
        complete.mkdir()
        terminal = {
            "primary_classification": "LAYER0_PROJECTION_NUMERICAL_ORIGIN_OBSERVED",
            "measured_attempt_consumed": True,
        }
        (complete / "terminal.json").write_text(
            json.dumps(terminal) + "\n", encoding="utf-8"
        )
        c = m.reconcile(complete, 0)
        if c["primary_classification"] != terminal["primary_classification"]:
            raise RuntimeError("complete terminal classification not preserved")
        if c["measured_terminal_present"] is not True:
            raise RuntimeError("complete terminal not detected")

    print(json.dumps({
        "status": "LAYER0_PROJECTION_ORIGIN_EXECUTE_ONCE_SELFTEST_PASS",
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

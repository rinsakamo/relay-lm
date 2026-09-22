#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-layer0-projection-row-alignment-posthoc.py"

def load():
    spec = importlib.util.spec_from_file_location("row_align", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load row-alignment analyzer")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def pack(xs):
    return struct.pack("<" + "f"*len(xs), *xs)

def main():
    m = load()
    a = pack([1.0, 2.0, 3.0, 4.0])
    b = pack([2.0, 4.0, 6.0, 8.0])
    c = pack([1.0, -2.0, 3.0, -4.0])
    if abs(m.cosine(a, b) - 1.0) > 1e-12:
        raise RuntimeError("positive scalar cosine mismatch")
    if m.cosine(a, c) >= 1.0:
        raise RuntimeError("non-collinear cosine not distinguished")
    s = m.summarize([0.25, 0.5, 0.75])
    if s != {"min":0.25,"max":0.75,"mean":0.5,"count":3}:
        raise RuntimeError("summary mismatch")
    print(json.dumps({
        "status":"LAYER0_PROJECTION_ROW_ALIGNMENT_POSTHOC_SELFTEST_PASS",
        "physical_calls":0,
        "gpu_calls":0,
        "model_loads":0,
        "generation_requests":0
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

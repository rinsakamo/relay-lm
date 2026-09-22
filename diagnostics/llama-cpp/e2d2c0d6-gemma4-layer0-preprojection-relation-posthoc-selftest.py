#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-layer0-preprojection-relation-posthoc.py"

def load():
    spec = importlib.util.spec_from_file_location("preproj_rel", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load analyzer")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def pack(xs):
    return struct.pack("<" + "f"*len(xs), *xs)

def main():
    m = load()
    a = pack([2.0, -4.0, 6.0, -8.0])
    b = pack([1.0, -2.0, 3.0, -4.0])
    r = m.row_relation(a,b)
    if abs(r["alpha_C_to_W"] - 2.0) > 1e-12:
        raise RuntimeError("scalar fit alpha mismatch")
    if r["relative_residual_after_scalar_fit"] > 1e-12:
        raise RuntimeError("pure scalar relation should have zero residual")
    if abs(r["cosine"] - 1.0) > 1e-12:
        raise RuntimeError("pure positive scalar relation should be collinear")
    print(json.dumps({
        "status":"LAYER0_PREPROJECTION_RELATION_POSTHOC_SELFTEST_PASS",
        "physical_calls":0,
        "generation_requests":0
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

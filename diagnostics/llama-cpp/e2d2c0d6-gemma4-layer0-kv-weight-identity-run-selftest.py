#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-layer0-kv-weight-identity-run.py"

def load():
    spec = importlib.util.spec_from_file_location("kv_weight_run", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load K/V weight runner")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    m = load()
    distinct = {
        "same_payload_sha256": False,
        "dequantized": {"bit_exact_equal": False},
    }
    if m.classify(distinct) != "LAYER0_KV_WEIGHTS_DISTINCT":
        raise RuntimeError("distinct classifier mismatch")

    identical = {
        "same_payload_sha256": True,
        "dequantized": {"bit_exact_equal": True},
    }
    if m.classify(identical) != "LAYER0_KV_WEIGHTS_IDENTICAL":
        raise RuntimeError("identical classifier mismatch")

    mixed = {
        "same_payload_sha256": False,
        "dequantized": {"bit_exact_equal": True},
    }
    if m.classify(mixed) != "LAYER0_KV_WEIGHT_IDENTITY_MIXED_OR_AMBIGUOUS":
        raise RuntimeError("mixed classifier mismatch")

    print(json.dumps({
        "status": "LAYER0_KV_WEIGHT_IDENTITY_RUN_SELFTEST_PASS",
        "physical_calls": 0,
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

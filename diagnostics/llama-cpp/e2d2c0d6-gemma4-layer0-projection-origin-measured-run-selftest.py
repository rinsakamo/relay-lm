#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-layer0-projection-origin-measured-run.py"


def load_module():
    spec = importlib.util.spec_from_file_location("projection_origin_runner", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load measured runner")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    m = load_module()
    checks = []

    l0 = m.FIXTURE / "L0.request.json"
    lc = m.FIXTURE / "LC.request.json"
    m.validate_request(l0, m.EXPECTED_L0_SHA, 883, True)
    m.validate_request(lc, m.EXPECTED_LC_SHA, 2927, False)
    checks.append("committed_request_identity")

    dummy = m.Server(
        binary=Path("/x/llama-server"),
        model=Path("/x/model.gguf"),
        port=34567,
        label="W",
        kv_root=Path("/x/kv"),
        projection_root=Path("/x/projection"),
        out=Path("/x/out"),
    )
    cmd = dummy.command()
    required = [
        "--ctx-size", "8192",
        "--parallel", "1",
        "--gpu-layers", "999",
        "--no-context-shift",
        "--batch-size", "512",
        "--ubatch-size", "512",
        "--flash-attn", "on",
    ]
    joined = "\0".join(cmd)
    for item in required:
        if item not in cmd:
            raise RuntimeError(f"runtime argument missing: {item}")
    if "--flash-attn\0off" in joined:
        raise RuntimeError("FA-OFF unexpectedly present")
    checks.append("runtime_shape")

    source = TARGET.read_text(encoding="utf-8")
    if source.count('send_request(W, "W"') != 1:
        raise RuntimeError("runner must contain exactly one W send site")
    if source.count('send_request(C, "C"') != 1:
        raise RuntimeError("runner must contain exactly one C send site")
    for forbidden in ('send_request(W, "L1"', 'WR2', '"L0R"'):
        if forbidden in source:
            raise RuntimeError(f"forbidden historical request path present: {forbidden}")
    checks.append("exact_two_request_surface")

    if m.EXPECTED_W_HISTORICAL_DIGEST == m.EXPECTED_C_HISTORICAL_DIGEST:
        raise RuntimeError("historical W/C identities unexpectedly equal")
    checks.append("historical_digest_pins")

    print(json.dumps({
        "status": "LAYER0_PROJECTION_ORIGIN_MEASURED_RUNNER_SELFTEST_PASS",
        "checks": checks,
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

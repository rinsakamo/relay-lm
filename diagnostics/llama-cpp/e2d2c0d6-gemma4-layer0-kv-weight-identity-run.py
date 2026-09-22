#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
AUDIT = HERE / "e2d2c0d6-gemma4-layer0-kv-weight-identity-audit.py"
SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-kv-weight-identity-audit-selftest.py"

def run_json(cmd, out, err, expected_key=None, expected_value=None):
    cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    out.write_bytes(cp.stdout)
    err.write_bytes(cp.stderr)
    if cp.returncode != 0:
        raise RuntimeError(f"command failed rc={cp.returncode}: {cmd}")
    obj = json.loads(cp.stdout)
    if expected_key is not None and obj.get(expected_key) != expected_value:
        raise RuntimeError(f"unexpected {expected_key}: {obj.get(expected_key)!r}")
    return obj

def classify(audit):
    raw_equal = bool(audit["same_payload_sha256"])
    dq_equal = bool(audit["dequantized"]["bit_exact_equal"])
    if raw_equal and dq_equal:
        return "LAYER0_KV_WEIGHTS_IDENTICAL"
    if not raw_equal and not dq_equal:
        return "LAYER0_KV_WEIGHTS_DISTINCT"
    return "LAYER0_KV_WEIGHT_IDENTITY_MIXED_OR_AMBIGUOUS"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--llama-source", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    args = ap.parse_args()

    if args.out_root.exists():
        raise RuntimeError(f"refusing to overwrite output root: {args.out_root}")
    args.out_root.mkdir(parents=True)

    gguf_py = args.llama_source / "gguf-py"
    if not gguf_py.is_dir():
        raise RuntimeError(f"gguf-py not found under llama source: {gguf_py}")
    if not AUDIT.is_file() or not SELFTEST.is_file():
        raise RuntimeError("required audit/selftest missing")

    st = run_json(
        [sys.executable, str(SELFTEST)],
        args.out_root / "selftest.stdout.json",
        args.out_root / "selftest.stderr.txt",
        "status",
        "GEMMA4_LAYER0_KV_WEIGHT_IDENTITY_AUDIT_SELFTEST_PASS",
    )

    audit_out = args.out_root / "kv-weight-identity.json"
    audit = run_json(
        [
            sys.executable, str(AUDIT),
            "--model", str(args.model),
            "--gguf-py-root", str(gguf_py),
            "--out", str(audit_out),
        ],
        args.out_root / "audit.stdout.json",
        args.out_root / "audit.stderr.txt",
        "classification",
        "GEMMA4_LAYER0_KV_WEIGHT_IDENTITY_AUDIT_COMPLETE",
    )

    scientific = classify(audit)
    terminal = {
        "classification": "LAYER0_KV_WEIGHT_IDENTITY_ZERO_GPU_COMPLETE",
        "scientific_classification": scientific,
        "model_sha256": audit["model_sha256"],
        "K": audit["K"],
        "V": audit["V"],
        "same_type": audit["same_type"],
        "same_shape": audit["same_shape"],
        "same_payload_sha256": audit["same_payload_sha256"],
        "dequantized": audit["dequantized"],
        "physical_calls": 0,
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
        "measured_requests": 0,
    }
    (args.out_root / "terminal.json").write_text(
        json.dumps(terminal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(terminal, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

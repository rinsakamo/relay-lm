#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-kv-fixture-v2-segmentation-control-materialize.py"


def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def main():
    errors = []
    with tempfile.TemporaryDirectory(prefix="relaylm-kv-seg-control-selftest.") as td:
        out = Path(td) / "control"
        run = subprocess.run(
            [sys.executable, str(TARGET), "--out-dir", str(out)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if run.returncode != 0:
            errors.append(f"materializer failed: rc={run.returncode}")
        else:
            obj = json.loads(run.stdout)
            if obj.get("status") != "LOGICAL_PREFIX_SEGMENTATION_CONTROL_MATERIALIZED":
                errors.append("materializer terminal mismatch")

            warm = json.loads((HERE / "fixtures/e2d2c0d6-gemma4-kv-v2/warm.tokens.json").read_text(encoding="utf-8"))
            control = json.loads((out / "C883.tokens.json").read_text(encoding="utf-8"))
            req = json.loads((out / "C883.request.json").read_text(encoding="utf-8"))
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))

            if len(control) != 883:
                errors.append("control length != 883")
            if lcp(warm, control) != 865:
                errors.append("warm/control LCP != 865")
            if control == warm:
                errors.append("control unexpectedly equals warm")
            if req.get("prompt") != control:
                errors.append("request prompt != control")
            if req.get("cache_prompt") is not False:
                errors.append("control cache_prompt must be false")
            if req.get("n_predict") != 1 or req.get("temperature") != 0:
                errors.append("generation contract mismatch")
            if req.get("stream") is not False or req.get("n_probs") != 20:
                errors.append("stream/n_probs contract mismatch")

            seg = manifest.get("expected_prompt_segmentation", {})
            expected = {
                "n_batch": 512,
                "n_ubatch": 512,
                "total_tokens": 883,
                "first_decode_tokens": 371,
                "second_decode_tokens": 508,
                "final_decode_tokens": 4,
                "logical_position_511_decode_ordinal": 2,
            }
            if seg != expected:
                errors.append(f"segmentation contract mismatch: {seg}")

    out_obj = {
        "status": (
            "LOGICAL_PREFIX_SEGMENTATION_CONTROL_SELFTEST_PASS"
            if not errors
            else "LOGICAL_PREFIX_SEGMENTATION_CONTROL_SELFTEST_FAIL"
        ),
        "errors": errors,
    }
    print(json.dumps(out_obj, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

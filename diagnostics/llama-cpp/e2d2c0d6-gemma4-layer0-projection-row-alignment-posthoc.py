#!/usr/bin/env python3
import argparse
import importlib.util
import json
import math
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
BASE = HERE / "e2d2c0d6-gemma4-layer0-projection-origin-posthoc.py"

def load_base():
    spec = importlib.util.spec_from_file_location("projection_posthoc", BASE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load base posthoc")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def f32s(raw):
    return struct.unpack("<" + "f" * (len(raw)//4), raw)

def cosine(a_raw, b_raw):
    a = f32s(a_raw)
    b = f32s(b_raw)
    if len(a) != len(b):
        raise RuntimeError("row width mismatch")
    aa = bb = ab = 0.0
    for x, y in zip(a, b):
        xf = float(x); yf = float(y)
        aa += xf*xf; bb += yf*yf; ab += xf*yf
    if aa == 0.0 or bb == 0.0:
        raise RuntimeError("zero-norm row")
    return ab / math.sqrt(aa*bb)

def summarize(vals):
    return {
        "min": min(vals),
        "max": max(vals),
        "mean": sum(vals)/len(vals),
        "count": len(vals),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projection-root", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    if args.out is not None and args.out.exists():
        raise RuntimeError(f"refusing to overwrite: {args.out}")

    m = load_base()
    wa = m.load_projection_dump(args.projection_root / "W-p0-370-w371")
    wb = m.load_projection_dump(args.projection_root / "W-p371-878-w508")
    c  = m.load_projection_dump(args.projection_root / "C-p0-511-w512")

    result = {
        "classification": "LAYER0_PROJECTION_ROW_ALIGNMENT_POSTHOC_COMPLETE",
        "physical_calls": 0,
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
        "tensors": {},
        "cross_tensor_payload_identity": {},
    }

    # Check whether Kcur/Vcur payloads are accidentally identical within each dump.
    for dump_name, dump in (("W_A", wa), ("W_B", wb), ("C", c)):
        k = dump["tensors"]["Kcur-0"]
        v = dump["tensors"]["Vcur-0"]
        result["cross_tensor_payload_identity"][dump_name] = {
            "Kcur_sha256": k["sha256"],
            "Vcur_sha256": v["sha256"],
            "Kcur_equals_Vcur": k["sha256"] == v["sha256"],
            "Kcur_ne0": k["ne0"],
            "Vcur_ne0": v["ne0"],
        }

    for name in m.EXPECTED_TENSORS:
        # Segment A is both local-column and logical-position aligned.
        a_cos = []
        for pos in range(371):
            a_cos.append(cosine(
                wa["tensors"][name]["rows"][pos],
                c["tensors"][name]["rows"][pos],
            ))

        # Segment B: W local column i corresponds to logical position 371+i.
        logical_cos = []
        cold_local_cos = []
        prev_warm_local_cos = []
        logical_beats_cold_local = 0
        cold_local_beats_logical = 0
        prev_warm_beats_logical = 0
        logical_beats_prev_warm = 0
        exact_prev_warm_rows = 0
        rows = []
        for i in range(141):
            logical_pos = 371 + i
            wrow = wb["tensors"][name]["rows"][logical_pos]
            c_logical = c["tensors"][name]["rows"][logical_pos]
            c_local = c["tensors"][name]["rows"][i]
            wa_local = wa["tensors"][name]["rows"][i]
            cl = cosine(wrow, c_logical)
            cc = cosine(wrow, c_local)
            cw = cosine(wrow, wa_local)
            logical_cos.append(cl)
            cold_local_cos.append(cc)
            prev_warm_local_cos.append(cw)
            if cl > cc:
                logical_beats_cold_local += 1
            elif cc > cl:
                cold_local_beats_logical += 1
            if cl > cw:
                logical_beats_prev_warm += 1
            elif cw > cl:
                prev_warm_beats_logical += 1
            if wrow == wa_local:
                exact_prev_warm_rows += 1
            rows.append({
                "warm_local_column": i,
                "warm_logical_position": logical_pos,
                "cosine_vs_cold_same_logical": cl,
                "cosine_vs_cold_same_local_column": cc,
                "cosine_vs_previous_warm_same_local_column": cw,
                "delta_cold_local_minus_logical": cc - cl,
                "delta_previous_warm_minus_logical": cw - cl,
                "exact_equal_previous_warm_same_local_column": wrow == wa_local,
            })

        result["tensors"][name] = {
            "segment_A_same_local_and_logical": summarize(a_cos),
            "segment_B_same_logical": summarize(logical_cos),
            "segment_B_same_cold_local_column": summarize(cold_local_cos),
            "segment_B_same_previous_warm_local_column": summarize(prev_warm_local_cos),
            "segment_B_cold_local_beats_logical_rows": cold_local_beats_logical,
            "segment_B_logical_beats_cold_local_rows": logical_beats_cold_local,
            "segment_B_previous_warm_beats_logical_rows": prev_warm_beats_logical,
            "segment_B_logical_beats_previous_warm_rows": logical_beats_prev_warm,
            "segment_B_exact_equal_previous_warm_rows": exact_prev_warm_rows,
            "segment_B_rows": rows,
        }

    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

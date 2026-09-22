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

def f32s(raw: bytes):
    if len(raw) % 4:
        raise RuntimeError("non-f32 row length")
    return struct.unpack("<" + "f" * (len(raw)//4), raw)

def row_relation(a_raw: bytes, b_raw: bytes):
    a = f32s(a_raw)
    b = f32s(b_raw)
    if len(a) != len(b):
        raise RuntimeError("row length mismatch")
    aa = sum(float(x)*float(x) for x in a)
    bb = sum(float(x)*float(x) for x in b)
    ab = sum(float(x)*float(y) for x,y in zip(a,b))
    if aa == 0.0 or bb == 0.0:
        raise RuntimeError("zero norm row")
    alpha_b_to_a = ab / bb
    residual_sq = sum((float(x) - alpha_b_to_a*float(y))**2 for x,y in zip(a,b))
    cosine = ab / math.sqrt(aa*bb)
    rel_resid = math.sqrt(residual_sq / aa)
    same_sign = 0
    nonzero_pairs = 0
    max_abs = 0.0
    for x,y in zip(a,b):
        max_abs = max(max_abs, abs(float(x)-float(y)))
        if x != 0.0 and y != 0.0:
            nonzero_pairs += 1
            if (x > 0) == (y > 0):
                same_sign += 1
    return {
        "alpha_C_to_W": alpha_b_to_a,
        "cosine": cosine,
        "relative_residual_after_scalar_fit": rel_resid,
        "same_sign_fraction_nonzero": same_sign/nonzero_pairs if nonzero_pairs else 1.0,
        "max_absolute_difference": max_abs,
    }

def summarize(rows):
    keys = ("alpha_C_to_W","cosine","relative_residual_after_scalar_fit","same_sign_fraction_nonzero","max_absolute_difference")
    out = {}
    for key in keys:
        vals = [r[key] for r in rows]
        out[key] = {
            "min": min(vals),
            "max": max(vals),
            "mean": sum(vals)/len(vals),
        }
    out["rows"] = len(rows)
    out["near_pure_scalar_rows_rel_resid_le_1e-6"] = sum(
        r["relative_residual_after_scalar_fit"] <= 1e-6 for r in rows
    )
    out["near_collinear_rows_cos_ge_0_999999"] = sum(r["cosine"] >= 0.999999 for r in rows)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projection-root", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    if args.out is not None and args.out.exists():
        raise RuntimeError(f"refusing to overwrite: {args.out}")

    m = load_base()
    warm_dumps = [m.load_projection_dump(args.projection_root / name) for name in m.W_DUMPS]
    cold_dump = m.load_projection_dump(args.projection_root / m.C_DUMP)
    positions = list(range(512))
    warm, geometry = m.merge_projection_rows(warm_dumps, positions)

    result = {
        "classification": "LAYER0_PREPROJECTION_RELATION_POSTHOC_COMPLETE",
        "tensors": {},
        "cross_tensor_scale_consistency": {},
        "physical_calls": 0,
        "generation_requests": 0,
    }
    per_tensor_rows = {}
    for name in m.EXPECTED_TENSORS:
        crows = cold_dump["tensors"][name]["rows"]
        rows = []
        for pos in positions:
            rel = row_relation(warm[name][pos], crows[pos])
            rel["position"] = pos
            rows.append(rel)
        per_tensor_rows[name] = rows
        result["tensors"][name] = {
            "summary": summarize(rows),
            "segment_A_0_370": summarize(rows[:371]),
            "segment_B_371_511": summarize(rows[371:]),
            "rows": rows,
        }

    # Projection is linear before K/V normalization. If the attn_norm W/C difference
    # is predominantly a row-wise scalar factor, Kcur/Vcur should carry approximately
    # the same factor for each logical row.
    for name in ("Kcur-0","Vcur-0"):
        deltas = []
        for pos in positions:
            a = per_tensor_rows["attn_norm-0"][pos]["alpha_C_to_W"]
            b = per_tensor_rows[name][pos]["alpha_C_to_W"]
            deltas.append(abs(a-b))
        result["cross_tensor_scale_consistency"][name] = {
            "max_abs_alpha_delta_vs_attn_norm": max(deltas),
            "mean_abs_alpha_delta_vs_attn_norm": sum(deltas)/len(deltas),
        }

    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

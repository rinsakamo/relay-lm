#!/usr/bin/env python3
import argparse
import importlib.util
import json
import math
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
BASE = HERE / "e2d2c0d6-gemma4-layer0-projection-origin-posthoc.py"
FIXTURE = HERE / "fixtures" / "e2d2c0d6-gemma4-kv-v2" / "L0.request.json"

def load_base():
    spec = importlib.util.spec_from_file_location("projection_posthoc", BASE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load base posthoc")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def f32s(raw):
    return struct.unpack("<" + "f"*(len(raw)//4), raw)

def cosine(a_raw,b_raw):
    a=f32s(a_raw); b=f32s(b_raw)
    aa=bb=ab=0.0
    for x,y in zip(a,b):
        xf=float(x); yf=float(y)
        aa+=xf*xf; bb+=yf*yf; ab+=xf*yf
    if aa == 0.0 or bb == 0.0:
        raise RuntimeError("zero norm row")
    return ab/math.sqrt(aa*bb)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--projection-root",type=Path,required=True)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if args.out is not None and args.out.exists():
        raise RuntimeError(f"refusing to overwrite: {args.out}")

    m=load_base()
    wb=m.load_projection_dump(args.projection_root/"W-p371-878-w508")
    c=m.load_projection_dump(args.projection_root/"C-p0-511-w512")
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    tokens=fixture["prompt"]
    if len(tokens) != 883:
        raise RuntimeError("unexpected L0 fixture length")

    result={
        "classification":"LAYER0_LOCAL_COLUMN_NEAREST_ROW_POSTHOC_COMPLETE",
        "physical_calls":0,"gpu_calls":0,"model_loads":0,"generation_requests":0,
        "token_control":{
            "rows":141,
            "local_i_token_equals_logical_371_plus_i":sum(tokens[i]==tokens[371+i] for i in range(141)),
        },
        "tensors":{},
    }

    for name in m.EXPECTED_TENSORS:
        crows=c["tensors"][name]["rows"]
        rows=[]
        best_local=0
        best_logical=0
        best_token_match_local=0
        best_token_matches_target=0
        local_beats_logical_distinct_token=0
        distinct_token_rows=0
        best_local_distinct_token=0
        best_logical_distinct_token=0
        best_token_match_local_distinct_token=0
        best_token_match_target_distinct_token=0

        for i in range(141):
            logical=371+i
            wrow=wb["tensors"][name]["rows"][logical]
            sims=[cosine(wrow,crows[j]) for j in range(512)]
            best=max(range(512),key=lambda j:sims[j])
            local_sim=sims[i]
            logical_sim=sims[logical]
            if best==i: best_local+=1
            if best==logical: best_logical+=1
            if tokens[best]==tokens[i]: best_token_match_local+=1
            if tokens[best]==tokens[logical]: best_token_matches_target+=1
            distinct=tokens[i]!=tokens[logical]
            if distinct:
                distinct_token_rows+=1
                if local_sim>logical_sim:
                    local_beats_logical_distinct_token+=1
                if best==i:
                    best_local_distinct_token+=1
                if best==logical:
                    best_logical_distinct_token+=1
                if tokens[best]==tokens[i]:
                    best_token_match_local_distinct_token+=1
                if tokens[best]==tokens[logical]:
                    best_token_match_target_distinct_token+=1
            rows.append({
                "local_column":i,
                "warm_logical_position":logical,
                "warm_token":tokens[logical],
                "cold_local_token":tokens[i],
                "tokens_equal":tokens[i]==tokens[logical],
                "best_cold_row":best,
                "best_cold_token":tokens[best],
                "best_cosine":sims[best],
                "same_local_cosine":local_sim,
                "same_logical_cosine":logical_sim,
                "best_is_local":best==i,
                "best_is_logical":best==logical,
                "best_token_matches_local_token":tokens[best]==tokens[i],
                "best_token_matches_warm_logical_token":tokens[best]==tokens[logical],
            })

        result["tensors"][name]={
            "best_row_is_same_local_column":best_local,
            "best_row_is_same_logical_position":best_logical,
            "best_row_token_matches_local_token":best_token_match_local,
            "best_row_token_matches_warm_logical_token":best_token_matches_target,
            "distinct_local_vs_logical_token_rows":distinct_token_rows,
            "same_local_beats_same_logical_on_distinct_token_rows":local_beats_logical_distinct_token,
            "best_row_is_same_local_column_on_distinct_token_rows":best_local_distinct_token,
            "best_row_is_same_logical_position_on_distinct_token_rows":best_logical_distinct_token,
            "best_row_token_matches_local_token_on_distinct_token_rows":best_token_match_local_distinct_token,
            "best_row_token_matches_warm_logical_token_on_distinct_token_rows":best_token_match_target_distinct_token,
            "rows":rows,
        }

    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.out is not None:
        args.out.write_text(text,encoding="utf-8")
    print(text,end="")
    return 0

if __name__=="__main__":
    raise SystemExit(main())

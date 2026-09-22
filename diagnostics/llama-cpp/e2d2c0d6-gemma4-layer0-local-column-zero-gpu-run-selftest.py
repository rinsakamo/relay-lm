#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
TARGET=HERE/"e2d2c0d6-gemma4-layer0-local-column-zero-gpu-run.py"

def load():
    spec=importlib.util.spec_from_file_location("combined",TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load combined runner")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    m=load()
    nearest={
        "tensors":{
            name:{
                "distinct_local_vs_logical_token_rows":131,
                "same_local_beats_same_logical_on_distinct_token_rows":131,
                "best_row_is_same_local_column":100,
                "best_row_is_same_logical_position":2,
                "best_row_token_matches_local_token":120,
                "best_row_token_matches_warm_logical_token":10,
            }
            for name in ("attn_norm-0","Kcur-0","Vcur-0")
        }
    }
    cls,decisions=m.classify(nearest)
    if cls!="LOCAL_COLUMN_CORRESPONDENCE_PERSISTS_UNDER_DISTINCT_TOKEN_CONTROL":
        raise RuntimeError("positive classifier mismatch")

    nearest["tensors"]["attn_norm-0"]["same_local_beats_same_logical_on_distinct_token_rows"]=130
    cls,_=m.classify(nearest)
    if cls!="LOCAL_COLUMN_CORRESPONDENCE_NOT_UNIFORM_UNDER_DISTINCT_TOKEN_CONTROL":
        raise RuntimeError("negative classifier mismatch")

    print(json.dumps({
        "status":"LAYER0_LOCAL_COLUMN_AND_GGUF_ZERO_GPU_RUN_SELFTEST_PASS",
        "physical_calls":0,
        "gpu_calls":0,
        "model_loads":0,
        "generation_requests":0
    },sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

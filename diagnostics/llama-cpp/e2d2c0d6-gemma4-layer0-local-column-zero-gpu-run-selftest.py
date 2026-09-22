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

def tensor(distinct=131, local_beats=131, best_local=90, best_logical=2, token_local=110, token_target=12):
    return {
        "distinct_local_vs_logical_token_rows":distinct,
        "same_local_beats_same_logical_on_distinct_token_rows":local_beats,
        "best_row_is_same_local_column_on_distinct_token_rows":best_local,
        "best_row_is_same_logical_position_on_distinct_token_rows":best_logical,
        "best_row_token_matches_local_token_on_distinct_token_rows":token_local,
        "best_row_token_matches_warm_logical_token_on_distinct_token_rows":token_target,
        "best_row_is_same_local_column":best_local,
        "best_row_is_same_logical_position":best_logical,
    }

def main():
    m=load()

    positive={"tensors":{
        name:tensor()
        for name in ("attn_norm-0","Kcur-0","Vcur-0")
    }}
    cls,_=m.classify(positive)
    if cls!="LOCAL_COLUMN_NEAREST_MAPPING_SUPPORTED_UNDER_DISTINCT_TOKEN_CONTROL":
        raise RuntimeError("nearest-mapping classifier mismatch")

    pairwise_only={"tensors":{
        name:tensor(best_local=1,best_logical=2,token_local=10,token_target=12)
        for name in ("attn_norm-0","Kcur-0","Vcur-0")
    }}
    cls,_=m.classify(pairwise_only)
    if cls!="LOCAL_COLUMN_PAIRWISE_CORRESPONDENCE_ONLY_UNDER_DISTINCT_TOKEN_CONTROL":
        raise RuntimeError("pairwise-only classifier mismatch")

    negative={"tensors":{
        name:tensor(local_beats=130)
        for name in ("attn_norm-0","Kcur-0","Vcur-0")
    }}
    cls,_=m.classify(negative)
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

#!/usr/bin/env python3
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
NEAREST = HERE / "e2d2c0d6-gemma4-layer0-local-column-nearest-row-posthoc.py"
NEAREST_SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-local-column-nearest-row-posthoc-selftest.py"
GGUF_AUDIT = HERE / "e2d2c0d6-gemma4-gguf-projection-name-audit.py"
GGUF_SELFTEST = HERE / "e2d2c0d6-gemma4-gguf-projection-name-audit-selftest.py"
LOCATOR = HERE / "e2d2c0d6-gemma4-layer0-projection-row-alignment-run.py"

def load_module(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {path}")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def run_json(cmd, stdout_path: Path, stderr_path: Path, expected_key=None, expected_value=None):
    cp=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    stdout_path.write_bytes(cp.stdout)
    stderr_path.write_bytes(cp.stderr)
    if cp.returncode != 0:
        raise RuntimeError(f"command failed rc={cp.returncode}: {cmd}")
    obj=json.loads(cp.stdout)
    if expected_key is not None and obj.get(expected_key) != expected_value:
        raise RuntimeError(f"unexpected {expected_key}: {obj.get(expected_key)}")
    return obj

def classify(nearest):
    decisions={}
    all_local_distinct=True
    for name,t in nearest["tensors"].items():
        distinct=t["distinct_local_vs_logical_token_rows"]
        local_beats=t["same_local_beats_same_logical_on_distinct_token_rows"]
        best_local=t["best_row_is_same_local_column"]
        best_logical=t["best_row_is_same_logical_position"]
        decisions[name]={
            "distinct_token_rows":distinct,
            "same_local_beats_same_logical_on_distinct_token_rows":local_beats,
            "best_row_is_same_local_column":best_local,
            "best_row_is_same_logical_position":best_logical,
            "best_row_token_matches_local_token":t["best_row_token_matches_local_token"],
            "best_row_token_matches_warm_logical_token":t["best_row_token_matches_warm_logical_token"],
        }
        all_local_distinct = all_local_distinct and distinct > 0 and local_beats == distinct

    if all_local_distinct:
        primary="LOCAL_COLUMN_CORRESPONDENCE_PERSISTS_UNDER_DISTINCT_TOKEN_CONTROL"
    else:
        primary="LOCAL_COLUMN_CORRESPONDENCE_NOT_UNIFORM_UNDER_DISTINCT_TOKEN_CONTROL"
    return primary,decisions

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--search-root",type=Path,default=Path("/tmp"))
    ap.add_argument("--model",type=Path,required=True)
    ap.add_argument("--out-root",type=Path,required=True)
    args=ap.parse_args()

    if args.out_root.exists():
        raise RuntimeError(f"refusing to overwrite output root: {args.out_root}")
    args.out_root.mkdir(parents=True)

    required=[NEAREST,NEAREST_SELFTEST,GGUF_AUDIT,GGUF_SELFTEST,LOCATOR]
    missing=[str(p) for p in required if not p.is_file()]
    if missing:
        raise RuntimeError(f"required helper missing: {missing}")

    nearest_st=run_json(
        [sys.executable,str(NEAREST_SELFTEST)],
        args.out_root/"nearest-selftest.stdout.json",
        args.out_root/"nearest-selftest.stderr.txt",
        "status","LAYER0_LOCAL_COLUMN_NEAREST_ROW_POSTHOC_SELFTEST_PASS",
    )
    gguf_st=run_json(
        [sys.executable,str(GGUF_SELFTEST)],
        args.out_root/"gguf-selftest.stdout.json",
        args.out_root/"gguf-selftest.stderr.txt",
        "status","GEMMA4_GGUF_PROJECTION_NAME_AUDIT_SELFTEST_PASS",
    )

    locator=load_module(LOCATOR,"row_alignment_locator")
    measured=locator.find_unique(args.search_root)

    nearest_out=args.out_root/"nearest-row.json"
    nearest=run_json(
        [
            sys.executable,str(NEAREST),
            "--projection-root",str(measured["root"]/"projection"),
            "--out",str(nearest_out),
        ],
        args.out_root/"nearest-row.stdout.json",
        args.out_root/"nearest-row.stderr.txt",
        "classification","LAYER0_LOCAL_COLUMN_NEAREST_ROW_POSTHOC_COMPLETE",
    )

    gguf_out=args.out_root/"gguf-projection-name-audit.json"
    gguf=run_json(
        [
            sys.executable,str(GGUF_AUDIT),
            "--model",str(args.model),
            "--out",str(gguf_out),
        ],
        args.out_root/"gguf-audit.stdout.json",
        args.out_root/"gguf-audit.stderr.txt",
        "classification","GEMMA4_GGUF_PROJECTION_NAME_AUDIT_COMPLETE",
    )

    scientific,decisions=classify(nearest)
    terminal={
        "classification":"LAYER0_LOCAL_COLUMN_AND_GGUF_ZERO_GPU_COMPLETE",
        "scientific_classification":scientific,
        "measured_root":str(measured["root"].resolve()),
        "gguf_layer0_projection_path":gguf["layer0_projection_path"],
        "gguf_counts":gguf["counts"],
        "tensor_decisions":decisions,
        "token_control":nearest["token_control"],
        "physical_calls":0,
        "gpu_calls":0,
        "model_loads":0,
        "generation_requests":0,
        "measured_requests":0,
    }
    (args.out_root/"terminal.json").write_text(
        json.dumps(terminal,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps(terminal,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

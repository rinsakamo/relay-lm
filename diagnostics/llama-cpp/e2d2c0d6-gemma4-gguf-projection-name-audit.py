#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

EXPECTED_MODEL_SHA256 = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"

def sha256_file(path: Path):
    import hashlib
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def contains_name(blob: bytes, name: str) -> bool:
    return name.encode("utf-8") in blob

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",type=Path,required=True)
    ap.add_argument("--layers",type=int,default=48)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if args.out is not None and args.out.exists():
        raise RuntimeError(f"refusing to overwrite: {args.out}")
    if not args.model.is_file():
        raise RuntimeError(f"model missing: {args.model}")

    model_sha=sha256_file(args.model)
    if model_sha != EXPECTED_MODEL_SHA256:
        raise RuntimeError(f"model SHA mismatch: {model_sha}")

    blob=args.model.read_bytes()
    layers=[]
    for il in range(args.layers):
        names={
            "q":f"blk.{il}.attn_q.weight",
            "k":f"blk.{il}.attn_k.weight",
            "v":f"blk.{il}.attn_v.weight",
            "qkv":f"blk.{il}.attn_qkv.weight",
        }
        present={key:contains_name(blob,name) for key,name in names.items()}
        layers.append({"layer":il,"names":names,"present":present})

    l0=layers[0]
    if l0["present"]["qkv"]:
        l0_path="FUSED_QKV"
    elif l0["present"]["q"] and l0["present"]["k"] and l0["present"]["v"]:
        l0_path="SEPARATE_Q_K_V"
    elif l0["present"]["q"] and l0["present"]["k"] and not l0["present"]["v"]:
        l0_path="SEPARATE_Q_K_WITH_V_REUSED_FROM_K"
    else:
        l0_path="UNRESOLVED"

    result={
        "classification":"GEMMA4_GGUF_PROJECTION_NAME_AUDIT_COMPLETE",
        "model_sha256":model_sha,
        "layer0_projection_path":l0_path,
        "layer0":l0,
        "counts":{
            key:sum(1 for x in layers if x["present"][key])
            for key in ("q","k","v","qkv")
        },
        "layers":layers,
        "physical_calls":0,
        "gpu_calls":0,
        "model_loads":0,
        "generation_requests":0,
    }
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.out is not None:
        args.out.write_text(text,encoding="utf-8")
    print(text,end="")
    return 0

if __name__=="__main__":
    raise SystemExit(main())

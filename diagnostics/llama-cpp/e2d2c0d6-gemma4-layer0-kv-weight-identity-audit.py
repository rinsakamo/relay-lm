#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import sys

EXPECTED_MODEL_SHA256 = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"

def sha256_file(path: Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_slice(path: Path, offset: int, size: int):
    h=hashlib.sha256()
    remaining=size
    with path.open("rb") as f:
        f.seek(offset)
        while remaining:
            chunk=f.read(min(1024*1024,remaining))
            if not chunk:
                raise RuntimeError("unexpected EOF while hashing tensor slice")
            h.update(chunk)
            remaining-=len(chunk)
    return h.hexdigest()

def load_reader(gguf_py_root: Path):
    root=str(gguf_py_root.resolve())
    if root not in sys.path:
        sys.path.insert(0,root)
    from gguf import GGUFReader
    return GGUFReader

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",type=Path,required=True)
    ap.add_argument("--gguf-py-root",type=Path,required=True)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()

    if args.out is not None and args.out.exists():
        raise RuntimeError(f"refusing to overwrite: {args.out}")
    if not args.model.is_file():
        raise RuntimeError(f"model missing: {args.model}")
    if not args.gguf_py_root.is_dir():
        raise RuntimeError(f"gguf-py root missing: {args.gguf_py_root}")

    model_sha=sha256_file(args.model)
    if model_sha != EXPECTED_MODEL_SHA256:
        raise RuntimeError(f"model SHA mismatch: {model_sha}")

    GGUFReader=load_reader(args.gguf_py_root)
    reader=GGUFReader(args.model,"r")
    by_name={t.name:t for t in reader.tensors}

    names={
        "K":"blk.0.attn_k.weight",
        "V":"blk.0.attn_v.weight",
    }
    missing=[name for name in names.values() if name not in by_name]
    if missing:
        raise RuntimeError(f"required layer-0 projection tensor missing: {missing}")

    tensors={}
    for key,name in names.items():
        t=by_name[name]
        tensors[key]={
            "name":name,
            "type":getattr(t.tensor_type,"name",str(t.tensor_type)),
            "shape":[int(x) for x in t.shape.tolist()],
            "n_elements":int(t.n_elements),
            "n_bytes":int(t.n_bytes),
            "data_offset":int(t.data_offset),
            "payload_sha256":sha256_slice(args.model,int(t.data_offset),int(t.n_bytes)),
        }

    same_payload=(
        tensors["K"]["n_bytes"]==tensors["V"]["n_bytes"]
        and tensors["K"]["payload_sha256"]==tensors["V"]["payload_sha256"]
    )
    result={
        "classification":"GEMMA4_LAYER0_KV_WEIGHT_IDENTITY_AUDIT_COMPLETE",
        "model_sha256":model_sha,
        "K":tensors["K"],
        "V":tensors["V"],
        "same_type":tensors["K"]["type"]==tensors["V"]["type"],
        "same_shape":tensors["K"]["shape"]==tensors["V"]["shape"],
        "same_payload_sha256":same_payload,
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

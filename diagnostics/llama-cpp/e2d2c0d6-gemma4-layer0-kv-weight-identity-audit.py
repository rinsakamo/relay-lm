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

def load_gguf(gguf_py_root: Path):
    root=str(gguf_py_root.resolve())
    if root not in sys.path:
        sys.path.insert(0,root)
    import gguf
    return gguf

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

    gguf=load_gguf(args.gguf_py_root)
    reader=gguf.GGUFReader(args.model,"r")
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

    # Dequantize with the frozen gguf-py implementation. This is CPU/file-only:
    # it does not instantiate llama.cpp, a model context, CUDA, or a backend.
    import numpy as np
    kdq=gguf.quants.dequantize(by_name[names["K"]].data, by_name[names["K"]].tensor_type).astype(np.float32, copy=False)
    vdq=gguf.quants.dequantize(by_name[names["V"]].data, by_name[names["V"]].tensor_type).astype(np.float32, copy=False)
    if kdq.shape != vdq.shape:
        dq_equal=False
        dq_max_abs=None
        dq_mean_abs=None
        kdq_sha=hashlib.sha256(kdq.tobytes(order="C")).hexdigest()
        vdq_sha=hashlib.sha256(vdq.tobytes(order="C")).hexdigest()
    else:
        diff=np.abs(kdq-vdq)
        dq_equal=bool(np.array_equal(kdq,vdq))
        dq_max_abs=float(diff.max()) if diff.size else 0.0
        dq_mean_abs=float(diff.mean()) if diff.size else 0.0
        kdq_sha=hashlib.sha256(kdq.tobytes(order="C")).hexdigest()
        vdq_sha=hashlib.sha256(vdq.tobytes(order="C")).hexdigest()

    result={
        "classification":"GEMMA4_LAYER0_KV_WEIGHT_IDENTITY_AUDIT_COMPLETE",
        "model_sha256":model_sha,
        "K":tensors["K"],
        "V":tensors["V"],
        "same_type":tensors["K"]["type"]==tensors["V"]["type"],
        "same_shape":tensors["K"]["shape"]==tensors["V"]["shape"],
        "same_payload_sha256":same_payload,
        "dequantized":{
            "K_shape":[int(x) for x in kdq.shape],
            "V_shape":[int(x) for x in vdq.shape],
            "K_f32_sha256":kdq_sha,
            "V_f32_sha256":vdq_sha,
            "bit_exact_equal":dq_equal,
            "max_absolute_difference":dq_max_abs,
            "mean_absolute_difference":dq_mean_abs,
        },
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

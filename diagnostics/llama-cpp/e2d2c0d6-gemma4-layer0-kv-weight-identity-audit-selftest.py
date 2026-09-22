#!/usr/bin/env python3
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile

HERE=Path(__file__).resolve().parent
TARGET=HERE/"e2d2c0d6-gemma4-layer0-kv-weight-identity-audit.py"

def load():
    spec=importlib.util.spec_from_file_location("kv_weight_audit",TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load K/V weight audit")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def enc_string(s):
    b=s.encode("utf-8")
    return struct.pack("<Q",len(b))+b

def build_synthetic_gguf(path):
    header=b"GGUF"+struct.pack("<IQQ",3,2,0)
    kname="blk.0.attn_k.weight"
    vname="blk.0.attn_v.weight"
    kinfo=enc_string(kname)+struct.pack("<I",1)+struct.pack("<Q",256)+struct.pack("<I",12)+struct.pack("<Q",0)
    vinfo=enc_string(vname)+struct.pack("<I",1)+struct.pack("<Q",256)+struct.pack("<I",14)+struct.pack("<Q",160)
    meta=header+kinfo+vinfo
    pad=(-len(meta))%32
    data=bytearray(160+210)
    path.write_bytes(meta+b"\x00"*pad+data)

def main():
    source=TARGET.read_text(encoding="utf-8")
    if "import numpy" in source or "from numpy" in source:
        raise RuntimeError("stdlib-only audit unexpectedly imports numpy")

    m=load()

    with tempfile.TemporaryDirectory(prefix="relaylm-kv-weight-audit-selftest-") as td:
        base=Path(td)

        p=base/"blob.bin"
        raw=b"abcdefgh0123456789XYZ"
        p.write_bytes(raw)
        got=m.sha256_slice(p,8,10)
        exp=hashlib.sha256(raw[8:18]).hexdigest()
        if got != exp:
            raise RuntimeError("slice SHA mismatch")

        q4=bytearray(144)
        q4[0:2]=struct.pack("<e",1.0)
        q4[2:4]=struct.pack("<e",0.0)
        q4[4:8]=bytes([1,1,1,1])
        q4[16:144]=bytes([0x11])*128
        q4v=m.decode_q4_k(bytes(q4))
        if len(q4v)!=256 or q4v[:128] != [1.0]*128 or q4v[128:] != [0.0]*128:
            raise RuntimeError("Q4_K synthetic decode mismatch")

        q6=bytearray(210)
        q6[192:208]=bytes([1])*16
        q6[208:210]=struct.pack("<e",1.0)
        q6v=m.decode_q6_k(bytes(q6))
        if len(q6v)!=256 or q6v != [-32.0]*256:
            raise RuntimeError("Q6_K synthetic decode mismatch")

        gguf=base/"synthetic.gguf"
        build_synthetic_gguf(gguf)
        parsed=m.parse_gguf(gguf)
        k=parsed["tensors"]["blk.0.attn_k.weight"]
        v=parsed["tensors"]["blk.0.attn_v.weight"]
        if k["type"]!="Q4_K" or k["n_bytes"]!=144:
            raise RuntimeError(f"synthetic K metadata mismatch: {k}")
        if v["type"]!="Q6_K" or v["n_bytes"]!=210:
            raise RuntimeError(f"synthetic V metadata mismatch: {v}")
        if v["data_offset"]-k["data_offset"]!=160:
            raise RuntimeError("synthetic tensor offset mismatch")

    print(json.dumps({
        "status":"GEMMA4_LAYER0_KV_WEIGHT_IDENTITY_AUDIT_SELFTEST_PASS",
        "implementation":"stdlib_only_frozen_format",
        "physical_calls":0,
        "gpu_calls":0,
        "model_loads":0,
        "generation_requests":0
    },sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

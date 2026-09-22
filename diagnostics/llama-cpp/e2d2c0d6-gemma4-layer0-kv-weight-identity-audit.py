#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

EXPECTED_MODEL_SHA256 = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
GGUF_DEFAULT_ALIGNMENT = 32

VALUE_SIZES = {
    0: 1,  # UINT8
    1: 1,  # INT8
    2: 2,  # UINT16
    3: 2,  # INT16
    4: 4,  # UINT32
    5: 4,  # INT32
    6: 4,  # FLOAT32
    7: 1,  # BOOL
    10: 8, # UINT64
    11: 8, # INT64
    12: 8, # FLOAT64
}

TYPE_NAMES = {
    0: "F32", 1: "F16", 2: "Q4_0", 3: "Q4_1", 6: "Q5_0", 7: "Q5_1",
    8: "Q8_0", 9: "Q8_1", 10: "Q2_K", 11: "Q3_K", 12: "Q4_K",
    13: "Q5_K", 14: "Q6_K", 15: "Q8_K", 16: "IQ2_XXS", 17: "IQ2_XS",
    18: "IQ3_XXS", 19: "IQ1_S", 20: "IQ4_NL", 21: "IQ3_S", 22: "IQ2_S",
    23: "IQ4_XS", 24: "I8", 25: "I16", 26: "I32", 27: "I64", 28: "F64",
    29: "IQ1_M", 30: "BF16", 34: "TQ1_0", 35: "TQ2_0", 39: "MXFP4",
    40: "NVFP4", 41: "Q1_0", 42: "Q2_0",
}

# Frozen gguf-py constants at llama.cpp e2d2c0d6...
QUANT_SIZES = {
    0: (1,4), 1:(1,2), 2:(32,18), 3:(32,20), 6:(32,22), 7:(32,24),
    8:(32,34), 9:(32,40), 10:(256,84), 11:(256,110), 12:(256,144),
    13:(256,176), 14:(256,210), 15:(256,292), 16:(256,66), 17:(256,74),
    18:(256,98), 19:(256,50), 20:(32,18), 21:(256,110), 22:(256,82),
    23:(256,136), 24:(1,1), 25:(1,2), 26:(1,4), 27:(1,8), 28:(1,8),
    29:(256,56), 30:(1,2), 34:(256,54), 35:(256,66), 39:(32,17),
    40:(64,36), 41:(128,18), 42:(64,18),
}

def sha256_file(path: Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def read_exact(f, n):
    b=f.read(n)
    if len(b)!=n:
        raise RuntimeError(f"unexpected EOF: wanted {n}, got {len(b)}")
    return b

def u32(f):
    return struct.unpack("<I", read_exact(f,4))[0]

def u64(f):
    return struct.unpack("<Q", read_exact(f,8))[0]

def gguf_string(f):
    n=u64(f)
    if n > 1_000_000_000:
        raise RuntimeError(f"implausible GGUF string length: {n}")
    return read_exact(f,n).decode("utf-8")

def skip_value(f, typ):
    if typ in VALUE_SIZES:
        f.seek(VALUE_SIZES[typ],1)
        return None
    if typ == 8: # STRING
        return gguf_string(f)
    if typ == 9: # ARRAY
        elem=u32(f)
        n=u64(f)
        if elem in VALUE_SIZES:
            f.seek(VALUE_SIZES[elem]*n,1)
            return None
        for _ in range(n):
            skip_value(f,elem)
        return None
    raise RuntimeError(f"unsupported GGUF metadata value type: {typ}")

def read_scalar_value(f, typ):
    if typ == 4:
        return u32(f)
    if typ == 10:
        return u64(f)
    if typ == 8:
        return gguf_string(f)
    return skip_value(f,typ)

def parse_gguf(path: Path):
    with path.open("rb") as f:
        if read_exact(f,4) != b"GGUF":
            raise RuntimeError("GGUF magic mismatch")
        version=u32(f)
        if version not in (2,3):
            raise RuntimeError(f"unsupported GGUF version: {version}")
        n_tensors=u64(f)
        n_kv=u64(f)

        alignment=GGUF_DEFAULT_ALIGNMENT
        for _ in range(n_kv):
            key=gguf_string(f)
            typ=u32(f)
            if key == "general.alignment":
                val=read_scalar_value(f,typ)
                if not isinstance(val,int):
                    raise RuntimeError("general.alignment is not integer")
                alignment=val
            else:
                skip_value(f,typ)

        infos={}
        for _ in range(n_tensors):
            name=gguf_string(f)
            n_dims=u32(f)
            if n_dims < 1 or n_dims > 4:
                raise RuntimeError(f"{name}: invalid n_dims={n_dims}")
            dims=[u64(f) for _ in range(n_dims)]
            qtype=u32(f)
            rel_off=u64(f)
            if qtype not in QUANT_SIZES:
                raise RuntimeError(f"{name}: unsupported quant type id={qtype}")
            n_elements=math.prod(dims)
            block,type_size=QUANT_SIZES[qtype]
            if n_elements % block:
                raise RuntimeError(f"{name}: n_elements={n_elements} not divisible by block={block}")
            n_bytes=n_elements//block*type_size
            infos[name]={
                "name":name, "type_id":qtype, "type":TYPE_NAMES.get(qtype,str(qtype)),
                "shape":dims, "n_elements":n_elements, "n_bytes":n_bytes,
                "relative_offset":rel_off,
            }

        pos=f.tell()
        data_offset=(pos + alignment - 1)//alignment*alignment
        for info in infos.values():
            info["data_offset"]=data_offset+info["relative_offset"]

    return {
        "version":version,
        "n_tensors":n_tensors,
        "n_kv":n_kv,
        "alignment":alignment,
        "data_offset":data_offset,
        "tensors":infos,
    }

def sha256_slice(path: Path, offset: int, size: int):
    h=hashlib.sha256()
    with path.open("rb") as f:
        f.seek(offset)
        remaining=size
        while remaining:
            b=f.read(min(1024*1024,remaining))
            if not b:
                raise RuntimeError("unexpected EOF while hashing tensor")
            h.update(b)
            remaining-=len(b)
    return h.hexdigest()

def f16(raw2):
    return struct.unpack("<e",raw2)[0]

def f32(x):
    return struct.unpack("<f", struct.pack("<f", float(x)))[0]

def decode_q4_k(block):
    if len(block)!=144:
        raise RuntimeError("Q4_K block size mismatch")
    d=f16(block[0:2])
    dmin=f16(block[2:4])
    s=block[4:16]
    qs=block[16:144]

    ds=list(s[0:4])
    ms=list(s[4:8])
    md=list(s[8:12])
    sc=[x & 0x3F for x in ds] + [
        (md[j] & 0x0F) | ((ds[j] >> 2) & 0x30) for j in range(4)
    ]
    mn=[x & 0x3F for x in ms] + [
        (md[j] >> 4) | ((ms[j] >> 2) & 0x30) for j in range(4)
    ]

    out=[]
    for chunk in range(4):
        q32=qs[chunk*32:(chunk+1)*32]
        for high in (False,True):
            g=chunk*2+(1 if high else 0)
            dd=f32(d*sc[g])
            dm=f32(dmin*mn[g])
            shift=4 if high else 0
            for b in q32:
                q=(b>>shift)&0x0F
                out.append(f32(f32(dd*q)-dm))
    if len(out)!=256:
        raise RuntimeError("Q4_K decode length mismatch")
    return out

def decode_q6_k(block):
    if len(block)!=210:
        raise RuntimeError("Q6_K block size mismatch")
    ql=block[0:128]
    qh=block[128:192]
    scales=[struct.unpack("<b",bytes([x]))[0] for x in block[192:208]]
    d=f16(block[208:210])

    lo=[]
    for chunk in range(2):
        q64=ql[chunk*64:(chunk+1)*64]
        for high in (False,True):
            shift=4 if high else 0
            vals=[(b>>shift)&0x0F for b in q64]
            lo.extend(vals[0:32])
            lo.extend(vals[32:64])

    hi=[]
    for chunk in range(2):
        q32=qh[chunk*32:(chunk+1)*32]
        for shift in (0,2,4,6):
            hi.extend([(b>>shift)&0x03 for b in q32])

    if len(lo)!=256 or len(hi)!=256:
        raise RuntimeError("Q6_K intermediate decode length mismatch")

    out=[]
    for i,(l,h) in enumerate(zip(lo,hi)):
        q=(l | (h<<4))-32
        ds=f32(d*scales[i//16])
        out.append(f32(ds*q))
    return out

def decoder_for(qtype):
    if qtype==12:
        return 144,decode_q4_k
    if qtype==14:
        return 210,decode_q6_k
    raise RuntimeError(f"stdlib dequantizer does not support {TYPE_NAMES.get(qtype,qtype)}")

def dequant_hash_and_compare(model, kinfo, vinfo):
    kb,kdec=decoder_for(kinfo["type_id"])
    vb,vdec=decoder_for(vinfo["type_id"])
    if kinfo["n_elements"] != vinfo["n_elements"]:
        return {
            "K_f32_sha256":None,"V_f32_sha256":None,
            "bit_exact_equal":False,
            "max_absolute_difference":None,
            "mean_absolute_difference":None,
            "reason":"element_count_mismatch",
        }

    kh=hashlib.sha256(); vh=hashlib.sha256()
    equal=True
    max_abs=0.0
    abs_sum=0.0
    count=0

    with model.open("rb") as f:
        kpos=kinfo["data_offset"]
        vpos=vinfo["data_offset"]
        nblocks=kinfo["n_elements"]//256
        for bi in range(nblocks):
            f.seek(kpos+bi*kb)
            kvals=kdec(read_exact(f,kb))
            f.seek(vpos+bi*vb)
            vvals=vdec(read_exact(f,vb))
            for x,y in zip(kvals,vvals):
                xb=struct.pack("<f",x)
                yb=struct.pack("<f",y)
                kh.update(xb); vh.update(yb)
                if xb!=yb:
                    equal=False
                delta=abs(float(x)-float(y))
                if delta>max_abs:
                    max_abs=delta
                abs_sum+=delta
                count+=1

    return {
        "K_f32_sha256":kh.hexdigest(),
        "V_f32_sha256":vh.hexdigest(),
        "bit_exact_equal":equal,
        "max_absolute_difference":max_abs,
        "mean_absolute_difference":abs_sum/count if count else 0.0,
        "elements_compared":count,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",type=Path,required=True)
    ap.add_argument("--llama-source",type=Path,required=False) # retained CLI compatibility; not imported
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if args.out is not None and args.out.exists():
        raise RuntimeError(f"refusing to overwrite: {args.out}")
    if not args.model.is_file():
        raise RuntimeError(f"model missing: {args.model}")

    model_sha=sha256_file(args.model)
    if model_sha!=EXPECTED_MODEL_SHA256:
        raise RuntimeError(f"model SHA mismatch: {model_sha}")

    parsed=parse_gguf(args.model)
    kn="blk.0.attn_k.weight"
    vn="blk.0.attn_v.weight"
    if kn not in parsed["tensors"] or vn not in parsed["tensors"]:
        raise RuntimeError("required layer-0 K/V weight missing")
    k=dict(parsed["tensors"][kn])
    v=dict(parsed["tensors"][vn])
    k["payload_sha256"]=sha256_slice(args.model,k["data_offset"],k["n_bytes"])
    v["payload_sha256"]=sha256_slice(args.model,v["data_offset"],v["n_bytes"])

    dq=dequant_hash_and_compare(args.model,k,v)
    raw_equal=(k["n_bytes"]==v["n_bytes"] and k["payload_sha256"]==v["payload_sha256"])

    result={
        "classification":"GEMMA4_LAYER0_KV_WEIGHT_IDENTITY_AUDIT_COMPLETE",
        "implementation":"stdlib_only_frozen_format",
        "numpy_required":False,
        "model_sha256":model_sha,
        "gguf":{
            "version":parsed["version"],
            "alignment":parsed["alignment"],
            "data_offset":parsed["data_offset"],
        },
        "K":k,
        "V":v,
        "same_type":k["type_id"]==v["type_id"],
        "same_shape":k["shape"]==v["shape"],
        "same_payload_sha256":raw_equal,
        "dequantized":dq,
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

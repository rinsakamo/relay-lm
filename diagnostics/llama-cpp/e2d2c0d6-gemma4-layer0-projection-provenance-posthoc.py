#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
from pathlib import Path

EXPECTED_DUMPS = ("W-p0-370-w371", "W-p371-878-w508", "C-p0-511-w512")
EXPECTED_WIDTHS = {
    "W-p0-370-w371": 371,
    "W-p371-878-w508": 508,
    "C-p0-511-w512": 512,
}
EXPECTED_TENSORS = ("attn_norm-0", "Kcur-0", "Vcur-0")
EXPECTED_FIELDS = [
    "name", "tensor_ptr", "data_ptr", "buffer_ptr", "view_src_ptr",
    "view_src_data_ptr", "view_offs", "op", "flags", "type", "ne0",
    "ne1", "nb0", "nb1", "src0_ptr", "src0_name", "src0_type",
    "src0_data_ptr", "src0_buffer_ptr", "src0_op", "src1_ptr",
    "src1_name", "src1_type", "src1_data_ptr", "src1_buffer_ptr",
    "src1_op",
]

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

NULL_POINTERS = {"", "0", "0x0", "(nil)", "nullptr", "NULL", "null"}

def pointer_value(value: str):
    v = value.strip()
    if v in NULL_POINTERS:
        return None
    try:
        if int(v, 0) == 0:
            return None
    except ValueError:
        pass
    return v

def load_provenance(dump: Path):
    p=dump/"provenance.tsv"
    if not p.is_file():
        raise RuntimeError(f"provenance missing: {p}")
    with p.open("r",encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f,delimiter="\t"))
    if not rows:
        raise RuntimeError(f"empty provenance: {p}")
    if list(rows[0].keys()) != EXPECTED_FIELDS:
        raise RuntimeError(f"provenance schema mismatch: {p}: {list(rows[0].keys())}")
    names=[r["name"] for r in rows]
    if len(names) != len(set(names)):
        raise RuntimeError(f"duplicate provenance tensor row: {p}: {names}")
    by_name={r["name"]:r for r in rows}
    if set(by_name) != set(EXPECTED_TENSORS):
        raise RuntimeError(f"provenance tensor set mismatch: {p}: {sorted(by_name)}")
    return by_name

def nonempty_distinct(a,b,key):
    av=pointer_value(a[key]) if key.endswith("_ptr") else a[key]
    bv=pointer_value(b[key]) if key.endswith("_ptr") else b[key]
    return av is not None and bv is not None and av != bv

def classify_dump(dump: Path):
    prov=load_provenance(dump)
    n=prov["attn_norm-0"]
    k=prov["Kcur-0"]
    v=prov["Vcur-0"]

    if dump.name not in EXPECTED_WIDTHS:
        raise RuntimeError(f"unexpected provenance dump name: {dump.name}")
    width = EXPECTED_WIDTHS[dump.name]
    expected_geometry = {
        "attn_norm-0": (3840, width, 4, 3840 * 4),
        "Kcur-0": (2048, width, 4, 2048 * 4),
        "Vcur-0": (2048, width, 4, 2048 * 4),
    }
    for tensor_name, row in prov.items():
        ne0, ne1, nb0, nb1 = expected_geometry[tensor_name]
        if row["type"] != "f32":
            raise RuntimeError(f"{dump}/{tensor_name}: expected f32, got {row['type']!r}")
        actual = (int(row["ne0"]), int(row["ne1"]), int(row["nb0"]), int(row["nb1"]))
        expected = (ne0, ne1, nb0, nb1)
        if actual != expected:
            raise RuntimeError(
                f"{dump}/{tensor_name}: geometry mismatch: {actual} != {expected}"
            )

    kp=dump/"Kcur-0.bin"
    vp=dump/"Vcur-0.bin"
    if not kp.is_file() or not vp.is_file():
        raise RuntimeError(f"K/V payload missing under {dump}")
    expected_kv_bytes = 2048 * width * 4
    if kp.stat().st_size != expected_kv_bytes or vp.stat().st_size != expected_kv_bytes:
        raise RuntimeError(
            f"K/V payload geometry mismatch under {dump}: "
            f"K={kp.stat().st_size} V={vp.stat().st_size} expected={expected_kv_bytes}"
        )
    ksha=sha256(kp); vsha=sha256(vp)
    value_identical=(kp.stat().st_size==vp.stat().st_size and ksha==vsha)

    checks={
        "tensor_ptr_distinct":nonempty_distinct(k,v,"tensor_ptr"),
        "data_ptr_distinct":nonempty_distinct(k,v,"data_ptr"),
        "buffer_ptr_distinct":nonempty_distinct(k,v,"buffer_ptr"),
        "view_src_ptr_distinct":(
            (pointer_value(k["view_src_ptr"]) is None and pointer_value(v["view_src_ptr"]) is None) or
            nonempty_distinct(k,v,"view_src_ptr")
        ),
        "src0_ptr_distinct":nonempty_distinct(k,v,"src0_ptr"),
        "src0_data_ptr_distinct":nonempty_distinct(k,v,"src0_data_ptr"),
        "src0_buffer_ptr_distinct":nonempty_distinct(k,v,"src0_buffer_ptr"),
        "src0_type_distinct":nonempty_distinct(k,v,"src0_type"),
        "src0_name_distinct":nonempty_distinct(k,v,"src0_name"),
        "src1_same_object":(
            pointer_value(k["src1_ptr"]) is not None
            and pointer_value(k["src1_ptr"]) == pointer_value(v["src1_ptr"])
        ),
        "src1_same_data":(
            pointer_value(k["src1_data_ptr"]) is not None
            and pointer_value(k["src1_data_ptr"]) == pointer_value(v["src1_data_ptr"])
        ),
        "src1_is_attn_norm_object":(
            pointer_value(k["src1_ptr"]) is not None
            and pointer_value(k["src1_ptr"]) == pointer_value(v["src1_ptr"])
            and pointer_value(k["src1_ptr"]) == pointer_value(n["tensor_ptr"])
        ),
        "src1_is_attn_norm_data":(
            pointer_value(k["src1_data_ptr"]) is not None
            and pointer_value(k["src1_data_ptr"]) == pointer_value(v["src1_data_ptr"])
            and pointer_value(k["src1_data_ptr"]) == pointer_value(n["data_ptr"])
        ),
        "op_equal":bool(k["op"] and k["op"]==v["op"]),
        "value_identical":value_identical,
    }
    checks["expected_projection_semantics"]=(
        k["op"]=="MUL_MAT" and v["op"]=="MUL_MAT"
        and k["src0_type"]=="Q4_K" and v["src0_type"]=="Q6_K"
        and k["src0_name"]=="blk.0.attn_k.weight"
        and v["src0_name"]=="blk.0.attn_v.weight"
        and k["src0_op"]=="NONE" and v["src0_op"]=="NONE"
        and k["type"]=="f32" and v["type"]=="f32" and n["type"]=="f32"
        and k["ne0"]=="2048" and v["ne0"]=="2048" and n["ne0"]=="3840"
        and checks["src1_is_attn_norm_object"]
        and checks["src1_is_attn_norm_data"]
        and k["src1_name"]=="attn_norm-0" and v["src1_name"]=="attn_norm-0"
        and k["src1_type"]=="f32" and v["src1_type"]=="f32"
        and k["src1_op"]=="MUL" and v["src1_op"]=="MUL"
    )

    if not checks["tensor_ptr_distinct"]:
        primary="K_V_RUNTIME_TENSOR_OBJECT_ALIAS"
    elif not checks["data_ptr_distinct"]:
        primary="K_V_RUNTIME_OUTPUT_DATA_ALIAS"
    elif not checks["src0_ptr_distinct"] or not checks["src0_data_ptr_distinct"]:
        primary="K_V_RUNTIME_WEIGHT_SOURCE_ALIAS"
    elif value_identical and checks["expected_projection_semantics"]:
        primary="K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_IDENTICAL"
    elif value_identical:
        primary="K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_IDENTICAL_SOURCE_SEMANTICS_UNEXPECTED"
    else:
        primary="K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_DISTINCT"

    return {
        "dump":dump.name,
        "classification":primary,
        "checks":checks,
        "K":{
            key:k[key] for key in (
                "tensor_ptr","data_ptr","buffer_ptr","view_src_ptr","view_src_data_ptr",
                "view_offs","op","flags","type","ne0","ne1","nb0","nb1",
                "src0_ptr","src0_name","src0_type","src0_data_ptr","src0_buffer_ptr","src0_op",
                "src1_ptr","src1_name","src1_type","src1_data_ptr","src1_buffer_ptr","src1_op",
            )
        },
        "V":{
            key:v[key] for key in (
                "tensor_ptr","data_ptr","buffer_ptr","view_src_ptr","view_src_data_ptr",
                "view_offs","op","flags","type","ne0","ne1","nb0","nb1",
                "src0_ptr","src0_name","src0_type","src0_data_ptr","src0_buffer_ptr","src0_op",
                "src1_ptr","src1_name","src1_type","src1_data_ptr","src1_buffer_ptr","src1_op",
            )
        },
        "K_payload_sha256":ksha,
        "V_payload_sha256":vsha,
    }

def classify_all(results):
    classes={r["classification"] for r in results}
    if classes == {"K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_IDENTICAL"}:
        return "K_V_DISTINCT_RUNTIME_PROVENANCE_IDENTICAL_VALUES_REPRODUCED"
    if len(classes)==1:
        return next(iter(classes))
    return "K_V_RUNTIME_PROVENANCE_MIXED_ACROSS_DUMPS"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--projection-root",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    if args.out.exists():
        raise RuntimeError(f"refusing to overwrite: {args.out}")
    results=[]
    for name in EXPECTED_DUMPS:
        d=args.projection_root/name
        if not d.is_dir():
            raise RuntimeError(f"projection dump missing: {d}")
        results.append(classify_dump(d))

    out={
        "classification":"LAYER0_PROJECTION_PROVENANCE_POSTHOC_COMPLETE",
        "scientific_classification":classify_all(results),
        "dumps":results,
        "physical_calls":0,
        "gpu_calls":0,
        "model_loads":0,
        "generation_requests":0,
        "measured_requests":0,
    }
    args.out.mkdir(parents=True)
    (args.out/"terminal.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

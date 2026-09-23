#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile

HERE=Path(__file__).resolve().parent
TARGET=HERE/"e2d2c0d6-gemma4-layer0-projection-provenance-posthoc.py"

def load():
    spec=importlib.util.spec_from_file_location("prov_posthoc",TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load provenance posthoc")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def row(m,name, tensor_ptr, data_ptr, src0_ptr, src0_name, src0_type, src0_data, src1_ptr="0xa0", src1_data="0xb0"):
    vals={
        "name":name,
        "tensor_ptr":tensor_ptr,
        "data_ptr":data_ptr,
        "buffer_ptr":"0xc0",
        "view_src_ptr":"0",
        "view_src_data_ptr":"0",
        "view_offs":"0",
        "op":"MUL_MAT" if name!="attn_norm-0" else "MUL",
        "flags":"2",
        "type":"f32",
        "ne0":"2048" if name!="attn_norm-0" else "3840",
        "ne1":"512",
        "nb0":"4",
        "nb1":"8192" if name!="attn_norm-0" else "15360",
        "src0_ptr":src0_ptr,
        "src0_name":src0_name,
        "src0_type":src0_type,
        "src0_data_ptr":src0_data,
        "src0_buffer_ptr":"0xd0",
        "src0_op":"NONE",
        "src1_ptr":src1_ptr,
        "src1_name":"attn_norm-0",
        "src1_type":"f32",
        "src1_data_ptr":src1_data,
        "src1_buffer_ptr":"0xc0",
        "src1_op":"MUL",
    }
    return [vals[f] for f in m.EXPECTED_FIELDS]

def write_dump(m,root,name,*,alias_tensor=False,alias_data=False,alias_weight=False,identical_values=True,
               null_src1=False, wrong_attn_binding=False, duplicate_k=False):
    d=root/name
    d.mkdir(parents=True)
    rows=[
        row(m,"attn_norm-0","0x10","0x20","0x01","norm","f32","0x02",src1_ptr="0x03",src1_data="0x04"),
        row(
            m,"Kcur-0","0x30","0x40","0x50","blk.0.attn_k.weight","Q4_K","0x60",
            src1_ptr="0" if null_src1 else ("0xa1" if wrong_attn_binding else "0x10"),
            src1_data="0" if null_src1 else ("0xb1" if wrong_attn_binding else "0x20"),
        ),
        row(
            m,"Vcur-0",
            "0x30" if alias_tensor else "0x31",
            "0x40" if alias_data else "0x41",
            "0x50" if alias_weight else "0x51",
            "blk.0.attn_k.weight" if alias_weight else "blk.0.attn_v.weight",
            "Q4_K" if alias_weight else "Q6_K",
            "0x60" if alias_weight else "0x61",
            src1_ptr="0" if null_src1 else ("0xa1" if wrong_attn_binding else "0x10"),
            src1_data="0" if null_src1 else ("0xb1" if wrong_attn_binding else "0x20"),
        ),
    ]
    if duplicate_k:
        rows.append(rows[1])
    with (d/"provenance.tsv").open("w",encoding="utf-8",newline="") as f:
        f.write("\t".join(m.EXPECTED_FIELDS)+"\n")
        for r in rows:
            f.write("\t".join(r)+"\n")
    payload=b"same-payload"
    (d/"Kcur-0.bin").write_bytes(payload)
    (d/"Vcur-0.bin").write_bytes(payload if identical_values else b"different---")
    return d

def main():
    m=load()
    with tempfile.TemporaryDirectory(prefix="relaylm-prov-posthoc-selftest-") as td:
        root=Path(td)

        d=write_dump(m,root,"strong")
        got=m.classify_dump(d)["classification"]
        if got!="K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_IDENTICAL":
            raise RuntimeError(f"strong classifier mismatch: {got}")

        d=write_dump(m,root,"tensor-alias",alias_tensor=True)
        got=m.classify_dump(d)["classification"]
        if got!="K_V_RUNTIME_TENSOR_OBJECT_ALIAS":
            raise RuntimeError(f"tensor alias classifier mismatch: {got}")

        d=write_dump(m,root,"data-alias",alias_data=True)
        got=m.classify_dump(d)["classification"]
        if got!="K_V_RUNTIME_OUTPUT_DATA_ALIAS":
            raise RuntimeError(f"data alias classifier mismatch: {got}")

        d=write_dump(m,root,"weight-alias",alias_weight=True)
        got=m.classify_dump(d)["classification"]
        if got!="K_V_RUNTIME_WEIGHT_SOURCE_ALIAS":
            raise RuntimeError(f"weight alias classifier mismatch: {got}")

        d=write_dump(m,root,"value-distinct",identical_values=False)
        got=m.classify_dump(d)["classification"]
        if got!="K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_DISTINCT":
            raise RuntimeError(f"value distinct classifier mismatch: {got}")

        d=write_dump(m,root,"null-src1",null_src1=True)
        got=m.classify_dump(d)["classification"]
        if got!="K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_IDENTICAL_SOURCE_SEMANTICS_UNEXPECTED":
            raise RuntimeError(f"null src1 incorrectly passed strong classification: {got}")

        d=write_dump(m,root,"wrong-attn-binding",wrong_attn_binding=True)
        got=m.classify_dump(d)["classification"]
        if got!="K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_IDENTICAL_SOURCE_SEMANTICS_UNEXPECTED":
            raise RuntimeError(f"wrong attn binding incorrectly passed strong classification: {got}")

        d=write_dump(m,root,"duplicate-k",duplicate_k=True)
        try:
            m.classify_dump(d)
        except RuntimeError:
            pass
        else:
            raise RuntimeError("duplicate provenance row was not rejected")

        strong=[m.classify_dump(write_dump(m,root,f"all-{i}")) for i in range(3)]
        got=m.classify_all(strong)
        if got!="K_V_DISTINCT_RUNTIME_PROVENANCE_IDENTICAL_VALUES_REPRODUCED":
            raise RuntimeError(f"aggregate classifier mismatch: {got}")

    print(json.dumps({
        "status":"LAYER0_PROJECTION_PROVENANCE_POSTHOC_SELFTEST_PASS",
        "physical_calls":0,
        "gpu_calls":0,
        "model_loads":0,
        "generation_requests":0,
        "measured_requests":0,
    },sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

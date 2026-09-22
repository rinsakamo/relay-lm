#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile

HERE=Path(__file__).resolve().parent
TARGET=HERE/"e2d2c0d6-gemma4-gguf-projection-name-audit.py"

def load():
    spec=importlib.util.spec_from_file_location("gguf_name_audit",TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load GGUF projection-name audit")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    m=load()
    with tempfile.TemporaryDirectory(prefix="relaylm-gguf-name-audit-selftest-") as td:
        p=Path(td)/"synthetic.gguf"
        payload=b"prefix\x00blk.0.attn_q.weight\x00mid\x00blk.0.attn_k.weight\x00suffix"
        p.write_bytes(payload)
        names=[
            "blk.0.attn_q.weight",
            "blk.0.attn_k.weight",
            "blk.0.attn_v.weight",
        ]
        found=m.scan_names(p,names)
        if found[names[0]] is not True or found[names[1]] is not True or found[names[2]] is not False:
            raise RuntimeError(f"unexpected scan result: {found}")

    print(json.dumps({
        "status":"GEMMA4_GGUF_PROJECTION_NAME_AUDIT_SELFTEST_PASS",
        "physical_calls":0,
        "gpu_calls":0,
        "model_loads":0,
        "generation_requests":0
    },sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

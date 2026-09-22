#!/usr/bin/env python3
import hashlib
import importlib.util
import json
from pathlib import Path
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

def main():
    m=load()
    with tempfile.TemporaryDirectory(prefix="relaylm-kv-weight-audit-selftest-") as td:
        p=Path(td)/"blob.bin"
        raw=b"abcdefgh0123456789XYZ"
        p.write_bytes(raw)
        got=m.sha256_slice(p,8,10)
        exp=hashlib.sha256(raw[8:18]).hexdigest()
        if got != exp:
            raise RuntimeError("slice SHA mismatch")
    print(json.dumps({
        "status":"GEMMA4_LAYER0_KV_WEIGHT_IDENTITY_AUDIT_SELFTEST_PASS",
        "physical_calls":0,
        "gpu_calls":0,
        "model_loads":0,
        "generation_requests":0
    },sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

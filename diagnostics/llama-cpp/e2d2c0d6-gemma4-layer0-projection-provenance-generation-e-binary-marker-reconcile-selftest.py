#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile
import sys

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-generation-e-binary-marker-reconcile.py"

def load_module():
    spec = importlib.util.spec_from_file_location("reconcile_mod", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load reconciliation module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def make_fixture(mod, root: Path, *, stable=True, brittle=False, extra_error=False):
    lib = root / "build-stage" / "build" / "bin" / "libllama.so"
    lib.parent.mkdir(parents=True, exist_ok=True)
    payload = b"ELF\x00"
    if stable:
        payload += b"provenance tensor missing: %s\x00tensor_ptr\x00src0_ptr\x00src1_ptr\x00"
    else:
        payload += b"tensor_ptr\x00src0_ptr\x00src1_ptr\x00"
    if brittle:
        payload += b"provenance.tsv\x00"
    lib.write_bytes(payload)

    terminal = {
        "preparation_generation": mod.EXPECTED_GENERATION,
        "primary_classification": "LAYER0_PROJECTION_PROVENANCE_PREPARATION_FAILED",
        "build_returncode": 0,
        "qualification_returncode": 1,
        "generated_requests": 0,
        "measured_l0_submitted": False,
        "measured_attempt_consumed": False,
    }
    build = {
        "preparation_generation": mod.EXPECTED_GENERATION,
        "primary_classification": "LAYER0_PROJECTION_PROVENANCE_BUILD_READY",
        "llama_lib_resolved": str(lib.resolve()),
        **mod.EXPECTED_BUILD_HASHES,
        **mod.EXPECTED_PATCH_HASHES,
    }
    errors = ["required runtime marker missing from llama: provenance.tsv"]
    if extra_error:
        errors.append("some unrelated failure")
    preflight = {
        "status": "LAYER0_PROJECTION_PROVENANCE_BINARY_PREFLIGHT_FAIL",
        "errors": errors,
        "runtime_artifacts": {
            "llama": {
                "sha256": mod.EXPECTED_BUILD_HASHES["llama_lib_sha256"],
                "required_markers": {
                    "provenance.tsv": False,
                    "tensor_ptr": True,
                    "src0_ptr": True,
                    "src1_ptr": True,
                },
            }
        },
    }
    write_json(root / "terminal.json", terminal)
    write_json(root / "build-stage" / "terminal.json", build)
    write_json(root / "qualification-stage" / "logical-prefix-binary-preflight.json", preflight)
    return lib

def main():
    mod = load_module()
    original_sha = mod.sha256
    results = []
    try:
        with tempfile.TemporaryDirectory(prefix="relaylm-prov-reconcile-selftest-") as td:
            root = Path(td) / "strong"
            lib = make_fixture(mod, root)
            mod.sha256 = lambda path: (
                mod.EXPECTED_BUILD_HASHES["llama_lib_sha256"]
                if Path(path).resolve() == lib.resolve()
                else original_sha(path)
            )
            out = mod.reconcile(root)
            results.append({
                "name": "strong_false_negative_reconciles",
                "ok": out["classification"] == "GENERATION_E_BINARY_MARKER_FALSE_NEGATIVE_RECONCILED"
                    and out["errors"] == []
                    and out["marker_evidence"]["brittle_provenance_tsv_present"] is False
                    and all(out["marker_evidence"]["stable_markers"].values()),
            })

        with tempfile.TemporaryDirectory(prefix="relaylm-prov-reconcile-selftest-") as td:
            root = Path(td) / "missing-stable"
            lib = make_fixture(mod, root, stable=False)
            mod.sha256 = lambda path: (
                mod.EXPECTED_BUILD_HASHES["llama_lib_sha256"]
                if Path(path).resolve() == lib.resolve()
                else original_sha(path)
            )
            out = mod.reconcile(root)
            results.append({
                "name": "missing_stable_marker_fails",
                "ok": out["classification"] == "GENERATION_E_BINARY_MARKER_RECONCILIATION_FAILED"
                    and any("stable provenance marker missing" in x for x in out["errors"]),
            })

        with tempfile.TemporaryDirectory(prefix="relaylm-prov-reconcile-selftest-") as td:
            root = Path(td) / "extra-error"
            lib = make_fixture(mod, root, extra_error=True)
            mod.sha256 = lambda path: (
                mod.EXPECTED_BUILD_HASHES["llama_lib_sha256"]
                if Path(path).resolve() == lib.resolve()
                else original_sha(path)
            )
            out = mod.reconcile(root)
            results.append({
                "name": "additional_historical_error_fails",
                "ok": out["classification"] == "GENERATION_E_BINARY_MARKER_RECONCILIATION_FAILED"
                    and any("additional errors" in x for x in out["errors"]),
            })

        with tempfile.TemporaryDirectory(prefix="relaylm-prov-reconcile-selftest-") as td:
            root = Path(td) / "brittle-present"
            lib = make_fixture(mod, root, brittle=True)
            mod.sha256 = lambda path: (
                mod.EXPECTED_BUILD_HASHES["llama_lib_sha256"]
                if Path(path).resolve() == lib.resolve()
                else original_sha(path)
            )
            out = mod.reconcile(root)
            results.append({
                "name": "brittle_marker_present_fails",
                "ok": out["classification"] == "GENERATION_E_BINARY_MARKER_RECONCILIATION_FAILED"
                    and any("brittle provenance.tsv marker unexpectedly present" in x for x in out["errors"]),
            })
    finally:
        mod.sha256 = original_sha

    errors = [r["name"] for r in results if not r["ok"]]
    status = (
        "GENERATION_E_BINARY_MARKER_RECONCILIATION_SELFTEST_PASS"
        if not errors
        else "GENERATION_E_BINARY_MARKER_RECONCILIATION_SELFTEST_FAIL"
    )
    print(json.dumps({"status": status, "results": results, "errors": errors}, indent=2, sort_keys=True))
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())

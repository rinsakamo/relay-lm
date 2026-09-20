#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import sys


def load_classifier():
    here = Path(__file__).resolve().parent
    path = here / "e2d2c0d6-gemma4-kv-logical-prefix-startup-classify.py"
    spec = importlib.util.spec_from_file_location("logical_prefix_startup_classifier", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load startup classifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_block(*, n_seq=1, n_ctx=8192, n_batch=512, n_ubatch=512, flash="enabled", base=8192, swa=1536):
    return (
        "llama_kv_cache_iswa: creating non-SWA KV cache, size = %d cells\n" % base
        + "llama_kv_cache_iswa: creating     SWA KV cache, size = %d cells\n" % swa
        + "llama_context: constructing llama_context\n"
        + "llama_context: n_seq_max             = %d\n" % n_seq
        + "llama_context: n_ctx                 = %d\n" % n_ctx
        + "llama_context: n_batch               = %d\n" % n_batch
        + "llama_context: n_ubatch              = %d\n" % n_ubatch
        + "llama_context: flash_attn            = %s\n" % flash
    )


def all_checks_true(evidence):
    return (
        evidence["context_block_count"] >= 1
        and all(v["ok"] for v in evidence["checks"].values())
    )


def main():
    c = load_classifier()
    errors = []

    valid = valid_block()
    if not all_checks_true(c.final_context_evidence(valid)):
        errors.append("valid final context did not pass")
    if not c.compact_swa_evidence(valid)["ok"]:
        errors.append("valid compact SWA did not pass")

    full = valid_block(swa=8192)
    if c.compact_swa_evidence(full)["ok"]:
        errors.append("full-size SWA incorrectly passed")

    wrong_base = valid_block(base=4096)
    if c.compact_swa_evidence(wrong_base)["ok"]:
        errors.append("wrong base KV size incorrectly passed")

    missing_alloc = (
        "llama_context: constructing llama_context\n"
        "llama_context: n_seq_max = 1\n"
        "llama_context: n_ctx = 8192\n"
        "llama_context: n_batch = 512\n"
        "llama_context: n_ubatch = 512\n"
        "llama_context: flash_attn = enabled\n"
    )
    if c.compact_swa_evidence(missing_alloc)["ok"]:
        errors.append("missing allocation log incorrectly passed")

    split = valid_block() + valid_block(n_ctx=4096)
    split_evidence = c.final_context_evidence(split)
    if split_evidence["checks"]["n_ctx_8192"]["ok"]:
        errors.append("final-context selector mixed evidence across contexts")

    wrong_flash = valid_block(flash="disabled")
    if c.final_context_evidence(wrong_flash)["checks"]["flash_attn_enabled"]["ok"]:
        errors.append("disabled flash attention incorrectly passed")

    status = (
        "LOGICAL_PREFIX_STARTUP_CLASSIFIER_SELFTEST_PASS"
        if not errors
        else "LOGICAL_PREFIX_STARTUP_CLASSIFIER_SELFTEST_FAIL"
    )
    import json
    print(json.dumps({"status": status, "errors": errors}, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

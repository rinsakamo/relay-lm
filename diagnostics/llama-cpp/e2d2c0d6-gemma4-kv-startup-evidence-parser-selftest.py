#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import sys


def load_runner():
    here = Path(__file__).resolve().parent
    runner_path = here / "e2d2c0d6-gemma4-kv-prefix-provenance-run.py"
    spec = importlib.util.spec_from_file_location("kv_prefix_provenance_runner", runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load KV provenance runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    runner = load_runner()
    match = runner._startup_evidence_match

    cases = [
        {
            "name": "exact-source-format",
            "text": (
                "llama_init_from_model: n_batch               = 512\n"
                "llama_init_from_model: n_ubatch              = 512\n"
                "llama_init_from_model: flash_attn            = enabled\n"
            ),
            "expected": {"batch": True, "ubatch": True, "flash": True},
        },
        {
            "name": "compact-spacing",
            "text": "n_batch=512\nn_ubatch=512\nflash_attn=enabled\n",
            "expected": {"batch": True, "ubatch": True, "flash": True},
        },
        {
            "name": "mixed-whitespace",
            "text": "n_batch\t =\t512\nn_ubatch    =  512\nflash_attn\t= enabled\n",
            "expected": {"batch": True, "ubatch": True, "flash": True},
        },
        {
            "name": "wrong-values",
            "text": "n_batch = 2048\nn_ubatch = 256\nflash_attn = disabled\n",
            "expected": {"batch": False, "ubatch": False, "flash": False},
        },
        {
            "name": "near-miss-identifiers",
            "text": "x_n_batch = 512\nn_ubatch_extra = 512\nmy_flash_attn = enabled\n",
            "expected": {"batch": False, "ubatch": False, "flash": False},
        },
    ]

    patterns = {
        "batch": r"^.*\bn_batch\s*=\s*512\b.*$",
        "ubatch": r"^.*\bn_ubatch\s*=\s*512\b.*$",
        "flash": r"^.*\bflash_attn\s*=\s*enabled\b.*$",
    }

    results = []
    errors = []
    for case in cases:
        observed = {name: bool(match(case["text"], pattern)["ok"]) for name, pattern in patterns.items()}
        ok = observed == case["expected"]
        results.append({
            "name": case["name"],
            "expected": case["expected"],
            "observed": observed,
            "ok": ok,
        })
        if not ok:
            errors.append(case["name"])

    out = {
        "status": "STARTUP_EVIDENCE_PARSER_SELFTEST_PASS" if not errors else "STARTUP_EVIDENCE_PARSER_SELFTEST_FAIL",
        "exact_llama_cpp_source_format": {
            "revision": "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d",
            "source": "src/llama-context.cpp",
            "lines": {
                "n_batch": 'LLAMA_LOG_INFO("%s: n_batch               = %u\\n", ...)',
                "n_ubatch": 'LLAMA_LOG_INFO("%s: n_ubatch              = %u\\n", ...)',
                "flash_attn": 'LLAMA_LOG_INFO("%s: flash_attn            = %s\\n", ...)',
            },
        },
        "cases": results,
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

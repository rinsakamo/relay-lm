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
                "llama_context: n_batch               = 512\n"
                "llama_context: n_ubatch              = 512\n"
                "llama_context: flash_attn            = enabled\n"
            ),
            "expected": {"batch": True, "ubatch": True, "flash": True},
        },
        {
            "name": "compact-spacing",
            "text": "llama_context:n_batch=512\nllama_context:n_ubatch=512\nllama_context:flash_attn=enabled\n",
            "expected": {"batch": True, "ubatch": True, "flash": True},
        },
        {
            "name": "mixed-whitespace",
            "text": "prefix llama_context : n_batch\t =\t512\nprefix llama_context: n_ubatch    =  512\nprefix llama_context : flash_attn\t= enabled\n",
            "expected": {"batch": True, "ubatch": True, "flash": True},
        },
        {
            "name": "wrong-values",
            "text": "llama_context: n_batch = 2048\nllama_context: n_ubatch = 256\nllama_context: flash_attn = disabled\n",
            "expected": {"batch": False, "ubatch": False, "flash": False},
        },
        {
            "name": "near-miss-identifiers",
            "text": "llama_context: x_n_batch = 512\nllama_context: n_ubatch_extra = 512\nllama_context: my_flash_attn = enabled\n",
            "expected": {"batch": False, "ubatch": False, "flash": False},
        },
    ]

    cases.append({
        "name": "argv-echo-is-not-runtime-evidence",
        "text": "--batch-size 512 --ubatch-size 512 --flash-attn on\n"
                "n_batch = 512 n_ubatch = 512 flash_attn = enabled\n",
        "expected": {"batch": False, "ubatch": False, "flash": False},
    })

    patterns = {
        "batch": r"^.*\bllama_context\s*:\s*n_batch\s*=\s*512\b.*$",
        "ubatch": r"^.*\bllama_context\s*:\s*n_ubatch\s*=\s*512\b.*$",
        "flash": r"^.*\bllama_context\s*:\s*flash_attn\s*=\s*enabled\b.*$",
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

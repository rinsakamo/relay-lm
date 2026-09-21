#!/usr/bin/env python3
import ast
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-kv-fixture-v2-tokenize-run.py"


def main():
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)

    popen_calls = []
    run_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "subprocess" and node.func.attr == "Popen":
                popen_calls.append(node.lineno)
            if node.func.value.id == "subprocess" and node.func.attr == "run":
                run_calls.append(node.lineno)

    checks = {
        "one_server_popen_site": len(popen_calls) == 1,
        "one_helper_run_site": len(run_calls) == 1,
        "health_endpoint_present": '"/health"' in source,
        "tokenize_endpoint_present": '"/tokenize"' in source,
        "no_completion_endpoint": "/completion" not in source,
        "no_chat_completion_endpoint": "/v1/chat/completions" not in source,
        "generation_counter_zero": '"generation_requests": 0' in source,
        "measured_l0_false": '"measured_l0_submitted": False' in source,
        "non_authorizing": '"measured_execution_authorized_by_this_result": False' in source,
        "fixed_ctx": '"--ctx-size", "8192"' in source,
        "fixed_parallel": '"--parallel", "1"' in source,
        "fixed_batch": '"--batch-size", "512"' in source,
        "fixed_ubatch": '"--ubatch-size", "512"' in source,
        "flash_attention_on": '"--flash-attn", "on"' in source,
        "context_shift_disabled": '"--no-context-shift"' in source,
        "expected_model_sha_bound": (
            "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
            in source
        ),
    }
    errors = [name for name, ok in checks.items() if not ok]
    out = {
        "status": (
            "LOGICAL_PREFIX_FIXTURE_V2_TOKENIZE_RUN_SELFTEST_PASS"
            if not errors
            else "LOGICAL_PREFIX_FIXTURE_V2_TOKENIZE_RUN_SELFTEST_FAIL"
        ),
        "checks": checks,
        "popen_lines": popen_calls,
        "run_lines": run_calls,
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

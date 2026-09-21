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
    http_endpoint_templates = []

    def endpoint_template(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            parts = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    parts.append(value.value)
                elif isinstance(value, ast.FormattedValue):
                    parts.append("{}")
                else:
                    return None
            return "".join(parts)
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "subprocess" and node.func.attr == "Popen":
                popen_calls.append(node.lineno)
            if node.func.value.id == "subprocess" and node.func.attr == "run":
                run_calls.append(node.lineno)

        if isinstance(node.func, ast.Name) and node.func.id in {"http_get", "http_post_raw"}:
            if node.args:
                template = endpoint_template(node.args[0])
                if template is not None:
                    http_endpoint_templates.append({
                        "function": node.func.id,
                        "template": template,
                        "line": node.lineno,
                    })

    endpoint_pairs = {
        (entry["function"], entry["template"])
        for entry in http_endpoint_templates
    }

    checks = {
        "one_server_popen_site": len(popen_calls) == 1,
        "one_helper_run_site": len(run_calls) == 1,
        "health_endpoint_present": (
            ("http_get", "http://127.0.0.1:{}/health") in endpoint_pairs
        ),
        "tokenize_endpoint_present": (
            ("http_post_raw", "http://127.0.0.1:{}/tokenize") in endpoint_pairs
        ),
        "only_health_and_tokenize_http_calls": endpoint_pairs == {
            ("http_get", "http://127.0.0.1:{}/health"),
            ("http_post_raw", "http://127.0.0.1:{}/tokenize"),
        },
        "no_completion_endpoint": all(
            "/completion" not in entry["template"]
            for entry in http_endpoint_templates
        ),
        "no_chat_completion_endpoint": all(
            "/v1/chat/completions" not in entry["template"]
            for entry in http_endpoint_templates
        ),
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
        "http_endpoint_templates": http_endpoint_templates,
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

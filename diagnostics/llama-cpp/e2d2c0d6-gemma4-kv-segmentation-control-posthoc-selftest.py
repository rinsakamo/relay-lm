#!/usr/bin/env python3
import ast
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-kv-segmentation-control-posthoc-reconcile.py"


def load_target():
    spec = importlib.util.spec_from_file_location("segmentation_control_posthoc_contract", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load posthoc reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    module = load_target()
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)

    subprocess_calls = []
    forbidden_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ):
            subprocess_calls.append(node.lineno)
        if isinstance(node.func, ast.Name) and node.func.id in {
            "http_get",
            "http_post_raw",
            "Server",
        }:
            forbidden_calls.append({"line": node.lineno, "name": node.func.id})
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"start", "stop"}
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in {"server", "w", "w2", "c883"}
        ):
            forbidden_calls.append({"line": node.lineno, "name": node.func.attr})

    checks = {
        "attempt_id_bound": (
            module.EXPECTED_ATTEMPT
            == "logical-prefix-kv-segmentation-control-20260922-6802c20c"
        ),
        "request_sha256_are_64_lower_hex": all(
            re.fullmatch(r"[0-9a-f]{64}", value)
            for value in (module.EXPECTED_W_SHA, module.EXPECTED_C883_SHA)
        ),
        "correct_c883_sha_bound": (
            module.EXPECTED_C883_SHA
            == "1e490f609ac0b844521784cd4603ea79a9c5ab0b199117e4395c4a8cf2efa47c"
        ),
        "three_requests_bound": module.EXPECTED_REQUESTS == ("W", "W2", "C883"),
        "three_dumps_bound": module.EXPECTED_DUMPS == (
            "W-P512", "W2-P512", "C883-P512"
        ),
        "no_subprocess_transitions": len(subprocess_calls) == 0,
        "no_http_or_server_calls": len(forbidden_calls) == 0,
        "imports_runner_read_only": (
            "load_runner()" in source
            and "runner.require_dump" in source
            and "runner.compare_three_dumps" in source
            and "runner.api_compare" in source
        ),
        "requires_consumed_incomplete_terminal": (
            '"PROBE_EXERCISED_INCOMPLETE"' in source
            and 'terminal.get("measured_attempt_consumed") is True' in source
            and 'terminal.get("rerun_authorized") is False' in source
        ),
        "requires_exact_failure_signature": all(
            name in source for name in ("WR-P512", "WR-R512", "WR2-P512", "C-P512")
        ),
        "validates_request_http_timings": all(
            token in source
            for token in (
                'http.get("status"), 200',
                'timings.get("cache_n"), 0',
                'timings.get("prompt_n"), 883',
                'timings.get("predicted_n"), 1',
            )
        ),
        "validates_each_dump": "runner.require_dump(kv_root, name)" in source,
        "three_point_geometry_only": (
            "require_three_point_geometry" in source
            and "EXPECTED_DUMPS" in source
        ),
        "posthoc_success_terminal": (
            '"SEGMENTATION_CONTROL_POSTHOC_RECONCILED"' in source
        ),
        "posthoc_failure_terminal": (
            '"SEGMENTATION_CONTROL_POSTHOC_NOT_RECONCILED"' in source
        ),
        "zero_runtime_counters_recorded": all(
            token in source
            for token in (
                '"model_calls": 0',
                '"server_startups": 0',
                '"gpu_guard_acquisitions": 0',
                '"http_requests": 0',
                '"subprocess_transitions": 0',
            )
        ),
        "measured_attempt_stays_consumed": (
            '"measured_attempt_remains_consumed": True' in source
            and '"rerun_authorized": False' in source
        ),
        "does_not_write_measured_root_terminal": (
            'write_json(args.measured_root / "terminal.json"' not in source
        ),
    }

    errors = [name for name, ok in checks.items() if not ok]
    out = {
        "status": (
            "SEGMENTATION_CONTROL_POSTHOC_SELFTEST_PASS"
            if not errors
            else "SEGMENTATION_CONTROL_POSTHOC_SELFTEST_FAIL"
        ),
        "checks": checks,
        "subprocess_calls": subprocess_calls,
        "forbidden_calls": forbidden_calls,
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

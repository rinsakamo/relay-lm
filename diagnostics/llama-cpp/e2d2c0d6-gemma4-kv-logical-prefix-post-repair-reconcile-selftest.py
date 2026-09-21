#!/usr/bin/env python3
import ast
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-kv-logical-prefix-post-repair-reconcile.py"


def load_target():
    spec = importlib.util.spec_from_file_location("post_repair_reconcile_contract", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load post-repair reconciliation helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    module = load_target()
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)

    subprocess_runs = []
    subprocess_run_args = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
            and node.func.attr == "run"
        ):
            subprocess_runs.append(node.lineno)
            if node.args and isinstance(node.args[0], ast.Name):
                subprocess_run_args.append(node.args[0].id)
            else:
                subprocess_run_args.append(None)

    git_object_ids = [
        module.EXPECTED_SOURCE_HEAD,
        module.EXPECTED_SOURCE_TREE,
    ]
    frozen_sha256 = [
        module.EXPECTED_MODEL_SHA,
        module.CONSUMED_SERVER_SHA,
        *module.EXPECTED_REQUESTS.values(),
    ]

    checks = {
        "git_object_ids_are_40_lower_hex": all(
            re.fullmatch(r"[0-9a-f]{40}", value)
            for value in git_object_ids
        ),
        "all_frozen_sha256_are_64_lower_hex": all(
            re.fullmatch(r"[0-9a-f]{64}", value)
            for value in frozen_sha256
        ),
        "correct_l0_sha_bound": (
            module.EXPECTED_REQUESTS["L0"]
            == "9120aed18e9aac20615cab2de00337eb9bf65edeb7249015c97d3c41d881e38d"
        ),
        "consumed_server_rejected": (
            "new server equals consumed server SHA" in source
        ),
        "only_one_subprocess_transition": len(subprocess_runs) == 1,
        "only_request_admission_subprocess": (
            len(subprocess_runs) == 1
            and subprocess_run_args == ["cmd"]
            and "e2d2c0d6-gemma4-kv-request-admission.py" in source
            and "subprocess.Popen" not in source
        ),
        "success_is_non_authorizing": (
            '"measured_execution_authorized_by_this_result": False' in source
        ),
        "zero_runtime_counters_recorded": (
            '"generated_requests": 0' in source
            and '"model_loads": 0' in source
            and '"server_startups": 0' in source
            and '"measured_l0_submitted": False' in source
            and '"measured_attempt_consumed": False' in source
        ),
        "requires_premeasured_ready": (
            "LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY" in source
        ),
        "requires_binary_preflight_pass": (
            "LOGICAL_PREFIX_BINARY_PREFLIGHT_PASS" in source
        ),
        "requires_startup_qualified": (
            "LOGICAL_PREFIX_STARTUP_QUALIFIED" in source
        ),
        "requires_request_admission_pass": (
            "REQUEST_ADMISSION_PASS" in source
        ),
    }

    errors = [name for name, ok in checks.items() if not ok]
    out = {
        "status": (
            "LOGICAL_PREFIX_POST_REPAIR_RECONCILE_SELFTEST_PASS"
            if not errors
            else "LOGICAL_PREFIX_POST_REPAIR_RECONCILE_SELFTEST_FAIL"
        ),
        "checks": checks,
        "subprocess_run_lines": subprocess_runs,
        "subprocess_run_args": subprocess_run_args,
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

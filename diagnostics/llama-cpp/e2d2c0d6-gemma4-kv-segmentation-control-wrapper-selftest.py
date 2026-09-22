#!/usr/bin/env python3
import ast
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-kv-segmentation-control-execute-once.py"


def load_target():
    spec = importlib.util.spec_from_file_location("segmentation_control_execute_once_contract", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load segmentation-control execute-once wrapper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    wrapper = load_target()
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)

    subprocess_runs = []
    guard_cmd_runs = []
    runner_cmd_runs = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
            and node.func.attr == "run"
        ):
            continue
        arg = node.args[0] if node.args else None
        name = arg.id if isinstance(arg, ast.Name) else None
        subprocess_runs.append({"line": node.lineno, "arg_name": name})
        if name == "guard_cmd":
            guard_cmd_runs.append(node.lineno)
        if name == "runner_cmd":
            runner_cmd_runs.append(node.lineno)

    frozen_sha256 = [
        wrapper.EXPECTED_SERVER_SHA,
        wrapper.EXPECTED_SERVER_IMPL_SHA,
        wrapper.EXPECTED_LLAMA_SHA,
        wrapper.EXPECTED_MODEL_SHA,
        wrapper.EXPECTED_ALIGNED_PATCH_SHA,
        wrapper.EXPECTED_LOGICAL_PATCH_SHA,
        wrapper.EXPECTED_APPLIED_PATCH_SHA,
        wrapper.EXPECTED_STARTUP_ARGV_SHA,
        *wrapper.EXPECTED_CONTROL_SHA256.values(),
    ]

    checks = {
        "authority_generation_bound": (
            wrapper.AUTHORITY_GENERATION
            == "logical-prefix-kv-segmentation-control-measured-authority-20260922-6802c20c-c883sha64"
        ),
        "attempt_id_bound": (
            wrapper.ATTEMPT_ID
            == "logical-prefix-kv-segmentation-control-20260922-6802c20c"
        ),
        "premeasured_root_bound": (
            str(wrapper.PREMEASURED_ROOT)
            == "/tmp/relaylm-segmentation-control-qual.UsVe3A/output"
        ),
        "parent_fixture_bound": (
            wrapper.FIXTURE_REPO_PATH
            == "diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2"
            and wrapper.EXPECTED_FIXTURE_COMMIT
            == "58d3c1e9b8cf973648be1aeb8a8b12429a69d088"
            and wrapper.EXPECTED_FIXTURE_SUBTREE
            == "455d94850515c70995addc6c1c446ba738a01474"
        ),
        "control_fixture_bound": (
            wrapper.CONTROL_REPO_PATH
            == "diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2-segmentation-control"
            and wrapper.EXPECTED_CONTROL_COMMIT
            == "ccf9e78a89d170ae43e6ccfa6aa0788bd9a6cacc"
            and wrapper.EXPECTED_CONTROL_SUBTREE
            == "ac26ba25c3b88cbd9586ec009eeefe66004e2cb5"
        ),
        "all_frozen_sha256_are_64_lower_hex": all(
            re.fullmatch(r"[0-9a-f]{64}", value)
            for value in frozen_sha256
        ),
        "git_ids_are_40_lower_hex": all(
            re.fullmatch(r"[0-9a-f]{40}", value)
            for value in (
                wrapper.EXPECTED_FIXTURE_COMMIT,
                wrapper.EXPECTED_FIXTURE_SUBTREE,
                wrapper.EXPECTED_CONTROL_COMMIT,
                wrapper.EXPECTED_CONTROL_SUBTREE,
            )
        ),
        "fresh_runtime_closure_bound": (
            wrapper.EXPECTED_SERVER_SHA
            == "6802c20c27073fd0ec4640808aa89586d9261b1775c07c0a01761e3a6169f95a"
            and wrapper.EXPECTED_SERVER_IMPL_SHA
            == "960a1e8ef9b49ac06898737bef8148d5ab680eb8f2062d35c289d797b631f17b"
            and wrapper.EXPECTED_LLAMA_SHA
            == "3cb5756febc27493f88b29373ed0274885bdb7a411163d6af24d430e0d57c463"
        ),
        "startup_identity_bound": (
            wrapper.EXPECTED_STARTUP_ARGV_SHA
            == "9ee42d8effe614d5ab9827c35c2bde820478ffa0626099b3b0f944e7c51519c8"
            and wrapper.EXPECTED_BASE_KV == 8192
            and wrapper.EXPECTED_SWA_KV == 1536
        ),
        "parent_and_control_ancestry_checks_present": (
            "EXPECTED_FIXTURE_COMMIT" in source
            and "EXPECTED_CONTROL_COMMIT" in source
            and '"merge-base"' in source
            and '"--is-ancestor"' in source
        ),
        "parent_and_control_subtree_readback_present": (
            "FIXTURE_REPO_PATH" in source
            and "CONTROL_REPO_PATH" in source
            and '"rev-parse"' in source
        ),
        "parent_admission_present": (
            "e2d2c0d6-gemma4-kv-fixture-v2-admission.py" in source
            and "LOGICAL_PREFIX_FIXTURE_V2_ADMISSION_PASS" in source
        ),
        "control_file_sha_validation_present": (
            "EXPECTED_CONTROL_SHA256" in source
            and "control fixture file set" in source
        ),
        "control_segmentation_validation_present": (
            '"first_decode_tokens": 371' in source
            and '"second_decode_tokens": 508' in source
            and '"final_decode_tokens": 4' in source
            and '"logical_position_511_decode_ordinal": 2' in source
        ),
        "runner_selftest_present": (
            "e2d2c0d6-gemma4-kv-segmentation-control-measured-runner-selftest.py"
            in source
            and "LOGICAL_PREFIX_SEGMENTATION_CONTROL_RUNNER_SELFTEST_PASS"
            in source
        ),
        "canonical_resource_guard_used": (
            "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py" in source
        ),
        "exactly_one_guard_child_transition": len(guard_cmd_runs) == 1,
        "no_direct_runner_transition": len(runner_cmd_runs) == 0,
        "pre_w_failure_is_not_exercised": "PROBE_NOT_EXERCISED" in source,
        "missing_terminal_uses_w_record": (
            'server-W" / "W.request.json"' in source
            and "w_request_record_exists" in source
        ),
        "consumed_fallback_present": (
            "PROBE_EXERCISED_INCOMPLETE" in source
            and '"rerun_authorized": False if w_attempted else None' in source
        ),
        "campaign_separation_recorded": (
            "campaign_queue_receipt_created" in source
            and "campaign_queue_or_spend_artifact_touched" in source
        ),
        "prior_measured_entrypoint_absent": (
            "e2d2c0d6-gemma4-kv-fixture-v2-execute-once.py" not in source
            and "e2d2c0d6-gemma4-kv-fixture-v2-measured-run.py" not in source
        ),
        "prior_runtime_server_absent": (
            "f6b671417ac9b6c7b4e00da95980caf828b8d63133ca61fdad60153b67a39e22"
            not in source
        ),
    }

    errors = [name for name, ok in checks.items() if not ok]
    out = {
        "status": (
            "LOGICAL_PREFIX_SEGMENTATION_CONTROL_WRAPPER_SELFTEST_PASS"
            if not errors
            else "LOGICAL_PREFIX_SEGMENTATION_CONTROL_WRAPPER_SELFTEST_FAIL"
        ),
        "checks": checks,
        "subprocess_runs": subprocess_runs,
        "guard_cmd_run_lines": guard_cmd_runs,
        "runner_cmd_run_lines": runner_cmd_runs,
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

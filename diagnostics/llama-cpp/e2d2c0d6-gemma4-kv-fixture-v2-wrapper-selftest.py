#!/usr/bin/env python3
import ast
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-kv-fixture-v2-execute-once.py"


def load_target():
    spec = importlib.util.spec_from_file_location("fixture_v2_execute_once_contract", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load fixture-v2 execute-once wrapper")
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
    ]

    checks = {
        "authority_generation_bound": (
            wrapper.AUTHORITY_GENERATION
            == "logical-prefix-kv-fixture-v2-measured-authority-20260922-f6b67141"
        ),
        "attempt_id_bound": (
            wrapper.ATTEMPT_ID
            == "logical-prefix-kv-fixture-v2-20260922-f6b67141"
        ),
        "premeasured_root_bound": (
            str(wrapper.PREMEASURED_ROOT)
            == "/tmp/relaylm-kv-v2-premeasured.kq8VQ5/output"
        ),
        "fixture_repo_path_bound": (
            wrapper.FIXTURE_REPO_PATH
            == "diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2"
        ),
        "fixture_subtree_bound": (
            wrapper.EXPECTED_FIXTURE_SUBTREE
            == "455d94850515c70995addc6c1c446ba738a01474"
        ),
        "all_frozen_sha256_are_64_lower_hex": all(
            re.fullmatch(r"[0-9a-f]{64}", value)
            for value in frozen_sha256
        ),
        "fixture_subtree_is_40_lower_hex": (
            re.fullmatch(r"[0-9a-f]{40}", wrapper.EXPECTED_FIXTURE_SUBTREE)
            is not None
        ),
        "new_runtime_closure_bound": (
            wrapper.EXPECTED_SERVER_SHA
            == "f6b671417ac9b6c7b4e00da95980caf828b8d63133ca61fdad60153b67a39e22"
            and wrapper.EXPECTED_SERVER_IMPL_SHA
            == "7456ded50dca4f6ad5f53dd9e178d16954e2c9134ee912c5ea8ed3760db3735a"
            and wrapper.EXPECTED_LLAMA_SHA
            == "178b81207d10e053490627e2755a61069ae912053cf0abcffa258989bac0528e"
        ),
        "startup_identity_bound": (
            wrapper.EXPECTED_STARTUP_ARGV_SHA
            == "5d9d486e67aa19e1b26ff00c33f50c30b57a41788c212bcccc2ab0bf4f992706"
            and wrapper.EXPECTED_BASE_KV == 8192
            and wrapper.EXPECTED_SWA_KV == 1536
        ),
        "fixture_subtree_git_readback_present": (
            'f"HEAD:{FIXTURE_REPO_PATH}"' in source
            and "git" in source
            and "rev-parse" in source
        ),
        "fixture_v2_admission_present": (
            "e2d2c0d6-gemma4-kv-fixture-v2-admission.py" in source
            and "LOGICAL_PREFIX_FIXTURE_V2_ADMISSION_PASS" in source
        ),
        "runner_selftest_present": (
            "e2d2c0d6-gemma4-kv-fixture-v2-measured-runner-selftest.py"
            in source
            and "LOGICAL_PREFIX_FIXTURE_V2_RUNNER_SELFTEST_PASS"
            in source
        ),
        "canonical_resource_guard_used": (
            "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py" in source
        ),
        "exactly_one_guard_child_transition": len(guard_cmd_runs) == 1,
        "no_direct_runner_transition": len(runner_cmd_runs) == 0,
        "pre_l0_failure_is_not_exercised": "PROBE_NOT_EXERCISED" in source,
        "missing_terminal_uses_l0_record": (
            'server-WR" / "L0.request.json"' in source
            and "l0_request_record_exists" in source
        ),
        "consumed_fallback_present": (
            "PROBE_EXERCISED_INCOMPLETE" in source
            and '"rerun_authorized": False if l0_attempted else None' in source
        ),
        "campaign_separation_recorded": (
            "campaign_queue_receipt_created" in source
            and "campaign_queue_or_spend_artifact_touched" in source
        ),
        "historical_request_root_absent": (
            "logical-prefix-request-id.JWuNTY" not in source
        ),
        "historical_consumed_server_absent": (
            "30d3f94f7335821a74828c243ab1dd315df9dc7a4c6df0cdff2f3ce1629dbaff"
            not in source
        ),
    }

    errors = [name for name, ok in checks.items() if not ok]
    out = {
        "status": (
            "LOGICAL_PREFIX_FIXTURE_V2_WRAPPER_SELFTEST_PASS"
            if not errors
            else "LOGICAL_PREFIX_FIXTURE_V2_WRAPPER_SELFTEST_FAIL"
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

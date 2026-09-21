#!/usr/bin/env python3
import ast
import importlib.util
import json
import re
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
WRAPPER_PATH = HERE / "e2d2c0d6-gemma4-kv-logical-prefix-replacement-execute-once.py"


def load_wrapper():
    spec = importlib.util.spec_from_file_location(
        "logical_prefix_replacement_execute_once_contract",
        WRAPPER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load replacement execute-once wrapper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    wrapper = load_wrapper()
    source = WRAPPER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    guard_run_calls = []
    direct_runner_runs = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
            and node.func.attr == "run"
        ):
            arg = node.args[0] if node.args else None
            if isinstance(arg, ast.Name) and arg.id == "guard_cmd":
                guard_run_calls.append(node.lineno)
            if isinstance(arg, ast.Name) and arg.id == "runner_cmd":
                direct_runner_runs.append(node.lineno)

    frozen_sha_values = [
        wrapper.EXPECTED_SERVER_SHA,
        wrapper.EXPECTED_SERVER_IMPL_SHA,
        wrapper.EXPECTED_LLAMA_SHA,
        wrapper.EXPECTED_MODEL_SHA,
        wrapper.EXPECTED_ALIGNED_PATCH_SHA,
        wrapper.EXPECTED_LOGICAL_PATCH_SHA,
        wrapper.EXPECTED_APPLIED_PATCH_SHA,
        *wrapper.EXPECTED_INPUTS.values(),
    ]

    checks = {
        "all_frozen_sha256_are_64_lower_hex": all(
            re.fullmatch(r"[0-9a-f]{64}", value)
            for value in frozen_sha_values
        ),
        "authority_generation_bound": (
            wrapper.AUTHORITY_GENERATION
            == "logical-prefix-kv-replacement-measured-authority-20260921-l0sha64"
        ),
        "attempt_id_bound": (
            wrapper.ATTEMPT_ID
            == "logical-prefix-kv-replacement-20260921-30d3f94f"
        ),
        "premeasured_root_bound": (
            str(wrapper.PREMEASURED_ROOT)
            == "/tmp/relaylm-logical-prefix-premeasured.4BYIKs/output"
        ),
        "request_reconciliation_root_bound": (
            str(wrapper.REQUEST_RECONCILIATION_ROOT)
            == "/tmp/relaylm-logical-prefix-request-id.JWuNTY/reconciliation"
        ),
        "server_sha_bound": (
            wrapper.EXPECTED_SERVER_SHA
            == "30d3f94f7335821a74828c243ab1dd315df9dc7a4c6df0cdff2f3ce1629dbaff"
        ),
        "server_impl_sha_bound": (
            wrapper.EXPECTED_SERVER_IMPL_SHA
            == "e6003c1e1a1c1c16dc5a09da485517eec6b6010d17f198acd34981075c14a64c"
        ),
        "llama_sha_bound": (
            wrapper.EXPECTED_LLAMA_SHA
            == "53228c024c04bd4a1acefa03d9ddc602cdfc78b5214d7fb7da13de458d2a2965"
        ),
        "model_sha_bound": (
            wrapper.EXPECTED_MODEL_SHA
            == "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
        ),
        "all_request_sha_bound": wrapper.EXPECTED_INPUTS == {
            "warm_tokens": "c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2",
            "target_tokens": "549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e",
            "L0": "9120aed18e9aac20615cab2de00337eb9bf65edeb7249015c97d3c41d881e38d",
            "L1": "d4deaa365324c5ca3c42eba4e6db9defe957a1cf06bbc08e9d3a01ba94ec0d1f",
            "LC": "284630a2f90e364b5dd336d3d9fadc59ddd0fa072fbac7cc825200bef2e7af52",
        },
        "replacement_runner_only": (
            "e2d2c0d6-gemma4-kv-logical-prefix-replacement-measured-run.py"
            in source
            and "e2d2c0d6-gemma4-kv-prefix-provenance-run.py" not in source
        ),
        "canonical_resource_guard_used": (
            "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py" in source
        ),
        "one_guard_child_transition": len(guard_run_calls) == 1,
        "no_direct_runner_transition": len(direct_runner_runs) == 0,
        "premeasured_terminal_required": (
            "LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY" in source
        ),
        "request_terminal_required": (
            "LOGICAL_PREFIX_REQUEST_IDENTITY_RECONCILED" in source
        ),
        "pre_l0_failure_classification": "PROBE_NOT_EXERCISED" in source,
        "campaign_separation_recorded": (
            "campaign_queue_receipt_created" in source
            and "campaign_queue_or_spend_artifact_touched" in source
        ),
        "missing_terminal_uses_l0_request_record": (
            'server-WR" / "L0.request.json"' in source
            and '"PROBE_EXERCISED_INCOMPLETE"' in source
            and '"l0_request_record_exists"' in source
        ),
        "consumed_fallback_forbids_rerun": (
            '"rerun_authorized": False if l0_attempted else None' in source
        ),
    }

    errors = [name for name, ok in checks.items() if not ok]
    out = {
        "status": (
            "LOGICAL_PREFIX_REPLACEMENT_WRAPPER_SELFTEST_PASS"
            if not errors
            else "LOGICAL_PREFIX_REPLACEMENT_WRAPPER_SELFTEST_FAIL"
        ),
        "checks": checks,
        "guard_run_lines": guard_run_calls,
        "direct_runner_run_lines": direct_runner_runs,
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

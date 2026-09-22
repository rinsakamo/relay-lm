#!/usr/bin/env python3
import ast
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-kv-segmentation-control-measured-run.py"


def load_target():
    spec = importlib.util.spec_from_file_location("segmentation_control_runner_contract", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load segmentation-control measured runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    runner = load_target()
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)

    parent_dir, parent_evidence, parent_manifest = runner.require_fixture(HERE)
    control_dir, control_evidence, control_manifest = runner.require_control_fixture(HERE)

    popen_calls = []
    subprocess_runs = []
    cli_options = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
            ):
                if node.func.attr == "Popen":
                    popen_calls.append(node.lineno)
                if node.func.attr == "run":
                    subprocess_runs.append(node.lineno)
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                cli_options.append(node.args[0].value)

    frozen_sha256 = [
        runner.EXPECTED_SERVER_SHA,
        runner.EXPECTED_SERVER_IMPL_SHA,
        runner.EXPECTED_LLAMA_SHA,
        runner.EXPECTED_MODEL_SHA,
        *runner.EXPECTED_FIXTURE_SHA256.values(),
        *runner.EXPECTED_CONTROL_SHA256.values(),
    ]
    git_ids = [
        runner.EXPECTED_FIXTURE_SUBTREE,
        runner.EXPECTED_CONTROL_SUBTREE,
        *runner.EXPECTED_FIXTURE_BLOBS.values(),
        *runner.EXPECTED_CONTROL_BLOBS.values(),
    ]

    sequence_positions = [
        source.find('submitted_requests.append("W")'),
        source.find('submitted_requests.append("W2")'),
        source.find('submitted_requests.append("C883")'),
    ]

    control_geometry = control_manifest.get("geometry", {})
    segmentation = control_manifest.get("expected_prompt_segmentation", {})

    checks = {
        "attempt_id_bound": (
            runner.ATTEMPT_ID
            == "logical-prefix-kv-segmentation-control-20260922-6802c20c"
        ),
        "all_frozen_sha256_are_64_lower_hex": all(
            re.fullmatch(r"[0-9a-f]{64}", value)
            for value in frozen_sha256
        ),
        "fixture_git_ids_are_40_lower_hex": all(
            re.fullmatch(r"[0-9a-f]{40}", value)
            for value in git_ids
        ),
        "fresh_runtime_closure_bound": (
            runner.EXPECTED_SERVER_SHA
            == "6802c20c27073fd0ec4640808aa89586d9261b1775c07c0a01761e3a6169f95a"
            and runner.EXPECTED_SERVER_IMPL_SHA
            == "960a1e8ef9b49ac06898737bef8148d5ab680eb8f2062d35c289d797b631f17b"
            and runner.EXPECTED_LLAMA_SHA
            == "3cb5756febc27493f88b29373ed0274885bdb7a411163d6af24d430e0d57c463"
        ),
        "parent_fixture_exact": (
            len(parent_evidence) == 9
            and parent_manifest.get("geometry", {}).get("warm_len") == 883
        ),
        "control_fixture_exact": (
            len(control_evidence) == 3
            and control_geometry.get("warm_len") == 883
            and control_geometry.get("control_len") == 883
            and control_geometry.get("lcp") == 865
        ),
        "segmentation_equalized": segmentation == {
            "n_batch": 512,
            "n_ubatch": 512,
            "total_tokens": 883,
            "first_decode_tokens": 371,
            "second_decode_tokens": 508,
            "final_decode_tokens": 4,
            "logical_position_511_decode_ordinal": 2,
        },
        "measurement_cli_is_narrow": sorted(cli_options) == sorted([
            "--server-bin",
            "--model",
            "--out-root",
            "--port-w",
            "--port-w2",
            "--port-c883",
        ]),
        "three_request_order_exact": (
            all(position >= 0 for position in sequence_positions)
            and sequence_positions == sorted(sequence_positions)
        ),
        "one_server_popen_site": len(popen_calls) == 1,
        "no_runtime_subprocess_comparator": len(subprocess_runs) == 0,
        "flash_attention_on": '"--flash-attn", "on"' in source,
        "logical_batch_512": (
            '"--batch-size", "512"' in source
            and '"--ubatch-size", "512"' in source
        ),
        "no_context_shift": '"--no-context-shift"' in source,
        "required_dump_points_present": all(
            name in source
            for name in ("W-P512", "W2-P512", "C883-P512")
        ),
        "three_terminal_classifications_present": all(
            name in source
            for name in (
                "SEGMENTATION_CONTROL_WARM_NOT_REPRODUCIBLE",
                "SEGMENTATION_CONTROL_KV_IDENTICAL",
                "SEGMENTATION_CONTROL_KV_DIFFERS",
            )
        ),
        "consumption_record_precedes_post": (
            source.find('send_request(w, "W"')
            > source.find('measured_w = True')
        ),
        "consumed_incomplete_semantics_present": (
            "PROBE_EXERCISED_INCOMPLETE" in source
            and '"rerun_authorized": False if measured_w else None' in source
        ),
        "all_terminals_non_authorizing": (
            source.count('"measured_execution_authorized_by_this_result": False') >= 2
        ),
        "prior_consumed_attempt_absent": (
            "logical-prefix-kv-fixture-v2-20260922-f6b67141" not in source
        ),
        "prior_runtime_server_absent": (
            "f6b671417ac9b6c7b4e00da95980caf828b8d63133ca61fdad60153b67a39e22"
            not in source
        ),
    }

    errors = [name for name, ok in checks.items() if not ok]
    out = {
        "status": (
            "LOGICAL_PREFIX_SEGMENTATION_CONTROL_RUNNER_SELFTEST_PASS"
            if not errors
            else "LOGICAL_PREFIX_SEGMENTATION_CONTROL_RUNNER_SELFTEST_FAIL"
        ),
        "checks": checks,
        "parent_fixture_directory": str(parent_dir),
        "control_fixture_directory": str(control_dir),
        "control_geometry": control_geometry,
        "segmentation": segmentation,
        "cli_options": cli_options,
        "popen_lines": popen_calls,
        "subprocess_run_lines": subprocess_runs,
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

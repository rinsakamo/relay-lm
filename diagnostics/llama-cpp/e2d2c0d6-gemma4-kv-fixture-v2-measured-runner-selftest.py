#!/usr/bin/env python3
import ast
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-kv-fixture-v2-measured-run.py"


def load_target():
    spec = importlib.util.spec_from_file_location("fixture_v2_measured_runner_contract", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load fixture-v2 measured runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    runner = load_target()
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)

    fixture_dir, fixture_evidence, manifest = runner.require_fixture(HERE)
    geometry = manifest.get("geometry", {})

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
    ]
    git_blobs = [
        runner.EXPECTED_FIXTURE_SUBTREE,
        *runner.EXPECTED_FIXTURE_BLOBS.values(),
    ]

    sequence_positions = [
        source.find('submitted_requests.append("L0")'),
        source.find('submitted_requests.append("L1")'),
        source.find('submitted_requests.append("L0R")'),
        source.find('submitted_requests.append("LC")'),
    ]

    checks = {
        "attempt_id_bound": (
            runner.ATTEMPT_ID
            == "logical-prefix-kv-fixture-v2-20260922-f6b67141"
        ),
        "all_frozen_sha256_are_64_lower_hex": all(
            re.fullmatch(r"[0-9a-f]{64}", value)
            for value in frozen_sha256
        ),
        "fixture_git_ids_are_40_lower_hex": all(
            re.fullmatch(r"[0-9a-f]{40}", value)
            for value in git_blobs
        ),
        "new_runtime_closure_bound": (
            runner.EXPECTED_SERVER_SHA
            == "f6b671417ac9b6c7b4e00da95980caf828b8d63133ca61fdad60153b67a39e22"
            and runner.EXPECTED_SERVER_IMPL_SHA
            == "7456ded50dca4f6ad5f53dd9e178d16954e2c9134ee912c5ea8ed3760db3735a"
            and runner.EXPECTED_LLAMA_SHA
            == "178b81207d10e053490627e2755a61069ae912053cf0abcffa258989bac0528e"
        ),
        "fixture_subtree_bound": (
            runner.EXPECTED_FIXTURE_SUBTREE
            == "455d94850515c70995addc6c1c446ba738a01474"
        ),
        "fixture_directory_fixed": (
            str(runner.FIXTURE_RELATIVE)
            == "fixtures/e2d2c0d6-gemma4-kv-v2"
        ),
        "fixture_file_set_exact": (
            sorted(fixture_evidence)
            == sorted(runner.EXPECTED_FIXTURE_SHA256)
            and len(fixture_evidence) == 9
        ),
        "fixture_geometry_exact": (
            geometry.get("warm_len") == 883
            and geometry.get("target_len") == 2927
            and geometry.get("lcp") == 865
            and geometry.get("target_suffix_source_offset") == 883
        ),
        "fixture_v2_admission_used": (
            "e2d2c0d6-gemma4-kv-fixture-v2-admission.py" in source
        ),
        "no_request_path_cli": not any(
            option in cli_options
            for option in (
                "--warm-tokens",
                "--target-tokens",
                "--l0-request",
                "--l1-request",
                "--lc-request",
            )
        ),
        "measurement_cli_is_narrow": sorted(cli_options) == sorted([
            "--server-bin",
            "--model",
            "--out-root",
            "--port-wr",
            "--port-wr2",
            "--port-c",
        ]),
        "four_request_order_exact": (
            all(position >= 0 for position in sequence_positions)
            and sequence_positions == sorted(sequence_positions)
        ),
        "one_server_popen_site": len(popen_calls) == 1,
        "admission_and_comparator_subprocess_sites": len(subprocess_runs) == 2,
        "flash_attention_on": '"--flash-attn", "on"' in source,
        "logical_batch_512": (
            '"--batch-size", "512"' in source
            and '"--ubatch-size", "512"' in source
        ),
        "no_context_shift": '"--no-context-shift"' in source,
        "required_dump_points_present": all(
            name in source
            for name in ("WR-P512", "WR-R512", "WR2-P512", "C-P512")
        ),
        "all_four_terminal_classifications_present": all(
            name in source
            for name in (
                "PREFIX_DUMP_NOT_REPRODUCIBLE",
                "PREFIX_KV_GENERATION_DIFFERS",
                "RETAINED_PREFIX_KV_MUTATED_BY_REUSE",
                "PREFIX_KV_IDENTICAL_THROUGH_REUSE",
            )
        ),
        "consumed_incomplete_semantics_present": (
            "PROBE_EXERCISED_INCOMPLETE" in source
            and '"rerun_authorized": False if measured_l0 else None' in source
        ),
        "historical_attempt_absent": (
            "logical-prefix-kv-replacement-20260921-30d3f94f" not in source
        ),
        "historical_request_sha_absent": (
            "9120aed18e9aac20615cab2de00337eb9bf65edeb7249015c97d3c41d881e38d"
            not in source
        ),
        "consumed_server_sha_absent": (
            "30d3f94f7335821a74828c243ab1dd315df9dc7a4c6df0cdff2f3ce1629dbaff"
            not in source
        ),
    }

    errors = [name for name, ok in checks.items() if not ok]
    out = {
        "status": (
            "LOGICAL_PREFIX_FIXTURE_V2_RUNNER_SELFTEST_PASS"
            if not errors
            else "LOGICAL_PREFIX_FIXTURE_V2_RUNNER_SELFTEST_FAIL"
        ),
        "checks": checks,
        "fixture_directory": str(fixture_dir),
        "fixture_geometry": geometry,
        "cli_options": cli_options,
        "popen_lines": popen_calls,
        "subprocess_run_lines": subprocess_runs,
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

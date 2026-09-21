#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

AUTHORITY_GENERATION = "logical-prefix-kv-fixture-v2-measured-authority-20260922-f6b67141"
ATTEMPT_ID = "logical-prefix-kv-fixture-v2-20260922-f6b67141"
PREMEASURED_ROOT = Path("/tmp/relaylm-kv-v2-premeasured.kq8VQ5/output")
FIXTURE_REPO_PATH = "diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2"

EXPECTED_SOURCE_HEAD = "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"
EXPECTED_SOURCE_TREE = "6d39fd93dc91fc0a4bc86dffe9782d4f26318004"
EXPECTED_FIXTURE_SUBTREE = "455d94850515c70995addc6c1c446ba738a01474"
EXPECTED_SERVER_SHA = "f6b671417ac9b6c7b4e00da95980caf828b8d63133ca61fdad60153b67a39e22"
EXPECTED_SERVER_IMPL_SHA = "7456ded50dca4f6ad5f53dd9e178d16954e2c9134ee912c5ea8ed3760db3735a"
EXPECTED_LLAMA_SHA = "178b81207d10e053490627e2755a61069ae912053cf0abcffa258989bac0528e"
EXPECTED_MODEL_SHA = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
EXPECTED_ALIGNED_PATCH_SHA = "cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a"
EXPECTED_LOGICAL_PATCH_SHA = "d62810fdc645cbb011c52047e9ba9227b1d6c29fafc0bac0e7cf659f6104e4c8"
EXPECTED_APPLIED_PATCH_SHA = "2f3829164ae8dffce6054681fbcef3f674fb901d37a2ffc383a91f3c867f7737"
EXPECTED_STARTUP_ARGV_SHA = "5d9d486e67aa19e1b26ff00c33f50c30b57a41788c212bcccc2ab0bf4f992706"
EXPECTED_BASE_KV = 8192
EXPECTED_SWA_KV = 1536


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def require_equal(observed, expected, label):
    if observed != expected:
        raise RuntimeError(f"{label}: {observed!r} != {expected!r}")


def terminal_not_exercised(root: Path, stage: str, reason: str):
    value = {
        "authority_generation": AUTHORITY_GENERATION,
        "attempt_id": ATTEMPT_ID,
        "primary_classification": "PROBE_NOT_EXERCISED",
        "measured_l0_submitted": False,
        "measured_attempt_consumed": False,
        "measured_execution_authorized_by_this_result": False,
        "stage": stage,
        "reason": reason,
    }
    write_json(root / "terminal.json", value)
    return value


def validate_premeasured(root: Path, here: Path):
    top = load_json(root / "terminal.json")
    build = load_json(root / "build-stage" / "terminal.json")
    qual_root = root / "qualification-stage"
    qual = load_json(qual_root / "terminal.json")
    binary = load_json(qual_root / "logical-prefix-binary-preflight.json")
    startup = load_json(qual_root / "logical-prefix-startup-classification.json")
    guard = load_json(qual_root / "shared-resource-guard" / "guard.json")
    idle = load_json(qual_root / "shared-resource-guard" / "external-quiescence.json")

    require_equal(
        top.get("primary_classification"),
        "LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY",
        "top classification",
    )
    require_equal(top.get("generated_requests"), 0, "top generated_requests")
    require_equal(top.get("measured_l0_submitted"), False, "top measured_l0_submitted")
    require_equal(top.get("measured_attempt_consumed"), False, "top measured_attempt_consumed")
    require_equal(
        top.get("measured_execution_authorized_by_this_result"),
        False,
        "top measured authorization",
    )

    require_equal(
        build.get("primary_classification"),
        "LOGICAL_PREFIX_REPLACEMENT_BUILD_READY",
        "build classification",
    )
    require_equal(build.get("source_head"), EXPECTED_SOURCE_HEAD, "source head")
    require_equal(build.get("source_tree"), EXPECTED_SOURCE_TREE, "source tree")
    require_equal(build.get("server_sha256"), EXPECTED_SERVER_SHA, "build server SHA")
    require_equal(
        build.get("aligned_reuse_patch_sha256"),
        EXPECTED_ALIGNED_PATCH_SHA,
        "aligned patch SHA",
    )
    require_equal(
        build.get("logical_prefix_patch_sha256"),
        EXPECTED_LOGICAL_PATCH_SHA,
        "logical patch SHA",
    )
    require_equal(
        build.get("applied_patch_sha256"),
        EXPECTED_APPLIED_PATCH_SHA,
        "applied.patch SHA",
    )

    current_aligned = here / "e2d2c0d6-gemma4-swa-ubatch-aligned-reuse-diagnostic.patch"
    current_logical = here / "e2d2c0d6-gemma4-kv-logical-prefix-dump-diagnostic.patch"
    require(current_aligned.is_file(), "current aligned patch missing")
    require(current_logical.is_file(), "current logical-prefix patch missing")
    require_equal(sha256(current_aligned), EXPECTED_ALIGNED_PATCH_SHA, "live aligned patch SHA")
    require_equal(sha256(current_logical), EXPECTED_LOGICAL_PATCH_SHA, "live logical patch SHA")

    applied_patch = root / "build-stage" / "applied.patch"
    require(applied_patch.is_file(), "applied.patch missing")
    require_equal(sha256(applied_patch), EXPECTED_APPLIED_PATCH_SHA, "live applied.patch SHA")

    require_equal(
        binary.get("status"),
        "LOGICAL_PREFIX_BINARY_PREFLIGHT_PASS",
        "binary preflight",
    )
    require_equal(binary.get("server_sha256"), EXPECTED_SERVER_SHA, "binary server SHA")
    require_equal(binary.get("model_sha256"), EXPECTED_MODEL_SHA, "binary model SHA")
    require_equal(
        binary.get("aligned_reuse_patch_sha256"),
        EXPECTED_ALIGNED_PATCH_SHA,
        "binary aligned patch SHA",
    )
    require_equal(
        binary.get("logical_prefix_patch_sha256"),
        EXPECTED_LOGICAL_PATCH_SHA,
        "binary logical patch SHA",
    )
    require_equal(binary.get("forbidden_old_marker_present"), False, "forbidden old marker")

    artifacts = binary.get("runtime_artifacts")
    require(isinstance(artifacts, dict), "runtime_artifacts missing")
    expected_artifacts = {
        "llama_server": EXPECTED_SERVER_SHA,
        "llama_server_impl": EXPECTED_SERVER_IMPL_SHA,
        "llama": EXPECTED_LLAMA_SHA,
    }
    live_artifacts = {}
    for name, expected_sha in expected_artifacts.items():
        entry = artifacts.get(name)
        require(isinstance(entry, dict), f"runtime artifact missing: {name}")
        require_equal(entry.get("sha256"), expected_sha, f"recorded {name} SHA")
        require_equal(
            entry.get("forbidden_old_marker_present"),
            False,
            f"{name} forbidden marker",
        )
        path = Path(entry.get("path", ""))
        require(path.is_file(), f"runtime artifact file missing: {name}: {path}")
        require_equal(sha256(path), expected_sha, f"live {name} SHA")
        live_artifacts[name] = {
            "path": str(path),
            "resolved_path": str(path.resolve(strict=True)),
            "sha256": expected_sha,
        }

    markers = binary.get("required_runtime_markers")
    require(isinstance(markers, dict) and markers, "required marker map missing")
    for marker, entry in markers.items():
        require(entry.get("present") is True, f"required marker absent: {marker}")

    require_equal(
        qual.get("primary_classification"),
        "LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY",
        "qualification classification",
    )
    require_equal(qual.get("server_sha256"), EXPECTED_SERVER_SHA, "qualification server SHA")
    require_equal(qual.get("model_sha256"), EXPECTED_MODEL_SHA, "qualification model SHA")
    require_equal(qual.get("generated_requests"), 0, "qualification generated_requests")
    require_equal(qual.get("measured_l0_submitted"), False, "qualification L0")
    require_equal(qual.get("measured_attempt_consumed"), False, "qualification consumed")
    require_equal(
        qual.get("measured_execution_authorized_by_this_result"),
        False,
        "qualification authorization",
    )

    require_equal(
        startup.get("primary_classification"),
        "LOGICAL_PREFIX_STARTUP_QUALIFIED",
        "startup classification",
    )
    evidence = startup.get("evidence")
    require(isinstance(evidence, dict), "startup evidence missing")
    plain = evidence.get("plain")
    probe = evidence.get("probe")
    require(isinstance(plain, dict) and isinstance(probe, dict), "plain/probe evidence missing")
    require_equal(
        plain.get("argv_canonical_sha256"),
        EXPECTED_STARTUP_ARGV_SHA,
        "plain canonical argv SHA",
    )
    require_equal(
        probe.get("argv_canonical_sha256"),
        EXPECTED_STARTUP_ARGV_SHA,
        "probe canonical argv SHA",
    )

    for arm_name, arm in (("plain", plain), ("probe", probe)):
        checks = arm.get("context", {}).get("checks", {})
        require(checks and all(x.get("ok") is True for x in checks.values()), f"{arm_name} context checks")
        swa = arm.get("compact_swa", {})
        require(swa.get("ok") is True, f"{arm_name} compact SWA")
        require_equal(swa.get("selected_base_size"), EXPECTED_BASE_KV, f"{arm_name} base KV")
        require_equal(swa.get("selected_swa_size"), EXPECTED_SWA_KV, f"{arm_name} SWA KV")
        require_equal(arm.get("unexpected_probe_output"), False, f"{arm_name} unexpected probe output")

    require_equal(guard.get("resource_key"), "llama-cpp:local-gpu", "guard resource")
    require_equal(guard.get("lock_acquired"), True, "guard lock")
    require_equal(guard.get("child_invoked"), True, "guard child")
    require_equal(guard.get("child_returncode"), 0, "guard child rc")
    require_equal(
        guard.get("guard_state"),
        "RELEASED_CANONICAL_DIAGNOSTIC_FLOCK",
        "guard state",
    )
    require_equal(guard.get("campaign_queue_receipt_created"), False, "campaign receipt")
    require_equal(
        guard.get("campaign_queue_or_spend_artifact_touched"),
        False,
        "campaign state mutation",
    )
    require(isinstance(idle, list) and len(idle) == 2, "idle observations must equal two")
    for ordinal, observation in enumerate(idle, start=1):
        require_equal(observation.get("observation"), ordinal, f"idle ordinal {ordinal}")
        require_equal(observation.get("busy_processes"), [], f"idle busy processes {ordinal}")
        require_equal(
            observation.get("listener_127_0_0_1_1234"),
            False,
            f"idle listener {ordinal}",
        )

    server_bin = Path(build.get("server_binary", ""))
    require(server_bin.is_file(), f"qualified server binary missing: {server_bin}")
    require_equal(sha256(server_bin), EXPECTED_SERVER_SHA, "qualified live server SHA")

    return {
        "premeasured_root": str(root),
        "source_head": EXPECTED_SOURCE_HEAD,
        "source_tree": EXPECTED_SOURCE_TREE,
        "aligned_patch_sha256": EXPECTED_ALIGNED_PATCH_SHA,
        "logical_patch_sha256": EXPECTED_LOGICAL_PATCH_SHA,
        "applied_patch_sha256": EXPECTED_APPLIED_PATCH_SHA,
        "server_bin": str(server_bin),
        "server_sha256": EXPECTED_SERVER_SHA,
        "runtime_artifacts": live_artifacts,
        "model_sha256": EXPECTED_MODEL_SHA,
        "startup_argv_canonical_sha256": EXPECTED_STARTUP_ARGV_SHA,
        "base_kv": EXPECTED_BASE_KV,
        "swa_kv": EXPECTED_SWA_KV,
        "required_runtime_markers": markers,
        "resource_guard": guard,
        "external_quiescence": idle,
    }


def validate_fixture_checkout(here: Path, preflight_root: Path):
    repo_root = here.parent.parent
    fixture_dir = repo_root / FIXTURE_REPO_PATH
    require(fixture_dir.is_dir(), f"fixture directory missing: {fixture_dir}")

    git = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "rev-parse",
            f"HEAD:{FIXTURE_REPO_PATH}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    (preflight_root / "fixture-subtree.stdout.txt").write_text(git.stdout, encoding="utf-8")
    (preflight_root / "fixture-subtree.stderr.txt").write_text(git.stderr, encoding="utf-8")
    require_equal(git.returncode, 0, "fixture subtree git returncode")
    require_equal(git.stdout.strip(), EXPECTED_FIXTURE_SUBTREE, "fixture subtree")

    admission = here / "e2d2c0d6-gemma4-kv-fixture-v2-admission.py"
    require(admission.is_file(), "fixture-v2 admission helper missing")
    admission_out = preflight_root / "fixture-v2-admission.json"
    cmd = [
        sys.executable,
        str(admission),
        "--fixture-dir",
        str(fixture_dir),
        "--out",
        str(admission_out),
    ]
    write_json(preflight_root / "fixture-v2-admission.argv.json", cmd)
    run = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (preflight_root / "fixture-v2-admission.stdout.txt").write_bytes(run.stdout)
    (preflight_root / "fixture-v2-admission.stderr.txt").write_bytes(run.stderr)
    require_equal(run.returncode, 0, "fixture-v2 admission returncode")
    admitted = load_json(admission_out)
    require_equal(
        admitted.get("status"),
        "LOGICAL_PREFIX_FIXTURE_V2_ADMISSION_PASS",
        "fixture-v2 admission",
    )
    return {
        "repo_root": str(repo_root),
        "fixture_directory": str(fixture_dir),
        "fixture_subtree": EXPECTED_FIXTURE_SUBTREE,
        "admission": admitted,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--preflight-root", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--port-wr", type=int, required=True)
    ap.add_argument("--port-wr2", type=int, required=True)
    ap.add_argument("--port-c", type=int, required=True)
    args = ap.parse_args()

    if args.preflight_root.exists():
        raise SystemExit(f"preflight root must not exist: {args.preflight_root}")
    if args.out_root.exists():
        raise SystemExit(f"measured output root must not exist: {args.out_root}")
    if len({args.port_wr, args.port_wr2, args.port_c}) != 3:
        raise SystemExit("all measured ports must be distinct")

    args.preflight_root.mkdir(parents=True)
    here = Path(__file__).resolve().parent

    try:
        apparatus = validate_premeasured(PREMEASURED_ROOT, here)
        fixture = validate_fixture_checkout(here, args.preflight_root)
        require(args.model.is_file(), f"model missing: {args.model}")
        require_equal(sha256(args.model), EXPECTED_MODEL_SHA, "live model SHA")
    except Exception as exc:
        terminal_not_exercised(
            args.preflight_root,
            "authority_reconciliation",
            str(exc),
        )
        return 2

    runner = here / "e2d2c0d6-gemma4-kv-fixture-v2-measured-run.py"
    runner_selftest = here / "e2d2c0d6-gemma4-kv-fixture-v2-measured-runner-selftest.py"
    guard = here / "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py"
    guard_selftest = here / "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard-selftest.py"

    for required in (runner, runner_selftest, guard, guard_selftest):
        if not required.is_file():
            terminal_not_exercised(
                args.preflight_root,
                "helper_presence",
                f"required helper missing: {required}",
            )
            return 3

    tests = [
        (
            "fixture-v2-runner-selftest",
            runner_selftest,
            "LOGICAL_PREFIX_FIXTURE_V2_RUNNER_SELFTEST_PASS",
        ),
        (
            "resource-guard-selftest",
            guard_selftest,
            "LOGICAL_PREFIX_RESOURCE_GUARD_SELFTEST_PASS",
        ),
    ]
    for label, path, expected_status in tests:
        run = subprocess.run(
            [sys.executable, str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        (args.preflight_root / f"{label}.stdout.json").write_bytes(run.stdout)
        (args.preflight_root / f"{label}.stderr.txt").write_bytes(run.stderr)
        if run.returncode != 0:
            terminal_not_exercised(args.preflight_root, label, f"{label} failed")
            return 4
        try:
            obj = json.loads(run.stdout)
        except Exception as exc:
            terminal_not_exercised(
                args.preflight_root,
                label,
                f"invalid JSON: {exc}",
            )
            return 4
        if obj.get("status") != expected_status:
            terminal_not_exercised(
                args.preflight_root,
                label,
                f"unexpected status: {obj.get('status')}",
            )
            return 4

    identity = {
        "authority_generation": AUTHORITY_GENERATION,
        "attempt_id": ATTEMPT_ID,
        "fixture": fixture,
        "apparatus": apparatus,
        "model": str(args.model),
        "model_sha256": EXPECTED_MODEL_SHA,
        "ports": {
            "WR": args.port_wr,
            "WR2": args.port_wr2,
            "C": args.port_c,
        },
        "campaign_queue_receipt_created": False,
        "campaign_queue_or_spend_artifact_touched": False,
    }
    write_json(args.preflight_root / "bound-identity.json", identity)

    runner_cmd = [
        sys.executable,
        str(runner),
        "--server-bin",
        apparatus["server_bin"],
        "--model",
        str(args.model),
        "--out-root",
        str(args.out_root),
        "--port-wr",
        str(args.port_wr),
        "--port-wr2",
        str(args.port_wr2),
        "--port-c",
        str(args.port_c),
    ]
    write_json(args.preflight_root / "measured-runner.argv.json", runner_cmd)

    guard_root = args.preflight_root / "shared-resource-guard"
    guard_cmd = [
        sys.executable,
        str(guard),
        "--evidence-root",
        str(guard_root),
        "--",
        *runner_cmd,
    ]
    write_json(args.preflight_root / "guard.argv.json", guard_cmd)

    run = subprocess.run(
        guard_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (args.preflight_root / "guard.stdout.txt").write_bytes(run.stdout)
    (args.preflight_root / "guard.stderr.txt").write_bytes(run.stderr)

    measured_terminal = args.out_root / "terminal.json"
    if measured_terminal.is_file():
        terminal = load_json(measured_terminal)
    else:
        guard_obj = {}
        try:
            guard_obj = load_json(guard_root / "guard.json")
        except Exception:
            pass

        child_invoked = guard_obj.get("child_invoked") is True
        l0_record = args.out_root / "server-WR" / "L0.request.json"
        l0_attempted = l0_record.is_file()
        fallback = {
            "authority_generation": AUTHORITY_GENERATION,
            "attempt_id": ATTEMPT_ID,
            "primary_classification": (
                "PROBE_EXERCISED_INCOMPLETE"
                if l0_attempted
                else "PROBE_NOT_EXERCISED"
            ),
            "measured_l0_submitted": l0_attempted,
            "measured_attempt_consumed": l0_attempted,
            "measured_execution_authorized_by_this_result": False,
            "stage": "guard_or_child_terminal_fallback",
            "reason": (
                "measured runner exited without terminal.json; "
                "classification derived conservatively from pre-POST L0 request record"
                if child_invoked
                else "measured runner was not invoked"
            ),
            "guard_returncode": run.returncode,
            "l0_request_record": str(l0_record),
            "l0_request_record_exists": l0_attempted,
            "rerun_authorized": False if l0_attempted else None,
        }
        fallback_path = (
            measured_terminal
            if args.out_root.is_dir()
            else args.preflight_root / "terminal.json"
        )
        write_json(fallback_path, fallback)
        write_json(
            args.preflight_root / "measured-terminal-readback.json",
            fallback,
        )
        return 5

    write_json(
        args.preflight_root / "measured-terminal-readback.json",
        terminal,
    )
    write_json(
        args.preflight_root / "wrapper-terminal.json",
        {
            "authority_generation": AUTHORITY_GENERATION,
            "attempt_id": ATTEMPT_ID,
            "guard_returncode": run.returncode,
            "measured_terminal": terminal,
            "campaign_queue_receipt_created": False,
            "campaign_queue_or_spend_artifact_touched": False,
        },
    )
    return run.returncode


if __name__ == "__main__":
    sys.exit(main())

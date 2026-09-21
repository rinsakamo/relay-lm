#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ATTEMPT_ID = "logical-prefix-kv-replacement-20260921-30d3f94f"
PREMEASURED_ROOT = Path("/tmp/relaylm-logical-prefix-premeasured.4BYIKs/output")
REQUEST_RECONCILIATION_ROOT = Path("/tmp/relaylm-logical-prefix-request-id.JWuNTY/reconciliation")

EXPECTED_SERVER_SHA = "30d3f94f7335821a74828c243ab1dd315df9dc7a4c6df0cdff2f3ce1629dbaff"
EXPECTED_SERVER_IMPL_SHA = "e6003c1e1a1c1c16dc5a09da485517eec6b6010d17f198acd34981075c14a64c"
EXPECTED_LLAMA_SHA = "53228c024c04bd4a1acefa03d9ddc602cdfc78b5214d7fb7da13de458d2a2965"
EXPECTED_MODEL_SHA = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
EXPECTED_ALIGNED_PATCH_SHA = "cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a"
EXPECTED_LOGICAL_PATCH_SHA = "caad4731d82659468624e73803b6de6c3b8ac081d44350b8f71ae2d0600e1f36"
EXPECTED_APPLIED_PATCH_SHA = "d8d251727e5f3aa9a2d38434c124d0feb8748024f78cce5d4ec185bd8266fc7e"

EXPECTED_INPUTS = {
    "warm_tokens": "c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2",
    "target_tokens": "549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e",
    "L0": "9120aed18e9aac20615cab2de00337eb9bf65edb7249015c97d3c41d881e38d",
    "L1": "d4deaa365324c5ca3c42eba4e6db9defe957a1cf06bbc08e9d3a01ba94ec0d1f",
    "LC": "284630a2f90e364b5dd336d3d9fadc59ddd0fa072fbac7cc825200bef2e7af52",
}


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


def terminal_not_exercised(root: Path, stage: str, reason: str):
    value = {
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


def require_equal(observed, expected, label):
    if observed != expected:
        raise RuntimeError(f"{label}: {observed!r} != {expected!r}")


def validate_premeasured():
    top = load_json(PREMEASURED_ROOT / "terminal.json")
    build = load_json(PREMEASURED_ROOT / "build-stage" / "terminal.json")
    qual = load_json(PREMEASURED_ROOT / "qualification-stage" / "terminal.json")

    require_equal(
        top.get("primary_classification"),
        "LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY",
        "premeasured terminal",
    )
    require_equal(top.get("generated_requests"), 0, "premeasured generated_requests")
    require_equal(top.get("measured_l0_submitted"), False, "premeasured measured_l0_submitted")
    require_equal(top.get("measured_attempt_consumed"), False, "premeasured measured_attempt_consumed")
    require_equal(
        top.get("measured_execution_authorized_by_this_result"),
        False,
        "premeasured measured execution authorization",
    )

    require_equal(
        build.get("primary_classification"),
        "LOGICAL_PREFIX_REPLACEMENT_BUILD_READY",
        "build classification",
    )
    require_equal(build.get("server_sha256"), EXPECTED_SERVER_SHA, "build server SHA")
    require_equal(build.get("aligned_reuse_patch_sha256"), EXPECTED_ALIGNED_PATCH_SHA, "aligned patch SHA")
    require_equal(build.get("logical_prefix_patch_sha256"), EXPECTED_LOGICAL_PATCH_SHA, "logical patch SHA")
    require_equal(build.get("applied_patch_sha256"), EXPECTED_APPLIED_PATCH_SHA, "applied patch SHA")

    require_equal(
        qual.get("primary_classification"),
        "LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY",
        "qualification classification",
    )
    require_equal(qual.get("server_sha256"), EXPECTED_SERVER_SHA, "qualification server SHA")
    require_equal(qual.get("model_sha256"), EXPECTED_MODEL_SHA, "qualification model SHA")
    require_equal(qual.get("generated_requests"), 0, "qualification generated_requests")
    require_equal(qual.get("measured_l0_submitted"), False, "qualification measured_l0_submitted")
    require_equal(qual.get("measured_attempt_consumed"), False, "qualification measured_attempt_consumed")

    artifacts = qual.get("runtime_artifacts")
    if not isinstance(artifacts, dict):
        raise RuntimeError("qualification runtime_artifacts missing")
    require_equal(
        artifacts.get("llama_server", {}).get("sha256"),
        EXPECTED_SERVER_SHA,
        "qualification llama-server SHA",
    )
    require_equal(
        artifacts.get("llama_server_impl", {}).get("sha256"),
        EXPECTED_SERVER_IMPL_SHA,
        "qualification server-impl SHA",
    )
    require_equal(
        artifacts.get("llama", {}).get("sha256"),
        EXPECTED_LLAMA_SHA,
        "qualification libllama SHA",
    )
    require_equal(qual.get("forbidden_old_marker_present"), False, "forbidden old marker")

    server_bin = Path(build["server_binary"])
    if not server_bin.is_file():
        raise RuntimeError(f"qualified server binary missing: {server_bin}")
    require_equal(sha256(server_bin), EXPECTED_SERVER_SHA, "live server SHA")
    require_equal(
        sha256(server_bin.parent / "libllama-server-impl.so"),
        EXPECTED_SERVER_IMPL_SHA,
        "live server-impl SHA",
    )
    require_equal(
        sha256(server_bin.parent / "libllama.so"),
        EXPECTED_LLAMA_SHA,
        "live libllama SHA",
    )
    return server_bin


def validate_request_reconciliation():
    terminal = load_json(REQUEST_RECONCILIATION_ROOT / "terminal.json")
    require_equal(
        terminal.get("status"),
        "LOGICAL_PREFIX_REQUEST_IDENTITY_RECONCILED",
        "request reconciliation terminal",
    )
    for key in (
        "generated_requests",
        "model_loads",
        "server_startups",
    ):
        require_equal(terminal.get(key), 0, f"request reconciliation {key}")
    require_equal(
        terminal.get("measured_l0_submitted"),
        False,
        "request reconciliation measured_l0_submitted",
    )
    require_equal(
        terminal.get("measured_attempt_consumed"),
        False,
        "request reconciliation measured_attempt_consumed",
    )
    require_equal(
        terminal.get("measured_execution_authorized_by_this_result"),
        False,
        "request reconciliation authorization",
    )

    identities = terminal.get("identities")
    if not isinstance(identities, dict):
        raise RuntimeError("request reconciliation identities missing")

    paths = {}
    for name, expected_sha in EXPECTED_INPUTS.items():
        entry = identities.get(name)
        if not isinstance(entry, dict):
            raise RuntimeError(f"request reconciliation identity missing: {name}")
        require_equal(entry.get("sha256"), expected_sha, f"{name} reconciled SHA")
        path = Path(entry["path"])
        if not path.is_file():
            raise RuntimeError(f"{name} artifact disappeared: {path}")
        require_equal(sha256(path), expected_sha, f"{name} live SHA")
        paths[name] = path
    return paths


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

    try:
        server_bin = validate_premeasured()
        inputs = validate_request_reconciliation()
        if not args.model.is_file():
            raise RuntimeError(f"model missing: {args.model}")
        require_equal(sha256(args.model), EXPECTED_MODEL_SHA, "live model SHA")
    except Exception as exc:
        terminal_not_exercised(args.preflight_root, "authority_reconciliation", str(exc))
        return 2

    here = Path(__file__).resolve().parent
    runner_selftest = here / "e2d2c0d6-gemma4-kv-logical-prefix-replacement-runner-selftest.py"
    runner = here / "e2d2c0d6-gemma4-kv-logical-prefix-replacement-measured-run.py"
    guard = here / "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py"
    guard_selftest = here / "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard-selftest.py"

    for required in (runner_selftest, runner, guard, guard_selftest):
        if not required.is_file():
            terminal_not_exercised(
                args.preflight_root,
                "helper_presence",
                f"required helper missing: {required}",
            )
            return 3

    tests = [
        ("replacement-runner-selftest", runner_selftest, "KV_RUNNER_CONTRACT_SELFTEST_PASS"),
        ("resource-guard-selftest", guard_selftest, "LOGICAL_PREFIX_RESOURCE_GUARD_SELFTEST_PASS"),
    ]
    for label, path, expected_status in tests:
        run = subprocess.run([sys.executable, str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (args.preflight_root / f"{label}.stdout.json").write_bytes(run.stdout)
        (args.preflight_root / f"{label}.stderr.txt").write_bytes(run.stderr)
        if run.returncode != 0:
            terminal_not_exercised(args.preflight_root, label, f"{label} failed")
            return 4
        try:
            obj = json.loads(run.stdout)
        except Exception as exc:
            terminal_not_exercised(args.preflight_root, label, f"invalid JSON: {exc}")
            return 4
        if obj.get("status") != expected_status:
            terminal_not_exercised(
                args.preflight_root,
                label,
                f"unexpected status: {obj.get('status')}",
            )
            return 4

    identity = {
        "attempt_id": ATTEMPT_ID,
        "premeasured_root": str(PREMEASURED_ROOT),
        "request_reconciliation_root": str(REQUEST_RECONCILIATION_ROOT),
        "server_bin": str(server_bin),
        "server_sha256": EXPECTED_SERVER_SHA,
        "server_impl_sha256": EXPECTED_SERVER_IMPL_SHA,
        "llama_sha256": EXPECTED_LLAMA_SHA,
        "model": str(args.model),
        "model_sha256": EXPECTED_MODEL_SHA,
        "inputs": {
            name: {"path": str(inputs[name]), "sha256": EXPECTED_INPUTS[name]}
            for name in EXPECTED_INPUTS
        },
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
        "--server-bin", str(server_bin),
        "--model", str(args.model),
        "--warm-tokens", str(inputs["warm_tokens"]),
        "--target-tokens", str(inputs["target_tokens"]),
        "--l0-request", str(inputs["L0"]),
        "--l1-request", str(inputs["L1"]),
        "--lc-request", str(inputs["LC"]),
        "--out-root", str(args.out_root),
        "--port-wr", str(args.port_wr),
        "--port-wr2", str(args.port_wr2),
        "--port-c", str(args.port_c),
    ]
    write_json(args.preflight_root / "measured-runner.argv.json", runner_cmd)

    guard_root = args.preflight_root / "shared-resource-guard"
    guard_cmd = [
        sys.executable,
        str(guard),
        "--evidence-root", str(guard_root),
        "--",
        *runner_cmd,
    ]
    write_json(args.preflight_root / "guard.argv.json", guard_cmd)

    run = subprocess.run(guard_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        l0_request_record = args.out_root / "server-WR" / "L0.request.json"
        l0_attempted = l0_request_record.is_file()

        fallback = {
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
                "measured runner exited without terminal.json; classification "
                "derived conservatively from the pre-POST L0 request record"
                if child_invoked
                else "measured runner was not invoked"
            ),
            "guard_returncode": run.returncode,
            "l0_request_record": str(l0_request_record),
            "l0_request_record_exists": l0_attempted,
            "rerun_authorized": False if l0_attempted else None,
        }

        fallback_path = (
            measured_terminal
            if args.out_root.is_dir()
            else args.preflight_root / "terminal.json"
        )
        write_json(fallback_path, fallback)
        write_json(args.preflight_root / "measured-terminal-readback.json", fallback)
        return 5

    write_json(args.preflight_root / "measured-terminal-readback.json", terminal)
    write_json(args.preflight_root / "wrapper-terminal.json", {
        "attempt_id": ATTEMPT_ID,
        "guard_returncode": run.returncode,
        "measured_terminal": terminal,
        "campaign_queue_receipt_created": False,
        "campaign_queue_or_spend_artifact_touched": False,
    })
    return run.returncode


if __name__ == "__main__":
    sys.exit(main())

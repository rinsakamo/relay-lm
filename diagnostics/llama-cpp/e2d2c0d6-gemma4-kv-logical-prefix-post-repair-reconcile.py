#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

EXPECTED_SOURCE_HEAD = "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"
EXPECTED_SOURCE_TREE = "6d39fd93dc91fc0a4bc86dffe9782d4f26318004"
EXPECTED_MODEL_SHA = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
CONSUMED_SERVER_SHA = "30d3f94f7335821a74828c243ab1dd315df9dc7a4c6df0cdff2f3ce1629dbaff"

EXPECTED_REQUESTS = {
    "warm_tokens": "c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2",
    "target_tokens": "549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e",
    "L0": "9120aed18e9aac20615cab2de00337eb9bf65edeb7249015c97d3c41d881e38d",
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


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def require_equal(observed, expected, label):
    if observed != expected:
        raise RuntimeError(f"{label}: {observed!r} != {expected!r}")


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

    current_aligned = here / "e2d2c0d6-gemma4-swa-ubatch-aligned-reuse-diagnostic.patch"
    current_logical = here / "e2d2c0d6-gemma4-kv-logical-prefix-dump-diagnostic.patch"
    require(current_aligned.is_file(), "current aligned patch missing")
    require(current_logical.is_file(), "current logical-prefix patch missing")

    aligned_sha = sha256(current_aligned)
    logical_sha = sha256(current_logical)
    require_equal(build.get("aligned_reuse_patch_sha256"), aligned_sha, "aligned patch SHA")
    require_equal(build.get("logical_prefix_patch_sha256"), logical_sha, "logical patch SHA")

    applied_patch = root / "build-stage" / "applied.patch"
    require(applied_patch.is_file(), "applied.patch missing")
    applied_sha = sha256(applied_patch)
    require_equal(build.get("applied_patch_sha256"), applied_sha, "applied.patch SHA")

    require_equal(
        binary.get("status"),
        "LOGICAL_PREFIX_BINARY_PREFLIGHT_PASS",
        "binary preflight",
    )
    require_equal(binary.get("model_sha256"), EXPECTED_MODEL_SHA, "model SHA")
    require_equal(binary.get("aligned_reuse_patch_sha256"), aligned_sha, "binary aligned patch SHA")
    require_equal(binary.get("logical_prefix_patch_sha256"), logical_sha, "binary logical patch SHA")
    require_equal(binary.get("forbidden_old_marker_present"), False, "forbidden old marker")

    server_sha = binary.get("server_sha256")
    require(isinstance(server_sha, str) and len(server_sha) == 64, "invalid server SHA")
    require(server_sha != CONSUMED_SERVER_SHA, "new server equals consumed server SHA")

    artifacts = binary.get("runtime_artifacts")
    require(isinstance(artifacts, dict), "runtime_artifacts missing")
    required_artifacts = ("llama_server", "llama_server_impl", "llama")
    live_artifacts = {}
    for name in required_artifacts:
        entry = artifacts.get(name)
        require(isinstance(entry, dict), f"runtime artifact missing: {name}")
        recorded_sha = entry.get("sha256")
        require(isinstance(recorded_sha, str) and len(recorded_sha) == 64, f"invalid {name} SHA")
        path = Path(entry.get("path", ""))
        require(path.is_file(), f"runtime artifact file missing: {name}: {path}")
        observed_sha = sha256(path)
        require_equal(observed_sha, recorded_sha, f"live {name} SHA")
        require_equal(
            entry.get("forbidden_old_marker_present"),
            False,
            f"{name} forbidden old marker",
        )
        live_artifacts[name] = {
            "path": str(path),
            "resolved_path": str(path.resolve(strict=True)),
            "sha256": observed_sha,
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
    require_equal(qual.get("server_sha256"), server_sha, "qualification server SHA")
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
    ev = startup.get("evidence")
    require(isinstance(ev, dict), "startup evidence missing")
    plain = ev.get("plain")
    probe = ev.get("probe")
    require(isinstance(plain, dict) and isinstance(probe, dict), "plain/probe evidence missing")
    require_equal(
        plain.get("argv_canonical_sha256"),
        probe.get("argv_canonical_sha256"),
        "plain/probe canonical argv SHA",
    )
    for arm_name, arm in (("plain", plain), ("probe", probe)):
        checks = arm.get("context", {}).get("checks", {})
        require(checks and all(x.get("ok") is True for x in checks.values()), f"{arm_name} context checks")
        swa = arm.get("compact_swa", {})
        require(swa.get("ok") is True, f"{arm_name} compact SWA")
        require_equal(swa.get("selected_base_size"), 8192, f"{arm_name} base KV")
        swa_size = swa.get("selected_swa_size")
        require(isinstance(swa_size, int) and 0 < swa_size < 8192, f"{arm_name} SWA KV")
        require_equal(arm.get("unexpected_probe_output"), False, f"{arm_name} unexpected probe output")
    require_equal(
        plain.get("compact_swa", {}).get("selected_swa_size"),
        probe.get("compact_swa", {}).get("selected_swa_size"),
        "plain/probe SWA geometry",
    )

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

    return {
        "premeasured_root": str(root),
        "source_head": build.get("source_head"),
        "source_tree": build.get("source_tree"),
        "aligned_reuse_patch_sha256": aligned_sha,
        "logical_prefix_patch_sha256": logical_sha,
        "applied_patch_sha256": applied_sha,
        "server_sha256": server_sha,
        "model": binary.get("model"),
        "model_sha256": binary.get("model_sha256"),
        "runtime_artifacts": live_artifacts,
        "required_runtime_markers": markers,
        "forbidden_old_marker_present": False,
        "startup_argv_canonical_sha256": plain.get("argv_canonical_sha256"),
        "base_kv": plain.get("compact_swa", {}).get("selected_base_size"),
        "swa_kv": plain.get("compact_swa", {}).get("selected_swa_size"),
        "resource_guard": guard,
        "external_quiescence": idle,
    }


def _validate_selected_requests(selected, out_root: Path, here: Path, provenance):
    require(isinstance(selected, dict), "request identities missing")

    live = {}
    for name, expected_sha in EXPECTED_REQUESTS.items():
        entry = selected.get(name)
        require(isinstance(entry, dict), f"request identity missing: {name}")
        require_equal(entry.get("sha256"), expected_sha, f"recorded {name} SHA")
        path = Path(entry.get("path", ""))
        require(path.is_file(), f"raw request artifact missing: {name}: {path}")
        observed = sha256(path)
        require_equal(observed, expected_sha, f"live {name} SHA")
        live[name] = {
            "path": str(path),
            "resolved_path": str(path.resolve(strict=True)),
            "sha256": observed,
        }

    admission = here / "e2d2c0d6-gemma4-kv-request-admission.py"
    require(admission.is_file(), "request admission helper missing")
    admission_out = out_root / "request-admission.json"
    admission_cmd = [
        sys.executable,
        str(admission),
        "--warm-tokens", live["warm_tokens"]["path"],
        "--target-tokens", live["target_tokens"]["path"],
        "--l0", live["L0"]["path"],
        "--l1", live["L1"]["path"],
        "--lc", live["LC"]["path"],
        "--out", str(admission_out),
    ]
    write_json(out_root / "request-admission.argv.json", admission_cmd)
    run = subprocess.run(admission_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out_root / "request-admission.stdout.txt").write_bytes(run.stdout)
    (out_root / "request-admission.stderr.txt").write_bytes(run.stderr)
    require_equal(run.returncode, 0, "request admission returncode")
    admitted = load_json(admission_out)
    require_equal(admitted.get("status"), "REQUEST_ADMISSION_PASS", "request admission status")

    return {
        "provenance": provenance,
        "identities": live,
        "request_admission": admitted,
        "l0r_rule": "send the exact L0 request bytes again on a fresh WR2 server",
    }


def revalidate_requests(prior_root, binding_json, search_roots, out_root: Path, here: Path):
    if prior_root is not None and (prior_root / "terminal.json").is_file():
        prior = load_json(prior_root / "terminal.json")
        require_equal(
            prior.get("status"),
            "LOGICAL_PREFIX_REQUEST_IDENTITY_RECONCILED",
            "prior request reconciliation",
        )
        return _validate_selected_requests(
            prior.get("identities"),
            out_root,
            here,
            {
                "mode": "prior_reconciliation",
                "prior_reconciliation_root": str(prior_root),
            },
        )

    if binding_json is not None and binding_json.is_file():
        binding = load_json(binding_json)
        inputs = binding.get("inputs")
        require(isinstance(inputs, dict), "request binding inputs missing")
        return _validate_selected_requests(
            inputs,
            out_root,
            here,
            {
                "mode": "measured_preflight_binding",
                "binding_json": str(binding_json),
            },
        )

    require(search_roots, "prior request reconciliation and request binding missing; no request search roots supplied")
    locator = here / "e2d2c0d6-gemma4-kv-artifact-locator.py"
    require(locator.is_file(), "artifact locator helper missing")
    locator_out = out_root / "artifact-locator.json"
    locator_cmd = [
        sys.executable,
        str(locator),
        *[str(root) for root in search_roots],
        "--out",
        str(locator_out),
    ]
    write_json(out_root / "artifact-locator.argv.json", locator_cmd)
    located = subprocess.run(locator_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out_root / "artifact-locator.stdout.txt").write_bytes(located.stdout)
    (out_root / "artifact-locator.stderr.txt").write_bytes(located.stderr)
    require_equal(located.returncode, 0, "artifact locator returncode")
    located_obj = load_json(locator_out)
    require_equal(located_obj.get("status"), "ARTIFACT_LOCATOR_PASS", "artifact locator status")

    return _validate_selected_requests(
        located_obj.get("selected"),
        out_root,
        here,
        {
            "mode": "bounded_artifact_rediscovery",
            "searched_roots": [str(root) for root in search_roots],
            "artifact_locator": str(locator_out),
        },
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--premeasured-root", type=Path, required=True)
    ap.add_argument("--prior-request-reconciliation-root", type=Path)
    ap.add_argument("--request-binding-json", type=Path)
    ap.add_argument("--request-search-root", action="append", type=Path, default=[])
    ap.add_argument("--out-root", type=Path, required=True)
    args = ap.parse_args()

    if args.out_root.exists():
        raise SystemExit(f"output root must not exist: {args.out_root}")
    args.out_root.mkdir(parents=True)

    here = Path(__file__).resolve().parent
    try:
        apparatus = validate_premeasured(args.premeasured_root, here)
        requests = revalidate_requests(
            args.prior_request_reconciliation_root,
            args.request_binding_json,
            args.request_search_root,
            args.out_root,
            here,
        )
        out = {
            "status": "LOGICAL_PREFIX_POST_REPAIR_RECONCILED",
            "apparatus": apparatus,
            "requests": requests,
            "generated_requests": 0,
            "model_loads": 0,
            "server_startups": 0,
            "measured_l0_submitted": False,
            "measured_attempt_consumed": False,
            "measured_execution_authorized_by_this_result": False,
        }
        write_json(args.out_root / "terminal.json", out)
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        out = {
            "status": "LOGICAL_PREFIX_POST_REPAIR_NOT_RECONCILED",
            "reason": f"{type(exc).__name__}: {exc}",
            "generated_requests": 0,
            "model_loads": 0,
            "server_startups": 0,
            "measured_l0_submitted": False,
            "measured_attempt_consumed": False,
            "measured_execution_authorized_by_this_result": False,
        }
        write_json(args.out_root / "terminal.json", out)
        print(json.dumps(out, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())

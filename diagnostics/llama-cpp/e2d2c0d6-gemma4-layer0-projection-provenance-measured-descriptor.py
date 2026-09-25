#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

EXPECTED_PREMEASURED_ROOT = Path("/home/rinsa/relaylm-evidence/provenance-preparation-generation-f-20260925T102433Z-474088").resolve()
EXPECTED_AUTHORITY_HEAD = "a68beee0537e1ebc9845a12c73f2b588cdc9dd66"
EXPECTED_AUTHORITY_TREE = "e9bee1fdd86f4d321182beb579376959f4b90930"
EXPECTED_GENERATION = "provenance-preparation-20260924-f"
EXPECTED_SOURCE_HEAD = "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"
EXPECTED_SOURCE_TREE = "6d39fd93dc91fc0a4bc86dffe9782d4f26318004"
EXPECTED_MODEL_SHA = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
EXPECTED_APPLIED_PATCH_SHA = "cbf9c2f61e2221328cd0db1d24127dd3d8f13be3681dd6dbfb135db51d6eff63"
EXPECTED_PATCHES = {
    "aligned_reuse_patch_sha256": "cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a",
    "logical_prefix_patch_sha256": "d62810fdc645cbb011c52047e9ba9227b1d6c29fafc0bac0e7cf659f6104e4c8",
    "projection_origin_patch_sha256": "61af8dce39b0dceb0ce12b7fef8014dcb8f94ba7564955783c5ff76c9d211674",
    "projection_provenance_patch_sha256": "413db229e31b1e68e760a354a34e61fae952aa237c81f37f2290b10c48905048",
}

RUNTIME_FILES = {
    "llama_server": "llama-server",
    "llama_server_impl": "libllama-server-impl.so",
    "llama": "libllama.so",
    "ggml": "libggml.so",
    "ggml_base": "libggml-base.so",
    "ggml_cpu": "libggml-cpu.so",
    "ggml_cuda": "libggml-cuda.so",
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def require(cond, message):
    if not cond:
        raise RuntimeError(message)

def verify_sealed(root: Path):
    require(root.is_dir(), f"premeasured root missing: {root}")
    root_mode = stat.S_IMODE(root.stat().st_mode)
    require((root_mode & 0o222) == 0, f"premeasured root writable: mode={oct(root_mode)}")
    writable = []
    for p in root.rglob("*"):
        try:
            mode = stat.S_IMODE(p.stat().st_mode)
        except FileNotFoundError:
            writable.append(f"disappeared:{p}")
            continue
        if mode & 0o222:
            writable.append(f"{oct(mode)}:{p}")
    require(not writable, f"writable entries in sealed root: {writable[:8]}")

def verify_manifest(root: Path):
    manifest = root / "prepared-artifact-manifest.sha256"
    require(manifest.is_file(), f"prepared artifact manifest missing: {manifest}")
    entries = []
    for lineno, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split(None, 1)
        require(len(parts) == 2 and len(parts[0]) == 64, f"malformed manifest line {lineno}")
        expected, path_text = parts
        path = Path(path_text.strip())
        require(path.is_absolute(), f"manifest path not absolute: {path}")
        resolved = path.resolve()
        require(resolved == root or root in resolved.parents, f"manifest path escapes premeasured root: {resolved}")
        require(resolved.is_file(), f"manifest file missing: {resolved}")
        actual = sha256(resolved)
        require(actual == expected, f"manifest hash mismatch: {resolved}")
        entries.append({"path": str(resolved), "sha256": actual})
    require(entries, "prepared artifact manifest empty")
    return {
        "path": str(manifest.resolve()),
        "sha256": sha256(manifest),
        "entries": entries,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--premeasured-root", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    root = args.premeasured_root.resolve()
    model = args.model.resolve()
    out = args.out.resolve()

    require(root == EXPECTED_PREMEASURED_ROOT, f"unexpected premeasured root: {root}")
    require(out != root and root not in out.parents, "descriptor output must be outside sealed premeasured root")
    require(not out.exists(), f"descriptor output must not exist: {out}")
    require(model.is_file(), f"model missing: {model}")
    require(sha256(model) == EXPECTED_MODEL_SHA, "model SHA mismatch")

    verify_sealed(root)
    manifest = verify_manifest(root)

    top = load_json(root / "terminal.json")
    build = load_json(root / "build-stage" / "terminal.json")
    qual = load_json(root / "qualification-stage" / "terminal.json")
    binary = load_json(root / "qualification-stage" / "logical-prefix-binary-preflight.json")
    startup = load_json(root / "qualification-stage" / "logical-prefix-startup-classification.json")
    guard = load_json(root / "qualification-stage" / "shared-resource-guard" / "guard.json")
    quiescence = load_json(root / "qualification-stage" / "shared-resource-guard" / "external-quiescence.json")

    require(top.get("preparation_generation") == EXPECTED_GENERATION, "top generation mismatch")
    require(top.get("primary_classification") == "LAYER0_PROJECTION_PROVENANCE_PREMEASURED_READY", "top classification mismatch")
    require(top.get("relaylm_authority_head") == EXPECTED_AUTHORITY_HEAD, "authority HEAD mismatch")
    require(top.get("relaylm_authority_remote_head") == EXPECTED_AUTHORITY_HEAD, "remote authority HEAD mismatch")
    require(top.get("relaylm_authority_tree") == EXPECTED_AUTHORITY_TREE, "authority tree mismatch")
    require(top.get("generated_requests") == 0, "top generated requests nonzero")
    require(top.get("measured_l0_submitted") is False, "top measured submission true")
    require(top.get("measured_attempt_consumed") is False, "top measured attempt consumed")
    require(top.get("measured_execution_authorized_by_this_result") is False, "top improperly authorizes measured execution")

    require(build.get("preparation_generation") == EXPECTED_GENERATION, "build generation mismatch")
    require(build.get("primary_classification") == "LAYER0_PROJECTION_PROVENANCE_BUILD_READY", "build classification mismatch")
    require(build.get("source_head") == EXPECTED_SOURCE_HEAD, "source HEAD mismatch")
    require(build.get("source_tree") == EXPECTED_SOURCE_TREE, "source tree mismatch")
    require(build.get("applied_patch_sha256") == EXPECTED_APPLIED_PATCH_SHA, "applied patch mismatch")
    for key, expected in EXPECTED_PATCHES.items():
        require(build.get(key) == expected, f"build patch mismatch: {key}")

    require(qual.get("preparation_generation") == EXPECTED_GENERATION, "qualification generation mismatch")
    require(qual.get("primary_classification") == "LAYER0_PROJECTION_PROVENANCE_PREMEASURED_READY", "qualification classification mismatch")
    require(qual.get("generated_requests") == 0, "qualification generated requests nonzero")
    require(qual.get("measured_l0_submitted") is False, "qualification measured submission true")
    require(qual.get("measured_attempt_consumed") is False, "qualification measured attempt consumed")
    require(qual.get("measured_execution_authorized_by_this_result") is False, "qualification improperly authorizes measured execution")

    require(binary.get("status") == "LAYER0_PROJECTION_PROVENANCE_BINARY_PREFLIGHT_PASS", "binary preflight mismatch")
    require(binary.get("errors") == [], "binary preflight errors")
    require(binary.get("model_sha256") == EXPECTED_MODEL_SHA, "binary model SHA mismatch")
    require(binary.get("forbidden_old_marker_present") is False, "forbidden old marker present")
    markers = binary.get("required_runtime_markers") or {}
    for marker in ("provenance tensor missing: %s", "tensor_ptr", "src0_ptr", "src1_ptr"):
        require((markers.get(marker) or {}).get("present") is True, f"stable runtime marker missing: {marker}")

    require(startup.get("primary_classification") == "LOGICAL_PREFIX_STARTUP_QUALIFIED", "startup classification mismatch")
    startup_evidence = startup.get("evidence") or {}
    argv_shas = {}
    for arm_name in ("plain", "probe"):
        arm = startup_evidence.get(arm_name) or {}
        require(arm.get("classification") == "READY_NON_GENERATIVE", f"{arm_name} startup not ready")
        require(arm.get("unexpected_probe_output") is False, f"{arm_name} unexpected probe output")
        checks = ((arm.get("context") or {}).get("checks") or {})
        for key in ("n_seq_max_1", "n_ctx_8192", "n_batch_512", "n_ubatch_512", "flash_attn_enabled"):
            require((checks.get(key) or {}).get("ok") is True, f"{arm_name} runtime check failed: {key}")
        swa = arm.get("compact_swa") or {}
        require(swa.get("ok") is True, f"{arm_name} compact SWA failed")
        require(swa.get("selected_base_size") == 8192, f"{arm_name} base KV mismatch")
        require(swa.get("selected_swa_size") == 1536, f"{arm_name} SWA KV mismatch")
        argv_sha = arm.get("argv_canonical_sha256")
        require(isinstance(argv_sha, str) and len(argv_sha) == 64, f"{arm_name} canonical argv SHA missing")
        argv_shas[arm_name] = argv_sha
    require(argv_shas["plain"] == argv_shas["probe"], "startup canonical argv differs across arms")

    require(guard.get("resource_key") == "llama-cpp:local-gpu", "resource key mismatch")
    require(guard.get("guard_state") == "RELEASED_CANONICAL_DIAGNOSTIC_FLOCK", "resource guard not cleanly released")
    require(guard.get("lock_acquired") is True, "resource guard lock not acquired")
    require(guard.get("child_invoked") is True, "resource guard child not invoked")
    require(guard.get("child_returncode") == 0, "resource guard child failed")
    require(guard.get("failure") is None, "resource guard failure present")
    require(guard.get("campaign_queue_receipt_created") is False, "campaign queue receipt created")
    require(guard.get("campaign_queue_or_spend_artifact_touched") is False, "campaign/spend artifact touched")
    require(isinstance(quiescence, list) and len(quiescence) == 2, "quiescence observation count mismatch")
    for obs in quiescence:
        require(obs.get("busy_processes") == [], "busy process in preparation quiescence")
        require(obs.get("listener_127_0_0_1_1234") is False, "1234 listener in preparation quiescence")
        require(obs.get("gpu_compute_processes") == [], "GPU compute process in preparation quiescence")

    bin_dir = (root / "build-stage" / "build" / "bin").resolve()
    runtime = {}
    binary_runtime = binary.get("runtime_artifacts") or {}
    qual_runtime = qual.get("runtime_artifacts") or {}
    build_fields = {
        "llama_server": "server_sha256",
        "llama_server_impl": "server_impl_sha256",
        "llama": "llama_lib_sha256",
        "ggml": "ggml_lib_sha256",
        "ggml_base": "ggml_base_sha256",
        "ggml_cpu": "ggml_cpu_sha256",
        "ggml_cuda": "ggml_cuda_sha256",
    }
    binary_keys = {
        "llama_server_impl": "llama_server_impl",
        "llama": "llama",
        "ggml": "ggml",
        "ggml_base": "ggml_base",
        "ggml_cpu": "ggml_cpu",
        "ggml_cuda": "ggml_cuda",
    }
    for name, filename in RUNTIME_FILES.items():
        path = (bin_dir / filename).resolve()
        require(path.is_file(), f"runtime artifact missing: {path}")
        actual = sha256(path)
        build_key = build_fields[name]
        require(build.get(build_key) == actual, f"build runtime SHA mismatch: {name}")
        if name == "llama_server":
            require(binary.get("server_sha256") == actual, "binary server SHA mismatch")
            require(qual.get("server_sha256") == actual, "qualification server SHA mismatch")
        else:
            bkey = binary_keys[name]
            require((binary_runtime.get(bkey) or {}).get("sha256") == actual, f"binary runtime SHA mismatch: {name}")
            require((qual_runtime.get(bkey) or {}).get("sha256") == actual, f"qualification runtime SHA mismatch: {name}")
        runtime[name] = {"path": str(path), "sha256": actual}

    descriptor = {
        "descriptor_generation": "provenance-measured-descriptor-20260925-a",
        "classification": "LAYER0_PROJECTION_PROVENANCE_MEASURED_DESCRIPTOR_READY",
        "relaylm_authority_head": EXPECTED_AUTHORITY_HEAD,
        "relaylm_authority_tree": EXPECTED_AUTHORITY_TREE,
        "preparation_generation": EXPECTED_GENERATION,
        "premeasured_root": str(root),
        "prepared_artifact_manifest": manifest,
        "source_head": EXPECTED_SOURCE_HEAD,
        "source_tree": EXPECTED_SOURCE_TREE,
        "model": {"path": str(model), "sha256": EXPECTED_MODEL_SHA},
        "patches": {
            **EXPECTED_PATCHES,
            "applied_patch_sha256": EXPECTED_APPLIED_PATCH_SHA,
        },
        "runtime": runtime,
        "startup_canonical_argv_sha256": argv_shas["plain"],
        "preparation_resource_guard": {
            "resource_key": guard.get("resource_key"),
            "guard_state": guard.get("guard_state"),
            "lock_acquired": guard.get("lock_acquired"),
            "child_returncode": guard.get("child_returncode"),
            "failure": guard.get("failure"),
        },
        "preparation_external_quiescence": quiescence,
        "stable_runtime_markers": {
            marker: (markers.get(marker) or {}).get("present")
            for marker in ("provenance tensor missing: %s", "tensor_ptr", "src0_ptr", "src1_ptr")
        },
        "generation_requests": 0,
        "measured_requests": 0,
        "measured_attempt_consumed": False,
        "measured_execution_authorized_by_this_result": False,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "LAYER0_PROJECTION_PROVENANCE_MEASURED_DESCRIPTOR_READY",
        "descriptor": str(out),
        "descriptor_sha256": sha256(out),
        "prepared_artifact_manifest_sha256": manifest["sha256"],
        "runtime": {k: v["sha256"] for k, v in runtime.items()},
        "startup_canonical_argv_sha256": argv_shas["plain"],
        "generation_requests": 0,
        "measured_requests": 0,
        "measured_attempt_consumed": False,
        "measured_execution_authorized_by_this_result": False,
    }, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise

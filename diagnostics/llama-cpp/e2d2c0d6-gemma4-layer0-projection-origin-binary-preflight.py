#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


EXPECTED_MODEL_SHA = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"

HERE = Path(__file__).resolve().parent
LOGICAL_PATCH = HERE / "e2d2c0d6-gemma4-kv-logical-prefix-dump-diagnostic.patch"
ALIGNED_PATCH = HERE / "e2d2c0d6-gemma4-swa-ubatch-aligned-reuse-diagnostic.patch"
ORIGIN_PATCH = HERE / "e2d2c0d6-gemma4-layer0-projection-origin-diagnostic.patch"

SERVER_IMPL_MARKERS = [
    b"RelayLM KV diagnostic failed at logical-prefix dump",
    b"RelayLM KV diagnostic found multiple logical position-511 prompt tokens",
    b"RelayLM KV diagnostic failed at retained-prefix dump",
]

LLAMA_LIBRARY_MARKERS = [
    b"target memory is not iSWA KV memory",
    b"refusing to overwrite existing diagnostic dump",
    b"refusing to overwrite existing projection-origin dump",
    b"projection-origin diagnostic dump failed",
    b"LLAMA_PROJECTION_ORIGIN_PROBE_DIR",
    b"LLAMA_PROJECTION_ORIGIN_PROBE_LABEL",
]

FORBIDDEN_OLD_BINARY_MARKER = b"RelayLM KV diagnostic failed at generated-prefix dump"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-bin", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    errors = []

    if not args.server_bin.is_file():
        errors.append("server binary missing")
    elif not os.access(args.server_bin, os.X_OK):
        errors.append("server binary is not executable")

    if not args.model.is_file():
        errors.append("model missing")

    if not LOGICAL_PATCH.is_file():
        errors.append("logical-prefix patch file missing")
    if not ALIGNED_PATCH.is_file():
        errors.append("aligned-reuse patch file missing")
    if not ORIGIN_PATCH.is_file():
        errors.append("projection-origin patch file missing")

    server_sha = sha256(args.server_bin) if args.server_bin.is_file() else None
    model_sha = sha256(args.model) if args.model.is_file() else None
    logical_patch_sha = sha256(LOGICAL_PATCH) if LOGICAL_PATCH.is_file() else None
    aligned_patch_sha = sha256(ALIGNED_PATCH) if ALIGNED_PATCH.is_file() else None
    origin_patch_sha = sha256(ORIGIN_PATCH) if ORIGIN_PATCH.is_file() else None

    if model_sha is not None and model_sha != EXPECTED_MODEL_SHA:
        errors.append("model SHA256 mismatch")

    artifact_specs = {
        "llama_server": {
            "path": args.server_bin,
            "required_markers": [],
        },
        "llama_server_impl": {
            "path": args.server_bin.parent / "libllama-server-impl.so",
            "required_markers": SERVER_IMPL_MARKERS,
        },
        "llama": {
            "path": args.server_bin.parent / "libllama.so",
            "required_markers": LLAMA_LIBRARY_MARKERS,
        },
    }

    runtime_artifacts = {}
    marker_results = {}
    old_marker_present = False

    for artifact_name, spec in artifact_specs.items():
        path = spec["path"]
        entry = {
            "path": str(path),
            "resolved_path": None,
            "sha256": None,
            "required_markers": {},
            "forbidden_old_marker_present": None,
        }

        if not path.is_file():
            errors.append(f"runtime artifact missing: {artifact_name}: {path}")
            runtime_artifacts[artifact_name] = entry
            continue

        resolved = path.resolve(strict=True)
        data = path.read_bytes()
        entry["resolved_path"] = str(resolved)
        entry["sha256"] = sha256(path)

        for marker in spec["required_markers"]:
            key = marker.decode("utf-8")
            present = marker in data
            entry["required_markers"][key] = present
            marker_results[key] = {
                "artifact": artifact_name,
                "path": str(path),
                "present": present,
            }
            if not present:
                errors.append(
                    f"required runtime marker missing from {artifact_name}: {key}"
                )

        artifact_old_marker_present = FORBIDDEN_OLD_BINARY_MARKER in data
        entry["forbidden_old_marker_present"] = artifact_old_marker_present
        old_marker_present = old_marker_present or artifact_old_marker_present
        runtime_artifacts[artifact_name] = entry

    if old_marker_present:
        errors.append("old generated-prefix instrumentation marker still present in runtime artifact closure")

    result = {
        "status": (
            "LAYER0_PROJECTION_ORIGIN_BINARY_PREFLIGHT_PASS"
            if not errors
            else "LAYER0_PROJECTION_ORIGIN_BINARY_PREFLIGHT_FAIL"
        ),
        "server_binary": str(args.server_bin),
        "server_sha256": server_sha,
        "model": str(args.model),
        "model_sha256": model_sha,
        "expected_model_sha256": EXPECTED_MODEL_SHA,
        "logical_prefix_patch": str(LOGICAL_PATCH),
        "logical_prefix_patch_sha256": logical_patch_sha,
        "aligned_reuse_patch": str(ALIGNED_PATCH),
        "aligned_reuse_patch_sha256": aligned_patch_sha,
        "projection_origin_patch": str(ORIGIN_PATCH),
        "projection_origin_patch_sha256": origin_patch_sha,
        "runtime_artifacts": runtime_artifacts,
        "required_runtime_markers": marker_results,
        "forbidden_old_marker_present": old_marker_present,
        "errors": errors,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

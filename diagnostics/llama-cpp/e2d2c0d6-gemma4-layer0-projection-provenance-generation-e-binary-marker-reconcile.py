#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import sys

EXPECTED_GENERATION = "provenance-preparation-20260923-e"
EXPECTED_BUILD_HASHES = {
    "server_sha256": "f97fa468e6a5c4ce7d72701bb90f991f04dc48d335aaefdfbc4f07231a975418",
    "server_impl_sha256": "8379cca997d51bdf117eba98f635b86111b24b59153d87724ff2889a44e7f423",
    "llama_lib_sha256": "a5f1ba1377e32f0a48d933ead19e7bf925dcec75b79c07db94004e7e26adca2e",
    "ggml_lib_sha256": "9eb83ea975cbfdc701ba5e21acb73008efea9f8d545766f049bdae7cc6cefbea",
    "ggml_base_sha256": "ed1750ba698060776cfa4431aea02b6c892f770769726901dab6bf170023fc58",
    "ggml_cpu_sha256": "025375dea683ac451670f6154d321c4ddf93b2aabddd80b17725476fc37d8fe9",
    "ggml_cuda_sha256": "04e6d70b307d4e1a2d37a5e0902eb25a509c9bcebf0267dbda1c3ad4496054c3",
    "applied_patch_sha256": "cbf9c2f61e2221328cd0db1d24127dd3d8f13be3681dd6dbfb135db51d6eff63",
}
EXPECTED_PATCH_HASHES = {
    "aligned_reuse_patch_sha256": "cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a",
    "logical_prefix_patch_sha256": "d62810fdc645cbb011c52047e9ba9227b1d6c29fafc0bac0e7cf659f6104e4c8",
    "projection_origin_patch_sha256": "61af8dce39b0dceb0ce12b7fef8014dcb8f94ba7564955783c5ff76c9d211674",
    "projection_provenance_patch_sha256": "413db229e31b1e68e760a354a34e61fae952aa237c81f37f2290b10c48905048",
}
BRITTLE_MARKER = b"provenance.tsv"
STABLE_MARKERS = (
    b"provenance tensor missing: %s",
    b"tensor_ptr",
    b"src0_ptr",
    b"src1_ptr",
)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def require(cond, errors, message):
    if not cond:
        errors.append(message)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    if args.out.exists():
        raise SystemExit(f"refusing to overwrite output: {args.out}")

    root = args.prep_root.resolve()
    errors = []

    terminal_path = root / "terminal.json"
    build_terminal_path = root / "build-stage" / "terminal.json"
    preflight_path = root / "qualification-stage" / "logical-prefix-binary-preflight.json"

    for path in (terminal_path, build_terminal_path, preflight_path):
        require(path.is_file(), errors, f"required evidence missing: {path}")

    if errors:
        out = {
            "classification": "GENERATION_E_BINARY_MARKER_RECONCILIATION_INCOMPLETE",
            "errors": errors,
            "physical_calls": 0,
            "gpu_calls": 0,
            "model_loads": 0,
            "generation_requests": 0,
            "measured_requests": 0,
        }
        args.out.mkdir(parents=True)
        (args.out / "terminal.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(out, indent=2, sort_keys=True))
        return 1

    terminal = load_json(terminal_path)
    build = load_json(build_terminal_path)
    preflight = load_json(preflight_path)

    require(terminal.get("preparation_generation") == EXPECTED_GENERATION, errors, "unexpected failed preparation generation")
    require(terminal.get("primary_classification") == "LAYER0_PROJECTION_PROVENANCE_PREPARATION_FAILED", errors, "unexpected failed preparation terminal classification")
    require(terminal.get("build_returncode") == 0, errors, "failed preparation did not record build rc 0")
    require(terminal.get("qualification_returncode") == 1, errors, "failed preparation did not record qualification rc 1")
    require(terminal.get("generated_requests") == 0, errors, "failed preparation generated requests")
    require(terminal.get("measured_l0_submitted") is False, errors, "failed preparation submitted measured L0")
    require(terminal.get("measured_attempt_consumed") is False, errors, "failed preparation consumed measured attempt")

    require(build.get("preparation_generation") == EXPECTED_GENERATION, errors, "unexpected build generation")
    require(build.get("primary_classification") == "LAYER0_PROJECTION_PROVENANCE_BUILD_READY", errors, "build was not ready")

    for key, expected in EXPECTED_BUILD_HASHES.items():
        require(build.get(key) == expected, errors, f"build evidence hash mismatch: {key}")
    for key, expected in EXPECTED_PATCH_HASHES.items():
        require(build.get(key) == expected, errors, f"patch evidence hash mismatch: {key}")

    require(preflight.get("status") == "LAYER0_PROJECTION_PROVENANCE_BINARY_PREFLIGHT_FAIL", errors, "historical preflight did not fail")
    preflight_errors = preflight.get("errors") or []
    expected_old_error = "required runtime marker missing from llama: provenance.tsv"
    require(expected_old_error in preflight_errors, errors, "historical preflight did not fail on provenance.tsv marker")
    other_errors = [x for x in preflight_errors if x != expected_old_error]
    require(other_errors == [], errors, f"historical preflight had additional errors: {other_errors!r}")

    llama_path_text = build.get("llama_lib_resolved")
    require(isinstance(llama_path_text, str) and llama_path_text, errors, "build terminal missing resolved libllama path")
    llama_path = Path(llama_path_text) if llama_path_text else None
    if llama_path is not None:
        require(llama_path.is_file(), errors, f"preserved libllama missing: {llama_path}")

    marker_evidence = {}
    if llama_path is not None and llama_path.is_file():
        require(sha256(llama_path) == EXPECTED_BUILD_HASHES["llama_lib_sha256"], errors, "preserved libllama SHA mismatch")
        data = llama_path.read_bytes()
        marker_evidence["brittle_provenance_tsv_present"] = BRITTLE_MARKER in data
        marker_evidence["stable_markers"] = {
            marker.decode("utf-8"): marker in data
            for marker in STABLE_MARKERS
        }
        require(BRITTLE_MARKER not in data, errors, "brittle provenance.tsv marker unexpectedly present")
        for marker in STABLE_MARKERS:
            require(marker in data, errors, f"stable provenance marker missing: {marker!r}")

    runtime = preflight.get("runtime_artifacts") or {}
    llama_entry = runtime.get("llama") or {}
    require(llama_entry.get("sha256") == EXPECTED_BUILD_HASHES["llama_lib_sha256"], errors, "historical preflight libllama SHA mismatch")
    old_markers = llama_entry.get("required_markers") or {}
    for marker in ("tensor_ptr", "src0_ptr", "src1_ptr"):
        require(old_markers.get(marker) is True, errors, f"historical preflight did not already prove schema marker: {marker}")
    require(old_markers.get("provenance.tsv") is False, errors, "historical preflight provenance.tsv state unexpected")

    classification = (
        "GENERATION_E_BINARY_MARKER_FALSE_NEGATIVE_RECONCILED"
        if not errors
        else "GENERATION_E_BINARY_MARKER_RECONCILIATION_FAILED"
    )
    out = {
        "classification": classification,
        "source_preparation_generation": EXPECTED_GENERATION,
        "prep_root": str(root),
        "historical_preflight_status": preflight.get("status"),
        "historical_preflight_errors": preflight_errors,
        "libllama_path": str(llama_path) if llama_path else None,
        "libllama_sha256": sha256(llama_path) if llama_path is not None and llama_path.is_file() else None,
        "marker_evidence": marker_evidence,
        "expected_stable_markers": [x.decode("utf-8") for x in STABLE_MARKERS],
        "errors": errors,
        "physical_calls": 0,
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
        "measured_requests": 0,
        "measured_attempt_consumed": False,
        "scientific_spend_consumed": False,
    }
    args.out.mkdir(parents=True)
    (args.out / "terminal.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())

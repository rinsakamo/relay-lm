#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BUILD = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-build-run.sh"
QUAL = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-qualification-run.sh"
PREP = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-prepare-run.sh"
PREFLIGHT = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-binary-preflight.py"
STARTUP_RUN = HERE / "e2d2c0d6-gemma4-kv-startup-recovery-run.sh"
STARTUP = HERE / "e2d2c0d6-gemma4-kv-startup-recovery.sh"
RESOURCE_GUARD = HERE / "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py"
RESOURCE_GUARD_SELFTEST = HERE / "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard-selftest.py"
STARTUP_CLASSIFIER = HERE / "e2d2c0d6-gemma4-kv-logical-prefix-startup-classify.py"
STARTUP_CLASSIFIER_SELFTEST = HERE / "e2d2c0d6-gemma4-kv-logical-prefix-startup-classifier-selftest.py"
PROVENANCE_POSTHOC = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-posthoc.py"
PROVENANCE_POSTHOC_SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-posthoc-selftest.py"
PROVENANCE_PATCH = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-diagnostic.patch"
E_RECONCILE = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-generation-e-binary-marker-reconcile.py"
E_RECONCILE_SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-generation-e-binary-marker-reconcile-selftest.py"

def require(cond, msg):
    if not cond:
        raise RuntimeError(msg)

def main():
    for path in (
        BUILD, QUAL, PREP, PREFLIGHT, STARTUP_RUN, STARTUP, RESOURCE_GUARD,
        RESOURCE_GUARD_SELFTEST, STARTUP_CLASSIFIER, STARTUP_CLASSIFIER_SELFTEST,
        PROVENANCE_POSTHOC, PROVENANCE_POSTHOC_SELFTEST, PROVENANCE_PATCH,
        E_RECONCILE, E_RECONCILE_SELFTEST,
    ):
        require(path.is_file(), f"missing apparatus file: {path}")

    for path in (BUILD, QUAL, PREP, STARTUP_RUN, STARTUP):
        cp = subprocess.run(["bash","-n",str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if cp.returncode != 0:
            raise RuntimeError(f"bash -n failed for {path.name}: {cp.stderr.decode('utf-8','replace')}")

    for path in (
        PREFLIGHT, RESOURCE_GUARD, RESOURCE_GUARD_SELFTEST, STARTUP_CLASSIFIER,
        STARTUP_CLASSIFIER_SELFTEST, PROVENANCE_POSTHOC, PROVENANCE_POSTHOC_SELFTEST,
        E_RECONCILE, E_RECONCILE_SELFTEST,
    ):
        cp = subprocess.run([sys.executable,"-m","py_compile",str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if cp.returncode != 0:
            raise RuntimeError(f"py_compile failed for {path.name}: {cp.stderr.decode('utf-8','replace')}")

    synthetic = {}
    for name, path, expected in (
        ("resource_guard", RESOURCE_GUARD_SELFTEST, "LOGICAL_PREFIX_RESOURCE_GUARD_SELFTEST_PASS"),
        ("startup_classifier", STARTUP_CLASSIFIER_SELFTEST, "LOGICAL_PREFIX_STARTUP_CLASSIFIER_SELFTEST_PASS"),
        ("provenance_posthoc", PROVENANCE_POSTHOC_SELFTEST, "LAYER0_PROJECTION_PROVENANCE_POSTHOC_SELFTEST_PASS"),
        ("generation_e_reconcile", E_RECONCILE_SELFTEST, "GENERATION_E_BINARY_MARKER_RECONCILIATION_SELFTEST_PASS"),
    ):
        cp = subprocess.run(
            [sys.executable, str(path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if cp.returncode != 0:
            raise RuntimeError(
                f"synthetic selftest failed for {name}: rc={cp.returncode}\n"
                f"stdout:\n{cp.stdout}\nstderr:\n{cp.stderr}"
            )
        try:
            parsed = json.loads(cp.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"synthetic selftest output is not JSON for {name}: {cp.stdout!r}") from exc
        if parsed.get("status") != expected:
            raise RuntimeError(f"synthetic selftest classification mismatch for {name}: {parsed!r}")
        synthetic[name] = parsed

    build = BUILD.read_text(encoding="utf-8")
    qual = QUAL.read_text(encoding="utf-8")
    prep = PREP.read_text(encoding="utf-8")
    preflight = PREFLIGHT.read_text(encoding="utf-8")
    startup_run = STARTUP_RUN.read_text(encoding="utf-8")
    startup = STARTUP.read_text(encoding="utf-8")
    resource_guard = RESOURCE_GUARD.read_text(encoding="utf-8")
    startup_classifier = STARTUP_CLASSIFIER.read_text(encoding="utf-8")
    provenance_posthoc = PROVENANCE_POSTHOC.read_text(encoding="utf-8")
    provenance_patch = PROVENANCE_PATCH.read_text(encoding="utf-8")
    e_reconcile = E_RECONCILE.read_text(encoding="utf-8")

    require('"preparation_generation": "provenance-preparation-20260924-f"' in build,
            "build missing preparation generation stamp")
    require('"preparation_generation": "provenance-preparation-20260924-f"' in qual,
            "qualification missing preparation generation stamp")
    require('"preparation_generation": "provenance-preparation-20260924-f"' in prep,
            "prepare missing preparation generation stamp")

    for marker in (
        "e2d2c0d6-gemma4-swa-ubatch-aligned-reuse-diagnostic.patch",
        "e2d2c0d6-gemma4-kv-logical-prefix-dump-diagnostic.patch",
        "e2d2c0d6-gemma4-layer0-projection-origin-diagnostic.patch",
        "e2d2c0d6-gemma4-layer0-projection-provenance-diagnostic.patch",
        'git -C "$src" apply --check "$provenance_patch"',
        '"primary_classification": "LAYER0_PROJECTION_PROVENANCE_BUILD_READY"',
        'libggml-cuda.so',
        '"ggml_cuda_sha256"',
    ):
        require(marker in build, f"build marker missing: {marker}")

    for marker in (
        "e2d2c0d6-gemma4-layer0-projection-provenance-binary-preflight.py",
        "e2d2c0d6-gemma4-layer0-projection-provenance-posthoc-selftest.py",
        "LAYER0_PROJECTION_PROVENANCE_BINARY_PREFLIGHT_PASS",
        "LAYER0_PROJECTION_PROVENANCE_PREMEASURED_READY",
        'gpu0.get("driver_version") != "591.44"',
        'gpu0.get("memory_total_mib") != 12288',
        '"generated_requests": 0',
        '"measured_l0_submitted": False',
        '"measured_attempt_consumed": False',
        '"measured_execution_authorized_by_this_result": False',
    ):
        require(marker in qual, f"qualification marker missing: {marker}")

    for marker in (
        "LAYER0_PROJECTION_PROVENANCE_BUILD_READY",
        "LAYER0_PROJECTION_PROVENANCE_PREMEASURED_READY",
        "LAYER0_PROJECTION_PROVENANCE_PREPARATION_FAILED",
        '"generated_requests": 0',
        '"measured_l0_submitted": False',
        '"measured_attempt_consumed": False',
        '"measured_execution_authorized_by_this_result": False',
    ):
        require(marker in prep, f"prepare marker missing: {marker}")

    require('"provenance.tsv"' in provenance_patch,
            "provenance patch no longer writes provenance.tsv")
    require('provenance tensor missing: %s' in provenance_patch,
            "provenance patch missing stable runtime failure marker")
    require('b"provenance.tsv"' not in preflight,
            "binary preflight regressed to brittle provenance.tsv filename marker")

    for marker in (
        'b"provenance tensor missing: %s"',
        'b"tensor_ptr"',
        'b"src0_ptr"',
        'b"src1_ptr"',
        '"LAYER0_PROJECTION_PROVENANCE_BINARY_PREFLIGHT_PASS"',
        '"projection_provenance_patch_sha256"',
        '"ggml_cuda"',
        'b"GGML_CUDA_GRAPH_OPT"',
    ):
        require(marker in preflight, f"preflight marker missing: {marker}")

    # Reject concrete measured/generation execution paths, not descriptive
    # fail-closed assertions such as "campaign queue receipt was not created".
    forbidden_execution_markers = (
        "/completion",
        "/v1/chat/completions",
        "scientific --execute",
        "layer0-projection-origin-measured-run.py",
        "layer0-projection-origin-execute-once.py",
        "layer0-projection-provenance-measured-run.py",
        "layer0-projection-provenance-execute-once.py",
    )
    for name,text in (
        ("build",build),
        ("qualification",qual),
        ("prepare",prep),
        ("preflight",preflight),
        ("startup-run",startup_run),
        ("startup",startup),
        ("resource-guard",resource_guard),
        ("startup-classifier",startup_classifier),
        ("provenance-posthoc",provenance_posthoc),
        ("generation-e-reconcile",e_reconcile),
    ):
        for token in forbidden_execution_markers:
            require(
                token not in text,
                f"{name} unexpectedly contains forbidden measured/generation execution marker: {token}",
            )

    for marker in (
        'curl --silent --show-error --max-time 2',
        '/health',
        'READY_NON_GENERATIVE',
        'UNEXPECTED_DUMP_DURING_NON_GENERATIVE_PREFLIGHT',
    ):
        require(marker in startup, f"startup helper missing non-generative marker: {marker}")

    require(
        'bash "$startup"' in startup_run,
        "startup-run does not invoke the qualified startup helper",
    )
    require(
        '--evidence-root "$guard_root" --' in qual,
        "qualification does not route startup through resource guard",
    )
    require(
        'bash "$startup_run"' in qual,
        "qualification does not invoke startup-run as guarded child",
    )

    for marker in (
        'RELAYLM_DIAGNOSTIC_AUTHORITY_HEAD',
        'refs/remotes/origin/diagnostic/llama-cpp-gemma4-swa-live-prefix-20260916',
        'remote_head=$(git -C "$repo_root" rev-parse "$authority_ref")',
        'git -C "$repo_root" fetch --quiet origin',
        '+$authority_branch_ref:$authority_ref',
        'https://github.com/rinsakamo/relay-lm.git',
        'status --porcelain --untracked-files=all',
        'preparation-static-selftest.json',
        'prepared-artifact-manifest.sha256',
        'build/qualification server SHA mismatch',
        'build/qualification server-impl SHA mismatch',
        'build/qualification libllama SHA mismatch',
        '("ggml_cuda_sha256", "ggml_cuda", "libggml-cuda")',
        'build/qualification {label} SHA mismatch',
        'chmod -R a-w "$out_root"',
        '/tmp/*|/var/tmp/*',
    ):
        require(marker in prep, f"prepare missing authority/sealing marker: {marker}")

    for marker in (
        'env -i',
        'GGML_CUDA_GRAPH_OPT=0',
        'CUDA_VISIBLE_DEVICES=0',
        'runtime-environment.effective.txt',
        'proc-environ.health-ready.txt',
        'proc-maps.health-ready.txt',
        'LLAMA_PROJECTION_ORIGIN_PROBE_DIR',
        'LLAMA_PROJECTION_ORIGIN_PROBE_LABEL',
        'UNEXPECTED_PROJECTION_DUMP_DURING_NON_GENERATIVE_PREFLIGHT',
    ):
        require(marker in startup, f"startup missing hermetic runtime marker: {marker}")

    for marker in (
        'gpu_compute_processes',
        '--query-compute-apps=pid,process_name',
        'gpu-inventory.json',
        '--query-gpu=index,uuid,name,driver_version,memory.total',
        'memory_total_mib',
        'RELEASE_FAILED_CANONICAL_DIAGNOSTIC_FLOCK',
        'RELEASED_WITH_FAILURE_CANONICAL_DIAGNOSTIC_FLOCK',
    ):
        require(marker in resource_guard, f"resource guard missing GPU/finalization marker: {marker}")

    for marker in (
        'swa == 1536',
        'EXPECTED_CANONICAL_STATIC_ARGV',
        'environment_contract',
        'runtime_library_contract',
        'ggml_cuda_sha256',
    ):
        require(marker in startup_classifier, f"startup classifier missing exact runtime marker: {marker}")

    for marker in (
        'NULL_POINTERS',
        'pointer_value',
        'duplicate provenance tensor row',
        'src1_is_attn_norm_object',
        'src1_is_attn_norm_data',
    ):
        require(marker in provenance_posthoc, f"provenance posthoc missing hardening marker: {marker}")

    for marker in (
        'EXPECTED_PREP_ROOT = Path("/home/rinsa/relaylm-evidence/provenance-preparation-20260924-e-20260924T002328-107161").resolve()',
        'unexpected preserved preparation root',
        'reconciliation output must be outside preserved preparation root',
        'current repaired preflight evidence must be outside preserved preparation root',
        '--current-preflight',
        'current repaired binary preflight did not pass',
        'current repaired preflight stable marker missing',
        'expected_bin_dir = (root / "build-stage" / "build" / "bin").resolve()',
        '"server_sha256": "llama-server"',
        '"llama_lib_sha256": "libllama.so"',
        '"ggml_cuda_sha256": "libggml-cuda.so"',
        'preserved artifact path mismatch',
        'preserved artifact SHA mismatch',
        'preserved applied.patch SHA mismatch',
        'GENERATION_E_BINARY_MARKER_FALSE_NEGATIVE_RECONCILED',
    ):
        require(marker in e_reconcile, f"generation-e reconciliation missing closure marker: {marker}")

    for marker in (
        'guard.get("campaign_queue_receipt_created") is not False',
        'guard.get("campaign_queue_or_spend_artifact_touched") is not False',
    ):
        require(marker in qual, f"qualification missing fail-closed spend assertion: {marker}")

    result={
        "status":"LAYER0_PROJECTION_PROVENANCE_PREPARATION_APPARATUS_STATIC_PASS",
        "build_shell_syntax":True,
        "qualification_shell_syntax":True,
        "prepare_shell_syntax":True,
        "binary_preflight_compile":True,
        "startup_shell_syntax":True,
        "startup_run_shell_syntax":True,
        "resource_guard_compile":True,
        "transitive_non_generation_gate":True,
        "authority_binding_gate":True,
        "hermetic_runtime_gate":True,
        "gpu_quiescence_gate":True,
        "exact_runtime_contract_gate":True,
        "runtime_library_closure_gate":True,
        "provenance_pointer_identity_gate":True,
        "persistent_evidence_sealing_gate":True,
        "generation_e_binary_marker_reconciliation_gate":True,
        "synthetic_selftests":synthetic,
        "completion_or_chat_generation_paths_present":False,
        "measured_execution_authorized":False,
        "preparation_generation":"provenance-preparation-20260924-f",
    }
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

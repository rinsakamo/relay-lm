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

def require(cond, msg):
    if not cond:
        raise RuntimeError(msg)

def main():
    for path in (BUILD, QUAL, PREP, PREFLIGHT, STARTUP_RUN, STARTUP, RESOURCE_GUARD):
        require(path.is_file(), f"missing apparatus file: {path}")

    for path in (BUILD, QUAL, PREP, STARTUP_RUN, STARTUP):
        cp = subprocess.run(["bash","-n",str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if cp.returncode != 0:
            raise RuntimeError(f"bash -n failed for {path.name}: {cp.stderr.decode('utf-8','replace')}")

    for path in (PREFLIGHT, RESOURCE_GUARD):
        cp = subprocess.run([sys.executable,"-m","py_compile",str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if cp.returncode != 0:
            raise RuntimeError(f"py_compile failed for {path.name}: {cp.stderr.decode('utf-8','replace')}")

    build = BUILD.read_text(encoding="utf-8")
    qual = QUAL.read_text(encoding="utf-8")
    prep = PREP.read_text(encoding="utf-8")
    preflight = PREFLIGHT.read_text(encoding="utf-8")
    startup_run = STARTUP_RUN.read_text(encoding="utf-8")
    startup = STARTUP.read_text(encoding="utf-8")
    resource_guard = RESOURCE_GUARD.read_text(encoding="utf-8")

    require('"preparation_generation": "provenance-preparation-20260923-c"' in build,
            "build missing preparation generation stamp")
    require('"preparation_generation": "provenance-preparation-20260923-c"' in qual,
            "qualification missing preparation generation stamp")
    require('"preparation_generation": "provenance-preparation-20260923-c"' in prep,
            "prepare missing preparation generation stamp")

    for marker in (
        "e2d2c0d6-gemma4-swa-ubatch-aligned-reuse-diagnostic.patch",
        "e2d2c0d6-gemma4-kv-logical-prefix-dump-diagnostic.patch",
        "e2d2c0d6-gemma4-layer0-projection-origin-diagnostic.patch",
        "e2d2c0d6-gemma4-layer0-projection-provenance-diagnostic.patch",
        'git -C "$src" apply --check "$provenance_patch"',
        '"primary_classification": "LAYER0_PROJECTION_PROVENANCE_BUILD_READY"',
    ):
        require(marker in build, f"build marker missing: {marker}")

    for marker in (
        "e2d2c0d6-gemma4-layer0-projection-provenance-binary-preflight.py",
        "e2d2c0d6-gemma4-layer0-projection-provenance-posthoc-selftest.py",
        "LAYER0_PROJECTION_PROVENANCE_BINARY_PREFLIGHT_PASS",
        "LAYER0_PROJECTION_PROVENANCE_PREMEASURED_READY",
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

    for marker in (
        'b"provenance.tsv"',
        'b"tensor_ptr"',
        'b"src0_ptr"',
        'b"src1_ptr"',
        '"LAYER0_PROJECTION_PROVENANCE_BINARY_PREFLIGHT_PASS"',
        '"projection_provenance_patch_sha256"',
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
        "completion_or_chat_generation_paths_present":False,
        "measured_execution_authorized":False,
        "preparation_generation":"provenance-preparation-20260923-c",
    }
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

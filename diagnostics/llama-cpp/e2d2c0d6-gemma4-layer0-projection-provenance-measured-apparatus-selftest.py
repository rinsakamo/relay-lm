#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
DESCRIPTOR = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-measured-descriptor.py"
RUNNER = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-measured-run.py"
RUNNER_SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-measured-run-selftest.py"
EXECUTE_ONCE = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-execute-once.py"
EXECUTE_SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-execute-once-selftest.py"
POSTHOC = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-posthoc.py"
POSTHOC_SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-posthoc-selftest.py"
DIGEST = HERE / "e2d2c0d6-gemma4-canonical-kv-directory-digest.py"
DIGEST_SELFTEST = HERE / "e2d2c0d6-gemma4-canonical-kv-directory-digest-selftest.py"
RESOURCE_GUARD = HERE / "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py"
RESOURCE_GUARD_SELFTEST = HERE / "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard-selftest.py"
DESCRIPTOR_PREP = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-measured-descriptor-prepare.py"
DESCRIPTOR_LAUNCHER = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-measured-descriptor-prepare-run.sh"

def require(cond, message):
    if not cond:
        raise RuntimeError(message)

def run_json(path: Path, expected_status: str):
    cp = subprocess.run(
        [sys.executable, str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"{path.name} failed rc={cp.returncode}\nstdout={cp.stdout}\nstderr={cp.stderr}")
    obj = json.loads(cp.stdout)
    require(obj.get("status") == expected_status, f"{path.name} status mismatch: {obj!r}")
    return obj

def main():
    files = (
        DESCRIPTOR, RUNNER, RUNNER_SELFTEST, EXECUTE_ONCE, EXECUTE_SELFTEST,
        POSTHOC, POSTHOC_SELFTEST, DIGEST, DIGEST_SELFTEST,
        RESOURCE_GUARD, RESOURCE_GUARD_SELFTEST, DESCRIPTOR_PREP,
    )
    for path in files:
        require(path.is_file(), f"missing measured apparatus file: {path}")
        cp = subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        require(cp.returncode == 0, f"py_compile failed for {path.name}: {cp.stderr.decode('utf-8','replace')}")

    require(DESCRIPTOR_LAUNCHER.is_file(), f"missing descriptor launcher: {DESCRIPTOR_LAUNCHER}")
    launcher_syntax = subprocess.run(
        ["bash", "-n", str(DESCRIPTOR_LAUNCHER)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        launcher_syntax.returncode == 0,
        f"bash -n failed for descriptor launcher: {launcher_syntax.stderr.decode('utf-8','replace')}",
    )

    synthetic = {
        "runner": run_json(
            RUNNER_SELFTEST,
            "LAYER0_PROJECTION_PROVENANCE_MEASURED_RUNNER_SELFTEST_PASS",
        ),
        "execute_once": run_json(
            EXECUTE_SELFTEST,
            "LAYER0_PROJECTION_PROVENANCE_EXECUTE_ONCE_SELFTEST_PASS",
        ),
        "posthoc": run_json(
            POSTHOC_SELFTEST,
            "LAYER0_PROJECTION_PROVENANCE_POSTHOC_SELFTEST_PASS",
        ),
        "digest": run_json(
            DIGEST_SELFTEST,
            "CANONICAL_KV_DIRECTORY_DIGEST_SELFTEST_PASS",
        ),
        "resource_guard": run_json(
            RESOURCE_GUARD_SELFTEST,
            "LOGICAL_PREFIX_RESOURCE_GUARD_SELFTEST_PASS",
        ),
    }

    descriptor = DESCRIPTOR.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    wrapper = EXECUTE_ONCE.read_text(encoding="utf-8")
    posthoc = POSTHOC.read_text(encoding="utf-8")
    descriptor_prep = DESCRIPTOR_PREP.read_text(encoding="utf-8")
    descriptor_launcher = DESCRIPTOR_LAUNCHER.read_text(encoding="utf-8")

    for marker in (
        'EXPECTED_PREMEASURED_ROOT = Path("/home/rinsa/relaylm-evidence/provenance-preparation-generation-f-20260925T102433Z-474088").resolve()',
        'EXPECTED_AUTHORITY_HEAD = "a68beee0537e1ebc9845a12c73f2b588cdc9dd66"',
        'EXPECTED_AUTHORITY_TREE = "e9bee1fdd86f4d321182beb579376959f4b90930"',
        'LAYER0_PROJECTION_PROVENANCE_PREMEASURED_READY',
        'prepared-artifact-manifest.sha256',
        'verify_sealed(root)',
        'verify_manifest(root)',
        'measured_execution_authorized_by_this_result": False',
        'LAYER0_PROJECTION_PROVENANCE_MEASURED_DESCRIPTOR_READY',
    ):
        require(marker in descriptor, f"descriptor materializer missing authority marker: {marker}")

    for forbidden in (
        'http.client',
        '"/completion"',
        '"/v1/chat/completions"',
        'subprocess.Popen',
        'nvidia-smi',
        'scientific --execute',
    ):
        require(forbidden not in descriptor, f"descriptor materializer unexpectedly physical: {forbidden}")

    for marker in (
        'RELAYLM_PROVENANCE_MEASURED_DESCRIPTOR_SHA256',
        'LAYER0_PROJECTION_PROVENANCE_MEASURED_PREFLIGHT_PASS',
        'EXPECTED_W_HISTORICAL_DIGEST',
        'EXPECTED_C_HISTORICAL_DIGEST',
        'canonical_argv_payload',
        'measured/startup canonical argv SHA',
        'http_post_raw(server.port, "/completion", raw)',
        'send_request(W, "W"',
        'send_request(C, "C"',
        'subject_kv_matches_historical": True',
        'verify_runtime_identity',
        'runtime-library-closure.json',
        '"GGML_CUDA_DISABLE_FUSION" in env',
    ):
        require(marker in runner, f"measured runner missing marker: {marker}")

    require(runner.count('send_request(W, "W"') == 1, "measured runner W send count != 1")
    require(runner.count('send_request(C, "C"') == 1, "measured runner C send count != 1")
    require('/v1/chat/completions' not in runner, "chat completion path present in measured runner")

    for marker in (
        'RELAYLM_PROVENANCE_MEASURED_DESCRIPTOR_SHA256',
        'subprocess.run(guard_cmd, check=False)',
        'LAYER0_PROJECTION_PROVENANCE_PROBE_EXERCISED_INCOMPLETE',
        'LAYER0_PROJECTION_PROVENANCE_PROBE_NOT_EXERCISED',
        '"rerun_authorized": False',
        '"campaign_queue_receipt_created": False',
        '"campaign_queue_or_spend_artifact_touched": False',
    ):
        require(marker in wrapper, f"execute-once wrapper missing marker: {marker}")
    require(wrapper.count("subprocess.run(guard_cmd, check=False)") == 1, "guarded measured child invocation surface != 1")

    for marker in (
        'LAYER0_PROJECTION_PROVENANCE_MEASURED_APPARATUS_STATIC_PASS',
        'LAYER0_PROJECTION_PROVENANCE_MEASURED_DESCRIPTOR_TRANSACTION_READY',
        'descriptor_materializer_invocations": 1',
        'physical_calls": 0',
        'gpu_calls": 0',
        'model_loads": 0',
        'generation_requests": 0',
        'measured_requests": 0',
        'measured_execution_authorized_by_this_result": False',
    ):
        require(marker in descriptor_prep, f"descriptor transaction orchestrator missing marker: {marker}")

    for forbidden in (
        'e2d2c0d6-gemma4-layer0-projection-provenance-measured-run.py',
        'e2d2c0d6-gemma4-layer0-projection-provenance-execute-once.py',
        'e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py',
        '"/completion"',
        '"/v1/chat/completions"',
        'nvidia-smi',
        'subprocess.Popen',
    ):
        require(forbidden not in descriptor_prep, f"descriptor transaction orchestrator unexpectedly physical: {forbidden}")

    for marker in (
        'output root must not exist before canonical launcher',
        'exec env -u PYTHONPYCACHEPREFIX',
        'PYTHONDONTWRITEBYTECODE=1',
        'e2d2c0d6-gemma4-layer0-projection-provenance-measured-descriptor-prepare.py',
    ):
        require(marker in descriptor_launcher, f"descriptor launcher missing marker: {marker}")

    require(
        'PYTHONPYCACHEPREFIX="' not in descriptor_launcher,
        "descriptor launcher regressed to output-root pycache prefix",
    )

    for marker in (
        'provenance.tsv',
        'K_V_DISTINCT_RUNTIME_PROVENANCE_IDENTICAL_VALUES_REPRODUCED',
        'K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_IDENTICAL_SOURCE_SEMANTICS_UNEXPECTED',
        'K_V_RUNTIME_PROVENANCE_MIXED_ACROSS_DUMPS',
    ):
        require(marker in posthoc, f"provenance posthoc marker missing: {marker}")

    result = {
        "status": "LAYER0_PROJECTION_PROVENANCE_MEASURED_APPARATUS_STATIC_PASS",
        "descriptor_generation": "provenance-measured-descriptor-20260925-b",
        "attempt_id": "layer0-projection-provenance-20260925-a",
        "synthetic_selftests": synthetic,
        "physical_calls": 0,
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
        "measured_requests": 0,
        "descriptor_transaction_gate": True,
        "descriptor_launcher_gate": True,
        "measured_execution_authorized": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

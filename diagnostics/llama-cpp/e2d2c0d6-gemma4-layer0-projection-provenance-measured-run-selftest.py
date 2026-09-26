#!/usr/bin/env python3
import importlib.util
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-measured-run.py"

def load_module():
    spec = importlib.util.spec_from_file_location("projection_provenance_runner", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load provenance measured runner")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    m = load_module()
    checks = []

    l0 = m.FIXTURE / "L0.request.json"
    lc = m.FIXTURE / "LC.request.json"
    m.validate_request(l0, m.EXPECTED_L0_SHA, 883, True)
    m.validate_request(lc, m.EXPECTED_LC_SHA, 2927, False)
    w_prompt = json.loads(l0.read_text(encoding="utf-8"))["prompt"]
    c_prompt = json.loads(lc.read_text(encoding="utf-8"))["prompt"]
    if w_prompt[:512] != c_prompt[:512]:
        raise RuntimeError("frozen W/C first 512 tokens differ")
    checks.append("committed_request_identity_and_prefix")

    server = Path("/home/rinsa/example/bin/llama-server")
    model = Path("/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf")
    payload = m.canonical_argv_payload(server, model)
    text = payload.decode("utf-8")
    for marker in (
        "server_bin=/home/rinsa/example/bin/llama-server\n",
        "model_path=/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf\n",
        "--ctx-size=8192\n",
        "--parallel=1\n",
        "--gpu-layers=999\n",
        "--no-context-shift\n",
        "--batch-size=512\n",
        "--ubatch-size=512\n",
        "--flash-attn=on\n",
        "--log-verbosity=4\n",
    ):
        if marker not in text:
            raise RuntimeError(f"canonical argv marker missing: {marker!r}")
    checks.append("canonical_argv_contract")

    source = TARGET.read_text(encoding="utf-8")
    if source.count('send_request(W, "W"') != 1:
        raise RuntimeError("runner must contain exactly one W send site")
    if source.count('send_request(C, "C"') != 1:
        raise RuntimeError("runner must contain exactly one C send site")
    if source.count('http_post_raw(server.port, "/completion", raw)') != 1:
        raise RuntimeError("runner must contain exactly one generic completion POST site")
    for forbidden in (
        "/v1/chat/completions",
        'send_request(W, "L1"',
        "WR2",
        '"L0R"',
        "--flash-attn\", \"off",
    ):
        if forbidden in source:
            raise RuntimeError(f"forbidden measured surface present: {forbidden}")
    checks.append("exact_two_request_surface")

    for marker in (
        '"CUDA_VISIBLE_DEVICES": "0"',
        '"GGML_CUDA_GRAPH_OPT": "0"',
        '"PATH": "/usr/local/cuda-12.8/bin:/usr/bin:/bin"',
        '"LANG": "C.UTF-8"',
        '"LC_ALL": "C.UTF-8"',
        '"LLAMA_KV_PROBE_LABEL": self.label',
        '"LLAMA_PROJECTION_ORIGIN_PROBE_LABEL": self.label',
        '"GGML_CUDA_DISABLE_FUSION" in env',
    ):
        if marker not in source:
            raise RuntimeError(f"hermetic runtime marker missing: {marker}")
    for marker in (
        "durable_mkdir(args.out_root)",
        "durable_mkdir(self.out)",
        "durable_write_bytes(record, raw)",
        "os.fsync(f.fileno())",
        "proc-executable.health-ready.txt",
        'require_equal(cmdline, self.command(), f"{self.label}: proc cmdline")',
        "unexpected KV dump directories",
        "unexpected projection dump directories",
        "measured-artifact-manifest.sha256",
        "seal_measured_root(args.out_root)",
        "descriptor measured attempt",
        "descriptor measured apparatus closure incomplete",
    ):
        if marker not in source:
            raise RuntimeError(f"measured hardening marker missing: {marker}")
    checks.append("durability_runtime_identity_and_sealing")

    checks.append("hermetic_runtime_contract")

    if m.EXPECTED_W_HISTORICAL_DIGEST == m.EXPECTED_C_HISTORICAL_DIGEST:
        raise RuntimeError("historical W/C digests unexpectedly equal")
    checks.append("historical_subject_digest_pins")

    expected_classes = {
        "K_V_DISTINCT_RUNTIME_PROVENANCE_IDENTICAL_VALUES_REPRODUCED",
        "K_V_RUNTIME_TENSOR_OBJECT_ALIAS",
        "K_V_RUNTIME_OUTPUT_DATA_ALIAS",
        "K_V_RUNTIME_WEIGHT_SOURCE_ALIAS",
        "K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_IDENTICAL_SOURCE_SEMANTICS_UNEXPECTED",
        "K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_DISTINCT",
        "K_V_RUNTIME_PROVENANCE_MIXED_ACROSS_DUMPS",
    }
    if m.ALLOWED_CLASSIFICATIONS != expected_classes:
        raise RuntimeError("allowed provenance classification set drifted")
    checks.append("terminal_classification_closed_set")

    print(json.dumps({
        "status": "LAYER0_PROJECTION_PROVENANCE_MEASURED_RUNNER_SELFTEST_PASS",
        "checks": checks,
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
        "measured_requests": 0,
    }, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

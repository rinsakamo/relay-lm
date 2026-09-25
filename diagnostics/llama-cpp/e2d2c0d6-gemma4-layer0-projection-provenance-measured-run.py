#!/usr/bin/env python3
import argparse
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

ATTEMPT_ID = "layer0-projection-provenance-20260925-a"
EXPECTED_DESCRIPTOR_GENERATION = "provenance-measured-descriptor-20260925-a"
EXPECTED_PREMEASURED_ROOT = Path("/home/rinsa/relaylm-evidence/provenance-preparation-generation-f-20260925T102433Z-474088").resolve()
EXPECTED_MODEL_SHA = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
EXPECTED_W_HISTORICAL_DIGEST = "492663002bf7f1c37d7df2e346d7eff38ff21d6225040c21e07f8fa4984b7ce6"
EXPECTED_C_HISTORICAL_DIGEST = "c7a5bfc7ea2176fd26b32ee0d45e644ca8737facd11f00647850001d45f373d2"
EXPECTED_L0_SHA = "d777877485b3307d8ee76e6b6df783d00b4302bb700c405ac5cbf2f6d7344f5d"
EXPECTED_LC_SHA = "63afb2a44ea12f14377ba52348616a0bd8ac3ebdd65d81d1a3ede1c4c2c64043"

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "e2d2c0d6-gemma4-kv-v2"
POSTHOC = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-posthoc.py"
DIGEST_TOOL = HERE / "e2d2c0d6-gemma4-canonical-kv-directory-digest.py"

ALLOWED_CLASSIFICATIONS = {
    "K_V_DISTINCT_RUNTIME_PROVENANCE_IDENTICAL_VALUES_REPRODUCED",
    "K_V_RUNTIME_TENSOR_OBJECT_ALIAS",
    "K_V_RUNTIME_OUTPUT_DATA_ALIAS",
    "K_V_RUNTIME_WEIGHT_SOURCE_ALIAS",
    "K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_IDENTICAL_SOURCE_SEMANTICS_UNEXPECTED",
    "K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_DISTINCT",
    "K_V_RUNTIME_PROVENANCE_MIXED_ACROSS_DUMPS",
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

def require_equal(observed, expected, label):
    if observed != expected:
        raise RuntimeError(f"{label}: {observed!r} != {expected!r}")

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def require_port_free(port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"port {port} is not free: {exc}") from exc

def validate_request(path: Path, expected_sha: str, expected_len: int, expected_cache: bool):
    if not path.is_file():
        raise RuntimeError(f"request missing: {path}")
    require_equal(sha256(path), expected_sha, f"{path.name} SHA256")
    obj = load_json(path)
    prompt = obj.get("prompt")
    if not isinstance(prompt, list) or len(prompt) != expected_len:
        raise RuntimeError(f"{path.name}: prompt length mismatch")
    require_equal(obj.get("cache_prompt"), expected_cache, f"{path.name} cache_prompt")
    require_equal(obj.get("n_predict"), 1, f"{path.name} n_predict")
    require_equal(obj.get("temperature"), 0, f"{path.name} temperature")
    require_equal(obj.get("stream"), False, f"{path.name} stream")

def validate_descriptor(descriptor_path: Path, model: Path):
    expected_sha = os.environ.get("RELAYLM_PROVENANCE_MEASURED_DESCRIPTOR_SHA256", "")
    if len(expected_sha) != 64:
        raise RuntimeError("RELAYLM_PROVENANCE_MEASURED_DESCRIPTOR_SHA256 is required")
    if not descriptor_path.is_file():
        raise RuntimeError(f"descriptor missing: {descriptor_path}")
    require_equal(sha256(descriptor_path), expected_sha, "descriptor SHA256")
    d = load_json(descriptor_path)
    require_equal(d.get("descriptor_generation"), EXPECTED_DESCRIPTOR_GENERATION, "descriptor generation")
    require_equal(d.get("classification"), "LAYER0_PROJECTION_PROVENANCE_MEASURED_DESCRIPTOR_READY", "descriptor classification")
    root = Path(d.get("premeasured_root", "")).resolve()
    require_equal(root, EXPECTED_PREMEASURED_ROOT, "descriptor premeasured root")
    require_equal((d.get("model") or {}).get("path"), str(model.resolve()), "descriptor model path")
    require_equal((d.get("model") or {}).get("sha256"), EXPECTED_MODEL_SHA, "descriptor model SHA")
    if not model.is_file():
        raise RuntimeError(f"model missing: {model}")
    require_equal(sha256(model), EXPECTED_MODEL_SHA, "model SHA256")

    runtime = d.get("runtime") or {}
    required = {
        "llama_server", "llama_server_impl", "llama", "ggml",
        "ggml_base", "ggml_cpu", "ggml_cuda",
    }
    if set(runtime) != required:
        raise RuntimeError(f"descriptor runtime set mismatch: {sorted(runtime)}")
    for name, entry in runtime.items():
        p = Path(entry.get("path", "")).resolve()
        if not p.is_file():
            raise RuntimeError(f"runtime artifact missing: {name}: {p}")
        require_equal(sha256(p), entry.get("sha256"), f"runtime SHA: {name}")

    argv_sha = d.get("startup_canonical_argv_sha256")
    if not isinstance(argv_sha, str) or len(argv_sha) != 64:
        raise RuntimeError("descriptor startup canonical argv SHA invalid")
    server_path = Path(runtime["llama_server"]["path"]).resolve()
    measured_argv_sha = hashlib.sha256(canonical_argv_payload(server_path, model)).hexdigest()
    require_equal(measured_argv_sha, argv_sha, "measured/startup canonical argv SHA")

    return d

def canonical_argv_payload(server: Path, model: Path) -> bytes:
    lines = [
        f"server_bin={server}",
        f"model_path={model}",
        "--host=127.0.0.1",
        "--ctx-size=8192",
        "--parallel=1",
        "--gpu-layers=999",
        "--no-context-shift",
        "--batch-size=512",
        "--ubatch-size=512",
        "--flash-attn=on",
        "--log-verbosity=4",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")

def http_get(port: int, path: str, timeout=2):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.request("GET", path)
        res = conn.getresponse()
        body = res.read()
        return res.status, body
    finally:
        conn.close()

def http_post_raw(port: int, path: str, body: bytes, timeout=600):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.request("POST", path, body=body, headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        res = conn.getresponse()
        data = res.read()
        return res.status, dict(res.getheaders()), data
    finally:
        conn.close()

class Server:
    def __init__(self, *, descriptor, model: Path, port: int, label: str, kv_root: Path, projection_root: Path, out: Path):
        self.descriptor = descriptor
        self.binary = Path(descriptor["runtime"]["llama_server"]["path"])
        self.model = model
        self.port = port
        self.label = label
        self.kv_root = kv_root
        self.projection_root = projection_root
        self.out = out
        self.proc = None
        self.stdout = None
        self.stderr = None

    def command(self):
        return [
            str(self.binary),
            "--model", str(self.model),
            "--host", "127.0.0.1",
            "--port", str(self.port),
            "--ctx-size", "8192",
            "--parallel", "1",
            "--gpu-layers", "999",
            "--no-context-shift",
            "--batch-size", "512",
            "--ubatch-size", "512",
            "--flash-attn", "on",
            "--log-verbosity", "4",
        ]

    def start(self):
        self.out.mkdir(parents=True, exist_ok=False)
        (self.out / "hermetic-home").mkdir()
        (self.out / "hermetic-tmp").mkdir()
        write_json(self.out / "argv.json", self.command())
        server_dir = self.binary.parent
        env = {
            "HOME": str(self.out / "hermetic-home"),
            "TMPDIR": str(self.out / "hermetic-tmp"),
            "PATH": "/usr/local/cuda-12.8/bin:/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "LD_LIBRARY_PATH": f"{server_dir}:/usr/local/cuda-12.8/lib64",
            "CUDA_VISIBLE_DEVICES": "0",
            "GGML_CUDA_GRAPH_OPT": "0",
            "LLAMA_KV_PROBE_DIR": str(self.kv_root),
            "LLAMA_KV_PROBE_LABEL": self.label,
            "LLAMA_PROJECTION_ORIGIN_PROBE_DIR": str(self.projection_root),
            "LLAMA_PROJECTION_ORIGIN_PROBE_LABEL": self.label,
        }
        write_json(self.out / "runtime-env.json", env)
        if "GGML_CUDA_DISABLE_FUSION" in env:
            raise RuntimeError("GGML_CUDA_DISABLE_FUSION unexpectedly set")

        self.stdout = (self.out / "server.stdout.txt").open("wb")
        self.stderr = (self.out / "server.stderr.txt").open("wb")
        self.proc = subprocess.Popen(self.command(), stdout=self.stdout, stderr=self.stderr, env=env)
        (self.out / "server.pid.txt").write_text(f"{self.proc.pid}\n", encoding="utf-8")

        attempts = []
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            rc = self.proc.poll()
            if rc is not None:
                raise RuntimeError(f"{self.label}: server exited before health: {rc}")
            try:
                status, body = http_get(self.port, "/health")
                attempts.append({"status": status, "body": body.decode("utf-8", "replace")})
                if status == 200:
                    write_json(self.out / "startup.json", {"ready": True, "attempts": attempts})
                    return
            except Exception as exc:
                attempts.append({"error": repr(exc)})
            time.sleep(1)
        write_json(self.out / "startup.json", {"ready": False, "attempts": attempts})
        raise RuntimeError(f"{self.label}: health timeout")

    def stop(self):
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.send_signal(signal.SIGTERM)
            try:
                self.proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=10)
        (self.out / "server.exit-code.txt").write_text(f"{self.proc.returncode}\n", encoding="utf-8")
        if self.stdout:
            self.stdout.close()
        if self.stderr:
            self.stderr.close()

def send_request(server: Server, name: str, request_path: Path, expected_prompt: int):
    raw = request_path.read_bytes()
    record = server.out / f"{name}.request.json"
    record.write_bytes(raw)
    (server.out / f"{name}.request.sha256.txt").write_text(hashlib.sha256(raw).hexdigest() + "\n", encoding="utf-8")
    status, headers, body = http_post_raw(server.port, "/completion", raw)
    write_json(server.out / f"{name}.http.json", {"status": status, "headers": headers})
    (server.out / f"{name}.response.raw.json").write_bytes(body)
    if status != 200:
        raise RuntimeError(f"{name}: HTTP {status}")
    obj = json.loads(body)
    write_json(server.out / f"{name}.response.pretty.json", obj)
    timings = obj.get("timings") or {}
    require_equal(timings.get("cache_n"), 0, f"{name} cache_n")
    require_equal(timings.get("prompt_n"), expected_prompt, f"{name} prompt_n")
    require_equal(timings.get("predicted_n"), 1, f"{name} predicted_n")

def digest_kv_dir(path: Path):
    mod = load_module(DIGEST_TOOL, "relaylm_provenance_kv_digest")
    return mod.digest_directory(path)

def validate_inputs(args):
    if args.port_w == args.port_c:
        raise RuntimeError("W and C ports must differ")
    require_port_free(args.port_w)
    require_port_free(args.port_c)
    if not POSTHOC.is_file() or not DIGEST_TOOL.is_file():
        raise RuntimeError("required diagnostic helper missing")
    l0 = FIXTURE / "L0.request.json"
    lc = FIXTURE / "LC.request.json"
    validate_request(l0, EXPECTED_L0_SHA, 883, True)
    validate_request(lc, EXPECTED_LC_SHA, 2927, False)
    descriptor = validate_descriptor(args.descriptor, args.model)
    return {
        "attempt_id": ATTEMPT_ID,
        "descriptor_sha256": sha256(args.descriptor),
        "descriptor": descriptor,
        "requests": {"W": EXPECTED_L0_SHA, "C": EXPECTED_LC_SHA},
        "ports": {"W": args.port_w, "C": args.port_c},
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--descriptor", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--out-root", type=Path)
    ap.add_argument("--port-w", type=int, required=True)
    ap.add_argument("--port-c", type=int, required=True)
    ap.add_argument("--preflight-only", action="store_true")
    args = ap.parse_args()

    identity = validate_inputs(args)
    if args.preflight_only:
        print(json.dumps({
            "classification": "LAYER0_PROJECTION_PROVENANCE_MEASURED_PREFLIGHT_PASS",
            "attempt_id": ATTEMPT_ID,
            "descriptor_sha256": identity["descriptor_sha256"],
            "requests": identity["requests"],
            "ports": identity["ports"],
            "generated_requests": 0,
            "measured_requests": 0,
            "measured_w_submitted": False,
            "measured_attempt_consumed": False,
        }, indent=2, sort_keys=True))
        return 0

    if args.out_root is None:
        raise RuntimeError("--out-root is required for measured execution")
    if args.out_root.exists():
        raise RuntimeError(f"out root must not exist: {args.out_root}")
    args.out_root.mkdir(parents=True)
    write_json(args.out_root / "identity.json", identity)

    kv_root = args.out_root / "kv"
    projection_root = args.out_root / "projection"

    W = Server(
        descriptor=identity["descriptor"], model=args.model, port=args.port_w, label="W",
        kv_root=kv_root, projection_root=projection_root, out=args.out_root / "server-W",
    )
    C = Server(
        descriptor=identity["descriptor"], model=args.model, port=args.port_c, label="C",
        kv_root=kv_root, projection_root=projection_root, out=args.out_root / "server-C",
    )

    try:
        W.start()
        send_request(W, "W", FIXTURE / "L0.request.json", 883)
    finally:
        W.stop()

    try:
        C.start()
        send_request(C, "C", FIXTURE / "LC.request.json", 2927)
    finally:
        C.stop()

    required = [
        kv_root / "W-P512",
        kv_root / "C-P512",
        projection_root / "W-p0-370-w371",
        projection_root / "W-p371-878-w508",
        projection_root / "C-p0-511-w512",
    ]
    missing = [str(p) for p in required if not p.is_dir()]
    if missing:
        raise RuntimeError(f"required measured dumps missing: {missing}")

    w_digest = digest_kv_dir(kv_root / "W-P512")
    c_digest = digest_kv_dir(kv_root / "C-P512")
    require_equal(w_digest["directory_sha256"], EXPECTED_W_HISTORICAL_DIGEST, "instrumented W historical digest")
    require_equal(c_digest["directory_sha256"], EXPECTED_C_HISTORICAL_DIGEST, "instrumented C historical digest")
    write_json(args.out_root / "instrumented-kv-digests.json", {"W": w_digest, "C": c_digest})

    posthoc_out = args.out_root / "posthoc"
    run = subprocess.run([
        sys.executable, str(POSTHOC),
        "--projection-root", str(projection_root),
        "--out", str(posthoc_out),
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    (args.out_root / "posthoc.stdout.json").write_bytes(run.stdout)
    (args.out_root / "posthoc.stderr.txt").write_bytes(run.stderr)
    if run.returncode != 0:
        raise RuntimeError(f"provenance posthoc failed rc={run.returncode}")

    terminal_path = posthoc_out / "terminal.json"
    if not terminal_path.is_file():
        raise RuntimeError("provenance posthoc terminal missing")
    posthoc = load_json(terminal_path)
    require_equal(posthoc.get("classification"), "LAYER0_PROJECTION_PROVENANCE_POSTHOC_COMPLETE", "posthoc completion")
    classification = posthoc.get("scientific_classification")
    if classification not in ALLOWED_CLASSIFICATIONS:
        raise RuntimeError(f"unexpected provenance scientific classification: {classification}")

    terminal = {
        "attempt_id": ATTEMPT_ID,
        "primary_classification": classification,
        "descriptor_sha256": identity["descriptor_sha256"],
        "instrumented_w_kv_digest": w_digest["directory_sha256"],
        "instrumented_c_kv_digest": c_digest["directory_sha256"],
        "subject_kv_matches_historical": True,
        "measured_w_submitted": True,
        "measured_c_submitted": True,
        "measured_attempt_consumed": True,
        "rerun_authorized": False,
        "request_count": 2,
        "request_order": ["W", "C"],
        "posthoc_returncode": run.returncode,
        "posthoc_terminal": str(terminal_path),
        "generated_requests": 2,
        "measured_requests": 2,
    }
    write_json(args.out_root / "terminal.json", terminal)
    print(json.dumps(terminal, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise

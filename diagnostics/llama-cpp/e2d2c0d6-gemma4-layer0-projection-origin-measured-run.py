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

ATTEMPT_ID = "layer0-projection-origin-20260922-a5d767da"

EXPECTED_SOURCE_HEAD = "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"
EXPECTED_SOURCE_TREE = "6d39fd93dc91fc0a4bc86dffe9782d4f26318004"
EXPECTED_MODEL_SHA = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"

EXPECTED_SERVER_SHA = "a5d767da8006aaf0537594ae308fc427cdb92154f48c5a3a325be3908352c5bb"
EXPECTED_SERVER_IMPL_SHA = "2a693007d6c344c6248478d6008c5055b76d2c885012aff133bdfa1b4be6dc71"
EXPECTED_LLAMA_SHA = "533a1a35c686c8375b077fb2eec3b8e293a6ef54d1a1f3643989542ab4e3b46e"

EXPECTED_APPLIED_PATCH_SHA = "5073a690590bf22e6b437425f1f6210b2dd239b549eaeb7509fad22deb43522d"
EXPECTED_ALIGNED_PATCH_SHA = "cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a"
EXPECTED_LOGICAL_PATCH_SHA = "d62810fdc645cbb011c52047e9ba9227b1d6c29fafc0bac0e7cf659f6104e4c8"
EXPECTED_ORIGIN_PATCH_SHA = "61af8dce39b0dceb0ce12b7fef8014dcb8f94ba7564955783c5ff76c9d211674"
EXPECTED_STARTUP_ARGV_SHA = "031c7df7867ea521e2df37fa3a0a97b60a7eb2303e7c54fee5c92b55aa8b6dea"

EXPECTED_W_HISTORICAL_DIGEST = "492663002bf7f1c37d7df2e346d7eff38ff21d6225040c21e07f8fa4984b7ce6"
EXPECTED_C_HISTORICAL_DIGEST = "c7a5bfc7ea2176fd26b32ee0d45e644ca8737facd11f00647850001d45f373d2"

EXPECTED_L0_SHA = "d777877485b3307d8ee76e6b6df783d00b4302bb700c405ac5cbf2f6d7344f5d"
EXPECTED_LC_SHA = "63afb2a44ea12f14377ba52348616a0bd8ac3ebdd65d81d1a3ede1c4c2c64043"

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "e2d2c0d6-gemma4-kv-v2"
POSTHOC = HERE / "e2d2c0d6-gemma4-layer0-projection-origin-posthoc.py"
DIGEST_TOOL = HERE / "e2d2c0d6-gemma4-canonical-kv-directory-digest.py"


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
    return obj


def validate_premeasured(root: Path, model: Path):
    top = load_json(root / "terminal.json")
    build = load_json(root / "build-stage" / "terminal.json")
    qual = load_json(root / "qualification-stage" / "terminal.json")
    binary = load_json(root / "qualification-stage" / "logical-prefix-binary-preflight.json")
    startup = load_json(root / "qualification-stage" / "logical-prefix-startup-classification.json")

    require_equal(top.get("primary_classification"), "LAYER0_PROJECTION_ORIGIN_PREMEASURED_READY", "top classification")
    require_equal(build.get("primary_classification"), "LAYER0_PROJECTION_ORIGIN_BUILD_READY", "build classification")
    require_equal(qual.get("primary_classification"), "LAYER0_PROJECTION_ORIGIN_PREMEASURED_READY", "qualification classification")
    require_equal(binary.get("status"), "LAYER0_PROJECTION_ORIGIN_BINARY_PREFLIGHT_PASS", "binary preflight")
    require_equal(startup.get("primary_classification"), "LOGICAL_PREFIX_STARTUP_QUALIFIED", "startup classification")

    startup_evidence = startup.get("evidence") or {}
    for arm_name in ("plain", "probe"):
        arm = startup_evidence.get(arm_name) or {}
        require_equal(arm.get("classification"), "READY_NON_GENERATIVE", f"{arm_name} startup arm")
        require_equal(arm.get("argv_canonical_sha256"), EXPECTED_STARTUP_ARGV_SHA, f"{arm_name} canonical argv")
        checks = ((arm.get("context") or {}).get("checks") or {})
        for key in ("n_seq_max_1", "n_ctx_8192", "n_batch_512", "n_ubatch_512", "flash_attn_enabled"):
            require_equal((checks.get(key) or {}).get("ok"), True, f"{arm_name} {key}")
        swa = arm.get("compact_swa") or {}
        require_equal(swa.get("ok"), True, f"{arm_name} compact SWA")
        require_equal(swa.get("selected_base_size"), 8192, f"{arm_name} base KV")
        require_equal(swa.get("selected_swa_size"), 1536, f"{arm_name} SWA KV")
        require_equal(arm.get("unexpected_probe_output"), False, f"{arm_name} unexpected startup probe output")

    require_equal(build.get("source_head"), EXPECTED_SOURCE_HEAD, "source HEAD")
    require_equal(build.get("source_tree"), EXPECTED_SOURCE_TREE, "source tree")
    require_equal(build.get("applied_patch_sha256"), EXPECTED_APPLIED_PATCH_SHA, "applied patch")
    require_equal(build.get("aligned_reuse_patch_sha256"), EXPECTED_ALIGNED_PATCH_SHA, "aligned patch")
    require_equal(build.get("logical_prefix_patch_sha256"), EXPECTED_LOGICAL_PATCH_SHA, "logical patch")
    require_equal(build.get("projection_origin_patch_sha256"), EXPECTED_ORIGIN_PATCH_SHA, "projection patch")

    server = root / "build-stage" / "build" / "bin" / "llama-server"
    server_impl = server.parent / "libllama-server-impl.so"
    llama_lib = server.parent / "libllama.so"
    for path, expected, label in (
        (server, EXPECTED_SERVER_SHA, "server"),
        (server_impl, EXPECTED_SERVER_IMPL_SHA, "server impl"),
        (llama_lib, EXPECTED_LLAMA_SHA, "libllama"),
        (model, EXPECTED_MODEL_SHA, "model"),
    ):
        if not path.is_file():
            raise RuntimeError(f"{label} missing: {path}")
        require_equal(sha256(path), expected, f"{label} SHA256")

    require_equal(binary.get("server_sha256"), EXPECTED_SERVER_SHA, "binary server SHA")
    require_equal(binary.get("model_sha256"), EXPECTED_MODEL_SHA, "binary model SHA")
    require_equal(binary.get("aligned_reuse_patch_sha256"), EXPECTED_ALIGNED_PATCH_SHA, "binary aligned patch")
    require_equal(binary.get("logical_prefix_patch_sha256"), EXPECTED_LOGICAL_PATCH_SHA, "binary logical patch")
    require_equal(binary.get("projection_origin_patch_sha256"), EXPECTED_ORIGIN_PATCH_SHA, "binary origin patch")
    require_equal(binary.get("forbidden_old_marker_present"), False, "forbidden old marker")

    artifacts = binary.get("runtime_artifacts") or {}
    require_equal((artifacts.get("llama_server_impl") or {}).get("sha256"), EXPECTED_SERVER_IMPL_SHA, "binary server impl SHA")
    require_equal((artifacts.get("llama") or {}).get("sha256"), EXPECTED_LLAMA_SHA, "binary libllama SHA")

    for obj, label in ((top, "top"), (qual, "qualification")):
        require_equal(obj.get("generated_requests"), 0, f"{label} generated requests")
        require_equal(obj.get("measured_l0_submitted"), False, f"{label} measured_l0_submitted")
        require_equal(obj.get("measured_attempt_consumed"), False, f"{label} measured consumed")

    return {
        "root": str(root.resolve()),
        "server": str(server.resolve()),
        "server_sha256": EXPECTED_SERVER_SHA,
        "server_impl_sha256": EXPECTED_SERVER_IMPL_SHA,
        "llama_sha256": EXPECTED_LLAMA_SHA,
        "model_sha256": EXPECTED_MODEL_SHA,
    }


def validate_historical(root: Path):
    digest_mod = load_module(DIGEST_TOOL, "relaylm_kv_digest")
    w = digest_mod.digest_directory(root / "WR-P512")
    c = digest_mod.digest_directory(root / "C-P512")
    require_equal(w["directory_sha256"], EXPECTED_W_HISTORICAL_DIGEST, "historical W digest")
    require_equal(c["directory_sha256"], EXPECTED_C_HISTORICAL_DIGEST, "historical C digest")
    return {"W": w["directory_sha256"], "C": c["directory_sha256"]}


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
    def __init__(self, *, binary: Path, model: Path, port: int, label: str, kv_root: Path, projection_root: Path, out: Path):
        self.binary = binary
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
        write_json(self.out / "argv.json", self.command())
        env = os.environ.copy()
        env.update({
            "LLAMA_KV_PROBE_DIR": str(self.kv_root),
            "LLAMA_KV_PROBE_LABEL": self.label,
            "LLAMA_PROJECTION_ORIGIN_PROBE_DIR": str(self.projection_root),
            "LLAMA_PROJECTION_ORIGIN_PROBE_LABEL": self.label,
        })
        write_json(self.out / "probe-env.json", {
            k: env[k] for k in (
                "LLAMA_KV_PROBE_DIR",
                "LLAMA_KV_PROBE_LABEL",
                "LLAMA_PROJECTION_ORIGIN_PROBE_DIR",
                "LLAMA_PROJECTION_ORIGIN_PROBE_LABEL",
            )
        })
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
    record.write_bytes(raw)  # consumption record is durable before HTTP POST
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
    return obj


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

    apparatus = validate_premeasured(args.premeasured_root, args.model)
    historical = validate_historical(args.historical_kv_root)
    return {
        "attempt_id": ATTEMPT_ID,
        "apparatus": apparatus,
        "historical": historical,
        "requests": {"W": EXPECTED_L0_SHA, "C": EXPECTED_LC_SHA},
        "ports": {"W": args.port_w, "C": args.port_c},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--premeasured-root", type=Path, required=True)
    ap.add_argument("--historical-kv-root", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--out-root", type=Path)
    ap.add_argument("--port-w", type=int, required=True)
    ap.add_argument("--port-c", type=int, required=True)
    ap.add_argument("--preflight-only", action="store_true")
    args = ap.parse_args()

    identity = validate_inputs(args)
    if args.preflight_only:
        print(json.dumps({
            "classification": "LAYER0_PROJECTION_ORIGIN_MEASURED_PREFLIGHT_PASS",
            **identity,
            "generated_requests": 0,
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

    server_bin = Path(identity["apparatus"]["server"])
    kv_root = args.out_root / "kv"
    projection_root = args.out_root / "projection"

    W = Server(
        binary=server_bin, model=args.model, port=args.port_w, label="W",
        kv_root=kv_root, projection_root=projection_root, out=args.out_root / "server-W",
    )
    C = Server(
        binary=server_bin, model=args.model, port=args.port_c, label="C",
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

    posthoc_out = args.out_root / "posthoc"
    run = subprocess.run([
        sys.executable, str(POSTHOC),
        "--projection-root", str(projection_root),
        "--instrumented-kv-root", str(kv_root),
        "--historical-kv-root", str(args.historical_kv_root),
        "--out", str(posthoc_out),
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (args.out_root / "posthoc.stdout.json").write_bytes(run.stdout)
    (args.out_root / "posthoc.stderr.txt").write_bytes(run.stderr)

    terminal_path = posthoc_out / "terminal.json"
    if not terminal_path.is_file():
        raise RuntimeError(f"posthoc terminal missing; rc={run.returncode}")
    posthoc = load_json(terminal_path)
    allowed = {
        "INSTRUMENTATION_PERTURBED_SUBJECT",
        "LAYER0_PROJECTION_NUMERICAL_ORIGIN_OBSERVED",
        "LAYER0_PREPROJECTION_DIFFERENCE_OBSERVED",
        "LAYER0_PROJECTION_OUTPUT_IDENTICAL_ORIGIN_LATER",
        "LAYER0_PROJECTION_PARTIAL_OR_AMBIGUOUS",
    }
    classification = posthoc.get("primary_classification")
    if classification not in allowed:
        raise RuntimeError(f"unexpected posthoc classification: {classification}")

    terminal = {
        "attempt_id": ATTEMPT_ID,
        "primary_classification": classification,
        "measured_w_submitted": True,
        "measured_c_submitted": True,
        "measured_attempt_consumed": True,
        "rerun_authorized": False,
        "request_count": 2,
        "request_order": ["W", "C"],
        "posthoc_returncode": run.returncode,
        "posthoc_terminal": str(terminal_path),
        "generated_requests": 2,
    }
    write_json(args.out_root / "terminal.json", terminal)
    print(json.dumps(terminal, indent=2, sort_keys=True))
    return 0 if classification != "INSTRUMENTATION_PERTURBED_SUBJECT" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise

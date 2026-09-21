#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

EXPECTED_MODEL_SHA = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
MIN_TOKEN_POOL = 2945


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def port_is_free(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def http_get(url: str, timeout: float):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def http_post_raw(url: str, raw: bytes, timeout: float):
    req = urllib.request.Request(
        url,
        data=raw,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--server-bin", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--port", type=int, required=True)
    args = ap.parse_args()

    if args.out_root.exists():
        raise SystemExit(f"output root must not exist: {args.out_root}")
    if not args.server_bin.is_file():
        raise SystemExit(f"server missing: {args.server_bin}")
    if not args.model.is_file():
        raise SystemExit(f"model missing: {args.model}")
    if sha256(args.model) != EXPECTED_MODEL_SHA:
        raise SystemExit("model SHA256 mismatch")
    if not port_is_free(args.port):
        raise SystemExit(f"port not free: {args.port}")

    args.out_root.mkdir(parents=True)
    here = Path(__file__).resolve().parent
    corpus_tool = here / "e2d2c0d6-gemma4-kv-fixture-v2-corpus.py"
    if not corpus_tool.is_file():
        raise SystemExit("fixture corpus tool missing")

    corpus = args.out_root / "source-corpus.txt"
    tokenizer_request = args.out_root / "tokenizer-request.json"
    generate = subprocess.run(
        [
            sys.executable,
            str(corpus_tool),
            "--out",
            str(corpus),
            "--request-out",
            str(tokenizer_request),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (args.out_root / "corpus-generator.stdout.txt").write_bytes(generate.stdout)
    (args.out_root / "corpus-generator.stderr.txt").write_bytes(generate.stderr)
    if generate.returncode != 0:
        raise SystemExit(f"corpus generator failed: {generate.returncode}")

    cmd = [
        str(args.server_bin),
        "--model", str(args.model),
        "--host", "127.0.0.1",
        "--port", str(args.port),
        "--ctx-size", "8192",
        "--parallel", "1",
        "--gpu-layers", "999",
        "--no-context-shift",
        "--batch-size", "512",
        "--ubatch-size", "512",
        "--flash-attn", "on",
        "--log-verbosity", "4",
    ]
    write_json(args.out_root / "server.argv.json", cmd)

    stdout_path = args.out_root / "server.stdout.txt"
    stderr_path = args.out_root / "server.stderr.txt"
    process = None
    tokenization_requests = 0
    health_requests = 0
    response_raw = None
    response_status = None

    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(cmd, stdout=stdout, stderr=stderr)

            ready = False
            for attempt in range(120):
                if process.poll() is not None:
                    raise RuntimeError(f"server exited before readiness: rc={process.returncode}")
                try:
                    status, raw = http_get(
                        f"http://127.0.0.1:{args.port}/health",
                        timeout=2,
                    )
                    health_requests += 1
                    (args.out_root / "health-response.json").write_bytes(raw)
                    if status == 200:
                        ready = True
                        break
                except (urllib.error.URLError, TimeoutError, ConnectionError):
                    pass
                time.sleep(1)
            if not ready:
                raise RuntimeError("server did not become healthy")

            request_raw = tokenizer_request.read_bytes()
            response_status, response_raw = http_post_raw(
                f"http://127.0.0.1:{args.port}/tokenize",
                request_raw,
                timeout=120,
            )
            tokenization_requests += 1
            (args.out_root / "tokenizer-response.json").write_bytes(response_raw)

            if response_status != 200:
                raise RuntimeError(f"/tokenize returned HTTP {response_status}")

            obj = json.loads(response_raw)
            tokens = obj.get("tokens") if isinstance(obj, dict) else None
            if not isinstance(tokens, list):
                raise RuntimeError("/tokenize response missing tokens list")
            if not all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in tokens):
                raise RuntimeError("/tokenize returned invalid token IDs")
            if len(tokens) < MIN_TOKEN_POOL:
                raise RuntimeError(
                    f"/tokenize token pool too short: {len(tokens)} < {MIN_TOKEN_POOL}"
                )
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=15)

    terminal = {
        "status": "LOGICAL_PREFIX_FIXTURE_V2_TOKENIZED",
        "server_binary": str(args.server_bin),
        "server_sha256": sha256(args.server_bin),
        "model": str(args.model),
        "model_sha256": sha256(args.model),
        "corpus": str(corpus),
        "corpus_sha256": sha256(corpus),
        "tokenizer_request": str(tokenizer_request),
        "tokenizer_request_sha256": sha256(tokenizer_request),
        "tokenizer_response": str(args.out_root / "tokenizer-response.json"),
        "tokenizer_response_sha256": sha256(args.out_root / "tokenizer-response.json"),
        "token_pool_len": len(json.loads(response_raw)["tokens"]),
        "health_requests": health_requests,
        "tokenization_requests": tokenization_requests,
        "generation_requests": 0,
        "measured_l0_submitted": False,
        "measured_attempt_consumed": False,
        "measured_execution_authorized_by_this_result": False,
        "server_exit_code": process.returncode if process is not None else None,
    }
    write_json(args.out_root / "terminal.json", terminal)
    print(json.dumps(terminal, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

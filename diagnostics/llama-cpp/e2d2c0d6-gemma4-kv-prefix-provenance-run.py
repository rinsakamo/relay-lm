#!/usr/bin/env python3
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time

EXPECTED_SERVER_SHA = "0a9160015c31d11b607b1bd7559e69fe90c02d1079ad7517ccb24ea75c71b08e"
EXPECTED_MODEL_SHA = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require_port_free(port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
    except OSError as exc:
        raise RuntimeError(f"port {port} is not free: {exc}") from exc
    finally:
        sock.close()


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
        conn.request(
            "POST",
            path,
            body=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        res = conn.getresponse()
        data = res.read()
        return res.status, dict(res.getheaders()), data
    finally:
        conn.close()


class Server:
    def __init__(self, *, binary: Path, model: Path, port: int, label: str, kv_root: Path, out: Path):
        self.binary = binary
        self.model = model
        self.port = port
        self.label = label
        self.kv_root = kv_root
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
        cmd = self.command()
        write_json(self.out / "argv.json", cmd)
        env = os.environ.copy()
        env["LLAMA_KV_PROBE_DIR"] = str(self.kv_root)
        env["LLAMA_KV_PROBE_LABEL"] = self.label
        write_json(self.out / "probe-env.json", {
            "LLAMA_KV_PROBE_DIR": str(self.kv_root),
            "LLAMA_KV_PROBE_LABEL": self.label,
        })
        self.stdout = (self.out / "server.stdout.txt").open("wb")
        self.stderr = (self.out / "server.stderr.txt").open("wb")
        self.proc = subprocess.Popen(cmd, stdout=self.stdout, stderr=self.stderr, env=env)
        (self.out / "server.pid.txt").write_text(f"{self.proc.pid}\n", encoding="utf-8")

        attempts = []
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            rc = self.proc.poll()
            if rc is not None:
                write_json(self.out / "startup.json", {
                    "ready": False,
                    "reason": "server_exited_before_health",
                    "exit_code": rc,
                    "attempts": attempts,
                })
                raise RuntimeError(f"{self.label}: server exited before health: {rc}")
            try:
                status, body = http_get(self.port, "/health")
                attempts.append({"status": status, "body": body.decode("utf-8", "replace")})
                if status == 200:
                    write_json(self.out / "startup.json", {
                        "ready": True,
                        "attempts": attempts,
                    })
                    return
            except Exception as exc:
                attempts.append({"error": repr(exc)})
            time.sleep(1)
        write_json(self.out / "startup.json", {
            "ready": False,
            "reason": "health_timeout",
            "attempts": attempts,
        })
        raise RuntimeError(f"{self.label}: health readiness timeout")

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


def send_request(server: Server, name: str, request_path: Path, expected_cache: int, expected_prompt: int):
    raw = request_path.read_bytes()
    req_out = server.out / f"{name}.request.json"
    # Preserve exact measured request bytes.
    req_out.write_bytes(raw)
    (server.out / f"{name}.request.sha256.txt").write_text(
        hashlib.sha256(raw).hexdigest() + "\n", encoding="utf-8"
    )

    status, headers, body = http_post_raw(server.port, "/completion", raw)
    (server.out / f"{name}.response.raw.json").write_bytes(body)
    write_json(server.out / f"{name}.http.json", {"status": status, "headers": headers})
    if status != 200:
        raise RuntimeError(f"{name}: HTTP {status}")

    obj = json.loads(body)
    write_json(server.out / f"{name}.response.pretty.json", obj)
    timings = obj.get("timings")
    if not isinstance(timings, dict):
        raise RuntimeError(f"{name}: missing timings")
    cache_n = timings.get("cache_n")
    prompt_n = timings.get("prompt_n")
    predicted_n = timings.get("predicted_n")
    if cache_n != expected_cache or prompt_n != expected_prompt:
        raise RuntimeError(
            f"{name}: path mismatch cache_n/prompt_n={cache_n}/{prompt_n}, "
            f"expected {expected_cache}/{expected_prompt}"
        )
    if predicted_n != 1:
        raise RuntimeError(f"{name}: predicted_n={predicted_n}, expected 1")

    return obj


def first_prob(response: dict):
    values = response.get("completion_probabilities")
    if not isinstance(values, list) or len(values) != 1:
        raise ValueError("completion_probabilities must contain exactly one generated token")
    tok = values[0]
    if not isinstance(tok, dict):
        raise ValueError("completion probability entry must be an object")
    tops = tok.get("top_logprobs")
    if not isinstance(tops, list) or len(tops) < 20:
        raise ValueError("top_logprobs must contain at least 20 entries")
    return tok


def api_compare(l1: dict, lc: dict):
    a = first_prob(l1)
    b = first_prob(lc)

    amap = {int(x["id"]): float(x["logprob"]) for x in a["top_logprobs"]}
    bmap = {int(x["id"]): float(x["logprob"]) for x in b["top_logprobs"]}
    common = sorted(set(amap) & set(bmap))
    deltas = {str(k): amap[k] - bmap[k] for k in common}
    max_item = None
    if deltas:
        token, delta = max(deltas.items(), key=lambda kv: abs(kv[1]))
        max_item = {"token_id": int(token), "delta_logprob_l1_minus_lc": delta, "abs_delta": abs(delta)}

    def margin(tok):
        tops = tok["top_logprobs"]
        return float(tops[0]["logprob"]) - float(tops[1]["logprob"]) if len(tops) >= 2 else None

    return {
        "first_token_equal": int(a["id"]) == int(b["id"]),
        "L1_first_token": {"id": a.get("id"), "token": a.get("token"), "logprob": a.get("logprob")},
        "LC_first_token": {"id": b.get("id"), "token": b.get("token"), "logprob": b.get("logprob")},
        "top_n_exact_equal": a["top_logprobs"] == b["top_logprobs"],
        "top_n_intersection": len(common),
        "L1_only_ids": sorted(set(amap) - set(bmap)),
        "LC_only_ids": sorted(set(bmap) - set(amap)),
        "L1_top1_top2_margin": margin(a),
        "LC_top1_top2_margin": margin(b),
        "intersection_deltas": deltas,
        "max_abs_delta": max_item,
        "top1_delta_logprob": float(a["logprob"]) - float(b["logprob"]),
    }


def _startup_evidence_match(text: str, pattern: str):
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return {
        "ok": match is not None,
        "matched_line": match.group(0).strip() if match is not None else None,
    }


def require_startup_evidence(server: Server):
    # Flush userspace buffers before reading retained startup logs.
    if server.stdout:
        server.stdout.flush()
    if server.stderr:
        server.stderr.flush()
    text = ""
    for path in (server.out / "server.stdout.txt", server.out / "server.stderr.txt"):
        try:
            text += path.read_text(encoding="utf-8", errors="replace") + "\n"
        except OSError:
            pass

    checks = {
        "flash_attn_enabled": _startup_evidence_match(
            text,
            r"^.*\bflash_attn\s*=\s*enabled\b.*$",
        ),
        "n_batch_512": _startup_evidence_match(
            text,
            r"^.*\bn_batch\s*=\s*512\b.*$",
        ),
        "n_ubatch_512": _startup_evidence_match(
            text,
            r"^.*\bn_ubatch\s*=\s*512\b.*$",
        ),
    }
    write_json(server.out / "startup-evidence.json", checks)
    missing = [name for name, result in checks.items() if not result["ok"]]
    if missing:
        raise RuntimeError(
            f"{server.label}: required startup evidence missing: {','.join(missing)}"
        )


def require_dump(kv_root: Path, name: str):
    p = kv_root / name
    if not p.is_dir():
        raise RuntimeError(f"required KV dump missing: {name}")
    bins = list(p.glob("*.bin"))
    if not bins:
        raise RuntimeError(f"required KV dump has no binary payload: {name}")


def localize_kv(comparison: dict):
    primary = comparison.get("classification")
    pair_for_class = {
        "PREFIX_DUMP_NOT_REPRODUCIBLE": "W_vs_W2",
        "PREFIX_KV_GENERATION_DIFFERS": "W_vs_C",
        "RETAINED_PREFIX_KV_MUTATED_BY_REUSE": "W_vs_R",
    }
    pair = pair_for_class.get(primary)
    if pair is None:
        return {
            "comparison_pair": None,
            "mismatch_file_count": 0,
            "first_mismatch": None,
            "layout_metadata_differs": False,
        }

    kv_pair = comparison.get("kv", {}).get(pair, {})
    different = list(kv_pair.get("different", []))

    def key(name: str):
        import re
        m = re.match(r"^(base|swa)\.layer-(\d+)\.(K|V)\.bin$", name)
        if not m:
            return (10**9, name, "")
        return (int(m.group(2)), m.group(1), m.group(3))

    ordered = sorted(different, key=key)
    first = None
    if ordered:
        import re
        m = re.match(r"^(base|swa)\.layer-(\d+)\.(K|V)\.bin$", ordered[0])
        if m:
            first = {
                "file": ordered[0],
                "cache_class": m.group(1),
                "layer": int(m.group(2)),
                "kind": m.group(3),
            }
        else:
            first = {"file": ordered[0]}

    layout = comparison.get("layout_metadata", {}).get(pair, {})
    return {
        "comparison_pair": pair,
        "mismatch_file_count": len(different),
        "first_mismatch": first,
        "layout_metadata_differs": not bool(layout.get("equal", False)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-bin", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--warm-tokens", type=Path, required=True)
    ap.add_argument("--target-tokens", type=Path, required=True)
    ap.add_argument("--l0-request", type=Path, required=True)
    ap.add_argument("--l1-request", type=Path, required=True)
    ap.add_argument("--lc-request", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--port-wr", type=int, required=True)
    ap.add_argument("--port-wr2", type=int, required=True)
    ap.add_argument("--port-c", type=int, required=True)
    args = ap.parse_args()

    if len({args.port_wr, args.port_wr2, args.port_c}) != 3:
        raise SystemExit("all three ports must be distinct")
    for port in (args.port_wr, args.port_wr2, args.port_c):
        require_port_free(port)
    if args.out_root.exists():
        raise SystemExit(f"output root must not exist: {args.out_root}")
    if sha256(args.server_bin) != EXPECTED_SERVER_SHA:
        raise SystemExit("instrumented server SHA256 mismatch")
    if sha256(args.model) != EXPECTED_MODEL_SHA:
        raise SystemExit("model SHA256 mismatch")

    args.out_root.mkdir(parents=True)
    kv_root = args.out_root / "kv"
    kv_root.mkdir()
    write_json(args.out_root / "physical-identity.json", {
        "server_sha256": sha256(args.server_bin),
        "model_sha256": sha256(args.model),
        "ports": {"WR": args.port_wr, "WR2": args.port_wr2, "C": args.port_c},
    })

    here = Path(__file__).resolve().parent
    admission = here / "e2d2c0d6-gemma4-kv-request-admission.py"
    comparator = here / "e2d2c0d6-gemma4-kv-prefix-digest-compare.py"

    admission_cmd = [
        sys.executable, str(admission),
        "--warm-tokens", str(args.warm_tokens),
        "--target-tokens", str(args.target_tokens),
        "--l0", str(args.l0_request),
        "--l1", str(args.l1_request),
        "--lc", str(args.lc_request),
        "--out", str(args.out_root / "request-admission.json"),
    ]
    write_json(args.out_root / "request-admission.argv.json", admission_cmd)
    admission_run = subprocess.run(admission_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (args.out_root / "request-admission.stdout.txt").write_bytes(admission_run.stdout)
    (args.out_root / "request-admission.stderr.txt").write_bytes(admission_run.stderr)
    if admission_run.returncode != 0:
        write_json(args.out_root / "terminal.json", {
            "primary_classification": "PROBE_NOT_EXERCISED",
            "measured_l0_submitted": False,
            "reason": "request admission failed",
        })
        raise SystemExit(2)

    measured_l0 = False
    submitted_requests = []
    servers = []
    try:
        wr = Server(
            binary=args.server_bin, model=args.model, port=args.port_wr,
            label="WR", kv_root=kv_root, out=args.out_root / "server-WR",
        )
        servers.append(wr)
        wr.start()
        require_startup_evidence(wr)

        measured_l0 = True
        submitted_requests.append("L0")
        l0 = send_request(wr, "L0", args.l0_request, 0, 883)
        require_dump(kv_root, "WR-P512")

        submitted_requests.append("L1")
        l1 = send_request(wr, "L1", args.l1_request, 512, 2415)
        require_dump(kv_root, "WR-R512")
        wr.stop()

        wr2 = Server(
            binary=args.server_bin, model=args.model, port=args.port_wr2,
            label="WR2", kv_root=kv_root, out=args.out_root / "server-WR2",
        )
        servers.append(wr2)
        wr2.start()
        require_startup_evidence(wr2)
        submitted_requests.append("L0R")
        l0r = send_request(wr2, "L0R", args.l0_request, 0, 883)
        require_dump(kv_root, "WR2-P512")
        wr2.stop()

        cold = Server(
            binary=args.server_bin, model=args.model, port=args.port_c,
            label="C", kv_root=kv_root, out=args.out_root / "server-C",
        )
        servers.append(cold)
        cold.start()
        require_startup_evidence(cold)
        submitted_requests.append("LC")
        lc = send_request(cold, "LC", args.lc_request, 0, 2927)
        require_dump(kv_root, "C-P512")
        cold.stop()

        api = api_compare(l1, lc)
        write_json(args.out_root / "api-L1-vs-LC.json", api)

        cmp_path = args.out_root / "kv-prefix-comparison.json"
        cmp_run = subprocess.run(
            [sys.executable, str(comparator), str(kv_root)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        cmp_path.write_bytes(cmp_run.stdout)
        (args.out_root / "kv-prefix-comparison.stderr.txt").write_bytes(cmp_run.stderr)
        if cmp_run.returncode != 0:
            raise RuntimeError(f"KV comparator failed: rc={cmp_run.returncode}")
        cmp_obj = json.loads(cmp_run.stdout)

        primary = cmp_obj.get("classification")
        kv_localization = localize_kv(cmp_obj)
        write_json(args.out_root / "kv-localization.json", kv_localization)
        allowed = {
            "PREFIX_DUMP_NOT_REPRODUCIBLE",
            "PREFIX_KV_GENERATION_DIFFERS",
            "RETAINED_PREFIX_KV_MUTATED_BY_REUSE",
            "PREFIX_KV_IDENTICAL_THROUGH_REUSE",
        }
        if primary not in allowed:
            raise RuntimeError(f"unexpected comparator classification: {primary}")

        terminal = {
            "primary_classification": primary,
            "measured_l0_submitted": True,
            "request_count": 4,
            "requests": ["L0", "L1", "L0R", "LC"],
            "api_L1_vs_LC": api,
            "kv_comparison_file": str(cmp_path),
            "kv_localization": kv_localization,
            "scientific_campaign_interaction": 0,
            "flash_attention_off_arms": 0,
        }
        write_json(args.out_root / "terminal.json", terminal)
        print(json.dumps(terminal, indent=2, sort_keys=True))
    except Exception as exc:
        for server in reversed(servers):
            try:
                server.stop()
            except Exception:
                pass
        terminal = {
            "primary_classification": (
                "PROBE_EXERCISED_INCOMPLETE" if measured_l0 else "PROBE_NOT_EXERCISED"
            ),
            "measured_l0_submitted": measured_l0,
            "submitted_requests": submitted_requests,
            "request_count_submitted": len(submitted_requests),
            "reason": str(exc),
            "retry_replay_repair": 0,
            "rerun_authorized": False if measured_l0 else None,
        }
        write_json(args.out_root / "terminal.json", terminal)
        print(json.dumps(terminal, indent=2, sort_keys=True))
        raise SystemExit(3)


if __name__ == "__main__":
    main()

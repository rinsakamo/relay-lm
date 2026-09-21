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

REPLACEMENT_ATTEMPT_ID = "logical-prefix-kv-replacement-20260921-30d3f94f"
EXPECTED_SERVER_SHA = "30d3f94f7335821a74828c243ab1dd315df9dc7a4c6df0cdff2f3ce1629dbaff"
EXPECTED_SERVER_IMPL_SHA = "e6003c1e1a1c1c16dc5a09da485517eec6b6010d17f198acd34981075c14a64c"
EXPECTED_LLAMA_SHA = "53228c024c04bd4a1acefa03d9ddc602cdfc78b5214d7fb7da13de458d2a2965"
EXPECTED_MODEL_SHA = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"

STARTUP_EVIDENCE_PATTERNS = {
    "n_seq_max_1": r"^.*\bllama_context\s*:\s*n_seq_max\s*=\s*1\b.*$",
    "n_ctx_8192": r"^.*\bllama_context\s*:\s*n_ctx\s*=\s*8192\b.*$",
    "n_batch_512": r"^.*\bllama_context\s*:\s*n_batch\s*=\s*512\b.*$",
    "n_ubatch_512": r"^.*\bllama_context\s*:\s*n_ubatch\s*=\s*512\b.*$",
    "flash_attn_enabled": r"^.*\bllama_context\s*:\s*flash_attn\s*=\s*enabled\b.*$",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require_runtime_closure(server_bin: Path):
    server_impl = server_bin.parent / "libllama-server-impl.so"
    llama_lib = server_bin.parent / "libllama.so"

    required = {
        "llama_server": (server_bin, EXPECTED_SERVER_SHA),
        "llama_server_impl": (server_impl, EXPECTED_SERVER_IMPL_SHA),
        "llama": (llama_lib, EXPECTED_LLAMA_SHA),
    }
    evidence = {}
    for name, (path, expected) in required.items():
        if not path.is_file():
            raise RuntimeError(f"required runtime artifact missing: {name}: {path}")
        observed = sha256(path)
        resolved = path.resolve(strict=True)
        evidence[name] = {
            "path": str(path),
            "resolved_path": str(resolved),
            "sha256": observed,
            "expected_sha256": expected,
        }
        if observed != expected:
            raise RuntimeError(
                f"runtime artifact SHA256 mismatch: {name}: {observed} != {expected}"
            )
    return evidence


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


def _startup_evidence_from_text(text: str):
    lines = text.splitlines()
    starts = [
        i for i, line in enumerate(lines)
        if re.search(
            r"\bllama_context\s*:\s*constructing\s+llama_context\b",
            line,
            flags=re.IGNORECASE,
        )
    ]

    if starts:
        start = starts[-1]
        block_lines = lines[start:]
        selected_context_index = len(starts) - 1
    else:
        block_lines = []
        selected_context_index = None

    block = "\n".join(block_lines)
    checks = {
        name: _startup_evidence_match(block, pattern)
        for name, pattern in STARTUP_EVIDENCE_PATTERNS.items()
    }
    return {
        "context_block_count": len(starts),
        "selected_context_index": selected_context_index,
        "selected_context_start_line": (
            lines[starts[-1]].strip() if starts else None
        ),
        "checks": checks,
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

    evidence = _startup_evidence_from_text(text)
    write_json(server.out / "startup-evidence.json", evidence)
    missing = [
        name
        for name, result in evidence["checks"].items()
        if not result["ok"]
    ]
    if evidence["context_block_count"] == 0:
        missing.insert(0, "llama_context_block")
    if missing:
        raise RuntimeError(
            f"{server.label}: required startup evidence missing: {','.join(missing)}"
        )


def require_dump(kv_root: Path, name: str):
    p = kv_root / name
    if not p.is_dir():
        raise RuntimeError(f"required KV dump missing: {name}")

    expected_bins = set()
    geometry = {}
    for cache_name in ("base", "swa"):
        cells_path = p / f"{cache_name}.cells.tsv"
        manifest_path = p / f"{cache_name}.manifest.tsv"
        if not cells_path.is_file() or not manifest_path.is_file():
            raise RuntimeError(f"{name}: missing {cache_name} cells/manifest metadata")

        cells_lines = cells_path.read_text(encoding="utf-8").splitlines()
        if len(cells_lines) != 513:
            raise RuntimeError(
                f"{name}: {cache_name}.cells.tsv data rows={max(0, len(cells_lines)-1)}, expected 512"
            )
        if cells_lines[0] != "cache\tstream\thead\tkv_size\tv_trans\tposition\tcell":
            raise RuntimeError(f"{name}: unexpected {cache_name}.cells.tsv header")

        positions = []
        kv_sizes = set()
        streams = set()
        v_trans_values = set()
        for line in cells_lines[1:]:
            fields = line.split("\t")
            if len(fields) != 7 or fields[0] != cache_name:
                raise RuntimeError(f"{name}: invalid {cache_name}.cells.tsv row")
            streams.add(int(fields[1]))
            kv_sizes.add(int(fields[3]))
            v_trans_values.add(int(fields[4]))
            positions.append(int(fields[5]))

        if len(streams) != 1:
            raise RuntimeError(f"{name}: {cache_name} spans multiple streams: {sorted(streams)}")
        if len(kv_sizes) != 1:
            raise RuntimeError(f"{name}: {cache_name} has inconsistent kv_size values: {sorted(kv_sizes)}")
        if v_trans_values != {0}:
            raise RuntimeError(f"{name}: {cache_name} V cache unexpectedly transposed")
        if positions != list(range(512)):
            raise RuntimeError(f"{name}: {cache_name} logical positions are not exactly 0..511")

        geometry[cache_name] = {
            "stream": next(iter(streams)),
            "kv_size": next(iter(kv_sizes)),
            "v_trans": 0,
            "logical_rows": 512,
        }

        manifest_lines = manifest_path.read_text(encoding="utf-8").splitlines()
        if not manifest_lines or manifest_lines[0] != "cache\tlayer\tkind\ttype\trow_bytes\trows":
            raise RuntimeError(f"{name}: unexpected {cache_name}.manifest.tsv header")
        if len(manifest_lines) <= 1:
            raise RuntimeError(f"{name}: empty {cache_name}.manifest.tsv")

        seen_layer_kind = set()
        for line in manifest_lines[1:]:
            fields = line.split("\t")
            if len(fields) != 6:
                raise RuntimeError(f"{name}: malformed {cache_name} manifest row")
            cache, layer_s, kind, _type, row_bytes_s, rows_s = fields
            if cache != cache_name or kind not in {"K", "V"}:
                raise RuntimeError(f"{name}: invalid {cache_name} manifest identity")
            layer = int(layer_s)
            row_bytes = int(row_bytes_s)
            rows = int(rows_s)
            if row_bytes <= 0 or rows != 512:
                raise RuntimeError(
                    f"{name}: invalid {cache_name} layer {layer} {kind} geometry "
                    f"row_bytes={row_bytes} rows={rows}"
                )
            key = (layer, kind)
            if key in seen_layer_kind:
                raise RuntimeError(f"{name}: duplicate {cache_name} layer/kind {key}")
            seen_layer_kind.add(key)

            bin_name = f"{cache_name}.layer-{layer}.{kind}.bin"
            bin_path = p / bin_name
            if not bin_path.is_file():
                raise RuntimeError(f"{name}: missing payload {bin_name}")
            expected_size = row_bytes * rows
            actual_size = bin_path.stat().st_size
            if actual_size != expected_size:
                raise RuntimeError(
                    f"{name}: payload size mismatch {bin_name}: "
                    f"{actual_size} != {expected_size}"
                )
            expected_bins.add(bin_name)

        layer_kinds = {}
        for layer, kind in seen_layer_kind:
            layer_kinds.setdefault(layer, set()).add(kind)
        incomplete_layers = sorted(layer for layer, kinds in layer_kinds.items() if kinds != {"K", "V"})
        if incomplete_layers:
            raise RuntimeError(
                f"{name}: {cache_name} layers missing K/V pair: {incomplete_layers}"
            )

        geometry[cache_name]["layer_count"] = len(layer_kinds)

    base_size = geometry["base"]["kv_size"]
    swa_size = geometry["swa"]["kv_size"]
    if base_size != 8192:
        raise RuntimeError(f"{name}: base kv_size={base_size}, expected 8192")
    if not (0 < swa_size < base_size):
        raise RuntimeError(
            f"{name}: compact SWA not proven: swa kv_size={swa_size}, base kv_size={base_size}"
        )

    actual_bins = {x.name for x in p.glob("*.bin") if x.is_file()}
    if actual_bins != expected_bins:
        raise RuntimeError(
            f"{name}: payload file set differs from manifests: "
            f"missing={sorted(expected_bins - actual_bins)} "
            f"unexpected={sorted(actual_bins - expected_bins)}"
        )

    return geometry

def require_consistent_dump_geometry(dump_geometry: dict):
    required = ("WR-P512", "WR-R512", "WR2-P512", "C-P512")
    missing = [name for name in required if name not in dump_geometry]
    if missing:
        raise RuntimeError(f"missing dump geometry records: {missing}")

    signature_fields = ("kv_size", "v_trans", "logical_rows", "layer_count")
    baseline_name = required[0]
    baseline = {
        cache_name: {
            field: dump_geometry[baseline_name][cache_name][field]
            for field in signature_fields
        }
        for cache_name in ("base", "swa")
    }

    for name in required[1:]:
        current = {
            cache_name: {
                field: dump_geometry[name][cache_name][field]
                for field in signature_fields
            }
            for cache_name in ("base", "swa")
        }
        if current != baseline:
            raise RuntimeError(
                f"KV dump geometry differs across observation points: "
                f"{baseline_name}={baseline} {name}={current}"
            )

    return {
        "baseline": baseline_name,
        "signature": baseline,
        "observations": list(required),
    }


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
    different = set(kv_pair.get("different", []))
    missing_left = set(kv_pair.get("missing_left", []))
    missing_right = set(kv_pair.get("missing_right", []))
    mismatched = different | missing_left | missing_right

    def key(name: str):
        m = re.match(r"^(base|swa)\.layer-(\d+)\.(K|V)\.bin$", name)
        if not m:
            return (10**9, name, "")
        return (int(m.group(2)), m.group(1), m.group(3))

    ordered = sorted(mismatched, key=key)
    first = None
    if ordered:
        filename = ordered[0]
        m = re.match(r"^(base|swa)\.layer-(\d+)\.(K|V)\.bin$", filename)
        difference_types = []
        if filename in different:
            difference_types.append("hash_diff")
        if filename in missing_left:
            difference_types.append("missing_left")
        if filename in missing_right:
            difference_types.append("missing_right")
        if m:
            first = {
                "file": filename,
                "cache_class": m.group(1),
                "layer": int(m.group(2)),
                "kind": m.group(3),
                "difference_types": difference_types,
            }
        else:
            first = {"file": filename, "difference_types": difference_types}

    layout = comparison.get("layout_metadata", {}).get(pair, {})
    return {
        "comparison_pair": pair,
        "mismatch_file_count": len(mismatched),
        "hash_diff_count": len(different),
        "missing_left_count": len(missing_left),
        "missing_right_count": len(missing_right),
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
    try:
        runtime_closure = require_runtime_closure(args.server_bin)
    except Exception as exc:
        raise SystemExit(str(exc))
    if sha256(args.model) != EXPECTED_MODEL_SHA:
        raise SystemExit("model SHA256 mismatch")

    args.out_root.mkdir(parents=True)
    kv_root = args.out_root / "kv"
    kv_root.mkdir()
    write_json(args.out_root / "physical-identity.json", {
        "attempt_id": REPLACEMENT_ATTEMPT_ID,
        "server_sha256": sha256(args.server_bin),
        "runtime_artifacts": runtime_closure,
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
    dump_geometry = {}
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
        dump_geometry["WR-P512"] = require_dump(kv_root, "WR-P512")

        submitted_requests.append("L1")
        l1 = send_request(wr, "L1", args.l1_request, 512, 2415)
        dump_geometry["WR-R512"] = require_dump(kv_root, "WR-R512")
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
        dump_geometry["WR2-P512"] = require_dump(kv_root, "WR2-P512")
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
        dump_geometry["C-P512"] = require_dump(kv_root, "C-P512")
        geometry_consistency = require_consistent_dump_geometry(dump_geometry)
        write_json(args.out_root / "kv-dump-geometry.json", {
            "observations": dump_geometry,
            "consistency": geometry_consistency,
        })
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
            "attempt_id": REPLACEMENT_ATTEMPT_ID,
            "primary_classification": primary,
            "measured_l0_submitted": True,
            "request_count": 4,
            "requests": ["L0", "L1", "L0R", "LC"],
            "api_L1_vs_LC": api,
            "kv_comparison_file": str(cmp_path),
            "kv_localization": kv_localization,
            "kv_dump_geometry": dump_geometry,
            "kv_dump_geometry_consistency": geometry_consistency,
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
            "attempt_id": REPLACEMENT_ATTEMPT_ID,
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

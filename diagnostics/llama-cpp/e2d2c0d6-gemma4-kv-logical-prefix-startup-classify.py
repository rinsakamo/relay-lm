#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

EXPECTED_MODEL_SHA = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
EXPECTED_CANONICAL_STATIC_ARGV = [
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

STARTUP_PATTERNS = {
    "n_seq_max_1": r"^.*\bllama_context\s*:\s*n_seq_max\s*=\s*1\b.*$",
    "n_ctx_8192": r"^.*\bllama_context\s*:\s*n_ctx\s*=\s*8192\b.*$",
    "n_batch_512": r"^.*\bllama_context\s*:\s*n_batch\s*=\s*512\b.*$",
    "n_ubatch_512": r"^.*\bllama_context\s*:\s*n_ubatch\s*=\s*512\b.*$",
    "flash_attn_enabled": r"^.*\bllama_context\s*:\s*flash_attn\s*=\s*enabled\b.*$",
}

BASE_KV_RE = re.compile(
    r"\bllama_kv_cache_iswa\s*:\s*creating\s+non-SWA\s+KV\s+cache,\s*size\s*=\s*(\d+)\s+cells\b",
    flags=re.IGNORECASE,
)
SWA_KV_RE = re.compile(
    r"\bllama_kv_cache_iswa\s*:\s*creating\s+SWA\s+KV\s+cache,\s*size\s*=\s*(\d+)\s+cells\b",
    flags=re.IGNORECASE,
)


def read_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8", errors="replace")


def read_stripped(path: Path) -> str:
    return read_text(path).strip()


def read_sha_line(path: Path) -> str:
    line = read_stripped(path)
    if not line:
        raise ValueError(f"empty sha file: {path}")
    return line.split()[0]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def combined_log(root: Path) -> str:
    parts = []
    for name in ("server.stdout.txt", "server.stderr.txt"):
        p = root / name
        if p.is_file():
            parts.append(read_text(p))
    return "\n".join(parts)


def final_context_evidence(text: str):
    lines = text.splitlines()
    starts = [
        i for i, line in enumerate(lines)
        if re.search(
            r"\bllama_context\s*:\s*constructing\s+llama_context\b",
            line,
            flags=re.IGNORECASE,
        )
    ]
    if not starts:
        return {
            "context_block_count": 0,
            "selected_context_index": None,
            "checks": {name: {"ok": False, "matched_line": None} for name in STARTUP_PATTERNS},
        }

    start = starts[-1]
    block = "\n".join(lines[start:])
    checks = {}
    for name, pattern in STARTUP_PATTERNS.items():
        m = re.search(pattern, block, flags=re.IGNORECASE | re.MULTILINE)
        checks[name] = {
            "ok": m is not None,
            "matched_line": m.group(0).strip() if m else None,
        }
    return {
        "context_block_count": len(starts),
        "selected_context_index": len(starts) - 1,
        "selected_context_start_line": lines[start].strip(),
        "checks": checks,
    }


def compact_swa_evidence(text: str):
    bases = [int(x) for x in BASE_KV_RE.findall(text)]
    swas = [int(x) for x in SWA_KV_RE.findall(text)]
    if not bases or not swas:
        return {
            "ok": False,
            "base_sizes": bases,
            "swa_sizes": swas,
            "selected_base_size": bases[-1] if bases else None,
            "selected_swa_size": swas[-1] if swas else None,
            "reason": "missing base/SWA allocation log",
        }

    base = bases[-1]
    swa = swas[-1]
    ok = base == 8192 and swa == 1536
    return {
        "ok": ok,
        "base_sizes": bases,
        "swa_sizes": swas,
        "selected_base_size": base,
        "selected_swa_size": swa,
        "reason": None if ok else "expected exact base=8192 and SWA=1536",
    }


def canonical_argv_contract(root: Path):
    path = root / "server.argv.canonical.txt"
    lines = read_text(path).splitlines()
    if len(lines) != 2 + len(EXPECTED_CANONICAL_STATIC_ARGV):
        return {
            "ok": False,
            "lines": lines,
            "reason": f"unexpected canonical argv line count: {len(lines)}",
        }
    if not lines[0].startswith("server_bin=") or not lines[1].startswith("model_path="):
        return {
            "ok": False,
            "lines": lines,
            "reason": "canonical argv missing server/model identity lines",
        }
    server_value = lines[0].split("=", 1)[1]
    model_value = lines[1].split("=", 1)[1]
    expected_server = read_stripped(root / "server-binary.resolved.txt")
    expected_model = read_stripped(root / "model.resolved.txt")
    static = lines[2:]
    checks = {
        "server_path_exact": server_value == expected_server,
        "model_path_exact": model_value == expected_model,
        "static_exact": static == EXPECTED_CANONICAL_STATIC_ARGV,
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "lines": lines,
        "static": static,
        "expected_static": EXPECTED_CANONICAL_STATIC_ARGV,
        "reason": None if all(checks.values()) else "canonical argv identity/static mismatch",
    }

def parse_env_file(path: Path):
    lines = [x for x in read_text(path).splitlines() if x]
    env = {}
    for line in lines:
        if "=" not in line:
            raise RuntimeError(f"malformed environment line in {path}: {line!r}")
        key, value = line.split("=", 1)
        if key in env:
            raise RuntimeError(f"duplicate environment key in {path}: {key}")
        env[key] = value
    return env


def environment_contract(name: str, root: Path):
    intended = parse_env_file(root / "runtime-environment.effective.txt")
    actual = parse_env_file(root / "proc-environ.health-ready.txt")
    base_keys = {
        "HOME", "TMPDIR", "PATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH",
        "CUDA_VISIBLE_DEVICES", "GGML_CUDA_GRAPH_OPT",
    }
    expected_keys = set(base_keys)
    if name == "probe":
        expected_keys |= {
            "LLAMA_KV_PROBE_DIR", "LLAMA_KV_PROBE_LABEL",
            "LLAMA_PROJECTION_ORIGIN_PROBE_DIR", "LLAMA_PROJECTION_ORIGIN_PROBE_LABEL",
        }
    expected_lib_dir = str(Path(read_stripped(root / "server-impl.resolved.txt")).parent)
    checks = {
        "key_set_exact": set(intended) == expected_keys and set(actual) == expected_keys,
        "actual_matches_intended": actual == intended,
        "home_exact": intended.get("HOME") == str(root / "hermetic-home"),
        "home_exists": (root / "hermetic-home").is_dir(),
        "tmpdir_exact": intended.get("TMPDIR") == str(root / "hermetic-tmp"),
        "tmpdir_exists": (root / "hermetic-tmp").is_dir(),
        "path_exact": intended.get("PATH") == "/usr/local/cuda-12.8/bin:/usr/bin:/bin",
        "lang_exact": intended.get("LANG") == "C.UTF-8",
        "lc_all_exact": intended.get("LC_ALL") == "C.UTF-8",
        "ld_library_path_exact": intended.get("LD_LIBRARY_PATH") == f"{expected_lib_dir}:/usr/local/cuda-12.8/lib64",
        "cuda_visible_devices_exact": intended.get("CUDA_VISIBLE_DEVICES") == "0",
        "cuda_graph_opt_disabled": intended.get("GGML_CUDA_GRAPH_OPT") == "0",
        "cuda_disable_fusion_absent": "GGML_CUDA_DISABLE_FUSION" not in intended and "GGML_CUDA_DISABLE_FUSION" not in actual,
        "probe_label_exact": (
            name != "probe" or intended.get("LLAMA_KV_PROBE_LABEL") == "PRE"
        ),
        "projection_probe_label_exact": (
            name != "probe" or intended.get("LLAMA_PROJECTION_ORIGIN_PROBE_LABEL") == "W"
        ),
        "projection_probe_dir_exact": (
            name != "probe" or intended.get("LLAMA_PROJECTION_ORIGIN_PROBE_DIR") == str(root / "projection-probe-root")
        ),
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "intended": intended,
        "actual": actual,
    }


def runtime_library_contract(root: Path):
    specs = {
        "server_impl": ("server-impl.resolved.txt", "libllama-server-impl.so"),
        "llama": ("llama-lib.resolved.txt", "libllama.so"),
        "ggml": ("ggml-lib.resolved.txt", "libggml.so"),
        "ggml_base": ("ggml-base.resolved.txt", "libggml-base.so"),
        "ggml_cpu": ("ggml-cpu.resolved.txt", "libggml-cpu.so"),
        "ggml_cuda": ("ggml-cuda.resolved.txt", "libggml-cuda.so"),
    }
    maps = read_text(root / "proc-maps.health-ready.txt").splitlines()
    checks = {}
    evidence = {}
    for key, (resolved_name, soname) in specs.items():
        expected = read_stripped(root / resolved_name)
        lines = [line for line in maps if soname in line]
        paths = sorted({line.split()[-1] for line in lines if line.split()})
        checks[f"{key}_loaded_exact"] = paths == [expected]
        evidence[key] = {"expected": expected, "loaded_paths": paths}
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "libraries": evidence,
    }


def inspect_arm(name: str, root: Path):
    log = combined_log(root)
    context = final_context_evidence(log)
    swa = compact_swa_evidence(log)
    probe_root = root / "probe-root"
    unexpected_probe_output = (
        probe_root.exists() and any(probe_root.iterdir())
    )
    projection_probe_root = root / "projection-probe-root"
    unexpected_projection_probe_output = (
        projection_probe_root.exists() and any(projection_probe_root.iterdir())
    )
    return {
        "name": name,
        "classification": read_stripped(root / "classification.txt"),
        "server_sha256": read_sha_line(root / "server-binary.sha256"),
        "server_impl_sha256": read_sha_line(root / "server-impl.sha256"),
        "llama_lib_sha256": read_sha_line(root / "llama-lib.sha256"),
        "ggml_lib_sha256": read_sha_line(root / "ggml-lib.sha256"),
        "ggml_base_sha256": read_sha_line(root / "ggml-base.sha256"),
        "ggml_cpu_sha256": read_sha_line(root / "ggml-cpu.sha256"),
        "ggml_cuda_sha256": read_sha_line(root / "ggml-cuda.sha256"),
        "model_sha256": read_sha_line(root / "model.sha256"),
        "argv_canonical_sha256": sha256(root / "server.argv.canonical.txt"),
        "argv_contract": canonical_argv_contract(root),
        "environment_contract": environment_contract(name, root),
        "runtime_library_contract": runtime_library_contract(root),
        "context": context,
        "compact_swa": swa,
        "unexpected_probe_output": unexpected_probe_output,
        "unexpected_projection_probe_output": unexpected_projection_probe_output,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plain", type=Path)
    ap.add_argument("probe", type=Path)
    args = ap.parse_args()

    errors = []
    evidence = {}

    try:
        evidence["plain"] = inspect_arm("plain", args.plain)
    except Exception as exc:
        errors.append(f"plain: {exc}")
    try:
        evidence["probe"] = inspect_arm("probe", args.probe)
    except Exception as exc:
        errors.append(f"probe: {exc}")

    if not errors:
        plain = evidence["plain"]
        probe = evidence["probe"]

        for arm in (plain, probe):
            if arm["classification"] != "READY_NON_GENERATIVE":
                errors.append(f"{arm['name']}: classification={arm['classification']}")
            if not arm["argv_contract"]["ok"]:
                errors.append(f"{arm['name']}: canonical argv contract mismatch: {arm['argv_contract']['reason']}")
            if not arm["environment_contract"]["ok"]:
                errors.append(f"{arm['name']}: runtime environment contract mismatch")
            if not arm["runtime_library_contract"]["ok"]:
                errors.append(f"{arm['name']}: loaded runtime library closure mismatch")
            missing = [
                key for key, value in arm["context"]["checks"].items()
                if not value["ok"]
            ]
            if arm["context"]["context_block_count"] == 0:
                missing.insert(0, "llama_context_block")
            if missing:
                errors.append(f"{arm['name']}: startup runtime evidence missing: {missing}")
            if not arm["compact_swa"]["ok"]:
                errors.append(f"{arm['name']}: compact SWA not proven")
            if arm["unexpected_probe_output"]:
                errors.append(f"{arm['name']}: unexpected KV probe output during non-generative startup")
            if arm["unexpected_projection_probe_output"]:
                errors.append(f"{arm['name']}: unexpected projection probe output during non-generative startup")

        if plain["server_sha256"] != probe["server_sha256"]:
            errors.append("server SHA differs between plain/probe")
        if plain["model_sha256"] != probe["model_sha256"]:
            errors.append("model SHA differs between plain/probe")
        if plain["server_impl_sha256"] != probe["server_impl_sha256"]:
            errors.append("server implementation library SHA differs between plain/probe")
        if plain["llama_lib_sha256"] != probe["llama_lib_sha256"]:
            errors.append("llama library SHA differs between plain/probe")
        for key, label in (
            ("ggml_lib_sha256", "ggml"),
            ("ggml_base_sha256", "ggml-base"),
            ("ggml_cpu_sha256", "ggml-cpu"),
            ("ggml_cuda_sha256", "ggml-cuda"),
        ):
            if plain[key] != probe[key]:
                errors.append(f"{label} library SHA differs between plain/probe")
        if plain["argv_canonical_sha256"] != probe["argv_canonical_sha256"]:
            errors.append("canonical argv differs between plain/probe")
        if plain["model_sha256"] != EXPECTED_MODEL_SHA:
            errors.append("model SHA does not match frozen authority")

        pgeom = (
            plain["compact_swa"]["selected_base_size"],
            plain["compact_swa"]["selected_swa_size"],
        )
        qgeom = (
            probe["compact_swa"]["selected_base_size"],
            probe["compact_swa"]["selected_swa_size"],
        )
        if pgeom != qgeom:
            errors.append(f"plain/probe KV allocation geometry differs: {pgeom} != {qgeom}")

    primary = (
        "LOGICAL_PREFIX_STARTUP_QUALIFIED"
        if not errors
        else "LOGICAL_PREFIX_STARTUP_NOT_QUALIFIED"
    )

    out = {
        "primary_classification": primary,
        "errors": errors,
        "evidence": evidence,
        "generated_requests": 0,
        "measured_attempt_consumed": False,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

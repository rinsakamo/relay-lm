#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

EXPECTED_MODEL_SHA = "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"

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
    ok = base == 8192 and 0 < swa < base
    return {
        "ok": ok,
        "base_sizes": bases,
        "swa_sizes": swas,
        "selected_base_size": base,
        "selected_swa_size": swa,
        "reason": None if ok else "expected base=8192 and 0<swa<base",
    }


def inspect_arm(name: str, root: Path):
    log = combined_log(root)
    context = final_context_evidence(log)
    swa = compact_swa_evidence(log)
    probe_root = root / "probe-root"
    unexpected_probe_output = (
        probe_root.exists() and any(probe_root.iterdir())
    )
    return {
        "name": name,
        "classification": read_stripped(root / "classification.txt"),
        "server_sha256": read_sha_line(root / "server-binary.sha256"),
        "model_sha256": read_sha_line(root / "model.sha256"),
        "argv_canonical_sha256": sha256(root / "server.argv.canonical.txt"),
        "context": context,
        "compact_swa": swa,
        "unexpected_probe_output": unexpected_probe_output,
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
                errors.append(f"{arm['name']}: unexpected probe output during non-generative startup")

        if plain["server_sha256"] != probe["server_sha256"]:
            errors.append("server SHA differs between plain/probe")
        if plain["model_sha256"] != probe["model_sha256"]:
            errors.append("model SHA differs between plain/probe")
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

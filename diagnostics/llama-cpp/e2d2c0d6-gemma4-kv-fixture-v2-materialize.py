#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

WARM_LEN = 883
TARGET_LEN = 2927
LCP_LEN = 865
TARGET_SUFFIX_LEN = TARGET_LEN - LCP_LEN
MIN_POOL_LEN = WARM_LEN + TARGET_SUFFIX_LEN
FORMAT_VERSION = 1


def canonical_json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_token_pool(path: Path):
    raw = path.read_bytes()
    obj = json.loads(raw)
    if isinstance(obj, dict):
        tokens = obj.get("tokens")
    else:
        tokens = obj
    if not isinstance(tokens, list):
        raise ValueError("tokenizer response must be a list or object with a tokens list")
    if not all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in tokens):
        raise ValueError("tokenizer tokens must be non-negative integers")
    if len(tokens) < MIN_POOL_LEN:
        raise ValueError(f"token pool too short: {len(tokens)} < {MIN_POOL_LEN}")
    return raw, tokens


def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def choose_target_offset(pool):
    warm_next = pool[LCP_LEN]
    last = len(pool) - TARGET_SUFFIX_LEN
    for offset in range(WARM_LEN, last + 1):
        if pool[offset] != warm_next:
            return offset
    raise ValueError("could not find deterministic target suffix with exact LCP boundary")


def write_new(path: Path, raw: bytes):
    if path.exists():
        raise FileExistsError(f"refusing to overwrite: {path}")
    path.write_bytes(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer-response", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    if args.out_dir.exists():
        raise SystemExit(f"output directory must not exist: {args.out_dir}")
    args.out_dir.mkdir(parents=True)

    response_raw, pool = load_token_pool(args.tokenizer_response)
    target_offset = choose_target_offset(pool)

    warm = pool[:WARM_LEN]
    target = pool[:LCP_LEN] + pool[target_offset:target_offset + TARGET_SUFFIX_LEN]

    if len(warm) != WARM_LEN or len(target) != TARGET_LEN:
        raise RuntimeError("fixture length construction failed")
    if lcp(warm, target) != LCP_LEN:
        raise RuntimeError("fixture LCP construction failed")

    base_generation = {
        "n_predict": 1,
        "temperature": 0,
        "stream": False,
        "n_probs": 20,
    }
    l0 = {"prompt": warm, "cache_prompt": True, **base_generation}
    l1 = {"prompt": target, "cache_prompt": True, **base_generation}
    lc = {"prompt": target, "cache_prompt": False, **base_generation}

    files = {
        "warm.tokens.json": canonical_json_bytes(warm),
        "target.tokens.json": canonical_json_bytes(target),
        "L0.request.json": canonical_json_bytes(l0),
        "L1.request.json": canonical_json_bytes(l1),
        "LC.request.json": canonical_json_bytes(lc),
    }

    for name, raw in files.items():
        write_new(args.out_dir / name, raw)

    manifest = {
        "format_version": FORMAT_VERSION,
        "subject": "logical-prefix-kv-fixture-v2",
        "tokenizer_response": {
            "path": str(args.tokenizer_response),
            "sha256": sha256_bytes(response_raw),
            "token_pool_len": len(pool),
        },
        "geometry": {
            "warm_len": len(warm),
            "target_len": len(target),
            "lcp": lcp(warm, target),
            "target_suffix_source_offset": target_offset,
            "target_suffix_len": TARGET_SUFFIX_LEN,
        },
        "files": {
            name: {
                "sha256": sha256_bytes(raw),
                "bytes": len(raw),
            }
            for name, raw in files.items()
        },
        "request_rule": {
            "L0R": "send the exact raw bytes of L0.request.json on a fresh WR2 server",
            "L1_vs_LC": "L1.request.json and LC.request.json differ only by cache_prompt",
        },
    }
    manifest_raw = canonical_json_bytes(manifest)
    write_new(args.out_dir / "manifest.json", manifest_raw)

    out = {
        "status": "LOGICAL_PREFIX_FIXTURE_V2_MATERIALIZED",
        "out_dir": str(args.out_dir),
        "manifest_sha256": sha256_bytes(manifest_raw),
        **manifest,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

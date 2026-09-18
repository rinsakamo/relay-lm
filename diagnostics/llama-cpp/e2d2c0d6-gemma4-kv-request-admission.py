#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

WARM_SHA = "c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2"
TARGET_SHA = "549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e"
WARM_LEN = 883
TARGET_LEN = 2927
LCP = 865


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_prompt_sha(tokens: list[int]) -> str:
    # Match the frozen fixture authority: compact JSON numeric array.
    data = json.dumps(tokens, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(data)


def load_request(path: Path):
    raw = path.read_bytes()
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError(f"{path}: request must be a JSON object")
    return raw, obj


def prompt(req: dict, path: Path) -> list[int]:
    value = req.get("prompt")
    if not isinstance(value, list) or not all(isinstance(x, int) and not isinstance(x, bool) for x in value):
        raise ValueError(f"{path}: prompt must be a numeric token array")
    return value


def lcp(a: list[int], b: list[int]) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def require_common(req: dict, path: Path):
    if req.get("n_predict") != 1:
        raise ValueError(f"{path}: n_predict must be exactly 1")
    if req.get("temperature") != 0:
        raise ValueError(f"{path}: temperature must be exactly 0")
    if req.get("stream", False):
        raise ValueError(f"{path}: streaming must be disabled")
    if req.get("n_probs", 0) < 20:
        raise ValueError(f"{path}: n_probs must be >= 20")
    if req.get("return_tokens") is not True:
        raise ValueError(f"{path}: return_tokens must be true")


def normalized_without_cache(req: dict):
    out = dict(req)
    out.pop("cache_prompt", None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("l0", type=Path)
    ap.add_argument("l1", type=Path)
    ap.add_argument("lc", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    errors = []
    evidence = {}
    loaded = {}

    for name, path in (("L0", args.l0), ("L1", args.l1), ("LC", args.lc)):
        try:
            raw, req = load_request(path)
            tok = prompt(req, path)
            require_common(req, path)
            loaded[name] = (raw, req, tok)
            evidence[name] = {
                "path": str(path),
                "request_sha256": sha256_bytes(raw),
                "prompt_len": len(tok),
                "prompt_array_sha256": canonical_prompt_sha(tok),
                "cache_prompt": req.get("cache_prompt"),
                "n_predict": req.get("n_predict"),
                "temperature": req.get("temperature"),
                "n_probs": req.get("n_probs"),
                "return_tokens": req.get("return_tokens"),
            }
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    if not errors:
        _, l0, warm = loaded["L0"]
        _, l1, target1 = loaded["L1"]
        _, lc, targetc = loaded["LC"]

        if len(warm) != WARM_LEN:
            errors.append(f"L0 prompt length {len(warm)} != {WARM_LEN}")
        if len(target1) != TARGET_LEN or len(targetc) != TARGET_LEN:
            errors.append("L1/LC target prompt length mismatch")
        if canonical_prompt_sha(warm) != WARM_SHA:
            errors.append("L0 frozen warm prompt SHA mismatch")
        if canonical_prompt_sha(target1) != TARGET_SHA:
            errors.append("L1 frozen target prompt SHA mismatch")
        if canonical_prompt_sha(targetc) != TARGET_SHA:
            errors.append("LC frozen target prompt SHA mismatch")
        if target1 != targetc:
            errors.append("L1 and LC prompt arrays differ")
        if lcp(warm, target1) != LCP:
            errors.append(f"warm/target LCP != {LCP}")

        if l0.get("cache_prompt") is not True:
            errors.append("L0 cache_prompt must be true")
        if l1.get("cache_prompt") is not True:
            errors.append("L1 cache_prompt must be true")
        if lc.get("cache_prompt") is not False:
            errors.append("LC cache_prompt must be false")

        if normalized_without_cache(l1) != normalized_without_cache(lc):
            errors.append("L1 and LC differ by more than cache_prompt")

    out = {
        "status": "REQUEST_ADMISSION_PASS" if not errors else "REQUEST_ADMISSION_FAIL",
        "errors": errors,
        "evidence": evidence,
        "l0r_request_rule": "reuse L0 request bytes exactly",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()

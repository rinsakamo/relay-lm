#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

WARM_FILE_SHA = "c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2"
TARGET_FILE_SHA = "549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e"
WARM_LEN = 883
TARGET_LEN = 2927
LCP = 865


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json_bytes(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw)


def load_token_file(path: Path, expected_sha: str, expected_len: int):
    raw, value = load_json_bytes(path)
    if sha256_bytes(raw) != expected_sha:
        raise ValueError(f"{path}: raw file SHA256 mismatch")
    if not isinstance(value, list) or not all(isinstance(x, int) and not isinstance(x, bool) for x in value):
        raise ValueError(f"{path}: must contain a numeric token array")
    if len(value) != expected_len:
        raise ValueError(f"{path}: token length {len(value)} != {expected_len}")
    return raw, value


def load_request(path: Path):
    raw, obj = load_json_bytes(path)
    if not isinstance(obj, dict):
        raise ValueError(f"{path}: request must be a JSON object")
    value = obj.get("prompt")
    if not isinstance(value, list) or not all(isinstance(x, int) and not isinstance(x, bool) for x in value):
        raise ValueError(f"{path}: prompt must be a numeric token array")
    return raw, obj, value


def lcp(a: list[int], b: list[int]) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def require_base(req: dict, path: Path):
    if req.get("n_predict") != 1:
        raise ValueError(f"{path}: n_predict must be exactly 1")
    if req.get("temperature") != 0:
        raise ValueError(f"{path}: temperature must be exactly 0")
    if req.get("stream", False):
        raise ValueError(f"{path}: streaming must be disabled")


def normalized_without_cache(req: dict):
    out = dict(req)
    out.pop("cache_prompt", None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--warm-tokens", type=Path, required=True)
    ap.add_argument("--target-tokens", type=Path, required=True)
    ap.add_argument("--l0", type=Path, required=True)
    ap.add_argument("--l1", type=Path, required=True)
    ap.add_argument("--lc", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    errors = []
    evidence = {}

    try:
        warm_raw, warm = load_token_file(args.warm_tokens, WARM_FILE_SHA, WARM_LEN)
        target_raw, target = load_token_file(args.target_tokens, TARGET_FILE_SHA, TARGET_LEN)
        evidence["fixture"] = {
            "warm_path": str(args.warm_tokens),
            "warm_file_sha256": sha256_bytes(warm_raw),
            "warm_len": len(warm),
            "target_path": str(args.target_tokens),
            "target_file_sha256": sha256_bytes(target_raw),
            "target_len": len(target),
            "lcp": lcp(warm, target),
        }
        if lcp(warm, target) != LCP:
            errors.append(f"fixture LCP != {LCP}")
    except Exception as exc:
        errors.append(f"fixture: {exc}")
        warm = None
        target = None

    loaded = {}
    for name, path in (("L0", args.l0), ("L1", args.l1), ("LC", args.lc)):
        try:
            raw, req, tok = load_request(path)
            require_base(req, path)
            loaded[name] = (raw, req, tok)
            evidence[name] = {
                "path": str(path),
                "request_sha256": sha256_bytes(raw),
                "prompt_len": len(tok),
                "cache_prompt": req.get("cache_prompt"),
                "n_predict": req.get("n_predict"),
                "temperature": req.get("temperature"),
                "n_probs": req.get("n_probs", 0),
                "return_tokens": req.get("return_tokens"),
            }
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    if warm is not None and target is not None and len(loaded) == 3:
        _, l0, l0_prompt = loaded["L0"]
        _, l1, l1_prompt = loaded["L1"]
        _, lc, lc_prompt = loaded["LC"]

        if l0_prompt != warm:
            errors.append("L0 prompt does not equal frozen warm token array")
        if l1_prompt != target:
            errors.append("L1 prompt does not equal frozen target token array")
        if lc_prompt != target:
            errors.append("LC prompt does not equal frozen target token array")

        if l0.get("cache_prompt") is not True:
            errors.append("L0 cache_prompt must be true")
        if l1.get("cache_prompt") is not True:
            errors.append("L1 cache_prompt must be true")
        if lc.get("cache_prompt") is not False:
            errors.append("LC cache_prompt must be false")

        if l1.get("n_probs", 0) < 20:
            errors.append("L1 n_probs must be >= 20")
        if lc.get("n_probs", 0) < 20:
            errors.append("LC n_probs must be >= 20")

        if normalized_without_cache(l1) != normalized_without_cache(lc):
            errors.append("L1 and LC differ by more than cache_prompt")

    out = {
        "status": "REQUEST_ADMISSION_PASS" if not errors else "REQUEST_ADMISSION_FAIL",
        "errors": errors,
        "evidence": evidence,
        "l0r_request_rule": "send the exact L0 request bytes again on the fresh WR2 server",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

PARENT_RELATIVE = Path("fixtures/e2d2c0d6-gemma4-kv-v2")
EXPECTED_PARENT_SUBTREE = "455d94850515c70995addc6c1c446ba738a01474"
EXPECTED_WARM_SHA = "cc42e325d85ed559835225b53152446bc405b2d166c10a3e16b07c7859bf7f27"
EXPECTED_TARGET_SHA = "8c05cf7a6d11d684be091c49a9f9d76201274e1efad31c9b19234cb4ec985730"
EXPECTED_WARM_LEN = 883
EXPECTED_TARGET_LEN = 2927
EXPECTED_LCP = 865
CONTROL_LEN = 883


def canonical_json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_raw_json(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw)


def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def write_new(path: Path, raw: bytes):
    require(not path.exists(), f"refusing to overwrite: {path}")
    path.write_bytes(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    if args.out_dir.exists():
        raise SystemExit(f"output directory must not exist: {args.out_dir}")

    here = Path(__file__).resolve().parent
    parent = here / PARENT_RELATIVE
    require(parent.is_dir(), f"parent fixture directory missing: {parent}")

    warm_raw, warm = load_raw_json(parent / "warm.tokens.json")
    target_raw, target = load_raw_json(parent / "target.tokens.json")

    require(sha256_bytes(warm_raw) == EXPECTED_WARM_SHA, "parent warm SHA mismatch")
    require(sha256_bytes(target_raw) == EXPECTED_TARGET_SHA, "parent target SHA mismatch")
    require(isinstance(warm, list) and all(isinstance(x, int) and not isinstance(x, bool) for x in warm), "warm tokens invalid")
    require(isinstance(target, list) and all(isinstance(x, int) and not isinstance(x, bool) for x in target), "target tokens invalid")
    require(len(warm) == EXPECTED_WARM_LEN, "parent warm length mismatch")
    require(len(target) == EXPECTED_TARGET_LEN, "parent target length mismatch")
    require(lcp(warm, target) == EXPECTED_LCP, "parent LCP mismatch")

    control = target[:CONTROL_LEN]
    require(len(control) == CONTROL_LEN, "control length mismatch")
    require(lcp(warm, control) == EXPECTED_LCP, "warm/control LCP mismatch")
    require(control != warm, "control must diverge from warm")
    require(control[EXPECTED_LCP] != warm[EXPECTED_LCP], "control must diverge exactly at LCP boundary")

    request = {
        "prompt": control,
        "cache_prompt": False,
        "n_predict": 1,
        "temperature": 0,
        "stream": False,
        "n_probs": 20,
    }

    control_tokens_raw = canonical_json_bytes(control)
    request_raw = canonical_json_bytes(request)

    args.out_dir.mkdir(parents=True)

    files = {
        "C883.tokens.json": control_tokens_raw,
        "C883.request.json": request_raw,
    }
    for name, raw in files.items():
        write_new(args.out_dir / name, raw)

    # With n_batch=n_ubatch=512 and completion/SWA checkpointing:
    # total=883 creates checkpoint boundaries at 883-512=371 and 883-4=879.
    # Position 511 is therefore captured after the second physical prompt decode.
    manifest = {
        "format_version": 1,
        "subject": "logical-prefix-kv-fixture-v2-segmentation-control",
        "parent_fixture": {
            "relative_path": str(PARENT_RELATIVE),
            "expected_subtree": EXPECTED_PARENT_SUBTREE,
            "warm_tokens_sha256": EXPECTED_WARM_SHA,
            "target_tokens_sha256": EXPECTED_TARGET_SHA,
        },
        "geometry": {
            "warm_len": EXPECTED_WARM_LEN,
            "control_len": CONTROL_LEN,
            "lcp": EXPECTED_LCP,
            "aligned_reuse": 512,
        },
        "expected_prompt_segmentation": {
            "n_batch": 512,
            "n_ubatch": 512,
            "total_tokens": CONTROL_LEN,
            "first_decode_tokens": 371,
            "second_decode_tokens": 508,
            "final_decode_tokens": 4,
            "logical_position_511_decode_ordinal": 2,
        },
        "request": {
            "cache_prompt": False,
            "n_predict": 1,
            "temperature": 0,
            "stream": False,
            "n_probs": 20,
        },
        "files": {
            name: {"sha256": sha256_bytes(raw), "bytes": len(raw)}
            for name, raw in files.items()
        },
        "interpretation": (
            "Compare fresh warm P512 against fresh C883 P512. "
            "Both prompts have equal total length and therefore equal checkpoint-driven "
            "physical prompt segmentation. Any remaining prefix KV difference cannot be "
            "attributed to the 883-vs-2927 segmentation difference observed previously."
        ),
    }
    manifest_raw = canonical_json_bytes(manifest)
    write_new(args.out_dir / "manifest.json", manifest_raw)

    out = {
        "status": "LOGICAL_PREFIX_SEGMENTATION_CONTROL_MATERIALIZED",
        "out_dir": str(args.out_dir),
        "manifest_sha256": sha256_bytes(manifest_raw),
        **manifest,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

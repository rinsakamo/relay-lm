#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

PROVENANCE_FILES = (
    "source-corpus.txt",
    "tokenizer-request.json",
    "tokenizer-response.json",
)
EXPECTED_FILES = (
    "warm.tokens.json",
    "target.tokens.json",
    "L0.request.json",
    "L1.request.json",
    "LC.request.json",
)
WARM_LEN = 883
TARGET_LEN = 2927
LCP_LEN = 865


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
        raise ValueError(message)


def normalized_without_cache(req):
    out = dict(req)
    out.pop("cache_prompt", None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    errors = []
    evidence = {}

    try:
        manifest_raw, manifest = load_raw_json(args.fixture_dir / "manifest.json")
        require(manifest.get("format_version") == 1, "manifest format_version must be 1")
        require(manifest.get("subject") == "logical-prefix-kv-fixture-v2", "unexpected fixture subject")
        files_meta = manifest.get("files")
        require(isinstance(files_meta, dict), "manifest files block missing")

        provenance_raw = {}
        for name in PROVENANCE_FILES:
            path = args.fixture_dir / name
            require(path.is_file(), f"fixture provenance file missing: {name}")
            raw = path.read_bytes()
            meta = files_meta.get(name)
            require(isinstance(meta, dict), f"manifest entry missing: {name}")
            observed = sha256_bytes(raw)
            require(meta.get("sha256") == observed, f"manifest SHA mismatch: {name}")
            require(meta.get("bytes") == len(raw), f"manifest byte count mismatch: {name}")
            provenance_raw[name] = raw
            evidence[name] = {
                "path": str(path),
                "sha256": observed,
                "bytes": len(raw),
            }

        corpus_text = provenance_raw["source-corpus.txt"].decode("utf-8")
        tokenizer_request = json.loads(provenance_raw["tokenizer-request.json"])
        require(
            tokenizer_request == {
                "content": corpus_text,
                "add_special": False,
                "parse_special": False,
                "with_pieces": False,
            },
            "tokenizer request/corpus/options mismatch",
        )
        tokenizer_response = json.loads(provenance_raw["tokenizer-response.json"])
        response_tokens = tokenizer_response.get("tokens") if isinstance(tokenizer_response, dict) else tokenizer_response
        require(
            isinstance(response_tokens, list)
            and all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in response_tokens),
            "tokenizer response tokens invalid",
        )

        tokenizer_provenance = manifest.get("tokenizer_provenance")
        require(isinstance(tokenizer_provenance, dict), "manifest tokenizer_provenance missing")
        require(
            tokenizer_provenance.get("corpus_sha256") == sha256_bytes(provenance_raw["source-corpus.txt"]),
            "manifest corpus SHA mismatch",
        )
        require(
            tokenizer_provenance.get("tokenizer_request_sha256") == sha256_bytes(provenance_raw["tokenizer-request.json"]),
            "manifest tokenizer request SHA mismatch",
        )
        require(
            tokenizer_provenance.get("tokenizer_response_sha256") == sha256_bytes(provenance_raw["tokenizer-response.json"]),
            "manifest tokenizer response SHA mismatch",
        )
        require(
            tokenizer_provenance.get("token_pool_len") == len(response_tokens),
            "manifest token_pool_len mismatch",
        )
        require(tokenizer_provenance.get("endpoint") == "/tokenize", "manifest tokenizer endpoint mismatch")
        require(tokenizer_provenance.get("add_special") is False, "manifest add_special mismatch")
        require(tokenizer_provenance.get("parse_special") is False, "manifest parse_special mismatch")
        require(tokenizer_provenance.get("with_pieces") is False, "manifest with_pieces mismatch")

        values = {}
        raw_files = {}
        for name in EXPECTED_FILES:
            path = args.fixture_dir / name
            require(path.is_file(), f"fixture file missing: {name}")
            raw, obj = load_raw_json(path)
            meta = files_meta.get(name)
            require(isinstance(meta, dict), f"manifest entry missing: {name}")
            observed = sha256_bytes(raw)
            require(meta.get("sha256") == observed, f"manifest SHA mismatch: {name}")
            require(meta.get("bytes") == len(raw), f"manifest byte count mismatch: {name}")
            values[name] = obj
            raw_files[name] = raw
            evidence[name] = {
                "path": str(path),
                "sha256": observed,
                "bytes": len(raw),
            }

        warm = values["warm.tokens.json"]
        target = values["target.tokens.json"]
        require(isinstance(warm, list) and all(isinstance(x, int) and not isinstance(x, bool) for x in warm), "warm tokens invalid")
        require(isinstance(target, list) and all(isinstance(x, int) and not isinstance(x, bool) for x in target), "target tokens invalid")
        require(len(warm) == WARM_LEN, f"warm length != {WARM_LEN}")
        require(len(target) == TARGET_LEN, f"target length != {TARGET_LEN}")
        require(lcp(warm, target) == LCP_LEN, f"LCP != {LCP_LEN}")

        geometry = manifest.get("geometry")
        require(isinstance(geometry, dict), "manifest geometry missing")
        require(geometry.get("warm_len") == WARM_LEN, "manifest warm_len mismatch")
        require(geometry.get("target_len") == TARGET_LEN, "manifest target_len mismatch")
        require(geometry.get("lcp") == LCP_LEN, "manifest LCP mismatch")

        l0 = values["L0.request.json"]
        l1 = values["L1.request.json"]
        lc = values["LC.request.json"]
        for label, req in (("L0", l0), ("L1", l1), ("LC", lc)):
            require(isinstance(req, dict), f"{label} request must be an object")
            require(req.get("n_predict") == 1, f"{label} n_predict != 1")
            require(req.get("temperature") == 0, f"{label} temperature != 0")
            require(req.get("stream") is False, f"{label} stream must be false")
            require(req.get("n_probs") == 20, f"{label} n_probs != 20")

        require(l0.get("prompt") == warm, "L0 prompt != warm fixture")
        require(l1.get("prompt") == target, "L1 prompt != target fixture")
        require(lc.get("prompt") == target, "LC prompt != target fixture")
        require(l0.get("cache_prompt") is True, "L0 cache_prompt must be true")
        require(l1.get("cache_prompt") is True, "L1 cache_prompt must be true")
        require(lc.get("cache_prompt") is False, "LC cache_prompt must be false")
        require(normalized_without_cache(l1) == normalized_without_cache(lc), "L1/LC differ by more than cache_prompt")

        evidence["manifest"] = {
            "path": str(args.fixture_dir / "manifest.json"),
            "sha256": sha256_bytes(manifest_raw),
            "corpus_sha256": tokenizer_provenance.get("corpus_sha256"),
            "tokenizer_request_sha256": tokenizer_provenance.get("tokenizer_request_sha256"),
            "tokenizer_response_sha256": tokenizer_provenance.get("tokenizer_response_sha256"),
            "token_pool_len": tokenizer_provenance.get("token_pool_len"),
            "target_suffix_source_offset": geometry.get("target_suffix_source_offset"),
        }
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")

    out = {
        "status": "LOGICAL_PREFIX_FIXTURE_V2_ADMISSION_PASS" if not errors else "LOGICAL_PREFIX_FIXTURE_V2_ADMISSION_FAIL",
        "errors": errors,
        "evidence": evidence,
        "l0r_request_rule": "send exact raw L0.request.json bytes on a fresh WR2 server",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

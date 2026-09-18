#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

WARM_SHA = "c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2"
TARGET_SHA = "549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e"
MAX_JSON_BYTES = 8 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json_file(path: Path):
    if path.stat().st_size > MAX_JSON_BYTES:
        return None, None
    raw = path.read_bytes()
    try:
        obj = json.loads(raw)
    except Exception:
        return raw, None
    return raw, obj


def is_token_array(obj):
    return isinstance(obj, list) and all(isinstance(x, int) and not isinstance(x, bool) for x in obj)


def request_role(obj, warm, target):
    if not isinstance(obj, dict):
        return None
    prompt = obj.get("prompt")
    if not is_token_array(prompt):
        return None
    if obj.get("n_predict") != 1 or obj.get("temperature") != 0 or obj.get("stream", False):
        return None

    cp = obj.get("cache_prompt")
    if prompt == warm and cp is True:
        return "L0"
    if prompt == target and cp is True and obj.get("n_probs", 0) >= 20:
        return "L1"
    if prompt == target and cp is False and obj.get("n_probs", 0) >= 20:
        return "LC"
    return None


def normalized_without_cache(obj):
    value = dict(obj)
    value.pop("cache_prompt", None)
    return value


def iter_json_files(roots):
    seen = set()
    for root in roots:
        root = root.resolve()
        if root in seen or not root.exists():
            continue
        seen.add(root)
        if root.is_file():
            if root.suffix.lower() == ".json":
                yield root
            continue
        for path in root.rglob("*.json"):
            try:
                if path.is_symlink() or not path.is_file():
                    continue
            except OSError:
                continue
            yield path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="+", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    files = []
    token_hits = {"warm": [], "target": []}

    # First pass: exact frozen token files by raw bytes.
    for path in iter_json_files(args.roots):
        try:
            raw, obj = load_json_file(path)
        except (OSError, PermissionError):
            continue
        if raw is None:
            continue
        digest = sha256(raw)
        if digest == WARM_SHA:
            token_hits["warm"].append({"path": str(path), "sha256": digest})
        if digest == TARGET_SHA:
            token_hits["target"].append({"path": str(path), "sha256": digest})
        files.append((path, raw, obj))

    errors = []
    if not token_hits["warm"]:
        errors.append("frozen warm token file not found")
    if not token_hits["target"]:
        errors.append("frozen target token file not found")

    warm = target = None
    if not errors:
        warm_paths = {x["path"] for x in token_hits["warm"]}
        target_paths = {x["path"] for x in token_hits["target"]}
        # Duplicate copies with identical raw hash are acceptable; choose lexicographically for admission input.
        warm_path = Path(sorted(warm_paths)[0])
        target_path = Path(sorted(target_paths)[0])
        _, warm = load_json_file(warm_path)
        _, target = load_json_file(target_path)
        if not is_token_array(warm) or len(warm) != 883:
            errors.append("warm token file content/length invalid")
        if not is_token_array(target) or len(target) != 2927:
            errors.append("target token file content/length invalid")

    request_hits = {"L0": [], "L1": [], "LC": []}
    if not errors:
        for path, raw, obj in files:
            role = request_role(obj, warm, target)
            if role:
                request_hits[role].append({
                    "path": str(path),
                    "sha256": sha256(raw),
                    "normalized_without_cache": normalized_without_cache(obj),
                })

    selected = {}
    if not errors:
        for role in ("L0", "L1", "LC"):
            hits = request_hits[role]
            if not hits:
                errors.append(f"no saved {role} request candidate found")
                continue
            by_sha = {}
            for hit in hits:
                by_sha.setdefault(hit["sha256"], []).append(hit["path"])
            if len(by_sha) != 1:
                errors.append(
                    f"{role} request identity ambiguous: {len(by_sha)} distinct raw request SHA256 values"
                )
                continue
            digest, paths = next(iter(by_sha.items()))
            selected[role] = {"path": sorted(paths)[0], "sha256": digest, "copies": sorted(paths)}

    if not errors and "L1" in selected and "LC" in selected:
        l1_hit = next(x for x in request_hits["L1"] if x["sha256"] == selected["L1"]["sha256"])
        lc_hit = next(x for x in request_hits["LC"] if x["sha256"] == selected["LC"]["sha256"])
        if l1_hit["normalized_without_cache"] != lc_hit["normalized_without_cache"]:
            errors.append("selected L1 and LC differ by more than cache_prompt")

    status = "ARTIFACT_LOCATOR_PASS" if not errors else "ARTIFACT_LOCATOR_FAIL"
    out = {
        "status": status,
        "errors": errors,
        "searched_roots": [str(x) for x in args.roots],
        "frozen_token_hits": token_hits,
        "request_candidates": {
            role: [{"path": x["path"], "sha256": x["sha256"]} for x in hits]
            for role, hits in request_hits.items()
        },
        "selected": selected if not errors else {},
        "rule": "Never reconstruct missing or ambiguous measured request artifacts.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(root: Path):
    bins = {}
    meta = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if p.suffix == ".bin":
            bins[rel] = sha256(p)
        elif p.name.endswith(".cells.tsv") or p.name.endswith(".manifest.tsv"):
            meta[rel] = sha256(p)
    return bins, meta


def compare(a, b):
    keys = sorted(set(a) | set(b))
    missing_left = [k for k in keys if k not in a]
    missing_right = [k for k in keys if k not in b]
    different = [k for k in keys if k in a and k in b and a[k] != b[k]]
    return {
        "equal": not missing_left and not missing_right and not different,
        "missing_left": missing_left,
        "missing_right": missing_right,
        "different": different,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--w", default="WR-P512")
    ap.add_argument("--r", default="WR-R512")
    ap.add_argument("--w2", default="WR2-P512")
    ap.add_argument("--c", default="C-P512")
    args = ap.parse_args()

    roots = {
        "W": args.root / args.w,
        "R": args.root / args.r,
        "W2": args.root / args.w2,
        "C": args.root / args.c,
    }

    for name, root in roots.items():
        if not root.is_dir():
            raise SystemExit(f"missing dump directory for {name}: {root}")

    data = {}
    for name, root in roots.items():
        bins, meta = collect(root)
        data[name] = {
            "root": str(root),
            "kv_sha256": bins,
            "meta_sha256": meta,
        }

    ww2 = compare(data["W"]["kv_sha256"], data["W2"]["kv_sha256"])
    wc = compare(data["W"]["kv_sha256"], data["C"]["kv_sha256"])
    wr = compare(data["W"]["kv_sha256"], data["R"]["kv_sha256"])
    rc = compare(data["R"]["kv_sha256"], data["C"]["kv_sha256"])

    layout_ww2 = compare(data["W"]["meta_sha256"], data["W2"]["meta_sha256"])
    layout_wc = compare(data["W"]["meta_sha256"], data["C"]["meta_sha256"])
    layout_wr = compare(data["W"]["meta_sha256"], data["R"]["meta_sha256"])

    if not ww2["equal"]:
        classification = "PREFIX_DUMP_NOT_REPRODUCIBLE"
    elif not wc["equal"]:
        classification = "PREFIX_KV_GENERATION_DIFFERS"
    elif not wr["equal"]:
        classification = "RETAINED_PREFIX_KV_MUTATED_BY_REUSE"
    else:
        classification = "PREFIX_KV_IDENTICAL_THROUGH_REUSE"

    out = {
        "classification": classification,
        "kv": {
            "W_vs_W2": ww2,
            "W_vs_C": wc,
            "W_vs_R": wr,
            "R_vs_C": rc,
        },
        "layout_metadata": {
            "W_vs_W2": layout_ww2,
            "W_vs_C": layout_wc,
            "W_vs_R": layout_wr,
        },
        "dumps": data,
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

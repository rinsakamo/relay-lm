#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

LINES = 2048
WORDS = (
    "relay cognition cache prefix memory boundary attention world self "
    "signal sequence tensor layer token context stable synthetic diagnostic"
)


def build_corpus() -> str:
    rows = [
        "RelayLM logical-prefix KV fixture v2 synthetic tokenizer corpus.",
        "This material is diagnostic-only and carries no benchmark content.",
    ]
    for i in range(LINES):
        rows.append(
            f"fixture-line-{i:05d} {WORDS} ordinal-{i:05d} "
            f"group-{i % 97:02d} phase-{i % 31:02d}."
        )
    return "\n".join(rows) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--request-out", type=Path, required=True)
    args = ap.parse_args()

    if args.out.exists():
        raise SystemExit(f"refusing to overwrite: {args.out}")
    if args.request_out.exists():
        raise SystemExit(f"refusing to overwrite: {args.request_out}")

    corpus = build_corpus()
    raw = corpus.encode("utf-8")
    request = {
        "content": corpus,
        "add_special": False,
        "parse_special": False,
        "with_pieces": False,
    }
    request_raw = (
        json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.request_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(raw)
    args.request_out.write_bytes(request_raw)

    print(f"corpus_path={args.out}")
    print(f"corpus_bytes={len(raw)}")
    print(f"corpus_sha256={hashlib.sha256(raw).hexdigest()}")
    print(f"request_path={args.request_out}")
    print(f"request_bytes={len(request_raw)}")
    print(f"request_sha256={hashlib.sha256(request_raw).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

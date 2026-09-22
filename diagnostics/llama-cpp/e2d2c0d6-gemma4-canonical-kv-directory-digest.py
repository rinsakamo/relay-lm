#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys


EXPECTED_MANIFEST_ROWS = {"base": 16, "swa": 80}
EXPECTED_KV_SIZE = {"base": 8192, "swa": 1536}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_cells(path: Path, cache: str):
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    expected_fields = ["cache", "stream", "head", "kv_size", "v_trans", "position", "cell"]
    if not rows or list(rows[0].keys()) != expected_fields:
        raise RuntimeError(f"unexpected cells schema: {path}")
    if len(rows) != 512:
        raise RuntimeError(f"{path}: data rows={len(rows)}, expected 512")
    positions = [int(r["position"]) for r in rows]
    if positions != list(range(512)):
        raise RuntimeError(f"{path}: logical positions are not exactly 0..511")
    if {r["cache"] for r in rows} != {cache}:
        raise RuntimeError(f"{path}: cache identity mismatch")
    if {int(r["kv_size"]) for r in rows} != {EXPECTED_KV_SIZE[cache]}:
        raise RuntimeError(f"{path}: unexpected kv_size")
    if {int(r["v_trans"]) for r in rows} != {0}:
        raise RuntimeError(f"{path}: V cache must be non-transposed")
    if len({int(r["cell"]) for r in rows}) != 512:
        raise RuntimeError(f"{path}: physical cell mapping is not unique")
    return {
        "rows": 512,
        "kv_size": EXPECTED_KV_SIZE[cache],
        "head": sorted({int(r["head"]) for r in rows}),
        "stream": sorted({int(r["stream"]) for r in rows}),
    }


def validate_manifest(root: Path, cache: str):
    path = root / f"{cache}.manifest.tsv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    expected_fields = ["cache", "layer", "kind", "type", "row_bytes", "rows"]
    if not rows or list(rows[0].keys()) != expected_fields:
        raise RuntimeError(f"unexpected manifest schema: {path}")
    if len(rows) != EXPECTED_MANIFEST_ROWS[cache]:
        raise RuntimeError(
            f"{path}: rows={len(rows)}, expected {EXPECTED_MANIFEST_ROWS[cache]}"
        )

    payloads = []
    layer_kinds = {}
    for row in rows:
        if row["cache"] != cache or row["kind"] not in {"K", "V"}:
            raise RuntimeError(f"invalid manifest row: {row}")
        layer = int(row["layer"])
        kind = row["kind"]
        row_bytes = int(row["row_bytes"])
        nrows = int(row["rows"])
        if row_bytes <= 0 or nrows != 512:
            raise RuntimeError(f"invalid payload geometry: {row}")
        layer_kinds.setdefault(layer, set()).add(kind)
        payload = root / f"{cache}.layer-{layer}.{kind}.bin"
        if not payload.is_file():
            raise RuntimeError(f"payload missing: {payload}")
        expected_size = row_bytes * nrows
        if payload.stat().st_size != expected_size:
            raise RuntimeError(
                f"{payload}: size={payload.stat().st_size}, expected={expected_size}"
            )
        payloads.append(payload)

    bad = sorted(layer for layer, kinds in layer_kinds.items() if kinds != {"K", "V"})
    if bad:
        raise RuntimeError(f"{cache}: incomplete K/V layer pairs: {bad}")
    return payloads


def digest_directory(root: Path):
    if not root.is_dir():
        raise RuntimeError(f"KV root is not a directory: {root}")

    expected = {
        "base.cells.tsv",
        "base.manifest.tsv",
        "swa.cells.tsv",
        "swa.manifest.tsv",
    }
    geometry = {}
    payloads = []
    for cache in ("base", "swa"):
        geometry[cache] = validate_cells(root / f"{cache}.cells.tsv", cache)
        payloads.extend(validate_manifest(root, cache))

    expected.update(p.name for p in payloads)
    actual = {p.name for p in root.iterdir() if p.is_file()}
    if actual != expected:
        raise RuntimeError(
            f"file set mismatch: missing={sorted(expected-actual)} "
            f"unexpected={sorted(actual-expected)}"
        )
    if len(payloads) != 96 or len(expected) != 100:
        raise RuntimeError(
            f"unexpected canonical file counts: payloads={len(payloads)}, files={len(expected)}"
        )

    records = []
    aggregate = hashlib.sha256()
    for name in sorted(expected):
        path = root / name
        file_sha = sha256_file(path)
        size = path.stat().st_size
        record = f"{name}\0{size}\0{file_sha}\n".encode("utf-8")
        aggregate.update(record)
        records.append({"path": name, "size": size, "sha256": file_sha})

    return {
        "classification": "CANONICAL_KV_DIRECTORY_DIGEST_COMPLETE",
        "root": str(root.resolve()),
        "algorithm": "sha256(sorted(relative_path\\0size\\0file_sha256\\n))",
        "directory_sha256": aggregate.hexdigest(),
        "file_count": len(records),
        "payload_count": len(payloads),
        "geometry": geometry,
        "files": records,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kv_root", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    result = digest_directory(args.kv_root)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"

    if args.out is not None:
        if args.out.exists():
            raise RuntimeError(f"refusing to overwrite output: {args.out}")
        args.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

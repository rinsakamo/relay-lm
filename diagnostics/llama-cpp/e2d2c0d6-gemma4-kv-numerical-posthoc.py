#!/usr/bin/env python3
"""Zero-GPU numeric comparison for canonical logical-prefix KV dumps.

Never guess cache dtype. Read it from base/swa manifest.tsv. Numeric decoding is
limited to f16/f32/bf16; all other types remain byte-authoritative and are
reported UNSUPPORTED_TYPE.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path

SCALAR = {"f16": (2, "e", "H"), "f32": (4, "f", "I"), "bf16": (2, None, "H")}
MANIFEST_HEADER = "cache\tlayer\tkind\ttype\trow_bytes\trows"
CELLS_HEADER = "cache\tstream\thead\tkv_size\tv_trans\tposition\tcell"


def manifest(root: Path, cache: str):
    lines = (root / f"{cache}.manifest.tsv").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != MANIFEST_HEADER:
        raise ValueError(f"bad manifest header: {cache}")
    out = {}
    for line in lines[1:]:
        f = line.split("\t")
        if len(f) != 6 or f[0] != cache or f[2] not in {"K", "V"}:
            raise ValueError(f"bad manifest row: {line!r}")
        layer, kind, dtype, row_bytes, rows = int(f[1]), f[2], f[3], int(f[4]), int(f[5])
        if row_bytes <= 0 or rows <= 0:
            raise ValueError("invalid geometry")
        key = (layer, kind)
        if key in out:
            raise ValueError(f"duplicate manifest key: {key}")
        out[key] = (dtype, row_bytes, rows)
    if not out:
        raise ValueError(f"empty manifest: {cache}")
    return out


def cells(root: Path, cache: str):
    lines = (root / f"{cache}.cells.tsv").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != CELLS_HEADER:
        raise ValueError(f"bad cells header: {cache}")
    out = []
    for line in lines[1:]:
        f = line.split("\t")
        if len(f) != 7 or f[0] != cache:
            raise ValueError(f"bad cells row: {line!r}")
        out.append((int(f[5]), int(f[6])))
    if [p for p, _ in out] != list(range(len(out))):
        raise ValueError(f"non-canonical logical positions: {cache}")
    return out


def bf16(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits << 16))[0]


def decode(buf: bytes, dtype: str):
    size, fmt, ifmt = SCALAR[dtype]
    if len(buf) % size:
        raise ValueError(f"unaligned {dtype} payload")
    n = len(buf) // size
    bits = list(struct.unpack(f"<{n}{ifmt}", buf))
    if dtype == "bf16":
        vals = [bf16(x) for x in bits]
    else:
        vals = list(struct.unpack(f"<{n}{fmt}", buf))
    return vals, bits, size * 8


def ordered(bits: int, width: int) -> int:
    sign = 1 << (width - 1)
    mask = (1 << width) - 1
    return ((~bits) & mask) if bits & sign else bits | sign


def numeric(a: bytes, b: bytes, dtype: str):
    av, ab, width = decode(a, dtype)
    bv, bb, _ = decode(b, dtype)
    if len(av) != len(bv):
        raise ValueError("decoded length mismatch")
    finite = nan = inf = diff = 0
    abs_sum = rel_sum = max_abs = max_rel = 0.0
    max_ulp = 0
    for x, y, xb, yb in zip(av, bv, ab, bb):
        diff += xb != yb
        if math.isnan(x) or math.isnan(y):
            nan += 1
            continue
        if math.isinf(x) or math.isinf(y):
            inf += 1
            continue
        finite += 1
        d = abs(x - y)
        r = d / max(abs(x), abs(y), 1e-30)
        abs_sum += d
        rel_sum += r
        max_abs = max(max_abs, d)
        max_rel = max(max_rel, r)
        if xb != yb:
            max_ulp = max(max_ulp, abs(ordered(xb, width) - ordered(yb, width)))
    return {
        "numeric_status": "DECODED",
        "dtype": dtype,
        "elements": len(av),
        "differing_elements": diff,
        "finite_pairs": finite,
        "nan_pairs": nan,
        "inf_pairs": inf,
        "max_abs_error": max_abs,
        "mean_abs_error": abs_sum / finite if finite else None,
        "max_relative_error": max_rel,
        "mean_relative_error": rel_sum / finite if finite else None,
        "max_ulp_like_distance": max_ulp,
    }


def one_file(left: Path, right: Path, cache: str, layer: int, kind: str, spec):
    dtype, row_bytes, rows = spec
    name = f"{cache}.layer-{layer}.{kind}.bin"
    a = (left / name).read_bytes()
    b = (right / name).read_bytes()
    expected = row_bytes * rows
    if len(a) != expected or len(b) != expected:
        raise ValueError(f"payload size mismatch: {name}")
    byte_diff = sum(x != y for x, y in zip(a, b))
    row_diffs = []
    per_row = []
    for row in range(rows):
        s, e = row * row_bytes, (row + 1) * row_bytes
        d = sum(x != y for x, y in zip(a[s:e], b[s:e]))
        per_row.append(d)
        if d:
            row_diffs.append(row)
    result = {
        "file": name, "cache": cache, "layer": layer, "kind": kind, "dtype": dtype,
        "row_bytes": row_bytes, "rows": rows, "bytes": expected,
        "differing_bytes": byte_diff,
        "differing_byte_fraction": byte_diff / expected if expected else 0.0,
        "differing_rows": len(row_diffs),
        "first_differing_position": row_diffs[0] if row_diffs else None,
        "last_differing_position": row_diffs[-1] if row_diffs else None,
        "max_differing_bytes_per_row": max(per_row, default=0),
    }
    if dtype in SCALAR:
        result["numeric"] = numeric(a, b, dtype)
    else:
        result["numeric"] = {"numeric_status": "UNSUPPORTED_TYPE", "dtype": dtype}
    return result


def analyze(left: Path, right: Path):
    left, right = left.resolve(strict=True), right.resolve(strict=True)
    files = []
    layout = {}
    for cache in ("base", "swa"):
        lm, rm = manifest(left, cache), manifest(right, cache)
        if lm != rm:
            raise ValueError(f"manifest mismatch: {cache}")
        lc, rc = cells(left, cache), cells(right, cache)
        layout[cache] = {
            "rows": len(lc),
            "logical_positions_equal": [p for p, _ in lc] == [p for p, _ in rc],
            "physical_cell_mapping_equal": lc == rc,
        }
        for layer, kind in sorted(lm):
            files.append(one_file(left, right, cache, layer, kind, lm[(layer, kind)]))
    differing = [x for x in files if x["differing_bytes"]]
    unsupported = sorted({x["dtype"] for x in files if x["numeric"]["numeric_status"] != "DECODED"})
    groups = {}
    for x in files:
        key = f"{x['cache']}:{x['kind']}"
        g = groups.setdefault(key, {"files": 0, "bytes": 0, "differing_bytes": 0, "differing_rows_sum": 0})
        g["files"] += 1
        g["bytes"] += x["bytes"]
        g["differing_bytes"] += x["differing_bytes"]
        g["differing_rows_sum"] += x["differing_rows"]
    for g in groups.values():
        g["differing_byte_fraction"] = g["differing_bytes"] / g["bytes"] if g["bytes"] else 0.0
    return {
        "classification": "KV_NUMERICAL_POSTHOC_COMPLETE" if not unsupported else "KV_BYTE_POSTHOC_COMPLETE_NUMERIC_PARTIAL",
        "left": str(left), "right": str(right), "layout": layout,
        "file_count": len(files), "differing_file_count": len(differing),
        "first_differing_file": differing[0]["file"] if differing else None,
        "numeric_unsupported_types": unsupported, "groups": groups, "files": files,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("left", type=Path)
    ap.add_argument("right", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    payload = json.dumps(analyze(args.left, args.right), indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

EXPECTED_TENSORS = ("attn_norm-0", "Kcur-0", "Vcur-0")
W_DUMPS = ("W-p0-370-w371", "W-p371-878-w508")
C_DUMP = "C-p0-511-w512"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_projection_dump(path: Path):
    if not path.is_dir():
        raise RuntimeError(f"projection dump missing: {path}")

    positions_path = path / "positions.tsv"
    manifest_path = path / "manifest.tsv"
    if not positions_path.is_file() or not manifest_path.is_file():
        raise RuntimeError(f"projection metadata missing: {path}")

    with positions_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if not rows or set(rows[0]) != {"column", "position"}:
        raise RuntimeError(f"unexpected positions schema: {positions_path}")

    positions = [int(row["position"]) for row in rows]
    columns = [int(row["column"]) for row in rows]
    if columns != list(range(len(rows))):
        raise RuntimeError(f"non-canonical physical columns: {path}")
    if positions != list(range(positions[0], positions[0] + len(positions))):
        raise RuntimeError(f"non-contiguous logical positions: {path}")

    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        manifest_rows = list(csv.DictReader(f, delimiter="\t"))
    by_name = {row["name"]: row for row in manifest_rows}
    if set(by_name) != set(EXPECTED_TENSORS):
        raise RuntimeError(
            f"projection tensor set mismatch: {path}: {sorted(by_name)}"
        )

    tensors = {}
    for name in EXPECTED_TENSORS:
        row = by_name[name]
        if row["type"] != "f32":
            raise RuntimeError(f"{path}/{name}: type={row['type']!r}, expected f32")
        ne0 = int(row["ne0"])
        ne1 = int(row["ne1"])
        ne2 = int(row["ne2"])
        ne3 = int(row["ne3"])
        row_bytes = int(row["row_bytes"])
        nrows = int(row["rows"])
        if ne1 != len(positions) or nrows != len(positions) or ne2 != 1 or ne3 != 1:
            raise RuntimeError(f"{path}/{name}: unexpected tensor geometry")
        if row_bytes != ne0 * 4:
            raise RuntimeError(
                f"{path}/{name}: row_bytes={row_bytes}, expected {ne0 * 4}"
            )
        payload = path / f"{name}.bin"
        if not payload.is_file():
            raise RuntimeError(f"projection payload missing: {payload}")
        raw = payload.read_bytes()
        expected_size = row_bytes * nrows
        if len(raw) != expected_size:
            raise RuntimeError(
                f"{payload}: size={len(raw)}, expected {expected_size}"
            )
        row_map = {
            pos: raw[i * row_bytes : (i + 1) * row_bytes]
            for i, pos in enumerate(positions)
        }
        tensors[name] = {
            "ne0": ne0,
            "row_bytes": row_bytes,
            "rows": row_map,
            "sha256": sha256(payload),
        }

    return {
        "path": str(path),
        "positions": positions,
        "tensors": tensors,
    }


def merge_projection_rows(dumps, positions):
    out = {name: {} for name in EXPECTED_TENSORS}
    geometry = {}
    for dump in dumps:
        for name in EXPECTED_TENSORS:
            tensor = dump["tensors"][name]
            g = (tensor["ne0"], tensor["row_bytes"])
            if name in geometry and geometry[name] != g:
                raise RuntimeError(f"inconsistent geometry across warm dumps: {name}")
            geometry[name] = g
            for pos, row in tensor["rows"].items():
                if pos in out[name]:
                    raise RuntimeError(f"duplicate warm logical position {pos} for {name}")
                out[name][pos] = row

    required = set(positions)
    for name in EXPECTED_TENSORS:
        missing = sorted(required - set(out[name]))
        if missing:
            raise RuntimeError(f"warm projection positions missing for {name}: {missing[:8]}")
        out[name] = {pos: out[name][pos] for pos in positions}
    return out, geometry


def f32_ordered(bits: int) -> int:
    if bits & 0x80000000:
        return (~bits) & 0xFFFFFFFF
    return bits | 0x80000000


def compare_f32_rows(a_rows, b_rows, positions, ne0):
    differing_rows = []
    differing_elements = 0
    total_elements = len(positions) * ne0
    abs_sum = 0.0
    rel_sum = 0.0
    max_abs = 0.0
    max_rel = 0.0
    max_ulp = 0

    for pos in positions:
        a = a_rows[pos]
        b = b_rows[pos]
        if len(a) != len(b) or len(a) != ne0 * 4:
            raise RuntimeError(f"row geometry mismatch at position {pos}")
        if a != b:
            differing_rows.append(pos)

        for off in range(0, len(a), 4):
            abits = struct.unpack_from("<I", a, off)[0]
            bbits = struct.unpack_from("<I", b, off)[0]
            av = struct.unpack_from("<f", a, off)[0]
            bv = struct.unpack_from("<f", b, off)[0]
            if not math.isfinite(av) or not math.isfinite(bv):
                raise RuntimeError(
                    f"non-finite f32 value at position {pos}, element {off // 4}"
                )
            delta = abs(av - bv)
            scale = max(abs(av), abs(bv))
            rel = delta / scale if scale else 0.0
            abs_sum += delta
            rel_sum += rel
            max_abs = max(max_abs, delta)
            max_rel = max(max_rel, rel)
            if abits != bbits:
                differing_elements += 1
                ulp = abs(f32_ordered(abits) - f32_ordered(bbits))
                max_ulp = max(max_ulp, ulp)

    return {
        "rows": len(positions),
        "differing_rows": len(differing_rows),
        "differing_row_fraction": len(differing_rows) / len(positions),
        "first_differing_position": differing_rows[0] if differing_rows else None,
        "last_differing_position": differing_rows[-1] if differing_rows else None,
        "elements": total_elements,
        "differing_elements": differing_elements,
        "differing_element_fraction": (
            differing_elements / total_elements if total_elements else 0.0
        ),
        "max_absolute_error": max_abs,
        "mean_absolute_error": abs_sum / total_elements if total_elements else 0.0,
        "max_relative_error": max_rel,
        "mean_relative_error": rel_sum / total_elements if total_elements else 0.0,
        "max_ulp_like_distance": max_ulp,
        "bit_exact_equal": differing_elements == 0,
    }


def parse_cells(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    required = {"cache", "stream", "head", "kv_size", "v_trans", "position", "cell"}
    if not rows or set(rows[0]) != required:
        raise RuntimeError(f"unexpected cells schema: {path}")
    return {
        "mapping": [(int(r["position"]), int(r["cell"])) for r in rows],
        "kv_size": sorted({int(r["kv_size"]) for r in rows}),
        "v_trans": sorted({int(r["v_trans"]) for r in rows}),
        "heads": sorted({int(r["head"]) for r in rows}),
        "streams": sorted({int(r["stream"]) for r in rows}),
    }


def kv_integrity_compare(new_dir: Path, historical_dir: Path):
    if not new_dir.is_dir() or not historical_dir.is_dir():
        raise RuntimeError(
            f"KV integrity input missing: new={new_dir} historical={historical_dir}"
        )

    result = {
        "new": str(new_dir),
        "historical": str(historical_dir),
        "metadata": {},
        "payloads": {},
    }
    ok = True

    expected_bins = set()
    for cache in ("base", "swa"):
        new_cells = parse_cells(new_dir / f"{cache}.cells.tsv")
        hist_cells = parse_cells(historical_dir / f"{cache}.cells.tsv")
        cells_equal = (
            new_cells["mapping"] == hist_cells["mapping"]
            and new_cells["kv_size"] == hist_cells["kv_size"]
            and new_cells["v_trans"] == hist_cells["v_trans"]
        )

        new_manifest = (new_dir / f"{cache}.manifest.tsv").read_bytes()
        hist_manifest = (historical_dir / f"{cache}.manifest.tsv").read_bytes()
        manifest_equal = new_manifest == hist_manifest

        result["metadata"][cache] = {
            "mapping_kvsize_vtrans_equal": cells_equal,
            "manifest_byte_equal": manifest_equal,
            "new_heads": new_cells["heads"],
            "historical_heads": hist_cells["heads"],
            "new_streams": new_cells["streams"],
            "historical_streams": hist_cells["streams"],
        }
        ok = ok and cells_equal and manifest_equal

        with (new_dir / f"{cache}.manifest.tsv").open(
            "r", encoding="utf-8", newline=""
        ) as f:
            rows = list(csv.DictReader(f, delimiter="\t"))
        for row in rows:
            expected_bins.add(f"{cache}.layer-{int(row['layer'])}.{row['kind']}.bin")

    new_bins = {p.name for p in new_dir.glob("*.bin") if p.is_file()}
    hist_bins = {p.name for p in historical_dir.glob("*.bin") if p.is_file()}
    file_set_equal = new_bins == hist_bins == expected_bins
    result["payloads"]["file_set_equal"] = file_set_equal
    result["payloads"]["expected_count"] = len(expected_bins)
    result["payloads"]["new_count"] = len(new_bins)
    result["payloads"]["historical_count"] = len(hist_bins)
    ok = ok and file_set_equal

    differing = []
    if file_set_equal:
        for name in sorted(expected_bins):
            a = new_dir / name
            b = historical_dir / name
            if a.stat().st_size != b.stat().st_size or a.read_bytes() != b.read_bytes():
                differing.append(name)
    result["payloads"]["differing_files"] = differing
    result["payloads"]["differing_count"] = len(differing)
    result["equal"] = ok and not differing
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projection-root", type=Path, required=True)
    ap.add_argument("--instrumented-kv-root", type=Path, required=True)
    ap.add_argument("--historical-kv-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    if args.out.exists():
        raise RuntimeError(f"output path already exists: {args.out}")

    integrity = {
        "W": kv_integrity_compare(
            args.instrumented_kv_root / "W-P512",
            args.historical_kv_root / "WR-P512",
        ),
        "C": kv_integrity_compare(
            args.instrumented_kv_root / "C-P512",
            args.historical_kv_root / "C-P512",
        ),
    }

    out = {
        "integrity": integrity,
        "primary_classification": None,
        "projection": None,
    }

    if not all(x["equal"] for x in integrity.values()):
        out["primary_classification"] = "INSTRUMENTATION_PERTURBED_SUBJECT"
        args.out.mkdir(parents=True, exist_ok=False)
        (args.out / "terminal.json").write_text(
            json.dumps(out, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(out, indent=2, sort_keys=True))
        return 2

    warm_dumps = [
        load_projection_dump(args.projection_root / name)
        for name in W_DUMPS
    ]
    cold_dump = load_projection_dump(args.projection_root / C_DUMP)

    if warm_dumps[0]["positions"] != list(range(0, 371)):
        raise RuntimeError("unexpected W width-371 logical positions")
    if warm_dumps[1]["positions"] != list(range(371, 879)):
        raise RuntimeError("unexpected W width-508 logical positions")
    if cold_dump["positions"] != list(range(0, 512)):
        raise RuntimeError("unexpected C width-512 logical positions")

    positions = list(range(512))
    warm, warm_geometry = merge_projection_rows(warm_dumps, positions)

    result = {}
    for name in EXPECTED_TENSORS:
        cold_tensor = cold_dump["tensors"][name]
        ne0, row_bytes = warm_geometry[name]
        if (cold_tensor["ne0"], cold_tensor["row_bytes"]) != (ne0, row_bytes):
            raise RuntimeError(f"W/C projection geometry mismatch: {name}")
        cold_rows = {pos: cold_tensor["rows"][pos] for pos in positions}

        result[name] = {
            "all": compare_f32_rows(warm[name], cold_rows, positions, ne0),
            "segment_A_0_370": compare_f32_rows(
                warm[name], cold_rows, list(range(0, 371)), ne0
            ),
            "segment_B_371_511": compare_f32_rows(
                warm[name], cold_rows, list(range(371, 512)), ne0
            ),
        }

    pre_equal = result["attn_norm-0"]["all"]["bit_exact_equal"]
    k_equal = result["Kcur-0"]["all"]["bit_exact_equal"]
    v_equal = result["Vcur-0"]["all"]["bit_exact_equal"]

    if not pre_equal:
        classification = "LAYER0_PREPROJECTION_DIFFERENCE_OBSERVED"
    elif not k_equal or not v_equal:
        classification = "LAYER0_PROJECTION_NUMERICAL_ORIGIN_OBSERVED"
    elif k_equal and v_equal:
        classification = "LAYER0_PROJECTION_OUTPUT_IDENTICAL_ORIGIN_LATER"
    else:
        classification = "LAYER0_PROJECTION_PARTIAL_OR_AMBIGUOUS"

    out["primary_classification"] = classification
    out["projection"] = result
    out["logical_mapping"] = {
        "W_0_370": "W-p0-370-w371 columns 0..370",
        "W_371_511": "W-p371-878-w508 columns 0..140",
        "C_0_511": "C-p0-511-w512 columns 0..511",
    }

    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "terminal.json").write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

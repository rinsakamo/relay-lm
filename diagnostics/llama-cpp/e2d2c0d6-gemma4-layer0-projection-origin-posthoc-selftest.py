#!/usr/bin/env python3
import csv
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
ANALYZER = HERE / "e2d2c0d6-gemma4-layer0-projection-origin-posthoc.py"


def write_projection_dump(root: Path, name: str, positions, mutate=None):
    d = root / name
    d.mkdir(parents=True, exist_ok=False)
    (d / "positions.tsv").write_text(
        "column\tposition\n" +
        "".join(f"{i}\t{p}\n" for i, p in enumerate(positions)),
        encoding="utf-8",
    )

    ne0 = 2
    row_bytes = ne0 * 4
    rows = len(positions)
    manifest_lines = [
        "name\ttype\tne0\tne1\tne2\tne3\tnb0\tnb1\tnb2\tnb3\trow_bytes\trows\n"
    ]
    for tensor in ("attn_norm-0", "Kcur-0", "Vcur-0"):
        manifest_lines.append(
            f"{tensor}\tf32\t{ne0}\t{rows}\t1\t1\t4\t{row_bytes}\t"
            f"{row_bytes * rows}\t{row_bytes * rows}\t{row_bytes}\t{rows}\n"
        )
        raw = bytearray()
        for pos in positions:
            vals = [
                pos * 0.001 + (0.1 if tensor == "Kcur-0" else 0.2 if tensor == "Vcur-0" else 0.0),
                pos * -0.002 + (0.3 if tensor == "Kcur-0" else 0.4 if tensor == "Vcur-0" else 0.0),
            ]
            if mutate is not None:
                vals = mutate(tensor, pos, vals)
            raw.extend(struct.pack("<2f", *vals))
        (d / f"{tensor}.bin").write_bytes(raw)

    (d / "manifest.tsv").write_text("".join(manifest_lines), encoding="utf-8")


def write_kv_dump(root: Path, name: str, head: int):
    d = root / name
    d.mkdir(parents=True, exist_ok=False)
    for cache, layers, kv_size in (
        ("base", range(8), 8192),
        ("swa", range(40), 1536),
    ):
        cells = ["cache\tstream\thead\tkv_size\tv_trans\tposition\tcell\n"]
        for pos in range(512):
            cells.append(f"{cache}\t0\t{head}\t{kv_size}\t0\t{pos}\t{pos}\n")
        (d / f"{cache}.cells.tsv").write_text("".join(cells), encoding="utf-8")

        manifest = ["cache\tlayer\tkind\ttype\trow_bytes\trows\n"]
        for layer in layers:
            for kind in ("K", "V"):
                manifest.append(f"{cache}\t{layer}\t{kind}\tf16\t2\t512\n")
                payload = bytes([(layer * 7 + (0 if kind == "K" else 3)) & 0xFF, 0]) * 512
                (d / f"{cache}.layer-{layer}.{kind}.bin").write_bytes(payload)
        (d / f"{cache}.manifest.tsv").write_text("".join(manifest), encoding="utf-8")


def run_analyzer(proj: Path, newkv: Path, histkv: Path, out: Path):
    cp = subprocess.run(
        [
            sys.executable,
            str(ANALYZER),
            "--projection-root", str(proj),
            "--instrumented-kv-root", str(newkv),
            "--historical-kv-root", str(histkv),
            "--out", str(out),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    terminal = json.loads((out / "terminal.json").read_text(encoding="utf-8"))
    return cp, terminal


def main():
    if not ANALYZER.is_file():
        raise RuntimeError(f"analyzer missing: {ANALYZER}")

    with tempfile.TemporaryDirectory(prefix="relaylm-projection-origin-selftest-") as td:
        root = Path(td)
        proj = root / "projection"
        newkv = root / "new-kv"
        histkv = root / "historical-kv"
        proj.mkdir()
        newkv.mkdir()
        histkv.mkdir()

        write_projection_dump(proj, "W-p0-370-w371", range(0, 371))
        write_projection_dump(proj, "W-p371-878-w508", range(371, 879))

        def cold_projection_mutation(tensor, pos, vals):
            if tensor == "Kcur-0" and pos == 7:
                vals = list(vals)
                vals[0] += 0.125
            return vals

        write_projection_dump(
            proj,
            "C-p0-511-w512",
            range(0, 512),
            mutate=cold_projection_mutation,
        )

        write_kv_dump(newkv, "W-P512", head=123)
        write_kv_dump(newkv, "C-P512", head=456)
        # Head is deliberately allowed to differ; canonical mapping/payload does not.
        write_kv_dump(histkv, "WR-P512", head=879)
        write_kv_dump(histkv, "C-P512", head=512)

        cp1, term1 = run_analyzer(proj, newkv, histkv, root / "out-origin")
        if cp1.returncode != 0:
            raise RuntimeError(f"origin case failed: rc={cp1.returncode}: {cp1.stderr}")
        if term1["primary_classification"] != "LAYER0_PROJECTION_NUMERICAL_ORIGIN_OBSERVED":
            raise RuntimeError(f"unexpected origin classification: {term1['primary_classification']}")
        if not term1["projection"]["attn_norm-0"]["all"]["bit_exact_equal"]:
            raise RuntimeError("pre-projection synthetic control unexpectedly differs")
        if term1["projection"]["Kcur-0"]["all"]["differing_elements"] != 1:
            raise RuntimeError("synthetic K projection difference was not isolated")

        # Integrity failure must dominate any projection observation.
        damaged = newkv / "W-P512" / "swa.layer-0.K.bin"
        raw = bytearray(damaged.read_bytes())
        raw[0] ^= 1
        damaged.write_bytes(raw)

        cp2, term2 = run_analyzer(proj, newkv, histkv, root / "out-perturbed")
        if cp2.returncode != 2:
            raise RuntimeError(f"integrity case rc={cp2.returncode}, expected 2")
        if term2["primary_classification"] != "INSTRUMENTATION_PERTURBED_SUBJECT":
            raise RuntimeError(f"unexpected integrity classification: {term2['primary_classification']}")
        if term2["projection"] is not None:
            raise RuntimeError("projection result must not be interpreted after integrity failure")

    print("LAYER0_PROJECTION_ORIGIN_POSTHOC_SELFTEST_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

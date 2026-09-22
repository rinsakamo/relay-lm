#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import struct
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-kv-numerical-posthoc.py"
spec = importlib.util.spec_from_file_location("kvnum", TARGET)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def write_dump(root: Path, delta: bool):
    root.mkdir()
    for cache, kv_size in (("base", 8192), ("swa", 1536)):
        (root / f"{cache}.cells.tsv").write_text(
            "cache\tstream\thead\tkv_size\tv_trans\tposition\tcell\n"
            + "".join(f"{cache}\t0\t0\t{kv_size}\t0\t{i}\t{i}\n" for i in range(2)),
            encoding="utf-8",
        )
    (root / "base.manifest.tsv").write_text(
        "cache\tlayer\tkind\ttype\trow_bytes\trows\n"
        "base\t8\tK\tf16\t4\t2\n"
        "base\t8\tV\tf32\t8\t2\n",
        encoding="utf-8",
    )
    (root / "swa.manifest.tsv").write_text(
        "cache\tlayer\tkind\ttype\trow_bytes\trows\n"
        "swa\t0\tK\tq8_0\t4\t2\n"
        "swa\t0\tV\tbf16\t4\t2\n",
        encoding="utf-8",
    )
    f16 = [1.0, 2.0, 3.0, 4.0]
    q = bytearray(b"abcdefgh")
    if delta:
        f16[2] = 3.001953125
        q[3] ^= 1
    (root / "base.layer-8.K.bin").write_bytes(struct.pack("<4e", *f16))
    (root / "base.layer-8.V.bin").write_bytes(struct.pack("<4f", 1.0, 2.0, 3.0, 4.0))
    (root / "swa.layer-0.K.bin").write_bytes(q)
    (root / "swa.layer-0.V.bin").write_bytes(struct.pack("<4H", 0x3F80, 0x4000, 0x4040, 0x4080))


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        a, b = root / "a", root / "b"
        write_dump(a, False)
        write_dump(b, True)
        report = mod.analyze(a, b)
        assert report["classification"] == "KV_BYTE_POSTHOC_COMPLETE_NUMERIC_PARTIAL"
        assert report["file_count"] == 4
        assert report["differing_file_count"] == 2
        assert report["numeric_unsupported_types"] == ["q8_0"]
        f16 = next(x for x in report["files"] if x["file"] == "base.layer-8.K.bin")
        assert f16["differing_rows"] == 1
        assert f16["first_differing_position"] == 1
        assert f16["numeric"]["numeric_status"] == "DECODED"
        assert f16["numeric"]["differing_elements"] == 1
        q8 = next(x for x in report["files"] if x["file"] == "swa.layer-0.K.bin")
        assert q8["differing_bytes"] == 1
        assert q8["numeric"]["numeric_status"] == "UNSUPPORTED_TYPE"
        print("KV_NUMERICAL_ANALYZER_SELFTEST_PASS")


if __name__ == "__main__":
    main()

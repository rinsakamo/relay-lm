#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent
TARGET = HERE / "e2d2c0d6-gemma4-canonical-kv-directory-digest.py"


def load_module():
    spec = importlib.util.spec_from_file_location("kv_digest", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load digest module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_fixture(root: Path):
    root.mkdir(parents=True, exist_ok=False)
    for cache, layers, kv_size in (
        ("base", range(8), 8192),
        ("swa", range(40), 1536),
    ):
        cells = ["cache\tstream\thead\tkv_size\tv_trans\tposition\tcell\n"]
        for pos in range(512):
            cells.append(f"{cache}\t0\t123\t{kv_size}\t0\t{pos}\t{pos}\n")
        (root / f"{cache}.cells.tsv").write_text("".join(cells), encoding="utf-8")

        manifest = ["cache\tlayer\tkind\ttype\trow_bytes\trows\n"]
        for layer in layers:
            for kind in ("K", "V"):
                manifest.append(f"{cache}\t{layer}\t{kind}\tf16\t2\t512\n")
                byte0 = (layer * 11 + (0 if kind == "K" else 5)) & 0xFF
                (root / f"{cache}.layer-{layer}.{kind}.bin").write_bytes(
                    bytes([byte0, 0]) * 512
                )
        (root / f"{cache}.manifest.tsv").write_text("".join(manifest), encoding="utf-8")


def main():
    mod = load_module()
    with tempfile.TemporaryDirectory(prefix="relaylm-kv-digest-selftest-") as td:
        root = Path(td) / "kv"
        write_fixture(root)

        a = mod.digest_directory(root)
        b = mod.digest_directory(root)
        if a["classification"] != "CANONICAL_KV_DIRECTORY_DIGEST_COMPLETE":
            raise RuntimeError("unexpected classification")
        if a["directory_sha256"] != b["directory_sha256"]:
            raise RuntimeError("digest is not deterministic")
        if a["file_count"] != 100 or a["payload_count"] != 96:
            raise RuntimeError("unexpected canonical file counts")

        target = root / "swa.layer-0.K.bin"
        raw = bytearray(target.read_bytes())
        raw[0] ^= 1
        target.write_bytes(raw)
        c = mod.digest_directory(root)
        if c["directory_sha256"] == a["directory_sha256"]:
            raise RuntimeError("payload mutation did not change directory digest")

        extra = root / "unexpected.txt"
        extra.write_text("x", encoding="utf-8")
        rejected = False
        try:
            mod.digest_directory(root)
        except RuntimeError:
            rejected = True
        if not rejected:
            raise RuntimeError("unexpected file was not rejected")

    print(json.dumps({
        "status": "CANONICAL_KV_DIRECTORY_DIGEST_SELFTEST_PASS",
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

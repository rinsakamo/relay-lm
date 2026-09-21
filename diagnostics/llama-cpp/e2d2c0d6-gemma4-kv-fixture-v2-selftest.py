#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "e2d2c0d6-gemma4-kv-fixture-v2-corpus.py"
MATERIALIZE = HERE / "e2d2c0d6-gemma4-kv-fixture-v2-materialize.py"
ADMISSION = HERE / "e2d2c0d6-gemma4-kv-fixture-v2-admission.py"


def main():
    errors = []
    with tempfile.TemporaryDirectory(prefix="relaylm-kv-fixture-v2-selftest.") as td:
        root = Path(td)
        corpus = root / "source-corpus.txt"
        tokenizer_request = root / "tokenizer-request.json"
        tokenizer_response = root / "tokenizer-response.json"
        fixture_dir = root / "fixture"
        admission_out = root / "admission.json"

        generated = subprocess.run(
            [
                sys.executable,
                str(CORPUS),
                "--out",
                str(corpus),
                "--request-out",
                str(tokenizer_request),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if generated.returncode != 0:
            errors.append(f"corpus generator failed: rc={generated.returncode}")

        # Purely synthetic token pool for contract testing. No model/server call.
        tokenizer_response.write_text(
            json.dumps({"tokens": list(range(10000))}, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

        materialize = subprocess.run(
            [
                sys.executable,
                str(MATERIALIZE),
                "--corpus",
                str(corpus),
                "--tokenizer-request",
                str(tokenizer_request),
                "--tokenizer-response",
                str(tokenizer_response),
                "--out-dir",
                str(fixture_dir),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if materialize.returncode != 0:
            errors.append(f"materializer failed: rc={materialize.returncode}")

        if not errors:
            admitted = subprocess.run(
                [
                    sys.executable,
                    str(ADMISSION),
                    "--fixture-dir",
                    str(fixture_dir),
                    "--out",
                    str(admission_out),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if admitted.returncode != 0:
                errors.append(f"admission failed: rc={admitted.returncode}")

        if not errors:
            manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))
            admission = json.loads(admission_out.read_text(encoding="utf-8"))
            geometry = manifest.get("geometry", {})
            if geometry.get("warm_len") != 883:
                errors.append("warm_len contract failed")
            if geometry.get("target_len") != 2927:
                errors.append("target_len contract failed")
            if geometry.get("lcp") != 865:
                errors.append("LCP contract failed")
            if admission.get("status") != "LOGICAL_PREFIX_FIXTURE_V2_ADMISSION_PASS":
                errors.append("admission terminal mismatch")

            l1 = json.loads((fixture_dir / "L1.request.json").read_text(encoding="utf-8"))
            lc = json.loads((fixture_dir / "LC.request.json").read_text(encoding="utf-8"))
            l1_without = dict(l1)
            lc_without = dict(lc)
            l1_without.pop("cache_prompt", None)
            lc_without.pop("cache_prompt", None)
            if l1_without != lc_without:
                errors.append("L1/LC differ by more than cache_prompt")

    out = {
        "status": (
            "LOGICAL_PREFIX_FIXTURE_V2_SELFTEST_PASS"
            if not errors
            else "LOGICAL_PREFIX_FIXTURE_V2_SELFTEST_FAIL"
        ),
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

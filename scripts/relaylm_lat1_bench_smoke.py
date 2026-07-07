"""LAT-1 bench smoke: generate -> bench -> output schema, end to end.

Runs the full LAT-1 offline bench pipeline at a minimal size (N=20) inside a
temporary directory so it completes locally in a few seconds, and verifies
the bench tooling's fail-closed behavior against non-empty and symlinked
store directories.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

GENERATOR = REPO_ROOT / "scripts" / "relaylm_lat1_bench_store_generator.py"
BENCH = REPO_ROOT / "scripts" / "relaylm_lat1_retrieval_bench.py"

_EXPECTED_RESULT_KEYS = {
    "store_size",
    "query_count",
    "repeat",
    "p50_ms",
    "p95_ms",
    "avg_selected_count",
}


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )


def check_generate_bench_roundtrip() -> None:
    bench_root = REPO_ROOT / "runtime" / "bench"
    bench_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=bench_root) as td:
        stores_root = Path(td) / "stores"
        results_root = Path(td) / "results"

        generate = _run(
            [
                str(GENERATOR),
                "--sizes",
                "20",
                "--out-root",
                str(stores_root),
                "--seed",
                "1",
            ]
        )
        require(generate.returncode == 0, generate.stdout + generate.stderr)
        store_dir = stores_root / "size_20"
        require(store_dir.is_dir(), generate.stdout)
        mem_root = store_dir / "memory" / "mem"
        require((mem_root / "index.md").is_file(), mem_root)
        require((mem_root / "log.md").is_file(), mem_root)
        page_files = [
            *(mem_root / "primary").rglob("*.md"),
            *(mem_root / "secondary").rglob("*.md"),
        ]
        require(len(page_files) == 20, page_files)
        print("ok store generator produces 20 synthetic pages under runtime/")

        bench = _run(
            [
                str(BENCH),
                "--stores-root",
                str(stores_root),
                "--out-root",
                str(results_root),
                "--repeat",
                "1",
            ]
        )
        require(bench.returncode == 0, bench.stdout + bench.stderr)
        result_path = results_root / "lat1_retrieval_bench_results.json"
        require(result_path.is_file(), bench.stdout)
        results = json.loads(result_path.read_text(encoding="utf-8"))
        require(isinstance(results, list) and len(results) == 1, results)
        entry = results[0]
        require(set(entry.keys()) == _EXPECTED_RESULT_KEYS, entry)
        require(entry["store_size"] == 20, entry)
        require(entry["query_count"] == 20, entry)
        require(entry["repeat"] == 1, entry)
        require(isinstance(entry["p50_ms"], (int, float)) and entry["p50_ms"] >= 0, entry)
        require(isinstance(entry["p95_ms"], (int, float)) and entry["p95_ms"] >= 0, entry)
        print("ok retrieval bench completes locally in seconds and emits the documented JSON schema")

        rerun = _run(
            [
                str(GENERATOR),
                "--sizes",
                "20",
                "--out-root",
                str(stores_root),
                "--seed",
                "1",
            ]
        )
        require(rerun.returncode != 0, rerun.stdout + rerun.stderr)
        require("fail-closed" in (rerun.stdout + rerun.stderr), rerun.stdout + rerun.stderr)
        print("ok store generator refuses to overwrite an existing non-empty store directory")


def check_bench_rejects_stores_root_outside_bench_dir() -> None:
    bench_root = REPO_ROOT / "runtime" / "bench"
    bench_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=bench_root) as td:
        results_root = Path(td) / "results"
        with tempfile.TemporaryDirectory() as outside_td:
            outside_stores_root = Path(outside_td) / "stores"
            (outside_stores_root / "size_20").mkdir(parents=True)

            bench = _run(
                [
                    str(BENCH),
                    "--stores-root",
                    str(outside_stores_root),
                    "--out-root",
                    str(results_root),
                    "--repeat",
                    "1",
                ]
            )
            require(bench.returncode != 0, bench.stdout + bench.stderr)
            combined = bench.stdout + bench.stderr
            require(
                "--stores-root" in combined
                and "runtime/bench" in combined
                and "LAT-1 bench directory" in combined,
                combined,
            )
            require(not results_root.exists(), results_root)
            print("ok retrieval bench refuses --stores-root outside runtime/bench/ (fail-closed)")


def check_generator_rejects_symlinked_store_target() -> None:
    bench_root = REPO_ROOT / "runtime" / "bench"
    bench_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=bench_root) as td:
        stores_root = Path(td) / "stores"
        stores_root.mkdir()
        link_target = Path(td) / "target"
        link_target.mkdir()
        symlink_path = stores_root / "size_20"
        try:
            symlink_path.symlink_to(link_target, target_is_directory=True)
        except (NotImplementedError, OSError):
            print("ok symlink test skipped: platform does not allow directory symlink creation")
            return

        generate = _run(
            [
                str(GENERATOR),
                "--sizes",
                "20",
                "--out-root",
                str(stores_root),
                "--seed",
                "1",
            ]
        )
        require(generate.returncode != 0, generate.stdout + generate.stderr)
        combined = generate.stdout + generate.stderr
        require("symlinked bench store directory" in combined and "fail-closed" in combined, combined)
        require(not (link_target / "memory").exists(), link_target)
        print("ok store generator refuses symlinked size_<N> targets")


def check_bench_rejects_symlinked_store_target() -> None:
    bench_root = REPO_ROOT / "runtime" / "bench"
    bench_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=bench_root) as td:
        stores_root = Path(td) / "stores"
        results_root = Path(td) / "results"
        stores_root.mkdir()
        link_target = Path(td) / "target"
        link_target.mkdir()
        symlink_path = stores_root / "size_20"
        try:
            symlink_path.symlink_to(link_target, target_is_directory=True)
        except (NotImplementedError, OSError):
            print("ok symlink test skipped: platform does not allow directory symlink creation")
            return

        bench = _run(
            [
                str(BENCH),
                "--stores-root",
                str(stores_root),
                "--out-root",
                str(results_root),
                "--sizes",
                "20",
                "--repeat",
                "1",
            ]
        )
        require(bench.returncode != 0, bench.stdout + bench.stderr)
        combined = bench.stdout + bench.stderr
        require("symlinked bench store directory" in combined and "fail-closed" in combined, combined)
        require(not results_root.exists(), results_root)
        print("ok retrieval bench refuses symlinked size_<N> stores")


def main() -> int:
    check_generate_bench_roundtrip()
    check_bench_rejects_stores_root_outside_bench_dir()
    check_generator_rejects_symlinked_store_target()
    check_bench_rejects_symlinked_store_target()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
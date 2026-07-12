"""Queue/claim/lease semantics, concurrency, verify invariants, and the CLI."""

import concurrent.futures
import json
import subprocess
import sys
import time
from pathlib import Path

from mdsqlite_spike import bench, ops, verify

LAUNCHER = Path(__file__).resolve().parents[1] / "run_spike.py"


def _enqueue(conn, key, now):
    conn.execute(
        "INSERT INTO jobs(job_id, idempotency_key, kind, state, created_at, "
        "updated_at) VALUES(?, ?, 'test', 'pending', ?, ?)",
        (f"job_{key}", f"test:{key}", now, now),
    )
    conn.commit()


def test_claim_lease_and_expiry(env):
    conn = env.open_ops()
    _enqueue(conn, "a", env.now())
    epoch = 1000.0
    job = ops.claim_next(conn, "w1", env.now(), epoch, lease_seconds=30)
    assert job == "job_a"
    assert ops.claim_next(conn, "w2", env.now(), epoch + 10) is None
    reclaimed = ops.claim_next(conn, "w2", env.now(), epoch + 31)
    assert reclaimed == "job_a"
    row = conn.execute("SELECT claimed_by FROM jobs WHERE job_id = 'job_a'").fetchone()
    assert row["claimed_by"] == "w2"
    conn.close()


def test_concurrent_claims_hand_out_distinct_jobs(env):
    seed = env.open_ops()
    for i in range(20):
        _enqueue(seed, f"c{i:02d}", env.now())
    seed.close()
    ops.reset_lock_stats()

    def worker(name):
        conn = env.open_ops()
        got = []
        try:
            while True:
                job = ops.claim_next(conn, name, env.now(), time.time())
                if job is None:
                    return got
                got.append(job)
        finally:
            conn.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(worker, [f"w{i}" for i in range(4)]))
    claimed = [job for jobs in results for job in jobs]
    assert sorted(claimed) == sorted(set(claimed))
    assert len(claimed) == 20


def test_verify_reports_all_invariants(seeded_env):
    report = verify.run_verify(seeded_env)
    assert report["ok"], report
    assert set(report["invariants"]) == {
        "cache_integrity",
        "cache_matches_markdown",
        "markdown_render_roundtrip",
        "cache_rebuild_equivalence",
        "receipts_only_for_applied_jobs",
        "ops_db_holds_no_mem_content",
        "no_orphaned_intents",
        "tombstones_correspond_to_hidden_memory",
        "usage_history_is_operational_authority",
    }


def _cli(root, *args):
    proc = subprocess.run(
        [sys.executable, str(LAUNCHER), "--root", str(root), *args],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return json.loads(proc.stdout)


def test_cli_end_to_end(tmp_path):
    root = tmp_path / "cli-root"

    fixture = _cli(root, "init-fixture", "--pages", "2", "--blocks", "3")
    assert fixture == {"pages": 2, "blocks": 6, "seed": 1}

    built = _cli(root, "build-cache")
    assert built["inserted"] == 6

    hits = _cli(root, "search", "kw1x2")
    assert [h["block_id"] for h in hits["hits"]] == ["blk_p1b2"]
    assert hits["usage"]["blk_p1b2"]["usage_count"] == 1

    applied = _cli(
        root, "apply-candidate", "--candidate-id", "cli-1",
        "--page", "cli_notes.md", "--content", "cli formed memory clikw",
    )
    assert applied["outcome"] == "applied"

    found = _cli(root, "search", "clikw")
    assert len(found["hits"]) == 1

    forgotten = _cli(root, "forget", "--block-id", applied["block_id"])
    assert forgotten["outcome"] == "applied"
    assert _cli(root, "search", "clikw")["hits"] == []

    restored = _cli(root, "restore", "--block-id", applied["block_id"])
    assert restored["outcome"] == "applied"
    assert len(_cli(root, "search", "clikw")["hits"]) == 1

    drill = _cli(root, "simulate-failure", "--failpoint",
                 "after_replace_before_cache")
    assert drill["crashed"] is True
    assert drill["recovery"]["rolled_forward"]

    rebuilt = _cli(root, "rebuild-cache")
    assert rebuilt["rebuilt"] is True

    verified = _cli(root, "verify")
    assert verified["ok"] is True, verified


def test_benchmark_emits_machine_readable_results(env):
    report = bench.run_benchmark(env, pages=2, blocks_per_page=3, searches=5)
    json.dumps(report)
    assert report["fixture"] == {"pages": 2, "blocks": 6, "seed": 1}
    for key in (
        "compile_seconds", "incremental_update", "search_latency",
        "apply_latency", "rebuild_seconds", "contention", "recovery",
        "invariants",
    ):
        assert key in report
    assert report["invariants"]["ok"], report["invariants"]
    assert all(entry["pass"] for entry in report["recovery"].values()), (
        report["recovery"]
    )
    assert report["contention"]["jobs"] == sum(
        report["contention"]["claims_per_worker"]
    )

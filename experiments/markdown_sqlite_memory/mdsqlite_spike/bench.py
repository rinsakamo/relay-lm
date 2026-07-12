"""Benchmark and failure-drill harness; emits machine-readable JSON."""

from __future__ import annotations

import concurrent.futures
import json
import platform
import statistics
import threading
import time
import uuid
from datetime import datetime, timezone

from . import cache, mdstore, ops, search, slp, verify
from .fixtures import init_fixture
from .slp import Candidate, SpikeEnv


def _timed(fn) -> tuple[float, object]:
    start = time.perf_counter()
    result = fn()
    return time.perf_counter() - start, result


def _percentiles(samples: list[float]) -> dict:
    ordered = sorted(samples)
    return {
        "n": len(ordered),
        "mean_ms": statistics.fmean(ordered) * 1000,
        "p50_ms": ordered[len(ordered) // 2] * 1000,
        "p95_ms": ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))] * 1000,
        "max_ms": ordered[-1] * 1000,
    }


def _contention_drill(env: SpikeEnv, workers: int = 4, jobs_per_worker: int = 25) -> dict:
    """Concurrent enqueue+claim against operations.db to observe lock waits."""
    ops.reset_lock_stats()
    seed_conn = env.open_ops()
    now = env.now()
    with ops.immediate_txn(seed_conn):
        for i in range(workers * jobs_per_worker):
            seed_conn.execute(
                "INSERT INTO jobs(job_id, idempotency_key, kind, state, "
                "created_at, updated_at) VALUES(?, ?, 'contention-drill', "
                "'pending', ?, ?)",
                (f"drill_{uuid.uuid4().hex[:12]}", f"drill:{uuid.uuid4().hex}",
                 now, now),
            )
    seed_conn.close()

    barrier = threading.Barrier(workers)

    def worker(name: str) -> int:
        conn = env.open_ops()
        claimed = 0
        barrier.wait()
        try:
            while True:
                job_id = ops.claim_next(conn, name, env.now(), time.time())
                if job_id is None:
                    return claimed
                with ops.immediate_txn(conn):
                    conn.execute(
                        "UPDATE jobs SET state = 'applied', updated_at = ? "
                        "WHERE job_id = ?",
                        (env.now(), job_id),
                    )
                claimed += 1
        finally:
            conn.close()

    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        counts = list(pool.map(worker, [f"drill-worker-{i}" for i in range(workers)]))
    elapsed = time.perf_counter() - start
    stats = ops.get_lock_stats()
    conn = env.open_ops()
    conn.execute("DELETE FROM jobs WHERE kind = 'contention-drill'")
    conn.commit()
    conn.close()
    return {
        "workers": workers,
        "jobs": workers * jobs_per_worker,
        "claims_per_worker": counts,
        "elapsed_seconds": elapsed,
        "busy_retries": stats["busy_retries"],
        "busy_wait_seconds": stats["wait_seconds"],
        "txn_acquisitions": stats["acquisitions"],
        "txn_acquire_seconds": stats["acquire_seconds"],
        "max_txn_acquire_seconds": stats["max_acquire_seconds"],
    }


def _recovery_drill(env: SpikeEnv) -> dict:
    """Deterministic crash drill at each failpoint, then startup recovery."""
    results = {}
    for failpoint in slp.FAILPOINTS:
        candidate = Candidate(
            candidate_id=f"bench-recovery-{failpoint}",
            page="bench_recovery.md",
            content=f"recovery drill memory for failpoint {failpoint}",
        )
        env.failpoints.arm(failpoint)
        try:
            slp.apply_candidate(env, candidate)
            results[failpoint] = {"pass": False, "detail": "failpoint did not fire"}
            continue
        except slp.InjectedFailure:
            pass
        report = slp.startup(env)
        if failpoint == "before_replace":
            ok = bool(report["rolled_back"]) and not report["rolled_forward"]
            retry = slp.apply_candidate(env, candidate)
            ok = ok and retry.outcome == "applied"
        else:
            ok = bool(report["rolled_forward"]) and not report["conflicts"]
        results[failpoint] = {"pass": ok, "detail": report}
    return results


def run_benchmark(
    env: SpikeEnv, pages: int = 20, blocks_per_page: int = 25, searches: int = 50
) -> dict:
    fixture = init_fixture(env, pages=pages, blocks_per_page=blocks_per_page)

    conn = env.open_cache()
    compile_seconds, _ = _timed(
        lambda: cache.build_from_markdown(conn, env.pages_dir)
    )

    # Incremental update: touch one block on one page.
    rel_path = "topic_000.md"
    page_file = env.page_path(rel_path)
    text = page_file.read_text(encoding="utf-8")
    page = mdstore.parse_page(text, rel_path)
    page.blocks[0].content += " incremental-touch"
    page.blocks[0].revision += 1
    new_text = mdstore.render_page(page)
    mdstore.atomic_replace(page_file, new_text)
    incremental_seconds, stats = _timed(
        lambda: cache.refresh_page(conn, rel_path, new_text)
    )

    search_samples = []
    for i in range(searches):
        marker = f"kw{i % pages}x{i % blocks_per_page}"
        plan = search.plan_search(marker)
        seconds, hits = _timed(
            lambda p=plan: search.execute_search(conn, p, count_usage=False)
        )
        search_samples.append(seconds)
    conn.close()

    ops.reset_lock_stats()
    apply_samples = []
    for i in range(10):
        candidate = Candidate(
            candidate_id=f"bench-apply-{i}",
            page="bench_applies.md",
            content=f"benchmark applied memory number {i} token benchkw{i}",
            user_tags=("bench",),
        )
        seconds, result = _timed(lambda c=candidate: slp.apply_candidate(env, c))
        assert result.outcome == "applied", result
        apply_samples.append(seconds)
    apply_lock_stats = ops.get_lock_stats()

    def rebuild() -> None:
        for suffix in ("", "-wal", "-shm"):
            p = env.root / (env.cache_path.name + suffix)
            if p.exists():
                p.unlink()
        rebuilt = env.open_cache()
        cache.build_from_markdown(rebuilt, env.pages_dir)
        rebuilt.close()

    rebuild_seconds, _ = _timed(rebuild)

    contention = _contention_drill(env)
    recovery = _recovery_drill(env)
    invariants = verify.run_verify(env)

    return {
        "spike": "markdown_sqlite_memory",
        "experimental": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        },
        "fixture": fixture,
        "compile_seconds": compile_seconds,
        "incremental_update": {
            "seconds": incremental_seconds,
            "rows": {
                "inserted": stats.inserted,
                "updated": stats.updated,
                "deleted": stats.deleted,
                "unchanged": stats.unchanged,
            },
        },
        "search_latency": _percentiles(search_samples),
        "apply_latency": _percentiles(apply_samples),
        "apply_lock_stats": apply_lock_stats,
        "rebuild_seconds": rebuild_seconds,
        "contention": contention,
        "recovery": recovery,
        "invariants": invariants,
    }


def main_json(env: SpikeEnv, **kwargs) -> str:
    return json.dumps(run_benchmark(env, **kwargs), indent=2)

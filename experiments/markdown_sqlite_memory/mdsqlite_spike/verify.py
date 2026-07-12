"""Invariant verification for the spike; emits machine-readable results."""

from __future__ import annotations

from . import cache, mdstore, ops
from .slp import SpikeEnv


def _rebuild_equivalence(env: SpikeEnv) -> tuple[bool, str]:
    """Compare the live cache's canonical dump against a fresh rebuild."""
    live = env.open_cache()
    try:
        current = cache.canonical_dump(live)
    finally:
        live.close()
    scratch_path = env.root / "verify-rebuild.db"
    for suffix in ("", "-wal", "-shm"):
        p = scratch_path.parent / (scratch_path.name + suffix)
        if p.exists():
            p.unlink()
    scratch = cache.open_cache(scratch_path)
    try:
        cache.build_from_markdown(scratch, env.pages_dir)
        rebuilt = cache.canonical_dump(scratch)
    finally:
        scratch.close()
        for suffix in ("", "-wal", "-shm"):
            p = scratch_path.parent / (scratch_path.name + suffix)
            if p.exists():
                p.unlink()
    if current == rebuilt:
        return True, "canonical dump identical after rebuild from Markdown"
    return False, (
        f"canonical dump mismatch: live has {len(current)} blocks, "
        f"rebuild has {len(rebuilt)}"
    )


def run_verify(env: SpikeEnv) -> dict:
    """Run every invariant check; returns {'ok': bool, 'invariants': {...}}."""
    invariants: dict[str, dict] = {}

    def record(name: str, ok: bool, detail: str) -> None:
        invariants[name] = {"pass": bool(ok), "detail": detail}

    # 1. Cache integrity + no stale page projections.
    try:
        conn = env.open_cache()
        problems = cache.integrity_check(conn)
        record(
            "cache_integrity",
            not problems,
            "; ".join(problems) or "PRAGMA integrity_check and FTS check ok",
        )
        stale = cache.stale_pages(conn, env.pages_dir)
        record(
            "cache_matches_markdown",
            not stale,
            f"stale pages: {stale}" if stale else "all page digests match Markdown",
        )
        conn.close()
    except (cache.CacheCorruptError, cache.SchemaVersionError) as exc:
        record("cache_integrity", False, str(exc))
        record("cache_matches_markdown", False, "skipped: cache unreadable")

    # 2. Markdown reproducibility: parse -> render round-trips every page.
    bad_pages = []
    for rel_path, text in mdstore.load_pages(env.pages_dir).items():
        page = mdstore.parse_page(text, rel_path)
        if mdstore.render_page(page) != text:
            bad_pages.append(rel_path)
    record(
        "markdown_render_roundtrip",
        not bad_pages,
        f"non-roundtripping pages: {bad_pages}" if bad_pages
        else "render(parse(page)) == page for all pages",
    )

    # 3. Cache is rebuildable losslessly for canonical queries.
    try:
        ok, detail = _rebuild_equivalence(env)
    except Exception as exc:  # rebuild must never crash verification
        ok, detail = False, f"rebuild failed: {exc}"
    record("cache_rebuild_equivalence", ok, detail)

    ops_conn = ops.connect(env.ops_path)
    try:
        # 4. Pending/applying work is never presented as committed MEM:
        #    only applied jobs may hold receipts.
        row = ops_conn.execute(
            "SELECT COUNT(*) AS n FROM apply_receipts r JOIN jobs j "
            "ON j.job_id = r.job_id WHERE j.state != 'applied'"
        ).fetchone()
        record(
            "receipts_only_for_applied_jobs",
            row["n"] == 0,
            f"{row['n']} receipts attached to non-applied jobs",
        )
        # 5. No committed MEM content authority in operations.db: receipts
        #    carry digests and block IDs only. Structural check that no
        #    ops table has a MEM content column.
        content_cols = []
        for table in ("apply_receipts", "apply_intents", "tombstones", "jobs"):
            for col in ops_conn.execute(f"PRAGMA table_info({table})"):
                if col["name"] in ("content", "normalized_text"):
                    content_cols.append(f"{table}.{col['name']}")
        record(
            "ops_db_holds_no_mem_content",
            not content_cols,
            f"content columns found: {content_cols}" if content_cols
            else "receipts/intents/tombstones reference digests and IDs only",
        )
        # 6. No lingering intents without a live applying job.
        row = ops_conn.execute(
            "SELECT COUNT(*) AS n FROM apply_intents i JOIN jobs j "
            "ON j.job_id = i.job_id WHERE j.state NOT IN ('applying')"
        ).fetchone()
        record(
            "no_orphaned_intents",
            row["n"] == 0,
            f"{row['n']} intents attached to non-applying jobs",
        )
        # 7. Tombstoned content keys are absent from active cache blocks.
        conn = env.open_cache()
        keys = [
            r["content_key"]
            for r in ops_conn.execute("SELECT content_key FROM tombstones")
        ]
        leaked = []
        for key in keys:
            hit = conn.execute(
                "SELECT block_id FROM blocks WHERE content_key = ? "
                "AND status = 'active' LIMIT 1",
                (key,),
            ).fetchone()
            if hit is not None:
                leaked.append(hit["block_id"])
        conn.close()
        record(
            "tombstoned_content_not_active",
            not leaked,
            f"active blocks matching tombstones: {leaked}" if leaked
            else f"{len(keys)} tombstone keys, none active in cache",
        )
    finally:
        ops_conn.close()

    return {
        "ok": all(entry["pass"] for entry in invariants.values()),
        "invariants": invariants,
    }

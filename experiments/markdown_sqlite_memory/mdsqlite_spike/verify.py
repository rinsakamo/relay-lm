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

    try:
        ok, detail = _rebuild_equivalence(env)
    except Exception as exc:
        ok, detail = False, f"rebuild failed: {exc}"
    record("cache_rebuild_equivalence", ok, detail)

    ops_conn = ops.connect(env.ops_path)
    try:
        row = ops_conn.execute(
            "SELECT COUNT(*) AS n FROM apply_receipts r JOIN jobs j "
            "ON j.job_id = r.job_id WHERE j.state != 'applied'"
        ).fetchone()
        record(
            "receipts_only_for_applied_jobs",
            row["n"] == 0,
            f"{row['n']} receipts attached to non-applied jobs",
        )

        content_cols = []
        for table in (
            "apply_receipts",
            "apply_intents",
            "tombstones",
            "jobs",
            "memory_usage_events",
        ):
            for col in ops_conn.execute(f"PRAGMA table_info({table})"):
                if col["name"] in ("content", "normalized_text"):
                    content_cols.append(f"{table}.{col['name']}")
        record(
            "ops_db_holds_no_mem_content",
            not content_cols,
            f"content columns found: {content_cols}" if content_cols
            else "operational records reference digests, IDs, and content-free events only",
        )

        row = ops_conn.execute(
            "SELECT COUNT(*) AS n FROM apply_intents i JOIN jobs j "
            "ON j.job_id = i.job_id WHERE j.state NOT IN ('applying')"
        ).fetchone()
        record(
            "no_orphaned_intents",
            row["n"] == 0,
            f"{row['n']} intents attached to non-applying jobs",
        )

        cache_conn = env.open_cache()
        tombstones = ops_conn.execute(
            "SELECT block_id, content_key FROM tombstones ORDER BY tombstone_id"
        ).fetchall()
        active_leaks = []
        non_hidden = []
        for tombstone in tombstones:
            active = cache_conn.execute(
                "SELECT block_id FROM blocks WHERE content_key = ? "
                "AND status = 'active' LIMIT 1",
                (tombstone["content_key"],),
            ).fetchone()
            if active is not None:
                active_leaks.append(active["block_id"])
            current = cache_conn.execute(
                "SELECT status FROM blocks WHERE block_id = ?",
                (tombstone["block_id"],),
            ).fetchone()
            if current is None or current["status"] != "hidden":
                non_hidden.append(tombstone["block_id"])
        cache_conn.close()
        record(
            "tombstones_correspond_to_hidden_memory",
            not active_leaks and not non_hidden,
            (
                f"active matches={active_leaks}; non-hidden tombstone blocks={non_hidden}"
                if active_leaks or non_hidden
                else f"{len(tombstones)} tombstones, all corresponding memories hidden"
            ),
        )

        usage_columns = {
            row["name"]
            for row in ops_conn.execute("PRAGMA table_info(memory_usage_events)")
        }
        expected_usage_columns = {
            "event_id", "block_id", "event_kind", "query_digest", "occurred_at"
        }
        record(
            "usage_history_is_operational_authority",
            expected_usage_columns <= usage_columns,
            (
                "durable content-free usage-event table present in operations.db"
                if expected_usage_columns <= usage_columns
                else f"missing usage columns: {sorted(expected_usage_columns - usage_columns)}"
            ),
        )
    finally:
        ops_conn.close()

    return {
        "ok": all(entry["pass"] for entry in invariants.values()),
        "invariants": invariants,
    }

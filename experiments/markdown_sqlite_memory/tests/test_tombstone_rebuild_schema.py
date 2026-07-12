"""Flows I (lifecycle/tombstones), J (cache recovery), K (versioning)."""

import pytest

from mdsqlite_spike import cache, mdstore, ops, search, slp
from mdsqlite_spike.slp import Candidate


def test_flow_i_forget_hides_and_tombstone_blocks_reformation(seeded_env):
    cand = Candidate(
        candidate_id="tomb-1",
        page="notes.md",
        content="The User Prefers   Dark Roast Coffee.",
    )
    applied = slp.apply_candidate(seeded_env, cand)
    assert applied.outcome == "applied"

    conn = seeded_env.open_cache()
    assert search.execute_search(conn, search.plan_search("roast"))
    conn.close()

    result = slp.forget(seeded_env, applied.block_id, reason="user_request")
    assert result.outcome == "applied"

    # Forget is a canonical hidden revision, not Purge/physical deletion.
    page = mdstore.parse_page(
        seeded_env.page_path("notes.md").read_text(), "notes.md"
    )
    hidden = page.get(applied.block_id)
    assert hidden is not None
    assert hidden.status == "hidden"
    assert hidden.revision == 2

    conn = seeded_env.open_cache()
    assert not search.execute_search(conn, search.plan_search("roast"))
    hidden_hits = search.execute_search(
        conn, search.plan_search("roast", status="hidden"), count_usage=False
    )
    assert [hit.block_id for hit in hidden_hits] == [applied.block_id]
    conn.close()

    # Tombstones survive restart and block equivalent automatic re-formation.
    slp.startup(seeded_env)
    equivalent = Candidate(
        candidate_id="tomb-2",
        page="notes.md",
        content="the user prefers dark roast coffee.",
    )
    blocked = slp.apply_candidate(seeded_env, equivalent)
    assert blocked.outcome == "blocked_tombstone"

    ops_conn = seeded_env.open_ops()
    job = ops_conn.execute(
        "SELECT state FROM jobs WHERE idempotency_key = 'candidate:tomb-2'"
    ).fetchone()
    assert job["state"] == "blocked_tombstone"
    assert ops_conn.execute(
        "SELECT COUNT(*) FROM tombstones WHERE block_id = ?",
        (applied.block_id,),
    ).fetchone()[0] == 1
    ops_conn.close()


def test_restore_reactivates_markdown_and_clears_tombstone(seeded_env):
    applied = slp.apply_candidate(
        seeded_env,
        Candidate(candidate_id="restore-1", page="notes.md", content="restore me"),
    )
    forgotten = slp.forget(seeded_env, applied.block_id)
    assert forgotten.outcome == "applied"

    restored = slp.restore(seeded_env, applied.block_id)
    assert restored.outcome == "applied"

    page = mdstore.parse_page(
        seeded_env.page_path("notes.md").read_text(), "notes.md"
    )
    current = page.get(applied.block_id)
    assert current is not None
    assert current.status == "active"
    assert current.revision == 3

    ops_conn = seeded_env.open_ops()
    assert ops_conn.execute(
        "SELECT COUNT(*) FROM tombstones WHERE block_id = ?",
        (applied.block_id,),
    ).fetchone()[0] == 0
    ops_conn.close()

    conn = seeded_env.open_cache()
    assert [
        hit.block_id for hit in search.execute_search(conn, search.plan_search("restore"))
    ] == [applied.block_id]
    conn.close()

    # Equivalent content is no longer tombstone-blocked, but active duplicate
    # detection still prevents forming a second copy.
    equivalent = slp.apply_candidate(
        seeded_env,
        Candidate(candidate_id="restore-equivalent", page="notes.md", content="restore me"),
    )
    assert equivalent.outcome == "duplicate"


def test_forget_restore_cycles_are_revision_scoped_and_idempotent(seeded_env):
    applied = slp.apply_candidate(
        seeded_env,
        Candidate(candidate_id="cycle-1", page="notes.md", content="cycle note"),
    )
    first = slp.forget(seeded_env, applied.block_id)
    repeated_hidden = slp.forget(seeded_env, applied.block_id)
    restore = slp.restore(seeded_env, applied.block_id)
    second = slp.forget(seeded_env, applied.block_id)

    assert first.outcome == "applied"
    assert repeated_hidden.outcome == "duplicate"
    assert restore.outcome == "applied"
    assert second.outcome == "applied"

    page = mdstore.parse_page(
        seeded_env.page_path("notes.md").read_text(), "notes.md"
    )
    current = page.get(applied.block_id)
    assert current is not None
    assert current.status == "hidden"
    assert current.revision == 4


def test_flow_j_cache_delete_and_rebuild_equivalence(seeded_env):
    conn = seeded_env.open_cache()
    before = cache.canonical_dump(conn)
    conn.close()
    assert before

    for suffix in ("", "-wal", "-shm"):
        p = seeded_env.root / (seeded_env.cache_path.name + suffix)
        if p.exists():
            p.unlink()

    report = slp.startup(seeded_env)
    assert report["cache_rebuilt"] is True

    conn = seeded_env.open_cache()
    after = cache.canonical_dump(conn)
    hits = search.execute_search(conn, search.plan_search("kw2x1"))
    conn.close()
    assert after == before
    assert [h.block_id for h in hits] == ["blk_p2b1"]


def test_flow_j_cache_corruption_detected_and_rebuilt(seeded_env):
    conn = seeded_env.open_cache()
    before = cache.canonical_dump(conn)
    conn.close()

    for suffix in ("-wal", "-shm"):
        p = seeded_env.root / (seeded_env.cache_path.name + suffix)
        if p.exists():
            p.unlink()
    seeded_env.cache_path.write_bytes(b"this is not a sqlite database at all")

    report = slp.startup(seeded_env)
    assert report["cache_rebuilt"] is True
    conn = seeded_env.open_cache()
    assert cache.canonical_dump(conn) == before
    conn.close()


def test_flow_k_newer_cache_schema_rejected_not_downgraded(seeded_env):
    conn = seeded_env.open_cache()
    conn.execute(
        "UPDATE schema_meta SET value = ? WHERE key = 'schema_version'",
        (str(cache.CACHE_SCHEMA_VERSION + 1),),
    )
    conn.commit()
    conn.close()
    with pytest.raises(cache.SchemaVersionError):
        seeded_env.open_cache()
    with pytest.raises(cache.SchemaVersionError):
        slp.startup(seeded_env)


def test_flow_k_controlled_cache_migration_v1_to_v2(env):
    db_path = env.cache_path
    env.cache_path.parent.mkdir(parents=True, exist_ok=True)
    conn = cache._connect(db_path)
    cache._create_schema(conn, version=1)
    conn.execute(
        "INSERT INTO pages(path, title, digest) VALUES('p.md', 'P', 'd')"
    )
    conn.execute(
        "INSERT INTO blocks(block_id, page_path, status, kind, revision, updated, "
        "content, normalized_text, content_key, subject_key, block_digest) "
        "VALUES('blk_m1', 'p.md', 'active', 'fact', 1, '', 'c', 'c', 'k', 's', 'bd')"
    )
    conn.commit()
    conn.close()

    migrated = cache.open_cache(db_path)
    version = migrated.execute(
        "SELECT value FROM schema_meta WHERE key = 'schema_version'"
    ).fetchone()[0]
    assert int(version) == cache.CACHE_SCHEMA_VERSION
    migrated.close()


def test_flow_k_integrity_check_reports_healthy(seeded_env):
    conn = seeded_env.open_cache()
    assert cache.integrity_check(conn) == []
    conn.close()


def test_ops_schema_v1_migrates_to_durable_usage_v2(tmp_path):
    db_path = tmp_path / "operations.db"
    conn = ops.connect(db_path)
    conn.execute("DROP TABLE memory_usage_events")
    conn.execute("DROP INDEX IF EXISTS idx_memory_usage_block_time")
    conn.execute(
        "UPDATE schema_meta SET value = '1' WHERE key = 'schema_version'"
    )
    conn.commit()
    conn.close()

    migrated = ops.connect(db_path)
    assert int(
        migrated.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        ).fetchone()[0]
    ) == ops.OPS_SCHEMA_VERSION
    assert migrated.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='memory_usage_events'"
    ).fetchone() is not None
    migrated.close()


def test_ops_schema_newer_version_rejected(seeded_env):
    conn = seeded_env.open_ops()
    conn.execute(
        "UPDATE schema_meta SET value = ? WHERE key = 'schema_version'",
        (str(ops.OPS_SCHEMA_VERSION + 1),),
    )
    conn.commit()
    conn.close()
    with pytest.raises(ops.OpsSchemaVersionError):
        seeded_env.open_ops()

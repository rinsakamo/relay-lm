"""Flows I (tombstones), J (cache loss/corruption), K (integrity/versioning)."""

import pytest

from mdsqlite_spike import cache, mdstore, search, slp
from mdsqlite_spike.slp import Candidate


def test_flow_i_forget_and_tombstone_block_reformation(seeded_env):
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

    # Gone from Markdown and from normal search immediately.
    page = mdstore.parse_page(seeded_env.page_path("notes.md").read_text())
    assert page.get(applied.block_id) is None
    conn = seeded_env.open_cache()
    assert not search.execute_search(conn, search.plan_search("roast"))
    conn.close()

    # Tombstones survive restart: recovery over fresh connections, then an
    # equivalent candidate (different id, normalized-equal content) is
    # blocked from automatic re-formation.
    slp.startup(seeded_env)
    equivalent = Candidate(
        candidate_id="tomb-2",
        page="notes.md",
        content="the user prefers dark roast coffee.",
    )
    blocked = slp.apply_candidate(seeded_env, equivalent)
    assert blocked.outcome == "blocked_tombstone"
    page = mdstore.parse_page(seeded_env.page_path("notes.md").read_text())
    assert not page.blocks

    ops_conn = seeded_env.open_ops()
    job = ops_conn.execute(
        "SELECT state FROM jobs WHERE idempotency_key = 'candidate:tomb-2'"
    ).fetchone()
    assert job["state"] == "blocked_tombstone"
    ops_conn.close()


def test_forget_is_idempotent(seeded_env):
    applied = slp.apply_candidate(
        seeded_env,
        Candidate(candidate_id="f-1", page="notes.md", content="ephemeral note"),
    )
    first = slp.forget(seeded_env, applied.block_id)
    second = slp.forget(seeded_env, applied.block_id)
    assert first.outcome == "applied"
    assert second.outcome == "duplicate_submission"


def test_flow_j_cache_delete_and_rebuild_equivalence(seeded_env):
    conn = seeded_env.open_cache()
    before = cache.canonical_dump(conn)
    conn.close()
    assert before  # sanity: fixture produced blocks

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


def test_flow_k_newer_schema_rejected_not_downgraded(seeded_env):
    conn = seeded_env.open_cache()
    conn.execute(
        "UPDATE schema_meta SET value = ? WHERE key = 'schema_version'",
        (str(cache.CACHE_SCHEMA_VERSION + 1),),
    )
    conn.commit()
    conn.close()
    with pytest.raises(cache.SchemaVersionError):
        seeded_env.open_cache()
    # startup() must not paper over a newer schema by rebuilding.
    with pytest.raises(cache.SchemaVersionError):
        slp.startup(seeded_env)


def test_flow_k_controlled_migration_v1_to_v2(env, tmp_path):
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
    row = migrated.execute(
        "SELECT search_hits FROM usage_counters WHERE block_id = 'blk_m1'"
    ).fetchone()
    assert row[0] == 0
    migrated.close()


def test_flow_k_integrity_check_reports_healthy(seeded_env):
    conn = seeded_env.open_cache()
    assert cache.integrity_check(conn) == []
    conn.close()


def test_ops_schema_newer_version_rejected(seeded_env):
    from mdsqlite_spike import ops

    conn = seeded_env.open_ops()
    conn.execute(
        "UPDATE schema_meta SET value = ? WHERE key = 'schema_version'",
        (str(ops.OPS_SCHEMA_VERSION + 1),),
    )
    conn.commit()
    conn.close()
    with pytest.raises(ops.OpsSchemaVersionError):
        seeded_env.open_ops()

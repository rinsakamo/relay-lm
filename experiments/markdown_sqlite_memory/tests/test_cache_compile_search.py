"""Flows A (initial compile), B (incremental compile), C (search)."""

from mdsqlite_spike import cache, durable_usage, mdstore, search


def test_initial_compile_and_fts(seeded_env):
    conn = seeded_env.open_cache()
    assert conn.execute("SELECT COUNT(*) FROM blocks").fetchone()[0] == 12
    hits = search.execute_search(conn, search.plan_search("kw1x2"))
    assert [h.block_id for h in hits] == ["blk_p1b2"]
    conn.close()


def test_incremental_update_touches_only_affected_rows(seeded_env):
    rel_path = "topic_001.md"
    page_file = seeded_env.page_path(rel_path)
    page = mdstore.parse_page(page_file.read_text(), rel_path)
    page.blocks[2].content = "changed content with marker freshkw."
    page.blocks[2].revision += 1
    new_text = mdstore.render_page(page)
    mdstore.atomic_replace(page_file, new_text)

    conn = seeded_env.open_cache()
    stats = cache.refresh_page(conn, rel_path, new_text)
    assert (stats.inserted, stats.updated, stats.deleted, stats.unchanged) == (0, 1, 0, 3)

    hits = search.execute_search(conn, search.plan_search("freshkw"))
    assert [h.block_id for h in hits] == [page.blocks[2].block_id]
    # The pre-change text is no longer findable.
    assert not search.execute_search(conn, search.plan_search("kw1x2"))
    conn.close()


def test_incremental_block_removal(seeded_env):
    rel_path = "topic_002.md"
    page_file = seeded_env.page_path(rel_path)
    page = mdstore.parse_page(page_file.read_text(), rel_path)
    removed = page.blocks.pop(0)
    new_text = mdstore.render_page(page)
    mdstore.atomic_replace(page_file, new_text)

    conn = seeded_env.open_cache()
    stats = cache.refresh_page(conn, rel_path, new_text)
    assert stats.deleted == 1 and stats.unchanged == 3
    row = conn.execute(
        "SELECT 1 FROM blocks WHERE block_id = ?", (removed.block_id,)
    ).fetchone()
    assert row is None
    conn.close()


def test_search_metadata_filters(seeded_env):
    conn = seeded_env.open_cache()
    all_prefs = search.execute_search(conn, search.plan_search("", kind="preference"))
    assert all_prefs and all(h.kind == "preference" for h in all_prefs)

    tagged = search.execute_search(conn, search.plan_search("", user_tags=("beta",)))
    assert tagged and all("beta" in h.user_tags for h in tagged)

    paged = search.execute_search(
        conn, search.plan_search("", page_prefix="topic_000")
    )
    assert paged and all(h.page_path == "topic_000.md" for h in paged)
    conn.close()


def test_search_plan_is_bounded_and_llm_free(seeded_env):
    plan = search.plan_search(" ".join(f"term{i}" for i in range(50)), limit=10_000)
    assert len(plan.terms) == search.MAX_TERMS
    assert plan.limit == search.MAX_LIMIT
    # The future planning hook is a protocol; the shipped planner is
    # deterministic and never performs I/O.
    assert isinstance(search.DeterministicPlanner(), search.SearchPlanner)


def test_search_usage_is_durable_operational_state(seeded_env):
    conn = seeded_env.open_cache()
    search.execute_search(conn, search.plan_search("kw0x1"))
    before = durable_usage.usage_summary_for_cache(conn, "blk_p0b1")
    assert before["usage_count"] == 1
    assert before["last_used_at"] is not None
    conn.close()

    # Delete the rebuildable cache while preserving operations.db.
    for suffix in ("", "-wal", "-shm"):
        path = seeded_env.root / (seeded_env.cache_path.name + suffix)
        if path.exists():
            path.unlink()
    rebuilt = seeded_env.open_cache()
    cache.build_from_markdown(rebuilt, seeded_env.pages_dir)
    after = durable_usage.usage_summary_for_cache(rebuilt, "blk_p0b1")
    assert after == before
    rebuilt.close()


def test_relations_projected_from_source_refs(seeded_env):
    conn = seeded_env.open_cache()
    rows = conn.execute(
        "SELECT dst_block_id, relation FROM block_relations "
        "WHERE src_block_id = 'blk_p0b1'"
    ).fetchall()
    assert [(r[0], r[1]) for r in rows] == [("blk_p0b0", "references")]
    conn.close()

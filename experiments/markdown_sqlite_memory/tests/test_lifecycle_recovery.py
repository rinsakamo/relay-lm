"""Crash-window regressions for reversible Forget/Restore lifecycle changes."""

import pytest

from mdsqlite_spike import mdstore, search, slp
from mdsqlite_spike.slp import Candidate


def _status(env, block_id: str) -> tuple[str, int]:
    page = mdstore.parse_page(env.page_path("notes.md").read_text(), "notes.md")
    block = page.get(block_id)
    assert block is not None
    return block.status, block.revision


def _tombstone_count(env, block_id: str) -> int:
    conn = env.open_ops()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM tombstones WHERE block_id = ?", (block_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def test_forget_failure_before_replace_preserves_active_memory(seeded_env):
    applied = slp.apply_candidate(
        seeded_env,
        Candidate(candidate_id="forget-pre", page="notes.md", content="keep active"),
    )
    seeded_env.failpoints.arm("before_replace")
    with pytest.raises(slp.InjectedFailure):
        slp.forget(seeded_env, applied.block_id)

    assert _status(seeded_env, applied.block_id) == ("active", 1)
    assert _tombstone_count(seeded_env, applied.block_id) == 0

    report = slp.startup(seeded_env)
    assert len(report["rolled_back"]) == 1
    assert _status(seeded_env, applied.block_id) == ("active", 1)


def test_forget_failure_after_replace_rolls_forward_hidden_and_tombstone(seeded_env):
    applied = slp.apply_candidate(
        seeded_env,
        Candidate(candidate_id="forget-post", page="notes.md", content="hide safely"),
    )
    seeded_env.failpoints.arm("after_replace_before_cache")
    with pytest.raises(slp.InjectedFailure):
        slp.forget(seeded_env, applied.block_id)

    # Markdown landed, receipt/tombstone have not yet committed.
    assert _status(seeded_env, applied.block_id) == ("hidden", 2)
    assert _tombstone_count(seeded_env, applied.block_id) == 0

    report = slp.startup(seeded_env)
    assert len(report["rolled_forward"]) == 1
    assert _status(seeded_env, applied.block_id) == ("hidden", 2)
    assert _tombstone_count(seeded_env, applied.block_id) == 1

    conn = seeded_env.open_cache()
    assert not search.execute_search(conn, search.plan_search("hide"), count_usage=False)
    conn.close()


def test_restore_failure_after_replace_rolls_forward_active_and_clears_tombstone(seeded_env):
    applied = slp.apply_candidate(
        seeded_env,
        Candidate(candidate_id="restore-post", page="notes.md", content="restore safely"),
    )
    assert slp.forget(seeded_env, applied.block_id).outcome == "applied"
    assert _tombstone_count(seeded_env, applied.block_id) == 1

    seeded_env.failpoints.arm("after_cache_before_receipt")
    with pytest.raises(slp.InjectedFailure):
        slp.restore(seeded_env, applied.block_id)

    # Markdown/cache show active, but tombstone remains until the receipt transaction.
    assert _status(seeded_env, applied.block_id) == ("active", 3)
    assert _tombstone_count(seeded_env, applied.block_id) == 1

    report = slp.startup(seeded_env)
    assert len(report["rolled_forward"]) == 1
    assert _status(seeded_env, applied.block_id) == ("active", 3)
    assert _tombstone_count(seeded_env, applied.block_id) == 0

    conn = seeded_env.open_cache()
    assert [
        hit.block_id
        for hit in search.execute_search(
            conn, search.plan_search("restore"), count_usage=False
        )
    ] == [applied.block_id]
    conn.close()

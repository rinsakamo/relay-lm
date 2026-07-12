"""Flows D-H: SLP apply, deterministic failure windows, stale snapshots."""

import json

import pytest

from mdsqlite_spike import mdstore, search, slp
from mdsqlite_spike.slp import Candidate


def _candidate(n=1, **overrides):
    defaults = dict(
        candidate_id=f"cand-{n}",
        page="notes.md",
        content=f"newly formed memory number {n} with token newkw{n}",
        kind="fact",
        user_tags=("fresh",),
        source_refs=("conv:9999#1",),
    )
    defaults.update(overrides)
    return Candidate(**defaults)


def _receipt_count(env, job_id=None):
    conn = env.open_ops()
    try:
        if job_id:
            return conn.execute(
                "SELECT COUNT(*) FROM apply_receipts WHERE job_id = ?", (job_id,)
            ).fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM apply_receipts").fetchone()[0]
    finally:
        conn.close()


def test_flow_d_apply_happy_path(seeded_env):
    result = slp.apply_candidate(seeded_env, _candidate())
    assert result.outcome == "applied"
    assert result.receipt_id is not None

    # Markdown holds the committed content.
    page = mdstore.parse_page(seeded_env.page_path("notes.md").read_text())
    block = page.get(result.block_id)
    assert block is not None and "newkw1" in block.content
    assert block.revision == 1

    # The cache projection sees it immediately.
    conn = seeded_env.open_cache()
    hits = search.execute_search(conn, search.plan_search("newkw1"))
    assert [h.block_id for h in hits] == [result.block_id]
    conn.close()

    # Receipt records the digest transition, not the content.
    ops_conn = seeded_env.open_ops()
    receipt = ops_conn.execute("SELECT * FROM apply_receipts").fetchone()
    assert receipt["post_digest"] == mdstore.file_digest(
        seeded_env.page_path("notes.md")
    )
    assert json.loads(receipt["block_ids"]) == [result.block_id]
    ops_conn.close()


def test_apply_is_idempotent_per_candidate(seeded_env):
    first = slp.apply_candidate(seeded_env, _candidate())
    again = slp.apply_candidate(seeded_env, _candidate())
    assert first.outcome == "applied"
    assert again.outcome == "duplicate_submission"
    assert again.receipt_id == first.receipt_id
    assert _receipt_count(seeded_env) == 1


def test_duplicate_content_is_not_reformed(seeded_env):
    slp.apply_candidate(seeded_env, _candidate())
    other = slp.apply_candidate(
        seeded_env, _candidate(candidate_id="cand-other")
    )
    assert other.outcome == "duplicate"
    assert _receipt_count(seeded_env) == 1


def test_contradiction_candidates_are_surfaced(seeded_env):
    base = _candidate(content="user timezone is currently europe berlin")
    slp.apply_candidate(seeded_env, base)
    conflicting = slp.apply_candidate(
        seeded_env,
        _candidate(
            n=2, content="user timezone is currently asia tokyo"
        ),
    )
    assert conflicting.outcome == "applied"
    assert conflicting.contradictions == [
        mdstore.stable_block_id("cand-1")
    ]


def test_update_existing_block_bumps_revision(seeded_env):
    first = slp.apply_candidate(seeded_env, _candidate())
    update = slp.apply_candidate(
        seeded_env,
        _candidate(
            candidate_id="cand-1-update",
            content="updated memory content with token updkw",
            block_id=first.block_id,
        ),
    )
    assert update.outcome == "applied"
    page = mdstore.parse_page(seeded_env.page_path("notes.md").read_text())
    assert page.get(first.block_id).revision == 2


def test_flow_e_failure_before_replace(seeded_env):
    pre = mdstore.file_digest(seeded_env.page_path("notes.md"))
    seeded_env.failpoints.arm("before_replace")
    with pytest.raises(slp.InjectedFailure):
        slp.apply_candidate(seeded_env, _candidate())

    # Markdown untouched, no receipt, job recoverable.
    assert mdstore.file_digest(seeded_env.page_path("notes.md")) == pre
    assert _receipt_count(seeded_env) == 0
    report = slp.startup(seeded_env)
    assert len(report["rolled_back"]) == 1
    assert not report["rolled_forward"] and not report["conflicts"]

    # Retry succeeds cleanly.
    retry = slp.apply_candidate(seeded_env, _candidate())
    assert retry.outcome == "applied"
    assert _receipt_count(seeded_env) == 1


@pytest.mark.parametrize(
    "failpoint", ["after_replace_before_cache", "after_cache_before_receipt"]
)
def test_flows_f_g_failure_after_replace(seeded_env, failpoint):
    seeded_env.failpoints.arm(failpoint)
    with pytest.raises(slp.InjectedFailure):
        slp.apply_candidate(seeded_env, _candidate())

    # Markdown was replaced but the mutation is not yet committed
    # (no durable receipt).
    page = mdstore.parse_page(seeded_env.page_path("notes.md").read_text())
    assert page.blocks and _receipt_count(seeded_env) == 0

    # Restart: recovery rolls forward deterministically without re-applying.
    report = slp.startup(seeded_env)
    assert len(report["rolled_forward"]) == 1
    assert not report["conflicts"]
    assert _receipt_count(seeded_env) == 1

    # No double apply: single block, revision 1, one receipt; cache agrees
    # with Markdown.
    page = mdstore.parse_page(seeded_env.page_path("notes.md").read_text())
    assert len(page.blocks) == 1 and page.blocks[0].revision == 1
    conn = seeded_env.open_cache()
    hits = search.execute_search(conn, search.plan_search("newkw1"))
    assert len(hits) == 1
    conn.close()

    # A second recovery pass is a no-op (recovery itself is idempotent).
    report = slp.startup(seeded_env)
    assert not report["rolled_forward"] and not report["rolled_back"]
    assert _receipt_count(seeded_env) == 1


def test_flow_g_idempotency_key_present_after_recovery(seeded_env):
    seeded_env.failpoints.arm("after_cache_before_receipt")
    with pytest.raises(slp.InjectedFailure):
        slp.apply_candidate(seeded_env, _candidate())
    slp.startup(seeded_env)
    # Resubmitting the same candidate after recovery is a duplicate
    # submission, not a re-apply.
    again = slp.apply_candidate(seeded_env, _candidate())
    assert again.outcome == "duplicate_submission"
    assert _receipt_count(seeded_env) == 1


def test_flow_h_stale_snapshot_two_workers(seeded_env):
    # Both workers plan from the same page snapshot.
    plan_one = slp.plan_candidate(seeded_env, _candidate(n=1))
    plan_two = slp.plan_candidate(seeded_env, _candidate(n=2))
    assert plan_one.pre_digest == plan_two.pre_digest

    first = slp.commit_plan(seeded_env, plan_one, worker="worker-A")
    assert first.outcome == "applied"

    # The second writer must not overwrite newer Markdown.
    second = slp.commit_plan(seeded_env, plan_two, worker="worker-B")
    assert second.outcome == "stale_snapshot"
    page = mdstore.parse_page(seeded_env.page_path("notes.md").read_text())
    assert [b.block_id for b in page.blocks] == [plan_one.block_ids[0]]

    # Re-plan from the fresh snapshot and retry: both memories survive.
    retry = slp.apply_candidate(seeded_env, _candidate(n=2), worker="worker-B")
    assert retry.outcome == "applied"
    page = mdstore.parse_page(seeded_env.page_path("notes.md").read_text())
    assert len(page.blocks) == 2

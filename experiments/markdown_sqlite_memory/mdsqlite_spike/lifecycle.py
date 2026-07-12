"""Reversible lifecycle transitions for the Markdown/SQLite spike.

Forget is a canonical ``active -> hidden`` Markdown revision.  Restore is the
inverse ``hidden -> active`` revision.  Physical block removal is intentionally
not part of either operation and remains a separate, unimplemented Purge
boundary.

Both transitions use the existing intent/digest/cache/receipt protocol.  The
lifecycle tombstone insert/delete is committed in the same operations.db
transaction as the apply receipt, including restart roll-forward.
"""
from __future__ import annotations

from dataclasses import replace
import json
from types import ModuleType

from . import cache, mdstore, ops, slp


def _existing_idempotency(ops_conn, key: str):
    row = ops_conn.execute(
        "SELECT * FROM idempotency WHERE key = ?", (key,)
    ).fetchone()
    if row is None:
        return None
    return slp.ApplyResult(
        outcome="duplicate_submission",
        job_id=row["job_id"],
        receipt_id=row["receipt_id"],
    )


def _plan_transition(
    env: slp.SpikeEnv,
    block_id: str,
    *,
    from_status: str,
    to_status: str,
    operation: str,
    reason: str,
) -> slp.ApplyPlan | slp.ApplyResult:
    ops_conn = env.open_ops()
    cache_conn = env.open_cache()
    try:
        row = cache_conn.execute(
            "SELECT page_path, content_key, status, revision FROM blocks "
            "WHERE block_id = ?",
            (block_id,),
        ).fetchone()
        if row is None:
            return slp.ApplyResult(
                outcome="failed", error=f"block {block_id} not found in cache"
            )
        if row["status"] == to_status:
            return slp.ApplyResult(outcome="duplicate", block_id=block_id)
        if row["status"] != from_status:
            return slp.ApplyResult(
                outcome="failed",
                block_id=block_id,
                error=(
                    f"{operation} requires status {from_status!r}; "
                    f"found {row['status']!r}"
                ),
            )

        page_rel = row["page_path"]
        page_file = env.page_path(page_rel)
        current_text = page_file.read_text(encoding="utf-8")
        page = mdstore.parse_page(current_text, page_rel)
        current = page.get(block_id)
        if current is None:
            return slp.ApplyResult(
                outcome="failed",
                error=f"block {block_id} not present in Markdown page {page_rel}",
            )

        key = f"{operation}:{block_id}:r{current.revision}"
        duplicate = _existing_idempotency(ops_conn, key)
        if duplicate is not None:
            return duplicate

        transitioned = replace(
            current,
            status=to_status,
            revision=current.revision + 1,
            updated=env.now(),
        )
        new_text = mdstore.render_page(mdstore.with_block(page, transitioned))
        tombstone = {
            "action": "insert" if to_status == "hidden" else "delete",
            "block_id": block_id,
            "content_key": row["content_key"],
            "reason": reason,
        }
        return slp.ApplyPlan(
            job_id=slp._job_id_for(key),
            idempotency_key=key,
            kind=operation,
            page_rel=page_rel,
            pre_digest=mdstore.text_digest(current_text),
            post_digest=mdstore.text_digest(new_text),
            new_text=new_text,
            block_ids=(block_id,),
            tombstone=tombstone,
        )
    finally:
        ops_conn.close()
        cache_conn.close()


def plan_forget(
    env: slp.SpikeEnv, block_id: str, reason: str
) -> slp.ApplyPlan | slp.ApplyResult:
    return _plan_transition(
        env,
        block_id,
        from_status="active",
        to_status="hidden",
        operation="forget",
        reason=reason,
    )


def plan_restore(
    env: slp.SpikeEnv, block_id: str, reason: str
) -> slp.ApplyPlan | slp.ApplyResult:
    return _plan_transition(
        env,
        block_id,
        from_status="hidden",
        to_status="active",
        operation="restore",
        reason=reason,
    )


def _apply_tombstone_action(ops_conn, tombstone: dict, now: str) -> None:
    action = tombstone.get("action", "insert")
    block_id = tombstone["block_id"]
    content_key = tombstone["content_key"]
    if action == "insert":
        ops_conn.execute(
            "DELETE FROM tombstones WHERE block_id = ? OR content_key = ?",
            (block_id, content_key),
        )
        ops_conn.execute(
            "INSERT INTO tombstones(block_id, content_key, reason, created_at) "
            "VALUES(?, ?, ?, ?)",
            (block_id, content_key, tombstone["reason"], now),
        )
        return
    if action == "delete":
        ops_conn.execute(
            "DELETE FROM tombstones WHERE block_id = ? OR content_key = ?",
            (block_id, content_key),
        )
        return
    raise ValueError(f"unknown tombstone action {action!r}")


def finish_commit(env, ops_conn, cache_conn, plan_row: dict, now: str) -> int:
    """Lifecycle-aware replacement for ``slp._finish_commit``."""
    page_file = env.page_path(plan_row["page_path"])
    actual = mdstore.file_digest(page_file)
    if actual != plan_row["post_digest"]:
        raise RuntimeError(
            f"digest verification failed for {plan_row['page_path']}: "
            f"expected {plan_row['post_digest']}, found {actual}"
        )
    cache.refresh_page(
        cache_conn, plan_row["page_path"], page_file.read_text(encoding="utf-8")
    )
    env.failpoints.hit("after_cache_before_receipt")
    block_ids = plan_row["block_ids"]
    if not isinstance(block_ids, str):
        block_ids = json.dumps(list(block_ids))
    with ops.immediate_txn(ops_conn):
        cur = ops_conn.execute(
            "INSERT INTO apply_receipts(job_id, page_path, pre_digest, post_digest, "
            "block_ids, committed_at) VALUES(?, ?, ?, ?, ?, ?)",
            (
                plan_row["job_id"],
                plan_row["page_path"],
                plan_row["pre_digest"],
                plan_row["post_digest"],
                block_ids,
                now,
            ),
        )
        receipt_id = cur.lastrowid
        tombstone = plan_row.get("tombstone")
        if tombstone:
            _apply_tombstone_action(ops_conn, tombstone, now)
        ops_conn.execute(
            "INSERT INTO idempotency(key, job_id, outcome, receipt_id, created_at) "
            "VALUES(?, ?, ?, ?, ?)",
            (
                plan_row["idempotency_key"],
                plan_row["job_id"],
                "applied",
                receipt_id,
                now,
            ),
        )
        ops_conn.execute(
            "UPDATE jobs SET state = 'applied', updated_at = ?, last_error = NULL "
            "WHERE job_id = ?",
            (now, plan_row["job_id"]),
        )
        ops_conn.execute(
            "DELETE FROM apply_intents WHERE job_id = ?", (plan_row["job_id"],)
        )
    return receipt_id


def forget(
    env: slp.SpikeEnv,
    block_id: str,
    reason: str = "user_forget",
    worker: str = "worker-0",
) -> slp.ApplyResult:
    plan = plan_forget(env, block_id, reason)
    if isinstance(plan, slp.ApplyResult):
        return plan
    return slp.commit_plan(env, plan, worker)


def restore(
    env: slp.SpikeEnv,
    block_id: str,
    reason: str = "user_restore",
    worker: str = "worker-0",
) -> slp.ApplyResult:
    plan = plan_restore(env, block_id, reason)
    if isinstance(plan, slp.ApplyResult):
        return plan
    return slp.commit_plan(env, plan, worker)


def install(slp_module: ModuleType) -> None:
    """Install lifecycle-correct public operations into the experiment module."""
    slp_module._finish_commit = finish_commit
    slp_module.plan_forget = plan_forget
    slp_module.forget = forget
    slp_module.plan_restore = plan_restore
    slp_module.restore = restore

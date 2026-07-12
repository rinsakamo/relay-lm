"""SLP apply pipeline: SQLite reconciliation, atomic Markdown commit, recovery.

Commit protocol for one MEM mutation (page-granular):

1. Reconcile the candidate against the cache and operations store
   (idempotency, tombstones, duplicates, contradiction candidates).
2. Plan: render the target page's post-image; record ``pre_digest`` and
   ``post_digest``.
3. Durably record an *apply intent* in operations.db and move the job to
   ``applying``.                                     [failpoint: before_replace]
4. Under the operations.db IMMEDIATE-transaction mutex:
   a. stale check — the page digest on disk must equal ``pre_digest``,
      otherwise the snapshot is stale and the job goes back to ``pending``;
   b. atomic Markdown replace (tmp file, fsync, rename, dir fsync);
                                         [failpoint: after_replace_before_cache]
   c. digest verification of the replaced file;
   d. incremental cache refresh;       [failpoint: after_cache_before_receipt]
   e. durable apply receipt + idempotency record (+ tombstone for forgets),
      job -> ``applied``, intent cleared.

**The mutation is committed exactly when step 4e's transaction commits**
(the receipt becomes durable). Any failure before 4b leaves Markdown
untouched and the job retryable. Any failure after 4b is recovered
deterministically by ``recover()``: the durable intent plus the on-disk
digest decide whether to roll the job forward (finish cache refresh and
receipt — never re-render, so no double-apply) or back (reset to pending).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import cache, mdstore, ops

FAILPOINTS = (
    "before_replace",
    "after_replace_before_cache",
    "after_cache_before_receipt",
)


class InjectedFailure(RuntimeError):
    """Deterministic fault injected at a named failpoint."""

    def __init__(self, name: str):
        super().__init__(f"injected failure at failpoint {name!r}")
        self.failpoint = name


class Failpoints:
    def __init__(self) -> None:
        self._armed: set[str] = set()

    def arm(self, name: str) -> None:
        if name not in FAILPOINTS:
            raise ValueError(f"unknown failpoint {name!r}; known: {FAILPOINTS}")
        self._armed.add(name)

    def disarm(self, name: str) -> None:
        self._armed.discard(name)

    def hit(self, name: str) -> None:
        if name in self._armed:
            self._armed.discard(name)
            raise InjectedFailure(name)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SpikeEnv:
    """Paths, clock and failpoints for one spike working directory."""

    def __init__(self, root: Path, clock=None):
        self.root = Path(root)
        self.pages_dir = self.root / "pages"
        self.cache_path = self.root / "memory-cache.db"
        self.ops_path = self.root / "operations.db"
        self.failpoints = Failpoints()
        self._clock = clock or _utc_now

    def now(self) -> str:
        return self._clock()

    def open_cache(self):
        return cache.open_cache(self.cache_path)

    def open_ops(self):
        return ops.connect(self.ops_path)

    def page_path(self, rel_path: str) -> Path:
        return self.pages_dir / rel_path


@dataclass
class Candidate:
    """Synthetic SLP candidate (fixture input; no LLM involved)."""

    candidate_id: str
    page: str
    content: str
    kind: str = "fact"
    user_tags: tuple[str, ...] = ()
    system_tags: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    block_id: str | None = None  # set to update an existing block

    def idempotency_key(self) -> str:
        return f"candidate:{self.candidate_id}"


@dataclass
class ApplyResult:
    outcome: str  # applied | duplicate | duplicate_submission | blocked_tombstone
    #             # | stale_snapshot | failed
    job_id: str | None = None
    block_id: str | None = None
    receipt_id: int | None = None
    contradictions: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class ApplyPlan:
    job_id: str
    idempotency_key: str
    kind: str
    page_rel: str
    pre_digest: str
    post_digest: str
    new_text: str
    block_ids: tuple[str, ...]
    contradictions: list[str] = field(default_factory=list)
    tombstone: dict | None = None  # for forget jobs


def _job_id_for(key: str) -> str:
    return "job_" + mdstore.stable_block_id(key)[4:]


def _ensure_job(
    ops_conn, plan_key: str, kind: str, payload: dict, now: str, max_attempts: int = 3
) -> str:
    job_id = _job_id_for(plan_key)
    ops_conn.execute(
        "INSERT INTO jobs(job_id, idempotency_key, kind, payload, state, "
        "attempts, max_attempts, created_at, updated_at) "
        "VALUES(?, ?, ?, ?, 'pending', 0, ?, ?, ?) "
        "ON CONFLICT(idempotency_key) DO NOTHING",
        (job_id, plan_key, kind, json.dumps(payload, sort_keys=True), max_attempts,
         now, now),
    )
    return job_id


def find_contradictions(cache_conn, kind: str, subject_key: str, content_key: str) -> list[str]:
    """Active blocks sharing the subject heuristic but with different content."""
    if not subject_key:
        return []
    return [
        r["block_id"]
        for r in cache_conn.execute(
            "SELECT block_id FROM blocks WHERE status = 'active' AND kind = ? "
            "AND subject_key = ? AND content_key != ? ORDER BY block_id",
            (kind, subject_key, content_key),
        )
    ]


def plan_candidate(env: SpikeEnv, candidate: Candidate) -> ApplyPlan | ApplyResult:
    """Reconcile in SQLite and produce a render plan from the current snapshot.

    Returns an ``ApplyResult`` directly for terminal reconciliation outcomes
    (duplicate submission, tombstone block, duplicate content).
    """
    ops_conn = env.open_ops()
    cache_conn = env.open_cache()
    try:
        now = env.now()
        key = candidate.idempotency_key()

        existing = ops_conn.execute(
            "SELECT * FROM idempotency WHERE key = ?", (key,)
        ).fetchone()
        if existing is not None:
            return ApplyResult(
                outcome="duplicate_submission",
                job_id=existing["job_id"],
                receipt_id=existing["receipt_id"],
            )

        probe = mdstore.Block(block_id="probe", content=candidate.content)
        content_key = probe.content_key()
        subject_key = probe.subject_key()

        tomb = ops.tombstone_for_content_key(ops_conn, content_key)
        if tomb is not None:
            with ops.immediate_txn(ops_conn):
                job_id = _ensure_job(
                    ops_conn, key, "apply_candidate",
                    {"candidate_id": candidate.candidate_id}, now,
                )
                ops_conn.execute(
                    "UPDATE jobs SET state = 'blocked_tombstone', updated_at = ?, "
                    "last_error = ? WHERE job_id = ?",
                    (now, f"blocked by tombstone {tomb['tombstone_id']}", job_id),
                )
                ops.record_failure(
                    ops_conn, job_id, "reconcile",
                    f"candidate matches tombstone content_key {content_key}", now,
                )
            return ApplyResult(outcome="blocked_tombstone", job_id=job_id)

        if candidate.block_id is None:
            dup = cache_conn.execute(
                "SELECT block_id FROM blocks WHERE content_key = ? "
                "AND status = 'active' LIMIT 1",
                (content_key,),
            ).fetchone()
            if dup is not None:
                return ApplyResult(outcome="duplicate", block_id=dup["block_id"])

        contradictions = find_contradictions(
            cache_conn, candidate.kind, subject_key, content_key
        )

        page_rel = candidate.page
        page_file = env.page_path(page_rel)
        current_text = (
            page_file.read_text(encoding="utf-8") if page_file.exists() else ""
        )
        page = (
            mdstore.parse_page(current_text, page_rel)
            if current_text
            else mdstore.Page(title=Path(page_rel).stem.replace("_", " ").title())
        )
        block_id = candidate.block_id or mdstore.stable_block_id(
            candidate.candidate_id
        )
        prior = page.get(block_id)
        block = mdstore.Block(
            block_id=block_id,
            status="active",
            kind=candidate.kind,
            user_tags=candidate.user_tags,
            system_tags=candidate.system_tags,
            source_refs=candidate.source_refs,
            revision=(prior.revision + 1) if prior else 1,
            updated=now,
            content=candidate.content.strip(),
        )
        new_text = mdstore.render_page(mdstore.with_block(page, block))
        return ApplyPlan(
            job_id=_job_id_for(key),
            idempotency_key=key,
            kind="apply_candidate",
            page_rel=page_rel,
            pre_digest=mdstore.text_digest(current_text) if current_text
            else mdstore.EMPTY_DIGEST,
            post_digest=mdstore.text_digest(new_text),
            new_text=new_text,
            block_ids=(block_id,),
            contradictions=contradictions,
        )
    finally:
        ops_conn.close()
        cache_conn.close()


def plan_forget(env: SpikeEnv, block_id: str, reason: str) -> ApplyPlan | ApplyResult:
    ops_conn = env.open_ops()
    cache_conn = env.open_cache()
    try:
        key = f"forget:{block_id}"
        existing = ops_conn.execute(
            "SELECT * FROM idempotency WHERE key = ?", (key,)
        ).fetchone()
        if existing is not None:
            return ApplyResult(
                outcome="duplicate_submission",
                job_id=existing["job_id"],
                receipt_id=existing["receipt_id"],
            )
        row = cache_conn.execute(
            "SELECT page_path, content_key FROM blocks WHERE block_id = ?",
            (block_id,),
        ).fetchone()
        if row is None:
            return ApplyResult(
                outcome="failed", error=f"block {block_id} not found in cache"
            )
        page_rel = row["page_path"]
        page_file = env.page_path(page_rel)
        current_text = page_file.read_text(encoding="utf-8")
        page = mdstore.parse_page(current_text, page_rel)
        if page.get(block_id) is None:
            return ApplyResult(
                outcome="failed",
                error=f"block {block_id} not present in Markdown page {page_rel}",
            )
        new_text = mdstore.render_page(mdstore.without_block(page, block_id))
        return ApplyPlan(
            job_id=_job_id_for(key),
            idempotency_key=key,
            kind="forget",
            page_rel=page_rel,
            pre_digest=mdstore.text_digest(current_text),
            post_digest=mdstore.text_digest(new_text),
            new_text=new_text,
            block_ids=(block_id,),
            tombstone={
                "block_id": block_id,
                "content_key": row["content_key"],
                "reason": reason,
            },
        )
    finally:
        ops_conn.close()
        cache_conn.close()


def _finish_commit(env: SpikeEnv, ops_conn, cache_conn, plan_row: dict, now: str) -> int:
    """Steps 4c-4e given that the Markdown replace already happened.

    ``plan_row`` needs: job_id, page_path, pre_digest, post_digest,
    block_ids (JSON list or tuple), tombstone (dict or None),
    idempotency_key, outcome. The caller supplies connections; the receipt
    transaction is the commit point. Idempotent: never re-renders Markdown.
    """
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
            ops_conn.execute(
                "INSERT INTO tombstones(block_id, content_key, reason, created_at) "
                "VALUES(?, ?, ?, ?)",
                (
                    tombstone["block_id"],
                    tombstone["content_key"],
                    tombstone["reason"],
                    now,
                ),
            )
        ops_conn.execute(
            "INSERT INTO idempotency(key, job_id, outcome, receipt_id, created_at) "
            "VALUES(?, ?, ?, ?, ?)",
            (plan_row["idempotency_key"], plan_row["job_id"], "applied", receipt_id,
             now),
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


def commit_plan(env: SpikeEnv, plan: ApplyPlan, worker: str = "worker-0") -> ApplyResult:
    """Execute steps 3-4 of the commit protocol for a prepared plan."""
    ops_conn = env.open_ops()
    cache_conn = env.open_cache()
    try:
        now = env.now()
        # Step 3: durable intent before any Markdown mutation.
        with ops.immediate_txn(ops_conn):
            _ensure_job(
                ops_conn, plan.idempotency_key, plan.kind,
                {"contradictions": plan.contradictions}, now,
            )
            row = ops_conn.execute(
                "SELECT state, attempts, max_attempts FROM jobs WHERE job_id = ?",
                (plan.job_id,),
            ).fetchone()
            if row["state"] == "applied":
                return ApplyResult(outcome="duplicate_submission", job_id=plan.job_id)
            if row["attempts"] >= row["max_attempts"]:
                return ApplyResult(
                    outcome="failed", job_id=plan.job_id,
                    error="max attempts exhausted",
                )
            ops_conn.execute(
                "UPDATE jobs SET state = 'applying', attempts = attempts + 1, "
                "claimed_by = ?, updated_at = ? WHERE job_id = ?",
                (worker, now, plan.job_id),
            )
            ops_conn.execute(
                "INSERT OR REPLACE INTO apply_intents(job_id, page_path, pre_digest, "
                "post_digest, block_ids, tombstone_json, created_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?)",
                (
                    plan.job_id,
                    plan.page_rel,
                    plan.pre_digest,
                    plan.post_digest,
                    json.dumps(list(plan.block_ids)),
                    json.dumps(plan.tombstone) if plan.tombstone else None,
                    now,
                ),
            )
        env.failpoints.hit("before_replace")

        # Step 4a-4b: stale check and Markdown replace are atomic under the
        # operations.db IMMEDIATE-transaction apply mutex, so a concurrent
        # applier cannot slip between the check and the replace
        # (single-host serialization).
        page_file = env.page_path(plan.page_rel)
        with ops.immediate_txn(ops_conn):
            actual = mdstore.file_digest(page_file)
            if actual != plan.pre_digest:
                ops_conn.execute(
                    "UPDATE jobs SET state = 'pending', updated_at = ?, "
                    "last_error = ? WHERE job_id = ?",
                    (now, f"stale snapshot: expected {plan.pre_digest[:12]}, "
                          f"found {actual[:12]}", plan.job_id),
                )
                ops_conn.execute(
                    "DELETE FROM apply_intents WHERE job_id = ?", (plan.job_id,)
                )
                ops.record_failure(
                    ops_conn, plan.job_id, "stale_check",
                    "page digest changed since plan snapshot", now,
                )
                stale = True
            else:
                mdstore.atomic_replace(page_file, plan.new_text)
                stale = False
        if stale:
            return ApplyResult(
                outcome="stale_snapshot", job_id=plan.job_id,
                error="page changed since snapshot; re-plan and retry",
            )
        env.failpoints.hit("after_replace_before_cache")
        receipt_id = _finish_commit(
            env,
            ops_conn,
            cache_conn,
            {
                "job_id": plan.job_id,
                "page_path": plan.page_rel,
                "pre_digest": plan.pre_digest,
                "post_digest": plan.post_digest,
                "block_ids": plan.block_ids,
                "tombstone": plan.tombstone,
                "idempotency_key": plan.idempotency_key,
            },
            now,
        )
        return ApplyResult(
            outcome="applied",
            job_id=plan.job_id,
            block_id=plan.block_ids[0],
            receipt_id=receipt_id,
            contradictions=plan.contradictions,
        )
    finally:
        ops_conn.close()
        cache_conn.close()


def apply_candidate(
    env: SpikeEnv, candidate: Candidate, worker: str = "worker-0"
) -> ApplyResult:
    plan = plan_candidate(env, candidate)
    if isinstance(plan, ApplyResult):
        return plan
    return commit_plan(env, plan, worker)


def forget(env: SpikeEnv, block_id: str, reason: str = "user_forget",
           worker: str = "worker-0") -> ApplyResult:
    plan = plan_forget(env, block_id, reason)
    if isinstance(plan, ApplyResult):
        return plan
    return commit_plan(env, plan, worker)


def recover(env: SpikeEnv) -> dict:
    """Deterministic restart recovery.

    For every job stuck in ``applying`` with a durable intent, the on-disk
    page digest decides the direction:

    - digest == post_digest: Markdown replace happened; roll forward by
      finishing cache refresh and receipt (no re-render, no double-apply);
    - digest == pre_digest: Markdown untouched; roll back to ``pending``
      (or ``failed`` once attempts are exhausted);
    - anything else: an unrelated writer touched the page; fail the job and
      rebuild the cache from Markdown.

    Independently, any cache page whose digest disagrees with Markdown is
    re-projected (covers crash windows where the replace landed but the
    cache refresh did not).
    """
    report = {"rolled_forward": [], "rolled_back": [], "failed": [],
              "conflicts": [], "cache_pages_refreshed": []}
    ops_conn = env.open_ops()
    cache_conn = env.open_cache()
    try:
        now = env.now()
        rows = ops_conn.execute(
            "SELECT j.job_id, j.attempts, j.max_attempts, i.page_path, "
            "i.pre_digest, i.post_digest, i.block_ids, i.tombstone_json, "
            "j.idempotency_key "
            "FROM jobs j JOIN apply_intents i ON i.job_id = j.job_id "
            "WHERE j.state = 'applying' ORDER BY j.created_at"
        ).fetchall()
        for row in rows:
            actual = mdstore.file_digest(env.page_path(row["page_path"]))
            if actual == row["post_digest"]:
                _finish_commit(
                    env,
                    ops_conn,
                    cache_conn,
                    {
                        "job_id": row["job_id"],
                        "page_path": row["page_path"],
                        "pre_digest": row["pre_digest"],
                        "post_digest": row["post_digest"],
                        "block_ids": row["block_ids"],
                        "tombstone": json.loads(row["tombstone_json"])
                        if row["tombstone_json"] else None,
                        "idempotency_key": row["idempotency_key"],
                    },
                    now,
                )
                report["rolled_forward"].append(row["job_id"])
            elif actual == row["pre_digest"]:
                retryable = row["attempts"] < row["max_attempts"]
                with ops.immediate_txn(ops_conn):
                    ops_conn.execute(
                        "UPDATE jobs SET state = ?, updated_at = ?, last_error = ? "
                        "WHERE job_id = ?",
                        (
                            "pending" if retryable else "failed",
                            now,
                            "recovered: crash before Markdown replace",
                            row["job_id"],
                        ),
                    )
                    ops_conn.execute(
                        "DELETE FROM apply_intents WHERE job_id = ?",
                        (row["job_id"],),
                    )
                report["rolled_back" if retryable else "failed"].append(row["job_id"])
            else:
                with ops.immediate_txn(ops_conn):
                    ops_conn.execute(
                        "UPDATE jobs SET state = 'failed', updated_at = ?, "
                        "last_error = 'recovered: page digest matches neither "
                        "pre nor post image' WHERE job_id = ?",
                        (now, row["job_id"]),
                    )
                    ops_conn.execute(
                        "DELETE FROM apply_intents WHERE job_id = ?",
                        (row["job_id"],),
                    )
                    ops.record_failure(
                        ops_conn, row["job_id"], "recover",
                        "conflicting page mutation detected", now,
                    )
                report["conflicts"].append(row["job_id"])
        # Cache staleness sweep: restart detects digest mismatches and
        # re-projects those pages from Markdown.
        for rel_path in cache.stale_pages(cache_conn, env.pages_dir):
            page_file = env.page_path(rel_path)
            text = (
                page_file.read_text(encoding="utf-8") if page_file.exists() else None
            )
            cache.refresh_page(cache_conn, rel_path, text)
            report["cache_pages_refreshed"].append(rel_path)
        return report
    finally:
        ops_conn.close()
        cache_conn.close()


def startup(env: SpikeEnv) -> dict:
    """Open (or rebuild) the cache, then run recovery. Returns the report.

    A corrupt or deleted memory-cache.db is not an error: it is rebuilt from
    Markdown, which is the whole point of the projection.
    """
    report: dict = {"cache_rebuilt": False}
    try:
        if not env.cache_path.exists():
            raise cache.CacheCorruptError("memory-cache.db missing")
        conn = env.open_cache()
        problems = cache.integrity_check(conn)
        conn.close()
        if problems:
            raise cache.CacheCorruptError("; ".join(problems))
    except (cache.CacheCorruptError, cache.SchemaVersionError) as exc:
        if isinstance(exc, cache.SchemaVersionError):
            raise  # newer schema must never be silently rebuilt over
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(env.cache_path) + suffix)
            if candidate.exists():
                candidate.unlink()
        conn = env.open_cache()
        cache.build_from_markdown(conn, env.pages_dir)
        conn.close()
        report["cache_rebuilt"] = True
    report.update(recover(env))
    return report

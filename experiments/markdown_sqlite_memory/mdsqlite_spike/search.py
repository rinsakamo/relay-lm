"""Search over the memory cache: FTS keyword match plus metadata filters.

``SearchPlanner`` is the bounded future planning interface: a production
system could put an LLM behind it to turn a natural-language query into a
``SearchPlan``. This spike ships only the deterministic planner and never
calls an LLM. Plans are bounded by construction (term count and result
limit are clamped), so any planner implementation stays within budget.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

MAX_TERMS = 8
MAX_LIMIT = 100
_TOKEN_RE = re.compile(r"[a-z0-9_]+")


@dataclass(frozen=True)
class SearchPlan:
    terms: tuple[str, ...] = ()
    kind: str | None = None
    user_tags: tuple[str, ...] = ()
    system_tags: tuple[str, ...] = ()
    status: str = "active"
    page_prefix: str | None = None
    limit: int = 20

    def bounded(self) -> "SearchPlan":
        return SearchPlan(
            terms=self.terms[:MAX_TERMS],
            kind=self.kind,
            user_tags=self.user_tags,
            system_tags=self.system_tags,
            status=self.status,
            page_prefix=self.page_prefix,
            limit=max(1, min(self.limit, MAX_LIMIT)),
        )


@dataclass
class SearchHit:
    block_id: str
    page_path: str
    kind: str
    status: str
    revision: int
    content: str
    score: float
    user_tags: list[str] = field(default_factory=list)


@runtime_checkable
class SearchPlanner(Protocol):
    """Future hook: an LLM-backed planner would implement this protocol."""

    def plan(self, query: str, **filters) -> SearchPlan: ...


class DeterministicPlanner:
    """Tokenizing planner used by the spike; no LLM involved."""

    def plan(self, query: str, **filters) -> SearchPlan:
        terms = tuple(_TOKEN_RE.findall(query.lower()))
        return SearchPlan(terms=terms, **filters).bounded()


def plan_search(query: str, **filters) -> SearchPlan:
    return DeterministicPlanner().plan(query, **filters)


def execute_search(
    conn: sqlite3.Connection, plan: SearchPlan, count_usage: bool = True
) -> list[SearchHit]:
    plan = plan.bounded()
    params: list = []
    if plan.terms:
        match = " AND ".join(f'"{term}"' for term in plan.terms)
        sql = (
            "SELECT b.block_id, b.page_path, b.kind, b.status, b.revision, "
            "b.content, bm25(blocks_fts) AS score "
            "FROM blocks_fts JOIN blocks b ON b.block_id = blocks_fts.block_id "
            "WHERE blocks_fts MATCH ?"
        )
        params.append(match)
    else:
        sql = (
            "SELECT b.block_id, b.page_path, b.kind, b.status, b.revision, "
            "b.content, 0.0 AS score FROM blocks b WHERE 1=1"
        )
    sql += " AND b.status = ?"
    params.append(plan.status)
    if plan.kind:
        sql += " AND b.kind = ?"
        params.append(plan.kind)
    if plan.page_prefix:
        sql += " AND b.page_path LIKE ?"
        params.append(plan.page_prefix + "%")
    for tag in plan.user_tags:
        sql += (
            " AND EXISTS(SELECT 1 FROM block_tags t WHERE t.block_id = b.block_id "
            "AND t.namespace = 'user' AND t.tag = ?)"
        )
        params.append(tag)
    for tag in plan.system_tags:
        sql += (
            " AND EXISTS(SELECT 1 FROM block_tags t WHERE t.block_id = b.block_id "
            "AND t.namespace = 'system' AND t.tag = ?)"
        )
        params.append(tag)
    sql += " ORDER BY score, b.block_id LIMIT ?"
    params.append(plan.limit)
    hits = [
        SearchHit(
            block_id=row["block_id"],
            page_path=row["page_path"],
            kind=row["kind"],
            status=row["status"],
            revision=row["revision"],
            content=row["content"],
            score=row["score"],
        )
        for row in conn.execute(sql, params)
    ]
    for hit in hits:
        hit.user_tags = [
            r["tag"]
            for r in conn.execute(
                "SELECT tag FROM block_tags WHERE block_id = ? AND namespace = 'user' "
                "ORDER BY tag",
                (hit.block_id,),
            )
        ]
    if count_usage and hits:
        conn.execute("BEGIN IMMEDIATE")
        try:
            for hit in hits:
                conn.execute(
                    "UPDATE usage_counters SET search_hits = search_hits + 1 "
                    "WHERE block_id = ?",
                    (hit.block_id,),
                )
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
    return hits

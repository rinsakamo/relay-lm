"""Durable usage-event adapter for the rebuildable search cache.

Search ranking/content stays in ``memory-cache.db``.  Usage history is written
to the sibling ``operations.db`` because last-use and usage-count projections
cannot be reconstructed from Markdown alone.
"""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import ModuleType

from . import ops


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cache_path(conn) -> Path | None:
    rows = conn.execute("PRAGMA database_list").fetchall()
    for row in rows:
        name = row[1]
        filename = row[2]
        if name == "main" and filename:
            return Path(filename)
    return None


def _query_digest(plan) -> str:
    payload = dataclasses.asdict(plan) if dataclasses.is_dataclass(plan) else repr(plan)
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def usage_summary_for_cache(conn, block_id: str) -> dict:
    path = _cache_path(conn)
    if path is None:
        return {"block_id": block_id, "usage_count": 0, "last_used_at": None}
    ops_conn = ops.connect(path.parent / "operations.db")
    try:
        return ops.usage_summary(ops_conn, block_id)
    finally:
        ops_conn.close()


def install(search_module: ModuleType) -> None:
    """Patch the spike search function once, preserving its public signature."""
    if getattr(search_module.execute_search, "_relaylm_durable_usage", False):
        return
    original = search_module.execute_search

    def execute_search(conn, plan, count_usage: bool = True):
        hits = original(conn, plan, count_usage=False)
        if count_usage and hits:
            path = _cache_path(conn)
            if path is not None:
                ops_conn = ops.connect(path.parent / "operations.db")
                try:
                    now = _utc_now()
                    digest = _query_digest(plan)
                    with ops.immediate_txn(ops_conn):
                        for hit in hits:
                            ops.record_usage_event(
                                ops_conn,
                                hit.block_id,
                                now,
                                event_kind="search_hit",
                                query_digest=digest,
                            )
                finally:
                    ops_conn.close()
        return hits

    execute_search._relaylm_durable_usage = True
    execute_search.__name__ = original.__name__
    execute_search.__doc__ = original.__doc__
    search_module.execute_search = execute_search

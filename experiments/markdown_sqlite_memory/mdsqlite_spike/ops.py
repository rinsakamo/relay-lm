"""operations.db — persistent operational authority.

Holds state that cannot be rebuilt from Markdown: jobs, claims/leases, retries,
apply intents, idempotency keys, apply receipts, lifecycle tombstones, durable
usage events, and failure records. Committed MEM content authority never lives
here — receipts and events reference page digests and stable block IDs, not MEM
content.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

OPS_SCHEMA_VERSION = 2
BUSY_TIMEOUT_MS = 5000
_IMMEDIATE_MAX_ATTEMPTS = 2000


class OpsSchemaVersionError(RuntimeError):
    pass


_lock_stats_guard = threading.Lock()
_lock_stats = {
    "busy_retries": 0,
    "wait_seconds": 0.0,
    "acquisitions": 0,
    "acquire_seconds": 0.0,
    "max_acquire_seconds": 0.0,
}


def reset_lock_stats() -> None:
    with _lock_stats_guard:
        _lock_stats["busy_retries"] = 0
        _lock_stats["wait_seconds"] = 0.0
        _lock_stats["acquisitions"] = 0
        _lock_stats["acquire_seconds"] = 0.0
        _lock_stats["max_acquire_seconds"] = 0.0


def get_lock_stats() -> dict:
    with _lock_stats_guard:
        return dict(_lock_stats)


def _record_wait(seconds: float) -> None:
    with _lock_stats_guard:
        _lock_stats["busy_retries"] += 1
        _lock_stats["wait_seconds"] += seconds


def _record_acquire(seconds: float) -> None:
    with _lock_stats_guard:
        _lock_stats["acquisitions"] += 1
        _lock_stats["acquire_seconds"] += seconds
        if seconds > _lock_stats["max_acquire_seconds"]:
            _lock_stats["max_acquire_seconds"] = seconds


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        row = (
            conn.execute(
                "SELECT value FROM schema_meta WHERE key = 'schema_version'"
            ).fetchone()
            if _has_meta(conn)
            else None
        )
        if row is None:
            _create_schema(conn)
            return conn
        try:
            version = int(row["value"])
        except (TypeError, ValueError) as exc:
            raise OpsSchemaVersionError(
                f"operations schema has invalid version {row['value']!r}"
            ) from exc
        if version > OPS_SCHEMA_VERSION:
            raise OpsSchemaVersionError(
                f"operations schema v{version} is newer than supported "
                f"v{OPS_SCHEMA_VERSION}; refusing silent downgrade"
            )
        if version < OPS_SCHEMA_VERSION:
            _migrate(conn, version)
        return conn
    except BaseException:
        conn.close()
        raise


def _has_meta(conn: sqlite3.Connection) -> bool:
    return (
        conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_meta'"
        ).fetchone()
        is not None
    )


def _create_usage_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS memory_usage_events(
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_id TEXT NOT NULL,
            event_kind TEXT NOT NULL CHECK(event_kind IN ('search_hit', 'retrieval_use')),
            query_digest TEXT,
            occurred_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memory_usage_block_time
            ON memory_usage_events(block_id, occurred_at, event_id);
        """
    )


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_meta(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS jobs(
            job_id TEXT PRIMARY KEY,
            idempotency_key TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            payload TEXT NOT NULL DEFAULT '{}',
            state TEXT NOT NULL CHECK(state IN (
                'pending', 'claimed', 'applying', 'applied',
                'failed', 'blocked_tombstone'
            )),
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 3,
            claimed_by TEXT,
            lease_expires_at REAL,
            last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state, created_at);
        CREATE TABLE IF NOT EXISTS apply_intents(
            job_id TEXT PRIMARY KEY REFERENCES jobs(job_id) ON DELETE CASCADE,
            page_path TEXT NOT NULL,
            pre_digest TEXT NOT NULL,
            post_digest TEXT NOT NULL,
            block_ids TEXT NOT NULL,
            tombstone_json TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS apply_receipts(
            receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL UNIQUE REFERENCES jobs(job_id),
            page_path TEXT NOT NULL,
            pre_digest TEXT NOT NULL,
            post_digest TEXT NOT NULL,
            block_ids TEXT NOT NULL,
            committed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS idempotency(
            key TEXT PRIMARY KEY,
            job_id TEXT NOT NULL REFERENCES jobs(job_id),
            outcome TEXT NOT NULL,
            receipt_id INTEGER,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tombstones(
            tombstone_id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_id TEXT NOT NULL,
            content_key TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tombstones_key ON tombstones(content_key);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_tombstones_block_key
            ON tombstones(block_id, content_key);
        CREATE TABLE IF NOT EXISTS failures(
            failure_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            stage TEXT NOT NULL,
            error TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    _create_usage_schema(conn)
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES('schema_version', ?)",
        (str(OPS_SCHEMA_VERSION),),
    )


def _migrate(conn: sqlite3.Connection, from_version: int) -> None:
    if from_version != 1:
        raise OpsSchemaVersionError(
            f"operations schema v{from_version} is older than supported "
            f"v{OPS_SCHEMA_VERSION}; no migration path is defined"
        )
    conn.execute("BEGIN IMMEDIATE")
    try:
        _create_usage_schema(conn)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_tombstones_block_key "
            "ON tombstones(block_id, content_key)"
        )
        conn.execute(
            "UPDATE schema_meta SET value = ? WHERE key = 'schema_version'",
            (str(OPS_SCHEMA_VERSION),),
        )
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


@contextmanager
def immediate_txn(conn: sqlite3.Connection):
    """Short explicit write transaction (BEGIN IMMEDIATE) with retry.

    Also serves as the single-host apply mutex: only one holder can be in an
    IMMEDIATE transaction on operations.db at a time. Lock waits show up in two
    counters: ``acquire_seconds`` (time spent inside BEGIN IMMEDIATE, where
    busy_timeout absorbs contention) and ``busy_retries`` (explicit retries
    after busy_timeout was exhausted).
    """
    delay = 0.002
    attempts = 0
    while True:
        try:
            start = time.perf_counter()
            conn.execute("BEGIN IMMEDIATE")
            _record_acquire(time.perf_counter() - start)
            break
        except sqlite3.OperationalError as exc:
            message = str(exc).lower()
            if "locked" not in message and "busy" not in message:
                raise
            attempts += 1
            if attempts > _IMMEDIATE_MAX_ATTEMPTS:
                raise
            _record_wait(delay)
            time.sleep(delay)
            delay = min(delay * 2, 0.05)
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


def claim_next(
    conn: sqlite3.Connection,
    worker: str,
    now_iso: str,
    now_epoch: float,
    lease_seconds: float = 30.0,
) -> str | None:
    """Claim the oldest pending (or lease-expired) job. Returns job_id."""
    with immediate_txn(conn):
        row = conn.execute(
            "SELECT job_id FROM jobs WHERE state = 'pending' "
            "OR (state = 'claimed' AND lease_expires_at < ?) "
            "ORDER BY created_at, job_id LIMIT 1",
            (now_epoch,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE jobs SET state = 'claimed', claimed_by = ?, "
            "lease_expires_at = ?, updated_at = ? WHERE job_id = ?",
            (worker, now_epoch + lease_seconds, now_iso, row["job_id"]),
        )
        return row["job_id"]


def record_failure(
    conn: sqlite3.Connection, job_id: str | None, stage: str, error: str, now_iso: str
) -> None:
    conn.execute(
        "INSERT INTO failures(job_id, stage, error, created_at) VALUES(?, ?, ?, ?)",
        (job_id, stage, error, now_iso),
    )


def tombstone_for_content_key(
    conn: sqlite3.Connection, content_key: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM tombstones WHERE content_key = ? LIMIT 1", (content_key,)
    ).fetchone()


def record_usage_event(
    conn: sqlite3.Connection,
    block_id: str,
    occurred_at: str,
    *,
    event_kind: str = "search_hit",
    query_digest: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO memory_usage_events(block_id, event_kind, query_digest, occurred_at) "
        "VALUES(?, ?, ?, ?)",
        (block_id, event_kind, query_digest, occurred_at),
    )


def usage_summary(conn: sqlite3.Connection, block_id: str) -> dict:
    row = conn.execute(
        "SELECT COUNT(*) AS usage_count, MAX(occurred_at) AS last_used_at "
        "FROM memory_usage_events WHERE block_id = ?",
        (block_id,),
    ).fetchone()
    return {
        "block_id": block_id,
        "usage_count": int(row["usage_count"]),
        "last_used_at": row["last_used_at"],
    }

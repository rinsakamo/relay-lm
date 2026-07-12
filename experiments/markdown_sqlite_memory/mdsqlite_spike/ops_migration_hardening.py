"""Transactional schema-migration hardening for the experiment operations DB."""
from __future__ import annotations

from types import ModuleType


def install(ops_module: ModuleType) -> None:
    def migrate(conn, from_version: int) -> None:
        if from_version != 1:
            raise ops_module.OpsSchemaVersionError(
                f"operations schema v{from_version} is older than supported "
                f"v{ops_module.OPS_SCHEMA_VERSION}; no migration path is defined"
            )
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS memory_usage_events("
                "event_id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "block_id TEXT NOT NULL, "
                "event_kind TEXT NOT NULL CHECK(event_kind IN "
                "('search_hit', 'retrieval_use')), "
                "query_digest TEXT, occurred_at TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_usage_block_time "
                "ON memory_usage_events(block_id, occurred_at, event_id)"
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_tombstones_block_key "
                "ON tombstones(block_id, content_key)"
            )
            conn.execute(
                "UPDATE schema_meta SET value = ? WHERE key = 'schema_version'",
                (str(ops_module.OPS_SCHEMA_VERSION),),
            )
            conn.commit()
        except BaseException:
            conn.rollback()
            raise

    ops_module._migrate = migrate

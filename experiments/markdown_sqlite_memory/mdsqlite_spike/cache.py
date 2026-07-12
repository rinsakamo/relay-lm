"""memory-cache.db — persistent but fully rebuildable projection of Markdown.

The cache holds parsed blocks, page/block digests, normalized text, tags,
source refs, derived relationships, usage counters, and an FTS5 index. It is
never authoritative for committed MEM content: deleting the database and
rebuilding from Markdown must restore equivalent canonical query results
(usage counters are the one documented lossy projection — see README).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import mdstore

CACHE_SCHEMA_VERSION = 2
BUSY_TIMEOUT_MS = 5000


class SchemaVersionError(RuntimeError):
    """The on-disk schema is newer than this code supports."""


class CacheCorruptError(RuntimeError):
    """The cache database is unreadable or fails integrity checks."""


@dataclass
class RefreshStats:
    inserted: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        return conn
    except BaseException:
        conn.close()
        raise


def _create_schema(conn: sqlite3.Connection, version: int = CACHE_SCHEMA_VERSION) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_meta(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pages(
            path TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            digest TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS blocks(
            block_id TEXT PRIMARY KEY,
            page_path TEXT NOT NULL REFERENCES pages(path) ON DELETE CASCADE,
            status TEXT NOT NULL,
            kind TEXT NOT NULL,
            revision INTEGER NOT NULL,
            updated TEXT NOT NULL,
            content TEXT NOT NULL,
            normalized_text TEXT NOT NULL,
            content_key TEXT NOT NULL,
            subject_key TEXT NOT NULL,
            block_digest TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_blocks_page ON blocks(page_path);
        CREATE INDEX IF NOT EXISTS idx_blocks_content_key ON blocks(content_key);
        CREATE INDEX IF NOT EXISTS idx_blocks_subject ON blocks(kind, subject_key);
        CREATE TABLE IF NOT EXISTS block_tags(
            block_id TEXT NOT NULL REFERENCES blocks(block_id) ON DELETE CASCADE,
            namespace TEXT NOT NULL CHECK(namespace IN ('user', 'system')),
            tag TEXT NOT NULL,
            PRIMARY KEY(block_id, namespace, tag)
        );
        CREATE TABLE IF NOT EXISTS block_source_refs(
            block_id TEXT NOT NULL REFERENCES blocks(block_id) ON DELETE CASCADE,
            ref TEXT NOT NULL,
            PRIMARY KEY(block_id, ref)
        );
        CREATE TABLE IF NOT EXISTS block_relations(
            src_block_id TEXT NOT NULL REFERENCES blocks(block_id) ON DELETE CASCADE,
            dst_block_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            PRIMARY KEY(src_block_id, dst_block_id, relation)
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS blocks_fts USING fts5(
            block_id UNINDEXED,
            normalized_text
        );
        """
    )
    if version >= 2:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_counters(
                block_id TEXT PRIMARY KEY REFERENCES blocks(block_id)
                    ON DELETE CASCADE,
                search_hits INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES('schema_version', ?)",
        (str(version),),
    )


def _migrate(conn: sqlite3.Connection, from_version: int) -> None:
    """Controlled experimental migration. Never silently downgrades."""
    if from_version == 1:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                """
                CREATE TABLE usage_counters(
                    block_id TEXT PRIMARY KEY REFERENCES blocks(block_id)
                        ON DELETE CASCADE,
                    search_hits INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                "INSERT INTO usage_counters(block_id, search_hits) "
                "SELECT block_id, 0 FROM blocks"
            )
            conn.execute(
                "UPDATE schema_meta SET value = ? WHERE key = 'schema_version'",
                (str(CACHE_SCHEMA_VERSION),),
            )
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        return
    raise SchemaVersionError(f"no migration path from cache schema v{from_version}")


def open_cache(path: Path, create: bool = True) -> sqlite3.Connection:
    exists = path.exists()
    if not exists and not create:
        raise FileNotFoundError(path)
    conn: sqlite3.Connection | None = None
    try:
        conn = _connect(path)
        if not exists:
            _create_schema(conn)
            return conn
        row = conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            raise CacheCorruptError(f"cache db {path} has no schema_version")
        try:
            version = int(row["value"])
        except (TypeError, ValueError) as exc:
            raise CacheCorruptError(
                f"cache db {path} has invalid schema_version {row['value']!r}"
            ) from exc
        if version > CACHE_SCHEMA_VERSION:
            raise SchemaVersionError(
                f"cache schema v{version} is newer than supported "
                f"v{CACHE_SCHEMA_VERSION}; refusing silent downgrade"
            )
        if version < CACHE_SCHEMA_VERSION:
            _migrate(conn, version)
        return conn
    except (CacheCorruptError, SchemaVersionError):
        if conn is not None:
            conn.close()
        raise
    except sqlite3.DatabaseError as exc:
        if conn is not None:
            conn.close()
        raise CacheCorruptError(f"cannot open cache db {path}: {exc}") from exc
    except BaseException:
        if conn is not None:
            conn.close()
        raise


def integrity_check(conn: sqlite3.Connection) -> list[str]:
    """Return a list of integrity problems (empty when healthy)."""
    problems: list[str] = []
    try:
        rows = conn.execute("PRAGMA integrity_check").fetchall()
        if [r[0] for r in rows] != ["ok"]:
            problems.extend(str(r[0]) for r in rows)
        conn.execute(
            "INSERT INTO blocks_fts(blocks_fts, rank) VALUES('integrity-check', 0)"
        )
    except sqlite3.DatabaseError as exc:
        problems.append(str(exc))
    return problems


def _insert_block(conn: sqlite3.Connection, page_path: str, block: mdstore.Block) -> None:
    conn.execute(
        """
        INSERT INTO blocks(
            block_id, page_path, status, kind, revision, updated, content,
            normalized_text, content_key, subject_key, block_digest
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            block.block_id,
            page_path,
            block.status,
            block.kind,
            block.revision,
            block.updated,
            block.content,
            block.normalized_text(),
            block.content_key(),
            block.subject_key(),
            block.digest(),
        ),
    )
    for tag in block.user_tags:
        conn.execute(
            "INSERT INTO block_tags(block_id, namespace, tag) VALUES(?, 'user', ?)",
            (block.block_id, tag),
        )
    for tag in block.system_tags:
        conn.execute(
            "INSERT INTO block_tags(block_id, namespace, tag) VALUES(?, 'system', ?)",
            (block.block_id, tag),
        )
    for ref in block.source_refs:
        conn.execute(
            "INSERT INTO block_source_refs(block_id, ref) VALUES(?, ?)",
            (block.block_id, ref),
        )
        if ref.startswith("mem:"):
            conn.execute(
                "INSERT OR IGNORE INTO block_relations"
                "(src_block_id, dst_block_id, relation) VALUES(?, ?, 'references')",
                (block.block_id, ref[len("mem:"):]),
            )
    conn.execute(
        "INSERT OR IGNORE INTO usage_counters(block_id, search_hits) VALUES(?, 0)",
        (block.block_id,),
    )
    conn.execute(
        "INSERT INTO blocks_fts(block_id, normalized_text) VALUES(?, ?)",
        (block.block_id, block.normalized_text()),
    )


def _delete_block(conn: sqlite3.Connection, block_id: str) -> None:
    conn.execute("DELETE FROM blocks_fts WHERE block_id = ?", (block_id,))
    conn.execute("DELETE FROM blocks WHERE block_id = ?", (block_id,))


def refresh_page(
    conn: sqlite3.Connection, rel_path: str, text: str | None
) -> RefreshStats:
    """Incrementally project one page; only affected rows are touched.

    ``text=None`` means the page file no longer exists and its rows must go.
    """
    stats = RefreshStats()
    conn.execute("BEGIN IMMEDIATE")
    try:
        if text is None:
            block_ids = [
                r["block_id"]
                for r in conn.execute(
                    "SELECT block_id FROM blocks WHERE page_path = ?", (rel_path,)
                )
            ]
            for block_id in block_ids:
                _delete_block(conn, block_id)
                stats.deleted += 1
            conn.execute("DELETE FROM pages WHERE path = ?", (rel_path,))
            conn.commit()
            return stats
        page = mdstore.parse_page(text, rel_path)
        digest = mdstore.text_digest(text)
        existing = {
            r["block_id"]: r["block_digest"]
            for r in conn.execute(
                "SELECT block_id, block_digest FROM blocks WHERE page_path = ?",
                (rel_path,),
            )
        }
        conn.execute(
            "INSERT INTO pages(path, title, digest) VALUES(?, ?, ?) "
            "ON CONFLICT(path) DO UPDATE SET title = excluded.title, "
            "digest = excluded.digest",
            (rel_path, page.title, digest),
        )
        seen: set[str] = set()
        for block in page.blocks:
            seen.add(block.block_id)
            old_digest = existing.get(block.block_id)
            if old_digest == block.digest():
                stats.unchanged += 1
                continue
            if old_digest is not None:
                _delete_block(conn, block.block_id)
                stats.updated += 1
            else:
                stats.inserted += 1
            _insert_block(conn, rel_path, block)
        for block_id in existing:
            if block_id not in seen:
                _delete_block(conn, block_id)
                stats.deleted += 1
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return stats


def build_from_markdown(conn: sqlite3.Connection, pages_dir: Path) -> RefreshStats:
    """Full compile: wipe projections and re-project every page."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM blocks_fts")
        conn.execute("DELETE FROM blocks")
        conn.execute("DELETE FROM pages")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    total = RefreshStats()
    for rel_path, text in mdstore.load_pages(pages_dir).items():
        stats = refresh_page(conn, rel_path, text)
        total.inserted += stats.inserted
        total.updated += stats.updated
        total.deleted += stats.deleted
        total.unchanged += stats.unchanged
    return total


def stale_pages(conn: sqlite3.Connection, pages_dir: Path) -> list[str]:
    """Pages whose cached digest disagrees with the Markdown on disk."""
    on_disk = mdstore.load_pages(pages_dir)
    cached = {
        r["path"]: r["digest"] for r in conn.execute("SELECT path, digest FROM pages")
    }
    stale = [
        path
        for path, text in on_disk.items()
        if cached.get(path) != mdstore.text_digest(text)
    ]
    stale.extend(path for path in cached if path not in on_disk)
    return sorted(stale)


def canonical_dump(conn: sqlite3.Connection) -> list[dict]:
    """Deterministic canonical projection used for rebuild-equivalence checks.

    Excludes usage counters, which are a documented lossy projection.
    """
    dump: list[dict] = []
    for row in conn.execute(
        "SELECT block_id, page_path, status, kind, revision, updated, content, "
        "normalized_text, content_key, subject_key, block_digest "
        "FROM blocks ORDER BY block_id"
    ):
        entry = dict(row)
        entry["user_tags"] = [
            r["tag"]
            for r in conn.execute(
                "SELECT tag FROM block_tags WHERE block_id = ? AND namespace = 'user' "
                "ORDER BY tag",
                (row["block_id"],),
            )
        ]
        entry["system_tags"] = [
            r["tag"]
            for r in conn.execute(
                "SELECT tag FROM block_tags WHERE block_id = ? AND namespace = 'system' "
                "ORDER BY tag",
                (row["block_id"],),
            )
        ]
        entry["source_refs"] = [
            r["ref"]
            for r in conn.execute(
                "SELECT ref FROM block_source_refs WHERE block_id = ? ORDER BY ref",
                (row["block_id"],),
            )
        ]
        entry["relations"] = [
            [r["dst_block_id"], r["relation"]]
            for r in conn.execute(
                "SELECT dst_block_id, relation FROM block_relations "
                "WHERE src_block_id = ? ORDER BY dst_block_id, relation",
                (row["block_id"],),
            )
        ]
        dump.append(entry)
    return dump

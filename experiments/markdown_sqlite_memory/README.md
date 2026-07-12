# Markdown-authority / SQLite-projection memory spike

**Status: EXPERIMENT ONLY.** This directory is an isolated architecture
spike. It is not wired into the relay-lm production runtime, it does not
modify current RelayMEM/SLP storage behavior, no production module imports
it, and nothing here is accepted architecture. PR #567 does not authorize a
production migration. All fixtures are synthetic; no user data is read,
migrated, or deleted. The Markdown block syntax used here
(`relaymem-spike` v0) is experimental and does not imply a final production
syntax.

## Candidate model under test

| Store | Role | Rebuildable? |
| --- | --- | --- |
| Markdown pages (`pages/*.md`) | Steady-state canonical authority for durable MEM content and user-visible organization | It *is* the source |
| `memory-cache.db` | Parsed blocks, digests, tags, source refs, relations, lifecycle, usage counters, FTS5 | Yes — delete and recompile from Markdown |
| `operations.db` | Jobs, claims/leases, retries, apply intents, idempotency keys, apply receipts, deletion tombstones, failure records | No — operational authority, holds nothing derivable from Markdown |
| vector/graph indexes | Out of scope here; same rebuildable-projection class as the cache | Yes (by construction) |

SLP reconciles candidates inside SQLite and commits accepted changes
atomically back to Markdown.

## Commit protocol

A MEM mutation is **committed at exactly one event: the operations.db
transaction that makes the apply receipt durable** (after the Markdown
revision write and digest verification succeeded). Order:

1. Reconcile candidate in SQLite (idempotency, tombstone, duplicate,
   contradiction checks) and render the page post-image; record
   `pre_digest`/`post_digest`.
2. Durably record an apply intent in `operations.db`.
3. Under the `operations.db` `BEGIN IMMEDIATE` apply mutex: verify the
   on-disk digest still equals `pre_digest` (stale-snapshot rejection),
   then atomically replace the page (temp file → fsync → rename → dir
   fsync).
4. Verify the post-replace digest, refresh the cache projection, then in
   one transaction: apply receipt + idempotency record (+ tombstone for
   forgets) + job → `applied`.

Failure windows (all deterministically fault-injected and tested):

- **before replace** — Markdown unchanged; recovery resets the job to
  `pending` (retryable) or `failed` when attempts are exhausted.
- **after replace, before cache refresh / before receipt** — the durable
  intent plus the on-disk digest let restart recovery roll the job
  *forward*: re-project the page and write the receipt. Recovery never
  re-renders, so there is no double-apply; it is idempotent across repeated
  crashes.
- **unrecognized digest** (a foreign writer touched the page) — job fails,
  cache is rebuilt from Markdown.

The SQLite cache alone can never invent committed MEM: search reads only
what was projected from Markdown, receipts store digests and block IDs
(never content), and `verify` enforces that no receipt exists for a
non-applied job.

## Layout

- `mdsqlite_spike/mdstore.py` — experimental page syntax, parse/render
  round-trip, atomic durable replace, digests
- `mdsqlite_spike/cache.py` — memory-cache.db schema v2, incremental
  refresh, FTS5, integrity + versioning (newer schema rejected; v1→v2
  controlled migration)
- `mdsqlite_spike/ops.py` — operations.db, `BEGIN IMMEDIATE` helper with
  lock-wait instrumentation, claim/lease queue
- `mdsqlite_spike/slp.py` — reconciliation, apply pipeline, failpoints,
  restart recovery
- `mdsqlite_spike/search.py` — FTS + metadata filters; bounded
  `SearchPlanner` protocol as the future (non-LLM in this spike) planning
  hook
- `mdsqlite_spike/fixtures.py`, `bench.py`, `verify.py`, `cli.py`
- `tests/` — flows A–K, run explicitly (deliberately outside the
  production `testpaths`)
- `results/` — machine-readable benchmark output from Linux runs

## Usage

```bash
# tests (from the repo root)
python -m pytest experiments/markdown_sqlite_memory/tests

# CLI
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike init-fixture --pages 5 --blocks 8
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike build-cache
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike search kw1x2 --kind fact
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike apply-candidate \
    --candidate-id c1 --page notes.md --content "a new durable memory"
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike forget --block-id blk_p0b1
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike simulate-failure --failpoint after_replace_before_cache
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike rebuild-cache
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike verify
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike benchmark --pages 20 --blocks 25
```

## Concurrency / platform notes

- Both databases run WAL, `foreign_keys=ON`, `busy_timeout=5000`, short
  explicit transactions; writes use `BEGIN IMMEDIATE`.
- The `BEGIN IMMEDIATE` transaction on operations.db doubles as the
  single-host apply mutex: the stale-digest check and the Markdown replace
  happen atomically under it.
- Lock waits are measured two ways: time spent acquiring `BEGIN IMMEDIATE`
  (contention absorbed by busy_timeout) and explicit busy retries after
  timeout exhaustion.
- Executed and measured on Linux only. WSL and Windows durability
  (fsync/rename semantics, WAL over 9p or NTFS) are explicitly unproven
  here; do not extrapolate.

## Known lossy projection

`usage_counters` (search hit counts) live in memory-cache.db for locality
but are **not** rebuildable from Markdown; a rebuild resets them to zero.
Canonical-query equivalence deliberately excludes them. If usage history
must survive a cache rebuild, it belongs in operations.db (or an
append-only usage log) instead — this is a spike finding, not a decision.

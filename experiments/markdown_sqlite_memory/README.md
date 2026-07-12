# Markdown-authority / SQLite-projection memory spike

**Status: EXPERIMENT ONLY.** This directory is an isolated architecture spike.
It is not wired into the RelayLM production runtime, it does not modify current
RelayMEM/SLP storage behavior, and no production module imports it. All fixtures
are synthetic. The Markdown syntax (`relaymem-spike` v0) is experimental and
does not imply final production syntax.

## Candidate model under test

| Store | Role | Rebuildable? |
| --- | --- | --- |
| Markdown pages (`pages/*.md`) | Steady-state canonical authority for durable MEM content and user-visible organization, including active/hidden lifecycle state | It is the source |
| `memory-cache.db` | Parsed blocks, digests, tags, source refs, relations, lifecycle projection and FTS5 | Yes — delete and compile again from Markdown |
| `operations.db` | Jobs, claims/leases, retries, intents, idempotency, receipts, lifecycle tombstones, durable usage events and failures | No — operational authority; holds no MEM content |
| vector/graph indexes | Out of scope; same rebuildable-projection class as the cache | Yes by construction |

SQLite may persist on disk without becoming the MEM-content authority. The
authority rule is behavioral: deleting `memory-cache.db` must not lose committed
MEM, lifecycle state, or durable usage history. Markdown reconstructs content
and organization; `operations.db` preserves non-rebuildable operational facts.

## Lifecycle contract validated across Tracks B, C and D

- **Forget is reversible hide**, not physical deletion.
- Forget commits a new Markdown block revision with `status: hidden`.
- Normal active search excludes the block immediately after cache refresh.
- A durable tombstone blocks automatic re-formation while hidden.
- **Restore** commits a new `status: active` revision and clears the tombstone in
  the same receipt transaction.
- **Purge is a separate irreversible operation and is not implemented by this
  spike.** Neither `forget` nor `restore` removes the canonical block.

This matches the current lifecycle characterization tests and the Memory
Explorer mock. It also avoids using one ambiguous “delete” operation for hide
and physical erasure.

## Commit protocol

A MEM mutation is committed at one event: the `operations.db` transaction that
makes the apply receipt durable, after the Markdown revision write, digest
verification and cache refresh have succeeded.

1. Reconcile in SQLite: idempotency, tombstone, duplicate and contradiction
   checks; render the Markdown post-image and record `pre_digest`/`post_digest`.
2. Durably record an apply intent in `operations.db`.
3. Under the `operations.db` `BEGIN IMMEDIATE` apply mutex:
   - verify the file still matches `pre_digest`;
   - atomically replace it using same-directory temp write, fsync, rename and
     directory fsync.
4. Verify `post_digest` and refresh the cache.
5. In one operations transaction, write the receipt and idempotency row, apply
   the tombstone insert/delete, mark the job applied and remove the intent.

Recovery reads the durable intent and current file digest:

- `pre_digest`: the replace did not happen; return to pending or failed.
- `post_digest`: roll forward cache/receipt/tombstone work without re-rendering.
- anything else: a foreign writer changed the page; fail the job and rebuild
  the projection from Markdown.

The same failure matrix is tested for formation, Forget and Restore.

## Durable usage history

Memory Explorer needs last-use time and usage history. Those values cannot be
reconstructed from Markdown content, so they are not cache authority.

Search now writes content-free `memory_usage_events` to `operations.db`:

- stable block ID;
- event kind;
- query-plan digest, not query text;
- occurrence time.

Counts and last-used timestamps are derived from these events. Deleting and
rebuilding `memory-cache.db` preserves the usage result as long as
`operations.db` remains. The old experimental `usage_counters` cache table is
not read or written by the corrected path and is not an authority; a production
schema should omit it or regenerate any aggregate exclusively from usage
events.

## Search boundary

`SearchPlanner` is a bounded protocol for a future LLM-backed planner. The spike
uses a deterministic planner only. Terms and result limits are clamped; SQL,
table names and mutation authority are not exposed to a planner. Search reads
the cache and records only content-free usage events.

## Commands

```bash
python -m pytest experiments/markdown_sqlite_memory/tests

python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike init-fixture --pages 5 --blocks 8
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike build-cache
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike search kw1x2 --kind fact
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike apply-candidate \
  --candidate-id c1 --page notes.md --content "a durable memory"
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike forget --block-id blk_p0b1
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike restore --block-id blk_p0b1
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike recover
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike verify
python experiments/markdown_sqlite_memory/run_spike.py --root /tmp/spike benchmark --pages 20 --blocks 25
```

## Findings

Supported at Linux spike scale:

- Markdown/cache rebuild equivalence for canonical MEM queries;
- incremental page projection;
- bounded FTS/metadata search;
- deterministic recovery for all tested crash windows;
- stale-snapshot rejection;
- reversible Forget/Restore with durable re-formation prevention;
- durable usage history independent of the rebuildable cache;
- explicit schema versions and refusal of unsupported newer schemas.

Constraints observed:

- SQLite write locks are not fair; a multi-worker design needs explicit
  fairness/backoff policy.
- Page-granular digests serialize writers to a hot page.
- fsync bounds apply throughput; batching is needed for large imports.
- This validates a single-host design, not multi-host concurrent writers.
- Windows/WSL durability, WAL behavior and timing remain unproven. In WSL,
  tests should use the Linux filesystem rather than `/mnt/c`.

## Adoption boundary

This spike demonstrates technical feasibility; it does not authorize production
migration. Production adoption still requires an accepted storage proposal,
current-data migration plan, backup/restore procedure, full characterization
suite, Windows/WSL testing and a hard cutover with no permanent dual authority.

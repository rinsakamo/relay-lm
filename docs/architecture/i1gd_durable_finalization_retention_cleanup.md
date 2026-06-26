# I1-GD Durable-finalization retention and cleanup

Status: **implemented production boundary**

Authority: this document defines the completed I1-GD maintenance contract for
`relaymem.slp_durable_finalization.v0` evidence after I1-GB publication and
I1-GC completion convergence. It does not redefine the evidence or completion
schemas and does not prove I1-GE.

## Production boundary

One call to
`maintain_relaymem_slp_durable_finalization_retention(...)` performs one bounded,
non-recursive pass:

```text
configured durable-finalization root
  -> secure fd-relative bounded inventory
  -> deterministic locator grouping and ordering
  -> exact state classification
  -> shared I1-GC nonblocking per-record fence
  -> canonical reread
  -> retain | isolate | cleanup | blocked
  -> directory durability
  -> bounded content-free result
  -> return
```

The boundary does not sleep, poll, recurse, rediscover replay work, invoke I1-GC,
or execute a queue job.

## Record-state matrix

| State | Required evidence | I1-GD action |
| --- | --- | --- |
| `fresh_incomplete` | valid base and optional ordered segments, no seal, age below orphan grace | retain |
| `expired_incomplete_orphan` | valid incomplete evidence, age at or above orphan grace | isolate, then remove known components |
| `sealed_pending` | exact valid sealed evidence, no valid completion | retain indefinitely for I1-GC/O1B replay |
| `complete_retained` | exact valid seal and matching valid completion, age below completed retention | retain |
| `complete_retention_expired` | exact valid seal and matching valid completion, age at or above completed retention | isolate, then remove evidence and completion |
| `isolated_retained` | valid isolation marker below isolated retention | finish partial cleanup and retain marker |
| `isolated_retention_expired` | valid isolation marker at or above isolated retention | finish cleanup, then remove marker last |
| `corrupt_known_locator` | corrupt known canonical component or impossible known combination | isolate before removing known components |
| `unsupported_known_locator` | known locator with unsupported schema | isolate before removing known components |
| `unsafe_or_unclassifiable` | symlink, hardlink, special file, unstable inode/type/metadata, noncanonical name, or unknown ownership | fail closed; do not mutate |
| `ambiguous` | conflicting identity or marker collision | fail closed; do not mutate |
| lock busy | I1-GB/I1-GC/another maintenance owner holds the exact fence | bounded skip |

A sealed record without completion is never deleted or isolated because of age,
capacity pressure, or repeated maintenance passes.

## Retention clock

Retention uses the newest stable `mtime` among the canonical components currently
participating in classification. `atime` is not used. Isolation retention uses
the stable isolation-marker `mtime`.

The caller may inject a wall-clock provider for deterministic tests. Future-dated
metadata, negative/non-finite age, metadata changes during reread, and backward
clock movement block early deletion.

## Isolation schema

I1-GD adds the runtime-private schema:

```text
relaymem.slp_durable_finalization_isolation.v0
```

The immutable marker includes only:

```text
runtime_private = true
content_included = false
record_kind = isolation
record_revision = 0
locator_digest
sealed_record_schema
classification
reason_id
bounded boolean component flags
isolation_digest
```

It contains no conversation content, namespace, run/session/turn/job/dispatch
value, lineage object, path, raw exception, downstream result, or public
projection value.

The filename is a reserved non-segment member of the existing logical-record
namespace:

```text
durable-finalization-v0-<locator>.segment-isolation.json
```

This placement is deliberate. The current I1-GC canonical segment inventory
rejects it as an unexpected component. Therefore, after isolation publication,
I1-GC fails closed even when a crash leaves base/segments/seal beside the marker.
Only I1-GD recognizes the exact reserved filename as an isolation marker.

Exact marker republish converges as a duplicate. Different valid content at the
same locator is an identity collision and blocks cleanup.

## Cleanup ordering

Every destructive cleanup follows this order:

```text
canonical classification under the shared fence
  -> immutable isolation marker no-clobber publish
  -> marker-file fsync and directory fsync
  -> exact canonical isolation reread
  -> stable known-component preflight
  -> secure component unlink with canonical reread semantics
  -> directory fsync
  -> retain isolation marker
  -> after isolated retention, verify no components remain
  -> delete isolation marker last
  -> directory fsync
```

Base, segment, seal, and completion are never removed before the isolation marker
is durable and exactly reread. The per-record lock file is never removed.

## Crash convergence

The normal recoverable interrupted state is:

```text
valid isolation marker
+ zero or more remaining known components
```

A later pass reacquires the exact shared fence, rereads the marker and components,
and continues cleanup forward. It does not roll back the marker or infer mutation
success from an exception string.

Production fault seams cover:

- after inventory, before lock;
- after lock, before reread;
- after isolation publication, before reread;
- after isolation reread, before first unlink;
- during component cleanup;
- after component cleanup, before directory fsync;
- after directory fsync, before return;
- during isolation deletion;
- after isolation deletion, before directory fsync.

## Shared fence ownership

I1-GD does not introduce a separate lock namespace. The shared boundary delegates
to the exact I1-GC per-record fence:

```text
.durable-finalization-replay-v0-<locator>.lock
flock(LOCK_EX | LOCK_NB)
```

The same filename, unsafe-file rejection, no-follow behavior, fsync-on-create,
and open-inode lifetime are preserved. Busy is a non-destructive bounded skip.
The lock file remains after evidence and isolation retention cleanup so mutual
exclusion cannot split across old and newly created inodes.

## Inventory and security model

Inventory is private-root validated, fd-relative, non-recursive, deterministic,
and bounded before classification. A capacity-exceeded inventory does not infer
absence and performs no cleanup. Recognized logical records are sorted by locator
digest, and at most the configured per-pass count is processed.

Reads and deletes require regular files, link count one, `O_NOFOLLOW`, bounded
size, and stable device/inode/type/size/mtime across open/read/pre-unlink checks.
Symlinks, hardlinks, directories, FIFOs, sockets, devices, path escapes,
noncanonical names, duplicate JSON keys, noncanonical JSON, non-finite values,
oversized files, and unstable objects fail closed.

Known publication temporary files are recognized but retained by the initial
production boundary; I1-GD does not weaken active-writer safety to reclaim them.

## Content-free result

The bounded result exposes only status, gates, inventory/processing counts,
retained/isolated/cleaned counts, lock-busy/blocked counts, capacity/timeout flags,
and bounded reason IDs. `repr()` and log projection omit locator/digest/path,
identifiers, timestamps, raw content, raw messages, namespace, tokens, exception
text, and nested protected results.

## Configuration

All gates are independent from the I1-GB/I1-GC publication gate and default safe:

```yaml
relaymem_slp_durable_finalization_retention_enabled: false
relaymem_slp_durable_finalization_retention_dry_run_only: true
relaymem_slp_durable_finalization_retention_apply_enabled: false
relaymem_slp_durable_finalization_completed_retention_seconds: 604800
relaymem_slp_durable_finalization_orphan_grace_seconds: 86400
relaymem_slp_durable_finalization_isolated_retention_seconds: 2592000
relaymem_slp_durable_finalization_cleanup_max_records_per_pass: 64
relaymem_slp_durable_finalization_cleanup_timeout_ms: 5000
```

Dry-run performs inventory, classification, and content-free projection only.
Apply requires enabled, not dry-run-only, apply enabled, and a valid absolute
pre-existing private root with positive bounded values.

## Downstream non-mutation

I1-GD does not create, repair, update, or remove:

- C1-5 protected source artifacts;
- B2 queue records;
- B3 lifecycle transitions;
- C2 execution state;
- C1-2 worker or M3a-M3h output;
- Correct/Forget state;
- SOUL state.

A valid completion marker remains only I1-GC's proof that the exact sealed record,
C1-5 protected source, and B2 queue correlation converged in source-before-queue
order. It is not B3 terminal success, worker execution, Primary MEM formation,
semantic quality, or later retrieval use.

## Validation matrix

The dedicated I1-GD smoke covers default-off and dry-run gates, incomplete/orphan
classification, sealed-pending retention, exact completion validation, isolation
duplicate/collision handling, interrupted cleanup convergence, marker-last
retention, shared-fence contention, unsafe-file rejection, bounded processing,
future clock handling, replay exclusion after isolation, content leakage checks,
and I1-GA/I1-GB/I1-GC regressions.

## Remaining boundaries

I1-GD completes retention and cleanup only. The following remain unimplemented:

- I1-GE full crash-at-every-boundary production validation;
- O1B replay discovery and delegation;
- O1C queued-work discovery;
- scheduler polling, daemonization, and service supervision.

Current I1-G status is therefore **in progress**: I1-GA through I1-GD are
complete, while I1-GE remains unimplemented.

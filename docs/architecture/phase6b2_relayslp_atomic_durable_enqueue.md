---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6b2_relayslp_atomic_durable_enqueue
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6-B2 durable enqueue storage contract changes
  - Phase 6-B3 claim lease retry or terminal-state helper lands
  - queue backend or record schema changes
relaylm_not_authoritative_for:
  - RelayMEM memory meaning or memory-write idempotency
  - worker RelaySLP execution
  - claim lease retry or terminal-state mutation
  - page index or log apply
  - RelaySOUL mutation
  - request-runtime wiring
relaylm_related_authority:
  - phase6_async_relayslp_bounded_slice.md
  - phase6a2_relayslp_response_handoff_contract.md
  - phase6b0_relayslp_durable_queue_contract.md
  - phase6b1_relayslp_dispatch_preflight.md
  - relaymem_slp_current_target.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# Phase 6-B2 RelaySLP Atomic Durable Enqueue

## Status

Phase 6-B2 is implemented as a default-off, dry-run-first, helper-only atomic durable enqueue boundary.

```text
exact runtime-private B1 result
  -> exact B1 durable-job candidate revalidation
  -> secure queue-root inspection
  -> existing record classification or durable timestamp assignment
  -> atomic create-if-absent publication
  -> content-free queue status projection
```

B2 does not invoke a scheduler, worker, RelaySLP, RelayMEM apply helper, or RelaySOUL mutation. It is not request-runtime wired and cannot change or delay the already-finalized visible response.

## Public helper

```python
enqueue_relaymem_slp_durable_job(
    preflight_result,
    queue_root=...,
    enabled=False,
    dry_run_only=True,
    apply_enabled=False,
)
```

The related schemas remain:

```text
relaymem.slp_dispatch_preflight.v0
relaymem.slp_durable_enqueue.v0
relaymem.slp_durable_job.v0
relaymem.slp_queue_status_projection.v0
relaymem.slp_dispatch_key.v0
relaymem.slp_job_id.v0
```

Actual create-if-absent publication requires all three explicit gates:

```text
enabled = true
apply_enabled = true
dry_run_only = false
```

The defaults perform no write. With `enabled=true` and either `dry_run_only=true` or `apply_enabled=false`, B2 securely inspects the queue root and any existing identity record but does not create a record.

## Exact B1 consumption

B2 accepts only an exact in-process `RelayMEMSLPDispatchPreflightResult` with one exact `RelayMEMSLPDurableJobCandidate`.

The B1 result must still be the successful dry-run shape:

```text
status = dry_run_ready
enabled = true
dry_run_only = true
source_candidate_valid = true
response_finalized = true
durable_job_count = 1
durable_job_created = true
blocked_reasons = []
```

All B1 queue-I/O, enqueue, duplicate, worker, RelaySLP, memory-write, SOUL-mutation, and visible-response side-effect flags must remain false.

B2 revalidates the exact runtime field sets, strict bool/int distinctions, dispatch key, job ID, source identity, initial queue state, retry defaults, and absence of pre-populated durable timestamps. A mapping returned by `to_runtime_dict()`, a public projection, trace record, frontend metadata object, or lookalike class is rejected.

## Queue identity and storage layout

The queue identity is the B1 `dispatch_idempotency_key`. A RelayMEM memory-write idempotency key is never accepted as queue identity.

The caller supplies one dedicated absolute `queue_root` directory. B2 does not create the queue root or derive it from frontend input. The queue root and every path component must already exist as real directories.

The deterministic filename is:

```text
slp-dispatch-v0-<64 lowercase hexadecimal dispatch digest>.json
```

The filename is derived only from the validated dispatch key. No run ID, session ID, namespace, lineage value, raw content, caller filename, or memory-write key participates in path construction.

## Canonical durable record

For a new record, B2 copies the exact validated B1 candidate and assigns one UTC timestamp to both:

```text
created_at
updated_at
```

The timestamp is assigned only inside the gated B2 apply attempt. It uses an RFC 3339 UTC representation ending in `Z`. B2 does not accept a caller-supplied durable timestamp.

The record is encoded as UTF-8 compact canonical JSON with:

```text
ensure_ascii = true
sort_keys = true
separators = (",", ":")
allow_nan = false
no trailing newline
```

Unknown fields, missing fields, duplicate JSON keys, malformed UTF-8, malformed JSON, non-canonical bytes, unsupported schemas, strict-type violations, impossible initial state, invalid timestamps, dispatch-key mismatch, or job-ID mismatch fail closed.

## Atomic create-if-absent publication

B2 uses a same-directory temporary regular file and no-clobber publication:

1. create a private temporary file with `O_CREAT | O_EXCL | O_NOFOLLOW`,
2. write the complete canonical record bytes,
3. `fsync` and verify the temporary file,
4. atomically hard-link the temporary inode to the deterministic final filename,
5. re-open and strictly verify the final record,
6. `fsync` the queue directory,
7. unlink the temporary name and `fsync` the directory again.

The hard-link step is the uniqueness constraint. It cannot replace an existing final record. A concurrent winner is inspected and classified under the same duplicate/collision/corruption rules.

B2 never truncates, replaces, repairs, or rewrites an existing queue record.

## Existing record classification

The B0 outcome vocabulary is implemented:

```text
enqueued_new
duplicate_existing
blocked_collision
blocked_corrupt
write_failed
```

### `enqueued_new`

A new exact record was atomically published and the containing directory was durably synchronized.

### `duplicate_existing`

The existing record is strict, canonical, and has the same canonical dispatch identity fields. Operational fields excluded from dispatch identity, including source-admission, runtime-terminal, and persistence-policy status, do not create a second record and do not overwrite the existing record.

### `blocked_collision`

The deterministic dispatch filename contains a record that claims the same dispatch key but has different canonical dispatch identity fields. It is not accepted as a duplicate and is not overwritten.

### `blocked_corrupt`

The existing path is a symlink, unexpected file type, oversized record, malformed UTF-8/JSON, duplicate-key JSON, non-canonical encoding, schema drift, impossible state, invalid timestamp, or otherwise fails strict record validation. Corrupt records are not repaired or overwritten.

### `write_failed`

The queue root cannot be securely opened, a temporary file cannot be fully written and synchronized, atomic publication fails, final verification fails, or directory durability cannot be confirmed. A failure after publication may report `enqueue_applied=true` while retaining `write_failed`; retry safely converges through exact duplicate classification.

## Filesystem fail-closed boundary

B2 walks the absolute queue root from its filesystem anchor with directory file descriptors. Every component is checked with `follow_symlinks=false`, opened with `O_DIRECTORY | O_NOFOLLOW`, and inode-matched before use.

B2 rejects:

- relative or control-character-bearing queue roots,
- missing queue roots,
- symlinked queue-root components,
- non-directory queue-root components,
- final-record symlinks,
- directories, devices, FIFOs, sockets, or other unexpected final types,
- records that change inode while being read,
- path escape or caller-controlled final filenames.

Platforms without the required secure dirfd operations fail closed.

## Content-free projection

The public/default projection remains `relaymem.slp_queue_status_projection.v0` and includes only allowlisted state/status/count/boolean fields and bounded reason IDs.

It excludes:

- durable record bodies,
- B1 and B2 runtime-private candidates or results,
- job and dispatch identifiers,
- run, turn, session, namespace, and lineage values,
- queue-root and record paths,
- exact durable timestamps,
- claim owner and lease tokens,
- memory-write idempotency keys,
- raw content of any kind.

The optional `PipelineNodeResult` uses node name `relaymem_slp_durable_enqueue` and marks the private queue record as omitted.

## Visible-response independence

B2 is a detached post-finalization helper boundary. Enqueue success or failure must not:

- replace or downgrade the selected HTTP success,
- rewrite or append visible response text,
- delay stream completion while persistence is attempted,
- invoke a synchronous memory-write fallback,
- trigger TTS, audio, Live2D, or avatar execution.

Request-runtime wiring is still absent. A future caller must preserve this independence rather than synchronously gating ordinary visible response delivery on B2.

## Preserved non-goals

Phase 6-B2 does not:

- create or configure the queue root,
- scan unrelated queue records,
- claim work or create lease tokens,
- renew or recover leases,
- increment attempts, claim generations, or record revisions,
- perform retry release or terminal transitions,
- invoke a scheduler, worker, RelaySLP, or RelayMEM persistence apply,
- write Primary or Secondary MEM,
- update MEM pages, index, or log,
- mutate RelaySOUL,
- wire request runtime,
- change visible response delivery,
- execute TTS, audio, Live2D, or avatar behavior.

## Validation

```bash
python -m compileall -q \
  relaylm/relaymem_slp_durable_enqueue.py \
  scripts/relaylm_phase6b2_durable_enqueue_smoke.py \
  scripts/relaylm_phase6b2_durable_enqueue_security_smoke.py \
  scripts/relaylm_phase6b2_durable_enqueue_contract_smoke.py

PYTHONPATH=. python scripts/relaylm_phase6b0_durable_queue_contract_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b1_dispatch_preflight_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b1_dispatch_preflight_security_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b2_durable_enqueue_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b2_durable_enqueue_security_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b2_durable_enqueue_contract_smoke.py
```

Coverage includes default-off and dry-run-first gates, exact direct B1 consumption, strict bool/int rejection, dispatch/job identity re-derivation, canonical timestamped records, no-clobber publication, exact duplicate convergence, operational-field identity exclusions, collision and corruption classification, symlink and unexpected-file rejection, malformed UTF-8/JSON and schema drift, non-canonical bytes, queue-root path safety, content-free projections, and absence of worker/MEM/SOUL/visible-response side effects.

## Next bounded slice

Phase 6-B3 may add claim, lease, retry-release, stale-recovery, and terminal-state helpers over strict B2 records. B3 must remain separate from worker execution and must preserve revision, claim-generation, and lease-token fencing from the B0 contract.

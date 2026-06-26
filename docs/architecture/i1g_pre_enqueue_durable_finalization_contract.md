---
relaylm_doc_type: contract
relaylm_authority: i1g_pre_enqueue_durable_finalization_contract_publication_and_replay_target
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - I1-GB durable-finalization publication lands
  - I1-GC one-record replay lands
  - I1-GD retention or cleanup semantics change
  - I1-GE production crash-smoke evidence lands
  - O1B sealed-record discovery lands
  - I1-B finalized-turn identity or response-finalization order changes
relaylm_not_authoritative_for:
  - I1-GC restart replay and completion-marker production behavior
  - I1-GD retention and cleanup production behavior
  - I1-GE full crash-at-every-boundary proof
  - O1 scheduler discovery polling fairness or service lifecycle
  - C1-5 protected-source schema or persistence semantics
  - B2 or B3 queue schema and lifecycle semantics
  - C1-0 C1-2 C2 or M3a-M3h worker and memory semantics
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c2_one_queued_primary_worker_integration.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - o1a_two_lane_scheduler_contract.md
  - pipeline_implementation_plan.md
  - post_i3_evaluation_work_roadmap.md
---
# I1-G Pre-enqueue Durable-finalization Contract and Fault Model

## Status and authority

I1-GA is complete as the **contract, design decision, pure fault model, and validation boundary**. I1-GB is complete for bounded durable base/segment/seal publication and response-release admission. I1-GC restart replay/completion convergence, I1-GD retention/cleanup, and I1-GE full production crash validation remain unimplemented; I1-G overall is in progress.

O1A now defines only the scheduler-side two-lane round contract. Future O1B will discover at most one eligible sealed record, canonically reread it, and call I1-GC once. O1A/O1B do not own replay/completion and do not call C1-5 or B2 directly.

The canonical target is one **turn-scoped sealed durable-finalization publication record**, schema `relaymem.slp_durable_finalization.v0`. It is runtime-private, bounded, integrity-bound evidence. It is not a general journal, worker outbox, second queue, or second memory lifecycle.

## Problem statement

Current ordinary managed requests in explicit I1-GB apply mode use:

```text
backend response
  -> final safe visible response / parsed SSE unit
  -> exact I1-B source and A1 -> A2 -> B1 preparation
  -> private base/segment/seal publication and canonical reread
  -> HTTP body, protected SSE unit, or terminal completion release
  -> Starlette background finalizer
       -> canonical C1-5 durable protected-source commit
       -> canonical B2 content-free durable enqueue
       -> optional process-local hot cache
```

```text
Window A publication side — implemented by I1-GB
  restart evidence is durable before protected visible release

Window A recovery side — I1-GC unimplemented
  process exits after seal but before C1-5/B2
    -> sealed evidence exists
    -> no production one-record restart replay/completion marker yet

Window B — resolved
  C1-5 protected source committed
    -> B2 queue record committed
    -> process exits before/during worker execution
    -> C1-5 + B3 + C2 + C1-2 restart convergence
```

I1-G as a whole closes Window A; I1-GB implements publication admission, while I1-GC is still required for restart replay and completion convergence. Window B, B3 lifecycle, C1-5 claim-time rehydration, C1-2, and M3a-M3h remain unchanged.

## Current versus target path

```text
current through I1-GB apply mode:
  ordinary finalization -> private durable evidence -> visible delivery
    -> process-local background finalizer -> C1-5 source -> B2 queue

remaining target through I1-GC/I1-GD:
  ordinary finalization
    -> recoverable durable-finalization evidence
    -> visible response remains content-independent
    -> restart-safe publication through canonical C1-5 then canonical B2
    -> exact duplicate convergence
    -> durable completion marker
    -> bounded cleanup
```

For non-stream, the complete record is sealed before body release. For stream, each bounded append-only segment is durably committed before its corresponding visible bytes are yielded, and the final seal is durable before terminal completion (`[DONE]` or normal EOF) is released. The contract does not claim atomic remote-client receipt; it guarantees RelayLM does not intentionally release a server-visible unit before restart evidence for that unit exists.

## Chosen design and rejected alternatives

| Candidate | Assessment | Decision |
|---|---|---|
| Generic durable outbox | Works for a complete non-stream item, but a post-finalization item cannot cover already-yielded stream chunks without buffering; risks duplicating B2/B3 | Rejected |
| Global append-only journal | Stream-safe, but adds global ordering, cursor, compaction, and corruption domains unrelated to one turn | Rejected |
| Durable finalized-turn publication record | Turn-scoped, bounded, stream-capable, and hands exact I1-B material to existing C1-5/B2 | **Selected** |
| Reuse C1-5, B2, or RelayRUN | C1-5 needs finalized capture/B1 identity, B2 must stay content-free, RelayRUN is not protected finalized-turn authority | Rejected |

The selected record may use immutable same-directory files and per-record append-only segments internally. There is still one production path: every sealed record converges through C1-5 then B2.

## Authority diagram

```text
request runtime
  -> I1-B finalized-turn content and A1/A2/B1 identity
  -> I1-G durable-finalization evidence/completion
  -> C1-5 protected-source authority
  -> B2 content-free queue publication
  -> B3 queue lifecycle
  -> C2 one queued-record coordination
  -> C1-0 / C1-2 claim-time source and worker
  -> M3a-M3h Primary MEM formation/persistence
```

| Boundary | Input | Output | Owns | Does not own |
|---|---|---|---|---|
| Request runtime | managed request, backend result, final safe output | transport units and finalization inputs | request/transport lifecycle | queue, worker, memory |
| I1-B | exact request-local context and final visible content | finalized source and exact B1 candidate | finalized-turn meaning and production identity | I1-G storage, queue lifecycle, MEM writes |
| I1-G | exact I1-B material and release evidence | sealed/complete record and content-free projection | Window-A evidence, replay eligibility, completion/retention classification | B3, worker, memory lifecycle |
| C1-5 | exact protected capture plus B1 correlation | durable source and claim-time rehydration | protected-source persistence/integrity/cleanup | queue publication/lifecycle |
| B2 | exact B1 result | canonical content-free queue record | create-if-absent publication and duplicate/collision classification | claim/retry/terminal and content |
| B3 | canonical B2 record plus fenced request | queue transition | claim, lease, retry, stale recovery, terminal | source, worker, MEM |
| C2 | one selected exact queued record | one claim/rehydrate/execute result | coordination only | discovery/scanner/service lifecycle |
| C1-0/C1-2 | current claim and fresh source/scope | one fenced worker outcome | source correlation and execution | selection and memory meaning |
| M3a-M3h | validated worker source | page/index/log/recovery evidence | Primary MEM formation/persistence | dispatch and finalization replay |
| O1A/O1B | bounded scheduler opportunity and selected locator | one bounded replay-lane result | scheduling/discovery only | replay, C1-5, B2, B3, worker, MEM |

Relevant current production modules and test seams are:

```text
relaylm/relaymem_slp_durable_finalization_record.py
relaylm/relaymem_slp_durable_finalization_store.py
relaylm/relaymem_slp_durable_finalization_publication.py
relaylm/relaymem_slp_runtime_finalization.py
relaylm/relaymem_slp_finalized_turn_source.py
relaylm/relaymem_slp_runtime_enqueue.py
relaylm/relaymem_slp_durable_runtime_enqueue.py
relaylm/relaymem_slp_protected_source_store.py
relaylm/_relaymem_slp_protected_source_artifact.py
relaylm/relaymem_slp_durable_enqueue.py
relaylm/relaymem_slp_queue_record.py
relaylm/relaymem_slp_queue_state.py
relaylm/relaymem_slp_one_queued_job_runner.py
relaylm/relaymem_slp_primary_worker_source.py
relaylm/relaymem_slp_primary_worker_source_registry.py
```

## Canonical record/state contract

```text
schema_version = relaymem.slp_durable_finalization.v0
runtime_private = true
content_included = true
```

One logical record target consists of immutable evidence and markers. I1-GB implements base, segments, and seal only; completion and cleanup/isolation lifecycle authority remain later slices:

```text
base record             exact run/turn/character correlation
zero or more segments   stream only; bounded, append-only, hash-chained
seal marker             exact finalized turn + exact B1 job/dispatch identity
completion marker       exact C1-5 + B2 convergence verified
isolation marker        bounded control evidence only
```

Minimal derived states:

| State | Meaning | Replayable | Auto-delete |
|---|---|---:|---:|
| `incomplete` | no valid seal | no | only after strict expiry proof |
| `sealed` | valid seal, no completion | yes | no |
| `complete` | valid completion bound to seal | no | after retention floor |
| `isolated` | corrupt, unsupported, collision, or invariant violation | no | no |

These are not B3 queued/claimed/retry/terminal states and do not describe memory formation.

The private storage locator is a deterministic digest over exact I1-B run-local correlation (`schema + run_id + turn_index + character_id`). It is only a locator, never job, dispatch, lineage, lease, or memory-write identity. The seal records the exact B1-produced job and dispatch identities.

The private payload may contain exact bounded finalized-turn evidence. Queue records remain content-free. Integrity binds schema/markers, locator inputs, base, ordered segments/hash chain, complete finalized payload, exact B1 identity, character correlation, and revision under canonical serialization.

`record_revision` is bounded optimistic concurrency for I1-G markers only. Timestamps are retention hints, never identity, ordering, duplicate, replay, or completion authority.

`complete` means only: valid seal; exact C1-5 artifact validated; exact B2 record validated against the same B1 identity; source-before-queue preserved; completion marker durably committed and reread. It does not mean B3 terminal or Primary MEM formed.

Unknown schemas/fields, duplicate JSON keys, malformed UTF-8/JSON, noncanonical bytes, bad hash chain, revision mismatch, symlink/path escape, unsafe file type, identity/content collision, and impossible marker combinations fail closed into isolation. They are not repaired, overwritten, replayed, or automatically deleted.

## Commit point and response independence

A sealed turn has restart-replay evidence only after seal publication, directory durability, canonical reread, and identity/integrity validation. Production restart replay and completion convergence are not available until I1-GC.

In apply mode:

- non-stream requires a valid durable seal before body release;
- stream requires a valid durable segment before each yield and a valid seal before terminal completion;
- disabled/dry-run preserves current behavior and therefore does not close Window A.

Durability may add bounded pre-release latency. It may not modify selected visible bytes, invoke M3a-M3h or a worker inline, or wait without configured byte/count/time bounds.

A failure before any byte is released is a pre-delivery finalization failure, not a rewrite of an already-visible response. A failure after partial stream delivery leaves released bytes unchanged, stops further unprotected release, and leaves an incomplete non-replayable record.

Publication success requires atomic publication, directory durability, canonical reread, expected revision, and integrity validation. A rename/fsync exception is uncertain: success is never inferred. I1-G completion requires canonical C1-5 and B2 rereads plus durable completion-marker reread.

## Publication ordering

```text
private base commit/reread
  -> each stream segment commit/reread before yield
  -> exact I1-B finalized source
  -> existing A1/A2/B1 builders
  -> seal commit/reread with exact B1 identity
  -> non-stream body or stream terminal completion release
  -> original finalizer or one-record restart replay
       -> canonical C1-5 persist/converge
       -> canonical B2 enqueue/converge
       -> exact correlation reread
       -> completion marker commit/reread
  -> later bounded cleanup
```

The source-before-queue invariant is absolute:

```text
valid C1-5 protected source durable
  before
claimable canonical B2 queue record
```

## One-record replay algorithm

1. Accept one caller-selected deterministic record locator; do not scan.
2. Securely open the root and acquire a nonblocking per-record exclusive lock.
3. Canonically reread base, segments, seal, completion, and isolation markers.
4. Complete -> `safe_noop/already_complete`; do not republish.
5. Incomplete -> `not_replayable`; never invent final content.
6. Isolated/corrupt/unsupported/unsafe -> no mutation or replay.
7. Validate schema, revision, segment chain, seal digest, run/turn/character correlation, and stored exact B1 identity.
8. Rebuild the exact I1-B source and invoke existing A1/A2/B1 builders. Require exact equality with sealed B1 identity; never generate substitutes.
9. Inspect C1-5: absent -> publish; exact equivalent -> continue; corrupt/unsafe/different content -> isolate.
10. Inspect B2: absent with exact source -> canonical B2; exact existing -> continue; collision/corrupt/unsafe -> isolate.
11. Queue present while source absent -> invariant violation; never fabricate source or delete queue.
12. Ambiguous C1-5/B2 result -> canonical reread; never infer success.
13. Verify exact job/dispatch/character correlation and source-before-queue.
14. If B3 is terminal, do not transition/execute it; exact source+queue correlation may finish I1-G.
15. Commit completion with expected revision/no-clobber, fsync, canonical reread, release lock, return a content-free result.

No retry loop, sleep, polling, scanner, daemon, or worker execution belongs in this helper.

## O1B caller boundary

Future O1B is outside I1-GC. It may perform one bounded non-recursive discovery, secure eligibility classification, deterministic one-candidate selection, canonical reread, and one I1-GC call. It must not:

```text
reconstruct protected content
call C1-5 or B2 directly
decide completion independently
pass replay output directly to C2
extract job/dispatch identity for the queue lane
scan repeatedly, sleep, retry, or execute a worker
```

O1A orders replay before queue. After replay, the queue lane must independently discover the queue root. Same-round execution of a newly converged B2 record is possible but neither guaranteed nor specially prioritized.

## Idempotency and duplicate convergence

- Exact replay uses the same I1-B/B1 identity and converges to one C1-5 artifact and one B2 record.
- Same I1-G locator plus different protected content is collision/manual isolation.
- C1-5 equivalent-existing and B2 `duplicate_existing` count only after exact reread.
- Original finalizer and concurrent replays use a per-record lock; C1-5/B2 no-clobber remains cross-process uniqueness authority.
- Dispatch identity is never memory-write identity.
- I1-G completion suppresses only finalization replay; it does not replace B3/C1-2/M3 idempotency.

## Retention and cleanup

| Class | Required handling | Automatic deletion |
|---|---|---|
| incomplete | bounded TTL, never replay | only after reread proves no seal/source/queue |
| sealed pending | retain until complete/isolate | no |
| complete | retain through audit floor | yes after exact reread |
| source orphan / no queue | replay B2 or retain | only after completion/proven no-queue path |
| queue / no source | invariant violation | never |
| corrupt/unsupported/isolated | preserve for operator | never |

Cleanup begins only for exact complete records after the retention floor. Failure sets `cleanup_required` and never rolls back visible response, C1-5, B2/B3, worker, or memory state. Batch count, bytes, age, and operation duration are bounded. Disk pressure never evicts sealed pending, corrupt, isolated, or uncertain records.

## Public content-free projection

Target schema: `relaymem.slp_durable_finalization_projection.v0`.

Allowed fields:

```text
schema_version enabled dry_run_only apply_enabled outcome_status failure_stage
reason_ids record_present sealed replayable source_present queue_present complete
cleanup_required bounded_segment_count bounded_attempt_count
```

Forbidden everywhere public, in logs, exceptions, repr, stdout/stderr, traces, browser, and SOUL Lab: user/assistant text; governed title/summary/body; namespace; run/session/job/dispatch/lineage/idempotency identities; paths; digests; lease token; exact timestamps; raw exception; nested protected result.

O1 scheduler projections may expose only bounded replay-lane status/booleans. They do not embed this projection, the locator, or the private I1-GC result.

## Required fault matrix

| # | Fault point | Durable artifacts present | Queue state | Visible effect | Restart action | Duplicate risk | Cleanup | Status/reason | Classification |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | before finalized-turn production | none | none | no protected release | no replay | none | none | `not_created/finalized_turn_unavailable` | safe no-op |
| 2 | before durable record creation | none | none | no release in apply | no replay | none | none | `publication_failed/record_not_created` | safe no-op |
| 3 | temp write | temp only | none | no release | discard proven temp | none | temp cleanup | `publication_failed/temp_write_failed` | cleanup required |
| 4 | before/after replace | temp/final uncertain | none | wait for reread | canonical reread | exact only | proven temp | `publication_uncertain/canonical_reread_required` | retryable replay |
| 5 | directory fsync uncertain | final may exist | none | no success/unprotected release | reread/retry durability | exact | retain | `publication_uncertain/directory_durability_unconfirmed` | retryable replay |
| 6 | before visible delivery | seal or segment | none | unchanged | replay sealed | exact | later | `evidence_ready/visible_release_pending` | idempotent continue |
| 7 | after visible delivery | seal/covered units | none | released bytes unchanged | replay sealed; incomplete no replay | exact | TTL/normal | `replay_pending/post_release_interruption` | retryable replay |
| 8 | before source publication | sealed | none | none | one-record replay | exact | retain | `replay_pending/source_not_published` | retryable replay |
| 9 | source after commit / before B2 | seal+source | none | none | verify then B2 | exact C1-5 duplicate | retain | `replay_pending/queue_not_published` | idempotent continue |
| 10 | B2 ambiguous failure | seal+source; queue unknown | unknown | none | canonical B2 reread | exact B2 duplicate | retain | `replay_pending/queue_outcome_uncertain` | retryable replay |
| 11 | B2 `enqueued_new` before completion | seal+source+queue | queued/later | none | verify/complete | marker duplicate | later | `completion_pending/queue_published` | idempotent continue |
| 12 | exact `duplicate_existing` | seal+source+queue | canonical existing | none | verify/complete | none logical | normal | `completion_pending/exact_duplicate` | idempotent continue |
| 13 | completion write | marker uncertain | any canonical | none | completion reread | exact marker | temp | `completion_uncertain/completion_reread_required` | retryable replay |
| 14 | complete before cleanup | complete + downstream | any | none | safe no-op | none | after floor | `complete/cleanup_pending` | cleanup required |
| 15 | cleanup failure | complete remains | unchanged | none | no replay | none | bounded retry | `complete/cleanup_failed` | cleanup required |
| 16 | restart double replay | sealed | absent/existing | none | lock+reread | exact only | normal | `converged/concurrent_replay` | idempotent continue |
| 17 | original finalizer/replay race | sealed | absent/existing | none | lock+C1-5/B2 convergence | exact only | normal | `converged/finalizer_replay_race` | idempotent continue |
| 18 | two replay processes | sealed | absent/existing | none | one lock winner | exact only | normal | `retryable/replay_lock_busy` | retryable replay |
| 19 | same identity/different content | conflicting evidence | unknown | reject conflicting release | isolate | collision | retain | `isolated/content_collision` | manual isolation required |
| 20 | corrupt/truncated record | invalid evidence | unknown | stop protected release | no replay | unknown | retain/isolate | `corrupt/record_invalid` | corruption / invariant violation |
| 21 | unsupported schema | unsupported record | unknown | stop protected release | no replay | unknown | retain/isolate | `isolated/schema_unsupported` | manual isolation required |
| 22 | symlink/path escape/unsafe type | unsafe evidence | unknown | fail closed | no follow/replay | unknown | isolate | `corrupt/unsafe_path_or_type` | corruption / invariant violation |
| 23 | root missing | none | none | no apply release | operator repair | none | none | `blocked/root_missing` | manual isolation required |
| 24 | permission denied | none/uncertain | none/unknown | no unprotected release | reread after repair | exact | retain | `blocked/permission_denied` | manual isolation required |
| 25 | disk full/capacity | none/proven partial | none | bounded backpressure | retry after repair | exact | proven temp only | `retryable/capacity_exhausted` | retryable replay |
| 26 | stale retention expiry | incomplete/sealed/complete | absent/existing | none | classify by reread | exact | proven classes only | `retention/classified_at_expiry` | cleanup required |
| 27 | source exists / queue absent | seal+source | none | none | canonical B2 | exact source duplicate | retain | `replay_pending/orphan_source` | idempotent continue |
| 28 | queue exists / source absent | seal+queue/no source | claimable/later | none | never fabricate/delete; isolate | unsafe | operator only | `invariant_violation/queue_without_source` | corruption / invariant violation |
| 29 | terminal B3 stale replay | seal+source+queue | terminal | none | no transition/worker; complete I1-G if exact | none | normal | `converged/downstream_terminal` | safe no-op |
| 30 | leakage canary | any private | any | no mutation | public output must omit | none | none | `projection_valid/content_free` | safe no-op |

## Security invariants

Roots are absolute, pre-existing, runtime-private, and permission-protected. Components are opened without following symlinks and inode/type checked. Temp/final files are bounded private regular files with same-directory publication. Canonical JSON rejects duplicate keys, malformed/noncanonical data, unknown fields, and non-finite values. Filenames contain no protected content. Repr/projections omit content/private identities. Capacity is checked before accepting protected bytes. Uncertain evidence is retained rather than deleting material that may correlate to a claimable queue.

## Current I1-GB configuration

I1-GB adds these exact default-off top-level settings:

```yaml
relaymem_slp_durable_finalization_enabled: false
relaymem_slp_durable_finalization_dry_run_only: true
relaymem_slp_durable_finalization_apply_enabled: false
relaymem_slp_durable_finalization_root:
relaymem_slp_durable_finalization_max_record_bytes: 524288
relaymem_slp_durable_finalization_max_segment_bytes: 65536
relaymem_slp_durable_finalization_max_segment_count: 256
relaymem_slp_durable_finalization_max_record_count: 1024
relaymem_slp_durable_finalization_publication_timeout_ms: 5000
```

Apply requires the exact `true/false/true` gate combination, an absolute pre-existing non-symlink private root, and valid positive bounds. Dry-run validates/prepares but writes no evidence and does not block response release. Retention deadlines and cleanup cadence are intentionally absent until I1-GD. No setting enables a scanner, daemon, or retry loop.

O1A target scheduler field names are contract-only. They are not current `RelayLMConfig` fields and do not elevate these I1-G gates.

## Implementation slices and dependencies

### I1-GA — complete

Contract/design decision, authority/schema/commit/replay/retention/projection/security model, deterministic 30-point fault model, leakage smoke, and minimal documentation indexing. No production runtime behavior.

### I1-GB — durable-finalization publication — complete

Implements the private record/store/publication modules, immutable base/segment/seal publication, strict canonical validation, pure exact A1/A2/B1 preparation reused by the background finalizer, bounded stream pre-yield and non-stream pre-release admission, and content-free projections. C1-5/B2 schemas and source-before-queue semantics are unchanged. No restart replay, completion marker, scanner, worker, or cleanup is added.

### I1-GC — one-record replay and duplicate suppression

Implement one caller-selected sealed-record replay through existing I1-B builders, C1-5, and B2; add per-record fencing, canonical reread, exact duplicate convergence, and completion marker. No discovery or service lifecycle.

### O1A — two-lane scheduler contract — complete as contract only

Defines replay-before-queue round ordering, one opportunity/delegation per lane, independent queue rediscovery after replay, lane-local failure isolation, pure idle/run-next/stop disposition, target-only scheduler gates, and content-free projection. It adds no production scan, I1-GC invocation, polling, sleep, config, CLI, or runtime behavior.

### O1B — sealed-record discovery — unimplemented

Will perform bounded secure discovery, deterministic one-candidate selection, canonical reread, and one I1-GC delegation. It will not own replay convergence.

### I1-GD — retention, orphan reconciliation, and cleanup

Implement bounded classification/cleanup for incomplete, sealed, complete, orphan, corrupt, unsupported, and isolated records. No continuously running scanner.

### I1-GE — production crash-at-every-boundary integration smoke

Add deterministic production fault injection around base/segment/seal, visible release, C1-5, B2 ambiguity, completion, concurrency, restart, retention, and leakage for non-stream and stream. Depends on I1-GB through I1-GD.

O1C through O1F remain later operations slices. I1-G owns no polling cadence, queue selection, fairness, daemon, or supervised execution.

## Validation plan

```bash
python -m compileall relaylm scripts
PYTHONPATH=. python scripts/relaylm_o1a_two_lane_scheduler_contract_smoke.py
PYTHONPATH=. python scripts/relaylm_i1g_pre_enqueue_fault_model_smoke.py
PYTHONPATH=. python scripts/relaylm_i1gb_durable_finalization_publication_smoke.py
PYTHONPATH=. python scripts/relaylm_i1gb_durable_finalization_app_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6_runtime_enqueue_source_capture_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6_runtime_enqueue_app_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_durable_protected_source_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b2_durable_enqueue_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b3_queue_state_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c2_one_queued_job_runner_ci_runner.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
```

The current canonical C2 runner replaces the proposed but nonexistent `relaylm_phase6c2_one_queued_primary_worker_integration_smoke.py` filename.

## Explicit non-goals after I1-GB / O1A

I1-GB does not implement I1-GC one-record restart replay, completion markers, sealed-record discovery, directory scanning, I1-GD retention/cleanup/orphan reconciliation, I1-GE full crash proof, C1-5/B2/B3 schema changes, queue scanning, scheduling, daemon or supervised service lifecycle, inline worker execution, M3a-M3h/retrieval changes, SOUL Lab changes, CORS/auth changes, queue content, public private identities/paths, or browser-visible protected payloads.

O1A does not implement O1B/O1C production discovery or delegation, O1D fairness/backoff/jitter, O1E stale recovery/cancellation/shutdown, O1F operational validation, a scheduler loop, config/CLI wiring, a daemon, or always-on operation.

## I1-GC durable-finalization replay current boundary (2026-06-26)

This section supersedes earlier statements in this file that describe I1-GC as pending.

I1-GC is implemented as a caller-selected, one-record production convergence authority:

```text
sealed I1-G evidence
  -> exact finalized-turn source reconstruction
  -> existing A1 / A2 / B1 preparation
  -> exact sealed job / dispatch identity verification
  -> canonical C1-5 protected-source convergence
  -> canonical B2 queue convergence
  -> exact downstream reread and correlation verification
  -> immutable completion marker
  -> content-free replay result
```

The normal I1-GB background finalizer and restart replay share the same nonblocking,
cross-process, deterministic per-locator fence. Completion is published only after
canonical reread proves exact C1-5 source-before-B2 queue correlation. A terminal B3
record may satisfy that downstream proof without mutation, but I1-G completion does
not mean B3 terminal success, worker execution, or Primary MEM formation.

Duplicate, race, uncertain-write, and restart paths converge by canonical reread.
`queue exists / source absent`, identity mismatch, collision, corruption, unsupported
schema, symlink, hardlink, and unsafe file type fail closed. Public projections remain
content-free and omit locator, digest, path, namespace, job, dispatch, lineage,
timestamp, lease token, protected payload, and raw exception values.

O1A remains the completed pure replay-then-queue scheduler-round contract. It does not
discover records or invoke I1-GC. Future O1B may discover and delegate one exact sealed
record to this authority without owning completion semantics.

Still incomplete and intentionally out of scope:

- I1-GD retention, orphan reconciliation, isolation lifecycle, and cleanup
- I1-GE full crash-at-every-boundary production validation
- O1B sealed-record discovery and one I1-GC delegation
- O1C through O1F production queue discovery, ordering, fairness, recovery, and validation
- O2 supervised always-on worker service
- B3 transition, C2/worker execution, M3a-M3h, and SOUL Lab UI from replay

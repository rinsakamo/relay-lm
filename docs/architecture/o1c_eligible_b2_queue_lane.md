---
relaylm_doc_type: implementation_handoff
relaylm_authority: o1c_eligible_queue_lane
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_related_authority:
  - docs/architecture/o0_local_one_job_runner.md
  - docs/architecture/o1a_two_lane_scheduler_contract.md
  - docs/architecture/phase6b3_relayslp_queue_state_helpers.md
  - docs/architecture/phase6c2_one_queued_primary_worker_integration.md
---
# O1C Eligible B2/B3 Queue-Lane Discovery

## Status

O1C is complete as one bounded production queue-lane adapter. It connects the O1A queue-lane opportunity to the existing Phase 6-C2 one queued-job adapter without creating a scheduler round, polling loop, daemon, or second queue lifecycle.

```text
configured B2/B3 queue root
  -> one bounded non-recursive secure discovery
  -> exact queue filename recognition and canonical B3 validation
  -> queued/due/future classification
  -> lexicographic one-candidate selection
  -> canonical selected-record reread
  -> server-owned character and store resolution
  -> exact C2 request construction
  -> at most one C2 delegation
  -> O1A-compatible queue LaneOutcome
  -> return
```

The public production entry point is:

```python
run_relaymem_slp_scheduler_queue_lane_once(
    *,
    config: RelayLMConfig,
    gates: SchedulerGates,
    now: datetime | None = None,
    fault_injector: Callable[[str], None] | None = None,
) -> LaneOutcome
```

## Ownership

O0 remains the explicit operator command boundary. It owns CLI parsing, content-free CLI projection, exit categories, and one process invocation.

O1A remains the pure deterministic replay-before-queue round contract. It validates already-bounded lane outcomes and derives `stop`, `run_next_round`, or `idle`; it does not invoke O1C itself.

O1C owns only queue inventory, eligibility classification, deterministic selection, canonical reread, server-owned scope resolution, exact C2 request construction, one C2 call, and bounded queue-lane mapping.

B3 remains sole authority for claim CAS, record revision, claim generation and owner, lease state, retry release, stale recovery, and terminal transition.

C2 remains sole integration authority for B3 claim, C1-5 durable protected-source rehydration, fresh C1-0 source preparation, C1-2 worker execution, retry or terminal convergence, and terminal-only protected-source cleanup.

## Shared O0-compatible helper

`relaylm/relaymem_slp_queue_candidate.py` is the single production source for:

- lower O0 worker-gate validation;
- configured absolute-root validation;
- secure bounded queue discovery;
- future-retry observation;
- lexicographic candidate selection;
- canonical selected-record reread;
- namespace-to-character and character-store resolution;
- fresh source-registry and exact C2 request construction.

`relaylm/local_worker_once.py` now consumes this helper while retaining its existing request schema, CLI options, optional explicit character assertion, projection fields, exit categories, exit codes, and private test seams. The shared helper owns no CLI behavior, scheduler aggregation, C2 invocation loop, or queue mutation.

## Gate intersection

O1C receives exact O1A `SchedulerGates` from its caller and also honors the existing lower O0/C2 gates in `RelayLMConfig`.

```text
scheduler disabled or queue lane disabled
  -> no discovery and no C2

lower local worker disabled or invalid
  -> bounded failed outcome, never no-work

scheduler dry-run + lower apply
  -> C2 dry-run

scheduler apply + lower dry-run
  -> C2 dry-run

scheduler apply + lower apply
  -> C2 apply
```

The scheduler gate cannot elevate a lower dry-run gate. O1C adds no scheduler configuration fields; O1B or a later integration slice must own shared scheduler configuration.

## Root and inventory security

Queue, protected-source, and configured memory roots are server-owned absolute paths. Queue discovery uses the existing `open_queue_root()` secure dirfd walk and a nonblocking shared queue-root advisory lock.

One invocation performs one non-recursive inventory. Every directory entry counts toward `relaymem_local_worker_discovery_max_entries`, including nonmatching names. Exceeding the cap fails closed before selection; partial inventory is never used.

The accepted queue filename grammar is:

```text
slp-dispatch-v0-<64 lowercase hex>.json
```

Every grammar-matching object is read through existing storage and record authorities. Symlinks, hardlinks, non-regular objects, oversized data, malformed or noncanonical JSON, duplicate keys, invalid schema, identity mismatch, filename mismatch, or unstable inode/type fail closed. O1C never repairs, renames, removes, or isolates a queue object.

## Eligibility matrix

| Canonical state | Retry time | O1C behavior |
| --- | --- | --- |
| `queued` | absent or due | eligible candidate |
| `queued` | future | future hint only |
| `claimed` | any | no immediate queue work |
| terminal | any | no immediate queue work |
| invalid or unsafe | any | fail closed |

When no due candidate exists but at least one future queued record exists, O1C returns `future_retry_only` with `future_work_hint_present=true`. The earliest future timestamp may be retained only in runtime-private state. It is never projected, converted into a delay, slept on, or used to define backoff or jitter.

## Deterministic v0 selection

Due candidates are sorted by canonical queue filename in ascending lexicographic order and the first is selected. This is a stable O0-compatible v0 ordering only. It is not FIFO, fairness, age priority, starvation prevention, semantic priority, or retry priority.

## Canonical reread

The discovery snapshot is not C2 authority. After selection, O1C independently reopens the queue root, reacquires the existing shared lock, and rereads the same canonical filename.

The reread must preserve device and inode, bytes, canonical mapping, schema and identity, queued state, record revision, claim generation, and due retry state. Missing, replaced, changed, claimed, terminal, revised, regenerated, future-shifted, or corrupt candidates are not delegated.

The queue-root lock is released before C2. A later race is resolved only by B3 claim CAS; O1C adds no reservation file, owner marker, or global correctness lock.

## Character and store scope

O1C accepts no operator or browser character assertion. It resolves the selected record namespace against server-owned `model_routes` whose character exists in `characters`.

- zero matching characters fails;
- multiple matching characters fails as ambiguous;
- exactly one character is passed to `resolve_relaymem_character_store_root()` with the configured memory root.

The namespace is never used as a character ID or path component.

## Exact C2 request

Every delegation constructs a fresh `RelayMEMSLPPrimaryWorkerSourceRegistry` using the existing configured bounds and builds one exact `RelayMEMSLPOneQueuedJobRunnerRequest` containing:

- the exact canonical reread record;
- server-resolved character and character-partitioned store root;
- configured queue and protected-source roots;
- existing local-worker claim owner, lease duration, and protected-source artifact bound;
- effective dry-run/apply gates from the safe intersection.

O1C reconstructs no source content. C1-5 durable protected-source persistence remains restart authority.

## C2 result mapping

O1C maps C2 result booleans and bounded reason IDs into the O1A queue status vocabulary.

- `dry_run_ready` -> `dry_run_ready`;
- terminal worker result -> `terminal`;
- retry release or retryable worker result -> `retry_released`;
- nonterminal invoked worker -> `executed`;
- cleanup still required -> `cleanup_required`;
- bounded claim conflict or lost claim -> `candidate_changed`;
- retryable source failure -> `failed` with `retryable=true`;
- blocked/unsafe source state -> bounded `unsafe_state` or `failed`;
- invalid, disabled, or worker failure -> `failed`.

`mutation_may_have_occurred` is true when C2 reports a performed claim, worker invocation, queue transition, terminal state, or cleanup requirement. Raw C2 results remain runtime-private and are excluded from equality, repr, and public projection.

## Same-round replay independence

O1A orders replay before queue, but O1B output is never handed directly to O1C. When replay converges a new B2 record, O1C may observe it only by independently opening and scanning the queue root, applying the normal selection rule, performing canonical reread, and constructing its own C2 request.

Same-round execution is possible but not guaranteed, and replay-created records receive no special priority.

## Concurrency and races

Two O1C calls, or O0 and O1C, may select the same queued record. Both converge on the same C2/B3 authority; one claim CAS can win and the other receives a bounded conflict or changed result.

B2 enqueue during discovery follows current bounded directory-iteration semantics. Retry-time changes between scan and reread become `candidate_changed`. Stale claim recovery and terminal-cleanup retries are not performed by O1C.

## Content-free boundary

The public lane outcome contains only bounded booleans, status, and approved reason IDs. It never exposes namespace, character value, job or dispatch identity, revision, generation, claim owner, lease token, retry timestamp, filename, roots or paths, protected content or digest, memory content, run/session/turn identity, raw request/result, raw exception, or config value.

## Validation

Dedicated functional and security smokes cover gate intersection, empty/future/due classification, cap overflow, non-recursive inventory, lock contention/failure, corrupt and hostile objects, deterministic selection, canonical reread races, unique/ambiguous scope, fresh registry construction, exact request fields, C2 mapping, fault seams, content leakage, real terminal execution, and no second-candidate fallback.

The O1C workflow also runs O0, O1A, B2, B3, C1-5, C1-2, C2, compileall, documentation-boundary, and documentation-link regressions.

## Non-goals and next boundaries

O1C does not implement:

- O1B sealed I1-G discovery and one I1-GC replay delegation;
- O1D ordering, fairness, retry-delay policy, backoff, or jitter;
- O1E stale recovery, cancellation, or graceful shutdown;
- O1F operational crash, concurrency, saturation, and leakage validation;
- O2 supervised worker service;
- O3 always-on operation;
- polling, sleeping, scheduler-round recursion, worker pools, daemon lifecycle, browser API, or new CLI authority.

O1C completion therefore does not mean the production scheduler, automatic continuous processing, fair scheduling, stale recovery, supervised service, or always-on operation is complete.

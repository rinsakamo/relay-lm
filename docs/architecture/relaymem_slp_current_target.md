---
relaylm_doc_type: current_target_boundary
relaylm_authority: relaymem_relayslp_current_target
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - RelayMEM or RelaySLP producer consumer boundary changes
  - Phase 6 deferred orchestration slice lands
  - durable MEM persistence apply state changes
  - ordinary-runtime worker integration changes
relaylm_not_authoritative_for:
  - repository-wide phase sequencing
  - exact RelayMEM or RelaySLP schemas
  - RelaySOUL approval contracts
relaylm_related_authority:
  - phase6_async_relayslp_bounded_slice.md
  - phase6a1_relayslp_job_admission_contract.md
  - phase6a2_relayslp_response_handoff_contract.md
  - phase6b0_relayslp_durable_queue_contract.md
  - phase6b1_relayslp_dispatch_preflight.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - relaymem_m3d_primary_writer_handoff.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_execution_design.md
  - memory_lifecycle_design.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# RelayMEM / RelaySLP Current / Target Boundary

## Current implemented boundary

### RelayMEM retrieval

Current RelayMEM provides bounded read-only store discovery, Primary/Secondary layout compatibility, retrieval priority, runtime-private snippet selection, content-free retrieval projection, and gated RelayCTX injection.

Current retrieval remains a usable foundation rather than proof of newly formed runtime memory. Existing durable pages can be retrieved, but the ordinary request runtime does not yet create new Primary MEM through a Phase 6 worker.

### RelayMEM Primary formation and persistence

Current direct/helper boundaries include:

```text
M3a formation candidate
M3b source lineage and write preflight
M3c deterministic Primary page candidate
M3d writer handoff and store-target preflight
M3e atomic no-clobber page publication
M3f read-only index/log reconciliation plan
M3g gated index-before-log reconciliation apply
M3h read-only receipt/store recovery audit
```

M3e can publish one exact Primary page. M3g can reconcile the bounded index/log state with retryable partial progress. M3h can inspect the M3g receipt and current store to classify no recovery, retryable reconciliation, manual confirmation, or future journal-aware recovery candidacy.

These boundaries are not request-runtime or worker wired. They are not evidence that ordinary turn-end memory formation is active.

### Phase 6 deferred orchestration

Current Phase 6 provides:

- A1 helper-only job admission,
- A2 helper-only finalized-turn handoff,
- B0 durable queue/state-machine contract,
- B1 helper-only deterministic dispatch/job-record candidate,
- B2 direct-helper atomic durable enqueue.

The implemented sequence is:

```text
exact finalized-turn metadata
  -> A1 admission
  -> A2 runtime-private enqueue candidate
  -> B1 dispatch identity and queued durable-record candidate
  -> B2 create or classify durable queue record
```

Current Phase 6 still does not provide:

- automatic request-finalization invocation,
- claim or lease transitions,
- retry-release or stale-lease recovery,
- scheduler/background execution,
- worker invocation,
- RelayMEM M3a-M3h execution,
- next-turn recall validation.

### Compatibility status anchors

Phase 6-B1 implements the first exact consumer of the A2 runtime-private handoff and performs no queue I/O. The next bounded RelayLM Core implementation is Phase 6-B3, followed by request-runtime enqueue wiring and worker execution for the active integration milestone.

## Current compatibility constraints

- Retrieval may still consume historical compatibility-shaped inputs through existing wrappers.
- Current query preparation may use request messages.
- Target `v1` retrieval and SLP projections do not all have current producers.
- A1/A2/B1/B2 accept exact runtime-private artifacts and must not reconstruct them from public projection, frontend metadata, or visible response text.
- B2 durable queue records and M3e/M3g durable memory writes are separate explicit apply boundaries.
- RelayRUN checkpoint and recovery artifacts do not yet provide a general SLP worker resume executor.
- M3h is read-only evidence and cannot authorize repair or replay.

## Ownership boundary

### RelayMEM owns

- memory candidate meaning,
- safety scope and persistence eligibility,
- source lineage,
- memory-write idempotency,
- deterministic page content,
- page/index/log apply semantics,
- reconciliation and recovery classification,
- Secondary MEM consolidation meaning.

### Phase 6 / RelayRUN owns

- deferred dispatch admission,
- response-finalization handoff,
- dispatch identity,
- queue record lifecycle,
- claim/lease/retry/terminal control,
- worker invocation and stage correlation,
- restart and checkpoint integration.

### RelaySLP and SOUL

RelaySLP may read SOUL as a protected anchor and may later emit a separately governed RelaySOUL proposal candidate. RelaySLP must never directly mutate SOUL.

## Idempotency boundary

Dispatch idempotency and memory-write idempotency remain separate:

```text
Phase 6 dispatch idempotency
  prevents duplicate queue scheduling and execution

RelayMEM memory-write idempotency
  prevents duplicate durable memory application
```

A worker retry may be valid after a queue lease failure while a previously completed memory write remains deduplicated. Public projection must not expose either private identity domain.

## Active migration: Primary MEM end-to-end integration

The next migration is not another independent persistence helper. It is the ordinary runtime path:

```text
finalized ordinary turn
  -> request-runtime A1/A2/B1/B2
  -> B3 queue claim/lease/retry lifecycle
  -> worker invokes M3a-M3h
  -> verified durable Primary MEM
  -> later RelayMEM retrieval
  -> RelayCTX injection
  -> response uses formed memory
```

### Step 1: Phase 6-B3

Add bounded claim, lease, retry-release, stale-recovery, and terminal-state helpers over exact B2 records. B3 remains control-only and does not execute memory work.

### Step 2: request-runtime enqueue wiring

Invoke A1/A2/B1/B2 after ordinary managed response finalization without delaying or invalidating the visible response.

### Step 3: bounded Primary MEM worker

Claim one eligible job and invoke existing M3a-M3h boundaries in order. Do not duplicate memory semantics inside the worker.

### Step 4: next-turn recall

Verify that the newly durable memory is discovered through current retrieval and injected through RelayCTX for the correct character and namespace only.

### Step 5: SOUL Lab observation

Expose real latest-run, formed, held, blocked, and used-memory read projections through server-owned `/lab/api/*` routes. The browser remains non-authoritative.

## Target after the active migration

After the Primary MEM loop is proven, later target work includes:

- Secondary MEM consolidation,
- broader restart/retry and checkpoint integration,
- real correction/forget/pin/merge memory operations,
- RelaySOUL proposal handoff and separately governed apply,
- broader page/index/log recovery only when M3h operational evidence requires it.

Secondary MEM and SOUL execution are not prerequisites for proving the Primary MEM loop.

## Preserved invariants

Every migration step must preserve:

- visible response delivery does not wait for deferred processing,
- SLP failure does not invalidate an already valid response,
- default-off and dry-run-first rollout where applicable,
- fail-closed namespace, lineage, policy, and schema validation,
- protected content-bearing memory/SLP domains,
- content-free generic trace, public errors, and status projections,
- autonomous ordinary `free_to_update` memory only when RelayMEM gates pass,
- held or blocked handling for sensitive, contradictory, destructive, cross-namespace, or SOUL-affecting changes,
- separation between dispatch and memory-write idempotency,
- no direct RelaySOUL mutation.

## Completion interpretation

M3a-M3h completion means the Primary MEM primitives exist. B2 completion means a durable queue record can be created. Neither means the memory feature is end to end.

The active migration is complete only when an ordinary finalized turn can enqueue work, a worker can safely produce verified Primary MEM, and a later ordinary turn can retrieve and use it within the correct scope.

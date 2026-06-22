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
  - phase6b0_relayslp_durable_queue_contract.md
  - phase6b1_relayslp_dispatch_preflight.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# RelayMEM / RelaySLP Current / Target Boundary

## Current implemented boundary

RelayMEM currently provides bounded read-only store discovery, Primary/Secondary layout compatibility, retrieval priority, runtime-private snippet selection, content-free retrieval projection, and gated RelayCTX injection.

The direct/helper Primary MEM chain is implemented through:

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

M3a-M3h are not request-runtime or worker wired. Their completion does not mean ordinary turn-end memory formation is active.

Phase 6 currently provides A1 admission, A2 response-finalization handoff, B0 queue design, B1 dispatch/job-record preflight, B2 durable enqueue, and B3 fenced durable queue lifecycle helpers.

### Compatibility status anchors

Phase 6-B1 implements the first exact consumer of the A2 runtime-private handoff and performs no queue I/O.

Phase 6-B2 implements atomic durable enqueue behind explicit direct-helper gates.

Phase 6-B3 implements default-off, dry-run-first fenced `claim`, `renew_lease`, `retry_release`, `stale_recovery`, and `commit_terminal` operations over complete canonical B2 records. It performs no worker execution.

The next bounded RelayLM Core implementation is Phase 6-C worker execution under an exact active B3 lease fence.

## Current limitations

The current runtime still lacks:

- automatic request-finalization invocation of A1/A2/B1/B2,
- scheduler/background worker execution,
- Phase 6-C worker invocation under the B3 lease fence,
- worker invocation of M3a-M3h,
- proof that newly formed memory is retrieved in a later turn,
- Secondary MEM consolidation,
- real SOUL Lab memory APIs.

A1/A2/B1/B2/B3 must consume exact runtime-private artifacts and must not reconstruct them from public projection, frontend metadata, or visible response text. B2 queue records and M3e/M3g memory writes remain separate apply boundaries. B3 controls only queue metadata. M3h is read-only evidence and cannot authorize repair or replay.

## Ownership boundary

RelayMEM owns memory meaning, safety scope, source lineage, memory-write idempotency, deterministic page content, page/index/log apply semantics, recovery classification, and Secondary MEM consolidation meaning.

Phase 6 / RelayRUN owns dispatch admission, response-finalization handoff, dispatch identity, queue lifecycle, claim/lease/retry/terminal control, worker invocation, and restart/checkpoint integration.

RelaySLP may read SOUL as a protected anchor and may later emit a separately governed proposal. It must never directly mutate SOUL.

## Idempotency boundary

Dispatch idempotency and memory-write idempotency remain separate:

```text
Phase 6 dispatch idempotency
  prevents duplicate queue scheduling, active claim, and execution dispatch

RelayMEM memory-write idempotency
  prevents duplicate durable memory application
```

A worker retry may be valid while a previously completed memory write remains deduplicated. The B3 lease token and claim generation are execution fences, not memory-write idempotency keys.

## Active migration: Primary MEM end-to-end integration

```text
finalized ordinary turn
  -> request-runtime A1/A2/B1/B2
  -> B3 queue claim/lease/retry lifecycle
  -> Phase 6-C worker invokes M3a-M3h
  -> verified durable Primary MEM
  -> later RelayMEM retrieval
  -> RelayCTX injection
  -> response uses formed memory
```

The sequence is:

1. wire A1/A2/B1/B2 into finalized managed turns while preserving visible-response independence,
2. implement Phase 6-C worker execution under the exact active B3 owner/generation/token fence,
3. invoke existing M3a-M3h boundaries without redefining memory semantics,
4. validate later-turn recall with character and namespace isolation,
5. expose real latest-run and memory outcomes through server-owned SOUL Lab APIs.

B3 is complete as a prerequisite, but the Primary MEM loop remains integration pending.

## Target after the active migration

After the Primary MEM loop is proven, later work may add Secondary MEM consolidation, broader restart/retry integration, correction/forget/pin/merge APIs, RelaySOUL proposal handoff, and broader recovery only when M3h evidence requires it.

## Preserved invariants

Every migration step must preserve:

- visible response delivery does not wait for deferred processing,
- SLP failure does not invalidate an already valid response,
- default-off and dry-run-first rollout where applicable,
- fail-closed namespace, lineage, policy, schema, queue, and lease validation,
- protected content-bearing memory/SLP domains,
- content-free public diagnostics,
- autonomous ordinary memory only when RelayMEM gates pass,
- held or blocked handling for sensitive, contradictory, destructive, cross-namespace, or SOUL-affecting changes,
- separation between dispatch and memory-write idempotency,
- terminal-state immutability and exact lease fencing,
- no direct RelaySOUL mutation.

## Completion interpretation

M3a-M3h completion means the Primary MEM primitives exist. B2 completion means a durable queue record can be created. B3 completion means Phase 6-owned queue metadata can be safely claimed, renewed, released, recovered, and terminated. None of these alone means the memory feature is end to end.

The active migration is complete only when an ordinary finalized turn can enqueue work, a Phase 6-C worker can safely produce verified Primary MEM under a B3 lease, and a later ordinary turn can retrieve and use it within the correct scope.

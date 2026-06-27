---
relaylm_doc_type: implementation_handoff
relaylm_authority: wave2_cross_slice_convergence_record
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - wave3_cross_slice_convergence_audit.md
  - i1gd_durable_finalization_retention_cleanup.md
  - phase_i4c2_primary_forget_recovery_finalization.md
  - o1b_sealed_i1g_replay_lane.md
  - o1c_eligible_b2_queue_lane.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status after Wave 2
  - Wave 3 or Wave 4 completion
---
# Wave 2 cross-slice convergence audit

Status: W2-INT implementation and regression validation complete after merge. This document is frozen historical evidence for the Wave 2 boundary and Wave 3 start inputs.

Authority: this handoff records the combined latest-main boundary after PR #403, #404, #405, and #406, plus the I-4C2 follow-up correction merged as PR #407 while this audit was in progress. Lower dedicated contracts remain authoritative for their own schemas and mutations. Current post-Wave-3 status belongs to [Project Status](../PROJECT_STATUS.md) and [Wave 3 Cross-Slice Convergence Audit](wave3_cross_slice_convergence_audit.md).

## Integrated inventory

- I1-GD: PR #403, merge `cd78f3bb1b4ffb1ded086530b2575f82c36217bd`.
- I-4C2: PR #404, merge `97e5a1060bface993bb4382f9a50074aca1ec37d`.
- O1C: PR #405, merge `969a9e8ae1753ea5b6d0a803967e6ec03b18fde6`.
- O1B: PR #406, merge `4efea62c14de2babed9b1340c5b9c8f7c21459a1`.
- W2-INT start: `97e5a1060bface993bb4382f9a50074aca1ec37d`.
- Latest-main synchronization: PR #407, merge `c23b82da89853947eb5a2269760e24d7c25829c0`, containing the reviewed I-4C2 concurrent-loser normalization and documentation correction. W2-INT treats that merged result as upstream authority and does not duplicate the production file in its final diff.

## Cross-slice authority map

| Boundary | Owner | Consumers | Frozen rule |
|---|---|---|---|
| isolation schema, filename, parser, temporary-name grammar | I1-GD isolation module | O1B, I1-GD fence | direct import; no optional fallback or copied suffix |
| per-record replay/retention fence | I1-GC `_acquire_fence` through I1-GD fence wrapper | I1-GC, I1-GD | one nonblocking locator fence; no second retention lock |
| replay eligibility and one delegation | O1B | O1A aggregation | isolated evidence is never delegated |
| queue candidate discovery and C2 request construction | shared `relaymem_slp_queue_candidate` | O0, O1C | one filename/eligibility/reread/scope authority |
| lane invariants and round projection | O1A | future O1D1 | pure; no filesystem, clock, sleep, or invocation |
| Forget prepared resume, hidden continuation, M3f/M3g convergence, tombstone, exact replay | I-4C2 | I-4D | ordinary retrieval exclusion is not claimed |

## Isolation and replay convergence

O1B imports the I1-GD isolation parser, maximum size, temporary-name recognizer, and secure reader directly. A marker appearing after selection but before canonical reread maps to `candidate_changed` or `isolated`, depending on whether the canonical reread first observes the changed component set or validates the marker; both outcomes prohibit I1-GC delegation. An already isolated record is not eligible. I1-GC still fails closed on the reserved component. I1-GD and I1-GC share the exact record fence. Retention owns marker creation/removal and never delegates replay; O1B never mutates isolation.

## Lane and same-round convergence

The permanent functional smoke invokes O1B once, invokes O1C independently against the queue root, and passes only the two public `LaneOutcome` values to `aggregate_scheduler_round(invocation_order=("replay", "queue"))`. O1C has no replay-result parameter and rescans the queue root using normal lexicographic selection. Scheduler projections contain no locator, job, dispatch, claim, root, content, or private timestamp.

O1C preserves the regression that `source_retryable` maps to `failed`; `retry_released` is reserved for a canonical worker/C2 retry release.

## O0 compatibility

O0 and O1C continue to share `relaymem_slp_queue_candidate`. O1C-specific lane mapping remains outside the helper; O0 CLI arguments, request/projection schemas, optional character assertion, one-C2 bound, and exit semantics remain owned by O0 and are exercised by its dedicated workflow.

## I-4C2 / I-4D ownership freeze

I-4C2 owns exact prepared resume, deterministic hidden-successor continuation, operation-scoped M3f/M3g convergence, canonical page/control correlation, immutable tombstone publication, and exact response-loss replay. The public concurrent-loser normalization merged through PR #407 is: finalized hidden/none -> `already_hidden`; hidden prepared/recovery-required -> `target_not_active`; hidden/corrupt -> `target_corrupt`; active stale target -> `stale_revision`.

I-4D alone owns ordinary M2 lifecycle filtering, prior physical-revision exclusion, RelayCTX hidden exclusion, historical used-memory lifecycle projection, and fresh-conversation proof. Before I-4D, ordinary M2 behavior is unchanged and no hidden-exclusion completion is claimed.

I-4D may consume only read-only authority that resolves logical identity, canonical current physical revision, lifecycle `active|hidden`, mutation `none|prepared|recovery_required|corrupt`, a fail-closed retrieval-eligibility signal, and prior-revision-to-logical mapping. It must not inject Forget reason or tombstone content into retrieval context.

## Configuration boundary

I1-GD accepted configuration remains default-off, dry-run-first, strictly typed, bounded, and rooted in an absolute server-owned private directory. At the Wave 2 boundary, O1 scheduler field names are target-only and O1D1 is a future owner of accepted scheduler configuration. Current post-Wave-3 scheduler status belongs to the Wave 3 audit.

## Root and lock map

| Lock | Owner and scope | Hold boundary | Post-release authority |
|---|---|---|---|
| I1-G record fence | I1-GC; one locator; nonblocking | replay or I1-GD record mutation, plus I1-GD root mutation lock | canonical reread / retention reclassification |
| queue discovery advisory lock | shared queue discovery; queue-root inventory only | never across C2 delegation | B3 canonical claim/CAS and reread |
| B3 record transition lock | B3; one queue record | canonical claim/lease/transition | B3 state validator |
| Primary mutation lock | shared Correct/Forget coordinator; one logical memory | resolver validation and mutation commit/recovery | canonical current-state resolver |

No O1B root lock is held across I1-GC, no O1C discovery lock is held across C2, and no cross-root global correctness lock exists.

## Security, leakage, and regression proof

The W2 integration workflow runs compileall; I1-GD contract, functional, and race smokes; O1A; O1B and O1C functional/security suites; I-4C2 recovery, fault, concurrency, security, and ownership suites; the W2 functional/security smokes; documentation checks; and a clean-tree check.

The repository's existing path-triggered workflows remain the dedicated authorities for O0 CLI/security compatibility, B2/B3 queue state, C1/C2 worker behavior, I1-GB/I1-GC, I-3/I-4B/I-4C1, and related UI/runtime regressions. The latest-main-synchronized W2-INT head must pass both the integration workflow and all triggered dedicated workflows.

The combined security smoke checks authoritative isolation parsing, unsafe filesystem replacement, root separation, and content-free `repr`, node results, O1A projections, and bounded error mapping. Dedicated lower security suites retain symlink, hardlink, malformed-record, capacity, and ownership coverage.

## Frozen next-phase inputs

At the Wave 2 boundary:

- I1-GE may start after W2-INT is merged; it owns full process-exit/restart validation only.
- I-4D may start with I-4C2 complete, tombstone replay stable, and read-only lifecycle/current-identity authority frozen; it owns ordinary M2/RelayCTX exclusion only.
- O1D1 may start with O1A pure, O1B/O1C stable, manual aggregation green, and scheduler config still unaccepted; it owns accepted gates and one replay-before-queue production round returning without sleep.
- I-5A, I-7A/B, and UI-B1A may rely on the shared Primary mutation fence and frozen current-state schemas, but add no behavior in W2-INT.

## Remaining non-goals at Wave 2

I1-GE crash-at-every-boundary proof, I-4D retrieval exclusion, Forget API/UI, production scheduler round/loop, fairness/backoff, stale-claim orchestration, shutdown, soak, supervised service, always-on operation, and Pin/Held/Merge behavior remain outside Wave 2. Later completion is recorded by later wave documents.

# Wave 2 cross-slice convergence audit

Status: review candidate on `wave2-cross-slice-convergence-audit`.

Authority: this handoff records the combined latest-main boundary after PR #403, #404, #405, and #406. Lower dedicated contracts remain authoritative for their own schemas and mutations.

## Integrated inventory

- I1-GD: PR #403, merge `cd78f3bb1b4ffb1ded086530b2575f82c36217bd`.
- I-4C2: PR #404, merge `97e5a1060bface993bb4382f9a50074aca1ec37d`.
- O1C: PR #405, merge `969a9e8ae1753ea5b6d0a803967e6ec03b18fde6`.
- O1B: PR #406, merge `4efea62c14de2babed9b1340c5b9c8f7c21459a1`.
- W2-INT start: `97e5a1060bface993bb4382f9a50074aca1ec37d`.

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

O1B imports the I1-GD isolation parser, maximum size, temporary-name recognizer, and secure reader directly. A marker appearing before canonical reread maps to `isolated`; an already isolated record is not eligible. I1-GC still fails closed on the reserved component. I1-GD and I1-GC share the exact record fence. Retention owns marker creation/removal and never delegates replay; O1B never mutates isolation.

## Lane and same-round convergence

The permanent functional smoke invokes O1B once, invokes O1C independently against the queue root, and passes only the two public `LaneOutcome` values to `aggregate_scheduler_round(invocation_order=("replay", "queue"))`. O1C has no replay-result parameter and rescans the queue root using normal lexicographic selection. Scheduler projections contain no locator, job, dispatch, claim, root, content, or private timestamp.

O1C preserves the regression that `source_retryable` maps to `failed`; `retry_released` is reserved for a canonical worker/C2 retry release.

## O0 compatibility

O0 and O1C continue to share `relaymem_slp_queue_candidate`. O1C-specific lane mapping remains outside the helper; O0 CLI arguments, request/projection schemas, optional character assertion, one-C2 bound, and exit semantics remain owned by O0 and are exercised by its dedicated workflow.

## I-4C2 / I-4D ownership freeze

I-4C2 owns exact prepared resume, deterministic hidden-successor continuation, operation-scoped M3f/M3g convergence, canonical page/control correlation, immutable tombstone publication, and exact response-loss replay. The public concurrent-loser normalization is: finalized hidden/none -> `already_hidden`; hidden prepared/recovery-required -> `target_not_active`; hidden/corrupt -> `target_corrupt`; active stale target -> `stale_revision`.

I-4D alone owns ordinary M2 lifecycle filtering, prior physical-revision exclusion, RelayCTX hidden exclusion, historical used-memory lifecycle projection, and fresh-conversation proof. Before I-4D, ordinary M2 behavior is unchanged and no hidden-exclusion completion is claimed.

I-4D may consume only read-only authority that resolves logical identity, canonical current physical revision, lifecycle `active|hidden`, mutation `none|prepared|recovery_required|corrupt`, a fail-closed retrieval-eligibility signal, and prior-revision-to-logical mapping. It must not inject Forget reason or tombstone content into retrieval context.

## Configuration boundary

I1-GD accepted configuration remains default-off, dry-run-first, strictly typed, bounded, and rooted in an absolute server-owned private directory. O1 scheduler field names remain target-only: O1B/O1C receive typed `SchedulerGates`; O1D1 owns any future accepted scheduler configuration and one production round coordinator. No polling, sleep, fairness, backoff, or scheduler loop is introduced here.

## Root and lock map

| Lock | Owner and scope | Hold boundary | Post-release authority |
|---|---|---|---|
| I1-G record fence | I1-GC; one locator; nonblocking | replay or I1-GD record mutation, plus I1-GD root mutation lock | canonical reread / retention reclassification |
| queue discovery advisory lock | shared queue discovery; queue-root inventory only | never across C2 delegation | B3 canonical claim/CAS and reread |
| B3 record transition lock | B3; one queue record | canonical claim/lease/transition | B3 state validator |
| Primary mutation lock | shared Correct/Forget coordinator; one logical memory | resolver validation and mutation commit/recovery | canonical current-state resolver |

No O1B root lock is held across I1-GC, no O1C discovery lock is held across C2, and no cross-root global correctness lock exists.

## Security and leakage

The combined security smoke checks authoritative isolation parsing, symlink/hardlink rejection through dedicated suites, invalid gate and filename failure, root separation, and content-free `repr`, log dictionaries, node results, O1A projections, and exception mapping. Dedicated I1-GD, O1B, O1C, O0, C2, and I-4C2 security suites remain mandatory in the W2 workflow.

## Frozen next-phase inputs

- I1-GE may start after combined I1-GA/B/C/D regressions and isolation/replay race tests are green; it owns full process-exit/restart validation only.
- I-4D may start with I-4C2 complete, tombstone replay stable, and read-only lifecycle/current-identity authority frozen; it owns ordinary M2/RelayCTX exclusion only.
- O1D1 may start with O1A pure, O1B/O1C stable, manual aggregation green, and scheduler config still unaccepted; it owns accepted gates and one replay-before-queue production round returning without sleep.
- I-5A, I-7A/B, and UI-B1A may rely on the shared Primary mutation fence and frozen current-state schemas, but add no behavior in W2-INT.

## Remaining non-goals

I1-GE crash-at-every-boundary proof, I-4D retrieval exclusion, Forget API/UI, production scheduler round/loop, fairness/backoff, stale-claim orchestration, shutdown, soak, supervised service, always-on operation, and Pin/Held/Merge behavior remain unimplemented.

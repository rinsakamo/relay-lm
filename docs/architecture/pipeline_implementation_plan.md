---
relaylm_doc_type: implementation_plan
relaylm_authority: implementation_status_and_phase_sequencing
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - phase lands
  - sequencing changes
  - an integration milestone changes state
  - a target-only schema gains production wiring
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact schema details
  - historical MVP authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - pipeline_responsibility_design.md
  - current_target_migration_guide.md
  - post_i3_evaluation_work_roadmap.md
  - wave3_cross_slice_convergence_audit.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - i1gd_durable_finalization_retention_cleanup.md
  - i1ge_durable_finalization_crash_validation.md
  - phase_i4d_primary_retrieval_exclusion.md
  - o1d1_production_scheduler_round.md
---
# RelayLM Pipeline Implementation Plan

Last reviewed: 2026-06-27 JST

## Purpose

This document owns implementation status, dependency sequencing, and active integration priority. Component responsibility remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), exact behavior remains in dedicated contracts, and current/target interpretation remains in [Current / Target / Migration Guide](current_target_migration_guide.md).

## Status legend

- **complete**: bounded production contract and intended wiring exist with smoke coverage;
- **contract complete**: pure contract/model/smoke exists but production discovery or delegation does not;
- **defined target**: exact target exists but production behavior is incomplete;
- **unimplemented**: required production producer/consumer/apply/UI/validation is absent;
- **planned**: sequenced target after current dependency gates;
- **deferred**: intentionally outside the active milestone.

## Current position

```text
Phase 5-C managed-route correctness: complete through bounded v0/v1 apply and C5 plumbing
Phase 5-D pre-stream hardening: complete through D2
Phase 5.5 Stream Unpack / TTS handoff preparation: RelayLM Core complete

Phase 6 asynchronous RelaySLP orchestration:
  A0-A2: complete
  B0-B3: complete
  I1-B ordinary request-runtime enqueue/source capture: complete
  C1-0 through C1-5: complete
  C2 one-job claim/rehydrate/execute adapter: complete
  O0 local one-job runner: complete

RelayMEM Primary integration:
  M1/M2 and M3a-M3h: complete
  I1 next-turn recall and scope isolation: complete
  Phase I-2 observation: complete
  Phase I-3 Correct: complete
  Phase I-4A Forget / Hide contract: defined target
  Phase I-4B resolver/shared fence/read-only Forget boundary: complete
  Phase I-4C1 hidden-successor commit: complete
  Phase I-4C2 recovery/finalization: complete
  Phase I-4D retrieval exclusion: complete
  Phase I-4E API/UI: unimplemented
  Phase I-4F full validation: unimplemented
  Phase I-4 overall: in progress

SOUL Lab:
  UI-A0 through UI-A7: complete
  Phase I-2 real Observation: complete
  Phase I-3 auditable Correct: complete
  UI-B0 real Home conversation: complete
  UI-B1A lifecycle visibility: planned after W3-INT

Durability and operations:
  I1-GA contract / fault model: complete
  I1-GB durable publication / pre-release admission: complete
  I1-GC one-record replay / exact convergence / completion: complete
  I1-GD bounded retention / isolation / orphan cleanup: complete
  I1-GE validation-only full production crash proof: complete
  I1-G overall: complete
  O1A two-lane round / adapter / idle contract: contract complete
  O1B sealed replay-lane adapter: complete
  O1C eligible queue-lane adapter: complete
  O1D1 accepted gates and one production round: complete
  O1D2 fairness/retry-time/backoff/jitter/pacing policy: unimplemented
  O1E stale recovery/cancellation/shutdown: unimplemented
  O1F operational validation: unimplemented
  O1 overall: in progress
  O2 supervised worker service: planned/unimplemented
  O3 always-on local operation: planned/unimplemented

Wave 3 implementation tracks complete
W3-INT complete only after this PR is merged
Wave 4 not open while W3-INT is unmerged
```

## Completed foundation

Phase 5-C, Phase 5-D, Phase 5.5, Phase 6 A0-A2, B0-B3, I1-B, C1-0 through C1-5, C2, O0, Phase I-1, Phase I-2, Phase I-3, UI-B0, I-4B, I-4C1, I-4C2, I1-GA through I1-GE, O1A, O1B, O1C, and O1D1 are complete at their bounded production or contract boundaries.

### I1-E / Phase I-2: real SOUL Lab observation — complete

Observation evidence is read-only. Phase I-2 exposes latest-run, formed/held/blocked memory, and used-memory evidence through bounded SOUL Lab read models; it does not authorize repair or retrieval mutation.

Phase 6-C1-0 through C1-5 are complete. Phase 6-C2 one-job claim/rehydrate/execute adapter is complete.

C2 proves one exact queued record claim/rehydrate/execute integration. O0 supplies an explicit local caller and remains one-shot. O1D1 supplies one production scheduler round and remains one-shot: it does not poll, sleep, recursively launch rounds, supervise, recover stale claims, or implement fairness/backoff/jitter.

## I1-G durable-finalization track

```text
I1-GA  contract / fault model                                      complete
I1-GB  durable publication and bounded response-release admission complete
I1-GC  one-record restart replay, exact convergence, completion    complete
I1-GD  bounded retention, isolation, orphan cleanup               complete
I1-GE  validation-only crash-at-every-boundary production proof   complete
```

I1-G completion means sealed durable-finalization evidence through exact C1-5 source convergence, exact B2 queue convergence, downstream correlation, durable completion marker, bounded retention/isolation lifecycle, and full process-exit/fresh-restart validation. It does not mean B3 terminal success, C2 execution, worker execution, Primary MEM formation, semantic quality, retrieval use, automatic scheduling, polling, supervision, or always-on operation.

## Phase I-4 Forget / Hide track

```text
I-4A  target contract                                                defined target
I-4B  current-state resolver/shared fence/read-only preflight        complete
I-4C1 hidden-successor commit                                        complete
I-4C2 prepared recovery / tombstone finalization                     complete
I-4D  ordinary M2/RelayCTX lifecycle and prior-revision exclusion    complete
I-4E  loopback API and SOUL Lab Forget UI                            unimplemented
I-4F  crash/race/security/fresh-conversation validation              unimplemented
```

I-4D is retrieval-only integration. It consumes the existing current-state resolver before M2 snippet construction, excludes every non-current or non-eligible lifecycle result, and preserves historical receipts while overlaying current lifecycle read-only. It does not implement mutation routes, recovery, restore, purge, or UI. Phase I-4 overall remains in progress until I-4E and I-4F land.

## O1 automatic-operation track

```text
O1A   pure two-lane contract and content-free aggregation             contract complete
O1B   one eligible sealed-record discovery and I1-GC delegation       complete
O1C   one eligible B2 discovery and C2 delegation                     complete
O1D1  accepted gates and one production replay-before-queue round     complete
O1D2  deterministic ordering/fairness/retry-time/backoff/jitter       unimplemented
O1E   stale recovery, cancellation checkpoints, graceful shutdown      unimplemented
O1F   corruption/concurrency/saturation/restart/leakage validation    unimplemented
O2    supervised worker service                                       planned/unimplemented
O3    always-on local operation                                       planned/unimplemented
```

O1D1 accepts exactly five `StrictBool` scheduler fields and invokes O1B then O1C at most once each, aggregating through O1A and returning without sleep. It never passes replay-private locator/job/dispatch/candidate identity into O1C. Same-round replay-to-queue is possible only through independent queue-root rediscovery by O1C and normal C2 authority.

## Dependency-first execution waves

### Wave 0 — completed implementation foundation

```text
I1-GB durable-finalization publication
I-4B resolver/shared fence/read-only Forget
O1A scheduling and idle contract
```

### Wave 1 — completed commit, replay, and retention authorities

```text
I1-GC one-record replay and completion convergence
I1-GD retention/orphan reconciliation/isolation cleanup
I-4C1 hidden-successor commit ownership
I-4C2 prepared recovery and tombstone finalization
O1B sealed replay-lane adapter
O1C eligible queue-lane adapter
```

### Wave 2 — completed cross-slice convergence audit

```text
W2-INT audit of I1-GD, I-4C2, O1B, and O1C
phase-boundary reconciliation for Wave 3 inputs
```

### Wave 3 — implementation tracks complete, W3-INT pending merge

```text
I1-GE validation-only full process-exit/restart proof
|| I-4D ordinary M2/RelayCTX exclusion and historical lifecycle projection
|| O1D1 accepted scheduler gates and one replay-before-queue production round
-> W3-INT cross-slice convergence audit and shared documentation integration
```

### Wave 4 — not open until W3-INT merge

```text
O1D2 ordering/fairness/retry-time/backoff/jitter/pacing -> O1E stale recovery/cancellation/shutdown
I-4E API/UI -> I-4F validation
O1F operational validation
UI-B1A read-only lifecycle visibility
I-5A and I-7A/B contracts
```

The frozen Wave 4 start contracts are recorded in [Wave 3 Cross-Slice Convergence Audit](wave3_cross_slice_convergence_audit.md).

## Governance order after Phase I-4

```text
I-5 Pin / Unpin
  -> I-7 Held Apply / Discard
  -> I-6 Merge / Supersession
  -> I-8 Secondary MEM consolidation
  -> I-9 RelaySOUL proposal / intervention / rollback
```

## Product evaluation sequence

The explicit E1 path is complete across two separate proven lanes:

```text
explicit trusted scene-qualified managed request
  -> O0 one-job execution
  -> Primary MEM formation
  -> Phase I-2 observation
  -> Phase I-3 Correct

Home real conversation
  -> existing M2 / RelayCTX recall
  -> Home New Conversation
  -> corrected-memory question
  -> Phase I-2 used-memory evidence
```

Direct Home-origin formation remains unproven because UI-B0 does not send trusted scene-admission metadata. O1D1 adds one caller-invoked production round only; it does not make the loop recurring or always-on. Repeated automatic operation still depends on O1D2/O1E policy and later O2/O3 service work.

## Documentation completion rule

When a phase lands, update together:

- `docs/PROJECT_STATUS.md`;
- this implementation plan;
- `docs/README.md`;
- `docs/architecture/README.md`;
- the dedicated contract/handoff;
- `post_i3_evaluation_work_roadmap.md`;
- affected current/target documents;
- status-checking smoke scripts;
- stale TODO or future-tense text.

Current documents must state one status only. Do not preserve a stale status and append a later section saying that it supersedes earlier text.

<!-- O1B_CURRENT_BOUNDARY -->
### O1B sealed replay-lane discovery — complete

O1B owns one bounded secure inventory of the configured durable-finalization root, exact grouping and eligibility classification, lexicographic selection of one sealed-pending locator, canonical selected-locator reread, and at most one delegation to the existing I1-GC authority. It owns no replay algorithm, completion publication, queue lane, C2/worker execution, scheduler round coordinator, polling, fairness, backoff, shutdown, supervision, or always-on operation.

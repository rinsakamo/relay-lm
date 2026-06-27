---
relaylm_doc_type: status
relaylm_authority: current_project_state
relaylm_status: current
relaylm_volatility: high
relaylm_owner: project_status
relaylm_update_trigger:
  - boundary moves between design dry-run read-only and apply
  - default behavior changes
  - supported request shape changes
  - current schema producer or consumer changes
  - active integration milestone changes state
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact schema details
  - historical implementation evidence
relaylm_related_authority:
  - docs/DOCUMENTATION_MODEL.md
  - docs/architecture/pipeline_responsibility_design.md
  - docs/architecture/pipeline_implementation_plan.md
  - docs/architecture/post_i3_evaluation_work_roadmap.md
  - docs/architecture/current_target_migration_guide.md
  - docs/architecture/wave3_cross_slice_convergence_audit.md
  - docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md
  - docs/architecture/i1gd_durable_finalization_retention_cleanup.md
  - docs/architecture/i1ge_durable_finalization_crash_validation.md
  - docs/architecture/phase_i4d_primary_retrieval_exclusion.md
  - docs/architecture/o1d1_production_scheduler_round.md
---
# RelayLM Project Status

Last reviewed: 2026-06-27 JST

## Purpose and authority

This page is the concise current-state view. When documents disagree:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) owns component responsibility and canonical target order.
2. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) owns implementation status and sequencing.
3. Dedicated current contracts and handoffs own exact bounded behavior.
4. [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) owns compatibility interpretation.
5. `docs/mvp/` and archived documents are historical evidence only.

## Current implementation position

```text
Managed-route correctness: Phase 5-C complete through bounded v0/v1 apply and C5 runtime plumbing
Pre-stream hardening: Phase 5-D complete through D2
Stream safety / TTS handoff preparation: Phase 5.5 complete for RelayLM Core
Asynchronous RelaySLP orchestration: I1-B and B3 complete; C1-0 through C1-5 complete; C2 one-job adapter complete
Local worker operation: O0 one invocation -> at most one eligible queued job complete
Scheduler contract: O1A replay-before-queue round / adapter / idle contract complete
Scheduler replay lane: O1B one bounded sealed-record discovery/reread/I1-GC adapter complete
Scheduler queue lane: O1C one bounded discovery/reread/scope/C2 adapter complete
O1D1 accepted gates/one-round coordinator: complete
Scheduler remaining production: O1D2 policy, O1E recovery/shutdown, and O1F validation unimplemented
O1 overall: in progress
O2 supervised worker service: planned/unimplemented
O3 always-on local operation: planned/unimplemented
RelayMEM Primary path: M1/M2 complete; M3a-M3h executable; next-turn recall and scope isolation complete
SOUL Lab UI: UI-A0 through UI-A7, Phase I-2, Phase I-3, and UI-B0 complete
Local E1 proof: explicit scene-qualified request -> O0 terminal success -> Primary MEM -> later Home recall complete
Direct Home-origin formation: not currently proven; trusted scene admission is missing
Phase I-4A Forget / Hide contract: defined target
Phase I-4B resolver / shared fence / read-only preflight-token-history: complete
Phase I-4C1 hidden-successor commit: complete
Phase I-4C2 prepared recovery / operation-scoped M3f-M3g / tombstone finalization: complete
Phase I-4D ordinary retrieval lifecycle exclusion: complete
Phase I-4E loopback API and SOUL Lab Forget UI: unimplemented
Phase I-4F full Forget validation: unimplemented
Phase I-4 overall: in progress
I1-GA contract / fault model: complete
I1-GB durable-finalization publication / pre-release admission: complete
I1-GC one-record restart replay / exact C1-5+B2 convergence / completion marker: complete
I1-GD retention / orphan reconciliation / isolation lifecycle / cleanup: complete
I1-GE full production crash validation: complete
I1-G overall: complete
Wave 3 implementation tracks complete
W3-INT merged
Wave 4 follow-up planning may use the frozen W3-INT authority map and inputs
```

## Core request/runtime foundation

Implemented:

- OpenAI-compatible `/v1/chat/completions` routing and backend forwarding;
- managed character resolution and SOUL / OUTPUT_POLICY application;
- selected RelayMEM M2 retrieval and bounded RelayCTX injection;
- non-stream and SSE response handling;
- post-response RelaySLP enqueue handoff where explicitly enabled;
- conservative default-off apply gates.

Current limitations include incomplete active tool-chain reconstruction, parser-versioned cache compatibility, output-side RelayREF/RelaySCN completion, and `/v1/responses` support.

## Phase 6 RelaySLP orchestration and O0

Implemented:

- A1/A2 deferred admission and finalized-turn handoff;
- B0-B3 durable enqueue and fenced lifecycle;
- I1-B ordinary runtime source publication and enqueue;
- C1-0 through C1-5 complete;
- C2 one-job claim/rehydrate/execute adapter: complete;
- O0 one-shot bounded queue discovery and one C2 delegation;
- O1A pure two-lane round/result/disposition contract;
- O1B one bounded eligible sealed I1-G replay-lane discovery and one existing I1-GC delegation;
- O1C one bounded eligible B2/B3 queue-lane discovery and one existing C2 delegation;
- O1D1 accepted scheduler gates and one production `replay -> queue` round.

B3 lifecycle: complete.

C1-5 keeps queue records content-free and persists the claim-independent protected capture before queue publication. C2 can claim one exact queued record, rehydrate a fresh protected source, invoke the one-claimed worker, and commit the canonical terminal result.

O0 adds `relaylm-worker --once --config config.yaml`. It is default-off, operator-invoked, and processes at most one currently eligible queued record. It does not poll, schedule, supervise, repair corrupt records, or create a second queue lifecycle.

## O1 operations boundary

O1A is complete as a pure contract. O1B and O1C are complete as one bounded replay and one bounded queue opportunity. O1D1 is complete for accepted scheduler gates and one production round:

```text
one exact RelayLMConfig
  -> accepted SchedulerGates
  -> O1B replay lane at most once
  -> O1C queue lane at most once
  -> O1A aggregate_scheduler_round(...)
  -> content-free projection validation
  -> return without sleep
```

The lane order is replay then queue. Replay output, locator, job identity, and dispatch identity are never passed directly to C2. A queue record converged by replay may be selected in the same round only through independent queue-root discovery and canonical reread by O1C.

The accepted scheduler fields are exactly:

```yaml
relaymem_local_scheduler_enabled: false
relaymem_local_scheduler_dry_run_only: true
relaymem_local_scheduler_apply_enabled: false
relaymem_local_scheduler_replay_lane_enabled: true
relaymem_local_scheduler_queue_lane_enabled: true
```

O1D1 is not a polling loop, does not choose when another round starts, and does not absorb O1B, O1C, I1-GC, C2, B3, or worker authority. O1 overall remains in progress. O1D2 owns deterministic ordering beyond fixed lane order, fairness/starvation prevention, retry-time handling, bounded backoff/jitter, and saturation pacing. O1E owns stale-claim operational recovery, cancellation checkpoints, and graceful shutdown. O1F owns corruption/concurrency/saturation/restart/leakage/operational validation. O2/O3 remain planned/unimplemented.

## I1-G durable-finalization boundary

The I1-GA through I1-GD durable-finalization boundary is complete and remains the production authority chain. I1-GA through I1-GE are complete. Visible-release restart evidence publication is implemented by I1-GB in explicit apply mode. Restart-time one-record replay is implemented by I1-GC. Durable-finalization bounded retention and cleanup is implemented by I1-GD. I1-GE proves real process-exit and fresh-process restart across the existing I1-GB/I1-GC/I1-GD production boundaries.

```text
ordinary finalized turn
  -> I1-GB durable base / stream segments / seal before protected visible release
  -> normal finalizer or caller-selected restart replay
  -> exact finalized-turn source reconstruction
  -> existing A1 / A2 / B1 preparation
  -> exact sealed job / dispatch identity verification
  -> canonical C1-5 protected-source convergence
  -> canonical B2 queue convergence
  -> exact downstream reread and correlation verification
  -> immutable content-free completion marker
  -> bounded I1-GD retention / isolation / cleanup pass
  -> I1-GE crash-at-every-boundary validation
```

I1-G completion means exact sealed evidence, exact C1-5 source, exact B2 queue correlation, durable completion, retention/isolation lifecycle, and full crash validation. It does not mean B3 terminal success, C2 execution, worker execution, Primary MEM formation, semantic quality, retrieval use, automatic scheduling, polling, supervision, or always-on operation.

## RelayMEM Primary persistence and governance

Implemented:

- M3a-M3h Primary MEM formation, page publication, index/log convergence, and recovery audit;
- exact one-claim worker execution;
- I1 next-turn Primary MEM recall: complete;
- character and namespace isolation: complete;
- bounded RelayCTX memory injection;
- I2 real SOUL Lab observation: complete;
- I3 auditable Primary MEM Correct: complete;
- I-4B canonical current-state resolution and shared Correct/Forget mutation fence;
- I-4C1 immutable Forget prepared evidence and deterministic hidden-successor M3e commit;
- I-4C2 exact prepared resume, operation-scoped M3f/M3g convergence, tombstone finalization, and exact replay;
- I-4D ordinary M2/RelayCTX lifecycle and prior-revision exclusion plus read-only historical lifecycle projection.

I-4D is retrieval-only integration. It consumes the existing current-state authority before snippet construction, excludes hidden, prior, prepared, recovery-required, corrupt, ambiguous, unsafe, and cross-scope candidates from ordinary M2 and RelayCTX, and adds read-only historical lifecycle projection without rewriting historical receipts. It does not implement Forget apply/recovery, M3f/M3g, mutation routes, UI, restore, purge, or physical deletion.

Forget is not product-complete until:

```text
I-4E loopback API and SOUL Lab UI
  -> I-4F crash/race/security/fresh-conversation validation
```

## SOUL Lab and E1 evaluation

UI-B0 real Home conversation: complete. The browser uses one server-projected route and the existing same-origin RelayLM Chat Completions path. It owns no backend, SOUL, namespace, filesystem, queue, worker, scheduler, or mutation authority.

The first local E1 result proves two separate lanes:

```text
formation lane
  explicit trusted scene-qualified managed request
    -> durable source and queue
    -> O0 one-job execution
    -> Primary MEM formation
    -> Phase I-2 observation

recall lane
  SOUL Lab Home real conversation
    -> existing M2 / RelayCTX recall
    -> remembered or corrected fact question
    -> Phase I-2 used-memory evidence
```

Direct Home-origin formation remains unproven because UI-B0 sends standard Chat Completions fields and does not self-assert trusted scene-admission metadata. The operator must also initialize the character-scoped Primary store structure before first apply.

The workstation evaluation exposed two quality gaps:

- finalized-turn summary formation needs speaker-provenance-safe evidence;
- recall responses need stronger separation between stored evidence and unsupported inference.

## Immediate dependency-first work

```text
After W3-INT merge:
  O1D2 ordering/fairness/retry-time/backoff/jitter/pacing -> O1E recovery/shutdown
  I-4E loopback API/UI -> I-4F full Forget validation
  O1F operational validation
  UI-B1A read-only lifecycle visibility
  I-5A Pin / Unpin contract/preflight
  I-7A/B Held Apply / Discard contract/preflight
```

The Wave 4 start contracts are frozen in [Wave 3 Cross-Slice Convergence Audit](architecture/wave3_cross_slice_convergence_audit.md) and may be used for follow-up implementation planning after the W3-INT merge.

## Safe defaults

Current mutation, worker, durable-finalization, retention, and scheduler-related paths remain default-off or dry-run-first. I1-GC does not add a scanner or automatic retry loop. I1-GD performs one bounded caller-invoked pass and does not poll or invoke replay. O1D1 accepts exact scheduler gates but runs only one caller-invoked round and returns without sleep. I-4D adds no accepted mutation route and no SOUL Lab Forget UI.

## Not yet implemented

- trusted scene admission for direct Home-origin Primary MEM formation;
- idempotent operator-facing character-store bootstrap;
- speaker-provenance-safe Primary MEM summary formation;
- strict evidence-grounded recall response generation;
- O1D2 scheduling policy, O1E recovery/shutdown, O1F validation, O2, and O3;
- I-4E API/UI and I-4F validation;
- restore/unhide or physical purge;
- I-5 through I-9 governance and RelaySOUL slices;
- durable transcript inspection;
- static SOUL Lab bundle serving;
- TTS/audio/avatar/Live2D execution;
- ASR and peer communication transport.

<!-- O1B_CURRENT_BOUNDARY -->
## O1B sealed replay-lane boundary

O1B is complete for one bounded, non-recursive inventory of the configured I1-G root, exact canonical grouping and eligibility classification, deterministic selection of one sealed-pending locator, canonical selected-record reread, and at most one existing I1-GC delegation. It does not implement the O1C queue algorithm, a scheduler round loop, fairness, backoff, polling, shutdown, supervision, or always-on operation.

## Wave 2 cross-slice convergence

W2-INT audits the merged I1-GD, I-4C2, O1B, and O1C production boundaries. It adds no scheduler loop or retrieval exclusion. The Wave 2 audit is frozen historical evidence.

## Wave 3 cross-slice convergence

Wave 3 implementation tracks are complete: I1-GE, I-4D, and O1D1. W3-INT records their source PRs, merge commits, completion reports, handoffs, lock/root/config map, leakage proof, and frozen Wave 4 inputs. W3-INT is merged; Wave 4 follow-up planning may use the frozen W3-INT authority map and inputs.

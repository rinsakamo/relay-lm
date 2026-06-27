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
  - MVP boundary and roadmap sequencing
  - exact schema details
  - historical implementation evidence
relaylm_related_authority:
  - docs/DOCUMENTATION_MODEL.md
  - docs/architecture/pipeline_responsibility_design.md
  - docs/architecture/project_execution_plan.md
  - docs/architecture/current_target_migration_guide.md
  - docs/architecture/relaymem_slp_current_target.md
  - docs/architecture/o1e_scheduler_operational_controls.md
  - docs/architecture/o1f_operational_validation.md
  - docs/architecture/e1_evaluation_consolidation.md
  - docs/architecture/phase_i4f_forget_validation.md
  - docs/architecture/wave5_cross_slice_convergence_audit.md
  - docs/architecture/wave4_cross_slice_convergence_audit.md
  - docs/architecture/wave3_cross_slice_convergence_audit.md
  - docs/architecture/phase_i4e_forget_api_ui.md
  - docs/architecture/o1d2_scheduler_policy.md
---
# RelayLM Project Status

Last reviewed: 2026-06-27 JST

## Purpose and authority

This page is the concise current-state view. When documents disagree:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) owns component responsibility and canonical target order.
2. This page owns current implementation status and active caveats.
3. [Project Execution Plan](architecture/project_execution_plan.md) owns MVP boundary, dependency sequencing, and roadmap ordering.
4. Dedicated current contracts and handoffs own exact bounded behavior.
5. [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) owns compatibility interpretation.
6. `docs/mvp/` and archived documents are historical evidence only.

This page owns current implementation status and active caveats. [Project Execution Plan](architecture/project_execution_plan.md) owns MVP boundary, dependency sequencing, and roadmap ordering.

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
O1D2 bounded scheduler policy/fairness/pacing: complete
O1E stale recovery/cancellation/shutdown: complete
O1F operational validation: complete
O1 overall: complete through validation-only caller-invoked local scheduler boundary
O2 supervised worker service: planned/unimplemented
O3 always-on local operation: planned/unimplemented

RelayMEM Primary path: M1/M2 complete; M3a-M3h executable; next-turn recall and scope isolation complete
SOUL Lab UI: UI-A0 through UI-A7, Phase I-2, Phase I-3, UI-B0, UI-B1A, and I-4E Forget UI complete
UI-B1A read-only lifecycle visibility: complete
Local E1 proof: explicit scene-qualified request -> O0 terminal success -> Primary MEM -> later Home recall complete
E1 evaluation consolidation: complete
Direct Home-origin formation: not currently proven; trusted scene admission is missing

Phase I-4A Forget / Hide contract: defined target contract; completed by I-4B through I-4F implementation slices
Phase I-4B resolver / shared fence / read-only preflight-token-history: complete
Phase I-4C1 hidden-successor commit: complete
Phase I-4C2 prepared recovery / operation-scoped M3f-M3g / tombstone finalization: complete
Phase I-4D ordinary retrieval lifecycle exclusion: complete
Phase I-4E loopback Forget API and SOUL Lab UI: complete
Phase I-4F full Forget validation: complete
Phase I-4 overall: complete

I-5A Pin / Unpin contract and read-only preflight: complete
I-5 runtime apply/API/UI/ranking behavior: unimplemented

I-7A/B Held Apply / Discard contract and read-only preflight: complete
I-7 runtime apply/discard/API/UI/durable governance evidence: unimplemented

I1-GA contract / fault model: complete
I1-GB durable-finalization publication / pre-release admission: complete
I1-GC one-record restart replay / exact C1-5+B2 convergence / completion marker: complete
I1-GD retention / orphan reconciliation / isolation lifecycle / cleanup: complete
I1-GE full production crash validation: complete
I1-G overall: complete

Wave 3 implementation tracks complete
W3-INT merged
Wave 4 implementation tracks complete
W4-INT merged
Post-Wave-4 / Wave 5 implementation tracks complete
W5-INT merged
O1F validation slice merged after W5-INT
```

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
- O1D1 accepted scheduler gates and one production `replay -> queue` round;
- O1D2 bounded scheduler policy wrapper;
- O1E bounded caller-invoked operational controls;
- O1F validation-only operational hardening.

B3 lifecycle: complete. C1-5 keeps queue records content-free and persists the claim-independent protected capture before queue publication.

I1 next-turn Primary MEM recall: complete. character and namespace isolation: complete.

## O1 operations boundary

O1A, O1B, O1C, and O1D1 are complete through one caller-invoked `replay -> queue` round. O1D2 is current implemented as a bounded policy wrapper around one O1D1 round:

```text
O1D1 one-round result
  -> content-free policy state
  -> deterministic fairness preference hints
  -> retry-window rounding
  -> bounded backoff/jitter recommendation
  -> bounded pacing recommendation
  -> return without sleeping
```

O1E is current implemented as a bounded caller-invoked operational-control layer around the existing O1D2/O1D1 stack. One explicit call may check cancellation, optionally orchestrate at most one B3 stale-recovery transition through existing B3 authority, invoke at most one O1D2/O1D1 scheduler round, check cancellation again, and return a bounded content-free projection. O1E does not poll, sleep, loop, daemonize, supervise, create background workers, start timers, or rewrite queue state directly.

O1F is current implemented as validation-only hardening over the caller-invoked O1E/O1D2/O1D1 stack. It validates corruption, concurrency, saturation/boundedness, restart reread, cancellation/shutdown projection, and leakage boundaries. O1F does not poll, sleep, loop, daemonize, supervise, create a worker pool, or implement O2/O3.

O2/O3 remain planned/unimplemented.

## RelayMEM Primary persistence and governance

Implemented governance boundaries now include:

- I-4B canonical current-state resolution and shared Correct/Forget mutation fence;
- I-4C1 immutable Forget prepared evidence and deterministic hidden-successor M3e commit;
- I-4C2 exact prepared resume, operation-scoped M3f/M3g convergence, tombstone finalization, and exact replay;
- I-4D ordinary M2/RelayCTX lifecycle and prior-revision exclusion plus read-only historical lifecycle projection;
- I-4E loopback-only Forget API and SOUL Lab UI;
- I-4F crash/race/security/fresh-conversation validation;
- I-5A Pin / Unpin contract and read-only preflight;
- I-7A/B Held Apply / Discard contract and read-only preflight.

Forget product-complete means one real current active Primary MEM can be hidden through the loopback/SOUL Lab API/UI surface, with explicit token confirmation, bounded receipt/history/lifecycle visibility, restart-safe recovery, fresh-process reread, fresh ordinary conversation exclusion, stale-browser fencing, multi-scope isolation, and no private-content leakage.

Forget product-complete does not mean restore, unhide, purge, physical deletion, batch Forget, Secondary MEM consolidation, RelaySOUL mutation, Pin / Unpin runtime behavior, Held Apply / Discard runtime behavior, scheduler/worker changes, or direct Home-origin Primary MEM formation.

I-5A is complete only for Pin / Unpin contract and read-only preflight. It does not implement Pin apply, Unpin apply, SOUL Lab API/UI, durable Pin state, M2 ranking changes, hidden-memory retrieval, semantic content mutation, physical deletion, queue/worker/scheduler changes, or durable-finalization changes.

I-7A/B is complete only for Held Apply / Discard contract and read-only preflight. It does not implement Held Apply runtime, Held Discard runtime, B3 queue mutation, retry release, terminal commit, Primary MEM page/index/log writes, C2 worker invocation, O1 scheduler invocation, or SOUL Lab mutation UI.

## SOUL Lab and E1 evaluation

UI-B0 real Home conversation is complete. UI-B1A read-only lifecycle and operation visibility is complete. I-4E Forget API/UI is complete. The browser uses server-projected routes and the existing same-origin RelayLM Chat Completions path. It owns no backend, SOUL, namespace, storage-root, queue, worker, scheduler, or mutation authority.

E1 evaluation consolidation is complete as a docs/evidence boundary. It records the evidence inventory, direct Home-origin formation decision, character-store bootstrap ergonomics, speaker-provenance quality requirements, evidence-grounded recall quality requirements, and docs-only validation.

Current MVP decision: Home is conversation, recall, observation, and governance evaluation unless a future trusted scene-admission phase changes that boundary. Primary MEM formation remains operator/trusted-admission-path driven for MVP evaluation.

Direct Home-origin formation remains unproven because UI-B0 sends standard Chat Completions fields and does not self-assert trusted scene-admission metadata. The workstation E1 proof still separates a trusted formation lane from the Home recall lane.

## Immediate dependency-first work

```text
Post-O1F next candidates:
  I-5B or Pin/Unpin runtime apply/API/UI/ranking work, if defined
  I-7C or Held Apply/Discard runtime/API/UI/durable evidence work, if defined
  E1-R1 trusted Home scene-admission path
  E1-R2 idempotent character-store bootstrap command
  E1-R3 provenance-preserving Primary MEM formation summary
  E1-R4 retrieval-response grounding and unsupported-detail suppression
  O2/O3 only after explicit MVP need
```

The Wave 4 implementation audit is [Wave 4 Cross-Slice Convergence Audit](architecture/wave4_cross_slice_convergence_audit.md). The Wave 5 convergence record is [Wave 5 Cross-Slice Convergence Audit](architecture/wave5_cross_slice_convergence_audit.md). The O1E operational-control handoff is [O1E Scheduler Operational Controls](architecture/o1e_scheduler_operational_controls.md). The O1F validation handoff is [O1F Operational Validation](architecture/o1f_operational_validation.md). The E1 consolidation record is [E1 MVP Evaluation Evidence Consolidation](architecture/e1_evaluation_consolidation.md). The I-4F validation handoff is [Phase I-4F Forget Validation](architecture/phase_i4f_forget_validation.md). Detailed MVP sequencing and post-MVP roadmap ordering live in [Project Execution Plan](architecture/project_execution_plan.md).

## Safe defaults

Current mutation, worker, durable-finalization, retention, scheduler-related paths, and E1 evaluation paths remain default-off or docs-only. I1-GC does not add a scanner or automatic retry loop. I1-GD performs one bounded caller-invoked pass and does not poll or invoke replay. O1D1 accepts exact scheduler gates but runs only one caller-invoked round and returns without sleep. O1D2 returns bounded policy hints only and does not sleep or schedule another round by itself. O1E returns bounded operational-control projections only and does not loop, poll, sleep, or supervise. O1F validates operational edges but does not loop, poll, sleep, supervise, or run always-on. I-4E/I-4F preserve I-4B/I-4C1/I-4C2/I-4D authority boundaries. E1 adds no runtime behavior changes.

## Not yet implemented

- trusted scene admission for direct Home-origin Primary MEM formation;
- idempotent operator-facing character-store bootstrap;
- speaker-provenance-safe Primary MEM summary formation;
- strict evidence-grounded recall response generation;
- O2 supervised worker service and O3 always-on local operation;
- restore/unhide or physical purge;
- Pin / Unpin runtime apply, API/UI, durable Pin state, and M2 ranking behavior;
- Held Apply / Discard runtime, API/UI, and durable governance evidence;
- RelaySOUL proposal/intervention/rollback slices;
- static SOUL Lab bundle serving;
- TTS/audio/avatar/Live2D execution;
- ASR and peer communication transport.

<!-- O1B_CURRENT_BOUNDARY -->
## O1B sealed replay-lane boundary

O1B is complete for one bounded, non-recursive inventory of the configured I1-G root, exact canonical grouping and eligibility classification, deterministic selection of one sealed-pending locator, canonical selected-record reread, and at most one existing I1-GC delegation. It does not implement the O1C queue algorithm, a scheduler round loop, polling, shutdown, supervision, or always-on operation.

## Wave 2 cross-slice convergence

W2-INT audits the merged I1-GD, I-4C2, O1B, and O1C production boundaries. It adds no scheduler loop or retrieval exclusion. The Wave 2 audit is frozen historical evidence.

## Wave 3 cross-slice convergence

Wave 3 implementation tracks are complete: I1-GE, I-4D, and O1D1. W3-INT records their source PRs, merge commits, completion reports, handoffs, lock/root/config map, leakage proof, and frozen Wave 4 inputs. W3-INT is merged.

## Wave 4 cross-slice convergence

Wave 4 implementation tracks are complete: O1D2, I-4E, UI-B1A, I-5A, and I-7A/B. W4-INT records their source PRs, merge commits, completion reports, handoffs, authority map, leakage review, and frozen post-Wave-4 inputs. W4-INT is merged.

## Wave 5 cross-slice convergence

Post-Wave-4 / Wave 5 implementation tracks are complete: E1 evaluation consolidation, O1E scheduler operational controls, and I-4F Forget product-completion validation. W5-INT records their source PRs, merge commits, completion reports, handoffs, authority map, leakage review, and frozen next inputs. W5-INT is merged.

## E1 evaluation consolidation

E1 records the post-Wave-4 evidence inventory and MVP decision that direct Home-origin formation is not required for current MVP evaluation. Home remains the real conversation, recall, observation, and governance evaluation surface. A future trusted Home scene-admission path must be designed explicitly before Home-origin Primary MEM formation can be claimed.

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
  - docs/architecture/o1f_operational_validation.md
  - docs/architecture/phase_i5b_pin_unpin_apply.md
  - docs/architecture/phase_i7c_held_apply_discard_runtime.md
  - docs/architecture/e1r1_trusted_home_scene_admission.md
  - docs/architecture/e1r2_character_store_bootstrap.md
  - docs/architecture/e1_evaluation_consolidation.md
  - docs/architecture/wave6_cross_slice_convergence_audit.md
  - docs/architecture/wave5_cross_slice_convergence_audit.md
---
# RelayLM Project Status

Last reviewed: 2026-06-28 JST

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
SOUL Lab UI: UI-A0 through UI-A7, Phase I-2, Phase I-3, UI-B0, UI-B1A, I-4E Forget UI, I-5B Pin / Unpin UI, and I-7C Held Governance UI complete
UI-B1A read-only lifecycle visibility: complete
Local E1 proof: explicit scene-qualified request -> O0 terminal success -> Primary MEM -> later Home recall complete
E1 evaluation consolidation: complete
E1-R1 trusted Home scene admission: complete
E1-R2 character-store bootstrap command: complete
Home can be a trusted formation source only through the E1-R1 route-owned gate; browser-owned trust remains rejected.

Phase I-4A Forget / Hide contract: defined target contract; completed by I-4B through I-4F implementation slices
Phase I-4B resolver / shared fence / read-only preflight-token-history: complete
Phase I-4C1 hidden-successor commit: complete
Phase I-4C2 prepared recovery / operation-scoped M3f-M3g / tombstone finalization: complete
Phase I-4D ordinary retrieval lifecycle exclusion: complete
Phase I-4E loopback Forget API and SOUL Lab UI: complete
Phase I-4F full Forget validation: complete
Phase I-4 overall: complete

I-5A Pin / Unpin contract and read-only preflight: complete
I-5B Pin / Unpin apply/API/UI/ranking behavior: complete

I-7A/B Held Apply / Discard contract and read-only preflight: complete
I-7C Held Apply/Discard runtime/API/UI/durable governance evidence: complete

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
Wave 6 implementation tracks complete
W6-INT merged
```

## O1 operations boundary

O1A through O1F are complete through a validation-only caller-invoked local scheduler boundary. O1D1 accepts the five exact scheduler gates and runs at most one `replay -> queue` round. O1D2 adds bounded policy hints without sleeping. O1E adds caller-invoked stale-recovery, cancellation, and shutdown projections without polling or supervision. O1F validates corruption, concurrency, saturation, restart reread, and leakage edges.

O2/O3 remain planned/unimplemented. O1F completion does not imply a daemon, worker pool, recurring schedule, service supervision, or always-on operation.

## RelayMEM Primary persistence and governance

Implemented governance boundaries now include:

- I-4B canonical current-state resolution and shared Correct/Forget mutation fence;
- I-4C1 immutable Forget prepared evidence and deterministic hidden-successor M3e commit;
- I-4C2 exact prepared resume, operation-scoped M3f/M3g convergence, tombstone finalization, and exact replay;
- I-4D ordinary M2/RelayCTX lifecycle and prior-revision exclusion plus read-only historical lifecycle projection;
- I-4E loopback-only Forget API and SOUL Lab UI;
- I-4F crash/race/security/fresh-conversation validation;
- I-5A Pin / Unpin contract and read-only preflight;
- I-5B durable Pin / Unpin apply, loopback API/UI, and deterministic ranking hint;
- I-7A/B Held Apply / Discard contract and read-only preflight;
- I-7C Held Apply / Discard runtime governance evidence, loopback API/UI, and explicit confirmation flow.

Forget product-complete means one real current active Primary MEM can be hidden through the loopback/SOUL Lab API/UI surface, with explicit token confirmation, bounded receipt/history/lifecycle visibility, restart-safe recovery, fresh-process reread, fresh ordinary conversation exclusion, stale-browser fencing, multi-scope isolation, and no private-content leakage.

I-5B Pin state is governance metadata and a ranking hint only. It does not admit hidden, prepared, recovery-required, corrupt, cross-scope, or prior physical revisions into retrieval and does not alter semantic memory content.

I-7C governs one already-held candidate through explicit Apply / Discard preflight and confirmation. It persists content-free decision evidence but does not start workers, schedulers, retry loops, C2, O1, or B3 lifecycle transitions from the UI.

## SOUL Lab and E1 evaluation

UI-B0 real Home conversation is complete. UI-B1A read-only lifecycle and operation visibility is complete. I-4E Forget API/UI, I-5B Pin / Unpin API/UI, and I-7C Held Governance API/UI are complete. The browser uses server-projected routes and the existing same-origin RelayLM Chat Completions path. It owns no backend, SOUL, namespace, storage-root, queue, worker, scheduler, or route authority.

E1 evaluation consolidation is complete as a docs/evidence boundary. E1-R1 adds a route-owned trusted Home scene-admission gate that defaults disabled and rejects browser-owned trust. E1-R2 adds a dry-run-first operator command for idempotent character-store bootstrap. E1-R3 and E1-R4 remain quality/evaluation follow-ups.

## Immediate dependency-first work

```text
Post-Wave-6 next candidates:
  E1-R3 provenance-preserving Primary MEM formation summary
  E1-R4 retrieval-response grounding and unsupported-detail suppression
  O2/O3 only after explicit MVP need
  Static SOUL Lab bundle serving, if local packaging requires it
```

The Wave 6 convergence record is [Wave 6 Cross-Slice Convergence Audit](architecture/wave6_cross_slice_convergence_audit.md). Detailed MVP sequencing and post-MVP roadmap ordering live in [Project Execution Plan](architecture/project_execution_plan.md).

## Safe defaults

Current mutation, worker, durable-finalization, retention, scheduler-related paths, and E1 evaluation paths remain default-off or explicitly caller/operator invoked. I1-GC does not add a scanner or automatic retry loop. I1-GD performs one bounded caller-invoked pass and does not poll or invoke replay. O1D1 accepts exact scheduler gates but runs only one caller-invoked round and returns without sleep. O1D2 returns bounded policy hints only. O1E returns bounded operational-control projections only. O1F validates operational edges but does not loop, poll, sleep, supervise, or run always-on. E1-R1 defaults disabled and does not accept browser-owned trust. E1-R2 is an explicit dry-run-first operator command.

## Not yet implemented

- speaker-provenance-safe Primary MEM summary formation;
- strict evidence-grounded recall response generation;
- O2 supervised worker service and O3 always-on local operation;
- restore/unhide or physical purge;
- Merge / Supersession runtime apply;
- Secondary MEM consolidation;
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

## Wave 6 cross-slice convergence

Wave 6 implementation tracks are complete: O1F operational validation, I-5B Pin / Unpin apply, I-7C Held Apply / Discard runtime governance, E1-R1 trusted Home scene admission, and E1-R2 character-store bootstrap. W6-INT records their source PRs, merge commits, completion reports, handoffs, authority map, leakage review, and frozen next inputs. W6-INT is merged.

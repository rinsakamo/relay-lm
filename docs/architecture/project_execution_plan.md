---
relaylm_doc_type: implementation_plan
relaylm_authority: mvp_execution_plan_and_post_mvp_roadmap
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - MVP boundary changes
  - dependency sequencing changes
  - a wave opens or closes through a convergence PR
  - evaluation decision changes
  - post-MVP roadmap ordering changes
relaylm_not_authoritative_for:
  - current implemented runtime status
  - component responsibility and canonical target order
  - exact schema details
  - historical implementation evidence
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - pipeline_responsibility_design.md
  - current_target_migration_guide.md
  - relaymem_slp_current_target.md
  - o1e_scheduler_operational_controls.md
  - e1_evaluation_consolidation.md
  - phase_i4f_forget_validation.md
  - wave5_cross_slice_convergence_audit.md
  - wave4_cross_slice_convergence_audit.md
  - wave3_cross_slice_convergence_audit.md
---
# RelayLM Project Execution Plan

Last reviewed: 2026-06-27 JST

## Purpose

This document is the single plan and roadmap authority for RelayLM execution. It owns dependency-first sequencing, MVP boundaries, MVP completion criteria, and post-MVP roadmap ordering.

It does not own current implementation status. Read [Project Status](../PROJECT_STATUS.md) first for the implemented boundary, incomplete work, and active caveats. Component responsibility remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), exact behavior remains in dedicated contracts and handoffs, and current/target interpretation remains in [Current / Target / Migration Guide](current_target_migration_guide.md).

## Authority split

```text
PROJECT_STATUS.md
  -> current implemented state, active gaps, next candidates

project_execution_plan.md
  -> MVP boundary, dependency sequence, roadmap, wave ordering

slice contracts and handoffs
  -> exact bounded behavior for one feature or phase

docs/mvp/** and wave audits
  -> historical evidence and frozen convergence records
```

The former plan and roadmap files are compatibility stubs that point here:

```text
pipeline_implementation_plan.md
post_i3_evaluation_work_roadmap.md
relaymem_mvp_implementation_plan.md
```

## MVP boundary

The MVP is the smallest text-first product boundary that lets a local operator evaluate whether RelayLM can sustain character-scoped memory safely through real conversation, observation, explicit governance, and bounded local operation.

MVP must provide:

- real SOUL Lab Home conversation through the existing OpenAI-compatible RelayLM path;
- Primary MEM formation from trusted scene-qualified managed requests;
- later-turn Primary MEM retrieval and RelayCTX injection;
- read-only observation of latest runs, formed memory, held or blocked outcomes, lifecycle state, and used-memory evidence;
- explicit auditable Correct;
- explicit Forget / Hide through API/UI plus validation;
- ordinary retrieval exclusion for hidden, prepared, recovery-required, corrupt, ambiguous, unsafe, cross-scope, and prior physical revisions;
- durable finalization evidence before protected visible release;
- one-record restart replay, retention/isolation cleanup, and crash validation;
- bounded local operation that can drain eligible replay and queue work through explicit caller-invoked rounds;
- caller-invoked O1E stale-recovery/cancellation/shutdown controls;
- E1 evidence consolidation with an explicit direct Home-origin formation decision.

MVP does not include:

- direct Home-origin trusted scene admission unless a later E1-R1 gate explicitly adds it;
- always-on daemon/service supervision unless a later explicit MVP gate proves it is required;
- voice, TTS execution, avatar, Live2D, ASR, or peer communication transport;
- Secondary MEM consolidation;
- Merge / Supersession runtime apply unless explicitly pulled into MVP later;
- RelaySOUL proposal/intervention/rollback runtime;
- experimental SOUL replacement or synthetic memory bootstrap.

## MVP execution lanes

```text
Memory governance
  I-4E Forget API/UI                         complete
    -> I-4F Forget validation                complete
    -> I-5A Pin / Unpin contract/preflight   complete
    -> I-5B or apply/API/UI/ranking work     candidate
    -> I-7A/B Held Apply/Discard preflight   complete
    -> I-7C or runtime governance work       candidate

Operations
  O1D2 ordering/fairness/retry/backoff/pacing complete
    -> O1E stale recovery/cancellation/shutdown complete
    -> O1F operational validation               candidate
    -> O2 supervised worker service, if required
    -> O3 always-on local operation, if required

Evaluation
  E1 evaluation consolidation                    complete
    -> direct Home-origin formation decision           Option A for current MVP
    -> E1-R1 trusted Home scene-admission path         candidate
    -> E1-R2 idempotent character-store bootstrap command
    -> E1-R3 provenance-preserving Primary MEM formation summary
    -> E1-R4 retrieval-response grounding and unsupported-detail suppression

SOUL Lab product
  UI-B1A lifecycle and operation visibility   complete
    -> operator-facing evaluation flow
    -> static bundle serving, if required for local MVP packaging
```

## MVP dependency waves

### Foundation already available for MVP planning

The current MVP plan assumes the completed foundations listed in [Project Status](../PROJECT_STATUS.md): Phase 6 through C2/O0, UI-B0 real Home conversation, Phase I-2 observation, Phase I-3 Correct, I1-GA through I1-GE, I-4B through I-4F, O1A through O1E, UI-B1A, I-5A, I-7A/B, and E1 evaluation consolidation.

### Wave 4 completed

```text
O1D2 bounded scheduler policy/fairness/pacing
I-4E loopback API and SOUL Lab Forget UI
UI-B1A read-only lifecycle visibility
I-5A Pin / Unpin contract/preflight
I-7A/B Held Apply / Discard contract/preflight
```

The frozen Wave 4 completion record is [Wave 4 Cross-Slice Convergence Audit](wave4_cross_slice_convergence_audit.md). The frozen Wave 4 start contracts remain recorded in [Wave 3 Cross-Slice Convergence Audit](wave3_cross_slice_convergence_audit.md).

### Wave 5 completed

```text
E1 evaluation consolidation
O1E stale recovery/cancellation/shutdown
I-4F crash/race/security/fresh-conversation validation
```

The Wave 5 convergence record is [Wave 5 Cross-Slice Convergence Audit](wave5_cross_slice_convergence_audit.md). Wave 5 closes the immediate post-Wave-4 validation/evaluation/operational-control gap without opening polling, service supervision, Pin/Unpin runtime apply, Held Apply/Discard runtime, direct Home-origin trusted formation, or O2/O3.

### E1 evaluation consolidation completed

E1 records the current MVP evaluation decision:

```text
Option A for current MVP
  -> Primary MEM formation remains operator/trusted-admission-path driven
  -> SOUL Lab Home remains real conversation, recall, observation, and governance evaluation
  -> direct Home-origin trusted memory formation remains unproven
  -> Option B trusted Home scene-admission is deferred to E1-R1
```

This decision avoids browser-owned trusted admission metadata and lets MVP evaluation proceed against the already proven local lane. It does not prevent a future bounded Home trusted scene-admission phase.

### Post-Wave-5 next candidates

```text
O1F operational validation

I-5B or Pin/Unpin apply/API/UI/ranking work, if defined
I-7C or Held Apply/Discard runtime/API/UI/durable evidence work, if defined

E1-R1 trusted Home scene-admission path
E1-R2 idempotent character-store bootstrap command
E1-R3 provenance-preserving Primary MEM formation summary
E1-R4 retrieval-response grounding and unsupported-detail suppression

O2 supervised worker service
  -> O3 always-on local operation
```

O2/O3 should remain after O1F unless a concrete evaluation requirement proves that supervised or always-on operation is necessary before the remaining governance UI/validation work.

## MVP completion criteria

MVP can be considered evaluable when the following are all true:

```text
trusted formation lane
  -> durable source and queue
  -> local operation drains eligible work
  -> Primary MEM forms durably
  -> Lab observation shows the evidence

conversation recall lane
  -> SOUL Lab Home real conversation
  -> ordinary M2 / RelayCTX retrieval uses current eligible memories
  -> hidden/prior/prepared/recovery/corrupt/cross-scope candidates are excluded

user governance lane
  -> Correct API/UI and later retrieval convergence
  -> Forget API/UI and later retrieval exclusion convergence
  -> lifecycle visibility is readable without mutating evidence

operations lane
  -> bounded replay-before-queue production rounds
  -> fairness/retry/backoff/recovery/shutdown validation
  -> no runtime-private content leakage in projections or docs
```

The direct Home-origin formation gap is resolved for current MVP evaluation by the E1 Option A decision: MVP formation remains operator/admission-path driven while Home is used for conversation, recall, observation, and governance evaluation. A future E1-R1 phase may replace that decision only by adding a documented trusted scene-admission path.

## Post-MVP roadmap

Post-MVP work should remain outside the MVP unless a later convergence PR explicitly moves it into the MVP boundary.

```text
I-6 Merge / Supersession
  -> reconcile multiple Primary MEM lines under explicit audit

I-8 Secondary MEM consolidation
  -> summarize or consolidate stable evidence after Primary governance is safe

I-9 RelaySOUL proposal / intervention / rollback
  -> persona-level proposal and explicit approval workflow

Voice / TTS / avatar production loop
  -> consume existing text and hint boundaries without changing memory authority

Character-to-character communication
  -> peer transport and conversation governance after single-character memory is stable

Experimental SOUL replacement and memory bootstrap
  -> post-MVP, non-destructive, explicit lab-only work
```

## Sequencing rules

- Do not use a plan update to claim current implementation completion; update [Project Status](../PROJECT_STATUS.md) through the appropriate implementation or convergence PR.
- Do not move a post-MVP item into MVP without naming the evaluation gate it unlocks.
- Do not allow operations work to absorb I1-G replay, B3 queue lifecycle, C2 worker execution, RelayMEM lifecycle, or SOUL Lab mutation authority.
- Do not allow memory-governance work to absorb scheduler, queue, durable-finalization, or worker authority.
- Do not allow a Home-origin request to become persistence-eligible through browser-owned hidden trusted metadata.
- Do not mark O1F/O2/O3 complete through O1E.
- Do not mark Pin/Unpin runtime apply complete through I-5A.
- Do not mark Held Apply/Discard runtime complete through I-7A/B.
- During a declared parallel wave, implementation PRs update only their unique handoff/completion report and implementation-coupled docs; the convergence PR updates this plan, Project Status, indexes, current-target documents, and smoke together.

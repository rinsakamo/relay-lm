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
  - o1f_operational_validation.md
  - phase_i5b_pin_unpin_apply.md
  - phase_i7c_held_apply_discard_runtime.md
  - e1r1_trusted_home_scene_admission.md
  - e1r2_character_store_bootstrap.md
  - e1r3_provenance_preserving_primary_mem_formation_summary.md
  - e1r4_retrieval_response_grounding.md
  - e1r5_primary_mem_recall_candidate_bridge.md
  - e1_evaluation_consolidation.md
  - wave7_cross_slice_convergence_audit.md
  - wave6_cross_slice_convergence_audit.md
  - wave5_cross_slice_convergence_audit.md
---
# RelayLM Project Execution Plan

Last reviewed: 2026-06-29 JST

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
- Primary MEM formation from trusted scene-qualified managed requests and from the E1-R1 route-owned trusted Home gate when explicitly enabled;
- speaker-provenance-safe Primary MEM formation summary so assistant acknowledgement/speculation and scene/trust qualification are not promoted to user facts;
- later-turn Primary MEM retrieval and RelayCTX injection through the M2-preferred path plus the bounded E1-R5 scoped Primary candidate bridge when M2 yields no eligible scoped Primary candidate;
- request-side retrieval-response grounding and unsupported-detail suppression for recalled Primary MEM evidence;
- read-only observation of latest runs, formed memory, held or blocked outcomes, lifecycle state, and used-memory evidence;
- explicit auditable Correct;
- explicit Forget / Hide through API/UI plus validation;
- explicit Pin / Unpin apply through API/UI plus deterministic ranking hint;
- explicit Held Apply / Discard runtime governance through API/UI plus durable content-free decision evidence;
- ordinary retrieval exclusion for hidden, prepared, recovery-required, corrupt, ambiguous, unsafe, cross-scope, and prior physical revisions;
- durable finalization evidence before protected visible release;
- one-record restart replay, retention/isolation cleanup, and crash validation;
- bounded local operation that can drain eligible replay and queue work through explicit caller-invoked rounds;
- caller-invoked O1E stale-recovery/cancellation/shutdown controls and O1F operational validation;
- dry-run-first character-store bootstrap for local evaluation.

MVP does not include:

- browser-owned trusted admission or frontend self-asserted persistence policy;
- always-on daemon/service supervision unless a later explicit MVP gate proves it is required;
- voice, TTS execution, avatar, Live2D, ASR, or peer communication transport;
- Secondary MEM consolidation;
- Merge / Supersession runtime apply unless explicitly pulled into MVP later;
- RelaySOUL proposal/intervention/rollback runtime;
- experimental SOUL replacement or synthetic memory bootstrap.

## MVP execution lanes

```text
Memory governance
  I-4E Forget API/UI                              complete
    -> I-4F Forget validation                     complete
    -> I-5A Pin / Unpin contract/preflight        complete
    -> I-5B Pin / Unpin apply/API/UI/ranking work complete
    -> I-7A/B Held Apply/Discard preflight        complete
    -> I-7C Held Apply/Discard runtime/API/UI/durable evidence complete

Operations
  O1D2 bounded scheduler policy/fairness/pacing complete
    -> O1E stale recovery/cancellation/shutdown complete
    -> O1F operational validation               complete
    -> O2 supervised worker service, if required
    -> O3 always-on local operation, if required

Evaluation
  E1 evaluation consolidation                    complete
    -> E1-R1 trusted Home scene-admission path         complete
    -> E1-R2 idempotent character-store bootstrap command complete
    -> E1-R3 provenance-preserving Primary MEM formation summary complete
    -> E1-R4 retrieval-response grounding and unsupported-detail suppression complete
    -> E1-R5 Primary MEM recall candidate discovery bridge complete

SOUL Lab product
  UI-B1A lifecycle and operation visibility   complete
    -> I-5B Pin / Unpin controls              complete
    -> I-7C Held Governance controls          complete
    -> operator-facing evaluation flow
    -> static bundle serving, if required for local MVP packaging
```

## MVP dependency waves

### Foundation already available for MVP planning

The current MVP plan assumes the completed foundations listed in [Project Status](../PROJECT_STATUS.md): Phase 6 through C2/O0, UI-B0 real Home conversation, Phase I-2 observation, Phase I-3 Correct, I1-GA through I1-GE, I-4B through I-4F, O1A through O1F, UI-B1A, I-5A/I-5B, I-7A/B/I-7C, E1, E1-R1, E1-R2, E1-R3, E1-R4, and E1-R5.

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
O1E stale recovery/cancellation/shutdown complete
I-4F crash/race/security/fresh-conversation validation
```

The Wave 5 convergence record is [Wave 5 Cross-Slice Convergence Audit](wave5_cross_slice_convergence_audit.md). Wave 5 closes the immediate post-Wave-4 validation/evaluation/operational-control gap without opening polling, service supervision, Pin/Unpin runtime apply, Held Apply/Discard runtime, direct Home-origin trusted formation, or O2/O3.

### O1F validation completed

```text
O1F operational validation
  -> corruption / concurrency / saturation / restart / leakage validation
  -> validation-only hardening over caller-invoked O1E/O1D2/O1D1
  -> no polling, sleep, service supervision, worker pool, or always-on operation
```

The O1F completion report is [O1F completion report](../mvp/wave6/o1f_completion_report.md). O1F completion allows O2/O3 to be considered later, but it does not itself prove that supervised or always-on operation is required for MVP.

### Post-O1F next candidates

This historical transition anchor records the candidate set that existed after O1F and before the later Wave 6, Wave 7, and E1-R5 implementation merges. It is kept so frozen convergence smokes can verify the transition while the current next-work list remains Post-E1-R5 / Post-Wave-7.

```text
I-5B Pin / Unpin apply/API/UI/ranking work                 complete in Wave 6
I-7C Held Apply/Discard runtime/API/UI/durable evidence    complete in Wave 6
E1-R1 trusted Home scene-admission path                    complete in Wave 6
E1-R2 idempotent character-store bootstrap command         complete in Wave 6
E1-R3 provenance-preserving Primary MEM formation summary  complete in Wave 7
E1-R4 retrieval-response grounding and unsupported-detail suppression complete in Wave 7
E1-R5 Primary MEM recall candidate discovery bridge        complete post-Wave-7
O2/O3 only after explicit MVP need
```

### Wave 6 completed

```text
I-5B Pin / Unpin apply/API/UI/ranking work
I-7C Held Apply/Discard runtime/API/UI/durable evidence
E1-R1 trusted Home scene-admission path
E1-R2 idempotent character-store bootstrap command
```

The Wave 6 convergence record is [Wave 6 Cross-Slice Convergence Audit](wave6_cross_slice_convergence_audit.md). Wave 6 closes the primary remaining user-governance and local-evaluation ergonomics gaps without adding O2/O3, browser-owned trust, semantic summary-quality changes, RelaySOUL mutation, or media runtime execution.

### Wave 7 completed

```text
E1-R3 provenance-preserving Primary MEM formation summary
  -> user assertion evidence remains distinguishable
  -> assistant acknowledgement/speculation is not promoted to user fact
  -> scene/trust evidence remains qualification metadata
  -> public diagnostics remain content-free

E1-R4 retrieval-response grounding and unsupported-detail suppression
  -> backend-bound grounded recall context
  -> unsupported date/name/preference/quantity/relationship/cause suppression
  -> public diagnostics remain content-free
```

The Wave 7 convergence record is [Wave 7 Cross-Slice Convergence Audit](wave7_cross_slice_convergence_audit.md). The E1-R3 handoff is [E1-R3 Provenance-Preserving Primary MEM Formation Summary](e1r3_provenance_preserving_primary_mem_formation_summary.md) and the completion report is [E1-R3 completion report](../mvp/wave7/e1r3_completion_report.md). The E1-R4 handoff is [E1-R4 Retrieval-Response Grounding](e1r4_retrieval_response_grounding.md) and the completion report is [E1-R4 completion report](../mvp/wave7/e1r4_completion_report.md).

Wave 7 closes the post-Wave-6 E1 evidence-quality lane without adding O2/O3, post-hoc visible response rewriting, browser-owned trust, semantic mutation authority, RelaySOUL mutation, or media runtime execution.

### Post-Wave-7 E1-R5 correction completed

```text
E1-R5 Primary MEM recall candidate discovery bridge
  -> M2 remains the preferred relevance owner
  -> bounded scoped Primary index/log/page fallback only when M2 yields no eligible scoped Primary candidate
  -> shared I-4D lifecycle eligibility still excludes hidden/prepared/recovery/corrupt/prior/cross-scope candidates
  -> public diagnostics remain content-free
```

The E1-R5 handoff is [E1-R5 Primary MEM Recall Candidate Discovery Bridge](e1r5_primary_mem_recall_candidate_bridge.md) and the completion report is [E1-R5 completion report](../mvp/wave7/e1r5_completion_report.md). E1-R5 corrects the E1 proof boundary; current docs must not claim that M2 alone always selects current eligible scoped Primary MEM.

### Post-E1-R5 / Post-Wave-7 next candidates

```text
O2 supervised worker service, only if required
  -> O3 always-on local operation, only if required

Static SOUL Lab bundle serving, only if required for local MVP packaging
```

O2/O3 should remain after the evidence-quality gates unless a concrete evaluation requirement proves that supervised or always-on operation is necessary before local MVP evaluation.

## MVP completion criteria

MVP can be considered evaluable when the following are all true:

```text
trusted formation lane
  -> durable source and queue
  -> speaker-provenance-safe formation summary
  -> local operation drains eligible work
  -> Primary MEM forms durably
  -> Lab observation shows the evidence

conversation recall lane
  -> SOUL Lab Home real conversation
  -> ordinary M2-preferred retrieval uses current eligible memories
  -> E1-R5 bounded scoped Primary candidate bridge covers the no-M2-scoped-candidate gap
  -> hidden/prior/prepared/recovery/corrupt/cross-scope candidates are excluded
  -> backend-bound recall responses are grounded to retrieved evidence
  -> unsupported recall details are suppressed or qualified

user governance lane
  -> Correct API/UI and later retrieval convergence
  -> Forget API/UI and later retrieval exclusion convergence
  -> Pin / Unpin API/UI and ranking hint convergence
  -> Held Apply / Discard API/UI and durable governance evidence
  -> lifecycle visibility is readable without mutating evidence

operations lane
  -> bounded replay-before-queue production rounds
  -> fairness/retry/backoff/recovery/shutdown/operational validation
  -> no runtime-private content leakage in projections or docs
```

E1-R1 means Home-origin trusted admission is available only through the route-owned server gate. It does not allow browser-owned trust metadata. E1-R2 means local store layout can be initialized through an explicit dry-run-first operator command. E1-R3 means Primary MEM formation summary is speaker-provenance-safe. E1-R4 means retrieval responses receive backend-bound grounding and unsupported-detail suppression. E1-R5 means scoped Primary MEM recall can bridge the no-M2-scoped-candidate gap without replacing M2 as preferred relevance owner or adding new mutation/scheduler authority.

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
  -> explicit post-MVP lab work only
```

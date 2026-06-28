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
  - docs/architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md
  - docs/architecture/e1r4_retrieval_response_grounding.md
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
E1-R3 provenance-preserving Primary MEM formation summary: complete
E1-R4 retrieval-response grounding and unsupported-detail suppression: complete
Home can be a trusted formation source only through the E1-R1 route-owned gate; browser-owned trust remains rejected.

Phase I-4A Forget / Hide contract: defined target contract; completed by I-4B through I-4F implementation slices
```

## Current caveats

E1-R4 is request-side only. It builds a backend-bound grounded recall context and instruction from eligible retrieved Primary MEM evidence; it does not add post-hoc visible response rewriting, polling, supervision, O2/O3, browser-owned trust, or new memory mutation authority.

## Immediate dependency-first work

```text
Post-E1-R4 next candidates:
  O2/O3 only after explicit MVP need
  Static SOUL Lab bundle serving, if local packaging requires it
```

## Not yet implemented

- O2 supervised worker service and O3 always-on local operation;
- restore/unhide or physical purge;
- Merge / Supersession;
- Secondary MEM consolidation;
- RelaySOUL proposal/intervention/rollback;
- TTS/audio/avatar/Live2D/ASR execution.

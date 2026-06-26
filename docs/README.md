---
relaylm_doc_type: documentation_index
relaylm_authority: repository_documentation_entrypoint
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - documentation entry points change
  - canonical authority ordering changes
  - placement rules change
relaylm_not_authoritative_for:
  - current runtime behavior
  - exact schema details
  - implementation phase completion claims
relaylm_current_status_source: PROJECT_STATUS.md
---
# RelayLM Documentation

RelayLM documentation is AI-first. Documents must remain correct when retrieved partially; current documents must not rely on a later "supersedes earlier text" correction inside the same file.

## Start here

- [Current project status](PROJECT_STATUS.md) — current implementation boundary through I1-GD, I-4C2, O0, O1A, O1B, O1C, UI-B0, and the local E1 result; Wave 3 is I1-GE, I-4D, and O1D1.
- [Documentation model](DOCUMENTATION_MODEL.md) — document types, metadata, authority, AI reading rules, and the parallel implementation/convergence flow.
- [Pipeline responsibility design](architecture/pipeline_responsibility_design.md) — component responsibility and canonical target order.
- [Pipeline implementation plan](architecture/pipeline_implementation_plan.md) — detailed implementation status and dependency-first sequencing.
- [Post-I3 evaluation and work roadmap](architecture/post_i3_evaluation_work_roadmap.md) — I-4 through I-9, durability, operations, UI, and evaluation gates.
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) — compatibility interpretation.
- [MVP evidence index](mvp/README.md) — historical snapshots and per-PR implementation completion reports.

## Current product-critical boundaries

- [Phase 6 I1-B runtime enqueue and protected source capture](architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md)
- [Phase 6-C1 Primary MEM worker contract](architecture/phase6c1_primary_mem_worker_contract.md)
- [Phase 6-C1-2 one-claimed worker](architecture/phase6c1_one_claimed_primary_worker_handoff.md)
- [Phase 6-C1-5 durable protected source persistence](architecture/phase6c1_durable_protected_source_persistence.md)
- [Phase 6-C2 one queued-job integration](architecture/phase6c2_one_queued_primary_worker_integration.md)
- [O0 local one-job runner](architecture/o0_local_one_job_runner.md)
- [O1A two-lane scheduler contract](architecture/o1a_two_lane_scheduler_contract.md)
- [O1B sealed I1-G replay lane](architecture/o1b_sealed_i1g_replay_lane.md)
- [O1C eligible B2/B3 queue lane](architecture/o1c_eligible_b2_queue_lane.md)
- [I1-G durable-finalization contract and completed GA-GD boundaries](architecture/i1g_pre_enqueue_durable_finalization_contract.md)
- [I1-GD durable-finalization retention and isolation lifecycle](architecture/i1gd_durable_finalization_retention_cleanup.md)
- [Integration I1 Primary MEM two-turn recall](architecture/integration_i1_primary_mem_two_turn_recall.md)
- [Phase I-2 real SOUL Lab observation](architecture/phase_i2_real_soul_lab_observation.md)
- [Phase I-3 auditable Primary MEM Correct](architecture/phase_i3_auditable_primary_mem_correct.md)
- [Phase I-4A Primary MEM Forget / Hide contract](architecture/phase_i4_primary_mem_forget_hide_contract.md)
- [Phase I-4B Primary Current State and Shared Mutation Fence](architecture/phase_i4b_primary_current_state_shared_fence.md)
- [Phase I-4C1 Primary Forget Hidden-Successor Commit](architecture/phase_i4c1_primary_forget_hidden_successor.md)
- [Phase I-4C2 Primary Forget Recovery and Finalization](architecture/phase_i4c2_primary_forget_recovery_finalization.md)
- [SOUL Lab UI-B0 real Home conversation](architecture/soul_lab_ui_b0_real_home_conversation.md)
- [RelayMEM / RelaySLP current / target boundary](architecture/relaymem_slp_current_target.md)
- [RelayMEM MVP implementation plan](architecture/relaymem_mvp_implementation_plan.md)
- [Architecture documentation index](architecture/README.md)

## Current status summary

Phase 6 is complete through B3, C1-0 through C1-5, C2, and the operator-invoked O0 runner. I1-GA through I1-GD are complete: explicit apply mode publishes sealed restart evidence before protected release; one caller-selected sealed record converges through exact C1-5, exact B2, and an immutable content-free completion marker; and one bounded caller-invoked maintenance pass provides retention, orphan isolation, and marker-last lifecycle convergence. I1-GE remains an unimplemented validation-only full production crash proof.

O1A is complete as the pure replay-before-queue round and idle contract. O1B is complete for one bounded sealed I1-G inventory, canonical selected-record reread, and at most one existing I1-GC delegation. O1C is complete for one bounded B2/B3 inventory, due/future classification, canonical reread, server-owned scope resolution, and at most one existing C2 delegation. O1D1 must accept the exact scheduler gates and execute one production round without sleeping. O1D2 fairness/retry-time/backoff/jitter/pacing, O1E stale recovery/shutdown, O1F operational validation, O2 supervision, and O3 always-on operation remain unimplemented. No recurring scheduler loop or automatic continuous processing is complete.

Phase I-2 observation, Phase I-3 Correct, and UI-B0 real Home conversation are complete. Phase I-4A defines the target Forget lifecycle. I-4B completes the read-only resolver/shared-fence/preflight-token-history boundary. Phase I-4C1 is complete for exact token/reason revalidation, immutable prepared evidence, deterministic hidden successor, and M3e publication. Phase I-4C2 is complete for exact prepared resume, operation-scoped M3f/M3g convergence, response-loss replay, and tombstone finalization. I-4D ordinary M2/RelayCTX lifecycle and prior-revision exclusion plus read-only historical lifecycle projection, I-4E API/UI, and I-4F production validation remain incomplete.

The first E1 workstation result proves explicit trusted-scene formation through O0 and separate real Home recall. It does not prove direct Home-origin formation or automatic scheduling.

## Target architecture and post-MVP design

- [Character belief, relationship, and social expression dynamics](architecture/character_belief_relationship_dynamics_design.md)
- [ADR: character-conditioned belief without rewriting observation](adr/character_conditioned_belief_model.md)
- [Experimental SOUL replacement and memory bootstrap](relaysoul/experimental_soul_replacement_memory_bootstrap_design.md)

These documents are target architecture only. Experimental SOUL replacement is explicitly post-MVP and does not alter the ordinary Phase I-9 revision/rollback path.

## Canonical precedence

1. `pipeline_responsibility_design.md` owns component responsibility and canonical target order.
2. `pipeline_implementation_plan.md` owns implementation status and sequencing.
3. Dedicated current contracts own exact bounded behavior.
4. `current_target_migration_guide.md` owns current/target/compatibility interpretation.
5. `docs/mvp/` and `docs/architecture/archive/` are historical evidence.

## Placement rules

- repository-wide current status -> `docs/PROJECT_STATUS.md`
- active and completed bounded handoffs -> `docs/architecture/`
- schemas and contracts -> `docs/contracts/`
- RelaySOUL governance -> `docs/relaysoul/`
- smoke and troubleshooting -> `docs/smoke/`
- historical rationale -> `docs/architecture/archive/`
- MVP snapshots and implementation completion reports -> `docs/mvp/`

## Parallel implementation documentation rule

For a declared parallel wave, each implementation PR must update only its code, tests/workflows, implementation-coupled exact schema/config docs, a unique slice-owned handoff, and one unique `docs/mvp/wave*/<slice>_completion_report.md`. It must not edit the shared status, shared plans, shared indexes, cross-slice current-target documents, previous-wave audit, or repository-wide documentation-boundary smoke merely to mark the slice complete.

After the parallel PRs merge, the wave convergence thread updates Project Status, shared implementation plans, both documentation indexes, the post-phase roadmap, relevant current/target documents, completion-report links, and repository-wide documentation smoke in one PR. The next wave and release/evaluation gate remain closed until that convergence PR is green and merged.

For a non-parallel slice without a reserved convergence thread, the implementation PR may still update all affected current documents atomically. The authoritative rules and reserved shared-file list are in [Documentation Model](DOCUMENTATION_MODEL.md).

## Wave 3 integrated boundary

- I1-GD is complete; I1-GE is the validation-only real process-exit/fresh-restart proof.
- Phase I-4C2 is complete; I-4D owns ordinary M2/RelayCTX lifecycle exclusion and read-only historical lifecycle projection only.
- O1B and O1C are complete; O1D1 owns accepted scheduler gates plus one replay-before-queue production round and returns without sleep.
- O1D2 owns fairness, retry-time, backoff, jitter, and saturation pacing; O1E/O1F own recovery/shutdown and validation.
- The W2-INT authority map and frozen Wave 3 inputs are in [Wave 2 cross-slice convergence audit](architecture/wave2_cross_slice_convergence_audit.md).

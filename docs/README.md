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

- [Current project status](PROJECT_STATUS.md) — current implementation boundary through I1-GC, I-4C1, O0, O1A, O1C, UI-B0, and the local E1 result.
- [Documentation model](DOCUMENTATION_MODEL.md) — document types, metadata, authority, and AI reading rules.
- [Pipeline responsibility design](architecture/pipeline_responsibility_design.md) — component responsibility and canonical target order.
- [Pipeline implementation plan](architecture/pipeline_implementation_plan.md) — detailed implementation status and dependency-first sequencing.
- [Post-I3 evaluation and work roadmap](architecture/post_i3_evaluation_work_roadmap.md) — I-4 through I-9, durability, operations, UI, and evaluation gates.
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) — compatibility interpretation.

## Current product-critical boundaries

- [Phase 6 I1-B runtime enqueue and protected source capture](architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md)
- [Phase 6-C1 Primary MEM worker contract](architecture/phase6c1_primary_mem_worker_contract.md)
- [Phase 6-C1-2 one-claimed worker](architecture/phase6c1_one_claimed_primary_worker_handoff.md)
- [Phase 6-C1-5 durable protected source persistence](architecture/phase6c1_durable_protected_source_persistence.md)
- [Phase 6-C2 one queued-job integration](architecture/phase6c2_one_queued_primary_worker_integration.md)
- [O0 local one-job runner](architecture/o0_local_one_job_runner.md)
- [O1A two-lane scheduler contract](architecture/o1a_two_lane_scheduler_contract.md)
- [O1C eligible B2/B3 queue lane](architecture/o1c_eligible_b2_queue_lane.md)
- [I1-G durable-finalization contract, publication, replay, and remaining retention boundary](architecture/i1g_pre_enqueue_durable_finalization_contract.md)
- [Integration I1 Primary MEM two-turn recall](architecture/integration_i1_primary_mem_two_turn_recall.md)
- [Phase I-2 real SOUL Lab observation](architecture/phase_i2_real_soul_lab_observation.md)
- [Phase I-3 auditable Primary MEM Correct](architecture/phase_i3_auditable_primary_mem_correct.md)
- [Phase I-4A Primary MEM Forget / Hide contract](architecture/phase_i4_primary_mem_forget_hide_contract.md)
- [Phase I-4B Primary Current State and Shared Mutation Fence](architecture/phase_i4b_primary_current_state_shared_fence.md)
- [Phase I-4C1 Primary Forget Hidden-Successor Commit](architecture/phase_i4c1_primary_forget_hidden_successor.md)
- [SOUL Lab UI-B0 real Home conversation](architecture/soul_lab_ui_b0_real_home_conversation.md)
- [RelayMEM / RelaySLP current / target boundary](architecture/relaymem_slp_current_target.md)
- [RelayMEM MVP implementation plan](architecture/relaymem_mvp_implementation_plan.md)
- [Architecture documentation index](architecture/README.md)

## Current status summary

Phase 6 is complete through B3, C1-0 through C1-5, C2, and the operator-invoked O0 runner. I1-GA, I1-GB, and I1-GC are complete: explicit apply mode publishes sealed restart evidence before protected release, and one caller-selected sealed record can converge through exact C1-5, exact B2, and an immutable content-free completion marker. I1-GD retention/cleanup and I1-GE full production crash validation remain incomplete.

O1A is complete as the pure replay-before-queue round and idle contract. O1B is complete for one bounded sealed I1-G inventory, canonical selected-record reread, and at most one existing I1-GC delegation. O1C is complete for one bounded B2/B3 inventory, due/future classification, canonical reread, server-owned scope resolution, and at most one existing C2 delegation. O1D fairness/backoff, O1E stale recovery/shutdown, O1F operational validation, O2 supervision, and O3 always-on operation remain unimplemented. No production scheduler loop or automatic continuous processing is complete.

Phase I-2 observation, Phase I-3 Correct, and UI-B0 real Home conversation are complete. Phase I-4A defines the target Forget lifecycle. I-4B completes the read-only resolver/shared-fence/preflight-token-history boundary. Phase I-4C1 is complete for exact token/reason revalidation, immutable prepared evidence, deterministic hidden successor, M3e publication, and hidden/recovery-required resolution. I-4C2 recovery/tombstone, I-4D M2 exclusion, I-4E API/UI, and I-4F production validation remain incomplete.

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
- MVP snapshots -> `docs/mvp/`

When an implemented boundary changes state, update Project Status, the implementation plan, both documentation indexes, the affected dedicated contract, the post-I3 roadmap, relevant current/target documents, and status-checking smoke scripts in the same change.

<!-- O1B_DOC_INDEX -->
- [O1B Sealed I1-G Replay-Lane Discovery](architecture/o1b_sealed_i1g_replay_lane.md) — bounded secure discovery, canonical reread, and one I1-GC delegation.

O1B is complete. O1D through O1F, O2, and O3 remain unimplemented; O1B is not a scheduler loop or always-on service.

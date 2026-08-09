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
  - accepted target contract implementation sequencing changes
  - post-RT-1 personality program sequencing changes
relaylm_not_authoritative_for:
  - current implemented runtime status
  - component responsibility and canonical target order
  - exact schema details
  - historical implementation evidence
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - ../release/v0.1-release-readiness.md
  - pipeline-responsibilities.md
  - file_first_character_workspace_design.md
  - character_template_creation_flow.md
  - current_target_migration_guide.md
  - relaymem_slp_current_target.md
  - analyzer_candidate_governance.md
  - acg1_analyzer_candidate_governance_contract.md
  - acg2_grounded_recall_detail_safety.md
  - acg3_retrieval_query_normalization.md
  - acg4_reference_intent_analyzer.md
  - acg5_relayemo_scene_cleanup.md
  - acg6_scene_wiki_classifier.md
  - cw_a1_file_first_source_tree_parser_contracts.md
  - cw_a2_workspace_compiler_projections.md
  - cw_a3_character_workspace_ui_rebuild.md
  - cw_a4_slp_workspace_maintenance_candidates.md
  - cw_a5_character_creation_templates_showcase_import.md
  - e1r5_primary_mem_recall_candidate_bridge.md
  - ../evidence/waves/e1r5_post_wave7_correction_convergence_audit.md
  - o2_supervised_scheduler_service.md
  - o3_always_on_local_scheduler.md
  - relayatn_reflex_layer_design.md
  - pm_d5_relaymem_flat_store_compatibility_removal.md
  - pm_d6_relayint_native_artifact_relayref_wrapper_removal.md
  - pm_d7_runtime_install_hook_fold_in.md
  - ../adr/0003-subjective-mem-direction.md
  - ../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md
  - ../adr/0005-subjective-mem-storage-authority.md
  - memory/formation.md
  - runtime/request-response-pipeline.md
  - ../contracts/governed-evidence-contract-family.md
  - ../contracts/relayctx-session-evidence-overlay.md
  - ../contracts/shared-assessment-subjective-mem.md
  - ../contracts/subjective-mem-storage-authority-and-commit-protocol.md
  - st1_subjective_mem_commit_runtime.md
  - lc1a_subjective_mem_correct.md
  - subjective-mem-forget-runtime.md
  - subjective-mem-restore-runtime.md
  - subjective-mem-consolidate-runtime.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - ../contracts/subjective-mem-canonical-markdown-v1.md
  - documentation-governance.md
  - repository-maintenance-system.md
  - ../operations/documentation-synthesis-and-retirement.md
---
# RelayLM Project Execution Plan

Last reviewed: 2026-08-09 JST

## Purpose

This document is the single plan and roadmap authority for RelayLM execution. It owns dependency-first sequencing, MVP boundaries, MVP completion criteria, and post-MVP roadmap ordering. It does not own current implementation status; read [Project Status](../PROJECT_STATUS.md) first.

It also owns the repository-wide order of the post-RT-1 program recorded in [Post-RT-1 repository-wide sequencing](#post-rt-1-repository-wide-sequencing). It does not own personality semantics: SOUL, SELF, REL / OTHER MODEL, GOAL, Working Self, SLP write authority, and Reflective / Self-Model Distillation are owned by the accepted [Character Personality and Experience Architecture](character/personality-and-experience.md), and this plan neither restates nor redefines them.

## MVP execution lanes

```text
Completed runtime and governance foundation
  I-4E Forget API/UI                              complete
    -> I-4F Forget validation                     complete
    -> I-5A Pin / Unpin contract/preflight        complete
    -> I-5B Pin / Unpin apply/API/UI/ranking work complete
    -> I-7A/B Held Apply/Discard preflight        complete
    -> I-7C Held Apply/Discard runtime/API/UI/durable evidence complete

Analyzer Candidate Governance
  ACG-0 P0 RelayREL / RelaySCN / RelayEMO ordering boundary complete
    -> ACG-1 Analyzer Candidate Governance contract complete
    -> ACG-2 Grounded Recall Query Detail Analyzer complete
    -> ACG-3 RelayMEM Query Analyzer / Retrieval Hint Normalization complete
    -> ACG-4 RelayREF / RelayINT Reference Analyzer consolidation complete
    -> ACG-5 RelayEMO scene ownership cleanup complete
    -> ACG-6 SCN structured classifier and scene-wiki integration complete

Character Workspace reset
  CW-A1 file-first source tree and parser contracts complete
    -> CW-A2 workspace compiler projections and KV-cache tiers complete
    -> CW-A3 Character Workspace UI rebuild complete
    -> CW-A4 SLP-maintained MEM/SCENE/REL wiki candidates and proposals complete
    -> CW-A5 character creation, templates, and showcase import complete

Operations
  O1D2 bounded scheduler policy/fairness/pacing complete
    -> O1E stale recovery/cancellation/shutdown complete
    -> O1F operational validation               complete
    -> O2 supervised worker service             complete as opt-in local scheduler service
    -> O3 always-on local operation             complete as opt-in local CLI/process wrapper

Evaluation
  E1 evaluation consolidation                    complete
    -> E1-R1 trusted Home scene-admission path         complete
    -> E1-R2 idempotent character-store bootstrap command complete
    -> E1-R3 provenance-preserving Primary MEM formation summary complete
    -> E1-R4 retrieval-response grounding and unsupported-detail suppression complete
    -> E1-R5 Primary MEM recall candidate discovery fallback complete
  durable-memory E2 value smoke after O2/O3 scheduler draining evidence complete as local human-reviewed v0.1 readiness evidence
```

## MVP completion criteria

For the file-first Character Workspace reset, MVP completion requires that target Character Workspace surfaces and projections remain clearly separated from current implementation status until dedicated implementation slices land.

CW-A3 closes the browser UI rebuild portion of the reset. It is presentation-only: Home stays on the existing RelayLM `/v1/chat/completions` authority path, and Character / Scenes / Relationships / Memory Wiki / Runtime / Advanced default to content-free projections, source-status vocabulary, and explicit Advanced separation for governance internals.

CW-A4 closes the first RelaySLP-maintained workspace maintenance slice for MEM / SCENE / REL wiki candidates and proposals only. It is dry-run-first, produces content-free public projections, writes only allowlisted inbox/proposal artifacts when explicitly requested, and preserves the uppercase source approval boundary. CW-A4 does not implement direct uppercase source rewrites, RelaySOUL apply/rollback, current-turn response effects, runtime prompt injection, queue/worker/O2/O3 authority, or replacement of RelayMEM lifecycle, RelaySCN scene, or RelayREL relationship runtime authorities.

CW-A5 closes the first character creation/template slice. It implements deterministic bundled templates, Quick Create, Advanced Create staging, showcase use-as-is/use-as-starter behavior, local template folder/zip validation, loopback creation APIs, explicit CLI dry-run/write commands, zero-character UI routing, and local CW-A2 build generation after approved commit. CW-A5 does not implement remote registries, unbounded downloads, automatic default active character restoration, normal-path LLM generation, runtime prompt injection changes, or active-character auto-selection after commit.

Phase I-2 is complete for read-only observation of latest runs, formed memory, held or blocked outcomes, lifecycle state, and used-memory evidence. That observation boundary remains read-only and cannot authorize repair, retrieval, mutation, or source-body exposure.

O2/O3 close the explicit opt-in local scheduler operation need for current MVP work. They do not make scheduling app-embedded, browser-owned, default-on, or independently mutation-authoritative. Durable-memory E2 value smoke is complete as a separate, local-only, human-reviewed evaluation scenario after O2/O3 draining evidence; it does not add runtime authority or commit content-bearing comparison artifacts.

## v0.1 release readiness boundary

The current v0.1 readiness assessment is [v0.1 Release Readiness Assessment](../release/v0.1-release-readiness.md); the separate frozen tag receipt is [v0.1 Final Main-HEAD Validation and Tag Receipt](../evidence/releases/v0.1-final-main-validation-tag-receipt.md). v0.1 readiness means the MVP implementation lanes listed above are complete, the durable-memory E2 value smoke has local human-reviewed evidence, the final main-HEAD validation passed, and the remaining items below are post-v0.1 decision debt rather than v0.1 blockers.

RelayATN is registered only as a gated post-v0.1 / post-voice-out candidate. This plan authorizes ATN-0 planning registration only and does not authorize implementation, runtime behavior changes, default-on resident processing, multi-user admission policy, or disclosure/memory authority.

## Post-MVP decision debt registry

Open or remaining decision debt:

- PM-D1 RelaySOUL gate design-freeze relation
- PM-D2 RelayINT -> RelayMEM relayint_intent_artifact legacy compatibility scope; evaluate closure or absorption after PM-D6 if the native artifact closes the legacy artifact scope
- PM-D4 client history exclusion default-off deployment decision
- PM-D9 analyzer candidate governance and multilingual schema policy follow-through after ACG-1 through ACG-6

Completed post-MVP debt:

- PM-D3 RelayEMO/RelaySCN scene_state ownership closed by P0-PIPE request-path ordering validation
- PM-D5 RelayMEM flat-store compatibility removal
- PM-D6 RelayINT native artifact / RelayREF wrapper removal
- PM-D7 runtime install hook fold-in
- PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in complete in PR #491

Implementation order for large compatibility removals and fold-ins completed as:

```text
PM-D5 -> PM-D6 -> PM-D7 -> PM-D8
```

PM-D3 was closed by P0-PIPE: RelayREL now precedes RelaySCN, RelaySCN owns same-turn normalized scene policy, and input-side RelayEMO no longer provides the normalized `scene_state` fallback. PM-D8 was historically related to PM-D5 because both touched Primary recall layout discovery and adapter/root handling. PR #491 closes PM-D8 by folding the former E1-R5 bridge behavior into canonical Primary recall while leaving the former bridge module compatibility no-op only.

Future RelaySCN-owned `scene_state` or scene-wiki work must be handled through dedicated RelaySCN or Character Workspace follow-up slices and must not be treated as remaining PM-D3 debt. ACG-6 does not add Character Workspace parser/compiler/UI, scene-wiki page mutation, or permissive runtime authority from classifier output alone.

## Contract-aligned implementation debt migration program

The governed Evidence, CTX-OVL, Shared Assessment / Subjective MEM, and Subjective MEM storage contracts are accepted target authorities. Their acceptance does not mean that the corresponding runtime, storage, migration, or deployment behavior is implemented. The current Primary MEM, queue, worker, lifecycle, scheduler, and Retrieval implementation remains the current implementation and the characterization/migration base until a later series explicitly replaces each owned boundary.

The dependency-first program is registered as:

```text
EV-1 Governed Evidence runtime foundation
  ├─> OVL-1 CTX-OVL participant-private vertical slice
  └─> ASM-1 Shared Assessment runtime foundation
         -> SM-1 Subjective MEM decision/result vertical slice
              -> ST-1 Markdown + operations commit protocol
                   -> LC-1 lifecycle migration
                        -> RT-1 Retrieval projection and hard cutover

normal-route target convergence
  = OVL-1 + RT-1 + their accepted prerequisite series
```

The series own the following bounded outcomes:

- **EV-1 Governed Evidence runtime foundation** implements the minimum single-principal, private-conversation Contract 1 path: canonical SourceEvent identity, explicit capture/admission, current authorization, assistant-response Evidence binding, coverage/checkpoint references, and producer/consumer validation. It does not enable unbounded client-history capture, multi-user access, export, replication, or purge.
- **OVL-1 CTX-OVL participant-private vertical slice** depends on EV-1 and implements bounded, rebuildable, non-durable RelayCTX working state for the first supported `participant` / `participant_private` partition. It adds exact Contract 1 binding, operation-time TTL, selection, invalidation, restart rebuild, bounded catch-up, and a content-free Reflex Snapshot. Unsupported partition or shared-scene behavior remains fail closed until its own later slice.
- **ASM-1 Shared Assessment runtime foundation** depends on EV-1 and implements character-independent Shared Assessment revisions, one logical current-state selector, formation-time authorization receipts, and the split Assessment Pass boundary. It cannot write Subjective MEM.
- **SM-1 Subjective MEM decision/result vertical slice** depends on ASM-1 and implements one end-to-end `create` path with exact assessment, character, scope, policy-revision, decision, result, and current-state linkage. The bounded implementation is documented in [SM-1 Subjective MEM Create Runtime](sm1_subjective_mem_create_runtime.md): it remains default-off, character-private, prepared-only, non-retrievable, and stops before ST-1 canonical publication. Similarity remains candidate generation only. SOUL-conditioned proposal generation cannot become production-authoritative until PM-D1 is resolved.
- **ST-1 Markdown + operations commit protocol** depends on the SM-1 record shape and implements the first canonical `create` publication using a prepared immutable post-image, canonical Markdown, a matching durable operations receipt, scoped idempotency, digest-based caller-invoked recovery, and rebuildable projection fencing. The bounded implementation is documented in [ST-1 Subjective MEM Commit Runtime](st1_subjective_mem_commit_runtime.md) and [Subjective MEM Canonical Markdown v1](../contracts/subjective-mem-canonical-markdown-v1.md): it remains default-off, create-only, single-host, and POSIX-apply-only; logical Retrieval eligibility does not wire ordinary Retrieval.
- **LC-1 lifecycle migration** depends on ST-1 and ports existing characterization-backed operations in bounded order: Correct, Forget, Pin/Unpin, Restore, then Consolidate. [LC-1A Subjective MEM Correct Runtime](lc1a_subjective_mem_correct.md) implements the exact `active -> active` Correct slice with an immutable canonical successor, shared mutation fence, content-free intent/receipt/idempotency state, and caller-invoked forward recovery. [LC-1B Subjective MEM Forget Runtime](subjective-mem-forget-runtime.md) implements the exact `active -> hidden` Forget slice with an immutable hidden successor, content-free anti-reformation tombstone, one canonical anti-reformation evaluator, deterministic idempotency, and caller-invoked forward recovery. LC-1C Pin/Unpin implements exact current `active -> pinned` and `pinned -> active` immutable successors while preserving semantic payload and using the shared lifecycle publication engine with content-free durable records. [LC-1D Subjective MEM Restore Runtime](subjective-mem-restore-runtime.md) implements the exact current `hidden -> active` immutable successor with authenticated Forget lineage, immutable tombstone-release records, shared lifecycle publication, deterministic idempotency, and caller-invoked forward recovery. [LC-1E Subjective MEM Consolidate Runtime](subjective-mem-consolidate-runtime.md) implements the exact current active Primary-to-Secondary immutable successor while preserving semantic payload and enforcing the exact lifecycle and lower-commit gate triples before durable reads. LC-1 is complete through Consolidate. Existing Primary MEM lifecycle code and tests remain migration evidence. Purge stays outside this series until a separate irreversible authority is accepted.
- **RT-1 Retrieval projection and hard cutover** depends on ST-1 and the completed LC-1 eligibility boundaries. [RT-1 Subjective MEM Retrieval Projection and Hard Cutover](subjective-mem-retrieval-projection-hard-cutover.md) defines the accepted ordered RT-1A through RT-1D boundary. RT-1A contract and projection foundation is complete in PR #774; RT-1B projection builder and deterministic rebuild is complete in PR #779; RT-1C shadow adapter, grounding handoff, and usage ledger is implemented in PR #784 as three bounded owners — exact canonical-page-bound selection and private handoff preparation, temporary content-free characterization, and a durable content-free usage ledger that seals admission only after exact durable success. RT-1D-S1 reader seams completed in PR #789 with resulting main `b272edb78602032009d4882a6244883cce610b86`, extracting existing managed-chat, Retrieval, and Primary recall reader responsibilities into bounded owners while preserving exact public behavior, stage order/offload/timing, diagnostics, Retrieval artifacts, Primary security/lifecycle/fallback behavior, and the RelayINT `metadata.ctx` / `ctx_handoff_guess` Mapping contract. S1 is a behavior-preserving structural prerequisite only: it enables no ordinary Subjective MEM Retrieval, changes no Primary MEM serving authority, and adds no RT-1D configuration, binding, durable cutover state, reader or writer decisions, fences, finalized receipt, retirement, persistence, recovery, worker, queue, scheduler, API, or UI behavior. Its mandatory P8 completed in PR #790 with exact resulting main `3e20274f18306f7db2410fd5239051411b9c052b`. RT-1D-S2 worker seams completed in PR #791 with resulting main `31b700a2db0af7819f761d51bd946ff6798eb4c9`. S2 extracted checkpointed Primary pipeline request construction and execution into `relaylm/_relaymem_slp_primary_worker_pipeline.py`, and extracted one-queued-job claim, source preparation, worker invocation, prepared-scope release, and terminal cleanup into `relaylm/_relaymem_slp_one_queued_job_runner_execute.py`. It preserved public request, result, and projection schemas and import locations; patchable module-level callables; claim revalidation, lease renewal counts, checkpoint order, protected-source release order, status/reason bytes, retry and terminal transitions; and durable queue/store/page/index/log bytes plus fault, crash, and recovery behavior. S2 remains a behavior-preserving structural prerequisite only and added no cutover binding, configuration, authority decision, Primary fence, Subjective serving, fallback change, retirement, scheduler/queue/store semantics, or new persistence/recovery authority. PR #792 completed the S2 mandatory P8 current-authority sync with exact resulting main `7e4fb4383dc6c1229d488ac200132b66f6b65bba`. The monolithic S3 behavior-preserving candidate returned to P1 with no persistent changes because it crossed the structural gates. PR #793 merged the monolithic S3 P1 Return architecture amendment with exact result `5011eaaddd895b434f3d870dcf2206527725629c`. RT-1D-S3A Correct core seams completed in PR #794 with exact resulting main `2d05a41235e396ac82d536437ed8e5568f617253` as a behavior-preserving Primary-only structural prerequisite. Its mandatory same-lane P8 completed in PR #795 with exact resulting main `bc27c25d0b745fc2d9927e9e21179b14cd337141`. RT-1D-S3B Forget core seams completed in PR #796 with exact resulting main `b75df848bf3982e00f67969c016ba1f28dd93427`; PR #797 is the mandatory S3B P8 current-authority synchronization. S3C completed in PR #798 with exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`. The mandatory S3C P8 current-authority synchronization PR #799 merged with exact resulting main `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`. RT-1D-R1 durable preparation is complete in PR #801; PR #803 completed with exact result `eee986422b45c50e0d9ad0528e863457be4db9a1` and no P8; the renewed R2 attempt returned at P1 without mutation; and live-root budget amendment PR #804 completed with exact result `00ba475c689631520538b7531022603447f11bd0` and no P8. The following R2 attempt returned at P1 again without mutation and is recorded in closed tree-neutral Draft PR #805 head `733b38fd3e74dcc542dd1c8f2ec1353a2cab6a95`; queued-runner root budget amendment PR #806 completed with exact result `cd8ce6e05b6476b08ecf25a5100fb0c3f0e77644`, the next R2 attempt returned at P1 in closed tree-neutral Draft PR #807 head `00991760b3070597d6b763a0b3ffc2eb820435f2`, and the staged writer-fence and smoke-carriage budget amendment PR #808 completed with exact result `758c160e1ee71bb9ad67fe10234e5a38c03c6a3d` and no P8. RT-1D-R2A decision owner and managed finalization carriage completed in PR #809 with exact result `0f0b88a0bd601d1cd14b830ca209a26107f62430`, and mandatory R2A P8 PR #810 completed with exact result `5822b01fd4642c89c39a2518672191bf1a8da115`. Primary MEM remains the sole ordinary served memory and Retrieval authority. Subjective ordinary retrieval remains disabled and unwired. No cutover, authority switch, serving, fallback, or retirement change occurred. RT-1D-R1 durable preparation is complete in PR #801; RT-1D-R2B implementation PR #811 and mandatory P8 PR #812 are complete; RT-1D-R2C is complete in PR #814 with exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`; at that historical point, RT-1D-R2D was next and had not started. RT-1B remains default-off and unwired from ordinary Retrieval; RT-1C remains default-off, explicit shadow-only, and unwired from ordinary Retrieval without changing Primary authority. Primary MEM remains the sole ordinary served memory and Retrieval authority. S1, S2, S3A, S3B, and S3C plus each mandatory P8/resulting-main verification were completed before the fresh RT-1D runtime transaction began with R1. No two transactions overlap. The series implements exact-current-revision selection, lifecycle/mutation fail-closed behavior, durable content-free usage events, projection rebuild equivalence, old/new characterization comparison, writer fencing, one-authority cutover, temporary-adapter removal, and retirement of replaced readers/writers.

  Every present-tense authority, default-off, unwired, and shadow-only statement in the RT-1 bullet above is the retained record of the RT-1 series as it was executed, scoped to the earlier points at which each sentence was written. None of them describes current state. RT-1 is complete: RT-1D-R4 one-authority activation merged as PR #834 with mandatory P8 PR #835, and RT-1D-R5 immediate retirement merged as PR #907 with mandatory P8 PR #929. The ordinary Primary reader is retired, the temporary RT-1C characterization and RT-1D-R3 rehearsal execution owners are deleted, and Primary MEM is not universally the sole ordinary served memory and Retrieval authority.

Decision gates apply narrowly:

- PM-D4 must be resolved before any new client-history capture becomes default-on; EV-1 may proceed with explicit route-owned capture while the existing default-off boundary remains.
- PM-D9 must be resolved before multilingual Assessment generation or analyzer/schema policy becomes production-default; deterministic record plumbing and contract validation may proceed first.
- PM-D1 must be resolved before SOUL-conditioned Subjective Formation apply or RelaySOUL intervention/rollback is treated as implemented.
- PM-D2 closure or absorption remains separately governed and must not be silently folded into this program.

Implementation and cleanup rules:

- Each series lands through an atomic PR or an explicitly coordinated atomic set with exact producer, consumer, schema/version, feature posture, migration effect, rollback boundary, and validation matrix.
- New writers and authority-changing readers begin default-off or dry-run-first unless an owning contract and reviewed deployment decision explicitly permit otherwise.
- `docs/PROJECT_STATUS.md` is updated only after exact-head validation proves an implementation boundary, including a pure contract foundation, has landed; plan registration alone never changes current implementation status.
- The existing Primary MEM M3/B/C/I/O paths, lifecycle modules, fixtures, smokes, and operator paths cannot be classified as dead, deleted, renamed, or consolidated while they remain a characterization, rollback, migration, or runtime dependency.
- Repository simplification and documentation hard cutover remain parallel, separately governed tracks. Overlap with this program requires shared-path and authority-reference reconciliation; inventory evidence alone cannot authorize deletion or debt closure.
- Permanent dual-read, dual-write, precedence fallback, or two live canonical memory authorities are prohibited. Any compatibility adapter must name its removal gate and may not become a second semantic authority.
- Current-user-data migration, backup/restore, platform support, and irreversible purge require their own accepted implementation or operations authority before execution.

This registration authorizes preparation of bounded implementation PRs in the dependency order above. It does not itself authorize runtime default-on behavior, migration of user data, deletion of existing assets, or the final authority cutover.

## Post-RT-1 repository-wide sequencing

The RT-1 series and the legacy Lane C critical implementation program are complete. RT-1D-R5 immediate retirement merged as PR #907 and its mandatory P8 merged as PR #929, so the ordinary Primary reader and its ranking and fallback path are retired and only explicitly classified read-only Primary history, observation, lifecycle, and admin projections survive. No RT-1 slice is in progress, unstarted, or uniquely next.

This section owns the repository-wide order from that completion to the character experience. It is planning-only registration: it authorizes no runtime, configuration, contract, schema, test, or workflow change, and no slice below may begin merely because it is registered here.

```text
RT-1 / Lane C legacy program                       COMPLETE
       ↓
Lane R  R5 governed core package migration
       +
Lane D  D5 / D6 canonicalization and final retirement
       ↓
Lane D  PD-1 Personality responsibility convergence
       ↓
Lane D  PD-2 exact Personality contracts
       ↓
Lane C  Personality Core
          PC-1 Personality State
            -> PC-2 Working Self
            -> PC-3 SLP automatic personality updates
            -> PC-4 Reflective Distillation
       ↓
9B end-to-end personality evaluation
       ↓
Character Presence / PWA / voice / avatar experience
```

### Preserved lane responsibilities

The three lanes keep their accepted separation, and the personality program never collapses them:

- **Lane R** owns repository maintenance and package migration. It moves paths and packages and never implements SELF, GOAL, REL / OTHER MODEL, Working Self, SLP personality writes, or Reflective Distillation.
- **Lane D** owns canonical responsibility convergence and exact contracts. It decides which component owns which responsibility and freezes the contracts, and never changes runtime authority.
- **Lane C** owns authority-changing semantic and runtime implementation. It may begin only after the responsibility and contract convergence it depends on is complete.

Detailed stage definitions remain owned by [Repository Structure and Documentation Canonicalization Plan](../planning/repository-structure-migration.md); lane-local continuation and PR convergence remain owned by [Workstream Orchestration, Lane-Local Continuation, and Stable PR Convergence](../planning/workstream-orchestration.md). Current implementation status remains owned by [Project Status](../PROJECT_STATUS.md).

### Lane R R6 boundary

Lane R R6 Primary MEM disposition remains required repository cleanup after R5. It is **not** a blanket prerequisite for Personality Design or Personality Core, because the ordinary Primary reader is already retired.

A specific later slice is blocked by R6 only when it has a concrete dependency on unresolved R6 work: an exact path, import, caller, recovery surface, or retained authority that R6 has not yet disposed of. Absent such a dependency, PD and PC slices may proceed in parallel with R6 under the ordinary path- and authority-disjointness rules. A free lane slot never authorizes skipping a concrete dependency, and R6 is never cited as a general gate.

### Lane D Personality Design registration

PD-1 and PD-2 are registered future Lane D work. They open only after Lane R R5 and Lane D D6 are complete.

**PD-1 Personality responsibility convergence.** Converge the existing canonical responsibilities that the accepted personality architecture actually changes, especially:

```text
SOUL / SELF boundary
REL / OTHER MODEL ownership
Character Workspace ownership
SLP maintenance ownership
context / Working Self responsibility
```

PD-1 revises only the responsibility nodes the accepted target changes. It does not reopen stable Evidence, storage, retrieval, or lifecycle authorities unless an exact dependency requires it.

**PD-2 exact Personality contracts.** Define the exact Personality State and Working Self contracts before any implementation begins. PD-2 completes before PC-1 starts.

### Lane C Personality Core registration

PC-1 through PC-4 are registered future Lane C work. PC-1 may not begin until PD-2 is complete, and the four slices stay in order:

- **PC-1 Personality State** implements the SELF, GOAL, and minimal REL / OTHER MODEL state foundations.
- **PC-2 Working Self** implements Working Self and its bounded per-turn semantic projection.
- **PC-3 SLP automatic personality updates** implements automatic validated updates of SELF, REL / OTHER MODEL, and GOAL, while SOUL remains outside automatic write authority.
- **PC-4 Reflective Distillation** implements governed Reflective / Self-Model Distillation, using a stronger model to produce grounded candidate SELF deltas that are adopted only through the accepted update authority.

Each slice is a separate authority-changing Lane C transaction under the ordinary single-writer, atomic-PR, and mandatory-P8 rules. The semantics of every term above are owned by [Character Personality and Experience Architecture](character/personality-and-experience.md); this plan registers only their order.

### Evaluation before Character Presence

The resulting architecture is validated first with a local 9B-class model end to end — conversation, context projection, persistence, SLP personality-state updates, and identity continuity — before Character Presence work begins.

Character Presence, the mobile-first PWA, voice, and avatar experience follow that evaluation. They are not scheduled before it, and a completed PC slice alone never authorizes them.

### Ordering authority note

This plan owns repository-wide sequencing; the accepted personality architecture owns semantics. Where the phase grouping in that document and the order recorded here differ — it groups Reflective Distillation after the character-experience phase, while this plan sequences PC-4 before the 9B evaluation and before Character Presence — the order recorded here governs repository execution, and the semantic definitions there remain unchanged and authoritative.

## Current next work

RT-1 is complete. RT-1D-R5 immediate retirement implementation merged as PR #907 and its mandatory P8 merged as PR #929, so no RT-1 slice is in progress, unstarted, or uniquely next, and the ordinary Primary reader is retired rather than fenced. The repository-wide order from here is owned by [Post-RT-1 repository-wide sequencing](#post-rt-1-repository-wide-sequencing).

The currently eligible repository work is:

```text
Lane R  R5 governed core package migration              eligible now
Lane D  D5 -> D6 canonicalization and final retirement  continue to completion
Lane R  R6 Primary MEM disposition                      required cleanup after R5
Lane C                                                  idle until PD-2 completes
```

Completed foundation retained for reference:

```text
Character Workspace reset
  CW-A1 file-first source tree and parser contracts complete
  CW-A2 workspace compiler projections and KV-cache tiers complete
  CW-A3 Character Workspace UI rebuild complete
  CW-A4 SLP-maintained MEM/SCENE/REL wiki candidates and proposals complete
  CW-A5 character creation, templates, and showcase import complete

Completed evaluation evidence:
  durable-memory E2 value smoke after O2/O3 scheduler draining evidence complete as local human-reviewed v0.1 readiness evidence

Completed post-MVP debt:
  PM-D3 RelayEMO/RelaySCN scene_state ownership closed by P0-PIPE
  PM-D5 RelayMEM flat-store compatibility removal complete
  PM-D6 RelayINT native artifact / RelayREF wrapper removal complete
  PM-D7 runtime install hook fold-in complete
  PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in complete
```

### Retained RT-1 program registry (historical)

The registry below is the retained record of the completed contract-aligned implementation debt program, preserved as historical evidence of how the RT-1 series was executed.

Every progress marker inside its RT-1 subtree — including `in progress`, per-stage progress, `next`, and `not started` — describes the repository only at the earlier point at which that line was written. None of them describes current state. RT-1A through RT-1D are complete, RT-1D-R4 one-authority activation merged as PR #834 with mandatory P8 PR #835, and RT-1D-R5 immediate retirement merged as PR #907 with mandatory P8 PR #929.

```text
Registered contract-aligned implementation debt:
  EV-1 Governed Evidence runtime foundation                            complete / default-off
    -> OVL-1 CTX-OVL participant-private vertical slice               complete / default-off / participant-private only
    -> ASM-1 Shared Assessment runtime foundation                     complete / default-off
         -> SM-1 Subjective MEM decision/result vertical slice        complete / default-off / prepared-only
              -> ST-1 Markdown + operations commit protocol           complete / default-off / create-only / POSIX apply
                   -> LC-1 lifecycle migration                        complete / LC-1A Correct, LC-1B Forget, LC-1C Pin/Unpin, LC-1D Restore, and LC-1E Consolidate implemented / default-off
                        -> RT-1 Retrieval projection and hard cutover in progress / RT-1A, RT-1B, and RT-1C complete
                             -> RT-1B projection builder and rebuild complete in PR #779 / default-off / unwired
                             -> RT-1C shadow adapter, grounding handoff, and usage ledger complete in PR #784 / default-off / shadow-only / unwired
                             -> RT-1D structural P1 Return / runtime implementation complete through R3
                                -> RT-1D-S1 reader seams complete in PR #789
                                   -> S1 mandatory P8 current-authority sync in PR #790 -> exact resulting main 3e20274f18306f7db2410fd5239051411b9c052b
                                      -> RT-1D-S2 worker seams complete in PR #791 -> exact resulting main 31b700a2db0af7819f761d51bd946ff6798eb4c9
                                         -> S2 mandatory P8 current-authority sync in PR #792 -> exact resulting main 7e4fb4383dc6c1229d488ac200132b66f6b65bba
                                            -> RT-1D-S3 P1 architecture amendment -> verify amendment resulting main before S3A
                                               -> RT-1D-S3A Correct core seams PR #794 -> P8 PR #795 result bc27c25d0b745fc2d9927e9e21179b14cd337141
                                                  -> RT-1D-S3B Forget core seams PR #796 result b75df848bf3982e00f67969c016ba1f28dd93427 -> mandatory S3B P8 PR #797 -> independently verify exact resulting main
                                                     -> RT-1D-S3C Soul Lab mutation route seams -> mandatory P8 -> verify resulting main
                                                        -> fresh RT-1D runtime transaction complete through R3 implementation / R1 and R2A-R2D merged with completed mandatory P8 gates
                                                           -> RT-1D-R3 implementation merged in PR #825 result 1eeb4c03151a20b8504819f6c72564b981c84157 -> mandatory R3 P8 PR #826 complete with exact result c291e26f1c20e6479df427054142916dd7df57db -> RT-1D-R4 P1 Return without mutation -> activation budget amendment complete in PR #828 result 9aea56d6d61d69c390bd0c2dc740739ab155d76e -> RT-1D-R4 second P1 Return without mutation -> runtime-projection budget amendment; exact-twelve R4 budget -> RT-1D-R4 third P1 Return without mutation -> cutover-facade structural budget amendment; strict below-1000 facade -> RT-1D-R4 first implementation PR #832 closed unmerged and frozen at head 737406d2f32b5d270177367f3b760af2eb4863a6 -> readiness/replay authority amendment; durable rehearsal_ready handoff and cross-time replay -> RT-1D-R4 one-authority activation complete in PR #834 result 53839b6c349e47a436a885419d699b52142adc86 -> mandatory R4 P8 current-authority synchronization complete in PR #835 result c623898fa8c2ba0a7c7151a912a940295829dda5 -> RT-1D-R4 P8 result/current-authority correction merged -> RT-1D-R5 immediate retirement complete in PR #907 -> mandatory R5 P8 complete in PR #929 -> RT-1 complete
```

The remaining decision debt below is current, not historical:

```text
Remaining post-v0.1 decision or gated candidates:
  PM-D1 RelaySOUL gate design-freeze relation
  PM-D4 client history exclusion default-off deployment decision
  PM-D9 analyzer candidate governance and multilingual schema policy follow-through
  PM-D2 closure or absorption after PM-D6 if RelayREF wrapper removal closes the legacy artifact scope
  RelayATN ATN-0 planning registration only after voice-out / SOUL Lab Runtime MVP; no runtime behavior changes authorized
```


### RT-1D-S3 ordered structural budgets

RT-1D-S3C Soul Lab mutation route seams completed in PR #798. RT-1D-S3C completed in PR #798 with exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`. Historical ordering includes S3A mandatory P8 PR #795 result `bc27c25d0b745fc2d9927e9e21179b14cd337141`.

Monolithic S3 returned to P1 with no persistent changes. Current files measured 1100 / 779 / 161 / 231 lines for Correct, Forget recovery, Correct routes, and Forget routes. The candidate still measured 771 lines in `_relaymem_primary_correction_apply.py`, with 125-line Correct apply, 120-line publication, 156-line Forget apply, 89-line Forget finalization, and 153-line Forget runtime orchestration. Those results fail the approximate below-700-module and about-80-line orchestration gates; no threshold waiver is authorized.

1. **RT-1D-S3A Correct core seams** completed in PR #794 with exact resulting main `2d05a41235e396ac82d536437ed8e5568f617253` using these production paths: `relaylm/relaymem_primary_correction.py`, `relaylm/_relaymem_primary_correction_preflight.py`, `relaylm/_relaymem_primary_correction_apply.py`, `relaylm/_relaymem_primary_correction_publication.py`, `relaylm/_relaymem_primary_correction_recovery.py`, `relaylm/_relaymem_primary_correction_history.py`; optional test only: `tests/test_rt1d_s3a_correct_seams.py`.
2. **RT-1D-S3B Forget core seams** completed in PR #796 with exact resulting main `b75df848bf3982e00f67969c016ba1f28dd93427` using exactly these production paths: `relaylm/relaymem_primary_forget_recovery.py`, `relaylm/_relaymem_primary_forget_apply.py`; optional test only: `tests/test_rt1d_s3b_forget_seams.py`.
3. **RT-1D-S3C Soul Lab mutation route seams** completed in PR #798 with exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e` using exactly four production paths: `relaylm/soul_lab_memory_correction_routes.py`, `relaylm/soul_lab_memory_forget_routes.py`, `relaylm/soul_lab_memory_correction_runtime.py`, and `relaylm/soul_lab_memory_forget_runtime.py`; no optional focused test was added.

**RT-1D-S3C Soul Lab mutation route seams** completed in PR #798 from bootstrap/parent main `e221f17906682bdb077d8016e09843d176af5df4`, with implementation head `97e161beab5b037ab1b8505641b9c6091b7b4ca0`, commit subject `refactor: extract RT-1D-S3C Soul Lab mutation seams`, and exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`. Its exact four-path diff was `relaylm/soul_lab_memory_correction_routes.py` (+42/-99; 104 lines), `relaylm/soul_lab_memory_correction_runtime.py` (+136/-0; 136 lines), `relaylm/soul_lab_memory_forget_routes.py` (+43/-168; 106 lines), and `relaylm/soul_lab_memory_forget_runtime.py` (+209/-0; 209 lines), total +430/-267, with no optional focused test. Every module is below the approximate 700-line trigger; maximum orchestration is 52 lines, all touched orchestration is below about 80 lines, and no waiver applies. Route metrics are Correction loopback 9, dependency resolution 12, installer 52, nested handlers 10 each; and Forget loopback 9, dependency resolution 13, installer 52, nested handlers 10 each. Correction runtime metrics are dependency owner 9, exact JSON 10, scope 7, error mapping 4, preflight 24, apply 22, history 16. Forget runtime metrics are dependency owner 10, exact JSON 10, scope 7, error mapping 4, preflight projection 20, apply projection 28, preflight 26, apply 27, history 22.

The one-way acyclic owner graph is `soul_lab_memory_correction_routes -> soul_lab_memory_correction_runtime` and `soul_lab_memory_forget_routes -> soul_lab_memory_forget_runtime`. Route owners retain installers, decorators and registration, paths, methods and order, `response_model=None`, namespace `Query` constraints (`min_length=1`, `max_length=128`), global loopback authorization, per-request dependency construction, and module-level patch seams. Runtime owners retain operation-specific JSON parsing, scope resolution, domain invocation, safe projection, error mapping, no-store JSON responses, and separate preflight/apply/history paths. There is no reverse route import, generic mutation runtime, dynamic import, `sys.modules` mutation, `importlib.reload`, production monkeypatch, or patch installer.

All six routes remain exact and ordered: `POST .../correct/preflight`, `POST .../correct`, `GET .../corrections`, `POST .../forget/preflight`, `POST .../forget`, and `GET .../forget-history`. Exact methods/order, `response_model=None`, namespace constraints, authorization-first order, strict `application/json`, 16,384-byte limit, empty/oversize/UTF-8/JSON/Pydantic errors, scope-before-domain order, the full error map and unknown normalization, exact successful objects, Forget projections, status/detail bytes, `Cache-Control: no-store`, leakage bounds, call arguments/order, and post-app-creation `patch.object` behavior are preserved. `relaylm/soul_lab_app.py` remained byte-identical with baseline/final SHA-256 `877457129d617ed0a90df879e1a41d9807503bb2612b68095812dfc87dea58e4`; configuration, contracts, workflows, documentation, and evidence were unchanged in PR #798.

The external baseline/candidate differential matrix SHA-256 was `44547117872e449294095f240d79f16b8bbd9c7f6c89737fa9c865e461c65dac`. It covered registration/order, authorization and authorization-before-domain access, media/body/UTF-8/JSON/Pydantic failures, valid preflight/apply/history objects and arguments, projections/leakage, every mapped error, unknown normalization, status/detail/cache, and post-install patches; its harness and stores remained outside the repository. Python 3.12 validation passed `scripts/relaylm_soul_lab_memory_routes_split_smoke.py`, `scripts/relaylm_phase_i3_primary_mem_correct_ci_runner.py`, `scripts/relaylm_phase_i4e_forget_api_security_smoke.py`, `scripts/relaylm_phase_i4f_forget_validation_security_smoke.py`, focused Correct/Forget security and validation smokes, `py_compile` for all four paths, `compileall` for `relaylm`/`scripts`/`tests`, `git diff --check`, and the isolated differential comparison. Every applicable exact-head workflow for `97e161beab5b037ab1b8505641b9c6091b7b4ca0` succeeded or was legitimately path-skipped; none failed, queued, or remained running.

S3A owns Correct preflight/token, apply/replay/receipt, publication, caller recovery, and read-only history seams. S3B owns Forget validation/replay, hidden-successor handoff, caller recovery, convergence, and finalization seams while the public Forget facade files remain byte-identical. S3C keeps route installation and global authorization in route owners and moves operation-specific parsing, scope resolution, invocation, safe projection, error mapping, and no-store responses into operation runtimes; `soul_lab_app.py` remains byte-identical. Exact imports, APIs, schemas, tokens, faults, lock order, durable bytes, idempotency, recovery, paths, methods, status codes, Cache-Control, patchability, and leakage bounds remain unchanged.

Each code PR is behavior-preserving and Primary-only, fixes its complete budget before writing, keeps new production modules below the approximate 700-line trigger and touched orchestration about 80 lines or less, and returns to its own P1 before any additional path. No generic mutation framework, second authority, cutover/configuration/serving/fallback/retirement change, or silent budget expansion is permitted. PR #793 is the merged architecture-only amendment, with exact result `5011eaaddd895b434f3d870dcf2206527725629c`, and requires no P8. The current order is S3A PR #794 result `2d05a41235e396ac82d536437ed8e5568f617253` -> S3A P8 PR #795 result `bc27c25d0b745fc2d9927e9e21179b14cd337141` -> S3B PR #796 result `b75df848bf3982e00f67969c016ba1f28dd93427` -> S3B P8 PR #797 result `e221f17906682bdb077d8016e09843d176af5df4` -> S3C PR #798 result `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e` -> mandatory S3C P8 PR #799 result `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f` -> architecture PR #800 result `68cc16b9d5ed7b999c22d27457390e53de851335` -> R1 PR #801 result `90a3c4f1cedf54e007cf5c0a6a9abc69a30d2acd` -> mandatory R1 P8 PR #802 current -> independently verify PR #802 exact resulting main after merge -> R2 next, not started; only the verified P8 result may bootstrap R2. PR #800 is architecture-only and requires no P8; no implementation slice may start from its PR head, and PR #800's independently verified resulting main bootstrapped R1. No Lane C transaction overlaps. S3B may not silently expand beyond `relaylm/relaymem_primary_forget_recovery.py` and `relaylm/_relaymem_primary_forget_apply.py`; only `tests/test_rt1d_s3b_forget_seams.py` is optional, while `relaylm/relaymem_primary_forget.py` and `relaylm/relaymem_primary_forget_public_apply.py` remain byte-identical. Any additional S3B path requires a fresh P1 before writing.

## MVP dependency waves

### Wave 4 completed

```text
O1D2 bounded scheduler policy/fairness/pacing
I-4E loopback API and SOUL Lab Forget UI
UI-B1A read-only lifecycle visibility
I-5A Pin / Unpin contract/preflight
I-7A/B Held Apply / Discard contract/preflight
```

Wave 4 closed the immediate policy, UI, and preflight convergence boundary without opening I-5B/I-7C runtime apply or O2/O3.

### Wave 5 completed

```text
E1 evaluation consolidation
O1E stale recovery/cancellation/shutdown complete
I-4F crash/race/security/fresh-conversation validation
```

Wave 5 closed the evaluation, operational-control, and Forget validation slices without adding polling, supervision, or always-on operation.

### O1F validation completed

```text
O1F operational validation
  -> corruption / concurrency / saturation / restart / leakage validation
  -> validation-only hardening over caller-invoked O1E/O1D2/O1D1
  -> no polling, sleep, service supervision, worker pool, or always-on operation
```

### Post-O1F next candidates

Post-O1F candidates have been closed or absorbed by later Wave 6, Wave 7, E1-R5, PM-D*, Character Workspace reset slices, O2/O3, and local durable-memory E2 value-smoke readiness evidence.

### Wave 7 completed

```text
E1-R3 provenance-preserving Primary MEM formation summary complete
E1-R4 retrieval-response grounding and unsupported-detail suppression complete
```

Wave 7 completed the E1-R3 / E1-R4 evidence and grounding slices without changing browser trust, RelaySOUL mutation, or media runtime authority.

### Post-Wave-7 E1-R5 correction completed

```text
E1-R5 Primary MEM recall candidate discovery fallback complete
```

E1-R5 remains a bounded scoped Primary MEM recall fallback. It preserves M2 as preferred relevance owner. PM-D8 canonical adapter fold-in is complete in PR #491; the former runtime bridge module remains compatibility no-op only.

### Character Workspace reset completed through CW-A5

```text
CW-A1 file-first source tree and parser contracts complete
CW-A2 workspace compiler projections and KV-cache tiers complete
CW-A3 Character Workspace UI rebuild complete
CW-A4 SLP-maintained MEM/SCENE/REL wiki candidates and proposals complete
CW-A5 character creation, templates, and showcase import complete
```

CW-A1 establishes the read-only file-first Character Workspace source-tree and parser contracts. CW-A2 adds deterministic `.relaylm/build/**` compiler projections and KV-cache tier summaries. CW-A3 rebuilds `apps/soul-lab` into Character Workspace top-level surfaces while preserving the existing Home conversation authority path and keeping browser authority presentation-only. CW-A4 adds dry-run-first RelaySLP MEM / SCENE / REL candidate/proposal planning, content-free projection, and explicit write-candidates mode for allowlisted inbox/proposal artifacts only. CW-A5 adds deterministic, explicit character creation/template/import surfaces while preserving the no-auto-default and no-hidden-activation boundary.

### O2/O3 local scheduler operation completed

```text
O2 supervised worker service complete as opt-in local scheduler service
O3 always-on local operation complete as opt-in local CLI/process wrapper
```

O2/O3 remain local operation support only. They are not app-embedded, not browser authority, not default-on, and do not add memory mutation authority. The durable-memory E2 scenario is complete as separate local human-reviewed value-smoke evidence and does not change O2/O3 authority.

### Post-v0.1 / post-voice-out RelayATN candidate registered

```text
ATN-0 RelayATN planning registration only
  -> target-boundary document added
  -> provisional vocabulary only
  -> no implementation, resident processing, runtime behavior change, or default-on operation authorized
```

RelayATN remains gated on voice-out / SOUL Lab Runtime MVP, first-audio and per-node latency baselines, canonical vocabulary registration or an explicit fold-in decision, and documented single-primary-user vs multi-input assumptions. ATN-1 and later slices must not be scheduled until those preconditions are satisfied.

### PM-D3 / PM-D5 / PM-D6 / PM-D7 / PM-D8 compatibility debt completed

```text
PM-D3 RelayEMO/RelaySCN scene_state ownership closed by P0-PIPE
PM-D5 RelayMEM flat-store compatibility removal complete
PM-D6 RelayINT native artifact / RelayREF wrapper removal complete
PM-D7 runtime install hook fold-in complete
PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in complete
```

PM-D3 is closed by the shipped P0-PIPE request-path ordering fix, which removes same-turn RelayEMO normalized `scene_state` fallback ownership from RelaySCN. PM-D5 removes legacy flat RelayMEM runtime discovery, PM-D6 makes RelayINT own the native input-side reference/intent artifact, PM-D7 adds explicit dry-run-first runtime install/preflight support, and PM-D8 folds the E1-R5 bounded scoped Primary fallback into canonical Primary recall.

### Post-E1-R5 / Post-Wave-7 next candidates

The paragraph below is the retained historical record of the post-E1-R5 candidate state. Each of its present-tense progress and authority statements is scoped to the earlier point at which it was written and does not describe current state; the current position is RT-1 complete, with Lane R R5 and Lane D D5/D6 eligible as recorded in [Post-RT-1 repository-wide sequencing](#post-rt-1-repository-wide-sequencing). The PM-D1, PM-D2, PM-D4, and PM-D9 decision debt it names does remain open.

Within the pre-existing post-E1-R5 decision-debt registry: The remaining candidates are PM-D1/PM-D4/PM-D9 follow-through and PM-D2 closure or absorption after PM-D6. The separately registered dependency-first implementation program is complete through RT-1D-S2: EV-1, OVL-1, ASM-1, SM-1, the default-off bounded ST-1 create commit slice, LC-1A through LC-1E, the RT-1A contract and projection foundation, the RT-1B projection builder and deterministic rebuild, the default-off shadow-only RT-1C selection, characterization, and usage ledger, the behavior-preserving RT-1D-S1 reader seams completed in PR #789, and the behavior-preserving RT-1D-S2 worker seams completed in PR #791 with exact resulting main `31b700a2db0af7819f761d51bd946ff6798eb4c9`. LC-1 lifecycle migration is complete; RT-1D-R1 and mandatory R1 P8 PR #802 are complete, the initial R2 attempt returned at P1 without repository mutation, and PR #803 was the historical architecture-only amendment and subsequently completed. PR #790 completed the S1 mandatory P8 current-authority sync with exact resulting main `3e20274f18306f7db2410fd5239051411b9c052b`. PR #792 completed the S2 mandatory P8 current-authority sync, and the S3A-S3C structural sequence plus mandatory P8 transactions subsequently completed through PR #799 result `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`. Architecture PR #800, R1 PR #801, and mandatory R1 P8 PR #802 then completed with their recorded results; renewed R2 was historically gated by PR #803 merge and independent verification of its exact resulting main. Primary MEM remains the sole ordinary served memory and Retrieval authority. PM-D4, PM-D9, and PM-D1 apply as the narrow default-on, multilingual-generation, and SOUL-conditioned-formation gates recorded above; PM-D2 remains separately governed. Durable-memory E2 value smoke is complete as local human-reviewed v0.1 readiness evidence. RelayATN remains ATN-0 planning-only debt after voice-out / SOUL Lab Runtime MVP and does not authorize implementation.

## RT-1D fresh runtime implementation authorization (historical)

This section is the retained record of the RT-1D runtime authorization as it stood at PR #800. Its present-tense statements — including the ordered R1 through R5 sequence and the Primary serving authority it names — are scoped to that earlier point and do not describe current state. R1 through R5 and every mandatory P8 have since completed, and RT-1 is complete.

Fresh RT-1D runtime P0/P1 architecture authorization PR #800 completed with result `68cc16b9d5ed7b999c22d27457390e53de851335`. Exact-current P0/P1 inspection at
`d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f` authorized, but at that inspection did not start, the
ordered Lane C runtime sequence `RT-1D-R1 durable preparation -> R2 Primary
writer-fence carriage -> R3 rehearsal/readiness -> R4 one-authority activation ->
R5 immediate retirement/proof`. Each is a separate exact-main implementation PR
followed by mandatory same-lane P8 and resulting-main verification. R4 is the only
authority-transfer slice. Primary remains the sole ordinary served memory and
Retrieval authority until that future transfer is durably finalized; no runtime,
configuration, serving, writer fence, fallback, or retirement behavior changed in
the architecture authorization. PR #800 is architecture-only and requires no P8.
RT-1D-R1 implementation is complete in PR #801: no implementation slice may start from the PR head, and
PR #800's independently verified resulting main bootstrapped R1 after PR
#800 merges.

The mandatory S3C P8 current-authority synchronization PR #799 merged as exact current main `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`. Fresh exact-current RT-1D P0/P1 inspection now authorizes the ordered runtime implementation budgets. This architecture transaction records that no cutover, authority switch, serving, fallback, writer fence, or retirement change occurred.

## Historical RT-1D-R2B P8 current-authority synchronization gate

The sequence and authority statements in this section are scoped to the RT-1D-R2B gate at which they were written and do not describe current state. R2B through R5 and every mandatory P8 have since completed.

The sequence at that historical point was: PR #803 exact result `eee986422b45c50e0d9ad0528e863457be4db9a1` -> renewed R2 P1 Return without mutation -> live-root budget amendment PR #804 exact result `00ba475c689631520538b7531022603447f11bd0` -> R2 P1 Return recorded in closed tree-neutral Draft PR #805 head `733b38fd3e74dcc542dd1c8f2ec1353a2cab6a95` -> queued-runner root budget amendment PR #806 exact result `cd8ce6e05b6476b08ecf25a5100fb0c3f0e77644` -> R2 P1 Return recorded in closed tree-neutral Draft PR #807 head `00991760b3070597d6b763a0b3ffc2eb820435f2` -> staged writer-fence and smoke-carriage budget amendment PR #808 exact result `758c160e1ee71bb9ad67fe10234e5a38c03c6a3d` -> RT-1D-R2A implementation PR #809 exact result `0f0b88a0bd601d1cd14b830ca209a26107f62430` -> completed mandatory R2A P8 PR #810 exact result `5822b01fd4642c89c39a2518672191bf1a8da115` -> independently verify the R2A P8 exact resulting main -> RT-1D-R2B complete in PR #811 exact result `a1fac7e4d3dee844990b680aa27130cee9051c3d` -> verify R2B exact result -> mandatory R2B P8 -> verify -> RT-1D-R2C -> verify -> mandatory R2C P8 -> verify -> RT-1D-R2D -> verify -> mandatory R2D P8 -> verify -> R3 may become next, not started by this amendment. Every implementation and P8 is a separate fresh-branch single-writer transaction; only the independently verified exact resulting main from the immediately preceding gate may bootstrap the next, never a PR head and never an audit branch. This P8 requires no further P8 and changes no production/runtime behavior.

RT-1D-R2B and mandatory P8 PR #812 are complete; RT-1D-R2C is complete in PR #814 with exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`; at that historical point, RT-1D-R2D was next and had not started. RT-1D-R2A completed in PR #809 with exactly three commits, final head `eafdc0629fd307ed7c136488280ddb449c5787f1`, exactly 9 changed paths and +829/-7, a full suite of 1041/1041, and exact-head CI with no candidate-caused failure. RT-1D-R2B bootstrapped from the independently verified R2A P8 result and completed in PR #811. RT-1D-R2C is complete in PR #814 with exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`; at that historical point, RT-1D-R2D was next and had not started; at that historical point, R2D, R3, R4, and R5 had not started. R2B queue, runner, worker, and pipeline carriage is complete.

The second P1 Return found two independent live roots. A `managed_chat_runtime.py`-only carriage is insufficient because `relaylm/managed_chat_response.py` constructs both stream and non-stream finalization calls; it must carry the same immutable decision to both. A route-only Pin fence is insufficient because `relaylm/relaymem_primary_pin_apply.py` owns apply/replay side effects, including replay state publication and new-operation receipt/state publication; its decision check must dominate every mutation. These are current owners, not new abstractions or authority transfers.

The third P1 Return found exactly one remaining production construction gap: `relaylm/relaymem_slp_queue_candidate.py`. Its `build_relaymem_slp_one_queued_job_request(...)` already receives `RelayLMConfig` and is the sole production constructor of `RelayMEMSLPOneQueuedJobRunnerRequest`. `relaylm/local_worker_once.py` and `relaylm/relaymem_slp_scheduler_queue_lane.py` stay out of budget because both already delegate request construction to that shared builder; authorizing them as well would duplicate derivation responsibility across three owners for no added coverage. `relaylm/relaymem_slp_scheduler_round.py`, `relaylm/cli/worker.py`, every queue-record schema or persistence path, and every worker validator path likewise stay out of budget. The builder must explicitly populate the immutable writer decision on the runner request; no permit-valued request-field default may conceal missing construction-root supply, and downstream owners may validate but may not re-derive or downgrade the decision.

The decision is never persisted in the B3 durable queue record. Python object identity cannot survive that boundary, so the same decision means exact immutable semantic value equality: same schema version, reconstructed state class, allow/reject class, `recovery_required` value, stable bounded reason identities, and `runtime_private_evidence_omitted` value, obtained independently by the runtime-finalization and queued-runner construction roots from the same authoritative configuration posture, with no arbitrary Mapping reconstruction. Because current configuration validation requires an empty cutover binding tuple for exact `primary_only` posture, `relaylm/subjective_mem_retrieval_cutover.py` remains the sole semantic owner and explicitly defines a binding-free `primary_stable` permitted result with no store access, no store root, no binding digest, and no durable read or write; rehearsal-bound posture reconstructs only from complete authorized inputs and otherwise returns reject plus `recovery_required`.

The fourth P1 Return, recorded in PR #807, proved that every required production seam fits inside the twenty-three paths but that strict missing/malformed fail-closed carriage cannot coexist with a frozen `scripts/` surface, because the changed entry points have direct existing smoke, support, and characterization callers. This amendment resolves that by staging R2 and authorizing only those exact callers per stage, without weakening any semantics; a permit-preserving unbound or default class is rejected.

The historical pre-R2D-P1-expansion R2 budget was the exact twenty-three-path ordered list in the RT-1D architecture, split across RT-1D-R2A (paths 1-4), RT-1D-R2B (paths 5-13), RT-1D-R2C (paths 14-20), and RT-1D-R2D (paths 21-23), with no twenty-fourth production path. At that historical point each stage additionally authorized only the exact existing non-production caller files frozen for it: 4 for R2A, 29 for R2B, 23 for R2C, and 5 for R2D, from an independently reproduced inventory of 58 distinct files and 61 stage assignments. There is no wildcard `scripts/` or `tests/` authority and no new test, smoke, or support file in any stage.

Each stage carries a path budget plus a call-site sub-budget. Call-site granularity is accepted and final and file granularity is rejected: a stage assignment is one direct call site, request-construction site, patch target, or explicitly named support-factory site, each individual site belongs to exactly one stage, and the same site may never be assigned to two stages. A listed overlap path is not whole-file authority. Every stage implementation PR and its mandatory P8 must prove the exact bootstrap blob, the exact owned site names with pre-edit line spans, the exact changed hunks, that all other-stage sites are unchanged, and the final blob, with focused tests and smokes for both changed and preserved sites. Every stage P1 re-fetches and remeasures against a fresh baseline taken after the preceding P8 result; completed earlier-stage sites remain protected. If an edit cannot be isolated without changing another stage's site or unrelated behavior, the stage returns to P1 and file authority is not broadened. Strict semantics are retained unchanged: missing and malformed decisions fail closed, there is no unbound or permit-valued default class, and runner, worker, pipeline, Correct, Forget, Pin, and Unpin leaves never re-derive. The twenty-third path is `relaylm/relaymem_slp_queue_candidate.py`, blob `3fc6f0f5a03bb717bcd163c692bc87e54c216f81`, 462 lines, maximum 510 (+48), with `build_relaymem_slp_one_queued_job_request` gaining at most 8 lines and remaining at or below 60 lines plus at most one bounded same-owner helper of at most 40 lines. Preserve every PR #803 structural limit: pipeline implementation baseline 1,033, maximum 1,083 (+50); Primary Pin baseline 742, maximum 777 (+35); cutover owner baseline 403, maximum 550; new functions at most 80 and new orchestration functions at most 60. Added limits are `managed_chat_response.py` blob `bcf8d6f42b21c23ea96e081d69f3c039c5da4f5c`, 543 lines, maximum 559 (+16), with `build_managed_chat_response` gaining at most 8 lines and no branch; and `relaymem_primary_pin_apply.py` blob `9dc4c8bd62623c0037821f19c8dab2d166dcbb01`, 617 lines, maximum 697 (+80), with `_apply_operation` at most 80 lines or, if already larger, no span increase plus only a bounded same-owner helper. R1-R5 ordering is unchanged. Primary remains the sole ordinary served memory and Retrieval authority.

### Current RT-1D-R2B P8 gate

RT-1D-R2B implementation PR #811 completed from exact bootstrap `5822b01fd4642c89c39a2518672191bf1a8da115`, reviewed head `9672a593b90dca06848e936c1099f828f913ae28`, and exact result `a1fac7e4d3dee844990b680aa27130cee9051c3d`, with three commits, 15 paths, +187/-0, 1041/1041, and successful exact-head CI. Mandatory R2B P8 PR #812 completed with exact result `ca4eae55ab2dd053978d1dc7a4dd4b55fee5e5a8` and requires no further P8. RT-1D-R2C completed in PR #814 with exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`; mandatory P8 PR #815 completed with exact result `4ab497e403f3c46b0808e0940ca583f0bd66a3f4`, and, at that historical point, RT-1D-R2D was next and had not started; at that historical point, R3, R4, and R5 had not started. No stage may bootstrap from PR #811's head.


## RT-1D-R2C completion and mandatory P8 (historical)

RT-1D-R2C completed in implementation PR #814 from bootstrap `ed078788e89d74caaa9219dec66fc3b1278dcb45`, final reviewed head `f2f42788348c00368085bba51bdb9130363564c9`, and exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`. Its two commits changed exactly 30 authorized paths, +260/-58: seven production Correct/Forget carriage paths and 23 frozen non-production caller assignments. External Python 3.12 validation passed 1049 tests in 683.23 seconds; every applicable exact-head workflow succeeded.

Correct and Forget roots derive the immutable Primary writer decision only through `relaylm/subjective_mem_retrieval_cutover.py`; public and internal apply/recovery boundaries fail closed before governed effects. No decision enters a durable schema or byte representation. R2B runner and R2D Pin/Unpin sites in the three overlap files remained byte-exact. Primary remains the sole ordinary authority; Subjective ordinary Retrieval remains disabled and unwired. No intent, fence record, readiness, activation, receipt, serving, fallback, or retirement behavior changed.

The mandatory R2C P8 authority sync was the transaction at that historical point and requires no recursive P8. After its independently verified result, at that historical point, RT-1D-R2D was next and had not started; at that historical point, R3, R4, and R5 had not started.


## RT-1D-R2D completion and mandatory P8 (historical)

RT-1D-R2D completed in implementation PR #818 from reviewed head `992496748efc70d51a7ed356e23aea650220902c` with exact squash result `a2197e9f92a8067d733f8adba524bf54eb2708b6`. Its two pre-squash commits changed exactly 10 paths, +119/-43: four production paths (`relaylm/subjective_mem_retrieval_cutover.py`, `relaylm/relaymem_primary_pin.py`, `relaylm/relaymem_primary_pin_apply.py`, and `relaylm/soul_lab_memory_pin_routes.py`) and six non-production paths (the semantic-owner test, four I-5B Pin/Unpin smokes, and lifecycle characterization).

`SubjectiveMemRetrievalPrimaryWriterDecision` remains the sole exact immutable Primary writer decision and `primary_writer_decision_permits_write` remains the sole semantic predicate. The P6 correction totalized malformed exact-type validation for uninitialized and partial instances, missing fields, wrong primitive types, unhashable values, and hostile equality values; all return `False`. The predicate retains its exact-type check and catches only `SubjectiveMemRetrievalCutoverError`. The downstream generic `except Exception` wrapper was removed. Pin/Unpin apply validates the exact decision before request validation, store-root resolution, store access, locking, replay, publication, or any durable effect. Soul Lab roots derive only through the sole resolver and carry that exact value.

Focused semantic-owner/lifecycle validation passed 126 tests, all four I-5B Pin/Unpin smokes passed, the external Python 3.12 suite passed 1063 tests with one dependency deprecation warning, execution safety passed, and every applicable exact-head GitHub check passed. No decision is serialized or persisted and no durable schema or bytes changed. Primary MEM remains the sole ordinary served memory and Retrieval authority; Subjective ordinary Retrieval remains disabled and unwired. No durable intent, fence record, readiness, activation, transfer receipt, serving, fallback, retirement, or R3 behavior was introduced.

The mandatory RT-1D-R2D P8 authority synchronization completed in PR #819 with exact result `dfdefcf89f16f2fb61abe00ef942af35f4c28053`. This documentation-only P8 requires no recursive P8. The post-P8 validator correction PR #820 completed with exact result `e87e6ee82e3626135993735ebe08aac123051e29` and also requires no P8. After independent verification of that exact resulting main, at that historical point RT-1D-R3 was uniquely next and had not started, and RT-1D-R4 and RT-1D-R5 had not started. R3 bootstrapped only from the independently verified exact PR #820 result, never PR #818 head, PR #819 head, or any unmerged branch head.

## RT-1D-R3 projection-generation identity P1 amendment (historical)

Fresh RT-1D-R3 P0/P1 inspection from exact bootstrap `6a790486564b9d917ff8a3b20ef7e30417dd74f2` found one authority mismatch before runtime mutation. The canonical RT-1B owner represents a projection generation as the exact `smretrievalgen_<64-lowercase-hex>` identity, while the current cutover binding and configuration incorrectly validate `projection_generation_id` as an unprefixed 64-character digest. Stripping or re-hashing the prefix would create a second representation and would not bind the exact canonical generation. RT-1D-R3 therefore remained unstarted until this architecture-only amendment merged and its exact resulting main was independently verified.

The single canonical representation is the exact RT-1B `smretrievalgen_<64-lowercase-hex>` value. `projection_source_digest`, `bootstrap_main_sha`, and `resulting_main_sha` remain raw 64-character lowercase SHA-256 values. Binding and configuration must reject a missing prefix, a foreign prefix, uppercase hexadecimal, non-hexadecimal content, and every short or long value; they must also fail closed when the configured and source-derived generation identities disagree. No prefix stripping, re-hashing, dual-read, fallback, or compatibility representation is authorized.

The R3 production/config budget is expanded only by `relaylm/config.py` and `config.example.yaml` alongside the existing `relaylm/subjective_mem_retrieval_cutover.py` and `relaylm/subjective_mem_retrieval_characterization.py` owners. The focused budget remains `tests/test_subjective_mem_retrieval_cutover.py`, `tests/test_subjective_mem_retrieval_characterization.py`, and `scripts/relaylm_subjective_mem_retrieval_cutover_smoke.py`. Exact negative coverage owns malformed prefix, case, hexadecimal, length, and configuration/binding/source disagreement. Projection builder/store, selection, usage ledger, Primary reader, managed route, and all R2 writer-carriage paths remain byte-identical. Primary remains the sole ordinary served authority; the amendment writes no authority state or ordinary usage event and introduces no R4 activation, serving, fallback, transfer, or retirement behavior. This architecture-only amendment requires no P8.

## RT-1D-R3 rehearsal coordinator P1 amendment (historical)

PR #823 was closed unmerged at exact frozen head `d411d443e71d771be4ac1f93e994d876e3f73b3a` after P6 proved that store-safe projection rehearsal and factory-only readiness proof construction could not fit the existing owners without prohibited physical-line compression. Its commits are audit and reviewed-design evidence only and must not be rebased, merged, cherry-picked, or otherwise reused as implementation history. RT-1D-R3 restarted from this amendment's independently verified resulting main after the amendment merged. This architecture-only amendment requires no P8.

The dedicated temporary production owner is `relaylm/subjective_mem_retrieval_rehearsal.py`, with focused evidence owner `tests/test_subjective_mem_retrieval_rehearsal.py`. The production owner stays below 500 normally formatted physical lines, every function stays below 80 normally formatted physical lines, and physical-line compression, wrapper splitting, hidden generated source, and responsibility laundering are prohibited. It is retained through R4 activation and accepted post-transfer validation; removal or permanent disabling belongs only to the later explicitly authorized post-transfer or retirement transaction.

The cutover semantic owner constructs one immutable content-free coordinator specification and validates the returned proof against the original binding and specification. Dependency direction is cutover owner to rehearsal coordinator; rehearsal coordinator to projection builder, projection store, selection, characterization, and canonical digest helpers. The coordinator imports neither cutover nor config, and builder/store, selection, characterization, and config import no coordinator. Readiness is factory-only: direct public construction is disabled, only the successful coordinator path constructs it, and its Subjective-serving, ordinary-usage-event, and authority-state-write booleans are constructor-closed false. Valid-looking unrelated readiness, generation, source, manifest, row-population, or characterization identities fail closed.

The coordinator requires an R3-exclusive disposable projection root whose bundle is exactly absent before any write. Every pre-existing exact, stale, foreign, corrupt, unsafe, or unreadable bundle is rejected byte-identically. It never reads or deletes after a failed write, deletes only a bundle installed and trusted-read by that invocation, verifies exact post-delete absence, rebuilds from the same fixed source, and requires built, trusted-read, and rebuilt projections to be exactly equal. Shadow and replay derive only from that generation, manifest, ordered row population, and canonical page bytes. Characterization must prove deterministic replay, rebuild equivalence, admitted leakage outcome, bounded Primary and Subjective latency, and no private-content combination.

The amended R3 production/config budget is exactly `relaylm/subjective_mem_retrieval_cutover.py`, `relaylm/subjective_mem_retrieval_rehearsal.py`, `relaylm/subjective_mem_retrieval_characterization.py`, `relaylm/config.py`, and `config.example.yaml`. The focused budget is exactly `tests/test_subjective_mem_retrieval_cutover.py`, `tests/test_subjective_mem_retrieval_rehearsal.py`, `tests/test_subjective_mem_retrieval_characterization.py`, and `scripts/relaylm_subjective_mem_retrieval_cutover_smoke.py`. Projection builder/store, selection, usage ledger, Primary reader, managed route, and all R2 writer-carriage paths remain byte-identical. The coordinator writes no ordinary usage event, authority state, intent, fence, receipt, activation, fallback, transfer, serving, or retirement state.

## RT-1D-R3 completion and mandatory P8 (completed)

This section records the RT-1D-R3 transaction as it completed. Its present-tense serving-authority statements are scoped to that point and do not describe current state; RT-1D-R4 activation and RT-1D-R5 retirement have since merged, and the RT-1D-R3 rehearsal execution owner is deleted.

RT-1D-R3 rehearsal coordinator implementation completed in PR #825 from bootstrap `5f91be0efbaf2ba07777c973e260c40af343b7d6`, final reviewed head `a21cfb0af9b0fbef3d466b145d81070b658e2540`, and exact squash result `1eeb4c03151a20b8504819f6c72564b981c84157`. Its three pre-squash commits changed exactly seven implementation paths, +914/-15: `config.example.yaml`, `relaylm/config.py`, `relaylm/subjective_mem_retrieval_cutover.py`, `relaylm/subjective_mem_retrieval_rehearsal.py`, `scripts/relaylm_subjective_mem_retrieval_cutover_smoke.py`, `tests/test_subjective_mem_retrieval_cutover.py`, and `tests/test_subjective_mem_retrieval_rehearsal.py`. The coordinator `relaylm/subjective_mem_retrieval_rehearsal.py` is 398 physical lines with a maximum function span of 40 lines. The Python 3.12 full suite passed 1086 tests with 0 failures and 1 warning in 671.84 seconds, every applicable final exact-head workflow succeeded, the normalized failure state is none, and `p6_stop` is false. The final governed Claude Code correction changed only the bounded `TypeError`/`ValueError` test expectation and preserved the existing implementation receipt's logical writer.

The accepted RT-1D-R3 semantics are one dedicated disposable rehearsal coordinator; an immutable specification validated before every projection or store effect; a factory-only readiness proof carrying complete binding, generation, source, manifest, ordered-row-population, characterization, readiness, and instance-owned closed-false authority fields; independent re-derivation and validation of the complete proof identity by the cutover semantic owner; an R3-exclusive fresh projection root in which every exact, stale, foreign, corrupt, unsafe, or unreadable pre-existing bundle fails closed without mutation; no read or delete after a failed write, deletion only of a bundle installed and trusted-read by the same invocation, exact post-delete absence, and same-source rebuild equality; and characterization proving deterministic replay, rebuild equivalence, admitted leakage outcome, bounded Primary and Subjective latency, and no private-content combination. RT-1D-R3 introduces no ordinary Subjective serving, ordinary usage event, authority-state write, intent, fence, receipt, activation, fallback, transfer, or retirement behavior, and Primary MEM remains the sole ordinary served memory and Retrieval authority.

At that historical point RT-1D implementation was complete through R3 rehearsal/readiness. RT-1D-R1 durable preparation and RT-1D-R2A through RT-1D-R2D Primary writer-fence carriage, together with their mandatory P8 gates, are completed historical work, not future steps. RT-1D-R3 rehearsal/readiness implementation merged separately as PR #825, and its mandatory R3 P8 completed in PR #826 with exact resulting main `c291e26f1c20e6479df427054142916dd7df57db`. At that historical point the final RT-1D hard cutover, authority transfer, ordinary Subjective serving, Primary retirement, and RT-1D-R4 and RT-1D-R5 were incomplete, RT-1D-R4 implementation and RT-1D-R5 had not started, and RT-1D-R4 implementation could then bootstrap only from the independently verified exact resulting main of the completed RT-1D-R4 activation budget amendment PR #828, `9aea56d6d61d69c390bd0c2dc740739ab155d76e`.

The mandatory RT-1D-R3 P8 current-authority synchronization completed in PR #826 from bootstrap `1eeb4c03151a20b8504819f6c72564b981c84157`, final reviewed head `3a9864839515d5787bd11c806fec655bffb9f0df`, and exact resulting main `c291e26f1c20e6479df427054142916dd7df57db`. It was documentation-only and required no recursive P8. RT-1D-R4 one-authority activation became uniquely next only after that exact resulting main was independently verified, and the RT-1D-R4 implementation attempt then returned at P1 without repository mutation. PR #823 remains closed, unmerged, and frozen at audit head `d411d443e71d771be4ac1f93e994d876e3f73b3a` as design evidence only, and its commits remain prohibited implementation history.

## RT-1D-R4 P1 Return and activation budget amendment (completed)

RT-1D-R4 one-authority activation returned at P1 without repository mutation from exact bootstrap main `c291e26f1c20e6479df427054142916dd7df57db`. The authorized implementation branch `agent/rt1d-r4-one-authority-activation` remains identical to that exact main, 0 ahead / 0 behind, with no implementation commit, push, receipt, PR, workflow run, or temporary artifact. That zero-diff implementation branch is frozen: it never received the amendment and must not be used as a bootstrap now that the amendment has merged. At that historical point RT-1D-R4 implementation and RT-1D-R5 had not started, and Primary MEM was the sole ordinary served memory and Retrieval authority in every deployment.

Two exact P1 blockers were proven before any runtime mutation. First, configuration cannot express the RT-1D-R4 requested deployment mode. The requested mode is owned exactly by `SubjectiveMemRetrievalCutoverMode` and `RelayLMConfig` validation in `relaylm/config.py`, and by `RequestedMode` and `SubjectiveMemRetrievalCutoverRequest.__post_init__` in `relaylm/subjective_mem_retrieval_cutover.py`; the cutover binding carries no requested-mode field. Both owners admit only `primary_only` and `rehearsal`, and the original exact-eight RT-1D-R4 production budget omitted `relaylm/config.py` and `config.example.yaml`, so the requested `subjective_only` mode cannot be introduced inside the implementation transaction. Second, the sole cutover semantic owner has no stable-structure capacity for R4 durable activation: `relaylm/subjective_mem_retrieval_cutover.py` is 688 normally formatted physical lines before R4, and adding transfer intent, both fences, exact-generation binding, atomic Subjective-reader and receipt finalization, idempotency, crash reconstruction, and forward-only recovery to that file would exceed the accepted roughly-700-line owner gate or require prohibited physical-line compression, wrapper splitting, or responsibility laundering.

This architecture-only amendment completed in PR #828 from bootstrap `c291e26f1c20e6479df427054142916dd7df57db`, final reviewed head `be2218ac7c5ddd3a9f2a9672846101be482dd97b`, and exact resulting main `9aea56d6d61d69c390bd0c2dc740739ab155d76e`. Its two commits changed exactly the four amendment paths `docs/PROJECT_STATUS.md`, `docs/architecture/project_execution_plan.md`, `docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md`, and `scripts/relaylm_documentation_current_boundary_smoke.py`, +300/-33; it changed no production, runtime, configuration, ordinary test, workflow, contract, ADR, evidence, completion-report, durable schema, or durable bytes; and it required no P8. The revised RT-1D-R4 authority recorded in the rest of this section was the accepted RT-1D-R4 architecture authority until the RT-1D-R4 runtime-projection budget amendment recorded below superseded its exact production/config budget; every other rule recorded in this section remains accepted current architecture authority. At that historical point RT-1D-R4 implementation was uniquely next and unstarted, and RT-1D-R5 was unstarted. RT-1D-R4 implementation could then bootstrap only from the independently verified exact PR #828 resulting main `9aea56d6d61d69c390bd0c2dc740739ab155d76e`, or from a later independently verified exact current `main` that advances it only by documentation-only current-authority correction, never from PR #828 head `be2218ac7c5ddd3a9f2a9672846101be482dd97b`, never from the frozen `agent/rt1d-r4-one-authority-activation` branch, never from the `agent/rt1d-r4-activation-budget-amendment` branch, and never from a correction PR head.

`relaylm/subjective_mem_retrieval_cutover.py` remains the sole public semantic cutover owner and public compatibility surface. One new private R4 mechanics owner is authorized: `relaylm/_subjective_mem_retrieval_cutover_activation.py`. The allowed dependency direction is exactly one-way: the ordinary route and cutover facade depend on `relaylm/subjective_mem_retrieval_cutover.py`, which depends on `relaylm/_subjective_mem_retrieval_cutover_activation.py`, which depends only on `EvidenceRecordStore` and canonical content-free digest helpers. The private activation owner must not import the cutover facade, the configuration owner, request-path owners, selection, the usage ledger, Primary owners, or RelayCTX; it receives one immutable, content-free, fully validated activation specification and dependency bundle from the cutover facade. No reverse import, dynamic import, monkeypatch installer, generic registry, second semantic evaluator, second store, or second journal is authorized, and the private activation owner is not a second semantic authority.

The private activation owner may own only the durable R4 mechanics: exact create-or-verify transfer intent, the Primary reader fence, the Primary writer fence, exact Subjective generation binding, atomic publication of Subjective-reader enablement together with the finalized transfer receipt, deterministic idempotency, exact predecessor and record binding, crash reconstruction, and forward-only recovery. The public cutover owner alone owns the public binding, the requested-mode, result, and decision schemas, semantic validation, the exact reader and writer authority decisions, and validation of the private owner's returned content-free result.

The cutover facade remains strictly below 1000 normally formatted physical lines under the RT-1D-R4 cutover-facade structural exception recorded below, which supersedes the earlier roughly-700 cutover-facade gate for RT-1D-R4 alone. The new private activation owner remains below roughly 600 normally formatted physical lines. Every new or materially changed orchestration remains at or below roughly 80 normally formatted physical lines. Physical-line compression, wrapper splitting, hidden generated source, and responsibility laundering are prohibited, and failure to hold these limits returns to P1 instead of broadening authority.

The PR #828 revised RT-1D-R4 production/config budget was exactly these eleven paths: `relaylm/subjective_mem_retrieval_cutover.py`, `relaylm/_subjective_mem_retrieval_cutover_activation.py`, `relaylm/config.py`, `config.example.yaml`, `relaylm/managed_chat_pipeline_runtime.py`, `relaylm/managed_chat_runtime.py`, `relaylm/relaymem_retrieval.py`, `relaylm/relaymem_primary_recall.py`, `relaylm/relayctx_repack.py`, `relaylm/subjective_mem_retrieval_selection.py`, and `relaylm/subjective_mem_retrieval_usage_ledger.py`. The original exact-eight RT-1D-R4 production budget is superseded and is no longer executable. That exact-eleven budget is itself superseded by the RT-1D-R4 runtime-projection budget amendment recorded below and is no longer executable. `EvidenceRecordStore`, the projection builder and store, the R3 rehearsal owner, the characterization owner, E1-R4 policy, the writer-carriage modules, canonical and lifecycle owners, API/UI, scheduler, deployment, workflow, and contract paths remain byte-identical. The RT-1D-R4 focused evidence budget is exactly the accepted existing evidence for those production paths: existing request-path tests; reader-seam and offload tests; pipeline-ordering tests; RelayCTX tests; Subjective selection and usage-ledger tests; existing configuration and cutover tests; `scripts/relaylm_p0_pipeline_ordering_smoke.py`; and `scripts/relaylm_subjective_mem_retrieval_cutover_smoke.py`. There is no wildcard `tests/` or `scripts/` authority, and no new generic test, smoke, support, helper, framework, or control-plane file is authorized.

The requested cutover mode is extended exactly to `primary_only`, `rehearsal`, and `subjective_only`. `primary_only` continues to require an empty cutover tuple and performs no store read. `rehearsal` continues to require the complete tuple and can neither write durable cutover state nor serve Subjective evidence. `subjective_only` requires the complete exact tuple and is only a requested deployment mode: it cannot authorize serving, skip rehearsal or readiness, repair state, or create fallback by itself. Configuration alone never enables Subjective serving. Before the Primary reader fence only Primary may serve; from the reader fence until atomic finalized activation neither authority may serve or fall back; and only an exact finalized transfer receipt bound to matching durable state may permit ordinary Subjective serving. Primary and Subjective are never simultaneously ordinary authorities. The extension is applied to both exact requested-mode owners together, so the configuration mode and the cutover request schema never disagree. Only the minimum public result and decision schema support required to represent `subjective_only` is authorized, with no compatibility alias, permissive default, dual mode, precedence rule, or configuration-only authority.

Bounded negative coverage owns unsupported and missing mode, an incomplete cutover tuple, configuration/binding/readiness/durable-state disagreement, attempted configuration-only serving, a partial chain, response-lost and idempotent replay, and every crash boundary around transfer intent, both fences, generation binding, and atomic activation with transfer-receipt finalization.

## RT-1D-R4 runtime-projection budget amendment

RT-1D-R4 one-authority activation returned at P1 a second time, without repository mutation, from exact bootstrap main `dc33626fe66ec79ee1d1a5cfc8a5aed23342032c`. The authorized implementation branch `agent/rt1d-r4-one-authority-activation-implementation` remains identical to that exact main, 0 ahead / 0 behind, with no implementation commit, push, receipt, PR, workflow run, or temporary artifact. Both zero-diff RT-1D-R4 implementation branches, `agent/rt1d-r4-one-authority-activation` and `agent/rt1d-r4-one-authority-activation-implementation`, are frozen and must never be reused as a bootstrap. At that historical point RT-1D-R4 implementation and RT-1D-R5 had not started, and Primary MEM was the sole ordinary served memory and Retrieval authority in every deployment.

Two exact P1 blockers were independently confirmed before any runtime mutation. First, no production exact-source acquisition owner exists. The RT-1B projection builder intentionally accepts one already-fixed `SubjectiveMemRetrievalProjectionSource` and explicitly does not enumerate or load canonical pages, current selectors, receipts, or authorization records; production code does not construct that source, and existing construction is test and rehearsal evidence only. The ordinary request path therefore cannot obtain the exact canonical source value that trusted Subjective selection requires. Second, no ordinary live-projection deployment authority exists. Current configuration carries the durable cutover store root and binding tuple but no distinct ordinary projection root, the projection store accepts a bundle only through a trusted read against both an exact fixed source and an explicit projection root, and the RT-1D-R3 root is rehearsal-exclusive and disposable with its bundle deleted after the proof. Reusing the durable cutover store as the disposable ordinary projection root would conflate two authorities and violate the accepted store separation.

These are architecture and budget defects, not implementation findings. Ordinary Subjective serving cannot be safely implemented by laundering source acquisition into selection, the cutover facade, the activation mechanics owner, Primary owners, or RelayCTX.

Exactly one additional private production owner is authorized: `relaylm/_subjective_mem_retrieval_runtime_projection.py`. Its sole responsibility is the ordinary-runtime projection boundary: acquire one exact current `SubjectiveMemRetrievalProjectionSource` by orchestrating the existing canonical workspace, Evidence-store, selector, receipt, and authorization owners without reimplementing their semantics; derive the exact projection through the existing RT-1B builder; install or exact-verify one disposable live projection bundle in a dedicated projection root through the existing projection store; trusted-read that bundle against the same exact source; return one immutable source, projection, and page-binding value to the cutover facade and ordinary route; and fail closed on missing, foreign, stale, mixed, corrupt, unsafe, unreadable, incomplete, or source-disagreeing state. It owns no cutover semantics, transfer intent, fence, receipt, selection rule, usage-event rule, canonical parser, lifecycle evaluator, Primary fallback, RelayCTX policy, or retirement behavior, and it must not become a second current selector, receipt validator, authorization evaluator, projection builder, projection store, selection owner, usage ledger, or cutover authority.

The allowed dependency direction is exactly one-way: the ordinary route and cutover facade depend on `relaylm/_subjective_mem_retrieval_runtime_projection.py`, which depends on the existing canonical source authorities, `relaylm/subjective_mem_retrieval_projection.py`, and `relaylm/subjective_mem_retrieval_projection_store.py`. No reverse import is allowed. The existing projection builder and store and the canonical and lifecycle owners remain byte-identical.

Exactly one configuration field is authorized: `subjective_mem_retrieval_projection_root`. It must be an absolute, normalized, non-symlinked directory and must be distinct from `subjective_mem_retrieval_cutover_store_root`, `evidence_data_root`, `subjective_mem_workspace_root`, and the RT-1D-R3 rehearsal root. `subjective_only` requires the complete existing cutover tuple and this projection root, and configuration still grants no serving authority.

The RT-1D-R4 production/config budget becomes the prior exact eleven paths plus exactly this new private owner, twelve paths total: `relaylm/subjective_mem_retrieval_cutover.py`, `relaylm/_subjective_mem_retrieval_cutover_activation.py`, `relaylm/_subjective_mem_retrieval_runtime_projection.py`, `relaylm/config.py`, `config.example.yaml`, `relaylm/managed_chat_pipeline_runtime.py`, `relaylm/managed_chat_runtime.py`, `relaylm/relaymem_retrieval.py`, `relaylm/relaymem_primary_recall.py`, `relaylm/relayctx_repack.py`, `relaylm/subjective_mem_retrieval_selection.py`, and `relaylm/subjective_mem_retrieval_usage_ledger.py`. The prior exact-eleven RT-1D-R4 production/config budget is superseded and is no longer executable. No thirteenth RT-1D-R4 production or configuration path, schema owner, registry, workflow, helper, generic smoke, control plane, fallback, or compatibility layer is authorized. The RT-1D-R4 focused evidence budget is unchanged.

Before transfer intent, source and projection preparation may fail with Primary still serving. After transfer intent, every source, generation, manifest, row-population, readiness, and binding disagreement fails closed with neither authority serving, and recovery remains forward-only. The final transfer receipt authorizes only the exact generation and source state finalized atomically at activation. Source drift after activation never silently rebinds, never falls back, and never restores Primary; it fails closed pending separately governed exact state convergence.

Structural limits are that the new private runtime-projection owner remains below roughly 600 normally formatted physical lines, every new or materially changed orchestration remains at or below roughly 80 normally formatted physical lines, and physical-line compression, wrapper splitting, dynamic import, hidden generated source, and responsibility laundering are prohibited. Failure to hold any limit returns to P1 instead of broadening authority.

This RT-1D-R4 runtime-projection budget amendment is documentation and current-boundary only. It changes no production, runtime, configuration, ordinary test, workflow, contract, ADR, evidence, completion-report, durable schema, or durable bytes, and it requires no P8. At that historical point RT-1D-R4 implementation was uniquely next and unstarted, RT-1D-R5 was unstarted, and RT-1D-R4 implementation could then bootstrap only from the independently verified exact resulting `main` of this runtime-projection budget amendment, never from either frozen RT-1D-R4 implementation branch, never from `agent/rt1d-r4-runtime-projection-budget-amendment`, and never from this amendment's PR head.

## RT-1D-R4 cutover-facade structural budget amendment

RT-1D-R4 one-authority activation returned at P1 a third time, without repository mutation, from exact bootstrap main `afe18c86de7bbf7d5605ccc74f1fcdd32b68de65`. The authorized implementation branch `agent/rt1d-r4-exact-twelve-activation-implementation` remains identical to that exact main, 0 ahead / 0 behind, with no implementation commit, push, receipt, PR, workflow run, or in-repository temporary artifact. That branch is frozen and must never be reused as a bootstrap or as implementation history, as are `agent/rt1d-r4-one-authority-activation`, `agent/rt1d-r4-one-authority-activation-implementation`, and `agent/rt1d-r4-runtime-projection-budget-amendment`. At that historical point RT-1D-R4 implementation and RT-1D-R5 had not started, and Primary MEM was the sole ordinary served memory and Retrieval authority in every deployment.

The P1 Return proved one exact structural blocker by measurement. The current cutover facade `relaylm/subjective_mem_retrieval_cutover.py` is 688 normally formatted physical lines. After the maximum behavior-preserving extraction the accepted activation-mechanics owner boundary allows — the durable state list, the durable record schema and field tuple, chain reconstruction, chain validation, exact record and predecessor binding, and the content-free identity predicates, 136 physical lines — the facade stands at 566 lines. The complete RT-1D-R4 facade surface then projects to 966 normally formatted physical lines: 278 lines above the current file and 266 lines above the earlier roughly-700 gate. The private activation owner, the private runtime-projection owner, and every materially changed orchestration otherwise remain within their accepted structural gates.

Further extraction sufficient to force the facade below roughly 700 lines would move the public cutover contracts, the exact reader and writer authority decisions, binding and readiness validation, or validation of the private owner's returned content-free result into another semantic owner. That would violate the accepted rule that `relaylm/subjective_mem_retrieval_cutover.py` is the sole public semantic cutover owner, or would require prohibited wrapper splitting and responsibility laundering.

The accepted decision is one explicit, measured, RT-1D-R4-only structural exception rather than a thirteenth production path or a second semantic evaluator. `relaylm/subjective_mem_retrieval_cutover.py` remains the sole public semantic cutover owner and public compatibility surface. The exact-twelve RT-1D-R4 production/config budget recorded above is unchanged, and no thirteenth RT-1D-R4 production or configuration path, schema owner, registry, workflow, helper, generic smoke, control plane, fallback, or compatibility layer is authorized. The RT-1D-R4 focused evidence budget is unchanged, there is no wildcard `tests/` or `scripts/` authority, and no new generic test, smoke, helper, support, framework, registry, or control-plane file is authorized.

The final normally formatted RT-1D-R4 cutover facade must remain strictly below 1000 physical lines, against the measured 966-line projection. This bounded RT-1D-R4-only exception supersedes the earlier roughly-700 cutover-facade gate for RT-1D-R4 alone. It is not a repository-wide precedent and it is not permission for physical-line compression. `relaylm/_subjective_mem_retrieval_cutover_activation.py` and `relaylm/_subjective_mem_retrieval_runtime_projection.py` each remain below roughly 600 normally formatted physical lines, and every new or materially changed orchestration remains at or below roughly 80 normally formatted physical lines. Physical-line compression, wrapper splitting, hidden generated source, dynamic import, duplicate semantic validation, second authority evaluation, and responsibility laundering remain prohibited. If the final facade reaches 1000 physical lines, either private owner exceeds its gate, or any orchestration exceeds its gate, the implementation returns to P1 without broadening authority.

Every accepted RT-1D-R4 semantic rule is unchanged: configuration is a deployment request and never serving authority; the allowed ordinary transition is exactly Primary-only, then neither, then Subjective-only; there is no dual serving and no Primary fallback; exact source, generation, manifest, ordered row population, readiness, and binding agreement is required; durable transfer intent and both Primary fences are required; Subjective-reader enablement and transfer-receipt finalization publish atomically; recovery is idempotent and forward-only; and no RT-1D-R5 retirement behavior is introduced.

This RT-1D-R4 cutover-facade structural budget amendment is documentation and current-boundary only. It changes no production, runtime, configuration, ordinary test, workflow, contract, ADR, evidence, completion-report, durable schema, or durable bytes, and it requires no P8. At that historical point RT-1D-R4 implementation was uniquely next and unstarted, RT-1D-R5 was unstarted, and RT-1D-R4 implementation could then restart only from a fresh branch created from the independently verified exact resulting `main` of this cutover-facade structural budget amendment.

## RT-1D-R4 readiness/replay authority amendment

RT-1D-R4 one-authority activation was implemented for the first time and returned at P1 on one remaining blocker, from exact bootstrap main `219966d0399ced172365d36e85c1d898496fa4a4`. Draft PR #832 reached final head `737406d2f32b5d270177367f3b760af2eb4863a6` with exactly the authorized twelve production/config and existing focused-evidence paths, +2965/-257, three normal commits, exactly one execution receipt, and clean exact-head CI. PR #832 is closed unmerged and frozen: its branch `agent/rt1d-r4-strict-below-1000-activation-implementation` and head `737406d2f32b5d270177367f3b760af2eb4863a6` are reviewed design evidence only, and no commit, cherry-pick, merge, rebase, or branch history from it may seed later implementation. The earlier frozen branches `agent/rt1d-r4-one-authority-activation`, `agent/rt1d-r4-one-authority-activation-implementation`, `agent/rt1d-r4-exact-twelve-activation-implementation`, `agent/rt1d-r4-activation-budget-amendment`, `agent/rt1d-r4-runtime-projection-budget-amendment`, and `agent/rt1d-r4-cutover-facade-budget-amendment` remain prohibited as bootstrap or implementation history. At that historical point RT-1D-R4 implementation and RT-1D-R5 had not started, and Primary MEM was the sole ordinary served memory and Retrieval authority in every deployment.

Two controller findings were confirmed closed on that exact head. The async managed handler offloads the whole blocking activation and decision boundary off the request event-loop thread while preserving activation before either authority decision, and the fenced ordinary artifact classifies the whole artifact truthfully instead of labeling a released runtime-private Subjective payload content-free while keeping the Primary-fence diagnostics content-free.

Two exact blockers remained and are resolved by this amendment. First, no readiness-carriage seam exists inside the exact-twelve RT-1D-R4 budget: the RT-1D-R3 readiness proof is factory-only, its identity binds a characterization digest derived from live per-request Primary served metrics and from the rehearsal's own request identity, so the ordinary `subjective_only` request path can neither transport nor reproduce it; `rehearsal` and `subjective_only` are mutually exclusive configurations; and no second disposable rehearsal projection root exists. Second, response-lost usage replay is bounded by the wall clock: the durable `usage_slot_id` and `result_id` are stable, but `usage_event_id` binds an event digest that folds `occurred_at`, so a replay in a later UTC second resolves the stable result, fails to match the recomputed event identity, and classifies as a slot-integrity conflict that releases nothing.

### RT-1D-R4 architecture decision A — durable RT-1D-R3-to-R4 readiness handoff

The accepted design is a durable handoff through the existing cutover authority chain, not transport or reconstruction of the factory-only readiness object. An exact `rehearsal` deployment may run the existing RT-1D-R3 rehearsal coordinator in the ordinary managed pipeline after the Primary served metrics for that request exist and while Primary remains the sole served authority. After the coordinator produces one complete factory-authentic proof and the public cutover facade revalidates its binding, readiness identity, exact source, generation, manifest, ordered row population, characterization, and configuration agreement, the facade may create-or-verify exactly the durable cutover prefix ending at `rehearsal_ready`.

The private activation mechanics owner performs only the exact predecessor-bound durable write. That write must be idempotent, must bind the complete existing cutover binding including `readiness_id`, and must never advance to `transfer_intent`, either Primary fence, exact Subjective generation binding, Subjective-reader enablement, or the finalized transfer receipt while the requested mode is `rehearsal`. The readiness proof object itself remains factory-only and non-serializable; it is not added to configuration, request payload, API, control plane, or a new durable record kind.

A later `subjective_only` deployment may activate only from an exact durable `rehearsal_ready` or later supported state. It must not mint readiness, accept configuration alone as readiness, or receive a live readiness proof through the ordinary request path.

Exactly one configuration field is added: `subjective_mem_retrieval_rehearsal_projection_root`. It is required only for `rehearsal`; it is prohibited for `primary_only` and `subjective_only`; and it must be absolute, normalized, non-symlinked, disposable, and distinct from `subjective_mem_retrieval_projection_root`, the cutover store root, the Evidence root, the Subjective workspace root, and every other operational root. The existing RT-1D-R3 rehearsal owner `relaylm/subjective_mem_retrieval_rehearsal.py` and the characterization owner `relaylm/subjective_mem_retrieval_characterization.py` remain byte-identical. No new proof schema, registry, helper, control plane, store, journal, or authority owner is authorized.

### RT-1D-R4 architecture decision B — cross-time response-lost usage replay

The stable usage slot remains authoritative and the first finalized event owns the occurrence time. `usage_slot_id` and the stable `result_id` remain unchanged and continue to bind request correlation, selected row, and idempotency identity. First finalization derives one event with the real canonical occurrence time and commits the exact event and result pair atomically.

Replay resolves the stable result record first, obtains the original `usage_event_id` from that result, reads the original event, validates both stored bodies exactly, and requires the stored pair to be internally exact. The stored event must match the incoming attempt on every immutable slot-bearing field: projection generation, request input digest, request correlation digest, selection digest, row digest, memory identity, memory revision, event kind, idempotency-key digest, and policy revision. The newly supplied wall-clock occurrence is the sole field not compared against the original event; the replay reuses the original stored occurrence, event digest, and event identity and returns `duplicate_finalized` without a second durable pair.

Any missing pair member, malformed result reference, foreign event, or disagreement in any immutable field remains incomplete or divergent, fails closed, and is never repaired or overwritten. Coverage must include an explicit different-second replay proving exactly one durable pair, plus negative true-disagreement cases. A timing-dependent same-second replay test is insufficient.

### RT-1D-R4 budget, ownership, and structural gates after this amendment

The exact-twelve RT-1D-R4 production/config path budget is unchanged: `relaylm/subjective_mem_retrieval_cutover.py`, `relaylm/_subjective_mem_retrieval_cutover_activation.py`, `relaylm/_subjective_mem_retrieval_runtime_projection.py`, `relaylm/config.py`, `config.example.yaml`, `relaylm/managed_chat_pipeline_runtime.py`, `relaylm/managed_chat_runtime.py`, `relaylm/relaymem_retrieval.py`, `relaylm/relaymem_primary_recall.py`, `relaylm/relayctx_repack.py`, `relaylm/subjective_mem_retrieval_selection.py`, and `relaylm/subjective_mem_retrieval_usage_ledger.py`. No thirteenth RT-1D-R4 production or configuration path is authorized by this amendment.

The RT-1D-R4 structural gates are unchanged: the cutover facade remains strictly below 1000 normally formatted physical lines; each private owner remains below roughly 600 normally formatted physical lines; every new or materially changed orchestration remains at or below roughly 80 normally formatted physical lines; and physical-line compression, wrapper splitting, dynamic import, duplicate semantic validation, second authority evaluator, and responsibility laundering remain prohibited.

The RT-1D-R4 focused evidence budget is unchanged: the existing request-path, reader-seam and offload, pipeline-ordering, RelayCTX, Subjective selection, usage-ledger, configuration, and cutover tests, plus `scripts/relaylm_p0_pipeline_ordering_smoke.py` and `scripts/relaylm_subjective_mem_retrieval_cutover_smoke.py`. There is no wildcard `tests/` or `scripts/` authority, and no new generic test, smoke, helper, support, framework, registry, or control-plane file is authorized.

Every other accepted RT-1D-R4 semantic rule is unchanged: configuration is a deployment request and never serving authority; the allowed ordinary transition is exactly Primary-only, then neither, then Subjective-only; there is no dual serving and no Primary fallback; exact source, generation, manifest, ordered row population, readiness, and binding agreement is required; durable transfer intent and both Primary fences are required; Subjective-reader enablement and transfer-receipt finalization publish atomically; recovery is idempotent and forward-only; and no RT-1D-R5 retirement behavior is introduced.

This RT-1D-R4 readiness/replay authority amendment is documentation and current-boundary only. It changes no production, runtime, configuration, ordinary test, workflow, contract, ADR, evidence, completion-report, durable schema, or durable bytes, and it requires no P8. At that historical point RT-1D-R4 implementation was uniquely next and unstarted and RT-1D-R5 was unstarted. RT-1D-R4 implementation then restarted exactly as this amendment required, from a fresh branch created from the independently verified exact resulting `main` of this readiness/replay authority amendment, never from PR #832 head `737406d2f32b5d270177367f3b760af2eb4863a6`, never from any earlier frozen RT-1D-R4 implementation or amendment branch, and never from this amendment's PR head. Mandatory RT-1D-R4 P8 remains required after the replacement implementation merges and before RT-1D-R5 may start.

## RT-1D-R4 completion and mandatory P8 (completed)

RT-1D-R4 one-authority activation implementation completed in PR #834 from exact bootstrap main `5273b3ba214e9ba7730fcc4b7683dfc96eeafdb7`, final reviewed head `d15daeec270ba453940bc10dad924a5df93dfeef`, and exact resulting main `53839b6c349e47a436a885419d699b52142adc86`. Its thirteen normal forward commits on one lineage changed exactly 22 paths, +2147/-258, with no amend, rebase, force-push, cherry-pick, or merge-from-main, and no commit, patch, tree, or branch history from frozen PR #832 or PR #833 was reused. It carried exactly one execution receipt, was accepted at cumulative P5/P6, and its normalized failure state is none with `p6_stop` false. RT-1D-R4 one-authority activation is therefore implemented and merged, and it is no longer an unstarted or uniquely next slice.

The exact-twelve RT-1D-R4 production/config budget was preserved exactly: eleven paths changed and `relaylm/subjective_mem_retrieval_selection.py` remained byte-identical by design, because its single projection construction site already passes neither `ordinary_route_admitted` nor `usage_event_recorded`, so admission is proven at the usage-ledger owner boundary rather than asserted at selection. The budget therefore stands at exactly 12 of 12 and no thirteenth RT-1D-R4 production or configuration path was taken. The focused evidence was exactly `tests/test_subjective_mem_retrieval_cutover.py`, `tests/test_subjective_mem_retrieval_usage_ledger.py`, `tests/test_rt1d_reader_seams.py`, and `tests/test_memory_stage_extraction.py`.

The bounded P5 smoke-carriage correction changed exactly seven existing Primary direct-recall smoke scripts. `apply_relaymem_primary_recall_scope()` now enforces the Primary reader fence at its own boundary, so 12 existing call sites across 7 files were corrected to construct the exact immutable decision through the canonical owner instead of weakening the production fence to make a missing decision imply `primary_only`. That correction changed no production or configuration path. No new test, smoke, helper, support, framework, registry, or control-plane file was created, and the RT-1D-R3 rehearsal and characterization owners, the projection builder and store, `relaylm/evidence_store.py`, the LAT-1 owners, the writer-carriage modules, API/UI, scheduler, deployment, workflow, and contract paths remain byte-identical.

The RT-1D-R4 structural gates held by measurement at the exact resulting main: `relaylm/subjective_mem_retrieval_cutover.py` is 998 physical lines against the strictly-below-1000 RT-1D-R4-only exception, `relaylm/_subjective_mem_retrieval_runtime_projection.py` is 481 and `relaylm/_subjective_mem_retrieval_cutover_activation.py` is 314 against the roughly-600 private-owner gate, and the materially changed orchestrations `run_managed_chat_pipeline` at 79, `run_relaymem_retrieval_stage` at 74, and `handle_managed_chat_completion` at 64 are each at or below roughly 80. No physical-line compression, wrapper splitting, dynamic import, duplicate semantic validation, second authority evaluator, or responsibility laundering was used. The full Python 3.12 suite passed 1089 tests with 0 failures and 1 warning at the final exact head, and no RT-1D-R5 retirement behavior was introduced.

Ordinary serving is now exactly one-authority. A deployment whose durable chain has not reached an exact finalized transfer receipt continues to serve Primary MEM alone. Only an exact finalized activation, bound to matching durable state, may serve Subjective alone. `neither` is the bounded fenced transition state between the Primary reader fence and that finalized receipt, and it releases no Primary-derived or Subjective-derived private material. There is no dual serving, no precedence, no empty-result fallback, no stale-projection fallback, and no Primary fallback in either direction, so Primary MEM is not universally the sole ordinary served memory and Retrieval authority once an exact finalized activation exists.

The mandatory RT-1D-R4 P8 current-authority synchronization completed in merged PR #835 from bootstrap `53839b6c349e47a436a885419d699b52142adc86`, reviewed head `1299084bb5256c6638925b518291c22ecd3a4178`, and exact resulting main `c623898fa8c2ba0a7c7151a912a940295829dda5`. Its cumulative scope was exactly the four authority paths, +360/-61, in two normal branch commits carrying exactly one execution receipt, its cumulative P5/P6 was accepted clean, and the Ready-event Agent execution safety run was green before the expected-head-protected merge. It was documentation and current-boundary only; it changed no production, runtime, configuration, ordinary test, workflow, contract, ADR, evidence, completion-report, durable schema, or durable byte; and it required no recursive P8. PR #835 is merged and completed, not open, current, or incomplete, and RT-1D-R4 implementation and its mandatory P8 are both complete.

This transaction is the bounded RT-1D-R4 P8 result/current-authority correction that records that merged PR #835 result. The merged P8 text necessarily still carried open-transaction present tense, so this correction replaces it with the exact completed result. It is documentation and current-boundary only, changes only the same four authority paths, introduces no runtime, serving, or retirement behavior, and requires no P8.

RT-1D-R5 immediate retirement was unstarted during that correction and introduced no retirement behavior. That correction merged as exact resulting `main` `71a334f8eab873775f378ee246daa0ca75b2ba71`, its result was independently verified, and RT-1D-R5 then became uniquely next. RT-1D-R5 may bootstrap only from an independently verified exact current `main`, never from PR #834 head `d15daeec270ba453940bc10dad924a5df93dfeef`, never from PR #835 head `1299084bb5256c6638925b518291c22ecd3a4178`, never from PR #836 head `cf964cf9b530c85656f25958f261e47038247413`, and never from any frozen RT-1D-R4 implementation or amendment branch. The final RT-1D Primary retirement was still incomplete at that historical point.

## RT-1D-R5 rehearsal-retirement budget amendment

The first RT-1D-R5 immediate retirement attempt returned at P1 with zero repository mutation from exact bootstrap main `71a334f8eab873775f378ee246daa0ca75b2ba71`. The authorized implementation branch `agent/rt1d-r5-immediate-retirement-proof` was never pushed, carries no commit, receipt, PR, workflow run, or temporary artifact, and is frozen as P1-return evidence only; it must not be pushed or reused as a bootstrap or as implementation history.

The blocker is an architecture/budget defect, not an implementation finding. The RT-1D-R5 production deletion/modification budget named exactly six paths and included `relaylm/subjective_mem_retrieval_characterization.py` but not `relaylm/subjective_mem_retrieval_rehearsal.py`, while the rehearsal coordinator directly imports that temporary characterization owner's Primary-served metrics type, characterization result type, admitted-leakage constant, and characterization evaluator and calls that evaluator, and `relaylm/subjective_mem_retrieval_cutover.py` directly imports the R3 rehearsal readiness schema, types, derivation, evaluator, and validator. Deleting or permanently disabling characterization while leaving rehearsal untouched therefore cannot produce a closed production import graph, and `tests/test_subjective_mem_retrieval_rehearsal.py` directly exercises that owner.

That amendment corrected the RT-1D-R5 production deletion/modification budget from exact six to exact seven paths by adding exactly `relaylm/subjective_mem_retrieval_rehearsal.py`, and added exactly `tests/test_subjective_mem_retrieval_rehearsal.py` to the bounded RT-1D-R5 focused-evidence budget while preserving the existing authorization for current tests/smokes of the RT-1D-R5 owners, request-path and package-import tests, the cutover test/smoke, and `scripts/relaylm_p0_pipeline_ordering_smoke.py`. It is not a wildcard `tests/` or `scripts/` budget and pre-authorizes no eighth production path: any continuing ordinary consumer outside the exact-seven budget still returns RT-1D-R5 to P1.

The RT-1D-R5 rehearsal-retirement budget amendment completed in merged PR #837 from bootstrap `71a334f8eab873775f378ee246daa0ca75b2ba71`, reviewed head `efd936329f214464f3e872d2fe0e314a2e90210a`, and exact resulting main `9468c870036226d4900fbc4c5ae94bf8c3758af8`. Its cumulative scope was exactly the four authority paths, +195/-24, in one normal forward branch commit carrying exactly one execution receipt, its cumulative P5/P6 was accepted clean, and the Ready-event Agent execution safety run 861 was green before the expected-head-protected merge. It was documentation and current-boundary only; it changed no production, runtime, configuration, ordinary test, workflow, contract, ADR, evidence, completion-report, durable schema, or durable bytes; it introduced no retirement behavior; and it required no P8. PR #837 is merged and completed, not open, current, Draft, unmerged, or incomplete.

## RT-1D-R5 budget-amendment result/current-authority correction

This transaction is the bounded RT-1D-R5 budget-amendment result/current-authority correction that records that merged PR #837 result. The merged amendment text necessarily still carried self-referential open-transaction present tense, so this correction replaces it with the exact completed result. It is documentation and current-boundary only, changes only the same four authority paths, introduces no runtime, serving, or retirement behavior, and requires no P8.

The accepted RT-1D-R5 authority is unchanged: the production deletion/modification budget is exactly seven paths, adding only `relaylm/subjective_mem_retrieval_rehearsal.py` to the former six; `tests/test_subjective_mem_retrieval_rehearsal.py` is explicitly in the bounded focused-evidence budget with no wildcard tests/scripts authority; rehearsal and shadow characterization execution surfaces retire together after exact post-transfer validation; durable R3/R4 readiness/activation records remain valid and are never rewritten by R5 retirement; cutover remains the sole durable chain, authority, and retirement semantic owner; writer modules remain byte-identical and transferred-domain writes remain rejected by the existing durable writer authority; Primary history/admin surfaces survive only when explicitly read-only and never as ordinary reader, writer, ranking, fallback, or mutation authority; and no eighth RT-1D-R5 production path is authorized.

RT-1D-R5 immediate retirement was unstarted during that correction and introduced no retirement behavior. That correction merged, its exact resulting `main` was independently verified, and RT-1D-R5 immediate retirement/proof then became uniquely next and restarted only from a fresh branch created from that verified correction result, never from PR #837 head `efd936329f214464f3e872d2fe0e314a2e90210a`, never from the frozen `agent/rt1d-r5-immediate-retirement-proof` branch, and never from that correction's PR head.

## RT-1D-R5 completion and mandatory P8 (completed)

RT-1D-R5 immediate retirement implementation completed in merged PR #907 from exact bootstrap main `731711f0a207bf547a07e56d84d60156542cff98`, final reviewed head `5911711f0f57c53a7388442b136577b4de76c938`, and exact resulting main `684b49f9bef5b34ccf9518891de85bdef3139c43`. Its cumulative scope was exactly 36 paths: six changed production paths inside the exact-seven RT-1D-R5 production budget, plus 30 bounded focused-evidence paths. `relaylm/relaymem_primary_recall_store.py` and every writer-carriage module remain byte-identical. Its cumulative P5/P6 was accepted clean with no open finding, the Ready-event Agent execution safety run 1132 was green, and the expected-head-protected squash merge succeeded. PR #907 is merged and completed, not open, current, Draft, unmerged, or incomplete.

The ordinary Primary reader is retired from current `main` rather than fenced. The scoped recall entry point, Primary candidate discovery, deterministic selection and ranking, the snippet handoff, and the no-candidate/policy fallback are removed, and `relaylm/relaymem_primary_recall_selection.py` is deleted. The temporary RT-1C shadow-characterization and RT-1D-R3 rehearsal execution owners are retired with it, and `relaylm/subjective_mem_retrieval_characterization.py` and `relaylm/subjective_mem_retrieval_rehearsal.py` are deleted. `run_relaymem_retrieval_stage` has exactly one fenced exit, and an ordinary decision still naming `primary_only` fails closed to `neither`.

Only explicitly classified read-only Primary history, observation, lifecycle, and admin projections remain. They are read-only survivors and are not ordinary reader, writer, ranking, fallback, or mutation authority, and they do not restore ordinary Primary serving.

Ordinary serving remains exactly one-authority. Before an exact finalized activation the accepted fail-closed cutover rules apply, so no ordinary request resolves a Primary store root, discovers or ranks a Primary candidate, or executes a Primary fallback. After an exact finalized transfer receipt only Subjective may serve. `neither` is the bounded fenced transition state and releases no Primary-derived or Subjective-derived private material. There is no dual serving, no precedence, no empty-result fallback, no stale-projection fallback, and no Primary fallback in either direction, so Primary MEM is no longer universally the sole ordinary served memory and Retrieval authority.

Retirement remains under the one existing cutover semantic owner. The durable chain advances through `post_transfer_validated` and then `retirement_complete` only over the accepted exact finalized-receipt path, forward-only and idempotently, and no second authority, alternate evaluator, or dynamic-import compatibility layer was introduced. Accepted RT-1D-R3 and RT-1D-R4 readiness and activation records remain valid and reconstructible.

The mandatory RT-1D-R5 P8 current-authority synchronization completed in merged PR #929 from bootstrap `684b49f9bef5b34ccf9518891de85bdef3139c43`, final reviewed head `f56302fc668491287d469d13a644b7a27d6d33a0`, and exact resulting main `ec3a0789a19c05b21c9b123e012c6aac1941e54a`. Its cumulative scope was exactly the four current-authority paths, its cumulative P5/P6 was accepted clean, and the Ready-event Agent execution safety run 1134 was green before the expected-head-protected squash merge. PR #929 is merged and completed, not open, current, Draft, unmerged, or incomplete. The R5 implementation and its mandatory P8 are therefore both complete. This result/current-authority correction only replaces the P8's self-referential open-transaction wording with the exact completed result; it is documentation and current-boundary only, introduces no runtime, serving, or retirement behavior, and requires no P8.

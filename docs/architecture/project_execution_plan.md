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

Last reviewed: 2026-07-31 JST

## Purpose

This document is the single plan and roadmap authority for RelayLM execution. It owns dependency-first sequencing, MVP boundaries, MVP completion criteria, and post-MVP roadmap ordering. It does not own current implementation status; read [Project Status](../PROJECT_STATUS.md) first.

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
- **RT-1 Retrieval projection and hard cutover** depends on ST-1 and the completed LC-1 eligibility boundaries. [RT-1 Subjective MEM Retrieval Projection and Hard Cutover](subjective-mem-retrieval-projection-hard-cutover.md) defines the accepted ordered RT-1A through RT-1D boundary. RT-1A contract and projection foundation is complete in PR #774; RT-1B projection builder and deterministic rebuild is complete in PR #779; RT-1C shadow adapter, grounding handoff, and usage ledger is implemented in PR #784 as three bounded owners — exact canonical-page-bound selection and private handoff preparation, temporary content-free characterization, and a durable content-free usage ledger that seals admission only after exact durable success. RT-1D-S1 reader seams completed in PR #789 with resulting main `b272edb78602032009d4882a6244883cce610b86`, extracting existing managed-chat, Retrieval, and Primary recall reader responsibilities into bounded owners while preserving exact public behavior, stage order/offload/timing, diagnostics, Retrieval artifacts, Primary security/lifecycle/fallback behavior, and the RelayINT `metadata.ctx` / `ctx_handoff_guess` Mapping contract. S1 is a behavior-preserving structural prerequisite only: it enables no ordinary Subjective MEM Retrieval, changes no Primary MEM serving authority, and adds no RT-1D configuration, binding, durable cutover state, reader or writer decisions, fences, finalized receipt, retirement, persistence, recovery, worker, queue, scheduler, API, or UI behavior. Its mandatory P8 completed in PR #790 with exact resulting main `3e20274f18306f7db2410fd5239051411b9c052b`. RT-1D-S2 worker seams completed in PR #791 with resulting main `31b700a2db0af7819f761d51bd946ff6798eb4c9`. S2 extracted checkpointed Primary pipeline request construction and execution into `relaylm/_relaymem_slp_primary_worker_pipeline.py`, and extracted one-queued-job claim, source preparation, worker invocation, prepared-scope release, and terminal cleanup into `relaylm/_relaymem_slp_one_queued_job_runner_execute.py`. It preserved public request, result, and projection schemas and import locations; patchable module-level callables; claim revalidation, lease renewal counts, checkpoint order, protected-source release order, status/reason bytes, retry and terminal transitions; and durable queue/store/page/index/log bytes plus fault, crash, and recovery behavior. S2 remains a behavior-preserving structural prerequisite only and added no cutover binding, configuration, authority decision, Primary fence, Subjective serving, fallback change, retirement, scheduler/queue/store semantics, or new persistence/recovery authority. PR #792 completed the S2 mandatory P8 current-authority sync with exact resulting main `7e4fb4383dc6c1229d488ac200132b66f6b65bba`. The monolithic S3 behavior-preserving candidate returned to P1 with no persistent changes because it crossed the structural gates. PR #793 merged the monolithic S3 P1 Return architecture amendment with exact result `5011eaaddd895b434f3d870dcf2206527725629c`. RT-1D-S3A Correct core seams completed in PR #794 with exact resulting main `2d05a41235e396ac82d536437ed8e5568f617253` as a behavior-preserving Primary-only structural prerequisite. Its mandatory same-lane P8 completed in PR #795 with exact resulting main `bc27c25d0b745fc2d9927e9e21179b14cd337141`. RT-1D-S3B Forget core seams completed in PR #796 with exact resulting main `b75df848bf3982e00f67969c016ba1f28dd93427`; PR #797 is the mandatory S3B P8 current-authority synchronization. S3C completed in PR #798 with exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`. The mandatory S3C P8 current-authority synchronization PR #799 merged with exact resulting main `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`. RT-1D-R1 durable preparation is complete in PR #801; PR #803 completed with exact result `eee986422b45c50e0d9ad0528e863457be4db9a1` and no P8; the renewed R2 attempt returned at P1 without mutation; and live-root budget amendment PR #804 completed with exact result `00ba475c689631520538b7531022603447f11bd0` and no P8. The following R2 attempt returned at P1 again without mutation and is recorded in closed tree-neutral Draft PR #805 head `733b38fd3e74dcc542dd1c8f2ec1353a2cab6a95`; queued-runner root budget amendment PR #806 completed with exact result `cd8ce6e05b6476b08ecf25a5100fb0c3f0e77644`, the next R2 attempt returned at P1 in closed tree-neutral Draft PR #807 head `00991760b3070597d6b763a0b3ffc2eb820435f2`, and staged writer-fence and smoke-carriage budget amendment Draft PR #PENDING is current. R2 remains not started and is gated by amendment merge plus independent verification of its exact resulting main. Primary MEM remains the sole ordinary served memory and Retrieval authority. Subjective ordinary retrieval remains disabled and unwired. No cutover, authority switch, serving, fallback, or retirement change occurred. RT-1D-R1 durable preparation is complete in PR #801; the PR #PENDING staged writer-fence and smoke-carriage budget amendment gate remains current and RT-1D-R2A remains not started. RT-1B remains default-off and unwired from ordinary Retrieval; RT-1C remains default-off, explicit shadow-only, and unwired from ordinary Retrieval without changing Primary authority. Primary MEM remains the sole ordinary served memory and Retrieval authority. S1, S2, S3A, S3B, and S3C plus each mandatory P8/resulting-main verification were completed before the fresh RT-1D runtime transaction began with R1. No two transactions overlap. The series implements exact-current-revision selection, lifecycle/mutation fail-closed behavior, durable content-free usage events, projection rebuild equivalence, old/new characterization comparison, writer fencing, one-authority cutover, temporary-adapter removal, and retirement of replaced readers/writers.

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

## Current next work

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
                             -> RT-1D structural P1 Return / runtime not started
                                -> RT-1D-S1 reader seams complete in PR #789
                                   -> S1 mandatory P8 current-authority sync in PR #790 -> exact resulting main 3e20274f18306f7db2410fd5239051411b9c052b
                                      -> RT-1D-S2 worker seams complete in PR #791 -> exact resulting main 31b700a2db0af7819f761d51bd946ff6798eb4c9
                                         -> S2 mandatory P8 current-authority sync in PR #792 -> exact resulting main 7e4fb4383dc6c1229d488ac200132b66f6b65bba
                                            -> RT-1D-S3 P1 architecture amendment -> verify amendment resulting main before S3A
                                               -> RT-1D-S3A Correct core seams PR #794 -> P8 PR #795 result bc27c25d0b745fc2d9927e9e21179b14cd337141
                                                  -> RT-1D-S3B Forget core seams PR #796 result b75df848bf3982e00f67969c016ba1f28dd93427 -> mandatory S3B P8 PR #797 -> independently verify exact resulting main
                                                     -> RT-1D-S3C Soul Lab mutation route seams -> mandatory P8 -> verify resulting main
                                                        -> fresh RT-1D runtime transaction / only after S3C P8 exact resulting-main verification / no overlapping Lane C writer

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

Within the pre-existing post-E1-R5 decision-debt registry: The remaining candidates are PM-D1/PM-D4/PM-D9 follow-through and PM-D2 closure or absorption after PM-D6. The separately registered dependency-first implementation program is complete through RT-1D-S2: EV-1, OVL-1, ASM-1, SM-1, the default-off bounded ST-1 create commit slice, LC-1A through LC-1E, the RT-1A contract and projection foundation, the RT-1B projection builder and deterministic rebuild, the default-off shadow-only RT-1C selection, characterization, and usage ledger, the behavior-preserving RT-1D-S1 reader seams completed in PR #789, and the behavior-preserving RT-1D-S2 worker seams completed in PR #791 with exact resulting main `31b700a2db0af7819f761d51bd946ff6798eb4c9`. LC-1 lifecycle migration is complete; RT-1D-R1 and mandatory R1 P8 PR #802 are complete, the initial R2 attempt returned at P1 without repository mutation, and Draft PR #803 is the current architecture-only amendment. PR #790 completed the S1 mandatory P8 current-authority sync with exact resulting main `3e20274f18306f7db2410fd5239051411b9c052b`. PR #792 completed the S2 mandatory P8 current-authority sync, and the S3A-S3C structural sequence plus mandatory P8 transactions subsequently completed through PR #799 result `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`. Architecture PR #800, R1 PR #801, and mandatory R1 P8 PR #802 then completed with their recorded results; renewed R2 remains gated by PR #803 merge and independent verification of its exact resulting main. Primary MEM remains the sole ordinary served memory and Retrieval authority. PM-D4, PM-D9, and PM-D1 apply as the narrow default-on, multilingual-generation, and SOUL-conditioned-formation gates recorded above; PM-D2 remains separately governed. Durable-memory E2 value smoke is complete as local human-reviewed v0.1 readiness evidence. RelayATN remains ATN-0 planning-only debt after voice-out / SOUL Lab Runtime MVP and does not authorize implementation.

## RT-1D fresh runtime implementation authorization

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

## Current RT-1D-R2 staged writer-fence and smoke-carriage budget amendment gate

The current sequence is: PR #803 exact result `eee986422b45c50e0d9ad0528e863457be4db9a1` -> renewed R2 P1 Return without mutation -> live-root budget amendment PR #804 exact result `00ba475c689631520538b7531022603447f11bd0` -> R2 P1 Return recorded in closed tree-neutral Draft PR #805 head `733b38fd3e74dcc542dd1c8f2ec1353a2cab6a95` -> queued-runner root budget amendment PR #806 exact result `cd8ce6e05b6476b08ecf25a5100fb0c3f0e77644` -> R2 P1 Return recorded in closed tree-neutral Draft PR #807 head `00991760b3070597d6b763a0b3ffc2eb820435f2` -> current staged writer-fence and smoke-carriage budget amendment Draft PR #PENDING -> independently verify the amendment exact resulting main -> RT-1D-R2A fresh implementation PR -> verify R2A exact result -> mandatory R2A P8 -> verify R2A P8 result -> RT-1D-R2B -> verify -> mandatory R2B P8 -> verify -> RT-1D-R2C -> verify -> mandatory R2C P8 -> verify -> RT-1D-R2D -> verify -> mandatory R2D P8 -> verify -> R3 may become next, not started by this amendment. Every implementation and P8 is a separate fresh-branch single-writer transaction; only the independently verified exact resulting main from the immediately preceding gate may bootstrap the next, never a PR head and never an audit branch. The amendment requires no P8 and changes no production/runtime behavior.

The second P1 Return found two independent live roots. A `managed_chat_runtime.py`-only carriage is insufficient because `relaylm/managed_chat_response.py` constructs both stream and non-stream finalization calls; it must carry the same immutable decision to both. A route-only Pin fence is insufficient because `relaylm/relaymem_primary_pin_apply.py` owns apply/replay side effects, including replay state publication and new-operation receipt/state publication; its decision check must dominate every mutation. These are current owners, not new abstractions or authority transfers.

The third P1 Return found exactly one remaining production construction gap: `relaylm/relaymem_slp_queue_candidate.py`. Its `build_relaymem_slp_one_queued_job_request(...)` already receives `RelayLMConfig` and is the sole production constructor of `RelayMEMSLPOneQueuedJobRunnerRequest`. `relaylm/local_worker_once.py` and `relaylm/relaymem_slp_scheduler_queue_lane.py` stay out of budget because both already delegate request construction to that shared builder; authorizing them as well would duplicate derivation responsibility across three owners for no added coverage. `relaylm/relaymem_slp_scheduler_round.py`, `relaylm/cli/worker.py`, every queue-record schema or persistence path, and every worker validator path likewise stay out of budget. The builder must explicitly populate the immutable writer decision on the runner request; no permit-valued request-field default may conceal missing construction-root supply, and downstream owners may validate but may not re-derive or downgrade the decision.

The decision is never persisted in the B3 durable queue record. Python object identity cannot survive that boundary, so the same decision means exact immutable semantic value equality: same schema version, reconstructed state class, allow/reject class, `recovery_required` value, stable bounded reason identities, and `runtime_private_evidence_omitted` value, obtained independently by the runtime-finalization and queued-runner construction roots from the same authoritative configuration posture, with no arbitrary Mapping reconstruction. Because current configuration validation requires an empty cutover binding tuple for exact `primary_only` posture, `relaylm/subjective_mem_retrieval_cutover.py` remains the sole semantic owner and explicitly defines a binding-free `primary_stable` permitted result with no store access, no store root, no binding digest, and no durable read or write; rehearsal-bound posture reconstructs only from complete authorized inputs and otherwise returns reject plus `recovery_required`.

The fourth P1 Return, recorded in PR #807, proved that every required production seam fits inside the twenty-three paths but that strict missing/malformed fail-closed carriage cannot coexist with a frozen `scripts/` surface, because the changed entry points have direct existing smoke, support, and characterization callers. This amendment resolves that by staging R2 and authorizing only those exact callers per stage, without weakening any semantics; a permit-preserving unbound or default class is rejected.

The authoritative R2 budget is the exact twenty-three-path ordered list in the RT-1D architecture, split across RT-1D-R2A (paths 1-4), RT-1D-R2B (paths 5-13), RT-1D-R2C (paths 14-20), and RT-1D-R2D (paths 21-23), with no twenty-fourth production path. Each stage additionally authorizes only the exact existing non-production caller files frozen for it: 4 for R2A, 29 for R2B, 23 for R2C, and 5 for R2D, from an independently reproduced inventory of 58 distinct files and 61 stage assignments. There is no wildcard `scripts/` or `tests/` authority and no new test, smoke, or support file in any stage. Strict semantics are retained unchanged: missing and malformed decisions fail closed, there is no unbound or permit-valued default class, and runner, worker, pipeline, Correct, Forget, Pin, and Unpin leaves never re-derive. The twenty-third path is `relaylm/relaymem_slp_queue_candidate.py`, blob `3fc6f0f5a03bb717bcd163c692bc87e54c216f81`, 462 lines, maximum 510 (+48), with `build_relaymem_slp_one_queued_job_request` gaining at most 8 lines and remaining at or below 60 lines plus at most one bounded same-owner helper of at most 40 lines. Preserve every PR #803 structural limit: pipeline implementation baseline 1,033, maximum 1,083 (+50); Primary Pin baseline 742, maximum 777 (+35); cutover owner baseline 403, maximum 550; new functions at most 80 and new orchestration functions at most 60. Added limits are `managed_chat_response.py` blob `bcf8d6f42b21c23ea96e081d69f3c039c5da4f5c`, 543 lines, maximum 559 (+16), with `build_managed_chat_response` gaining at most 8 lines and no branch; and `relaymem_primary_pin_apply.py` blob `9dc4c8bd62623c0037821f19c8dab2d166dcbb01`, 617 lines, maximum 697 (+80), with `_apply_operation` at most 80 lines or, if already larger, no span increase plus only a bounded same-owner helper. R1-R5 ordering is unchanged. Primary remains the sole ordinary served memory and Retrieval authority.

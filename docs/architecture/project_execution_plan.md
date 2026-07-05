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
  - e1r5_post_wave7_correction_convergence_audit.md
  - o2_supervised_scheduler_service.md
  - o3_always_on_local_scheduler.md
  - pm_d5_relaymem_flat_store_compatibility_removal.md
  - pm_d6_relayint_native_artifact_relayref_wrapper_removal.md
  - pm_d7_runtime_install_hook_fold_in.md
---
# RelayLM Project Execution Plan

Last reviewed: 2026-07-05 JST

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
    -> E1-R5 Primary MEM recall candidate discovery bridge complete
```

## MVP completion criteria

For the file-first Character Workspace reset, MVP completion requires that target Character Workspace surfaces and projections remain clearly separated from current implementation status until dedicated implementation slices land.

CW-A3 closes the browser UI rebuild portion of the reset. It is presentation-only: Home stays on the existing RelayLM `/v1/chat/completions` authority path, and Character / Scenes / Relationships / Memory Wiki / Runtime / Advanced default to content-free projections, source-status vocabulary, and explicit Advanced separation for governance internals.

CW-A4 closes the first RelaySLP-maintained workspace maintenance slice for MEM / SCENE / REL wiki candidates and proposals only. It is dry-run-first, produces content-free public projections, writes only allowlisted inbox/proposal artifacts when explicitly requested, and preserves the uppercase source approval boundary. CW-A4 does not implement direct uppercase source rewrites, RelaySOUL apply/rollback, current-turn response effects, runtime prompt injection, queue/worker/O2/O3 authority, or replacement of RelayMEM lifecycle, RelaySCN scene, or RelayREL relationship runtime authorities.

CW-A5 closes the first character creation/template slice. It implements deterministic bundled templates, Quick Create, Advanced Create staging, showcase use-as-is/use-as-starter behavior, local template folder/zip validation, loopback creation APIs, explicit CLI dry-run/write commands, zero-character UI routing, and local CW-A2 build generation after approved commit. CW-A5 does not implement remote registries, unbounded downloads, automatic default active character restoration, normal-path LLM generation, runtime prompt injection changes, or active-character auto-selection after commit.

Phase I-2 is complete for read-only observation of latest runs, formed memory, held or blocked outcomes, lifecycle state, and used-memory evidence. That observation boundary remains read-only and cannot authorize repair, retrieval, mutation, or source-body exposure.

O2/O3 close the explicit opt-in local scheduler operation need for current MVP work. They do not make scheduling app-embedded, browser-owned, default-on, or independently mutation-authoritative. Durable-memory E2 value smoke remains a separate evaluation scenario after O2/O3 draining evidence.

## Post-MVP decision debt registry

Open or remaining decision debt:

- PM-D1 RelaySOUL gate design-freeze relation
- PM-D2 RelayINT -> RelayMEM relayint_intent_artifact legacy compatibility scope; evaluate closure or absorption after PM-D6 if the native artifact closes the legacy artifact scope
- PM-D3 RelayEMO/RelaySCN scene_state ownership
- PM-D4 client history exclusion default-off deployment decision
- PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in
- PM-D9 analyzer candidate governance and multilingual schema policy follow-through after ACG-1 through ACG-6

Completed post-MVP debt:

- PM-D5 RelayMEM flat-store compatibility removal
- PM-D6 RelayINT native artifact / RelayREF wrapper removal
- PM-D7 runtime install hook fold-in

Implementation order for large compatibility removals was completed as:

```text
PM-D5 -> PM-D6 -> PM-D7
```

PM-D8 should be evaluated with PM-D5 when Primary recall layout discovery or adapter/root handling is touched.

Execute the existing RelaySCN-owned `scene_state` migration plan only through dedicated RelaySCN or Character Workspace follow-up slices. ACG-6 does not add Character Workspace parser/compiler/UI, scene-wiki page mutation, or permissive runtime authority from classifier output alone.

## Current next work

```text
Character Workspace reset
  CW-A1 file-first source tree and parser contracts complete
  CW-A2 workspace compiler projections and KV-cache tiers complete
  CW-A3 Character Workspace UI rebuild complete
  CW-A4 SLP-maintained MEM/SCENE/REL wiki candidates and proposals complete
  CW-A5 character creation, templates, and showcase import complete

Completed post-MVP debt:
  PM-D5 RelayMEM flat-store compatibility removal complete
  PM-D6 RelayINT native artifact / RelayREF wrapper removal complete
  PM-D7 runtime install hook fold-in complete

Remaining post-E1-R5 / post-Wave-7 candidates:
  E1-R5 scoped Primary recall candidate bridge boundary remains complete.
  PM-D1 RelaySOUL gate design-freeze relation
  PM-D3 RelayEMO/RelaySCN scene_state ownership
  PM-D4 client history exclusion default-off deployment decision
  PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in
  PM-D9 analyzer candidate governance and multilingual schema policy follow-through
  PM-D2 closure or absorption after PM-D6 if RelayREF wrapper removal closes the legacy artifact scope
  durable-memory E2 value smoke after O2/O3 scheduler draining evidence
```

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

Post-O1F candidates have been closed or absorbed by later Wave 6, Wave 7, E1-R5, PM-D*, Character Workspace reset slices, and O2/O3. Remaining operations evaluation work is durable-memory E2 value smoke after O2/O3 scheduler draining evidence.

### Wave 7 completed

```text
E1-R3 provenance-preserving Primary MEM formation summary complete
E1-R4 retrieval-response grounding and unsupported-detail suppression complete
```

Wave 7 completed the E1-R3 / E1-R4 evidence and grounding slices without changing browser trust, RelaySOUL mutation, or media runtime authority.

### Post-Wave-7 E1-R5 correction completed

```text
E1-R5 Primary MEM recall candidate discovery bridge complete
```

E1-R5 remains a bounded scoped Primary recall bridge. It preserves M2 as preferred relevance owner and is tracked for later canonical adapter fold-in by PM-D8.

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

O2/O3 remain local operation support only. They are not app-embedded, not browser authority, not default-on, and do not add memory mutation authority. The durable-memory E2 scenario remains separate evaluation work.

### PM-D5 / PM-D6 / PM-D7 compatibility debt completed

```text
PM-D5 RelayMEM flat-store compatibility removal complete
PM-D6 RelayINT native artifact / RelayREF wrapper removal complete
PM-D7 runtime install hook fold-in complete
```

PM-D5 removes legacy flat RelayMEM runtime discovery, PM-D6 makes RelayINT own the native input-side reference/intent artifact, and PM-D7 adds explicit dry-run-first runtime install/preflight support.

### Post-E1-R5 / Post-Wave-7 next candidates

The remaining candidates are PM-D1/PM-D3/PM-D4/PM-D8/PM-D9 follow-through, PM-D2 closure or absorption after PM-D6, and durable-memory E2 value smoke after O2/O3 scheduler draining evidence.

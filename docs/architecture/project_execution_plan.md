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
  - e1r5_primary_mem_recall_candidate_bridge.md
  - e1r5_post_wave7_correction_convergence_audit.md
---
# RelayLM Project Execution Plan

Last reviewed: 2026-07-04 JST

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
    -> CW-A2 workspace compiler projections and KV-cache tiers
    -> CW-A3 Character Workspace UI rebuild
    -> CW-A4 SLP-maintained MEM/SCENE/REL wiki candidates and proposals
    -> CW-A5 character creation, templates, and showcase import

Operations
  O1D2 bounded scheduler policy/fairness/pacing complete
    -> O1E stale recovery/cancellation/shutdown complete
    -> O1F operational validation               complete
    -> O2 supervised worker service, only if required
    -> O3 always-on local operation, only if required

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

Phase I-2 is complete for read-only observation of latest runs, formed memory, held or blocked outcomes, lifecycle state, and used-memory evidence. That observation boundary remains read-only and cannot authorize repair, retrieval, mutation, or source-body exposure.

## Post-MVP decision debt registry

- PM-D1 RelaySOUL gate design-freeze relation
- PM-D2 RelayINT -> RelayMEM relayint_intent_artifact legacy compatibility scope
- PM-D3 RelayEMO/RelaySCN scene_state ownership
- PM-D4 client history exclusion default-off deployment decision
- PM-D5 RelayMEM flat-store compatibility removal
- PM-D6 RelayINT native artifact / RelayREF wrapper removal
- PM-D7 runtime install hook fold-in
- PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in
- PM-D9 analyzer candidate governance and multilingual schema policy follow-through after ACG-1 through ACG-6

Implementation order for large compatibility removals:

```text
PM-D5 -> PM-D6 -> PM-D7
```

PM-D8 should be evaluated with PM-D5 when Primary recall layout discovery or adapter/root handling is touched.

Execute the existing RelaySCN-owned `scene_state` migration plan only through dedicated RelaySCN or Character Workspace follow-up slices. ACG-6 does not add Character Workspace parser/compiler/UI, scene-wiki page mutation, or permissive runtime authority from classifier output alone.

## Current next work

```text
Character Workspace reset
  CW-A1 file-first source tree and parser contracts complete
  CW-A2 workspace compiler projections and KV-cache tiers current next candidate
  CW-A3 Character Workspace UI rebuild
  CW-A4 SLP-maintained MEM/SCENE/REL wiki candidates and proposals
  CW-A5 character creation, templates, and showcase import

Post-E1-R5 / Post-Wave-7 next candidates:
  E1-R5 scoped Primary recall candidate bridge boundary remains complete; new work starts after P0-PIPE and ACG.
  PM-D1 RelaySOUL gate design-freeze relation
  PM-D4 client history exclusion default-off deployment decision
  PM-D5 RelayMEM flat-store compatibility removal
  PM-D6 RelayINT native artifact / RelayREF wrapper removal
  PM-D7 runtime install hook fold-in
  PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in
  PM-D9 analyzer candidate governance and multilingual schema policy
  PM-D2 closure or absorption after PM-D6 if RelayREF wrapper removal closes the legacy artifact scope
  O2/O3 only after explicit MVP need
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

### Wave 7 completed

```text
E1-R3 provenance-preserving Primary MEM formation summary complete
E1-R4 retrieval-response grounding and unsupported-detail suppression complete
```

Wave 7 completed the E1-R3 / E1-R4 evidence and grounding slices without changing O2/O3, browser trust, RelaySOUL mutation, or media runtime authority.

### Post-Wave-7 E1-R5 correction completed

```text
E1-R5 Primary MEM recall candidate discovery bridge complete
```

E1-R5 remains a bounded scoped Primary recall bridge. It preserves M2 as preferred relevance owner and is tracked for later canonical adapter fold-in by PM-D8.

### Character Workspace reset opened

```text
CW-A1 file-first source tree and parser contracts complete
CW-A2 workspace compiler projections and KV-cache tiers current next candidate
```

CW-A1 establishes the read-only file-first Character Workspace source-tree and parser contracts. It does not compile prompt projections, write `.relaylm/build/**`, mutate uppercase sources, maintain SLP wiki pages, rebuild UI, or auto-create a default character.

### Post-E1-R5 / Post-Wave-7 next candidates

```text
E1-R5 scoped Primary recall candidate bridge boundary remains complete; new work starts after P0-PIPE and ACG.
PM-D1 RelaySOUL gate design-freeze relation
PM-D4 client history exclusion default-off deployment decision
PM-D5 RelayMEM flat-store compatibility removal
PM-D6 RelayINT native artifact / RelayREF wrapper removal
PM-D7 runtime install hook fold-in
PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in
PM-D9 analyzer candidate governance and multilingual schema policy
PM-D2 closure or absorption after PM-D6 if RelayREF wrapper removal closes the legacy artifact scope
O2/O3 only after explicit MVP need
```

## Current authority links

ACG handoffs: [ACG-1](acg1_analyzer_candidate_governance_contract.md), [ACG-2](acg2_grounded_recall_detail_safety.md), [ACG-3](acg3_retrieval_query_normalization.md), [ACG-4](acg4_reference_intent_analyzer.md), [ACG-5](acg5_relayemo_scene_cleanup.md), and [ACG-6](acg6_scene_wiki_classifier.md). CW-A1 details are in [CW-A1 File-first Source Tree and Parser Contracts](cw_a1_file_first_source_tree_parser_contracts.md). E1-R5 details are in [E1-R5 Primary MEM Recall Candidate Bridge](e1r5_primary_mem_recall_candidate_bridge.md) and [E1-R5 Post-Wave-7 Correction Convergence Audit](e1r5_post_wave7_correction_convergence_audit.md).

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
  - docs/architecture/project_execution_plan.md
  - docs/architecture/p0_relayrel_relayscn_relayemo_ordering_fix.md
  - docs/architecture/analyzer_candidate_governance.md
  - docs/architecture/acg1_analyzer_candidate_governance_contract.md
  - docs/architecture/acg2_grounded_recall_detail_safety.md
  - docs/architecture/acg3_retrieval_query_normalization.md
  - docs/architecture/acg4_reference_intent_analyzer.md
  - docs/architecture/acg5_relayemo_scene_cleanup.md
  - docs/architecture/acg6_scene_wiki_classifier.md
  - docs/architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md
  - docs/architecture/e1r4_retrieval_response_grounding.md
  - docs/architecture/e1r5_primary_mem_recall_candidate_bridge.md
  - docs/architecture/e1r5_post_wave7_correction_convergence_audit.md
  - docs/architecture/wave7_cross_slice_convergence_audit.md
---
# RelayLM Project Status

Last reviewed: 2026-07-04 JST

## Purpose and authority

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

RelayMEM Primary path: M1/M2 complete; M3a-M3h executable; next-turn recall, scope isolation, and E1-R5 scoped candidate bridge complete
P0-PIPE RelayREL / RelaySCN / RelayEMO ordering: complete in PR #458 after actual app.py request-path rewiring and local validation; RelayREL now precedes RelaySCN, RelaySCN precedes input-side RelayEMO, RelayINT/RelayMEM/RelayCTX remain downstream
Analyzer Candidate Governance: ACG-1 contract/helpers complete; ACG-2 Grounded Recall Detail Safety complete; ACG-3 Retrieval Query Normalization complete; ACG-4 Reference/Intent Analyzer consolidation complete; ACG-5 RelayEMO scene ownership cleanup complete; ACG-6 SCN structured classifier and scene-wiki boundary complete
SOUL Lab UI: UI-A0 through UI-A7, Phase I-2, Phase I-3, UI-B0, UI-B1A, I-4E Forget UI, I-5B Pin / Unpin UI, and I-7C Held Governance UI complete
UI-B1A read-only lifecycle visibility: complete
Local E1 proof: explicit scene-qualified request -> O0 terminal success -> Primary MEM -> later Home recall complete through M2-preferred recall plus E1-R5 bounded scoped candidate bridge
E1 evaluation consolidation: complete
E1-R1 trusted Home scene admission: complete
E1-R2 character-store bootstrap command: complete
E1-R3 provenance-preserving Primary MEM formation summary: complete
E1-R4 retrieval-response grounding and unsupported-detail suppression: complete
E1-R5 Primary MEM recall candidate discovery bridge: complete
Home can be a trusted formation source only through the E1-R1 route-owned gate; browser-owned trust remains rejected.
I-5B Pin / Unpin apply/API/UI/ranking behavior: complete
I-7C Held Apply/Discard runtime/API/UI/durable governance evidence: complete
W6-INT merged
Wave 7 implementation tracks complete
W7-INT merged
Post-Wave-7 E1-R5 correction merged and converged
P0-PIPE ordering slice is complete after PR #458 rewired app.py and validation passed for compile, ordering smoke, docs link check, and current-boundary smoke
ACG-1 through ACG-6 analyzer governance slices are complete through bounded candidate producers, cleanup gates, and content-free public diagnostics
```

## Phase 6 and E1 current boundary

B0-B3 durable enqueue and fenced lifecycle are complete. B3 lifecycle: complete. C2 one-job claim/rehydrate/execute adapter: complete. I1 next-turn Primary MEM recall: complete. Character and namespace isolation: complete.

## Analyzer Candidate Governance boundary

ACG-1 Analyzer Candidate Governance is complete as the shared contract/helper slice. ACG-2 Grounded Recall Detail Safety is complete. ACG-3 Retrieval Query Normalization is complete. ACG-4 Reference/Intent Analyzer consolidation is complete. ACG-5 RelayEMO scene ownership cleanup is complete. ACG-6 SCN structured classifier and scene-wiki boundary is complete.

ACG-6 keeps classifier and scene-wiki matches non-authoritative by default. It does not implement Character Workspace parser/compiler/UI, scene-wiki page mutation, live LLM classifier calls, RelayEMO scene ownership restoration, or permissive policy from classifier output alone.

## Current caveats

E1-R4 is request-side only. It builds a backend-bound grounded recall context and instruction from eligible retrieved Primary MEM evidence; it does not add post-hoc visible response rewriting, polling, supervision, O2/O3, browser-owned trust, or new memory mutation authority.

E1-R5 is a bounded request-side fallback bridge. It does not replace M2 as the preferred relevance owner, does not run without query hints, does not scan unbounded filesystem trees, does not use the compatibility symlink, and does not add mutation, worker, scheduler, queue, browser trust, RelaySOUL, or media runtime authority.

Post-MVP decision debt is now tracked explicitly as PM-D1 RelaySOUL gate design-freeze relation, PM-D2 RelayINT -> RelayMEM relayref_artifact legacy compatibility scope, PM-D3 RelayEMO/RelaySCN scene_state ownership, PM-D4 client history exclusion default-off deployment decision, PM-D5 RelayMEM flat-store compatibility removal, PM-D6 RelayINT native artifact / RelayREF wrapper removal, PM-D7 runtime install hook fold-in, PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in, and PM-D9 analyzer candidate governance and multilingual schema policy. ACG-1 through ACG-6 close the current PM-D9 analyzer-governance sequence.

## Immediate dependency-first work

```text
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

The completed P0-PIPE implementation boundary is [P0 RelayREL / RelaySCN / RelayEMO Ordering Fix](architecture/p0_relayrel_relayscn_relayemo_ordering_fix.md). The ACG-1 contract is [ACG-1 Analyzer Candidate Governance Contract](architecture/acg1_analyzer_candidate_governance_contract.md). The ACG-2 handoff is [ACG-2 Grounded Recall Detail Safety](architecture/acg2_grounded_recall_detail_safety.md). The ACG-3 handoff is [ACG-3 Retrieval Query Normalization](architecture/acg3_retrieval_query_normalization.md). The ACG-4 handoff is [ACG-4 Reference Intent Analyzer](architecture/acg4_reference_intent_analyzer.md). The ACG-5 handoff is [ACG-5 RelayEMO Scene Cleanup](architecture/acg5_relayemo_scene_cleanup.md). The ACG-6 handoff is [ACG-6 Scene-Wiki Classifier Boundary](architecture/acg6_scene_wiki_classifier.md). The Analyzer Candidate Governance roadmap is [Analyzer Candidate Governance and Multilingual Schema Policy](architecture/analyzer_candidate_governance.md). The Wave 7 convergence record is [Wave 7 Cross-Slice Convergence Audit](architecture/wave7_cross_slice_convergence_audit.md). The E1-R5 post-correction convergence record is [E1-R5 Post-Wave-7 Correction Convergence Audit](architecture/e1r5_post_wave7_correction_convergence_audit.md). The E1-R3 implementation handoff is [E1-R3 Provenance-Preserving Primary MEM Formation Summary](architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md). The E1-R4 implementation handoff is [E1-R4 Retrieval-Response Grounding](architecture/e1r4_retrieval_response_grounding.md). The E1-R5 implementation handoff is [E1-R5 Primary MEM Recall Candidate Bridge](architecture/e1r5_primary_mem_recall_candidate_bridge.md). Detailed MVP sequencing and post-MVP roadmap ordering live in [Project Execution Plan](architecture/project_execution_plan.md).

## Not yet implemented

- Character Workspace source tree parser/compiler/UI;
- Quick Create / Advanced Create / template import UI;
- full RelayREL relationship Markdown parsing;
- O2 supervised worker service and O3 always-on local operation;
- restore/unhide or physical purge;
- Merge / Supersession runtime apply;
- Secondary MEM consolidation;
- RelaySOUL proposal/intervention/rollback slices;
- static SOUL Lab bundle serving;
- media runtime execution;
- ASR and peer communication transport.

<!-- O1B_CURRENT_BOUNDARY -->
## O1B sealed replay-lane boundary

O1B is complete for one bounded, non-recursive inventory of the configured I1-G root, exact canonical grouping and eligibility classification, deterministic selection of one sealed-pending locator, canonical selected-record reread, and at most one existing I1-GC delegation. It does not implement the O1C queue algorithm, a scheduler round loop, polling, shutdown, supervision, or always-on operation.

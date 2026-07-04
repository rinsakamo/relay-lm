---
relaylm_doc_type: current_target_migration
relaylm_authority: current_target_compatibility_interpretation
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# RelayLM Current / Target / Migration Guide

Last reviewed: 2026-07-04 JST

## Purpose

This guide distinguishes implemented runtime behavior from target architecture. Detailed RelayMEM/RelaySLP status lives in [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md), MVP sequencing and roadmap ordering live in [Project Execution Plan](project_execution_plan.md), and repository-wide current status lives in [Project Status](../PROJECT_STATUS.md).

## Current Wave 7 / P0-PIPE / ACG / CW compatibility interpretation

This section includes the Wave 7 / E1-R5 compatibility interpretation plus the post-Wave-7 P0-PIPE, ACG-1 through ACG-6, and CW-A1 through CW-A5 current boundaries.

```text
O1D2 is current implemented as bounded policy wrapper.
O1E is current implemented as bounded caller-invoked operational controls.
O1F is current implemented as validation-only operational hardening.
O2/O3 remain target/unimplemented.
I-4E is current implemented as loopback Forget API/UI.
I-4F is current implemented as validation-only Forget product completion.
UI-B1A is current implemented read-only visibility.
I-5A is current implemented contract/read-only preflight only.
I-5B is current implemented as Pin / Unpin apply/API/UI/ranking behavior.
I-7A/B is current implemented contract/read-only preflight only.
I-7C is current implemented as Held Apply / Discard runtime/API/UI/durable governance evidence.
E1 evaluation consolidation is current docs/evidence only.
E1-R1 is current implemented as route-owned trusted Home scene admission.
E1-R2 is current implemented as dry-run-first character-store bootstrap.
E1-R3 is current implemented as provenance-preserving Primary MEM formation summary.
E1-R4 is current implemented as request-side retrieval-response grounding and unsupported-detail suppression.
E1-R5 is current implemented as bounded scoped Primary MEM recall candidate discovery bridge.
P0-PIPE is current implemented as the shipped RelayREL -> RelaySCN -> RelayEMO request-path ordering correction.
ACG-1 is current implemented as the Analyzer Candidate Governance contract/helper boundary.
ACG-2 is current implemented as Grounded Recall detail safety behind Query Detail Analyzer governance.
ACG-3 is current implemented as RelayMEM retrieval query normalization behind Retrieval Query Analyzer governance.
ACG-4 is current implemented as RelayREF / RelayINT Reference/Intent Analyzer consolidation.
ACG-5 is current implemented as RelayEMO scene ownership cleanup and non-authoritative scene hint governance.
ACG-6 is current implemented as the bounded SCN structured classifier and scene-wiki matching boundary.
CW-A1 is current implemented as file-first source tree and parser contracts.
CW-A2 is current implemented as workspace compiler projections and KV-cache tier summaries.
CW-A3 is current implemented as the presentation-only Character Workspace UI rebuild.
CW-A4 is current implemented as dry-run-first SLP-maintained MEM/SCENE/REL wiki candidate and proposal planning.
CW-A5 is current implemented as deterministic character creation, bundled templates, showcase import, local validation, loopback APIs, CLI dry-run/write commands, zero-character UI routing, and local CW-A2 build generation after approved commit.
```

E1-R5 was merged after W7-INT and is now treated as a post-Wave-7 correction to the E1 proof boundary. Current docs must not read the E1 recall proof as "M2 alone always selects current eligible scoped Primary MEM". M2 remains preferred; E1-R5 bridges the no-M2-scoped-candidate gap under bounded exact-namespace and lifecycle checks.

The E1-R5 runtime bridge is not a permanent unowned compatibility assumption. PM-D8 in [Project Execution Plan](project_execution_plan.md) tracks the later decision to keep the bridge covered by E1-R5 smokes or fold it into the canonical Primary recall adapter. PM-D8 is related to PM-D5 because flat-store compatibility removal may touch Primary recall layout discovery and adapter/root handling.

P0-PIPE is complete in PR #458. Current request-path interpretation must not describe RelayEMO as the same-turn normalized `scene_state` owner for RelaySCN. RelayREL now precedes RelaySCN, RelaySCN no longer consumes a RelayEMO artifact fallback, and input-side RelayEMO runs after RelaySCN scene policy ownership is established.

ACG-1 through ACG-6 are current as bounded analyzer-governance slices. They establish shared candidate authority rules, Grounded Recall detail safety, RelayMEM retrieval query normalization, RelayREF / RelayINT reference-intent consolidation, RelayEMO scene ownership cleanup, and the first SCN structured classifier / scene-wiki matching boundary. They do not implement scene-wiki page mutation, broad retrieval/update authority from heuristic or LLM candidates, RelayEMO scene ownership restoration, live LLM classifier calls, or SOUL/source mutation authority.

CW-A1 through CW-A5 are current as bounded Character Workspace reset slices. They establish the file-first parser contract, compiler projections, presentation-only UI rebuild, dry-run-first MEM/SCENE/REL proposal planning, and explicit character creation/template/import flow. They do not implement direct uppercase source rewrites, automatic active-character selection, browser-owned authority, remote template registries, unbounded downloads, RelaySOUL apply/rollback, runtime prompt injection changes, O2/O3 worker services, media runtime execution, or permissive authority from template/import content alone.

## RelaySLP and Primary MEM migration

```text
ordinary finalized turn
  -> I1-B source-before-queue publication and B2 enqueue
  -> C2 / C1 worker path or O0 / O1D1 caller path
  -> O1D2 bounded policy hints for later caller decisions
  -> O1E bounded caller-invoked recovery/cancellation/shutdown controls
  -> O1F validation-only operational hardening
  -> M3a-M3h Primary MEM formation
  -> Phase I-1 later-turn M2-preferred retrieval
  -> E1-R5 bounded scoped Primary candidate bridge when M2 yields no eligible scoped candidate
  -> I-4D current-state lifecycle filtering
  -> I-4E loopback Forget API/UI over existing authorities
  -> I-4F full Forget product validation
  -> UI-B1A read-only lifecycle visibility
  -> I-5A/I-7A/B read-only governance preflight
  -> I-5B Pin / Unpin apply and ranking hint
  -> I-7C Held Apply / Discard runtime governance evidence
  -> E1-R1 route-owned trusted Home admission, when explicitly enabled
  -> E1-R2 dry-run-first character-store bootstrap for local evaluation
  -> E1-R3 provenance-preserving formation summary
  -> RelayREL content-free relationship projection
  -> RelaySCN scene policy without RelayEMO fallback
  -> input-side RelayEMO affect/expression hints
  -> RelayCTX bounded injection
  -> E1-R4 request-side grounded recall context
  -> ACG-1 through ACG-6 governed analyzer candidate boundaries
  -> CW-A1 through CW-A5 file-first Character Workspace parser/compiler/UI/creation boundaries
```

Completed behavior must not be re-listed as migration work: Phase I-1, I-2, I-3, I1-GA through I1-GE, O0, O1D1, O1D2, O1E, O1F, I-4D, I-4E, I-4F, UI-B1A, I-5A read-only preflight, I-5B runtime apply/ranking, I-7A/B read-only preflight, I-7C runtime governance, E1 evaluation consolidation, E1-R1 trusted Home scene admission, E1-R2 character-store bootstrap, E1-R3 provenance-preserving Primary MEM formation summary, E1-R4 retrieval-response grounding, E1-R5 scoped Primary recall candidate discovery bridge, P0-PIPE ordering, ACG-1 through ACG-6 analyzer governance slices, and CW-A1 through CW-A5 Character Workspace reset slices are complete.

Remaining migration is deliberately narrower:

```text
full RelayREL relationship Markdown parsing
RelayINT / RelayREF compatibility cleanup
RelayMEM flat-store compatibility removal
TTS/audio/avatar runtime adapter execution

O2 supervised worker service, if required
  -> O3 always-on operation, if required
```

## Safe defaults

Current apply, worker, durable-finalization, retention, scheduler, Character Workspace, and E1 evaluation settings remain default-off, explicit caller/operator invoked, or explicit user-approved where applicable. O1E operational controls and O1F validation do not authorize polling, sleep, loops, service supervision, or always-on processing. E1-R1 defaults disabled and admits Home-origin persistence only through route-owned configuration, never browser-owned hidden metadata. E1-R2 is dry-run-first and may only prepare safe store layout. E1-R3 keeps public provenance projections content-free. E1-R4 keeps public grounded-recall projections content-free and does not perform post-hoc visible response rewriting. E1-R5 keeps public bridge discovery projections content-free, preserves M2 as preferred relevance owner, fails closed without query hints, and does not imply broad scanning, memory mutation, scheduling, TTS, avatar execution, or a compatibility symlink dependency. P0-PIPE keeps ordering diagnostics content-free and does not expose relationship bodies, scene bodies, memory bodies, raw messages, private state, or assistant output. ACG-1 through ACG-6 keep public analyzer and classifier projections content-free and do not expose raw user text, free-form LLM rationale, source Markdown, memory text, scene Markdown, relationship Markdown, paths, queue payload bodies, scene-wiki body text, or unvalidated external signal bodies. CW-A1 through CW-A5 keep public workspace/creation projections content-free, require explicit approval before persistence, reject imported `.relaylm/**` runtime/build/state artifacts, and do not auto-activate a newly created character. No migration step may silently expose content-bearing runtime state in generic diagnostics or imply recurring scheduling/TTS/avatar execution from helper or handoff metadata alone.

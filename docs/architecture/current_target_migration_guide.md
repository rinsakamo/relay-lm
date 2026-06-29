---
relaylm_doc_type: current_target_migration
relaylm_authority: current_target_compatibility_interpretation
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# RelayLM Current / Target / Migration Guide

Last reviewed: 2026-06-29 JST

## Purpose

This guide distinguishes implemented runtime behavior from target architecture. Detailed RelayMEM/RelaySLP status lives in [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md), MVP sequencing and roadmap ordering live in [Project Execution Plan](project_execution_plan.md), and repository-wide current status lives in [Project Status](../PROJECT_STATUS.md).

## Current Wave 7 compatibility interpretation

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
```

E1-R5 was merged after W7-INT and is now treated as a post-Wave-7 correction to the E1 proof boundary. Current docs must not read the E1 recall proof as "M2 alone always selects current eligible scoped Primary MEM". M2 remains preferred; E1-R5 bridges the no-M2-scoped-candidate gap under bounded exact-namespace and lifecycle checks.

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
  -> RelayCTX bounded injection
  -> E1-R4 request-side grounded recall context
```

Completed behavior must not be re-listed as migration work: Phase I-1, I-2, I-3, I1-GA through I1-GE, O0, O1D1, O1D2, O1E, O1F, I-4D, I-4E, I-4F, UI-B1A, I-5A read-only preflight, I-5B runtime apply/ranking, I-7A/B read-only preflight, I-7C runtime governance, E1 evaluation consolidation, E1-R1 trusted Home scene admission, E1-R2 character-store bootstrap, E1-R3 provenance-preserving Primary MEM formation summary, E1-R4 retrieval-response grounding, and E1-R5 scoped Primary recall candidate discovery bridge are complete.

Remaining migration is deliberately narrower:

```text
O2 supervised worker service, if required
  -> O3 always-on operation, if required

RelayINT / RelayREF / RelaySCN ownership migrations
TTS/audio/avatar runtime adapter execution
```

## Safe defaults

Current apply, worker, durable-finalization, retention, scheduler, and E1 evaluation settings remain default-off or explicit caller/operator invoked where applicable. O1E operational controls and O1F validation do not authorize polling, sleep, loops, service supervision, or always-on processing. E1-R1 defaults disabled and admits Home-origin persistence only through route-owned configuration, never browser-owned hidden metadata. E1-R2 is dry-run-first and may only prepare safe store layout. E1-R3 keeps public provenance projections content-free. E1-R4 keeps public grounded-recall projections content-free and does not perform post-hoc visible response rewriting. E1-R5 keeps public bridge discovery projections content-free, preserves M2 as preferred relevance owner, fails closed without query hints, and does not imply broad scanning, memory mutation, scheduling, TTS, avatar execution, or a compatibility symlink dependency. No migration step may silently expose content-bearing runtime state in generic diagnostics or imply recurring scheduling/TTS/avatar execution from helper or handoff metadata alone.

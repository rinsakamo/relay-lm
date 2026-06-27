---
relaylm_doc_type: current_target_migration
relaylm_authority: current_target_compatibility_interpretation
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# RelayLM Current / Target / Migration Guide

Last reviewed: 2026-06-27 JST

## Purpose

This guide distinguishes implemented runtime behavior from target architecture. Detailed RelayMEM/RelaySLP status lives in [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md), MVP sequencing and roadmap ordering live in [Project Execution Plan](project_execution_plan.md), and repository-wide current status lives in [Project Status](../PROJECT_STATUS.md).

## Current Wave 4, I-4F, and E1 compatibility interpretation

```text
O1D2 is current implemented as bounded policy wrapper.
O1E/O1F remain target/unimplemented.
I-4E is current implemented as loopback Forget API/UI.
I-4F is current implemented as validation-only Forget product completion.
UI-B1A is current implemented read-only visibility.
I-5A is current implemented contract/read-only preflight only.
I-7A/B is current implemented contract/read-only preflight only.
E1 evaluation consolidation is current docs/evidence only.
Direct Home-origin trusted scene admission remains target work.
```

## RelaySLP and Primary MEM migration

```text
ordinary finalized turn
  -> I1-B source-before-queue publication and B2 enqueue
  -> C2 / C1 worker path or O0 / O1D1 caller path
  -> O1D2 bounded policy hints for later caller decisions
  -> M3a-M3h Primary MEM formation
  -> Phase I-1 later-turn M2 retrieval
  -> I-4D current-state lifecycle filtering
  -> I-4E loopback Forget API/UI over existing authorities
  -> I-4F full Forget product validation
  -> UI-B1A read-only lifecycle visibility
  -> I-5A/I-7A/B read-only governance preflight
  -> E1 evidence consolidation over the proven local lane
  -> RelayCTX bounded injection
```

Completed behavior must not be re-listed as migration work: Phase I-1, I-2, I-3, I1-GA through I1-GE, O0, O1D1, O1D2, I-4D, I-4E, I-4F, UI-B1A, I-5A read-only preflight, I-7A/B read-only preflight, and E1 evaluation consolidation are complete.

Remaining migration is deliberately narrower:

```text
O1E stale recovery/cancellation/shutdown
  -> O1F operational validation
  -> O2 supervised worker service, if required
  -> O3 always-on operation, if required

Pin/Unpin runtime apply/API/UI/ranking work
Held Apply/Discard runtime/API/UI/durable evidence work

E1-R1 trusted Home scene-admission path
E1-R2 idempotent character-store bootstrap command
E1-R3 provenance-preserving Primary MEM formation summary
E1-R4 retrieval-response grounding and unsupported-detail suppression

RelayINT / RelayREF / RelaySCN ownership migrations
TTS/audio/avatar runtime adapter execution
```

## Safe defaults

Current apply, worker, durable-finalization, retention, and scheduler settings remain default-off or dry-run-first where applicable. No migration step may silently enable actual apply, expose content-bearing runtime state in generic diagnostics, or imply recurring scheduling/TTS/avatar execution from helper or handoff metadata alone.

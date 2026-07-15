---
relaylm_doc_type: documentation_index
relaylm_authority: active_proposal_collection_navigation
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - an active proposal is added, accepted, rejected, or removed
relaylm_not_authoritative_for:
  - accepted architecture
  - current runtime behavior
  - implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
---

# RelayLM Proposals

Documents in this directory are undecided proposals. They provide decision arguments and validation requirements but do not override ADRs, current architecture, contracts, or `PROJECT_STATUS.md`.

## Active proposals

- [Subjective MEM Formation, Consolidation, and Retrieval](subjective-memory-formation-consolidation-and-retrieval.md) — proposes reinforcement-first subjective memory formation, a hot current-session evidence overlay, SOUL-centered / SCN-grounded / EMO-decoupled deferred reflection, evidence-preserving consolidation, hybrid Retrieval, and production evaluation gates.

## Supporting implementation evidence

- [RelayCTX Session Evidence Overlay (CTX-OVL) implementation feasibility](../evidence/implementation/session-evidence-overlay-feasibility.md) — records reusable runtime boundaries, missing cross-request and stream-finalization work, the SCN/EMO conditioning split, implementation slices, risks, and validation gates for provisional continuity before RelaySLP completion.
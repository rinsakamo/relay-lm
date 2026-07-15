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

- [Subjective MEM Formation, Consolidation, and Retrieval](subjective-memory-formation-consolidation-and-retrieval.md) — proposes reinforcement-first subjective memory formation, a hot current-session evidence overlay, bounded governed-ingress catch-up, SOUL-centered / SCN-grounded / EMO-decoupled deferred reflection, evidence-preserving consolidation, hybrid Retrieval, and production evaluation gates.

## Supporting implementation evidence

- [RelayCTX Session Evidence Overlay (CTX-OVL) implementation feasibility](../evidence/implementation/session-evidence-overlay-feasibility.md) — records reusable runtime boundaries, missing cross-request and stream-finalization work, the SCN/EMO conditioning split, RelayCTX implementation slices, risks, and validation gates for provisional continuity before RelaySLP completion.
- [CTX-OVL feasibility alignment with the current RelayCTX runtime contract](../evidence/implementation/session-evidence-overlay-current-relayctx-alignment.md) — distinguishes the current request-local, default-off RelayCTX short-term chain from the proposed cross-request CTX-OVL capability and records the remaining implementation gaps.
- [RelayATN / CTX-OVL boundary review](../evidence/implementation/relayatn-ctx-ovl-boundary-review.md) — records reviewed and revised RelayATN/CTX-OVL recommendations, catch-up limits, multi-user and scene-epoch failure behavior, and the exact non-authoritative counterpart checklist for the RelayATN-owned architecture document. Inclusion here means carried forward for proposal review, not accepted production architecture.

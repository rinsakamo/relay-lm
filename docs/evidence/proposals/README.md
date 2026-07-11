---
relaylm_doc_type: documentation_index
relaylm_authority: proposal_evidence_collection_router
relaylm_status: current
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - a proposal is accepted, rejected, withdrawn, or superseded
relaylm_not_authoritative_for:
  - undecided proposals
  - accepted decision authority
  - current implementation status
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source: ../../adr/0002-documentation-information-architecture.md
---
# Proposal Evidence

This collection preserves proposals after disposition. The proposal record explains the recommendation and its review context; the linked ADR or decision source is authoritative for the adopted or rejected decision.

## Records

- [Documentation information architecture hard-cutover proposal](documentation-restructure-proposal.md) — accepted by ADR 0002; exact submitted source retained alongside the evidence record.

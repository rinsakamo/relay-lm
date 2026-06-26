---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase_i4b_primary_current_state_shared_fence
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_soul_lab_integration
relaylm_update_trigger:
  - Phase I-4B implementation changes
  - Phase I-4C consumes the shared fence
relaylm_not_authoritative_for:
  - hidden lifecycle apply
  - M2 hidden-state exclusion
  - SOUL Lab mutation API or UI
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# Phase I-4B Primary Current State and Shared Mutation Fence

Last reviewed: 2026-06-26 JST

## Status

**Complete for the I-4B read-only boundary.**

I-4B adds the canonical Primary current-state resolver, preserves the existing
Phase I-3 per-memory `.lock` path as the shared Correct/Forget mutation fence,
and defines read-only Forget preflight, five-minute token validation, and bounded
zero-item history behavior.

The bounded zero-item history behavior is read-only and creates no durable Forget artifact.

The resolver returns one stable logical identity, current physical identity,
current revision, lifecycle state, mutation state, retrieval eligibility,
validated control/page status, and bounded content-free reasons. Valid unresolved
prepared mutation evidence is classified as `recovery_required` and remains
retrieval-ineligible.

Forget tokens use the dedicated `relaylm.primary_forget_apply_token.v0` domain,
bind the exact character/namespace/logical and physical identity/revisions,
lifecycle transition, reason digest, operation ID, issued time, and expiry, and
require canonical unpadded base64url encoding in addition to integrity validation.

## Compatibility

- Existing Phase I-3 Correct request/response schemas, apply-token behavior,
  artifact paths, operation keys, `.lock` location, prepared/applied receipts,
  M3e/M3f/M3g convergence, fault points, and recovery entry points are preserved.
- I-4B performs no Forget lifecycle write and does not create hidden successors,
  tombstones, prepared Forget artifacts, index/log mutations, or API/UI routes.
- Ordinary M2 selection, RelayCTX injection, current SOUL Lab reads, and
  historical used-memory evidence remain unchanged in this slice.

## Remaining work

- I-4C: hidden successor apply, prepared artifact, tombstone, exact replay, and
  forward-only recovery.
- I-4D: canonical hidden/prepared/recovery/corrupt exclusion in M2 and RelayCTX.
- I-4E: loopback-only API and SOUL Lab Forget UI.
- I-4F: full fault/security/fresh-conversation validation.

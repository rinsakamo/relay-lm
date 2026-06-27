---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase_i4b_primary_current_state_shared_fence
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_soul_lab_integration
relaylm_update_trigger:
  - Phase I-4B implementation changes
  - Phase I-4C1 and I-4C2 consume the shared fence
  - Later I-4D/I-4E/I-4F convergence updates the downstream status summary
relaylm_not_authoritative_for:
  - post-M3e Forget recovery, replay, and tombstone finalization
  - M2 hidden-state exclusion
  - SOUL Lab mutation API or UI
  - repository-wide current implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# Phase I-4B Primary Current State and Shared Mutation Fence

Last reviewed: 2026-06-27 JST

## Status

**Complete for the I-4B read-only boundary.** Downstream Phase I-4 continuation is also now complete through I-4F, but this handoff remains authoritative only for the I-4B resolver, shared mutation fence, read-only Forget preflight, apply-token validation, and bounded read-only history behavior.

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
- I-4B itself performs no Forget lifecycle write and does not create hidden successors,
  tombstones, prepared Forget artifacts, index/log mutations, or API/UI routes.
- Ordinary M2 selection, RelayCTX injection, current SOUL Lab reads, and
  historical used-memory evidence remain unchanged in the I-4B slice.

## I-4C1 consumer boundary

I-4C1 consumes this exact resolver and `.lock` authority. It adds immutable
`relaylm.mem.forget_prepared.v0`, deterministic
`relaymem.primary_lifecycle_page.v0`, existing M3c/M3d/M3e publication, canonical
page reread, one-winner Correct/Forget and Forget/Forget concurrency, and
`hidden / recovery_required / retrieval_eligible=false` resolution. It does not
change I-4B token semantics or ordinary M2 behavior.

## Downstream completion map

The following downstream slices consume I-4B but are not owned by this handoff:

```text
I-4C1: complete for hidden-successor commit ownership
I-4C2: complete for exact prepared resume, forward-only hidden continuation,
       operation-scoped M3f/M3g convergence, response-loss replay, and tombstone finalization
I-4D:  complete for ordinary M2/RelayCTX lifecycle exclusion, prior physical
       revision exclusion, and historical lifecycle projection
I-4E:  complete for loopback-only API and SOUL Lab Forget UI
I-4F:  complete for full fault/security/fresh-conversation validation
```

Current repository-wide Phase I-4 status lives in [Project Status](../PROJECT_STATUS.md). This file must not be read as the current authority for the completed downstream I-4 product surface.

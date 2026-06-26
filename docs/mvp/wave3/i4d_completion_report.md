---
relaylm_doc_type: implementation_completion_report
relaylm_authority: wave_slice_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - cross-slice sequencing
  - other phase completion
---
# Phase I-4D Implementation Completion Report

This report is evidence for one implementation pull request. It is not repository-wide current-status authority and does not open the next wave or release/evaluation gate.

## Scope

- Slice: Phase I-4D Primary lifecycle-aware retrieval exclusion
- Base branch: `main`
- Start main SHA: `4d31f45cfba967e23bd50f01f3c3d7ce9a8d0a33`
- Branch: `phase-i4d-primary-retrieval-exclusion`

## Implemented production boundary

- Ordinary retrieval consumes the complete shared Correct/Forget current-state index.
- Only the canonical current active physical revision remains eligible.
- Prior, hidden, prepared, recovery-required, corrupt, ambiguous, unresolved, and unsafe candidates fail closed.
- Existing M2 ordering, relevance, caps, budgets, and bounded handoff reconstruction remain authoritative.
- Fresh RelayCTX/backend-bound requests cannot include forgotten content.
- Historical used-memory receipts remain immutable.
- `relaylm.lab.memory_used_lifecycle.v1` overlays current lifecycle without changing v0 compatibility.

## Preserved authorities and non-goals

M2 remains the relevance owner. I-4B/I-4C1/I-4C2 remain mutation, hidden-successor, recovery, control, and finalization authorities. This PR adds no Forget mutation route, SOUL Lab mutation UI, restore path, bulk operation, scheduler change, or I1-G change. I-4E and I-4F remain unimplemented.

## Changed files

- `relaylm/relaymem_primary_i4c2_projection.py`
- `relaylm/relaymem_primary_retrieval_eligibility.py`
- `relaylm/soul_lab_used_memory_lifecycle_projection.py`
- `relaylm/soul_lab_app.py`
- `apps/soul-lab/src/features/lab/usedMemoryLifecycleApi.ts`
- `apps/soul-lab/scripts/usedMemoryLifecycleApiSmoke.mjs`
- `scripts/relaylm_phase_i4d_*.py`
- `.github/workflows/phase-i4d-primary-retrieval-exclusion.yml`
- `docs/architecture/phase_i4d_primary_retrieval_exclusion.md`
- this report

## Validation evidence

The dedicated workflow runs lifecycle, prior-revision, recovery-state, RelayCTX, fresh-conversation, historical projection, frontend schema, and leakage smokes. It also runs I-4B/I-4C1/I-4C2/I-1/I-2/I-3 regressions, RelayCTX injection, frontend typecheck/build, documentation links, and compileall.

Final workflow state is recorded on PR #413.

## Known limitations

I-4E loopback mutation API and SOUL Lab controls are not implemented. I-4F full production validation remains open. Historical lifecycle observation is read-only and versioned separately from the existing v0 receipt projection.

## Shared documentation update inputs

- Completion wording: I-4D M2/RelayCTX lifecycle and prior-revision exclusion complete.
- Remaining boundary: I-4E and I-4F unimplemented; Phase I-4 overall remains in progress.
- Handoff: `docs/architecture/phase_i4d_primary_retrieval_exclusion.md`.
- Schema addition: `relaylm.lab.memory_used_lifecycle.v1`.
- Cross-slice risk: Wave 3 integration must preserve M2 relevance ownership and immutable historical receipts.
- Recommended next phase: I-4E after W3-INT confirms the shared documentation state.

## Source pull request

- PR: #413
- URL: https://github.com/rinsakamo/relay-lm/pull/413

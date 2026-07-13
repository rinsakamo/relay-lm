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
# Phase I-4E Implementation Completion Report

This report is evidence for one implementation pull request. It is not repository-wide current-status authority and does not open the next wave or release/evaluation gate.

## Scope

- Slice: Phase I-4E loopback Forget API and SOUL Lab UI
- Base branch: `main`
- Start main SHA: `e77cfc612db33545a3a1891d03d359dff18f9e39`
- Branch: `phase-i4e-forget-api-ui`

## Implemented production boundary

- Added strict SOUL Lab Forget preflight/apply request contracts.
- Added loopback-only Forget preflight/apply/history routes under `/lab/api/characters/{character_id}/memory/{memory_id}`.
- Added bounded public preflight projection and bounded apply receipt over existing Forget authority.
- Wired SOUL Lab Observation page to explicit Forget preview/confirm/receipt UI.
- Refreshes used-memory lifecycle overlay after successful apply.
- Added backend and frontend smokes plus a dedicated workflow.

## Preserved authorities and non-goals

I-4B remains current-state resolver, shared mutation fence, preflight-token, and history authority. I-4C1 remains hidden-successor commit authority. I-4C2 remains recovery, tombstone, finalization, and public apply authority. I-4D remains ordinary M2/RelayCTX lifecycle exclusion and historical lifecycle overlay authority. This PR adds no restore, purge, unhide, physical deletion, repair, scheduler/worker behavior, retrieval algorithm change, or I-4F full validation.

## Changed files

- `relaylm/soul_lab_app.py`
- `relaylm/soul_lab_memory_forget.py`
- `apps/soul-lab/src/features/lab/ConnectedLabObservationPage.tsx`
- `apps/soul-lab/src/features/lab/PrimaryMemoryForgetPanel.tsx`
- `apps/soul-lab/src/features/lab/forgetApi.ts`
- `apps/soul-lab/scripts/forgetUiSmoke.mjs`
- `apps/soul-lab/package.json`
- `scripts/relaylm_phase_i4e_forget_api_smoke.py`
- `scripts/relaylm_phase_i4e_forget_api_security_smoke.py`
- `.github/workflows/phase-i4e-forget-api-ui.yml`
- `docs/architecture/phase_i4e_forget_api_ui.md`
- this report

## Validation evidence

The dedicated workflow runs compileall, I-4/I-4B/I-4C1/I-4C2/I-4D/I-3 regressions, the new I-4E functional and security smokes, SOUL Lab typecheck/build, Home conversation smoke, and the new Forget UI smoke.

Final workflow state is recorded on PR #420.

## Known limitations

I-4F full crash/race/security/fresh-conversation validation remains open. Recent-memory Observation remains a bounded read projection and does not itself own ordinary retrieval exclusion; I-4D retrieval and used-memory lifecycle overlay remain the exclusion evidence. Restore, purge, unhide, and physical deletion remain unimplemented.

## Shared documentation update inputs

- Completion wording: I-4E loopback Forget API and SOUL Lab Forget UI complete.
- Remaining boundary: I-4F full validation remains unimplemented; Phase I-4 overall remains in progress until I-4F lands.
- Handoff: `docs/architecture/phase_i4e_forget_api_ui.md`.
- Schema additions: `relaylm.lab.memory_forget_preflight_request.v0`, `relaylm.lab.memory_forget_apply_request.v0`, `relaylm.lab.memory_forget_preflight.v0`, `relaylm.lab.memory_forget_apply.v0`.
- Cross-slice risk: later integration must preserve I-4B/I-4C1/I-4C2/I-4D authority separation.
- Recommended next phase: I-4F after I-4E product surface stabilizes.

## Source pull request

- PR: #420
- URL: https://github.com/rinsakamo/relay-lm/pull/420

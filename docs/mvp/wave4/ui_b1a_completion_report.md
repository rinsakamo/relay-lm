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
# UI-B1A Lifecycle Visibility Completion Report

This report is evidence for one implementation pull request. It is not repository-wide current-status authority and does not open the next wave or release/evaluation gate.

## Scope

UI-B1A adds read-only lifecycle and operation visibility to SOUL Lab Home and Lab Observation after W3-INT. The implementation branch starts from `main` SHA `e77cfc612db33545a3a1891d03d359dff18f9e39`, where W3-INT is merged and Wave 4 follow-up planning may use the frozen W3-INT authority map and inputs.

## Implemented production boundary

The implementation adds a loopback-only Lab API projection at `GET /lab/api/characters/{character_id}/lab/lifecycle-visibility?namespace=...` with schema `relaylm.lab.lifecycle_visibility.v0`. The route reuses server-owned SOUL Lab observation scope resolution and returns `Cache-Control: no-store`.

The projection reports bounded, content-free status for:

- Primary MEM current lifecycle vocabulary: `active`, `hidden`, `prepared`, `recovery_required`, `corrupt`, `unknown`;
- durable-finalization vocabulary: `pending`, `complete`, `isolated`, `mixed`, `none`, `unknown`, `unavailable`, `not_connected`;
- queue/worker vocabulary: `queued`, `processing`, `formed`, `held`, `blocked`, `failed`, `mixed`, `none`, `unknown`, `unavailable`, `not_connected`;
- Fresh Conversation semantics: browser-local Home session reset, durable memory store retained, active current memories remain retrievable, hidden/current-ineligible memories remain excluded, and the Home transcript is not durable source evidence.

The Home and Lab Observation UI surfaces render this projection through wrapper components without changing the existing Home conversation contract or the existing Phase I-3 Correct-only mutation surface.

## Preserved authorities and non-goals

The implementation preserves I-4B/I-4C/I-4D current-state and lifecycle authorities, I1-G durable-finalization authorities, O1 queue/scheduler authorities, and existing SOUL Lab management/observation access control. The UI-B1A projection is not an apply authority and is not a scheduler, worker, recovery, cleanup, or repair authority.

This pull request adds no Forget apply, Pin apply, Held apply, SOUL apply, queue run, scheduler run, worker run, replay run, recovery control, repair control, cleanup control, restore, purge, unhide, browser-owned namespace/store/backend/route authority, durable transcript persistence, public binding, remote binding, TTS, audio, avatar, Live2D, or ASR behavior.

## Changed files

- `relaylm/soul_lab_lifecycle_visibility_projection.py`
- `relaylm/soul_lab_app.py`
- `apps/soul-lab/src/features/lifecycle/lifecycleVisibilityApi.ts`
- `apps/soul-lab/src/features/lifecycle/LifecycleVisibilityPanel.tsx`
- `apps/soul-lab/src/features/lifecycle/LifecycleAwareHomeConversationPage.tsx`
- `apps/soul-lab/src/features/lifecycle/ConnectedLifecycleLabObservationPage.tsx`
- `apps/soul-lab/src/app/App.tsx`
- `apps/soul-lab/src/app/RootApp.tsx`
- `apps/soul-lab/package.json`
- `apps/soul-lab/scripts/lifecycleVisibilitySmoke.mjs`
- `scripts/relaylm_ui_b1a_lifecycle_visibility_api_smoke.py`
- `scripts/relaylm_ui_b1a_lifecycle_visibility_security_smoke.py`
- `.github/workflows/soul-lab-ui-b1a-lifecycle-visibility.yml`
- `docs/architecture/soul_lab_ui_b1a_lifecycle_visibility.md`
- `docs/mvp/wave4/ui_b1a_completion_report.md`

## Validation evidence

The new UI-B1A workflow runs Python 3.12 editable installation, `compileall`, the UI-B1A API smoke, the UI-B1A route/security smoke, SOUL Lab TypeScript typecheck, the lifecycle visibility frontend smoke, and the SOUL Lab production build.

The API smoke verifies active Primary MEM lifecycle visibility, durable-finalization pending/complete/isolated status, queue/worker queued/processing/formed/held/blocked/failed status, Fresh Conversation invariants, and public projection leakage canaries for raw content, job/dispatch prefixes, claim tokens, exception text, and raw paths.

The security smoke verifies the loopback-only route boundary, `Cache-Control: no-store`, lack of mutation-control flags, lack of scheduler/worker controls, no raw content/path/private-identifier flags, no durable store reset from Fresh Conversation, no Home transcript durable-source claim, HTTP method rejection for mutation verbs, and remote-client spoofing rejection.

## Known limitations

UI-B1A is status visibility, not lifecycle mutation. Counts and statuses are bounded summaries intended for local SOUL Lab interpretation and do not substitute for the lower-level durable-finalization, queue, scheduler, worker, or current-state authorities. It does not prove semantic memory quality, end-user conversational quality, physical secure deletion, scheduler fairness, stale-claim recovery, operational supervision, or always-on production operation.

## Shared documentation update inputs

The later Wave 4 convergence pull request may record the following only after this implementation PR is merged and its CI evidence remains green:

- UI-B1A completed read-only lifecycle and operation visibility for SOUL Lab Home and Lab Observation.
- UI-B1A exposes only loopback-only, server-owned, content-free lifecycle/operation projection status and no mutation or scheduler controls.
- Fresh Conversation may be described in SOUL Lab as a browser-local Home session reset that retains durable memory and does not make the Home transcript durable source evidence.
- The implementation evidence path is `docs/mvp/wave4/ui_b1a_completion_report.md`.
- I-4E/I-4F, I-5A, I-7A/B, O1D2/O1E/O1F, and later operational phases remain separate boundaries.

## Source pull request

- PR: #421
- URL: https://github.com/rinsakamo/relay-lm/pull/421

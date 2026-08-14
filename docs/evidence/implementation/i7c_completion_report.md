---
relaylm_doc_type: implementation_completion_report
relaylm_authority: phase_i7c_held_governance_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../contracts/memory/held-governance.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current Held Apply / Discard runtime, API, UI, or governance behavior
  - current queue lifecycle or worker execution behavior
  - current implementation sequencing or release readiness
  - current operator procedure
relaylm_source_commit: 4add07ae3084b8f4bf1364189411014bb71cf118
relaylm_source_origin_commit: 21d10bfed22ed9626e4224bf927ff59a5e399505
relaylm_source_pr: 431
relaylm_recorded_on: 2026-06-27
relaylm_source_blob: 447298a00d418f461abda33060e7f59d96656c64
relaylm_source_content_sha256: 97e242a355bb0fd204492fb697ed6523ed85812cd3e73e7cb73696a89e258907
relaylm_exact_source_snapshot: i7c_completion_report-source.txt
---
# I-7C completion report

## Status and authority

This document is frozen implementation evidence for the I-7C Held Apply / Discard runtime-governance, API/UI, durable-evidence, and leakage-boundary slice introduced by PR #431, whose final source head is `4add07ae3084b8f4bf1364189411014bb71cf118` and merge commit is `21d10bfed22ed9626e4224bf927ff59a5e399505`. Current repository-wide status belongs to [Project Status](../../PROJECT_STATUS.md). Current Held Apply / Discard behavior belongs to [Held Apply / Discard Governance Contract](../../contracts/memory/held-governance.md), the production implementation, and the focused I-7A/B and I-7C smoke suite.

The exact pre-cutover report is retained byte-for-byte as [i7c_completion_report-source.txt](i7c_completion_report-source.txt). Statements below describe the source PR boundary unless explicitly qualified. Legacy-path strings inside the exact snapshot are historical source text, not live repository references.

Last reviewed: 2026-06-27 JST

This report is evidence for one implementation pull request. It is not current runtime, repository-wide status, sequencing, release-readiness, queue-lifecycle, worker-execution, or operator-procedure authority.

## Scope

I-7C implements Held Apply / Discard runtime governance for one already-held outcome candidate. The slice connects I-7A/B read-only preflight to durable runtime-private governance evidence, loopback SOUL Lab API routes, SOUL Lab UI controls, and smoke/workflow validation.

## Implemented production boundary

- Added runtime-private held candidate evidence admission and durable Apply / Discard decision receipts.
- Added preflight-token validation, exact replay/idempotency convergence, operation conflict detection, stale candidate detection, and source-evidence fail-closed behavior.
- Added loopback-only character/namespace-scoped held governance API routes.
- Added SOUL Lab UI client and panel for explicit preflight followed by explicit Apply or Discard confirmation.
- Updated the held observation list so held candidates are actionable without rendering held title/body/summary content.
- Added dedicated runtime, API, concurrency, security, UI source, and UI TypeScript smoke coverage.

## Preserved authorities and non-goals

- I-7A/B remains the governability preflight authority.
- I-4 current-state resolver remains the related Primary MEM validation authority.
- B3 queue lifecycle authority is preserved; I-7C does not create a new queue transition helper and does not rewrite queue files.
- Primary MEM semantic content is not changed by Discard, and I-7C does not invent a new Primary mutation.
- No worker, scheduler, retry loop, daemon, service supervision, polling, O1 invocation, C2 invocation from UI, Pin/Unpin apply, Forget restore/unhide/purge, Secondary MEM consolidation, RelaySOUL mutation, or source/body display is added.

## Changed files

- `relaylm/relaymem_held_governance.py`
- `relaylm/soul_lab_held_governance.py`
- `relaylm/lab_held_governance_api.py`
- `relaylm/soul_lab_app.py`
- `apps/soul-lab/src/features/lab/heldGovernanceApi.ts`
- `apps/soul-lab/src/features/lab/HeldGovernancePanel.tsx`
- `apps/soul-lab/src/features/lab/ConnectedLabObservationPage.tsx`
- `apps/soul-lab/scripts/heldGovernanceUiSmoke.mjs`
- `apps/soul-lab/package.json`
- `scripts/relaylm_phase_i7c_held_governance_runtime_smoke.py`
- `scripts/relaylm_phase_i7c_held_governance_api_smoke.py`
- `scripts/relaylm_phase_i7c_held_governance_concurrency_smoke.py`
- `scripts/relaylm_phase_i7c_held_governance_security_smoke.py`
- `scripts/relaylm_phase_i7c_held_governance_ui_smoke.py`
- `docs/architecture/phase_i7c_held_apply_discard_runtime.md`
- `docs/evidence/implementation/i7c_completion_report.md`
- `.github/workflows/phase-i7c-held-governance-runtime.yml`

## Validation evidence

Expected validation commands for source PR #431:

```bash
python -m compileall relaylm scripts
PYTHONPATH=.:scripts python scripts/relaylm_i7ab_held_apply_discard_contract_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i7c_held_governance_runtime_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i7c_held_governance_api_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i7c_held_governance_concurrency_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i7c_held_governance_security_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i7c_held_governance_ui_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i4d_primary_retrieval_exclusion_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_o1e_scheduler_operational_controls_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_relayslp_queue_state_smoke.py
cd apps/soul-lab
npm install
npm run build
npm run smoke:held-governance-ui
cd ../..
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/i7c_completion_report.md
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_docs_link_check.py
```

Local authoring validation recorded at source PR #431:

```bash
python -m py_compile relaylm/relaymem_held_governance.py relaylm/soul_lab_held_governance.py relaylm/lab_held_governance_api.py relaylm/soul_lab_app.py
python -m py_compile scripts/relaylm_phase_i7c_held_governance_runtime_smoke.py scripts/relaylm_phase_i7c_held_governance_api_smoke.py scripts/relaylm_phase_i7c_held_governance_concurrency_smoke.py scripts/relaylm_phase_i7c_held_governance_security_smoke.py scripts/relaylm_phase_i7c_held_governance_ui_smoke.py
```

At source PR #431, GitHub Actions was the execution source of truth for the listed validation. The dedicated I-7C workflow present at that source boundary is absent from the current tree and is not recreated during this cutover. Current validation routing belongs to the consolidated workflow and smoke inventory.

## Known limitations

- I-7C records the human governance decision and does not start downstream work.
- Queue terminal/cancel/dead-letter state changes remain future work unless an existing B3 authority is explicitly wired for a narrower case.
- Held candidate discovery from worker output remains a bounded evidence-admission helper rather than a scanner, daemon, or scheduler.
- Shared `PROJECT_STATUS.md`, execution plan, indexes, and cross-slice current-target docs are intentionally left for the Wave 6 convergence PR unless a link-smoke requires a minimal link.

## Shared documentation update inputs

At source PR #431, the later Wave 6 convergence thread was expected to:

- Mark `I-7C Held Apply / Discard runtime/API/UI/durable governance evidence` complete.
- Link `docs/architecture/phase_i7c_held_apply_discard_runtime.md`.
- Link `docs/evidence/implementation/i7c_completion_report.md`.
- Preserve that O1F, I-5B, and E1 follow-ups remain separate next candidates unless completed in parallel.

## Source pull request

- PR: #431
- URL: https://github.com/rinsakamo/relay-lm/pull/431

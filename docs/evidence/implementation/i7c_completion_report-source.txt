# I-7C completion report

relaylm_doc_type: implementation_completion_report
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_current_status_source: ../../PROJECT_STATUS.md

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
- `docs/mvp/wave6/i7c_completion_report.md`
- `.github/workflows/phase-i7c-held-governance-runtime.yml`

## Validation evidence

Expected PR validation:

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
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/i7c_completion_report.md
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_docs_link_check.py
```

Local authoring validation before PR creation:

```bash
python -m py_compile relaylm/relaymem_held_governance.py relaylm/soul_lab_held_governance.py relaylm/lab_held_governance_api.py relaylm/soul_lab_app.py
python -m py_compile scripts/relaylm_phase_i7c_held_governance_runtime_smoke.py scripts/relaylm_phase_i7c_held_governance_api_smoke.py scripts/relaylm_phase_i7c_held_governance_concurrency_smoke.py scripts/relaylm_phase_i7c_held_governance_security_smoke.py scripts/relaylm_phase_i7c_held_governance_ui_smoke.py
```

## Known limitations

- I-7C records the human governance decision and does not start downstream work.
- Queue terminal/cancel/dead-letter state changes remain future work unless an existing B3 authority is explicitly wired for a narrower case.
- Held candidate discovery from worker output remains a bounded evidence-admission helper rather than a scanner, daemon, or scheduler.
- Shared `PROJECT_STATUS.md`, execution plan, indexes, and cross-slice current-target docs are intentionally left for the Wave 6 convergence PR unless a link-smoke requires a minimal link.

## Shared documentation update inputs

For the Wave 6 convergence PR:

- Mark `I-7C Held Apply / Discard runtime/API/UI/durable governance evidence` complete.
- Link `docs/architecture/phase_i7c_held_apply_discard_runtime.md`.
- Link `docs/mvp/wave6/i7c_completion_report.md`.
- Preserve that O1F, I-5B, and E1 follow-ups remain separate next candidates unless completed in parallel.

## Source pull request

- PR: #431
- URL: https://github.com/rinsakamo/relay-lm/pull/431

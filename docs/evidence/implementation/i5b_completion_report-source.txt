# I-5B completion report: Pin / Unpin apply phase

relaylm_doc_type: implementation_completion_report
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_current_status_source: ../../PROJECT_STATUS.md

## Scope

I-5B implements explicit Pin / Unpin apply behavior for one current active Primary MEM after I-5A token preflight. The slice connects token-confirmed durable runtime-private Pin / Unpin evidence, loopback SOUL Lab API routes, SOUL Lab UI controls, a bounded Pin-aware ranking helper, and smoke/workflow validation.

## Implemented production boundary

- Added `relaylm/relaymem_primary_pin_apply.py` as the durable Primary MEM Pin / Unpin apply authority.
- Added runtime-private Pin / Unpin receipts under `memory/mem/pins/v0/<memory_id>/` and a bounded `state.json` projection.
- Added receipt-derived state convergence when `state.json` is absent after a crash window.
- Added explicit same-operation idempotent replay handling that republishes the state projection from the existing valid receipt.
- Added a Pin-aware ranking helper that only reorders already eligible candidates and preserves original order as deterministic tie-break.
- Added strict loopback-only SOUL Lab Pin / Unpin request contracts, route wiring, browser client parsing, and `PrimaryMemoryPinPanel` controls.
- Added dedicated apply, idempotency, ranking, security, UI source, and UI TypeScript smoke coverage.

## Preserved authorities and non-goals

- I-4B current-state resolver remains the current active Primary MEM authority.
- I-4D lifecycle exclusion remains the ordinary retrieval eligibility authority.
- I-5A token validation remains the Pin / Unpin token authority.
- Correct / Forget / Pin / Unpin share the existing per-memory mutation lock and shared operation inspection fence.
- Pin state is a ranking hint only; it does not expand retrieval eligibility and does not bypass lifecycle exclusion.
- No hidden-memory retrieval, restore, unhide, purge, physical deletion, semantic memory rewrite, Secondary MEM consolidation, Merge/Supersession, Held Apply / Discard runtime, queue/worker/scheduler change, or automatic ranking learning is added.

## Changed files

- `.github/workflows/phase-i5b-pin-unpin-apply.yml`
- `apps/soul-lab/package.json`
- `apps/soul-lab/scripts/pinUnpinUiSmoke.mjs`
- `apps/soul-lab/src/features/lab/ConnectedLabObservationPage.tsx`
- `apps/soul-lab/src/features/lab/PrimaryMemoryPinPanel.tsx`
- `apps/soul-lab/src/features/lab/pinApi.ts`
- `docs/architecture/phase_i5b_pin_unpin_apply.md`
- `docs/mvp/wave6/i5b_completion_report.md`
- `relaylm/relaymem_primary_pin_apply.py`
- `relaylm/relaymem_primary_pin_ranking.py`
- `relaylm/soul_lab_app.py`
- `relaylm/soul_lab_memory_pin.py`
- `relaylm/soul_lab_memory_pin_routes.py`
- `scripts/relaylm_phase_i5b_pin_unpin_apply_smoke.py`
- `scripts/relaylm_phase_i5b_pin_unpin_concurrency_smoke.py`
- `scripts/relaylm_phase_i5b_pin_unpin_ranking_smoke.py`
- `scripts/relaylm_phase_i5b_pin_unpin_security_smoke.py`

## Validation evidence

Expected PR validation:

```bash
python -m compileall relaylm scripts
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5a_pin_unpin_contract_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5b_pin_unpin_apply_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5b_pin_unpin_ranking_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5b_pin_unpin_concurrency_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5b_pin_unpin_security_smoke.py
cd apps/soul-lab
npm install
npm run build
npm run smoke:pin-unpin-ui
cd ../..
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/i5b_completion_report.md
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_docs_link_check.py
```

Connector-side authoring was performed through the GitHub connector because a local checkout is unavailable in this environment. GitHub Actions is the execution source of truth for the full listed validation.

## Known limitations

- Pin / Unpin is not exposed as a background operation and does not run from a scheduler, retry loop, daemon, or worker.
- Pin state affects only deterministic ordering among already eligible Primary MEM candidates.
- The ranking helper does not make hidden, stale, corrupt, or lifecycle-excluded memories eligible.
- Public projections remain content-free and path-free for Pin / Unpin artifacts; receipt bodies are runtime-private.
- Shared `PROJECT_STATUS.md`, execution plan, indexes, and cross-slice current-target docs are intentionally left for the Wave 6 convergence PR unless a link-smoke requires a minimal link.

## Shared documentation update inputs

For the Wave 6 convergence PR:

- Mark `I-5B Pin / Unpin apply/API/UI/durable governance evidence/ranking hint` complete.
- Link `docs/architecture/phase_i5b_pin_unpin_apply.md`.
- Link `docs/mvp/wave6/i5b_completion_report.md`.
- Preserve that Pin state is ranking-hint-only and never an eligibility expansion authority.

## Source pull request

- PR: #430
- URL: https://github.com/rinsakamo/relay-lm/pull/430

---
relaylm_doc_type: implementation_completion_report
relaylm_authority: phase_i5b_pin_unpin_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/phase_i5b_pin_unpin_apply.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current Pin / Unpin runtime, API, UI, or ranking behavior
  - current implementation sequencing or release readiness
  - current operator procedure
  - current retrieval eligibility rules outside the I-5B source boundary
relaylm_source_commit: eac44fb0038c0a7eadd94c1d29b2ce90f52a6349
relaylm_source_origin_commit: 734a3880035651f91eb065b892fc41af6f5cc026
relaylm_source_pr: 430
relaylm_recorded_on: 2026-06-28
relaylm_source_blob: 19d631470dc0cf16e65c214169e3097758381de9
relaylm_source_content_sha256: 2efce2a61fb09b9ed4226d2a09e6e6b78645bf11f65badc855e03f7e64b8aa85
relaylm_exact_source_snapshot: i5b_completion_report-source.txt
---
# I-5B completion report: Pin / Unpin apply phase

## Status and authority

This document is frozen implementation evidence for the I-5B Pin / Unpin apply, API/UI, durable-governance, and ranking-hint slice introduced by PR #430, whose final source head is `eac44fb0038c0a7eadd94c1d29b2ce90f52a6349` and merge commit is `734a3880035651f91eb065b892fc41af6f5cc026`. Current repository-wide status belongs to [Project Status](../../PROJECT_STATUS.md). Current Pin / Unpin behavior belongs to [Phase I-5B Pin / Unpin apply and ranking behavior](../../architecture/phase_i5b_pin_unpin_apply.md), the production implementation, and the focused I-5A/I-5B smoke suite.

The exact pre-cutover report is retained byte-for-byte as [i5b_completion_report-source.txt](i5b_completion_report-source.txt). Statements below describe the source PR boundary unless explicitly qualified.

Last reviewed: 2026-06-28 JST

This report is evidence for one implementation pull request. It is not current runtime, repository-wide status, sequencing, release-readiness, or operator-procedure authority.

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

At source PR #430, the implementation boundary included:

- `apps/soul-lab/package.json`
- `apps/soul-lab/scripts/pinUnpinUiSmoke.mjs`
- `apps/soul-lab/src/features/lab/ConnectedLabObservationPage.tsx`
- `apps/soul-lab/src/features/lab/PrimaryMemoryPinPanel.tsx`
- `apps/soul-lab/src/features/lab/pinApi.ts`
- `docs/architecture/phase_i5b_pin_unpin_apply.md`
- `docs/evidence/implementation/i5b_completion_report.md`
- `relaylm/relaymem_primary_pin_apply.py`
- `relaylm/relaymem_primary_pin_ranking.py`
- `relaylm/soul_lab_app.py`
- `relaylm/soul_lab_memory_pin.py`
- `relaylm/soul_lab_memory_pin_routes.py`
- `scripts/relaylm_phase_i5b_pin_unpin_apply_smoke.py`
- `scripts/relaylm_phase_i5b_pin_unpin_concurrency_smoke.py`
- `scripts/relaylm_phase_i5b_pin_unpin_ranking_smoke.py`
- `scripts/relaylm_phase_i5b_pin_unpin_security_smoke.py`

The dedicated I-5B workflow present at the source PR boundary is absent from the current tree and is not recreated by this cutover.

## Validation evidence

Expected validation commands for the source boundary:

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
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/i5b_completion_report.md
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_docs_link_check.py
```

At source PR #430, GitHub Actions was the execution source of truth for the full listed validation. Current validation routing belongs to the consolidated workflow and smoke inventory rather than the removed dedicated workflow.

## Known limitations

- Pin / Unpin is not exposed as a background operation and does not run from a scheduler, retry loop, daemon, or worker.
- Pin state affects only deterministic ordering among already eligible Primary MEM candidates.
- The ranking helper does not make hidden, stale, corrupt, or lifecycle-excluded memories eligible.
- Public projections remain content-free and path-free for Pin / Unpin artifacts; receipt bodies are runtime-private.
- Shared repository-wide state is not owned by this report.

## Shared documentation update inputs

At source PR #430, the later Wave 6 convergence thread was expected to:

- mark `I-5B Pin / Unpin apply/API/UI/durable governance evidence/ranking hint` complete;
- link `docs/architecture/phase_i5b_pin_unpin_apply.md`;
- link `docs/evidence/implementation/i5b_completion_report.md`;
- preserve that Pin state is ranking-hint-only and never an eligibility expansion authority.

## Source pull request

- PR: #430
- URL: https://github.com/rinsakamo/relay-lm/pull/430

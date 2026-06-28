---
relaylm_doc_type: mvp_completion_report
relaylm_authority: historical_evidence
relaylm_status: current
relaylm_owner: mvp_wave6
---
# I-5B completion report: Pin / Unpin apply phase

Date: 2026-06-27 JST

## Scope

I-5B adds durable Pin / Unpin apply evidence, bounded SOUL Lab API/UI contracts, production SOUL Lab route/panel wiring, and a deterministic Pin-aware ranking helper for already eligible Primary MEM candidates.

## Runtime behavior

- One current active Primary MEM can be pinned and unpinned through an explicit token-confirmed apply path.
- Pin / Unpin receipts are runtime-private, content-free governance evidence.
- Effective state can be derived from the latest valid receipt if `state.json` is missing after a crash.
- Same-operation replay returns an idempotent result and refreshes the state projection.
- Correct / Forget / Pin / Unpin share the per-memory mutation lock and existing Correct / Forget operation inspection.

## API/UI behavior

- Added strict Pin / Unpin browser request/response contracts.
- Browser request schemas do not accept store roots, paths, physical ids, route authority, or token claims.
- Mounted loopback-only Pin / Unpin routes from the existing SOUL Lab app via `relaylm/soul_lab_memory_pin_routes.py`.
- Mounted `PrimaryMemoryPinPanel` from active formed Primary MEM rows in `ConnectedLabObservationPage.tsx`.
- UI client parsing rejects private fields and requires explicit confirmation for apply.
- History projections are read-only, bounded, and content-free.

## Ranking behavior

Pin state is implemented as a ranking hint for candidates that are already selected and still eligible under Primary retrieval lifecycle rules. It does not expand eligibility and does not expose private Pin artifacts.

## Preserved authorities

- I-4B current-state resolver / shared mutation fence remains the mutation coordination authority.
- I-4D lifecycle exclusion remains the ordinary retrieval eligibility authority.
- I-4E loopback-only management boundary remains the API authority for production route wiring.
- I-5A token binding remains the preflight/apply contract authority.

## Security and leakage boundary

Public projections exclude raw reason text, reason digest, token digest, token claims, store root, filesystem path, physical id, raw exception text, and semantic memory content beyond existing bounded memory list displays.

## Validation

Implemented smoke coverage:

```bash
python -m compileall relaylm scripts
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5a_pin_unpin_contract_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5b_pin_unpin_apply_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5b_pin_unpin_ranking_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5b_pin_unpin_concurrency_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5b_pin_unpin_security_smoke.py
cd apps/soul-lab && npm run build && npm run smoke:pin-unpin-ui
```

Connector-side local validation was limited to syntax compilation of the generated new Python route module before commit. Full repository CI should run the listed commands on the PR branch.

## PR

PR: #430.

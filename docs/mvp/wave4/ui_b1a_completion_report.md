---
relaylm_doc_type: implementation_completion_report
relaylm_authority: ui_b1a_completion_report
relaylm_status: complete
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_source_pr: TBD
relaylm_related_handoff: ../../architecture/soul_lab_ui_b1a_lifecycle_visibility.md
---
# UI-B1A Completion Report

## Slice

UI-B1A: Read-only lifecycle and operation visibility.

## Summary

This slice adds a loopback-only read-only lifecycle visibility projection and SOUL Lab UI panels for Home and Lab Observation. The projection reports bounded Primary MEM current lifecycle, durable-finalization status, queue/worker status, and Fresh Conversation semantics without exposing raw content, raw paths, durable-finalization locators, queue/job/dispatch/claim identifiers, raw exceptions, store roots, or command payloads.

## Behavior added

- `GET /lab/api/characters/{character_id}/lab/lifecycle-visibility?namespace=...`
- schema `relaylm.lab.lifecycle_visibility.v0`
- Primary MEM lifecycle vocabulary: `active`, `hidden`, `prepared`, `recovery_required`, `corrupt`, `unknown`
- durable-finalization vocabulary: `pending`, `complete`, `isolated`, `mixed`, `none`, `unknown`, `unavailable`, `not_connected`
- queue/worker vocabulary: `queued`, `processing`, `formed`, `held`, `blocked`, `failed`, `mixed`, `none`, `unknown`, `unavailable`, `not_connected`
- Fresh Conversation explanation: browser-local session reset, durable store retained, active memories remain retrievable, hidden/current-ineligible memories remain excluded, Home transcript is not durable source

## Boundary preserved

UI-B1A remains read-only only. It adds no apply controls, queue controls, scheduler controls, worker controls, replay controls, recovery controls, repair controls, cleanup controls, restore/purge/unhide controls, durable transcript persistence, public binding, remote binding, TTS/audio/avatar/Live2D/ASR, or browser-owned authority.

## Validation

Required existing regression targets:

```bash
python -m compileall relaylm scripts
python scripts/relaylm_phase_i2_lab_observation_smoke.py
python scripts/relaylm_phase_i2_lab_observation_security_smoke.py
python scripts/relaylm_phase_i3_primary_mem_correct_smoke.py
python scripts/relaylm_phase_i4d_historical_projection_smoke.py
python scripts/relaylm_phase_i4d_primary_retrieval_exclusion_smoke.py
python scripts/relaylm_o1d1_production_round_security_smoke.py
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run smoke:home-conversation
npm run smoke:lifecycle-visibility
npm run build
```

New UI-B1A validation:

```bash
python scripts/relaylm_ui_b1a_lifecycle_visibility_api_smoke.py
python scripts/relaylm_ui_b1a_lifecycle_visibility_security_smoke.py
cd apps/soul-lab && npm run smoke:lifecycle-visibility
```

## Notes

Shared current-status/index documents are intentionally not updated in this slice beyond the dedicated handoff and Wave 4 completion report. Repository-wide status reconciliation is left to the next Wave 4 integration audit to avoid parallel current-status conflicts.

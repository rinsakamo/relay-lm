---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase_i4f_forget_product_validation
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase_i4e_forget_api_ui.md
  - phase_i4d_primary_retrieval_exclusion.md
  - phase_i4c2_primary_forget_recovery_finalization.md
  - phase_i4c1_primary_forget_hidden_successor.md
  - phase_i4b_primary_current_state_shared_fence.md
---
# Phase I-4F Forget Product Completion Validation

Last reviewed: 2026-06-27 JST

## Purpose

I-4F validates the completed explicit Forget / Hide product boundary over the existing I-4 authorities. It adds no new production mutation authority. The validated path is:

```text
one real current active Primary MEM
  -> SOUL Lab / loopback Forget preflight
  -> explicit confirmation with exact apply token
  -> existing I-4C1/I-4C2 hidden lifecycle apply/recovery
  -> I-4D ordinary M2 / RelayCTX exclusion
  -> browser refresh / fresh process / fresh conversation
  -> hidden memory remains retrieval-ineligible and not injected
  -> bounded receipt / history / lifecycle visibility
  -> no private-content leakage
```

## Preserved authorities

- I-4B remains current-state resolver, shared mutation fence, read-only preflight, token validation, and bounded history authority.
- I-4C1 remains durable prepared evidence and hidden-successor lifecycle commit authority.
- I-4C2 remains prepared resume, M3f/M3g convergence, tombstone finalization, public apply semantics, and response-loss replay authority.
- I-4D remains ordinary M2 / RelayCTX exclusion and historical lifecycle overlay authority.
- I-4E remains loopback-only API and SOUL Lab Forget UI authority.
- UI-B1A remains read-only lifecycle / operation visibility only.

## Validation matrix

| Area | Coverage |
|---|---|
| Product loop | `scripts/relaylm_phase_i4f_forget_validation_smoke.py` validates loopback preflight/apply, fresh process history reread, lifecycle overlay, and fresh ordinary conversation exclusion. |
| Crash/fault | `scripts/relaylm_phase_i4f_forget_validation_fault_smoke.py` validates preflight-only read-only behavior and invokes existing I-4C2 crash/restart seams plus I-4D fail-closed retrieval coverage. |
| Race/concurrency | `scripts/relaylm_phase_i4f_forget_validation_concurrency_smoke.py` validates Correct/Forget stale races, hidden-target rejection, and invokes existing one-winner I-4C2 concurrency coverage. |
| Security/token | `scripts/relaylm_phase_i4f_forget_validation_security_smoke.py` validates token binding/expiry/replay and invokes existing I-4C2 tombstone security plus I-4E loopback API security. |
| UI freshness | `scripts/relaylm_phase_i4f_forget_validation_ui_smoke.py` validates stale-generation fencing, explicit click confirmation, no hover/load apply trigger, strict API parsing, same-origin/no-store fetch, and bounded errors. |
| Browser API contract | `apps/soul-lab/scripts/forgetUiSmoke.mjs` remains the existing I-4E browser contract smoke and runs in the I-4F workflow. |

## Product-complete meaning

Forget is product-complete for explicit Hide of one current active Primary MEM. The validated result is that hidden, prepared, recovery-required, corrupt, ambiguous, unsafe, cross-scope, unresolved, and prior physical revision candidates cannot re-enter ordinary M2/RelayCTX or backend-bound messages, while historical used-memory receipts remain truthful through a separate read-only lifecycle overlay.

## Non-goals preserved

I-4F does not implement restore, unhide, purge, physical deletion, batch Forget, Secondary MEM consolidation, RelaySOUL mutation, Pin / Unpin runtime apply/API/UI/ranking behavior, Held Apply / Discard runtime/API/UI/durable evidence, queue/worker/scheduler/O1/O2/O3 behavior, polling, sleep loops, daemonization, service supervision, or always-on operation.

## Validation commands

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=.:scripts python scripts/relaylm_phase_i4f_forget_validation_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i4f_forget_validation_fault_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i4f_forget_validation_concurrency_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i4f_forget_validation_security_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i4f_forget_validation_ui_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_docs_link_check.py
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave5/i4f_completion_report.md
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
```

The I-4F workflow also runs key I-4B/I-4C1/I-4C2/I-4D/I-4E regressions and the existing SOUL Lab `npm run smoke:forget-ui` browser-contract smoke.

## Known limitations

Direct Home-origin Primary MEM formation remains unproven; I-4F validates Forget after a real current active Primary MEM exists. Pin/Unpin and Held Apply/Discard runtime behavior remain separate later phases.

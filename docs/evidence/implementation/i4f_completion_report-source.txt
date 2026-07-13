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
# I-4F Forget Product Completion Validation Report

This report is evidence for one implementation pull request. It is not repository-wide current-status authority and does not open unrelated runtime governance phases.

## Scope

- Slice: I-4F Forget Product Completion Validation Phase.
- Goal: validate the completed Forget / Hide product surface across crash, race, stale-browser, token, security, fresh-conversation, restart, and multi-character/scope isolation conditions.
- Base branch: `main`.
- Start boundary: post-Wave-4 main with I1-GA through I1-GE complete, O1A through O1D2 complete, I-4B through I-4E complete, UI-B0/UI-B1A complete, I-5A and I-7A/B complete only for contract/read-only preflight, and I-4F unimplemented.

## Implemented production boundary

I-4F is validation-first and adds no new production mutation authority. It proves that the existing I-4B/I-4C1/I-4C2/I-4D/I-4E path is product-complete for explicit Forget / Hide of one real current active Primary MEM:

```text
SOUL Lab / loopback preflight
  -> explicit apply-token confirmation
  -> hidden lifecycle commit / recovery / tombstone finalization
  -> ordinary M2 and RelayCTX exclusion
  -> fresh process, browser refresh, and fresh conversation reread
  -> bounded receipt/history/lifecycle visibility
  -> no private-content leakage
```

No production bug fix was required in this validation PR.

## Preserved authorities and non-goals

Preserved authorities: I-4B remains current-state resolver/token/fence/history authority; I-4C1 remains hidden-successor commit authority; I-4C2 remains recovery/tombstone/public-apply authority; I-4D remains retrieval-exclusion authority; I-4E remains loopback API/UI authority; UI-B1A remains read-only visibility only.

Non-goals preserved: no restore, unhide, purge, physical deletion, batch Forget, Secondary MEM consolidation, RelaySOUL mutation, Pin / Unpin runtime apply/API/UI/ranking behavior, Held Apply / Discard runtime/API/UI/durable evidence, queue/worker/scheduler/O1/O2/O3 changes, polling, sleep loops, daemonization, service supervision, or always-on operation.

## Changed files

- `docs/architecture/phase_i4f_forget_validation.md`
- `docs/mvp/wave5/i4f_completion_report.md`
- `scripts/relaylm_phase_i4f_forget_validation_smoke.py`
- `scripts/relaylm_phase_i4f_forget_validation_fault_smoke.py`
- `scripts/relaylm_phase_i4f_forget_validation_concurrency_smoke.py`
- `scripts/relaylm_phase_i4f_forget_validation_security_smoke.py`
- `scripts/relaylm_phase_i4f_forget_validation_ui_smoke.py`
- `.github/workflows/phase-i4f-forget-validation.yml`
- shared status/index/current-target docs and `scripts/relaylm_documentation_current_boundary_smoke.py`

## Validation evidence

Required focused validation commands:

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

The workflow also runs key I-4B/I-4C1/I-4C2/I-4D/I-4E regressions and the existing SOUL Lab `npm run smoke:forget-ui` browser-contract smoke. The validation matrix covers preflight-only read-only behavior, crash/restart seams, response-lost replay, one-winner races, Correct/Forget stale races, hidden-target rejection, strict token binding, loopback-only API access, tombstone/security leakage canaries, stale-browser fencing, no implicit apply triggers, fresh process reread, and fresh ordinary conversation exclusion.

## Known limitations

- Forget product-complete does not include restore, unhide, purge, physical deletion, or batch Forget.
- I-5A and I-7A/B remain contract/read-only preflight only; their runtime mutation/API/UI behavior is not completed by I-4F.
- O1E/O1F/O2/O3 remain separate operations work.
- Direct Home-origin Primary MEM formation remains unproven; I-4F validates Forget after a real current active Primary MEM exists.

## Shared documentation update inputs

- Completion wording: Phase I-4F full Forget validation is complete; Phase I-4 overall is complete through explicit Forget / Hide product validation.
- Forget product-complete means explicit loopback/SOUL Lab Forget can hide one current active Primary MEM and prove later ordinary retrieval/RelayCTX exclusion under crash, race, stale-browser, token, security, restart, fresh-conversation, and scope-isolation conditions.
- Remaining boundaries: restore/unhide/purge/physical deletion, Pin/Unpin runtime work, Held Apply/Discard runtime work, O1E/O1F operations work, E1 consolidation, and direct Home-origin formation decision.
- Handoff path: `docs/architecture/phase_i4f_forget_validation.md`.
- Config/schema changes: none.
- Cross-slice risk: I-4F must not be interpreted as a scheduler, worker, Pin/Unpin, Held Apply/Discard, Secondary MEM, RelaySOUL, restore, purge, or physical deletion authority.
- Recommended next phase: O1E/O1F operations work or E1 evaluation consolidation; Pin/Unpin and Held runtime work require separate definitions.

## Source pull request

- PR: #427
- URL: https://github.com/rinsakamo/relay-lm/pull/427

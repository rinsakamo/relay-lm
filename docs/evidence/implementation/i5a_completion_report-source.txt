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
  - Pin / Unpin apply implementation
---
# I-5A Completion Report: Pin / Unpin Contract and Read-Only Preflight

This report is evidence for one implementation pull request. It is not repository-wide current-status authority and does not update shared Wave 4 status indexes.

## Scope

- Slice: I-5A Pin / Unpin contract and read-only preflight
- Base branch: `main`
- Start main SHA: `e77cfc612db33545a3a1891d03d359dff18f9e39`
- Branch: `i5a-pin-unpin-contract-preflight`

## Implemented production boundary

I-5A adds the Pin / Unpin governance contract and a narrow read-only runtime boundary for preflight, token validation, and zero-item history projection.

The implemented boundary is:

```text
real current active Primary MEM
  -> current-state resolver reread
  -> shared mutation fence check
  -> read-only Pin or Unpin preflight
  -> bounded effect preview
  -> short-lived apply-token shaped contract
  -> zero-item read-only history projection
  -> no mutation
```

## Preserved authorities and non-goals

This slice intentionally does not implement Pin apply, Unpin apply, SOUL Lab API or UI, durable Pin state, retrieval ranking change, hidden-memory retrieval, semantic content mutation, physical deletion, queue, worker, scheduler, or durable-finalization changes.

The production boundary added by this slice is read-only. It uses current-state resolver reread and shared Primary mutation fence inspection before issuing or validating contract-shaped short-lived tokens.

## Changed files

- `docs/architecture/phase_i5_pin_unpin_contract.md`
- `relaylm/relaymem_primary_pin.py`
- `scripts/relaylm_phase_i5a_pin_unpin_contract_smoke.py`
- `scripts/relaylm_phase_i5a_pin_unpin_token_smoke.py`
- `scripts/relaylm_phase_i5a_pin_unpin_concurrency_smoke.py`
- `scripts/relaylm_phase_i5a_pin_unpin_security_smoke.py`
- `.github/workflows/phase-i5a-pin-unpin-contract.yml`
- this report

## Validation evidence

The I-5A smokes prove:

- active/current/none targets return read-only Pin preflight;
- active/current/none targets return read-only Unpin preflight;
- Pin and Unpin effect previews do not claim M2 ranking changes in I-5A;
- hidden targets fail closed;
- prepared/recovery-required targets fail closed;
- stale revisions fail closed;
- token validation rejects changed reason, operation id, memory id, namespace, revision, tampering, and expiry;
- token public payloads do not expose binding digests, physical ids, reason text, namespace, or store paths;
- Pin / Unpin preflight and validation do not create mutation artifacts or Primary page writes;
- Correct/Forget concurrency causes stale or conflict results rather than mutation.

Expected validation for the source PR:

```bash
python -m compileall relaylm scripts
python scripts/relaylm_phase_i3_primary_mem_correct_smoke.py
python scripts/relaylm_phase_i3_primary_mem_correct_security_smoke.py
python scripts/relaylm_phase_i4b_primary_forget_preflight_smoke.py
python scripts/relaylm_phase_i4c1_primary_forget_concurrency_smoke.py
python scripts/relaylm_phase_i4d_primary_retrieval_exclusion_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5a_pin_unpin_contract_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5a_pin_unpin_token_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5a_pin_unpin_concurrency_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i5a_pin_unpin_security_smoke.py
```

The dedicated workflow runs the I-5A smokes plus I-3/I-4 governance regressions.

## Known limitations

Pin apply, Unpin apply, durable Pin state, SOUL Lab API/UI, and retrieval ranking behavior remain unimplemented. I-5A treats Pin state as a contract-only target projection and does not persist or observe a real pinned state.

## Shared documentation update inputs

- Completion wording: I-5A Pin / Unpin contract and read-only preflight complete after the source PR merges.
- Remaining boundary: Pin apply, Unpin apply, durable Pin state, retrieval ranking behavior, and product UI remain unimplemented.
- Handoff: `docs/architecture/phase_i5_pin_unpin_contract.md`.
- Schema additions: `relaylm.lab.memory_pin_preflight_request.v0`, `relaylm.lab.memory_pin_preflight.v0`, `relaylm.lab.memory_pin_apply_request.v0`, `relaylm.lab.memory_pin_history.v0`, `relaylm.primary_pin_apply_token.v0`, `relaylm.lab.memory_unpin_preflight_request.v0`, `relaylm.lab.memory_unpin_preflight.v0`, `relaylm.lab.memory_unpin_apply_request.v0`, `relaylm.lab.memory_unpin_history.v0`, `relaylm.primary_unpin_apply_token.v0`.
- Cross-slice risk: later apply must preserve the shared Correct/Forget/Pin/Unpin mutation fence and must not make hidden memories retrievable.

## Source pull request

- PR: #417
- URL: https://github.com/rinsakamo/relay-lm/pull/417

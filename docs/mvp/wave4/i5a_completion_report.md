---
relaylm_doc_type: implementation_completion_report
relaylm_authority: wave4_i5a_pin_unpin_contract_preflight_completion
relaylm_status: complete_after_pr_merge
relaylm_volatility: frozen_after_merge
relaylm_owner: implementation
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - cross-slice sequencing
  - Pin / Unpin apply implementation
---
# I-5A Completion Report: Pin / Unpin Contract and Read-Only Preflight

This report is evidence for one Wave 4 implementation pull request. It is not repository-wide current-status authority and does not update shared Wave 4 status indexes.

## Scope completed

I-5A adds the Pin / Unpin governance contract and a narrow read-only runtime boundary for preflight, token validation, and zero-item history projection.

Implemented artifacts:

- `docs/architecture/phase_i5_pin_unpin_contract.md`
- `relaylm/relaymem_primary_pin.py`
- `scripts/relaylm_phase_i5a_pin_unpin_contract_smoke.py`
- `scripts/relaylm_phase_i5a_pin_unpin_token_smoke.py`
- `scripts/relaylm_phase_i5a_pin_unpin_concurrency_smoke.py`
- `scripts/relaylm_phase_i5a_pin_unpin_security_smoke.py`
- `.github/workflows/phase-i5a-pin-unpin-contract.yml`
- this report

## Boundary preserved

This slice intentionally does not implement:

- Pin apply;
- Unpin apply;
- SOUL Lab API or UI;
- durable Pin state;
- retrieval ranking change;
- hidden-memory retrieval;
- semantic content mutation;
- physical deletion;
- queue, worker, scheduler, or durable-finalization changes.

The production boundary added by this slice is read-only. It uses current-state resolver reread and shared Primary mutation fence inspection before issuing or validating contract-shaped short-lived tokens.

## Runtime behavior proven

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

## Validation commands

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

## Handoff to later slices

Later I-5B+ work may implement apply only after defining durable Pin / Unpin evidence and preserving this slice's exact identity, revision, lifecycle, mutation, token, and security boundaries.

## Source pull request

- PR: recorded on the GitHub pull request for this branch.

---
relaylm_doc_type: evidence
relaylm_authority: documentation_cutover_1c52_receipt
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - validated-head, merge attribution, or bookkeeping facts are finalized
relaylm_not_authoritative_for:
  - current runtime behavior
  - durable-finalization production authority
  - implementation sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
---
# Documentation Hard Cutover 1C-52 Receipt

- Cutover PR: #634
- Bookkeeping consolidation PR: #635
- Base main: `86d3af1b3c24569f1daf01b2b52ef8c5119046d8`
- Validated content head: `ca4a9bc98c48316dc777c9c7abf85f4d910a11ef`
- Merged commit: `8791d0495e1c4b56aa97b49acc27b745a65bdd4c`
- Merged at: `2026-07-22T08:16:33Z`
- Final cutover diff: 17 changed files, +610/-28
- Source: `docs/architecture/i1ge_durable_finalization_crash_validation.md`
- Canonical target: `docs/evidence/implementation/i1ge-durable-finalization-crash-validation-handoff.md`
- Disposition: `evidence_retained`, implemented as a move and retype from `implementation_handoff` / `historical_after_merge` to `evidence` / `frozen`
- Validation source PR: #411
- Validation final head: `6cb461cb614d14965f5a49c1c4b517755f44f4a6`
- Validation merge commit: `e2caa1bdb53468ca282e8f374ba8ceebf839c976`
- Validation merged at: `2026-06-26T22:41:44Z`
- Governance handoff source PR: #415
- Governance handoff merge commit: `394ea1628f2262625c460c60d6b218ccc90429ac`
- Governance handoff merged at: `2026-06-27T04:57:02Z`
- Source and pre-cutover blob: `c711874bc813f29e5ac23d85ebc315eeeb24eeba`
- Source content SHA-256: `4322642a4686ac77f2a72b695fc7d9e1ebe370670625b7ab5ea4278f46f50f57`
- Source recorded on: `2026-06-27`
- Current durable-finalization authority retained by: `docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md`, `docs/architecture/i1gd_durable_finalization_retention_cleanup.md`, implementation, and focused smokes
- Active referrers repaired: `docs/README.md`, `docs/architecture/README.md`, `docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md`, `docs/architecture/i1gd_durable_finalization_retention_cleanup.md`, `docs/architecture/soul_lab_ui_b1a_lifecycle_visibility.md`, `docs/evidence/implementation/i1ge_completion_report.md`, `docs/evidence/waves/wave3_cross_slice_convergence_audit.md`, `scripts/relaylm_e1_evaluation_consolidation_smoke.py`, `scripts/relaylm_wave3_cross_slice_convergence_smoke.py`, `scripts/relaylm_wave3_cross_slice_security_smoke.py`
- Immutable historical carriers preserved unchanged: `docs/evidence/waves/wave2_cross_slice_convergence_audit-source.txt`, `docs/evidence/waves/wave3_cross_slice_convergence_audit-source.txt`
- Fail-closed enforcement: `scripts/relaylm_i1ge_handoff_cutover_guard.py`, compiled and executed by `.github/workflows/documentation-current-boundary-smoke.yml`
- Guard self-test: 23 assertions
- Exact-head GitHub Actions: 16 workflows; 16 success, 0 failure, 0 pending
- Runtime files changed: 0
- `relaylm/**` files changed: 0
- Implementation-base integration: PR #629 merged before the final rebase as current main; it shared 0 cutover paths and no EV-1 content was duplicated in the cutover
- Unresolved review threads: 0

This receipt records the merged Cutover 1C-52 boundary. PR #634 merged as `8791d0495e1c4b56aa97b49acc27b745a65bdd4c` from reviewed head `ca4a9bc98c48316dc777c9c7abf85f4d910a11ef` on base `86d3af1b3c24569f1daf01b2b52ef8c5119046d8`; PR #635 consolidates those facts without changing the accepted cutover content. The historical I1-GE validation handoff remains non-authoritative for current runtime, contract, schema, storage, compatibility, alias, redirect, dual-read, or dual-write behavior.

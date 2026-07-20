---
relaylm_doc_type: evidence
relaylm_authority: documentation_cutover_1c47_receipt
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - merge attribution or bookkeeping facts are corrected from repository history
relaylm_not_authoritative_for:
  - current runtime behavior
  - Stream Unpack architecture
  - implementation sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
---
# Documentation Hard Cutover 1C-47 Receipt

- Cutover PR: #616
- Bookkeeping consolidation PR: #618
- Base main: `1ff1b1b9e501b59340c3b909a985edfc6c2a4d32`
- Final cutover head: `4b2ae3a5ea347d6479ad13b78ad6b8d6750ddf16`
- Merged commit: `341878ad1ff2df281e85e64095a2604bf0dab2f2`
- Merged at: `2026-07-20T15:16:17Z`
- Final cutover diff: 6 files, +496/-10
- Source: `docs/architecture/phase55a_stream_sentinel_buffer_dry_run_handoff.md`
- Canonical target: `docs/evidence/implementation/phase55a-stream-sentinel-buffer-dry-run-handoff.md`
- Disposition: `evidence_retained`, implemented as a move and retype from `implementation_handoff` / `historical_after_merge` to `evidence` / `frozen`
- Source PR: #311
- Source commit: `c0135a9547ef2eda6d58bf87a274cc009239b8aa`
- Source and pre-cutover blob: `95481903cd5cb43bc2444a8647fd44b919f7d9e7`
- Source and pre-cutover normalized SHA-256: `d46295251db3365fef805056a192278674ec09b043ace4bfec672b0dcedf8a5b`
- Current authority retained by: `docs/architecture/phase5_5_stream_unpack_bounded_slice.md`
- Live referrers repaired: parent architecture document and implementation evidence index
- Fail-closed enforcement: `scripts/relaylm_phase55a_handoff_cutover_guard.py`, compiled and executed by `.github/workflows/documentation-current-boundary-smoke.yml`
- Guard self-test after bookkeeping integration: 23 assertions
- Exact-head GitHub Actions: 15 workflow runs, 15 success, 0 failure
- Runtime files changed: 0
- `relaylm/**` files changed: 0
- Open-PR content imported: none
- Central migration ledger: integrated by PR #618
- `documentation-cutover-rules.yaml`: exact path override integrated by PR #618

This local receipt preserves the compact Cutover 1C-47 facts. The central append-only migration ledger is the collection-level migration record; the exact path override is the machine-readable disposition authority. The bookkeeping integration changes no cutover content, runtime behavior, storage behavior, contract, schema, or canonical architecture.

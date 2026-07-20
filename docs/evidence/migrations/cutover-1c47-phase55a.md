---
relaylm_doc_type: evidence
relaylm_authority: documentation_cutover_1c47_receipt
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - PR #616 is merged and the merge commit is recorded
relaylm_not_authoritative_for:
  - current runtime behavior
  - Stream Unpack architecture
  - implementation sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
---
# Documentation Hard Cutover 1C-47 Receipt

- Cutover PR: #616
- Base main: `1ff1b1b9e501b59340c3b909a985edfc6c2a4d32`
- Source: `docs/architecture/phase55a_stream_sentinel_buffer_dry_run_handoff.md`
- Canonical target: `docs/evidence/implementation/phase55a-stream-sentinel-buffer-dry-run-handoff.md`
- Disposition: moved and retyped from `implementation_handoff` / `historical_after_merge` to `evidence` / `frozen`
- Source PR: #311
- Source commit: `c0135a9547ef2eda6d58bf87a274cc009239b8aa`
- Source and pre-cutover blob: `95481903cd5cb43bc2444a8647fd44b919f7d9e7`
- Source and pre-cutover normalized SHA-256: `d46295251db3365fef805056a192278674ec09b043ace4bfec672b0dcedf8a5b`
- Current authority retained by: `docs/architecture/phase5_5_stream_unpack_bounded_slice.md`
- Live referrers repaired: parent architecture document and implementation evidence index
- Fail-closed enforcement: `scripts/relaylm_phase55a_handoff_cutover_guard.py`, compiled and executed by `.github/workflows/documentation-current-boundary-smoke.yml`
- Guard self-test: 20 assertions
- Runtime files changed: 0
- `relaylm/**` files changed: 0
- Open-PR content imported: none
- `merged_commit`: pending

This cutover uses a cutover-local receipt as an accepted sequencing deviation for the atomic relocation. The historical monolithic migration ledger and `documentation-cutover-rules.yaml` remain unchanged in this PR and require a later bookkeeping-only consolidation. The existing documentation-current-boundary workflow runs the fail-closed guard across repository text surfaces, preventing the retired path from returning before that bookkeeping consolidation.

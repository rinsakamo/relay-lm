---
relaylm_doc_type: evidence
relaylm_authority: documentation_cutover_1c55_receipt
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - validated-head merge attribution or bookkeeping facts are finalized
relaylm_not_authoritative_for:
  - current SOUL Lab runtime behavior
  - current public schema or storage authority
  - implementation sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
---
# Documentation Hard Cutover 1C-55 Receipt

- Cutover PR: #647
- Bookkeeping consolidation PR: pending after merge
- Base main: `80906b60aca640d9618d550d9decb12872d67a0d`
- Validated content head: `7acdd2f8d567e4b06a229105ade6c56969438243`
- Merged commit: `954eee9d26bd14d27da3d9a37e3caff9e6b760a3`
- Merged at: `2026-07-23T01:09:50Z`
- Source: `docs/architecture/phase_i2_real_soul_lab_observation.md`
- Canonical target: `docs/evidence/implementation/phase-i2-real-soul-lab-observation-handoff.md`
- Disposition: `evidence_retained`, implemented as a move and retype from `implementation_handoff` / `historical_after_merge` to `evidence` / `frozen`
- Source implementation PR: #377
- Source final head / merge / merged at: `a891dc67a47afeaf074443c69682adb7a5aa9fbc` / `4a24bdc9e6614433675eaa54f97b40647010c007` / `2026-06-24T12:34:06Z`
- Source and pre-cutover blob: `496c29ad94558a4bb0e12921cf20ad5358ae1120`
- Source content SHA-256: `989747ef065b315f94d079cf635e3da79c52dde45e3066cd4a3fae5cd0ef0079`
- Source recorded on: `2026-06-24`
- Pre-cutover path-bound referrer files: 13
- Referrers observed: `docs/README.md`, `docs/architecture/README.md`, `docs/architecture/integration_i1_primary_mem_two_turn_recall.md`, `docs/architecture/phase_i3_auditable_primary_mem_correct.md`, `docs/architecture/phase_i4_primary_mem_forget_hide_contract.md`, `docs/architecture/soul_lab_runtime_mvp.md`, `docs/architecture/soul_lab_ui_a7_management_projection_handoff.md`, `docs/architecture/soul_lab_ui_b0_real_home_conversation.md`, `docs/architecture/soul_lab_ui_b1a_lifecycle_visibility.md`, `docs/architecture/soul_lab_ui_mvp.md`, `docs/evidence/evaluations/e1_local_runtime_evaluation_2026_06_25.md`, `scripts/relaylm_e1_evaluation_consolidation_smoke.py`, `scripts/relaylm_phase_i2_documentation_boundary_smoke.py`
- Active path-bound references repaired: all 13
- Runtime files changed: 0
- `relaylm/**` files changed: 0
- Project-status preservation: `docs/PROJECT_STATUS.md` is unchanged; PR #645 remains separately owned.
- Parallel implementation: PR #646 merged first as `80906b60aca640d9618d550d9decb12872d67a0d`; the cutover was synchronized afterward, preserved its SM-1 architecture-index entry, and removed only the two retired Phase I-2 entries.
- Fail-closed enforcement: `scripts/relaylm_phase_i2_handoff_cutover_guard.py`, compiled and executed by `.github/workflows/documentation-current-boundary-smoke.yml`
- Guard self-test: 24 assertions
- Exact-head GitHub Actions: 16 workflow runs; 16 success; 0 failure; 0 pending; 0 skipped
- Unresolved review threads: 0

## Semantic coverage matrix

| # | Historical rule | Independent current owner |
|---:|---|---|
| 1 | loopback-only character/namespace-scoped observation routes | `relaylm/soul_lab_app.py`; current SOUL Lab architecture |
| 2 | exact versioned public observation schemas | `relaylm/soul_lab_observation.py`; browser schema validator |
| 3 | completed-run-only response-finalization observation | observation middleware and focused Phase I-2 smoke |
| 4 | validated recent Primary-memory projection | current Primary store implementation and SOUL Lab projection |
| 5 | held/blocked secondary outcome receipts | current observation implementation; worker result remains authoritative |
| 6 | used-memory evidence at RelayCTX injection boundary | current observation wrapper and RelayCTX implementation |
| 7 | bounded durable observation store safety | current observation store implementation and security smokes |
| 8 | read-only UI states and stale-response rejection | current SOUL Lab frontend and UI architecture |
| 9 | no repair, retrieval, mutation, scheduling, or adapter authority | current subsystem contracts and implementations |
| 10 | repository-wide completion/status | `docs/PROJECT_STATUS.md` |

## Conclusion

Every current normative behavior recorded by the old Phase I-2 handoff is independently owned by current SOUL Lab architecture, implementation, frontend validation, Project Status, and focused executable validation. The move therefore removes no unique current authority. The canonical document is frozen historical evidence only.

---
relaylm_doc_type: evidence
relaylm_authority: documentation_cutover_1c54_receipt
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - validated-head merge attribution or bookkeeping facts are finalized
relaylm_not_authoritative_for:
  - current runtime behavior
  - Primary Forget production authority
  - implementation sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
---
# Documentation Hard Cutover 1C-54 Receipt

- Cutover PR: #642
- Bookkeeping consolidation PR: #644
- Integration base / current main at final review: `32135811283edffa4408846c8a9e51173aea743e`
- Validated content head: `9b92df29a2cd112c6ad80086fdcfa4ad0e6fd0d6`
- Merged commit: `a21b9ac617fcf11d85a52e919f2ecb8678485927`
- Merged at: `2026-07-22T16:24:41Z`
- Final cutover diff: 16 changed files, +410/-31
- Source: `docs/architecture/phase_i4c2_primary_forget_recovery_finalization.md`
- Canonical target: `docs/evidence/implementation/i4c2-primary-forget-recovery-finalization-handoff.md`
- Disposition: `evidence_retained`, implemented as a move and retype from `implementation_handoff` / `historical_after_merge` to `evidence` / `frozen`
- Source implementation PRs: #404 and #407
- PR #404 final head / merge / merged at: `73416fab26f12e8c34793959bd3229f5c9fe8c59` / `97e5a1060bface993bb4382f9a50074aca1ec37d` / `2026-06-26T13:13:22Z`
- PR #407 final head / merge / merged at: `b4bff3b4804afa0e6f81d00410cd0d73512a15b7` / `c23b82da89853947eb5a2269760e24d7c25829c0` / `2026-06-26T13:55:01Z`
- Source and pre-cutover blob: `ab8f8e0f906690dfc9a28c680f4fb2b230211ce1`
- Source content SHA-256: `f0b6eeef01f423283ef0b48cf9e8940b1edfacef23a0483669058ff4d81bba92`
- Source recorded on: `2026-06-26`
- Pre-cutover path-bound referrer files: 10
- Referrers observed: `docs/README.md`, `docs/architecture/README.md`, `docs/architecture/phase_i4_primary_mem_forget_hide_contract.md`, `docs/architecture/phase_i4f_forget_validation.md`, `docs/evidence/implementation/i4c1-primary-forget-hidden-successor-handoff.md`, `docs/evidence/implementation/i4e_completion_report.md`, `docs/evidence/implementation/i4f_completion_report.md`, `docs/evidence/migrations/cutover-1c53-i4c1.md`, `docs/evidence/waves/wave2_cross_slice_convergence_audit-source.txt`, `docs/evidence/waves/wave2_cross_slice_convergence_audit.md`
- Active referrers repaired: `docs/README.md`, `docs/architecture/README.md`, `docs/architecture/phase_i4_primary_mem_forget_hide_contract.md`, `docs/architecture/phase_i4f_forget_validation.md`, `docs/evidence/implementation/i4c1-primary-forget-hidden-successor-handoff.md`, `docs/evidence/implementation/i4e_completion_report.md`, `docs/evidence/implementation/i4f_completion_report.md`, `docs/evidence/waves/wave2_cross_slice_convergence_audit.md`
- Historical references intentionally preserved only in the Wave 2 byte-exact source snapshot, Cutover 1C-53 receipt, cutover rules, and migration ledger.
- Parallel-work resolution: PR #636 and PR #639 merged before final review; their ASM-1 and OVL-1 changes were retained during exact main synchronization. PR #643 was open at merge time, changed only `docs/PROJECT_STATUS.md`, and had no cutover-path overlap. No open-PR content was imported.
- Runtime files changed: 0
- `relaylm/**` files changed: 0
- Project-status preservation: `docs/PROJECT_STATUS.md` was unchanged by Cutover 1C-54; later status convergence remains separately owned by PR #643.
- Fail-closed enforcement: `scripts/relaylm_i4c2_handoff_cutover_guard.py`, compiled and executed by `.github/workflows/documentation-current-boundary-smoke.yml`
- Guard self-test: 24 assertions
- Exact-head GitHub Actions: 16 workflows; 16 success, 0 failure, 0 pending
- Unresolved review threads: 0

## Semantic coverage matrix

| # | Historical rule | Independent current owner |
|---:|---|---|
| 1 | public apply/recover entry points | `relaylm/relaymem_primary_forget_recovery.py`; Phase I-4 master contract |
| 2 | sole shared Correct/Forget lock | `relaylm/relaymem_primary_mutation_coordinator.py`; master contract §9 |
| 3 | prepared → hidden → index-before-log → tombstone ordering | recovery/control-convergence implementation; master contract §§6, 12 |
| 4 | tombstone as sole durable applied-replay authority | finalization artifact + recovery implementation; master contract §8 |
| 5 | exact replay before token-expiry rejection | recovery/public-apply implementation and I-4C2/I-4F smokes |
| 6 | forward-only post-hidden recovery | recovery implementation; master contract §§6, 12 |
| 7 | page/control/prepared/tombstone correlation | lifecycle-page, control-convergence, finalization implementation |
| 8 | corrupt/ambiguous fail-closed behavior | current-state/recovery implementation; master contract §§6, 10 |
| 9 | PR #407 loser classifications | master contract §§6, 9; public-apply/recovery implementation; I-4E mapping; concurrency smokes |
| 10 | no rollback or guessed repair | master contract §§6, 12; recovery implementation |
| 11 | current-state projection and `retrieval_eligible=false` | current-state implementation; I-4D contract and recall filtering |
| 12 | non-goals and I-4D/I-4E/I-4F split | Phase I-4 master contract and current I-4D/I-4E/I-4F documents |

## Conclusion

Every current normative behavior recorded by the old I-4C2 handoff is independently owned by the Phase I-4 master contract, current implementation, current I-4D/I-4E/I-4F boundaries, and focused executable validation. The move therefore removes no unique current authority. The canonical document is frozen historical evidence only. PR #642 merged as `a21b9ac617fcf11d85a52e919f2ecb8678485927` from reviewed head `9b92df29a2cd112c6ad80086fdcfa4ad0e6fd0d6` on integration base `32135811283edffa4408846c8a9e51173aea743e`; PR #644 consolidates those facts without changing accepted cutover content.

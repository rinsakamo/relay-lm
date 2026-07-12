---
relaylm_doc_type: documentation_index
relaylm_authority: mvp_evidence_and_completion_report_index
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - release readiness assessment changes
  - a convergence PR indexes a merged completion report
  - historical milestone placement changes
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - MVP dependency sequencing
  - exact runtime contracts
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# RelayLM MVP Evidence

This directory is the transitional index for MVP-focused implementation notes, release-readiness assessments, and per-PR implementation completion reports retained during the documentation hard cutover.

> For the current phase, implemented boundaries, default-off/preflight-only behavior, and immediate next work, use [Project Status](../PROJECT_STATUS.md). The files in this directory are historical evidence rather than the current-state source of truth, except that an explicitly current release-readiness assessment may summarize evidence without becoming runtime authority.

## Release readiness assessments

- [v0.1 Release Readiness Assessment](v0.1_release_readiness.md) — content-free readiness assessment for the validated and tagged v0.1 boundary, including local human-reviewed durable-memory E2 value-smoke evidence handling and post-v0.1 decision debt.
- [v0.1 Final Main-HEAD Validation and Tag Receipt](v0.1_final_validation_receipt.md) — frozen exact-commit validation and tag-binding evidence.

## Implementation completion reports

Declared parallel waves use unique completion reports as the handoff from each implementation PR to the later convergence/documentation thread.

Path conventions during the documentation hard cutover:

```text
legacy/unmigrated: docs/mvp/wave<N>/<slice>_completion_report.md
canonical/migrated: docs/evidence/implementation/<slice>_completion_report.md
```

Each implementation PR creates only its own report. It must not edit this central index, another slice's report, or shared current-state documents merely to mark completion. The wave convergence PR links the merged reports here after verifying the source PRs and merge commits.

### Wave 8 merged completion reports

Wave 8 currently contains operator-facing evaluation-flow conveniences, runtime-non-contact offline tooling, measurement-only infrastructure evidence, and documentation convergence reports. These reports are historical evidence for their own slices only. The MVP eval runner report does not mark O2/O3, supervised workers, polling, or always-on operation complete; the E2 harness report proves only the comparison-transcript generator and not the later human quality judgment; the Twin Extraction report does not add MEM/SOUL ingestion or RelaySLP runtime wiring; the LAT-1 report does not implement response-time guarantees, degradation ladders, timeouts, search-algorithm changes, ANN/vector DB, Secondary MEM, SSE stream timing, O2/O3 changes, or TTS/avatar timing.

- [MVP eval runner completion report](../evidence/implementation/mvp_eval_runner_completion_report.md) — source PR #451.
- [O2/O3 and PM-D5-D7 docs convergence completion report](../evidence/implementation/o2_o3_pm_d5_d7_docs_convergence_completion_report.md) — source PR #490.
- [E2 Value Smoke Harness completion report](../evidence/implementation/e2_value_smoke_harness_completion_report.md) — source PR #481; harness implementation evidence only, with human judgment remaining separate and local-only.
- [Twin Extraction Tooling completion report](../evidence/implementation/twin_extraction_completion_report.md) — source PR #503; offline runtime-non-contact preprocessing/extraction tooling only.
- [LAT-1 Latency Measurement completion report](../evidence/implementation/lat1_latency_measurement_completion_report.md) — source PR #505; measurement-only evidence, no optimization or behavior change.

### Wave 7 merged completion reports

W7-INT verifies the source PR numbers, merge commits, and dedicated handoffs for the original Wave 7 historical reports. E1-R5 was merged after W7-INT and is indexed here as a post-Wave-7 correction report:

- [E1-R3 completion report](../evidence/implementation/e1r3_completion_report.md) — source PR #436, merge `7bb2525cb000e893146408065f1aa5976f2b54ab`.
- [E1-R4 completion report](../evidence/implementation/e1r4_completion_report.md) — source PR #437, merge `e6e5b32cd489dda493ff0171a260dd561a91765c`.
- [E1-R5 completion report](../evidence/implementation/e1r5_completion_report.md) — source PR #439, post-Wave-7 correction to the E1 recall proof boundary.

The Wave 7 cross-slice convergence record is [Wave 7 Cross-Slice Convergence Audit](../evidence/waves/wave7_cross_slice_convergence_audit.md). W7-INT is merged; E1-R5 is now reflected by current shared documents and dedicated handoff links.

Wave 7 dedicated handoffs:

- [E1-R3 Provenance-Preserving Primary MEM Formation Summary](../architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md)
- [E1-R4 Retrieval-Response Grounding](../architecture/e1r4_retrieval_response_grounding.md)
- [E1-R5 Primary MEM Recall Candidate Discovery Bridge](../architecture/e1r5_primary_mem_recall_candidate_bridge.md)

### Wave 6 merged completion reports

W6-INT verifies the source PR numbers, merge commits, and dedicated handoffs for these historical reports:

- [O1F completion report](../evidence/implementation/o1f_completion_report.md) — source PR #429, merge `961fff2d935cd764e81e577887328e86363e56d5`.
- [I-5B completion report](wave6/i5b_completion_report.md) — source PR #430, merge `734a3880035651f91eb065b892fc41af6f5cc026`.
- [I-7C completion report](wave6/i7c_completion_report.md) — source PR #431, merge `21d10bfed22ed9626e4224bf927ff59a5e399505`.
- [E1-R1 completion report](wave6/e1r1_completion_report.md) — source PR #433, merge `52768cbdac3c9630373a2c369574002ac196e72b`.
- [E1-R2 completion report](wave6/e1r2_completion_report.md) — source PR #432, merge `fefd3559ac32a37ed932faa130612a6a3da43c61`.

The Wave 6 cross-slice convergence record is [Wave 6 Cross-Slice Convergence Audit](../evidence/waves/wave6_cross_slice_convergence_audit.md). W6-INT is merged.

Wave 6 dedicated handoffs:

- [O1F operational validation](../architecture/o1f_operational_validation.md)
- [Phase I-5B Pin / Unpin apply and ranking behavior](../architecture/phase_i5b_pin_unpin_apply.md)
- [Phase I-7C Held Apply / Discard runtime governance](../architecture/phase_i7c_held_apply_discard_runtime.md)
- [E1-R1 trusted Home scene admission](../architecture/e1r1_trusted_home_scene_admission.md)
- [E1-R2 character-store bootstrap command](../architecture/e1r2_character_store_bootstrap.md)

### Wave 5 merged completion reports

W5-INT verifies the source PR numbers, merge commits, and dedicated handoffs for these historical reports:

- [E1 completion report](wave5/e1_completion_report.md) — source PR #425, merge `95c159ff747a167cd6cf99c7c5df656fd01e345d`.
- [O1E completion report](wave5/o1e_completion_report.md) — source PR #426, merge `49750ccb693ab6ebca1f5a0947c69c06a4a03d31`.
- [I-4F completion report](wave5/i4f_completion_report.md) — source PR #427, merge `937718dcb328fda5e3e37bb951b39fc66629f57a`.

The Wave 5 cross-slice convergence record is [Wave 5 Cross-Slice Convergence Audit](../evidence/waves/wave5_cross_slice_convergence_audit.md). W5-INT is merged.

### Wave 4 merged completion reports

W4-INT verified the source PR numbers, merge commits, and dedicated handoffs for these historical reports:

- [O1D2 completion report](wave4/o1d2_completion_report.md) — source PR #418, merge `49fb43130155826fcc8b2b951d77484ff8ddaddf`.
- [I-4E completion report](wave4/i4e_completion_report.md) — source PR #420, merge `3e3d2570ecdfcde4c8bfdee06c5607cb6632c133`.
- [UI-B1A completion report](wave4/ui_b1a_completion_report.md) — source PR #421, merge `5736636da839486140f72c731f18a4a85c39b13c`.
- [I-5A completion report](wave4/i5a_completion_report.md) — source PR #417, merge `2f8597911774b70f1c001db8332b3dfcc18d23ca`.
- [I-7A/B completion report](wave4/i7ab_completion_report.md) — source PR #423, merge `5e0f866e959ab2bc5af00e0502b2026f4b52a779`.

The Wave 4 cross-slice convergence record is [Wave 4 Cross-Slice Convergence Audit](../evidence/waves/wave4_cross_slice_convergence_audit.md). W4-INT is merged.

### Wave 3 merged completion reports

- [I1-GE completion report](wave3/i1ge_completion_report.md) — source PR #411, merge `e2caa1bdb53468ca282e8f374ba8ceebf839c976`.
- [I-4D completion report](wave3/i4d_completion_report.md) — source PR #414, merge `48e890f05f76196b73267559b079f4a05c441077`.
- [O1D1 completion report](wave3/o1d1_completion_report.md) — source PR #412, merge `9b6349236f1a01f3cdccbe9e3c2c874ae1137475`.

The cross-slice convergence record is [Wave 3 Cross-Slice Convergence Audit](../evidence/waves/wave3_cross_slice_convergence_audit.md). W3-INT is merged.

A completion report is evidence for one PR only. It is not authoritative for repository-wide current status, other slice completion, next-wave readiness, or release/evaluation readiness. Use [the template](IMPLEMENTATION_COMPLETION_REPORT_TEMPLATE.md) and validate reports with:

```bash
python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/o1f_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/i5b_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/i7c_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/e1r1_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/e1r2_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/e1r3_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/e1r4_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/e1r5_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/mvp_eval_runner_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/o2_o3_pm_d5_d7_docs_convergence_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/e2_value_smoke_harness_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/twin_extraction_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/lat1_latency_measurement_completion_report.md
```

The source PR number must be concrete before final review. The convergence thread records the merge commit from GitHub; the report does not need a self-referential head SHA.

## Retained focused historical notes

- [MVP-0: pass-through proxy](mvp0_pass_through_proxy.md)
- [MVP-1 runtime diagnostics](mvp1_runtime_diagnostics_smoke.md)
- [MVP-2 profile loading](mvp2_profile_file_loading.md)
- [MVP-40 extraction](mvp40_relayctx_short_term_extraction_dry_run.md)
- [MVP-41 assembly](mvp41_relayctx_short_term_block_assembly_dry_run.md)
- [MVP-42 injection preflight](mvp42_relayctx_short_term_runtime_injection_preflight.md)
- [MVP-43 apply gate](mvp43_relayctx_short_term_runtime_injection_apply_gate.md)
- [MVP-45 fast path](mvp45_relayint_fast_path_dry_run.md)
- [MVP-46 clarification preflight](mvp46_relayint_quick_clarification_preflight.md)
- [MVP-47 clarification apply plan](mvp47_relayint_quick_clarification_apply_plan.md)
- [MVP-48 node result scaffold](mvp48_pipeline_node_result_scaffold.md)

The redundant MVP-1 through MVP-33 and MVP-37 milestone summary snapshots were removed from the active tree in Cutover 1B. Their old paths and blob digests are recorded in [the deletion appendix](../evidence/migrations/cutover-1b-mvp-snapshot-deletions.tsv), and their contents remain recoverable from Git history and the frozen `v0.1` tag.

## Maintenance rule

- Do not add new generic milestone summary snapshots under `docs/mvp/`.
- A parallel implementation PR creates one uniquely named completion report and does not update this index.
- The wave convergence PR adds links to the merged reports and updates shared current-state documents.
- Treat existing MVP documents and completion reports as historical evidence; change them only to repair broken links, perform an authorized cutover move, or make an explicit factual correction.
- Use [Project Status](../PROJECT_STATUS.md) for repository-wide current implementation state and immediate next boundaries.

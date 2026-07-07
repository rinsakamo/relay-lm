# RelayLM MVP Summaries

This directory is the index for RelayLM MVP milestone summaries, MVP-focused implementation notes, and per-PR implementation completion reports.

> For the current phase, implemented boundaries, default-off/preflight-only behavior, and immediate next work, use [Project Status](../PROJECT_STATUS.md). The files in this directory are historical evidence rather than the current-state source of truth.

## Implementation completion reports

Declared parallel waves use unique completion reports as the handoff from each implementation PR to the later convergence/documentation thread.

Path convention:

```text
docs/mvp/wave<N>/<slice>_completion_report.md
```

Each implementation PR creates only its own report. It must not edit this central index, another slice's report, or shared current-state documents merely to mark completion. The wave convergence PR links the merged reports here after verifying the source PRs and merge commits.

### Wave 8 merged completion reports

Wave 8 currently contains operator-facing evaluation-flow conveniences, runtime-non-contact offline tooling, measurement-only infrastructure evidence, and documentation convergence reports. These reports are historical evidence for their own slices only. The MVP eval runner report does not mark O2/O3, supervised workers, polling, or always-on operation complete; the Twin Extraction report does not add MEM/SOUL ingestion or RelaySLP runtime wiring; the LAT-1 report does not implement response-time guarantees, degradation ladders, timeouts, search-algorithm changes, ANN/vector DB, Secondary MEM, SSE stream timing, O2/O3 changes, or TTS/avatar timing.

- [MVP eval runner completion report](wave8/mvp_eval_runner_completion_report.md) — source PR #451.
- [O2/O3 and PM-D5-D7 docs convergence completion report](wave8/o2_o3_pm_d5_d7_docs_convergence_completion_report.md) — source PR #490.
- [Twin Extraction Tooling completion report](wave8/twin_extraction_completion_report.md) — source PR #503; offline runtime-non-contact preprocessing/extraction tooling only.
- [LAT-1 Latency Measurement completion report](wave8/lat1_latency_measurement_completion_report.md) — source PR #505; measurement-only evidence, no optimization or behavior change.

### Wave 7 merged completion reports

W7-INT verifies the source PR numbers, merge commits, and dedicated handoffs for the original Wave 7 historical reports. E1-R5 was merged after W7-INT and is indexed here as a post-Wave-7 correction report:

- [E1-R3 completion report](wave7/e1r3_completion_report.md) — source PR #436, merge `7bb2525cb000e893146408065f1aa5976f2b54ab`.
- [E1-R4 completion report](wave7/e1r4_completion_report.md) — source PR #437, merge `e6e5b32cd489dda493ff0171a260dd561a91765c`.
- [E1-R5 completion report](wave7/e1r5_completion_report.md) — source PR #439, post-Wave-7 correction to the E1 recall proof boundary.

The Wave 7 cross-slice convergence record is [Wave 7 Cross-Slice Convergence Audit](../architecture/wave7_cross_slice_convergence_audit.md). W7-INT is merged; E1-R5 is now reflected by current shared documents and dedicated handoff links.

Wave 7 dedicated handoffs:

- [E1-R3 Provenance-Preserving Primary MEM Formation Summary](../architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md)
- [E1-R4 Retrieval-Response Grounding](../architecture/e1r4_retrieval_response_grounding.md)
- [E1-R5 Primary MEM Recall Candidate Discovery Bridge](../architecture/e1r5_primary_mem_recall_candidate_bridge.md)

### Wave 6 merged completion reports

W6-INT verifies the source PR numbers, merge commits, and dedicated handoffs for these historical reports:

- [O1F completion report](wave6/o1f_completion_report.md) — source PR #429, merge `961fff2d935cd764e81e577887328e86363e56d5`.
- [I-5B completion report](wave6/i5b_completion_report.md) — source PR #430, merge `734a3880035651f91eb065b892fc41af6f5cc026`.
- [I-7C completion report](wave6/i7c_completion_report.md) — source PR #431, merge `21d10bfed22ed9626e4224bf927ff59a5e399505`.
- [E1-R1 completion report](wave6/e1r1_completion_report.md) — source PR #433, merge `52768cbdac3c9630373a2c369574002ac196e72b`.
- [E1-R2 completion report](wave6/e1r2_completion_report.md) — source PR #432, merge `fefd3559ac32a37ed932faa130612a6a3da43c61`.

The Wave 6 cross-slice convergence record is [Wave 6 Cross-Slice Convergence Audit](../architecture/wave6_cross_slice_convergence_audit.md). W6-INT is merged.

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

The Wave 5 cross-slice convergence record is [Wave 5 Cross-Slice Convergence Audit](../architecture/wave5_cross_slice_convergence_audit.md). W5-INT is merged.

### Wave 4 merged completion reports

W4-INT verified the source PR numbers, merge commits, and dedicated handoffs for these historical reports:

- [O1D2 completion report](wave4/o1d2_completion_report.md) — source PR #418, merge `49fb43130155826fcc8b2b951d77484ff8ddaddf`.
- [I-4E completion report](wave4/i4e_completion_report.md) — source PR #420, merge `3e3d2570ecdfcde4c8bfdee06c5607cb6632c133`.
- [UI-B1A completion report](wave4/ui_b1a_completion_report.md) — source PR #421, merge `5736636da839486140f72c731f18a4a85c39b13c`.
- [I-5A completion report](wave4/i5a_completion_report.md) — source PR #417, merge `2f8597911774b70f1c001db8332b3dfcc18d23ca`.
- [I-7A/B completion report](wave4/i7ab_completion_report.md) — source PR #423, merge `5e0f866e959ab2bc5af00e0502b2026f4b52a779`.

The Wave 4 cross-slice convergence record is [Wave 4 Cross-Slice Convergence Audit](../architecture/wave4_cross_slice_convergence_audit.md). W4-INT is merged.

### Wave 3 merged completion reports

- [I1-GE completion report](wave3/i1ge_completion_report.md) — source PR #411, merge `e2caa1bdb53468ca282e8f374ba8ceebf839c976`.
- [I-4D completion report](wave3/i4d_completion_report.md) — source PR #414, merge `48e890f05f76196b73267559b079f4a05c441077`.
- [O1D1 completion report](wave3/o1d1_completion_report.md) — source PR #412, merge `9b6349236f1a01f3cdccbe9e3c2c874ae1137475`.

The cross-slice convergence record is [Wave 3 Cross-Slice Convergence Audit](../architecture/wave3_cross_slice_convergence_audit.md). W3-INT is merged.

A completion report is evidence for one PR only. It is not authoritative for repository-wide current status, other slice completion, next-wave readiness, or release/evaluation readiness. Use [the template](IMPLEMENTATION_COMPLETION_REPORT_TEMPLATE.md) and validate reports with:

```bash
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/o1f_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/i5b_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/i7c_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/e1r1_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/e1r2_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave7/e1r3_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave7/e1r4_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave7/e1r5_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave8/mvp_eval_runner_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave8/o2_o3_pm_d5_d7_docs_convergence_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave8/twin_extraction_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave8/lat1_latency_measurement_completion_report.md
```

The source PR number must be concrete before final review. The convergence thread records the merge commit from GitHub; the report does not need a self-referential head SHA.

## Earlier milestone summaries

These older summaries are kept indexed for discoverability while the documentation tree is being reorganized. They are historical snapshots, not current-state authority.

- [MVP-0: pass-through proxy](mvp0_pass_through_proxy.md)
- [MVP-1 summary](mvp1_summary.md)
- [MVP-2 summary](mvp2_summary.md)
- [MVP-3 summary](mvp3_summary.md)
- [MVP-4 summary](mvp4_summary.md)
- [MVP-5 summary](mvp5_summary.md)
- [MVP-6 summary](mvp6_summary.md)
- [MVP-7 summary](mvp7_summary.md)
- [MVP-8 summary](mvp8_summary.md)
- [MVP-9 summary](mvp9_summary.md)
- [MVP-10 summary](mvp10_summary.md)
- [MVP-11 summary](mvp11_summary.md)
- [MVP-12 summary](mvp12_summary.md)
- [MVP-13 summary](mvp13_summary.md)
- [MVP-14 summary](mvp14_summary.md)
- [MVP-15 summary](mvp15_summary.md)
- [MVP-16 summary](mvp16_summary.md)
- [MVP-17 summary](mvp17_summary.md)
- [MVP-18 summary](mvp18_summary.md)
- [MVP-19 summary](mvp19_summary.md)
- [MVP-20 summary](mvp20_summary.md)
- [MVP-21 summary](mvp21_summary.md)
- [MVP-22 summary](mvp22_summary.md)
- [MVP-23 summary](mvp23_summary.md)
- [MVP-24 summary](mvp24_summary.md)
- [MVP-25 summary](mvp25_summary.md)
- [MVP-26 summary](mvp26_summary.md)
- [MVP-27 summary](mvp27_summary.md)
- [MVP-28 summary](mvp28_summary.md)
- [MVP-29 summary](mvp29_summary.md)
- [MVP-30 summary](mvp30_summary.md)
- [MVP-31 summary](mvp31_summary.md)
- [MVP-32 summary](mvp32_summary.md)
- [MVP-33 summary](mvp33_summary.md)
- [MVP-37 summary](mvp37_summary.md)

Focused historical notes: [MVP-1 runtime diagnostics](mvp1_runtime_diagnostics_smoke.md), [MVP-2 profile loading](mvp2_profile_file_loading.md), [MVP-40 extraction](mvp40_relayctx_short_term_extraction_dry_run.md), [MVP-41 assembly](mvp41_relayctx_short_term_block_assembly_dry_run.md), [MVP-42 injection preflight](mvp42_relayctx_short_term_runtime_injection_preflight.md), [MVP-43 apply gate](mvp43_relayctx_short_term_runtime_injection_apply_gate.md), [MVP-45 fast path](mvp45_relayint_fast_path_dry_run.md), [MVP-46 clarification preflight](mvp46_relayint_quick_clarification_preflight.md), [MVP-47 clarification apply plan](mvp47_relayint_quick_clarification_apply_plan.md), and [MVP-48 node result scaffold](mvp48_pipeline_node_result_scaffold.md).

## Maintenance rule

- Create historical MVP summaries and focused implementation notes directly under `docs/mvp/` unless a declared parallel wave uses a `docs/mvp/wave<N>/` completion-report directory.
- A parallel implementation PR creates one uniquely named completion report and does not update this index.
- The wave convergence PR adds links to the merged reports and updates shared current-state documents.
- Treat existing MVP documents and completion reports as historical snapshots; change them only to repair broken links or make an explicit factual correction.
- Use [Project Status](../PROJECT_STATUS.md) for repository-wide current implementation state and immediate next boundaries.

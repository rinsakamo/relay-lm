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

### Wave 6 completion reports

- [O1F completion report](wave6/o1f_completion_report.md) — source PR #429, merge `961fff2d935cd764e81e577887328e86363e56d5`.

The O1F report is evidence for validation-only operational hardening over the existing caller-invoked O1E/O1D2/O1D1 stack. It does not implement O2 supervision, O3 always-on operation, polling, sleep, daemon behavior, service supervision, worker pools, or Primary MEM mutation.

### Wave 5 merged completion reports

W5-INT verifies the source PR numbers, merge commits, and dedicated handoffs for these historical reports:

- [E1 completion report](wave5/e1_completion_report.md) — source PR #425, merge `95c159ff747a167cd6cf99c7c5df656fd01e345d`.
- [O1E completion report](wave5/o1e_completion_report.md) — source PR #426, merge `49750ccb693ab6ebca1f5a0947c69c06a4a03d31`.
- [I-4F completion report](wave5/i4f_completion_report.md) — source PR #427, merge `937718dcb328fda5e3e37bb951b39fc66629f57a`.

The Wave 5 cross-slice convergence record is [Wave 5 Cross-Slice Convergence Audit](../architecture/wave5_cross_slice_convergence_audit.md). W5-INT is merged.

Wave 5 dedicated handoffs:

- [E1 MVP evaluation consolidation](../architecture/e1_evaluation_consolidation.md).
- [O1E scheduler operational controls](../architecture/o1e_scheduler_operational_controls.md).
- [Phase I-4F Forget product validation](../architecture/phase_i4f_forget_validation.md).
- [E1 local runtime evaluation](../architecture/e1_local_runtime_evaluation_2026_06_25.md).

### Wave 4 merged completion reports

W4-INT verified the source PR numbers, merge commits, and dedicated handoffs for these historical reports:

- [O1D2 completion report](wave4/o1d2_completion_report.md) — source PR #418, merge `49fb43130155826fcc8b2b951d77484ff8ddaddf`.
- [I-4E completion report](wave4/i4e_completion_report.md) — source PR #420, merge `3e3d2570ecdfcde4c8bfdee06c5607cb6632c133`.
- [UI-B1A completion report](wave4/ui_b1a_completion_report.md) — source PR #421, merge `5736636da839486140f72c731f18a4a85c39b13c`.
- [I-5A completion report](wave4/i5a_completion_report.md) — source PR #417, merge `2f8597911774b70f1c001db8332b3dfcc18d23ca`.
- [I-7A/B completion report](wave4/i7ab_completion_report.md) — source PR #423, merge `5e0f866e959ab2bc5af00e0502b2026f4b52a779`.

The Wave 4 cross-slice convergence record is [Wave 4 Cross-Slice Convergence Audit](../architecture/wave4_cross_slice_convergence_audit.md). W4-INT is merged.

Wave 4 dedicated handoffs:

- [O1D2 deterministic scheduler policy](../architecture/o1d2_scheduler_policy.md)
- [Phase I-4E Forget API and SOUL Lab UI](../architecture/phase_i4e_forget_api_ui.md)
- [SOUL Lab UI-B1A lifecycle visibility](../architecture/soul_lab_ui_b1a_lifecycle_visibility.md)
- [Phase I-5A Pin / Unpin contract and read-only preflight](../architecture/phase_i5_pin_unpin_contract.md)
- [Phase I-7A/B Held Apply / Discard contract and read-only preflight](../architecture/phase_i7ab_held_apply_discard_contract.md)

### Wave 3 merged completion reports

W3-INT verified the source PR numbers, merge commits, final heads, changed-file inventories, and dedicated handoffs for these historical reports:

- [I1-GE completion report](wave3/i1ge_completion_report.md) — source PR #411, merge `e2caa1bdb53468ca282e8f374ba8ceebf839c976`.
- [I-4D completion report](wave3/i4d_completion_report.md) — source PR #414, merge `48e890f05f76196b73267559b079f4a05c441077`.
- [O1D1 completion report](wave3/o1d1_completion_report.md) — source PR #412, merge `9b6349236f1a01f3cdccbe9e3c2c874ae1137475`.

The cross-slice convergence record is [Wave 3 Cross-Slice Convergence Audit](../architecture/wave3_cross_slice_convergence_audit.md). W3-INT is merged.

A completion report is evidence for one PR only. It is not authoritative for repository-wide current status, other slice completion, next-wave readiness, or release/evaluation readiness. Use [the template](IMPLEMENTATION_COMPLETION_REPORT_TEMPLATE.md) and validate the report with:

```bash
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave6/o1f_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave5/e1_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave5/o1e_completion_report.md
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave5/i4f_completion_report.md
```

The source PR number must be concrete before final review. The convergence thread records the merge commit from GitHub; the report does not need a self-referential head SHA.

## Current pipeline milestones

### RelayCTX short-term context

- [MVP-40: RelayCTX short-term extraction dry-run](mvp40_relayctx_short_term_extraction_dry_run.md)
- [MVP-41: RelayCTX short-term block assembly dry-run](mvp41_relayctx_short_term_block_assembly_dry_run.md)
- [MVP-42: RelayCTX short-term runtime injection preflight](mvp42_relayctx_short_term_runtime_injection_preflight.md)
- [MVP-43: RelayCTX short-term runtime injection apply gate](mvp43_relayctx_short_term_runtime_injection_apply_gate.md)

### RelayINT

- [MVP-45: RelayINT Fast Path dry-run](mvp45_relayint_fast_path_dry_run.md)
- [MVP-46: RelayINT quick clarification preflight](mvp46_relayint_quick_clarification_preflight.md)
- [MVP-47: RelayINT quick clarification apply plan](mvp47_relayint_quick_clarification_apply_plan.md)

### Pipeline node result scaffold

- [MVP-48: Pipeline node result scaffold](mvp48_pipeline_node_result_scaffold.md)

## MVP-0 and MVP-1

- [MVP-0: pass-through proxy](mvp0_pass_through_proxy.md)
- [MVP-1: config and routing smoke](mvp1_config_routing_smoke.md)
- [MVP-1: runtime diagnostics smoke](mvp1_runtime_diagnostics_smoke.md)
- [MVP-1: API diagnostics smoke](mvp1_api_diagnostics_smoke.md)
- [MVP-1 summary](mvp1_summary.md)

## MVP-2 focused notes

MVP-2 has several focused notes rather than only one summary file:

- [MVP-2: context compiler contract](mvp2_context_compiler_contract.md)
- [MVP-2: profile file loading](mvp2_profile_file_loading.md)
- [MVP-2: config profile resolution](mvp2_config_profile_resolution.md)
- [MVP-2: compiled system message](mvp2_compiled_system_message.md)
- [MVP-2: incoming system fallback](mvp2_incoming_system_fallback.md)
- [MVP-2: profile compile dry-run](mvp2_profile_compile_dry_run.md)
- [MVP-2: dry-run diagnostics headers](mvp2_dry_run_diagnostics_headers.md)
- [MVP-2: gated compile decision](mvp2_gated_compile_decision.md)
- [MVP-2: memory-light apply helper](mvp2_memory_light_apply.md)
- [MVP-2: runtime memory-light apply](mvp2_runtime_memory_light_apply.md)
- [MVP-2: memory-light API smoke](mvp2_memory_light_api_smoke.md)
- [MVP-2 summary](mvp2_summary.md)

## Earlier milestone summaries

These older summaries are kept indexed for discoverability while the documentation tree is being reorganized.

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
- [MVP-37 summary](mvp37_summary.md)

## Maintenance rule

- Create historical MVP summaries and focused implementation notes directly under `docs/mvp/` unless a declared parallel wave uses a `docs/mvp/wave<N>/` completion-report directory.
- A parallel implementation PR creates one uniquely named completion report and does not update this index.
- The wave convergence PR adds links to the merged reports and updates shared current-state documents.
- Treat existing MVP documents and completion reports as historical snapshots; change them only to repair broken links or make an explicit factual correction.
- Use [Project Status](../PROJECT_STATUS.md) for repository-wide current implementation state and immediate next boundaries.

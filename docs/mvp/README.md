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

### E1-R3 completion report

- [E1-R3 completion report](wave7/e1r3_completion_report.md) — source PR TBD by this PR before merge.

The E1-R3 architecture handoff is [E1-R3 Provenance-Preserving Primary MEM Formation Summary](../architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md).

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
```

The source PR number must be concrete before final review. The convergence thread records the merge commit from GitHub; the report does not need a self-referential head SHA.

## Earlier milestone summaries

These older summaries are kept indexed for discoverability while the documentation tree is being reorganized.

- [MVP-0: pass-through proxy](mvp0_pass_through_proxy.md)
- [MVP-1 summary](mvp1_summary.md)
- [MVP-2 summary](mvp2_summary.md)
- [MVP-3 summary](mvp3_summary.md)
- [MVP-4 summary](mvp4_summary.md)
- [MVP-5 summary](mvp5_summary.md)

## Maintenance rule

- Create historical MVP summaries and focused implementation notes directly under `docs/mvp/` unless a declared parallel wave uses a `docs/mvp/wave<N>/` completion-report directory.
- A parallel implementation PR creates one uniquely named completion report and does not update this index.
- The wave convergence PR adds links to the merged reports and updates shared current-state documents.
- Treat existing MVP documents and completion reports as historical snapshots; change them only to repair broken links or make an explicit factual correction.
- Use [Project Status](../PROJECT_STATUS.md) for repository-wide current implementation state and immediate next boundaries.

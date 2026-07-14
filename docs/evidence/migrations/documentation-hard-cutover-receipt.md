---
relaylm_doc_type: evidence
relaylm_authority: documentation_hard_cutover_migration_ledger
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - a documentation cutover PR moves, splits, synthesizes, absorbs, rebuilds, retains, or deletes a source
  - the cutover completes and this ledger is frozen
relaylm_not_authoritative_for:
  - current runtime behavior
  - exact contract wording
  - current documentation placement outside recorded merged entries
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source: ../../adr/0002-documentation-information-architecture.md
relaylm_cutover_baseline_tag: v0.1
relaylm_cutover_baseline_commit: 522018e62d69bcbe89465d574bf2d1b377f10bd9
relaylm_cutover_gate_commit: 1397a65c8e5f049b6e498f6db70a1a7da32ab151
---
# Documentation Hard-Cutover Migration Receipt

This append-only ledger records the authority-first documentation hard cutover authorized by ADR 0002. Old paths appear only as migration identifiers and do not create redirects, compatibility paths, or live authority.

## Cutover identity

```text
baseline tag: v0.1
baseline commit: 522018e62d69bcbe89465d574bf2d1b377f10bd9
tag binding: exact match
cutover gate record: 1397a65c8e5f049b6e498f6db70a1a7da32ab151
cutover state: active
```

## Verification rules

- `moved`: source authority has one new live canonical path and the old path is absent.
- `evidence_retained`: non-normative evidence remains under `docs/evidence/`.
- `rebuilt_verbatim`: normative blocks have equal normalized SHA-256 before and after migration.
- `split`: every source section has an explicit destination or deletion classification.
- `synthesized`: multiple source authorities are accounted for in a new stable document.
- `absorbed`: still-valid content is incorporated into another canonical authority.
- `retained`: path and authority remain canonical.
- `deleted_git_history_only`: the active-tree path is removed and the source remains recoverable from Git history.

## Entries

### C1A-001 — accepted documentation restructure proposal

```yaml
cutover_pr: 555
merged_commit: 3fd9b6dd833c869f50620355ffa698c41f496f10
old_path: docs/proposals/documentation_restructure_proposal.md
old_blob_sha: 4707ee9cd6d0a8184f36782cdd537e6a71a10131
old_content_sha256: 7c9d7fbc3b5a080ab601d9fcc67f95bdfdc712d9836d569de3b40a19c493ef91
source_commit: 5f9730d1e2630a30b6ade2faa03da580f1dccd38
source_pr: 549
disposition: moved
new_canonical_path: docs/evidence/proposals/documentation-restructure-proposal.md
exact_source_snapshot: docs/evidence/proposals/documentation-restructure-proposal-source.txt
exact_source_blob_sha: 4707ee9cd6d0a8184f36782cdd537e6a71a10131
verification:
  old_path_removed: true
  source_blob_reused_exactly: true
  canonical_evidence_metadata_added: true
  live_navigation_links_updated: true
  baseline_inventory_literals_retained_as_migration_inputs: true
```

The exact source snapshot intentionally retains its original pre-adoption metadata as immutable source text. The canonical Markdown evidence record carries the post-decision authority and lifecycle metadata.

### C1B-001 — low-value MVP milestone snapshots

```yaml
cutover_pr: 556
merged_commit: 982d119a6a05b66bf30418a156e6bceec79c7367
disposition: deleted_git_history_only
record_count: 34
record_file: docs/evidence/migrations/cutover-1b-mvp-snapshot-deletions.tsv
selection_rule: docs/mvp/mvp[0-9]+_summary.md classified as redundant milestone snapshots
preparation_c_literal_docs_path_dependency_count_per_record: 0
relative_link_dependency:
  source: docs/mvp/README.md
  link_count: 34
  resolution: removed_in_same_pr
verification:
  every_old_path_listed: true
  every_old_blob_sha_listed: true
  every_old_content_sha256_listed: true
  source_commit_and_source_pr_recorded_when_available: true
  all_paths_removed: true
  relative_index_links_removed: true
  documentation_link_check: passed
  recoverable_from_git_history: true
```

The TSV appendix is the file-level receipt for this batch. It is intentionally non-Markdown so embedded pre-cutover paths and metadata cannot be mistaken for active documentation authority. The Preparation C literal-path scan did not cover relative Markdown links; PR #556 corrected the MVP index and recorded that limitation explicitly.

### C1C1-001 — Phase I-3 validation receipt

```yaml
cutover_pr: 557
merged_commit: c1e41951d83a6a296e86d49e585cd8314257d8c4
old_path: docs/architecture/phase_i3_validation_receipt.md
old_blob_sha: 710bf4dfb98e1b824751dc071fd206b7c4b9afda
old_content_sha256: 8f5bd9b650a78838a93ee870dbbec99c112ba3ab55d27ceafda2767544139036
source_commit: 74b308f341cb049e6adebbe2b0c959950198739a
source_pr: 379
disposition: evidence_retained
new_canonical_path: docs/evidence/evaluations/phase_i3_validation_receipt.md
verification:
  old_path_removed: true
  current_filename_search_dependencies: 0
  canonical_evidence_metadata_added: true
  validation_conclusion_changed: false
  documentation_link_check: passed
```

This move changed placement and lifecycle metadata only. The recorded Phase I-3 verification results and privacy statement remained substantively unchanged.

### C1C2-001 — early MVP smoke sources

```yaml
cutover_pr: 558
merged_commit: b81f882fd2d015adbbb0a3987cdbcc12c4173d59
disposition: evidence_retained
record_count: 4
record_file: docs/evidence/migrations/cutover-1c2-early-mvp-smokes.tsv
verification:
  old_paths_removed: true
  preparation_c_literal_path_dependencies_per_record: 0
  current_filename_search_dependencies_per_record: 0
  exact_source_blobs_reused: true
  canonical_evidence_wrappers_added: true
  historical_commands_marked_non_current: true
  documentation_link_check: passed
```

Each source is retained byte-for-byte as a `.txt` snapshot. The canonical Markdown wrapper carries authority, lifecycle, and provenance metadata without presenting the historical commands as current operator guidance.

### C1C3-001 — early MVP-2 compile and diagnostics sources

```yaml
cutover_pr: 559
merged_commit: b03022812cc9ea2b7a439698df92287f7c10a1b4
disposition: evidence_retained
record_count: 3
record_file: docs/evidence/migrations/cutover-1c3-mvp2-compile-smokes.tsv
verification:
  old_paths_removed: true
  preparation_c_literal_path_dependencies_per_record: 0
  current_filename_search_dependencies_per_record: 0
  exact_source_blobs_reused: true
  canonical_evidence_wrappers_added: true
  historical_behavior_marked_non_current: true
  mixed_authority_incoming_system_fallback_excluded: true
  documentation_link_check: passed
```

The three source snapshots are byte-for-byte copies of the original blobs. `mvp2_incoming_system_fallback.md` remains outside this batch because it mixes historical implementation detail with current authority interpretation and requires an explicit split or absorption decision.

### C1C4-001 — Wave 2 cross-slice convergence audit

```yaml
cutover_pr: 561
merged_commit: 4ccb063e453398133d8166cc3e0cbaca1e8e3e38
old_path: docs/architecture/wave2_cross_slice_convergence_audit.md
old_blob_sha: 8a601773aef9619ff19a6e750736783a2c9415bc
old_content_sha256: bca9d9a44216d761e28f52e46ea3ddffd7cc264986a050fdb8ab5bc81205c67f
source_commit: 8f49544560472b1e0d68cea8406b4d971f7d93db
source_pr: 408
disposition: evidence_retained
new_canonical_path: docs/evidence/waves/wave2_cross_slice_convergence_audit.md
exact_source_snapshot: docs/evidence/waves/wave2_cross_slice_convergence_audit-source.txt
exact_source_blob_sha: 8a601773aef9619ff19a6e750736783a2c9415bc
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_path_references_updated_in_pr_tree: 2
  additional_filename_reference_updated_in_pr_tree: 1
  relative_markdown_link_dependencies_at_frozen_baseline: 0
  documentation_link_check: passed
  affected_smoke: passed
```

The canonical evidence document preserves the complete Wave 2 convergence account while correcting relative links for its new collection. The exact pre-cutover source remains available as the original Git blob. O1D1, I-4C2, and the Wave 5 convergence smoke now refer to the canonical evidence path.

### C1C5-001 — Wave 3 cross-slice convergence audit

```yaml
cutover_pr: 562
merged_commit: 4dc151989f0a918f51e2036c1ee55c8f438f811c
old_path: docs/architecture/wave3_cross_slice_convergence_audit.md
old_blob_sha: dc821cd28b045a65ed98b9ee24dfae31278a6289
old_content_sha256: b52479de59f60dfff4edacca25655e8c8212d423391ac825d98897ac252c3c2a
source_commit: 394ea1628f2262625c460c60d6b218ccc90429ac
source_pr: 415
disposition: evidence_retained
new_canonical_path: docs/evidence/waves/wave3_cross_slice_convergence_audit.md
exact_source_snapshot: docs/evidence/waves/wave3_cross_slice_convergence_audit-source.txt
exact_source_blob_sha: dc821cd28b045a65ed98b9ee24dfae31278a6289
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_path_references_updated_in_pr_tree: 7
  relative_markdown_link_dependencies_at_frozen_baseline: 3
  additional_current_tree_related_authority_references_updated: 8
  wave3_functional_smoke_updated: true
  wave3_security_smoke_updated: true
  wave5_regression_smoke_updated: true
  documentation_link_check: passed
  affected_current_boundary_checks: passed
```

The canonical evidence document preserves the complete Wave 3 convergence account while correcting relative links for its new collection. The exact pre-cutover source remains available as the original Git blob. The frozen dependency inventory identified six repository-root path literals (seven occurrences) and three relative-link referrers; the current-tree sweep found eight additional `relaylm_related_authority` YAML references not present at the frozen baseline, all updated in this PR. The Wave 4 convergence audit is unchanged except for the single stale related-authority reference this move requires.

### C1C6-001 — Wave 4 cross-slice convergence audit

```yaml
cutover_pr: 563
merged_commit: bbcad5447fec07fbd124f126a6cdd25f18656dc2
old_path: docs/architecture/wave4_cross_slice_convergence_audit.md
old_blob_sha: c6273fbe7e7809df510a22f04d30d43e25698b73
old_content_sha256: be9842738ce45abbd134547479f17f057ba16791f0216e98e583cf9c72022b56
source_commit: f920d3683f5f6666024dadd5e29b9d4ff8440dec
source_pr: 424
recorded_on: 2026-06-27
disposition: evidence_retained
new_canonical_path: docs/evidence/waves/wave4_cross_slice_convergence_audit.md
exact_source_snapshot: docs/evidence/waves/wave4_cross_slice_convergence_audit-source.txt
exact_source_blob_sha: c6273fbe7e7809df510a22f04d30d43e25698b73
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 1
  script_hard_coded_path_reference_files_updated_in_pr_tree: 2
  script_hard_coded_path_reference_occurrences_updated_in_pr_tree: 4
  relative_markdown_link_referrer_files_at_frozen_baseline: 3
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  current_tree_related_authority_references_updated: 1
  wave4_functional_smoke_updated: true
  wave5_regression_smoke_updated: true
  documentation_link_check: passed
  documentation_semantic_audit: passed
  affected_current_boundary_checks: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical evidence document preserves the complete Wave 4 convergence account while correcting relative links for its new collection. The exact pre-cutover source remains available as the original Git blob. The frozen and current-tree sweeps identified one repository-root literal in a later completion record, four hard-coded script occurrences across two smoke files, four Markdown relative links across three referrer files, and one `relaylm_related_authority` YAML reference. These dependency classes remain separately recorded; the old path below is only the historical migration identifier for this receipt.

### C1C7-001 — Wave 5 cross-slice convergence audit

```yaml
cutover_pr: 564
merged_commit: 8cf7caca3891b29cf3439dde8fb23e81a365a254
stacked_on_pr: 563
stack_dependency_resolved_by_merge_commit: bbcad5447fec07fbd124f126a6cdd25f18656dc2
old_path: docs/architecture/wave5_cross_slice_convergence_audit.md
old_blob_sha: 69b05a5f8380dd26be4dd51f57620278bf57ca76
old_content_sha256: b3935dc5a49da95a594897969c1b3430fd2e931f1dd4f909705afdbe29b36036
source_commit: a832b1c7537b778b79f95d694a263a8e0d3b4e78
source_pr: 428
recorded_on: 2026-06-27
disposition: evidence_retained
new_canonical_path: docs/evidence/waves/wave5_cross_slice_convergence_audit.md
exact_source_snapshot: docs/evidence/waves/wave5_cross_slice_convergence_audit-source.txt
exact_source_blob_sha: 69b05a5f8380dd26be4dd51f57620278bf57ca76
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 1
  script_hard_coded_path_reference_files_updated_in_pr_tree: 1
  script_hard_coded_path_reference_occurrences_updated_in_pr_tree: 1
  relative_markdown_link_referrer_files_at_frozen_baseline: 3
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  current_tree_related_authority_references_updated: 1
  wave5_functional_smoke_updated: true
  downstream_wave6_status_record_updated: true
  documentation_link_check: passed
  documentation_semantic_audit: passed
  affected_current_boundary_checks: passed
  inventory_tools_run: true
  current_tree_rg_classification: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical evidence document preserves the complete Wave 5 convergence account while correcting its two live relative links for the evidence collection. The exact pre-cutover source remains available as the original Git blob. The dependency sweep identified one repository-root literal in a later Wave 6 completion record, one hard-coded Wave 5 smoke path, four Markdown relative links across three router files, and one `relaylm_related_authority` YAML reference. PR #563 merged as `bbcad5447fec07fbd124f126a6cdd25f18656dc2`; PR #564 merged as `8cf7caca3891b29cf3439dde8fb23e81a365a254`; C1C7 is finalized by Cutover 1C-8.

### C1C8-001 — Wave 6 cross-slice convergence audit

```yaml
cutover_pr: 565
merged_commit: f4a32067e385b563f366b81a68bbadde823febd8
old_path: docs/architecture/wave6_cross_slice_convergence_audit.md
old_blob_sha: ecb06b4a95095c28c2b953fae926219d22cfe814
old_content_sha256: 915b99fba7e136543be041ab44debc9331ef081ed0c80b1ad1226fd184b9bbf4
source_commit: 497ee3196c93ec0f69b4001a9c6bbd237009e35a
source_pr: 435
recorded_on: 2026-06-28
disposition: evidence_retained
new_canonical_path: docs/evidence/waves/wave6_cross_slice_convergence_audit.md
exact_source_snapshot: docs/evidence/waves/wave6_cross_slice_convergence_audit-source.txt
exact_source_blob_sha: ecb06b4a95095c28c2b953fae926219d22cfe814
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 1
  script_hard_coded_path_reference_files_updated_in_pr_tree: 1
  script_hard_coded_path_reference_occurrences_updated_in_pr_tree: 1
  relative_markdown_link_referrer_files_at_frozen_baseline: 3
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  current_tree_related_authority_references_updated: 2
  current_boundary_smoke_historical_path_removed: true
  documentation_link_check: passed
  documentation_semantic_audit: passed
  affected_current_boundary_checks: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical evidence document preserves the complete Wave 6 convergence account while correcting its live relative links for the evidence collection. The exact pre-cutover source remains available as the original Git blob. The dependency sweep identified one hard-coded current-boundary path, four Markdown relative links across three router files, and two `relaylm_related_authority` YAML references. PR #565 merged as `f4a32067e385b563f366b81a68bbadde823febd8`; C1C8 is finalized by Cutover 1C-9.

### C1C9-001 — Wave 7 cross-slice convergence audit

```yaml
cutover_pr: 566
merged_commit: 0689fc6c926aeaaece5f404a831f1000294e5cbd
old_path: docs/architecture/wave7_cross_slice_convergence_audit.md
old_blob_sha: 8bd6635ac4be0c352a3631ee518128b0a3356110
old_content_sha256: 265b8fb6db411c65d760a6879d6a00e6e52265d12e7b2ff5b09c3705869eb3c4
source_commit: cc1417f93b679e3c2ca2bb5ed78f53e2cb93ad7a
source_pr: 438
recorded_on: 2026-06-28
disposition: evidence_retained
new_canonical_path: docs/evidence/waves/wave7_cross_slice_convergence_audit.md
exact_source_snapshot: docs/evidence/waves/wave7_cross_slice_convergence_audit-source.txt
exact_source_blob_sha: 8bd6635ac4be0c352a3631ee518128b0a3356110
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 2
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 3
  script_hard_coded_path_reference_files_updated_in_pr_tree: 2
  script_hard_coded_path_reference_occurrences_updated_in_pr_tree: 4
  relative_markdown_link_referrer_files_at_frozen_baseline: 5
  relative_markdown_link_dependencies_at_frozen_baseline: 6
  current_tree_related_authority_references_updated: 4
  current_boundary_smoke_historical_path_removed: true
  e1_evaluation_smoke_updated: true
  documentation_link_check: passed
  documentation_semantic_audit: passed
  affected_current_boundary_checks: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical evidence document preserves the complete Wave 7 convergence account while correcting six internal relative links for the evidence collection. The exact pre-cutover source remains available as the original Git blob. The dependency sweep identified three repository-root literals across two files, four hard-coded script occurrences across two smoke files, six Markdown relative links across five referrer files, and four `relaylm_related_authority` YAML references. PR #566 merged as `0689fc6c926aeaaece5f404a831f1000294e5cbd`; C1C9 is finalized by Cutover 1C-10.

### C1C10-001 — E1-R5 post-Wave-7 correction convergence audit

```yaml
cutover_pr: 568
merged_commit: 1950b4dd95882649dfdfaea89c9701dd7c51e354
old_path: docs/architecture/e1r5_post_wave7_correction_convergence_audit.md
old_blob_sha: 0d7cbceca1259d127ebf4fa1a7f91bcbf9e144e5
old_content_sha256: 552e8744b3f32f2e4c21eb8273f56fe0ee4f95e22cf33ad7ae734625dcc41edb
source_commit: 676678a004c688eca856e37b3ecf48f98801452c
source_pr: 498
origin_pr: 452
recorded_on: 2026-06-30
disposition: evidence_retained
new_canonical_path: docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit.md
exact_source_snapshot: docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit-source.txt
exact_source_blob_sha: 0d7cbceca1259d127ebf4fa1a7f91bcbf9e144e5
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 1
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 1
  script_hard_coded_path_reference_files_updated_in_pr_tree: 1
  script_hard_coded_path_reference_occurrences_updated_in_pr_tree: 2
  relative_markdown_link_referrer_files_at_frozen_baseline: 4
  relative_markdown_link_dependencies_at_frozen_baseline: 5
  current_tree_related_authority_references_updated: 3
  canonical_internal_relative_links_repaired: 6
  current_boundary_smoke_historical_path_removed: true
  e1_evaluation_smoke_updated: true
  documentation_link_check: passed
  documentation_semantic_audit: passed
  affected_current_boundary_checks: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical evidence document preserves the complete E1-R5 post-Wave-7 correction account while repairing six internal relative links for the evidence collection. The exact pre-cutover source remains available as the original Git blob. The record was introduced by PR #452 and its exact pre-cutover form includes the later PM-D8 closure convergence from PR #498 after runtime fold-in PR #491. The dependency sweep identified one repository-root literal, two hard-coded current-boundary occurrences, five Markdown relative links across four referrer files, and three `relaylm_related_authority` YAML references. PR #568 merged as `1950b4dd95882649dfdfaea89c9701dd7c51e354`; C1C10 is finalized by Cutover 1C-11.

### C1C11-001 — MVP eval runner completion report

```yaml
cutover_pr: 569
merged_commit: 92c8969697b63e582c535f34d0008acc740fc529
old_path: docs/mvp/wave8/mvp_eval_runner_completion_report.md
old_blob_sha: 3ba3a2f5e402240b8d322b0ac55d9c77dfaed237
old_content_sha256: 3565af79a521f80bef021a7a9a9cd31c525192b95f9dcb561a0e027c2f790635
source_commit: 89404bf0f8f4855be673af34c1450f063a22151c
source_pr: 451
recorded_on: 2026-06-30
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/mvp_eval_runner_completion_report.md
exact_source_snapshot: docs/evidence/implementation/mvp_eval_runner_completion_report-source.txt
exact_source_blob_sha: 3ba3a2f5e402240b8d322b0ac55d9c77dfaed237
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 4
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 7
  relative_markdown_link_referrer_files_at_frozen_baseline: 2
  relative_markdown_link_dependencies_at_frozen_baseline: 2
  completion_report_validator_updated: true
  implementation_evidence_index_updated: true
  mvp_eval_runner_registry_updated: true
  mvp_eval_runner_workflow_updated: true
  documentation_current_boundary_smoke_updated: true
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  focused_mvp_eval_runner_checks: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete MVP eval runner implementation boundary while clarifying that current runner and O2/O3 status remain owned elsewhere. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. The dependency sweep identified seven repository-root path occurrences across four files, two Markdown links across two router files, and one generic completion-report validator whose legacy-only placement rule required migration-aware canonical evidence support. PR #569 merged as `92c8969697b63e582c535f34d0008acc740fc529`; C1C11 is finalized by Cutover 1C-12.

### C1C12-001 — O2/O3 and PM-D5-D7 docs convergence completion report

```yaml
cutover_pr: 570
merged_commit: 81a6b0079acc2e33a9913c6edac7276629b1ff15
old_path: docs/mvp/wave8/o2_o3_pm_d5_d7_docs_convergence_completion_report.md
old_blob_sha: 27a87767c6ee47d44e69230d65d5e4d97032096e
old_content_sha256: 797be1f18e94f9a0e9cec536e109ca8257ad5bcf75ca4c623d9b15bb65e4c1a7
source_commit: 276656a8916d1d0dbcd8caa4523f99e1877ce9d9
source_pr: 490
recorded_on: 2026-07-05
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/o2_o3_pm_d5_d7_docs_convergence_completion_report.md
exact_source_snapshot: docs/evidence/implementation/o2_o3_pm_d5_d7_docs_convergence_completion_report-source.txt
exact_source_blob_sha: 27a87767c6ee47d44e69230d65d5e4d97032096e
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 2
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 3
  relative_markdown_link_referrer_files_at_frozen_baseline: 2
  relative_markdown_link_dependencies_at_frozen_baseline: 2
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete O2/O3 and PM-D5-D7 documentation-convergence boundary while clarifying that current status and sequencing remain owned by current authorities. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. The dependency sweep identified three repository-root path occurrences across two files and two relative Markdown links across two router files. The migration-aware completion-report model and PR-link checks introduced by C1C11 apply to this canonical record without further validator changes. PR #570 merged as `81a6b0079acc2e33a9913c6edac7276629b1ff15`; C1C12 is finalized by Cutover 1C-13.

### C1C13-001 — E2 Value Smoke Harness completion report

```yaml
cutover_pr: 571
merged_commit: 2d9fc3aa26145cf80cdbfa5d2ccb84261d7d963e
old_path: docs/mvp/wave8/e2_value_smoke_harness_completion_report.md
old_blob_sha: 333ba34007a38b794572683c41e947ae1d0ad8cf
old_content_sha256: ffc09e20a41f7202c05682aa9e50a8c859107a64bacdc33ff5e9a81723b13358
source_commit: 51d678dfb0a10899db424e59c08af70865b8333f
source_pr: 481
recorded_on: 2026-07-04
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/e2_value_smoke_harness_completion_report.md
exact_source_snapshot: docs/evidence/implementation/e2_value_smoke_harness_completion_report-source.txt
exact_source_blob_sha: 333ba34007a38b794572683c41e947ae1d0ad8cf
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 1
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 1
  relative_markdown_link_referrer_files_at_frozen_baseline: 3
  relative_markdown_link_dependencies_at_frozen_baseline: 3
  implementation_evidence_index_updated: true
  release_readiness_reference_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e2_harness_smoke: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete E2 comparison-transcript harness implementation boundary while separating it from the later local human judgment and release-readiness conclusion. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. The dependency sweep identified one repository-root path occurrence, three Markdown links across three referrer files, one release-readiness reference, and one current-boundary evidence-map addition. The migration-aware completion-report model and PR-link checks introduced by C1C11 apply without further validator changes. PR #571 merged as `2d9fc3aa26145cf80cdbfa5d2ccb84261d7d963e`; C1C13 is finalized by Cutover 1C-14.

### C1C14-001 — Twin Extraction Tooling completion report

```yaml
cutover_pr: 572
merged_commit: 4c0e7d64110c9e2df37398ee0cda4678d4143e1c
old_path: docs/mvp/wave8/twin_extraction_completion_report.md
old_blob_sha: c0b71f940cebf4b6de2f912870a1be7e14c90b60
old_content_sha256: 8e2db5550392a4c08d8aa62d78fdabb4e920428c7efdc4a477973b7174a4bd2d
source_commit: fc7e77ef52f137c2a9224b20dff1e8e4711ba0f3
source_origin_commit: 2e484f9aea04425285e9c5ce690b38a8beb87e82
source_pr: 503
recorded_on: 2026-07-07
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/twin_extraction_completion_report.md
exact_source_snapshot: docs/evidence/implementation/twin_extraction_completion_report-source.txt
exact_source_blob_sha: c0b71f940cebf4b6de2f912870a1be7e14c90b60
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 3
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 3
  relative_markdown_link_referrer_files_at_frozen_baseline: 2
  relative_markdown_link_dependencies_at_frozen_baseline: 2
  implementation_evidence_index_updated: true
  twin_extraction_runbook_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_twin_extraction_smokes: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete offline Twin Extraction implementation boundary while separating it from current runbook-owned operation and later review-import bridge evolution. The exact pre-cutover source is retained as the final Git blob and byte-for-byte snapshot. The dependency sweep identified three repository-root path occurrences across three files, two Markdown links across two router files, and one current-boundary canonical evidence-map addition. The migration-aware completion-report model and PR-link checks apply without further validator changes. PR #572 merged as `4c0e7d64110c9e2df37398ee0cda4678d4143e1c`; C1C14 is finalized by Cutover 1C-15.

### C1C15-001 — LAT-1 Latency Measurement completion report

```yaml
cutover_pr: 573
merged_commit: bd6effac133c04fb9132135360685c24edd6d2a0
old_path: docs/mvp/wave8/lat1_latency_measurement_completion_report.md
old_blob_sha: 0bf5743b7ba0ac85e657bb06ae88b8f1d41b3936
old_content_sha256: a33d190625ee5f6f4f9f74143f74cc6a505927b07175cf8aec00638e72b4db42
source_commit: 85817a391e27492cd139bd75929a60e1065a1454
source_origin_commit: c77cf8e37a3f52c67c523004cf2a37b4c28f62f8
source_pr: 505
recorded_on: 2026-07-07
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/lat1_latency_measurement_completion_report.md
exact_source_snapshot: docs/evidence/implementation/lat1_latency_measurement_completion_report-source.txt
exact_source_blob_sha: 0bf5743b7ba0ac85e657bb06ae88b8f1d41b3936
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 2
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 2
  relative_markdown_link_referrer_files_at_frozen_baseline: 2
  relative_markdown_link_dependencies_at_frozen_baseline: 2
  implementation_evidence_index_updated: true
  lat1_architecture_and_evaluation_authorities_preserved: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_lat1_smokes: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete LAT-1 timing and offline retrieval-bench implementation boundary while separating it from current architecture-owned measurement behavior and evaluation-owned local scaling results. The exact pre-cutover source is retained as the final Git blob and byte-for-byte snapshot. The dependency sweep identified two repository-root path references across two files, two Markdown links across two router files, and one current-boundary canonical evidence-map addition. The migration-aware completion-report model and PR-link checks apply without further validator changes. PR #573 merged as `bd6effac133c04fb9132135360685c24edd6d2a0`; C1C15 is finalized by Cutover 1C-16.

### C1C16-001 — E1-R3 completion report

```yaml
cutover_pr: 574
merged_commit: c9e440cb44f4a1e95dac68caeabfefb872779ca6
old_path: docs/mvp/wave7/e1r3_completion_report.md
old_blob_sha: 40ceeaa4a7eca7e90cafcfb522cc8340ab31e40a
old_content_sha256: dcb189583bbf8771adc27aeef215f7d6e67134f0db73f6ae91e73a058f58b81c
source_commit: f92190f7990a990ccee914a6a6be18bab5e07331
source_origin_commit: 7bb2525cb000e893146408065f1aa5976f2b54ab
source_pr: 436
recorded_on: 2026-06-28
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/e1r3_completion_report.md
exact_source_snapshot: docs/evidence/implementation/e1r3_completion_report-source.txt
exact_source_blob_sha: 40ceeaa4a7eca7e90cafcfb522cc8340ab31e40a
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 3
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 3
  relative_markdown_link_referrer_files_at_frozen_baseline: 4
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  wave7_convergence_evidence_link_updated: true
  e1_evaluation_consolidation_updated: true
  e1_evaluation_smoke_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e1r3_smokes: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete E1-R3 provenance-preserving formation-summary implementation boundary while separating it from current architecture-owned behavior and cross-slice E1 evaluation authority. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. The dependency sweep identified three repository-root references across three files, four Markdown links across four router/evidence files, one Wave 7 convergence-evidence link, and the dedicated E1 consolidation smoke path. The migration-aware completion-report model and PR-link checks apply without further validator changes. PR #574 merged as `c9e440cb44f4a1e95dac68caeabfefb872779ca6`; C1C16 is finalized by Cutover 1C-17.

### C1C17-001 — E1-R4 completion report

```yaml
cutover_pr: 575
merged_commit: 82d959ed00e958cb970ebcde0490903ae884322c
old_path: docs/mvp/wave7/e1r4_completion_report.md
old_blob_sha: ea940e524c7c99173108c8088a3435485bd3736a
old_content_sha256: 0b1ea5483d185ebb5701a984a868bb2f41439f02427c07c70904e820f8541880
source_commit: cad2fc03c3a6e566de60684e6628b75a0e70eae8
source_origin_commit: e6e5b32cd489dda493ff0171a260dd561a91765c
source_pr: 437
recorded_on: 2026-06-28
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/e1r4_completion_report.md
exact_source_snapshot: docs/evidence/implementation/e1r4_completion_report-source.txt
exact_source_blob_sha: ea940e524c7c99173108c8088a3435485bd3736a
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 4
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 4
  relative_markdown_link_referrer_files_at_frozen_baseline: 4
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  wave7_convergence_evidence_link_updated: true
  e1_evaluation_consolidation_updated: true
  e1_evaluation_smoke_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e1r4_smokes: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete E1-R4 retrieval-response grounding and unsupported-detail suppression implementation boundary while separating it from current architecture-owned behavior and cross-slice E1 evaluation authority. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. The dependency sweep identified four repository-root references across four files, four Markdown links across four router/evidence files, one Wave 7 convergence-evidence link, and the dedicated E1 consolidation smoke path. The migration-aware completion-report model and PR-link checks apply without further validator changes. The old path above is only the historical migration identifier for this receipt.

PR #575 merged as `82d959ed00e958cb970ebcde0490903ae884322c`; C1C17 is finalized by Cutover 1C-18.

### C1C18-001 — E1-R5 completion report

```yaml
cutover_pr: 576
merged_commit: 91c21085b468052f77b65d5e1577cd1940fe0b2b
old_path: docs/mvp/wave7/e1r5_completion_report.md
old_blob_sha: 68fa2b0c76caf745e55f5f4ef3fd3677c8681a8d
old_content_sha256: 2f7b777321433cada0d840973bf3639ae3b5f7f6a7fee7edfb76c6809027d956
source_commit: 392810b74a0c76785beee7e3af7a5da3eacffa39
source_origin_commit: 477874cd08658297c4c6626e9423dd05d7bf45a4
source_pr: 439
recorded_on: 2026-06-28
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/e1r5_completion_report.md
exact_source_snapshot: docs/evidence/implementation/e1r5_completion_report-source.txt
exact_source_blob_sha: 68fa2b0c76caf745e55f5f4ef3fd3677c8681a8d
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 5
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 6
  relative_markdown_link_referrer_files_at_frozen_baseline: 5
  relative_markdown_link_dependencies_at_frozen_baseline: 6
  e1r5_architecture_handoff_updated: true
  post_wave7_correction_audit_link_updated: true
  correction_audit_exact_snapshot_unchanged: true
  e1_evaluation_consolidation_updated: true
  e1_evaluation_smoke_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  cutover_preparation_self_test_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e1r5_smokes: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete E1-R5 bounded Primary MEM candidate-discovery implementation boundary from PR #439 while separating it from current architecture-owned behavior and the PR #491 canonical Primary recall adapter fold-in. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. The dependency sweep identified six repository-root references across five files and six Markdown-link dependencies across five router, handoff, and evidence files. The current Post-Wave-7 correction audit is relinked while its exact source snapshot remains unchanged. The old path above is only the historical migration identifier for this receipt.

### C1C19-001 — O1F completion report

```yaml
cutover_pr: 581
merged_commit: be3cf9fc2ed5e85fd3dff4737f8598e13edb6907
old_path: docs/mvp/wave6/o1f_completion_report.md
old_blob_sha: cae70dbe1648ed6757af928eeae0becd7fd313dd
old_content_sha256: b7c61bd6711e2f8ab741e4f73df5715d64229cfa5f11865c1004eed9d5a6e976
source_commit: 14b91b5ed21f240aa92eb54189e0b2d36ab089f7
source_origin_commit: 961fff2d935cd764e81e577887328e86363e56d5
source_pr: 429
recorded_on: 2026-06-27
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/o1f_completion_report.md
exact_source_snapshot: docs/evidence/implementation/o1f_completion_report-source.txt
exact_source_blob_sha: cae70dbe1648ed6757af928eeae0becd7fd313dd
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 4
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 6
  relative_markdown_link_referrer_files_at_frozen_baseline: 6
  relative_markdown_link_dependencies_at_frozen_baseline: 6
  o1f_architecture_handoff_updated: true
  wave6_convergence_evidence_link_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  consolidated_completion_report_smoke_updated: true
  dedicated_o1f_workflow_absent_in_current_tree: true
  cutover_preparation_self_test_reused_without_path_change: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_o1f_smokes: passed
  o1_scheduler_and_operational_regressions: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete O1F validation-only scheduler operational-hardening boundary from PR #429 while separating it from current architecture-, implementation-, and focused-smoke-owned behavior. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. The dependency sweep identified six repository-root literals across four files and six Markdown-link dependencies across six router, handoff, convergence, and source-report files. The consolidated scheduler-worker smoke command now validates the canonical report. The dedicated O1F workflow named by the historical source report is no longer present in the current tree and is not recreated. The migration-aware completion-report model and PR-link checks apply without validator changes. The old path above is only the historical migration identifier for this receipt.

### C1C20-001 — I-5B completion report

```yaml
cutover_pr: 582
merged_commit: ca1a921eba7131072c3608a5f2032e2d6008f770
old_path: docs/mvp/wave6/i5b_completion_report.md
old_blob_sha: 19d631470dc0cf16e65c214169e3097758381de9
old_content_sha256: 2efce2a61fb09b9ed4226d2a09e6e6b78645bf11f65badc855e03f7e64b8aa85
source_commit: eac44fb0038c0a7eadd94c1d29b2ce90f52a6349
source_origin_commit: 734a3880035651f91eb065b892fc41af6f5cc026
source_pr: 430
recorded_on: 2026-06-28
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/i5b_completion_report.md
exact_source_snapshot: docs/evidence/implementation/i5b_completion_report-source.txt
exact_source_blob_sha: 19d631470dc0cf16e65c214169e3097758381de9
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 1
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 1
  relative_markdown_link_referrer_files_at_frozen_baseline: 4
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: 3
  i5b_architecture_handoff_updated: true
  wave6_convergence_evidence_link_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  dedicated_i5b_workflow_absent_in_current_tree: true
  cutover_preparation_self_test_reused_without_path_change: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_i5a_i5b_smokes: passed
  soul_lab_pin_unpin_ui_validation: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete I-5B Pin / Unpin apply, API/UI, durable-governance, and ranking-hint boundary from PR #430 while separating it from current handoff-, implementation-, and focused-smoke-owned behavior. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. Four live Markdown-link dependencies and one repository-root validation literal are moved to the canonical path; legacy references remain only in this migration receipt and frozen exact source snapshots. The dedicated I-5B workflow named by the historical source report is no longer present in the current tree and is not recreated. The migration-aware completion-report model and PR-link checks apply without validator changes.

### C1C21-001 — I-7C completion report

```yaml
cutover_pr: 583
merged_commit: ff7f5ba3fab8dd9224ff8d77aa87e47ac221726e
old_path: docs/mvp/wave6/i7c_completion_report.md
old_blob_sha: 447298a00d418f461abda33060e7f59d96656c64
old_content_sha256: 97e242a355bb0fd204492fb697ed6523ed85812cd3e73e7cb73696a89e258907
source_commit: 4add07ae3084b8f4bf1364189411014bb71cf118
source_origin_commit: 21d10bfed22ed9626e4224bf927ff59a5e399505
source_pr: 431
recorded_on: 2026-06-27
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/i7c_completion_report.md
exact_source_snapshot: docs/evidence/implementation/i7c_completion_report-source.txt
exact_source_blob_sha: 447298a00d418f461abda33060e7f59d96656c64
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 3
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 3
  relative_markdown_link_referrer_files_at_frozen_baseline: 4
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: 3
  i7c_architecture_handoff_updated: true
  wave6_convergence_evidence_link_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  consolidated_held_governance_smoke_updated: true
  dedicated_i7c_workflow_absent_in_current_tree: true
  cutover_preparation_self_test_reused_without_path_change: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_i7ab_i7c_smokes: passed
  related_i4d_o1e_b3_regressions: passed
  soul_lab_held_governance_ui_validation: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete I-7C Held Apply / Discard runtime-governance, API/UI, durable-evidence, and leakage-boundary implementation boundary from PR #431 while separating it from current handoff-, implementation-, queue-lifecycle-, worker-, and focused-smoke-owned behavior. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. Four live Markdown-link dependencies and three repository-root validation or handoff literals are moved to the canonical path; legacy references remain only in this migration receipt and frozen exact source snapshots. The dedicated I-7C workflow named by the historical source report is no longer present in the current tree and is not recreated. The migration-aware completion-report model and PR-link checks apply without validator changes.

### C1C22-001 — E1-R1 completion report

```yaml
cutover_pr: 584
merged_commit: 4cc36a948b399d5657c89b0b0c835287f9b93cd3
old_path: docs/mvp/wave6/e1r1_completion_report.md
old_blob_sha: 3d4e78d63e4be836e1de8b0ad1781a513e5349bc
old_content_sha256: 35c8d68527fea415465119f28ca366897ab7d320f6828fa92489dff4af58c6d7
source_commit: 39c5b982c9883ee39792450d40e4528c8a8db84b
source_origin_commit: 52768cbdac3c9630373a2c369574002ac196e72b
source_pr: 433
recorded_on: 2026-06-27
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/e1r1_completion_report.md
exact_source_snapshot: docs/evidence/implementation/e1r1_completion_report-source.txt
exact_source_blob_sha: 3d4e78d63e4be836e1de8b0ad1781a513e5349bc
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 4
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 4
  relative_markdown_link_referrer_files_at_frozen_baseline: 4
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: 2
  e1r1_architecture_handoff_updated: true
  e1_evaluation_consolidation_updated: true
  wave6_convergence_evidence_link_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  consolidated_e1r1_smoke_updated: true
  e1_evaluation_smoke_updated: true
  dedicated_e1r1_workflow_absent_in_current_tree: true
  cutover_preparation_self_test_reused_without_path_change: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e1r1_smoke: passed
  e1_evaluation_consolidation_smoke: passed
  consolidated_runtime_e1r1_group: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete E1-R1 route-owned trusted Home scene-admission implementation boundary from PR #433 while separating it from current handoff-, trust-policy-, implementation-, source/queue-, worker-, and focused-smoke-owned behavior. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. Live Markdown-link and repository-root validation dependencies are moved to the canonical path; legacy references remain only in this migration receipt and frozen exact source snapshots. The dedicated E1-R1 workflow named by the historical source report is no longer present in the current tree and is not recreated. The migration-aware completion-report model and PR-link checks apply without validator changes.

### C1C23-001 — E1-R2 completion report

```yaml
cutover_pr: 585
merged_commit: c068a6a4d447f7b622346da2766507de532fe0bc
old_path: docs/mvp/wave6/e1r2_completion_report.md
old_blob_sha: 107923354f09e0e3340e329f282d2c818910cad2
old_content_sha256: 72e1fcb022cf2db3bcbda3e3d14a46a18da1f50c3747f6706301346abc6f7722
source_commit: 76f80f590f64c5078fb93bc43b62c49c866b84bf
source_origin_commit: fefd3559ac32a37ed932faa130612a6a3da43c61
source_pr: 432
recorded_on: 2026-06-27
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/e1r2_completion_report.md
exact_source_snapshot: docs/evidence/implementation/e1r2_completion_report-source.txt
exact_source_blob_sha: 107923354f09e0e3340e329f282d2c818910cad2
verification:
  old_path_removed_in_pr_tree: true
  exact_source_blob_reused: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 4
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 4
  relative_markdown_link_referrer_files_at_frozen_baseline: 4
  relative_markdown_link_dependencies_at_frozen_baseline: 4
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: 2
  e1r2_architecture_handoff_updated: true
  e1_evaluation_consolidation_updated: true
  wave6_convergence_evidence_link_updated: true
  implementation_evidence_index_updated: true
  documentation_current_boundary_smoke_updated: true
  consolidated_e1r2_smoke_updated: true
  e1_evaluation_smoke_updated: true
  dedicated_e1r2_workflow_absent_in_current_tree: true
  cutover_preparation_self_test_reused_without_path_change: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e1r2_smoke: passed
  e1_evaluation_consolidation_smoke: passed
  consolidated_runtime_e1r2_group: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete E1-R2 explicit dry-run-first idempotent character-store bootstrap implementation boundary from PR #432 while separating it from current handoff-, command-, store-layout-, implementation-, queue/worker/scheduler-, and focused-smoke-owned behavior. The exact pre-cutover source is retained as the original Git blob and byte-for-byte snapshot. Live Markdown-link and repository-root validation dependencies are moved to the canonical path; legacy references remain only in this migration receipt and frozen exact source snapshots. The dedicated E1-R2 workflow named by the historical source report is no longer present in the current tree and is not recreated. The migration-aware completion-report model and PR-link checks apply without validator changes.


### C1C24-001 — docs horizontal status sweep completion report

```yaml
cutover_pr: 587
merged_commit: aa40f19cdf808c9876e40b0a32ee9e5a3f1187e8
old_path: docs/mvp/wave6/docs_horizontal_status_sweep_completion_report.md
old_blob_sha: c92bc7e856ef28e862a738c47668d46c67a71904
old_content_sha256: 889edab78de527869e3b94c764fadf9d9cce92b03f8adb946e42c3e6ca6a7627
source_commit: 86577b7712ea9efcc228f32a431b3606e552d40a
source_origin_commit: 6a0a384d3524fe98528643da666284576d974cd1
source_pr: 434
source_blob_sha: 2057afb52dab8903064853f0899d954c888bb213
source_content_sha256: bf0ba10a2f97539a4217fd8c78629c83d05e0e70d0a361759b1ac9ca3173464e
post_source_link_repair_commit: d1b920c3c7fcdf16053e8c9f449863cadfcb7384
recorded_on: 2026-06-27
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/docs_horizontal_status_sweep_completion_report.md
exact_source_snapshot: docs/evidence/implementation/docs_horizontal_status_sweep_completion_report-source.txt
exact_source_blob_sha: c92bc7e856ef28e862a738c47668d46c67a71904
verification:
  old_path_removed_in_pr_tree: true
  exact_pre_cutover_blob_reused: true
  source_pr_blob_recorded: true
  source_pr_blob_differs_from_pre_cutover_blob: true
  source_delta_is_single_wave5_canonical_path_repair: true
  canonical_evidence_metadata_added: true
  external_live_old_path_dependencies_at_cutover: 0
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: 2
  implementation_evidence_index_updated: true
  mvp_evidence_index_updated: true
  documentation_router_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the docs-only horizontal current-status sweep from PR #434 while separating it from current Project Status, Documentation Model, feature-family behavior, sequencing, and operator guidance. The byte-exact snapshot retains the cutover input blob. The source PR final-head/merge blob is recorded separately because commit `d1b920c3c7fcdf16053e8c9f449863cadfcb7384` later repaired only the Wave 5 convergence-audit path. No external live old-path dependency existed at cutover; the two old-path occurrences were internal historical changed-file and validation-command text in the source report. This move removes the last Markdown file under `docs/mvp/wave6/` without adding a compatibility path.


### C1C25-001 — E1 MVP evaluation consolidation completion report

```yaml
cutover_pr: 588
merged_commit: ba991a144995b74ddac99cf665b9503d7dc5cd39
old_path: docs/mvp/wave5/e1_completion_report.md
old_blob_sha: c87b9929ce6e527ef2b94beeb2059f98439b6019
old_content_sha256: 980cc5898f3b6cb8bc7ad0b502740a5ca9f79a54ebfa023c24d5d1c3a55289da
source_commit: a4521f2a450ed52de3101e208676571c4c6b33e2
source_origin_commit: 95c159ff747a167cd6cf99c7c5df656fd01e345d
source_pr: 425
source_blob_sha: 9b16c8875668f8bde40de809c472e7873da3f34e
source_content_sha256: e5e2d6736aa3f9236e3da3b6c4ed0888fb9b046e18e2cba6af98d6eb6f5e63ec
post_source_link_repair_commit: 80c6e775ae30ba68b1eb51148b4395320364d8d3
recorded_on: 2026-06-27
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/e1_completion_report.md
exact_source_snapshot: docs/evidence/implementation/e1_completion_report-source.txt
exact_source_blob_sha: c87b9929ce6e527ef2b94beeb2059f98439b6019
verification:
  old_path_removed_in_pr_tree: true
  exact_pre_cutover_blob_reused: true
  source_pr_blob_recorded: true
  source_pr_blob_differs_from_pre_cutover_blob: true
  source_delta_is_single_wave4_canonical_path_repair: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 5
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 5
  markdown_link_referrer_files_updated_in_pr_tree: 3
  markdown_link_occurrences_updated_in_pr_tree: 3
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: 2
  frozen_wave5_source_snapshot_legacy_references_preserved: true
  implementation_evidence_index_updated: true
  mvp_evidence_index_updated: true
  documentation_router_updated: true
  architecture_router_updated: true
  e1_evaluation_consolidation_smoke_updated: true
  wave5_convergence_evidence_and_smoke_updated: true
  e1_and_wave5_workflows_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_e1_evaluation_smoke: passed
  wave5_cross_slice_convergence_smoke: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the docs-only E1 MVP evaluation-consolidation boundary from PR #425 while separating it from current E1 architecture, later E1-R1 through E1-R5 implementation, repository-wide status, sequencing, and operator guidance. The byte-exact snapshot retains the cutover input blob. The source PR final-head/merge blob is recorded separately because commit `80c6e775ae30ba68b1eb51148b4395320364d8d3` later repaired only the Wave 4 convergence-audit path. Five repository-root literals and three Markdown links are moved to the canonical path; historical old-path references remain only in the migration receipt and frozen exact source snapshots.


### C1C26-001 — O1E scheduler operational-controls completion report

```yaml
cutover_pr: 589
merged_commit: 087631f8bd18d95976bbeba4b1c3988a3d3df68e
old_path: docs/mvp/wave5/o1e_completion_report.md
old_blob_sha: bd876542c3774695830ec8929bcbb342de74e824
old_content_sha256: 5fa4248bde4015a635de0cbd98091e88d184bd7c8b0a467d2f3092823e466766
source_commit: f5f93562679f3ee1e87c36cd0ce9a0c6151d231d
source_origin_commit: 49750ccb693ab6ebca1f5a0947c69c06a4a03d31
source_pr: 426
source_blob_sha: bd876542c3774695830ec8929bcbb342de74e824
source_content_sha256: 5fa4248bde4015a635de0cbd98091e88d184bd7c8b0a467d2f3092823e466766
pre_cutover_blob_sha: bd876542c3774695830ec8929bcbb342de74e824
pre_cutover_content_sha256: 5fa4248bde4015a635de0cbd98091e88d184bd7c8b0a467d2f3092823e466766
post_source_modification_commits: []
recorded_on: 2026-06-27
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/o1e_completion_report.md
exact_source_snapshot: docs/evidence/implementation/o1e_completion_report-source.txt
exact_source_blob_sha: bd876542c3774695830ec8929bcbb342de74e824
verification:
  old_path_removed_in_pr_tree: true
  exact_pre_cutover_blob_reused: true
  source_pr_blob_recorded: true
  source_pr_blob_equals_pre_cutover_blob: true
  source_to_pre_cutover_text_diff_empty: true
  post_source_report_modifications_absent: true
  canonical_evidence_metadata_added: true
  repository_root_literal_reference_files_updated_in_pr_tree: 3
  repository_root_literal_reference_occurrences_updated_in_pr_tree: 3
  markdown_link_referrer_files_updated_in_pr_tree: 3
  markdown_link_occurrences_updated_in_pr_tree: 3
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: 2
  frozen_wave5_source_snapshot_legacy_references_preserved: true
  implementation_evidence_index_updated: true
  mvp_evidence_index_updated: true
  documentation_router_updated: true
  architecture_router_updated: true
  o1e_architecture_handoff_updated: true
  wave5_convergence_evidence_and_smoke_updated: true
  wave5_workflow_updated: true
  dedicated_o1e_workflow_absent_in_current_tree: true
  documentation_current_boundary_smoke_updated: true
  consolidated_scheduler_worker_report_path_dependency_absent: true
  consolidated_scheduler_worker_o1e_smokes_preserved: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_o1e_operational_controls_smokes: passed
  scheduler_contract_and_regression_smokes: 19_passed_1_environment_blocked
  o1b_security_unix_socket_smoke: environment_blocked_by_sandbox
  consolidated_scheduler_worker_group: environment_blocked_before_o1e_phase
  wave5_cross_slice_convergence_smoke: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  documentation_current_boundary_smoke: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete bounded O1E scheduler operational-controls implementation boundary from PR #426 while separating it from current handoff-, implementation-, contract-, B3 queue-lifecycle-, O1D1/O1D2 scheduler-, O1F validation-, and focused-smoke-owned behavior. The source PR final-head, merge, and pre-cutover forms are byte-identical, and no later commit modified the report. Three repository-root literals and three resolved Markdown links move to the canonical path. The exact snapshot and the frozen Wave 5 source snapshot retain their historical old-path text; no compatibility path, fallback, or runtime change is introduced. The dedicated O1E workflow named by the source report is absent from the current tree and is not recreated.


### C1C27-001 — I-4F Forget product-completion validation report

```yaml
cutover_pr: 590
merged_commit: 34739fdf154a1634a6eb8650f57acd66065312cd
old_path: docs/mvp/wave5/i4f_completion_report.md
old_blob_sha: f7c451802f97109fd431cbb1f6a57910d4ea5b93
old_content_sha256: 45e486844536829d23b9e303ef5e7925385f94ac5887027669facadafc9bbce5
source_commit: 2aac80c51c65b64dc70fd2c5f58b6ac729e89a23
source_origin_commit: 937718dcb328fda5e3e37bb951b39fc66629f57a
source_pr: 427
source_blob_sha: f7c451802f97109fd431cbb1f6a57910d4ea5b93
source_content_sha256: 45e486844536829d23b9e303ef5e7925385f94ac5887027669facadafc9bbce5
pre_cutover_blob_sha: f7c451802f97109fd431cbb1f6a57910d4ea5b93
pre_cutover_content_sha256: 45e486844536829d23b9e303ef5e7925385f94ac5887027669facadafc9bbce5
post_source_modification_commits: []
recorded_on: 2026-06-27
disposition: evidence_retained
new_canonical_path: docs/evidence/implementation/i4f_completion_report.md
exact_source_snapshot: docs/evidence/implementation/i4f_completion_report-source.txt
exact_source_blob_sha: f7c451802f97109fd431cbb1f6a57910d4ea5b93
verification:
  old_path_removed_in_pr_tree: true
  exact_pre_cutover_blob_reused: true
  source_head_blob_recorded: true
  source_merge_blob_recorded: true
  source_head_merge_and_pre_cutover_blobs_equal: true
  source_to_pre_cutover_text_diff_empty: true
  post_source_report_modifications_absent: true
  canonical_evidence_metadata_added: true
  exact_old_path_live_files_updated_in_pr_tree: 6
  exact_old_path_live_occurrences_updated_in_pr_tree: 7
  markdown_link_referrer_files_updated_in_pr_tree: 3
  markdown_link_occurrences_updated_in_pr_tree: 3
  source_report_internal_legacy_path_occurrences_preserved_in_exact_snapshot: 2
  frozen_wave5_source_snapshot_legacy_occurrences_preserved: 2
  implementation_evidence_index_updated: true
  mvp_evidence_index_updated: true
  documentation_router_updated: true
  architecture_router_updated: true
  i4f_architecture_handoff_updated: true
  wave5_convergence_evidence_and_smoke_updated: true
  wave5_workflow_updated: true
  consolidated_ui_report_path_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_i4f_smokes: passed
  i4a_through_i4e_regressions: passed
  soul_lab_ui_validation: passed
  consolidated_forget_lifecycle_regressions: passed
  wave5_cross_slice_convergence_smoke: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  documentation_current_boundary_smoke: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The canonical record preserves the complete validation-only I-4F Forget product-completion boundary from PR #427 while separating it from current handoff-, production-implementation-, contract-, focused-smoke-, and SOUL Lab UI-validation-owned behavior. The source final-head, merge, and pre-cutover forms are byte-identical, and no later commit modified the report. Seven exact old-path literals across six live files and three resolved Markdown links move to the canonical path. The exact snapshot and frozen Wave 5 source snapshot retain their historical old-path text. This completes the live Wave 5 completion-report cutover without compatibility files or runtime behavior change.


### C1C28-001 — Wave 4 implementation completion reports

```yaml
cutover_pr: 591
merged_commit: 4e37234d8d8c6b0f9bf28c5c31648d2955973ad4
record_count: 5
recorded_on: 2026-06-27
disposition: evidence_retained
records:
  - source_pr: 418
    source_commit: 83617461bd72fdd59bc9d058cb279b61c8e58603
    source_origin_commit: 49fb43130155826fcc8b2b951d77484ff8ddaddf
    old_path: docs/mvp/wave4/o1d2_completion_report.md
    source_blob_sha: 601daa1303ad7119aaddaffd84dc4cff2dbb234e
    source_content_sha256: ff45ac1565494f07a776ab5fcdb6b886230efda9f6c9e8162c67d019599ffc97
    pre_cutover_blob_sha: 711e6426fbdff5b6d768facd80b103ec6aed9c72
    pre_cutover_content_sha256: 4f3f0937f0900749cb379d7a6ea7ba3583011c3ecb3426716237c1f1e1f2fca3
    post_source_modification_commits:
      - 4dc151989f0a918f51e2036c1ee55c8f438f811c
    new_canonical_path: docs/evidence/implementation/o1d2_completion_report.md
    exact_source_snapshot: docs/evidence/implementation/o1d2_completion_report-source.txt
    exact_source_blob_sha: 711e6426fbdff5b6d768facd80b103ec6aed9c72
  - source_pr: 420
    source_commit: 551e0e7877e09f69d95a8491b55b2af8199f7dc7
    source_origin_commit: 3e3d2570ecdfcde4c8bfdee06c5607cb6632c133
    old_path: docs/mvp/wave4/i4e_completion_report.md
    source_blob_sha: c98117190fd8de637784181e7a413e28800917ea
    source_content_sha256: def12c88540101b20b26f815dc0afc0702f96b857b83bfb633d3add6d05c563d
    pre_cutover_blob_sha: c98117190fd8de637784181e7a413e28800917ea
    pre_cutover_content_sha256: def12c88540101b20b26f815dc0afc0702f96b857b83bfb633d3add6d05c563d
    post_source_modification_commits: []
    new_canonical_path: docs/evidence/implementation/i4e_completion_report.md
    exact_source_snapshot: docs/evidence/implementation/i4e_completion_report-source.txt
    exact_source_blob_sha: c98117190fd8de637784181e7a413e28800917ea
  - source_pr: 421
    source_commit: 8ef816b8815ac82bbb0c5d8da6a67407905b01ac
    source_origin_commit: 5736636da839486140f72c731f18a4a85c39b13c
    old_path: docs/mvp/wave4/ui_b1a_completion_report.md
    source_blob_sha: 1ec7c923e627415847c075f144bc4d7ecb4120ca
    source_content_sha256: fd6a164dfdffc74298b3ffdcb4b734eabb51dada08dc64556b130eeeb0445cb0
    pre_cutover_blob_sha: 1ec7c923e627415847c075f144bc4d7ecb4120ca
    pre_cutover_content_sha256: fd6a164dfdffc74298b3ffdcb4b734eabb51dada08dc64556b130eeeb0445cb0
    post_source_modification_commits: []
    new_canonical_path: docs/evidence/implementation/ui_b1a_completion_report.md
    exact_source_snapshot: docs/evidence/implementation/ui_b1a_completion_report-source.txt
    exact_source_blob_sha: 1ec7c923e627415847c075f144bc4d7ecb4120ca
  - source_pr: 417
    source_commit: 896536f3bd7fe11b18787b99852faf11f3a6eef9
    source_origin_commit: 2f8597911774b70f1c001db8332b3dfcc18d23ca
    old_path: docs/mvp/wave4/i5a_completion_report.md
    source_blob_sha: 899fb3c7f22f5b2e7deace4246834726c4674510
    source_content_sha256: 660600384845d88b78b783df887695c2fc3f27d4d23845f8c79b996e20b059bd
    pre_cutover_blob_sha: 899fb3c7f22f5b2e7deace4246834726c4674510
    pre_cutover_content_sha256: 660600384845d88b78b783df887695c2fc3f27d4d23845f8c79b996e20b059bd
    post_source_modification_commits: []
    new_canonical_path: docs/evidence/implementation/i5a_completion_report.md
    exact_source_snapshot: docs/evidence/implementation/i5a_completion_report-source.txt
    exact_source_blob_sha: 899fb3c7f22f5b2e7deace4246834726c4674510
  - source_pr: 423
    source_commit: d77b10a39911486ba95eb0458bfafa240559267f
    source_origin_commit: 5e0f866e959ab2bc5af00e0502b2026f4b52a779
    old_path: docs/mvp/wave4/i7ab_completion_report.md
    source_blob_sha: 5b56fc515e9e5df74694cd14da7cf0b68be693f6
    source_content_sha256: 1705167bdcc55694c9b8d2c90f02eaecf5970ed3982eb9897d3d4d69ac05389d
    pre_cutover_blob_sha: 5b56fc515e9e5df74694cd14da7cf0b68be693f6
    pre_cutover_content_sha256: 1705167bdcc55694c9b8d2c90f02eaecf5970ed3982eb9897d3d4d69ac05389d
    post_source_modification_commits: []
    new_canonical_path: docs/evidence/implementation/i7ab_completion_report.md
    exact_source_snapshot: docs/evidence/implementation/i7ab_completion_report-source.txt
    exact_source_blob_sha: 5b56fc515e9e5df74694cd14da7cf0b68be693f6
verification:
  old_paths_removed_in_pr_tree: true
  exact_pre_cutover_blobs_reused: true
  canonical_evidence_wrappers_added: 5
  source_head_and_merge_blobs_recorded: true
  source_head_merge_and_pre_cutover_equal_records: 4
  source_to_pre_cutover_diff_records: 1
  o1d2_delta_is_single_wave3_canonical_path_repair: true
  external_repository_root_literal_files_updated: 1
  external_repository_root_literal_occurrences_updated: 1
  markdown_link_referrer_files_updated: 3
  markdown_link_occurrences_updated: 15
  filename_validation_selectors_updated: 5
  source_report_internal_legacy_occurrences_preserved_in_exact_snapshots: 4
  implementation_evidence_index_updated: true
  documentation_router_updated: true
  architecture_router_updated: true
  mvp_evidence_index_updated: true
  current_authority_handoffs_updated: 5
  wave4_convergence_smoke_updated: true
  wave4_workflow_updated: true
  consolidated_group_selection_updated: true
  documentation_current_boundary_smoke_updated: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  focused_o1d2_smokes: passed
  focused_i4e_smokes: passed
  focused_ui_b1a_smokes: passed
  focused_i5a_smokes: passed
  focused_i7ab_smokes: passed
  downstream_regressions_and_consolidated_groups: passed
  soul_lab_ui_validation: passed
  wave4_cross_slice_convergence_smoke: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  documentation_current_boundary_smoke: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  consolidated_selection_self_test: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The five canonical records preserve the bounded Wave 4 implementation evidence from PRs #417, #418, #420, #421, and #423 while separating it from current handoff-, production-implementation-, contract-, focused-smoke-, later-continuation-, and SOUL Lab-owned behavior. O1D2 has one understood post-source documentation repair: commit `4dc151989f0a918f51e2036c1ee55c8f438f811c` replaced the former Wave 3 audit authority path with its canonical evidence path. The other four source, merge, and pre-cutover report forms are byte-identical. Fifteen resolved Markdown links, one external repository-root literal, and five filename validation selectors move atomically; four internal old-path strings remain only in byte-exact snapshots. No compatibility path or runtime behavior change is introduced.


### C1C29-001 — Wave 3 implementation completion reports

```yaml
cutover_pr: 592
merged_commit: aa6ccee64ee474c0e4d9d174f9e9e0df5366baeb
record_count: 3
recorded_on: 2026-06-27
disposition: evidence_retained
records:
  - source_pr: 411
    source_commit: 6cb461cb614d14965f5a49c1c4b517755f44f4a6
    source_origin_commit: e2caa1bdb53468ca282e8f374ba8ceebf839c976
    old_path: docs/mvp/wave3/i1ge_completion_report.md
    source_blob_sha: f03425235eea7a1a82bf881d796a4ce4e44205e8
    source_content_sha256: 088822c7c3c73503eee28572b3d084b34f6005e18a7aa1402c8d5173381e396c
    pre_cutover_blob_sha: f03425235eea7a1a82bf881d796a4ce4e44205e8
    pre_cutover_content_sha256: 088822c7c3c73503eee28572b3d084b34f6005e18a7aa1402c8d5173381e396c
    post_source_modification_commits: []
    new_canonical_path: docs/evidence/implementation/i1ge_completion_report.md
    exact_source_snapshot: docs/evidence/implementation/i1ge_completion_report-source.txt
    exact_source_blob_sha: f03425235eea7a1a82bf881d796a4ce4e44205e8
  - source_pr: 414
    source_commit: 81c58516a4ba04c6e439ff17d633575bb193f843
    source_origin_commit: 48e890f05f76196b73267559b079f4a05c441077
    old_path: docs/mvp/wave3/i4d_completion_report.md
    source_blob_sha: eecdd09ad3e6f2cc344b955f1962d034d7f321bb
    source_content_sha256: 6fc50a3b977636be47e270f21df4764127b695a280ef41996441a1589ce7eedc
    pre_cutover_blob_sha: eecdd09ad3e6f2cc344b955f1962d034d7f321bb
    pre_cutover_content_sha256: 6fc50a3b977636be47e270f21df4764127b695a280ef41996441a1589ce7eedc
    post_source_modification_commits: []
    new_canonical_path: docs/evidence/implementation/i4d_completion_report.md
    exact_source_snapshot: docs/evidence/implementation/i4d_completion_report-source.txt
    exact_source_blob_sha: eecdd09ad3e6f2cc344b955f1962d034d7f321bb
  - source_pr: 412
    source_commit: 7aa051abe6a9e49a2f67c193b7e742f9406ec54f
    source_origin_commit: 9b6349236f1a01f3cdccbe9e3c2c874ae1137475
    old_path: docs/mvp/wave3/o1d1_completion_report.md
    source_blob_sha: 5de4588bfa8c5c944d3506eb5f0784431b256b2d
    source_content_sha256: cf2be3319bf3daf8b7458ab8ea8642f39cb4489f293f9cb4de6d8e2155621eba
    pre_cutover_blob_sha: 5de4588bfa8c5c944d3506eb5f0784431b256b2d
    pre_cutover_content_sha256: cf2be3319bf3daf8b7458ab8ea8642f39cb4489f293f9cb4de6d8e2155621eba
    post_source_modification_commits: []
    new_canonical_path: docs/evidence/implementation/o1d1_completion_report.md
    exact_source_snapshot: docs/evidence/implementation/o1d1_completion_report-source.txt
    exact_source_blob_sha: 5de4588bfa8c5c944d3506eb5f0784431b256b2d
verification:
  old_paths_removed_in_pr_tree: true
  exact_pre_cutover_blobs_reused: true
  canonical_evidence_wrappers_added: 3
  source_head_and_merge_blobs_recorded: true
  source_head_merge_and_pre_cutover_equal_records: 3
  source_to_pre_cutover_diff_records: 0
  post_source_repairs: 0
  live_dependency_files_updated: 6
  live_dependency_occurrences_updated: 17
  shared_batch_files_updated: 6
  implementation_evidence_index_updated: true
  mvp_evidence_index_updated: true
  wave3_convergence_audit_link_repaired: true
  i1ge_architecture_handoff_updated: true
  i4d_architecture_handoff_evidence_link_added: true
  o1d1_architecture_handoff_evidence_link_added: true
  wave3_convergence_smoke_updated: true
  wave3_security_smoke_updated: true
  consolidated_group_selection_updated: true
  consolidated_smoke_contract_updated: true
  documentation_current_boundary_smoke_updated: true
  documentation_current_boundary_smoke_extended_for_wave3_reports: true
  migration_aware_completion_report_model_reused: true
  migration_aware_pr_link_smoke_reused: true
  source_report_internal_legacy_occurrences_preserved_in_exact_snapshots: 6
  frozen_wave3_audit_source_snapshot_legacy_occurrences_preserved: 3
  focused_i1ge_smokes: passed
  focused_i4d_smokes: passed
  focused_o1d1_smokes: passed
  downstream_regressions_and_consolidated_groups: passed
  wave3_cross_slice_convergence_smoke: passed
  wave3_cross_slice_security_smoke: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  documentation_current_boundary_smoke: passed
  completion_report_model_and_file_checks: passed
  completion_report_pr_link_check: passed
  consolidated_selection_self_test: passed
  all_github_actions: passed
  unresolved_review_threads: 0
```

The three canonical records preserve the bounded Wave 3 implementation evidence from PRs #411, #412, and #414 while separating it from current handoff-, production-authority-, configuration-, and focused-smoke-owned behavior. All three source, merge, and pre-cutover report forms are byte-identical; no post-source commit ever modified any of the three reports, so no repair was required. Seventeen resolved literal old-path occurrences across six live files move atomically, including retargeting the `docs/mvp/wave3/*` consolidated-selector wildcard to three explicit canonical paths and closing a pre-existing gap so the O1D1 canonical path now correctly selects the scheduler-worker group instead of only the unrelated recall/correction/forget/pin group. Six internal old-path string occurrences remain, and only inside byte-exact frozen snapshots (the two new Wave 3 report snapshots and the pre-existing Wave 3 convergence audit snapshot). No compatibility path, redirect, or runtime behavior change is introduced.

### C1C30-001 — remaining early-MVP historical implementation notes

```yaml
cutover_pr: 593
merged_commit: a7669fcb2906202fee8b89c601bf3dfbf28bfece
record_count: 4
cutover_recorded_on: 2026-07-14
disposition: evidence_retained
records:
  - record: MVP-0 pass-through proxy
    recorded_on: 2026-05-20
    source_pr: 4
    source_origin_commit: eab60e55d9c3899ca54be473faed2d8bafff4c60
    source_commit: 5b164e0deb371c9c8de0d3b7c57f38084077e2dc
    old_path: docs/mvp/mvp0_pass_through_proxy.md
    source_blob_sha: 5a98f4066458a34a34ff6e88c4a651ac77b59722
    source_content_sha256: 356e8fb6315ac480f85a7ef0050b8ffa8d3b31f6e5d8500c7219d41f62261d21
    post_source_modification_commits:
      - pr: 5
        origin_commit: 1d5e23ae4d64d6aec1292bf737f5272219ddf5ba
        commit: 5d2e9f0665e9ff840327ae093dc48fdddd6e7dd8
    pre_cutover_blob_sha: 9bd2eb600ae7586a337e58c19bdb868d1c3d1e4f
    pre_cutover_content_sha256: bad628ffc3748fe0ae41c704960eb087b0402ef4ebf905d5542f98929f8e10a2
    new_canonical_path: docs/evidence/implementation/mvp0_pass_through_proxy.md
    exact_source_snapshot: docs/evidence/implementation/mvp0_pass_through_proxy-source.txt
    exact_source_blob_sha: 9bd2eb600ae7586a337e58c19bdb868d1c3d1e4f
    advisory_verification: advisory_blob_and_sha256_confirmed_correct; advisory_source_commit_incomplete_omitted_pr5_modification
  - record: MVP-1 runtime diagnostics smoke
    recorded_on: 2026-05-20
    source_pr: 10
    source_origin_commit: 4a97a4dc730c718d06e567ccfaf47db2d278357d
    source_commit: 2890b1d13e7a937611e4ca467f761738d2a0082c
    old_path: docs/mvp/mvp1_runtime_diagnostics_smoke.md
    source_blob_sha: b5d2f6ff805832f71d89393d06d91c65add3e81c
    source_content_sha256: c9184d7a3b12c84b6aa3615a976118b9f6fd3c1d739eed1a453631898184acaf
    post_source_modification_commits: []
    pre_cutover_blob_sha: b5d2f6ff805832f71d89393d06d91c65add3e81c
    pre_cutover_content_sha256: c9184d7a3b12c84b6aa3615a976118b9f6fd3c1d739eed1a453631898184acaf
    new_canonical_path: docs/evidence/implementation/mvp1_runtime_diagnostics_smoke.md
    exact_source_snapshot: docs/evidence/implementation/mvp1_runtime_diagnostics_smoke-source.txt
    exact_source_blob_sha: b5d2f6ff805832f71d89393d06d91c65add3e81c
    advisory_verification: advisory_blob_sha256_source_commit_and_date_all_confirmed_correct
  - record: MVP-2 memory-light apply
    recorded_on: 2026-05-21
    source_pr: 21
    source_origin_commit: 793dbfa49798a4531039bdd6193c51db191d529d
    source_commit: ed5119b5fe3a07cd395ebd0a4cadaca7945e9599
    old_path: docs/mvp/mvp2_memory_light_apply.md
    source_blob_sha: 774819182af6268dc95c9ca5a61571890085c414
    source_content_sha256: b420a9c6c7b2f221996d6b30c1739fe4de62d0b070f791b998bd48728e434c6c
    post_source_modification_commits: []
    pre_cutover_blob_sha: 774819182af6268dc95c9ca5a61571890085c414
    pre_cutover_content_sha256: b420a9c6c7b2f221996d6b30c1739fe4de62d0b070f791b998bd48728e434c6c
    new_canonical_path: docs/evidence/implementation/mvp2_memory_light_apply.md
    exact_source_snapshot: docs/evidence/implementation/mvp2_memory_light_apply-source.txt
    exact_source_blob_sha: 774819182af6268dc95c9ca5a61571890085c414
    advisory_verification: advisory_blob_sha256_source_commit_and_date_all_confirmed_correct
  - record: MVP-2 profile file loading
    recorded_on: 2026-05-20
    source_pr: 14
    source_origin_commit: cf995f8f7b5b50b23e17ac92b1d0bd5789e26104
    source_commit: 386d76fbefd21eee59c015c01c2cc0c326da9410
    old_path: docs/mvp/mvp2_profile_file_loading.md
    source_blob_sha: d9569f158764b922a5c99f9c361dbdbf65cf56b3
    source_content_sha256: 089b8ece13ad60e68f953a3a4b5f7299f1642b40623fec66a7e8f21bdf64fac7
    post_source_modification_commits: []
    pre_cutover_blob_sha: d9569f158764b922a5c99f9c361dbdbf65cf56b3
    pre_cutover_content_sha256: 089b8ece13ad60e68f953a3a4b5f7299f1642b40623fec66a7e8f21bdf64fac7
    new_canonical_path: docs/evidence/implementation/mvp2_profile_file_loading.md
    exact_source_snapshot: docs/evidence/implementation/mvp2_profile_file_loading-source.txt
    exact_source_blob_sha: d9569f158764b922a5c99f9c361dbdbf65cf56b3
    advisory_verification: advisory_blob_sha256_source_commit_and_date_all_confirmed_correct
verification:
  old_paths_removed_in_pr_tree: true
  exact_pre_cutover_blobs_reused: true
  canonical_evidence_wrappers_added: 4
  source_head_merge_and_pre_cutover_equal_records: 3
  source_to_pre_cutover_diff_records: 1
  mvp0_delta_is_pr5_offline_install_fallback_documentation: true
  post_source_modification_commits_total: 1
  frozen_preparation_c_baseline_advisory_records_independently_reverified: 4
  advisory_records_confirmed_correct: 3
  advisory_records_corrected: 1
  source_pr_newly_established_not_previously_recorded: 3
  live_dependency_referrer_files_at_frozen_baseline: 1
  live_dependency_link_occurrences_at_frozen_baseline: 3
  live_dependency_referrer_files_updated: 1
  live_dependency_link_occurrences_retargeted: 3
  implementation_evidence_index_files_updated: 1
  new_evidence_index_entries_added: 4
  shared_index_files_updated: 2
  mvp2_memory_light_apply_live_referrers_before_cutover: 0
  implementation_evidence_index_updated: true
  mvp_evidence_index_updated: true
  historical_old_path_string_occurrences_preserved_in_exact_snapshots: 0
  historical_old_path_string_occurrences_preserved_as_migration_identifiers_in_wrappers: 4
  compileall: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  documentation_current_boundary_smoke: passed
  consolidated_smoke_contract: passed
  git_diff_check: passed
  no_canonical_record_selects_unrelated_runtime_group: true
  all_github_actions: passed
  unresolved_review_threads: 0
```

The four canonical records preserve the remaining low-risk early-MVP historical implementation notes (MVP-0 pass-through proxy, MVP-1 runtime diagnostics smoke, MVP-2 memory-light apply, and MVP-2 profile file loading) while explicitly disclaiming current proxy/pipeline, diagnostics-contract, memory/RelayCTX/persistence, and character-workspace/SOUL/profile-resolution authority respectively. Independent re-verification of the frozen Preparation C advisory table found the blob SHA, content SHA-256, source commit, and recorded date correct for three of four records (MVP-1, MVP-2 memory-light apply, MVP-2 profile file loading); the MVP-0 advisory cited only the PR #4 creation commit and omitted a same-day PR #5 follow-up commit that actually produced the pre-cutover blob, so this receipt records both PRs and the resulting single-commit content diff (an offline `--no-build-isolation` install fallback and a direct `python -m relaylm.app` run fallback). None of the four advisory records had a previously-recorded source PR; this receipt establishes source PR #4/#5, #10, #21, and #14 respectively from merge-commit bodies, none of them guessed. Three literal `docs/mvp/README.md` link occurrences move atomically to their canonical `docs/evidence/implementation/` paths in the same PR that adds four new index entries to `docs/evidence/implementation/README.md`; MVP-2 memory-light apply had zero live references anywhere in the tree before this cutover and remains a newly-indexed, previously-orphaned record. Four internal old-path string occurrences remain, and only as migration identifiers inside the four canonical wrapper bodies (`old path: docs/mvp/...`) — none appear inside the four byte-exact `-source.txt` snapshots. No compatibility path, redirect, or runtime behavior change is introduced.

### C1C31-001 — MVP-2 compile/apply compatibility chain

```yaml
cutover_pr: 594
merged_commit: 37140d4beda98562659686faa1b3464296e2d3fa
record_count: 4
cutover_recorded_on: 2026-07-14
disposition: split
records:
  - record: MVP-2 context compiler contract
    recorded_on: 2026-05-20
    source_pr: 13
    source_origin_commit: 9e22a95ce1cb7977e9da2829b3a38045789093d8
    source_commit: cb2ebc287e6dbe6c85d1285af3584b6484575b63
    old_path: docs/mvp/mvp2_context_compiler_contract.md
    source_blob_sha: 82054c9ab18c2205ef0b2e82fec48a92083b4257
    source_content_sha256: 0e38b8a5515b26f4ee0f211487d4a859f7b7a5a3fb2ebcbd9a87fdfc4eac9128
    post_source_modification_commits: []
    pre_cutover_blob_sha: 82054c9ab18c2205ef0b2e82fec48a92083b4257
    pre_cutover_content_sha256: 0e38b8a5515b26f4ee0f211487d4a859f7b7a5a3fb2ebcbd9a87fdfc4eac9128
    new_canonical_path: docs/evidence/implementation/mvp2_context_compiler_contract.md
    exact_source_snapshot: docs/evidence/implementation/mvp2_context_compiler_contract-source.txt
    exact_source_blob_sha: 82054c9ab18c2205ef0b2e82fec48a92083b4257
    advisory_verification: advisory_blob_sha256_confirmed_correct
    block_disposition:
      primitives_and_ordering_rule: current_already_covered
      concrete_room_anchor_placeholder: superseded_or_incorrect_for_current_retired_do_not_absorb
      smoke_and_out_of_scope: procedure_or_smoke_history_and_historical_evidence
    absorption_required: false
    live_referrers_before_cutover: 0
  - record: MVP-2 gated compile decision
    recorded_on: 2026-05-21
    source_pr: 20
    source_origin_commit: 4a720954d1fed12dbbe0f6b2ba69b25082511ddd
    source_commit: b9ccba293a780c4da3c89b61b53c6f7e739290c8
    old_path: docs/mvp/mvp2_gated_compile_decision.md
    source_blob_sha: 6da4b16095413191368ea2a75333a094d550977b
    source_content_sha256: 0b7437684b4e64c265ef3227cea5f075acc0440eaa1f20be4bbe979e63f76809
    post_source_modification_commits: []
    pre_cutover_blob_sha: 6da4b16095413191368ea2a75333a094d550977b
    pre_cutover_content_sha256: 0b7437684b4e64c265ef3227cea5f075acc0440eaa1f20be4bbe979e63f76809
    new_canonical_path: docs/evidence/implementation/mvp2_gated_compile_decision.md
    exact_source_snapshot: docs/evidence/implementation/mvp2_gated_compile_decision-source.txt
    exact_source_blob_sha: 6da4b16095413191368ea2a75333a094d550977b
    advisory_verification: advisory_blob_sha256_confirmed_correct
    block_disposition:
      gate_rule_and_decision_object: current_already_covered
      out_of_scope_list: superseded_or_incorrect_for_current
      run_section: procedure_or_smoke_history
    absorption_required: false
    live_referrers_before_cutover: 0
  - record: MVP-2 runtime memory-light apply
    recorded_on: 2026-05-21
    source_pr: 22
    source_origin_commit: e5b6a247134be4e52cc47c223e44af3a35c8896e
    source_commit: 71385a5f2ccebbe89e81b9369f5c5abce6a98114
    old_path: docs/mvp/mvp2_runtime_memory_light_apply.md
    source_blob_sha: 63a3edfaaa7e6177f61c69611cdc82c505dbbf35
    source_content_sha256: f3a3eec0fadd4c729254378b8c76ccdf00d3887f249fa8ded7960afc4eaed818
    post_source_modification_commits: []
    pre_cutover_blob_sha: 63a3edfaaa7e6177f61c69611cdc82c505dbbf35
    pre_cutover_content_sha256: f3a3eec0fadd4c729254378b8c76ccdf00d3887f249fa8ded7960afc4eaed818
    new_canonical_path: docs/evidence/implementation/mvp2_runtime_memory_light_apply.md
    exact_source_snapshot: docs/evidence/implementation/mvp2_runtime_memory_light_apply-source.txt
    exact_source_blob_sha: 63a3edfaaa7e6177f61c69611cdc82c505dbbf35
    advisory_verification: advisory_blob_sha256_confirmed_correct
    distinct_source_pr_from_sibling_mvp2_memory_light_apply_pr21: true
    block_disposition:
      runtime_wiring_behavior_bullets: current_already_covered
      safety_boundary_and_run_section: current_already_covered_and_procedure_or_smoke_history
    absorption_required: false
    live_referrers_before_cutover: 0
  - record: MVP-2 incoming system prompt fallback
    recorded_on: 2026-05-21
    source_pr: 17
    source_origin_commit: accdeab36ab718feb7781c2bbd09b12cf6465544
    source_commit: ac963e98eb25b8d2f9402d7eb48b78d8c84f79a5
    old_path: docs/mvp/mvp2_incoming_system_fallback.md
    source_blob_sha: 2662d59a3b6364610021a019c36ef3585ba2c684
    source_content_sha256: e2277a6b809b4a89ea139c7df2dd42f92b791e7ece8ea00605195e9dfb98f238
    post_source_modification_commits:
      - pr: 246
        commit: 3e502b710b794e83b45b0e66e6039c773e50c680
        recorded_on: 2026-06-12
        change: expanded_50_to_125_lines_added_current_authority_reinterpretation_developer_role_text_part_normalization_xml_escaping_relaysoul_non_mutation
    pre_cutover_blob_sha: f229f538222bd72e9b1fa4a0290d2320491c9ec0
    pre_cutover_content_sha256: efe00f859479bc17a09c220afb2cabcdeb42cda6fd41594ab19c90992414dde0
    new_canonical_path: docs/evidence/implementation/mvp2_incoming_system_fallback.md
    exact_source_snapshot: docs/evidence/implementation/mvp2_incoming_system_fallback-source.txt
    exact_source_snapshot_matches: pre_cutover_blob_not_source_commit_blob
    exact_source_blob_sha: f229f538222bd72e9b1fa4a0290d2320491c9ec0
    advisory_verification: advisory_blob_sha256_confirmed_correct_for_pre_cutover_state_only
    source_commit_and_pre_cutover_blob_are_different_versions_not_paired_as_same: true
    previously_excluded_from_c1c3_001_pending_split_decision: true
    block_disposition:
      system_developer_extraction: historical_evidence_plus_current_already_covered_policy_level
      text_part_normalization_whitespace_non_text_handling: current_absorb_required
      compiled_render_order: current_absorb_required
      xml_escaping_and_spoof_probe: current_absorb_required
      raw_instruction_non_authority: current_already_covered
      relayscn_scene_role_interpretation: current_already_covered
      relaysoul_non_mutation: current_already_covered
      managed_route_fallback_behavior: current_absorb_required_same_as_compiled_render_order
      current_vs_target_only: current_confirmed_live_not_aspirational
    absorption_required: true
    absorption_destination: docs/contracts/context_compiler_contract.md#current-systemdeveloper-compatibility-helper
    absorbed_blocks:
      - block: text_part_normalization_whitespace_non_text_handling
        source_digest_sha256: 25ff74e11f1122d3a53b0d296d7c03a13627c7899aa23999d8b4bae058b69298
        destination_digest_sha256: 25ff74e11f1122d3a53b0d296d7c03a13627c7899aa23999d8b4bae058b69298
        digest_match: true
      - block: compiled_render_order
        source_digest_sha256: 44de90416ffa1667c3d4d53634c72d071916c0e6477f30c4d2a2d76121e9b089
        destination_digest_sha256: 44de90416ffa1667c3d4d53634c72d071916c0e6477f30c4d2a2d76121e9b089
        digest_match: true
      - block: xml_escaping_and_spoof_probe
        source_digest_sha256: 3ed46ebbf6367c302adb02e714704f1218ec07b43ee7c1d87aadde618db0d7db
        destination_digest_sha256: 3ed46ebbf6367c302adb02e714704f1218ec07b43ee7c1d87aadde618db0d7db
        digest_match: true
    live_referrers_before_cutover: 0
    frozen_receipt_historical_mention_c1c3_001: retained_unchanged_historical_only
verification:
  old_paths_removed_in_pr_tree: true
  exact_pre_cutover_blobs_reused: true
  canonical_evidence_wrappers_added: 4
  source_head_merge_and_pre_cutover_equal_records: 3
  source_to_pre_cutover_diff_records: 1
  incoming_system_fallback_delta_is_pr246_current_authority_reinterpretation: true
  post_source_modification_commits_total: 1
  advisory_records_independently_reverified: 4
  advisory_records_confirmed_correct: 4
  advisory_records_corrected: 0
  source_pr_newly_established_not_previously_recorded: 4
  live_dependency_referrer_files_at_frozen_baseline: 0
  live_dependency_link_occurrences_at_frozen_baseline: 0
  live_dependency_referrer_files_updated: 0
  live_dependency_link_occurrences_retargeted: 0
  implementation_evidence_index_files_updated: 1
  new_evidence_index_entries_added: 4
  mvp_index_entries_added: 4
  shared_index_files_updated: 2
  all_four_records_had_zero_live_referrers_before_cutover: true
  implementation_evidence_index_updated: true
  mvp_evidence_index_updated: true
  absorbed_normative_blocks: 3
  absorbed_normative_blocks_exact_digest_match: 3
  absorption_destination_file: docs/contracts/context_compiler_contract.md
  absorption_destination_is_current_authority_edit: true
  no_absorption_required_for_three_of_four_records: true
  not_absorbed_already_covered_rules: 3
  historical_old_path_string_occurrences_preserved_in_exact_snapshots: 0
  historical_old_path_string_occurrences_preserved_as_migration_identifiers_in_wrappers: 4
  historical_old_path_string_occurrences_preserved_in_prior_frozen_receipt_entry: 1
  compileall: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  documentation_current_boundary_smoke: passed
  consolidated_smoke_contract: passed
  context_compiler_smoke: passed
  compile_gate_smoke: passed
  memory_light_apply_smoke: passed
  system_fallback_smoke: passed
  git_diff_check: passed
  no_canonical_record_selects_unrelated_runtime_group: true
  all_github_actions: passed
  codex_review: unavailable_usage_limit_reached
  unresolved_review_threads: 0
```

The four canonical records preserve the MVP-2 compile/apply compatibility chain (context block primitives/order, compile-apply gate, runtime memory-light payload apply, and incoming system/developer compatibility handling). Three records (context compiler contract, gated compile decision, runtime memory-light apply) are pure `evidence_retained`: every still-valid rule in each source is already owned, more completely, by current contract/architecture documents and unchanged code, and each had zero live referrers anywhere in the tree before this cutover. The context-compiler-contract record's concrete stable-prefix block list names the now-retired `room_anchor` placeholder (superseded by `relationship_anchor`); this is preserved only as history and explicitly not reintroduced as current. The fourth record (incoming system prompt fallback) required a `split` disposition, matching the pending-split note already recorded in the frozen C1C3-001 entry: its source commit (PR #17, 50 lines) and its pre-cutover blob (post PR #246, 125 lines) are different revisions and are not paired as the same version; three still-valid, currently-implemented rules (text-part-array normalization with whitespace preservation and non-text-part suppression, the compiled render order, and the concrete XML-escaping mechanism with its spoof-probe example) had no current-authority owner anywhere in the documentation tree and were absorbed verbatim into a new `### Current system/developer compatibility helper` subsection of the Context Compiler Contract in this same PR, with source and destination normalized SHA-256 digests recorded and confirmed to match exactly. Three other source rules (raw-instruction non-authority, RelaySCN scene-role interpretation, RelaySOUL non-mutation) were already covered, more rigorously, by the Client Instruction Authority Contract and were not duplicated. All four advisory pre-cutover blob/SHA-256 values from Preparation C were independently reverified and confirmed correct; none had a previously-recorded source PR, and this receipt establishes source PR #13, #20, #22, and #17 (plus the #246 post-source modification for the fourth) from merge-commit bodies, none guessed. None of the four records had any live referrer anywhere in the tree before this cutover (unlike several 1C-30 records), so no link retargeting was required; two new index entries per record were added instead, to `docs/evidence/implementation/README.md` and `docs/mvp/README.md`. Four internal old-path string occurrences remain, and only as migration identifiers inside the four canonical wrapper bodies (`old path: docs/mvp/...`); one additional historical old-path string occurrence remains unchanged inside the prior, already-frozen C1C3-001 entry. None appear inside the four byte-exact `-source.txt` snapshots. No compatibility path, redirect, or runtime behavior change is introduced. All 24 triggered GitHub Actions check runs on the final remote head (`6d0cb65819a1f6514c4095a946ea6b601ea85665`) completed as `success` or a correctly-skipped consolidated-smoke group; none of the new canonical evidence paths matched an unrelated RelayMEM/runtime/UI consolidated group. The automated Codex reviewer reported its usage limit was reached and did not produce a review; there are zero unresolved review threads.

### C1C32-001 — RelayCTX short-term runtime chain

```yaml
cutover_pr: 595
merged_commit: c5294353f3872593d67697997ea48ab7f05a0b94
record_count: 4
cutover_recorded_on: 2026-07-14
disposition: split
records:
  - record: MVP-40 RelayCTX short-term extraction dry-run
    recorded_on: 2026-06-06
    source_pr: 234
    source_origin_commit: a3335b6681ef8b14f108469942882f1cbb50f734
    source_commit: d794ad3859b5c48447f5073bc21913a33aaa6dac
    old_path: docs/mvp/mvp40_relayctx_short_term_extraction_dry_run.md
    source_blob_sha: 1ffcaa98d5c527c8f12f0ec8d56a4224c12c9564
    source_content_sha256: 19084122d521604d0092ead59f79ac4b1a95a174e0e4efe18e8132545a8de804
    post_source_modification_commits: []
    pre_cutover_blob_sha: 1ffcaa98d5c527c8f12f0ec8d56a4224c12c9564
    pre_cutover_content_sha256: 19084122d521604d0092ead59f79ac4b1a95a174e0e4efe18e8132545a8de804
    new_canonical_path: docs/evidence/implementation/mvp40_relayctx_short_term_extraction_dry_run.md
    exact_source_snapshot: docs/evidence/implementation/mvp40_relayctx_short_term_extraction_dry_run-source.txt
    exact_source_blob_sha: 1ffcaa98d5c527c8f12f0ec8d56a4224c12c9564
    advisory_verification: advisory_blob_sha256_confirmed_correct
    block_disposition:
      title_and_intro: historical_evidence
      safety_boundary_bullets: current_already_covered_by_context_packing_design_content_free_surfaces
      artifact_schema_fields: historical_evidence_plus_current_absorb_required_config_flag_already_covered
      classification_determinism_statement: current_absorb_required_code_derived_generalized_across_chain
    absorption_required: true
    absorption_destination: docs/contracts/relayctx_short_term_runtime_contract.md
    live_referrers_before_cutover: 1
  - record: MVP-41 RelayCTX short-term block assembly dry-run
    recorded_on: 2026-06-06
    source_pr: 235
    source_origin_commit: 40f98c532a535962068fdd28cc9d01fd065d5ff6
    source_commit: 2debea2f3fd50af6015807efa8e490898d9b558f
    old_path: docs/mvp/mvp41_relayctx_short_term_block_assembly_dry_run.md
    source_blob_sha: 8d83bc2bfd424dda09a7b85ec381b597343e0c4d
    source_content_sha256: 7c1ece92f8e5e39b569fb6b3147e6f1600e3ef294adf395cefc2d67947ebc03d
    post_source_modification_commits: []
    pre_cutover_blob_sha: 8d83bc2bfd424dda09a7b85ec381b597343e0c4d
    pre_cutover_content_sha256: 7c1ece92f8e5e39b569fb6b3147e6f1600e3ef294adf395cefc2d67947ebc03d
    new_canonical_path: docs/evidence/implementation/mvp41_relayctx_short_term_block_assembly_dry_run.md
    exact_source_snapshot: docs/evidence/implementation/mvp41_relayctx_short_term_block_assembly_dry_run-source.txt
    exact_source_blob_sha: 8d83bc2bfd424dda09a7b85ec381b597343e0c4d
    advisory_verification: advisory_blob_sha256_confirmed_correct
    block_disposition:
      scope_bullets: current_absorb_required_verbatim
      artifact_fields: current_absorb_required_code_derived_token_budget_hint_constant_nuance
      priority_order_list: current_absorb_required_verbatim_not_superseded_still_consumed_by_mvp42
      forward_looking_closing_line: procedure_or_smoke_history
    absorption_required: true
    absorption_destination: docs/contracts/relayctx_short_term_runtime_contract.md
    absorbed_blocks:
      - block: scope_bullets
        source_digest_sha256: 7f1f62c60e0ac580bee9393de1db31e83197769d772577a843baa1762ca43c9f
        destination_digest_sha256: 7f1f62c60e0ac580bee9393de1db31e83197769d772577a843baa1762ca43c9f
        digest_match: true
      - block: priority_order_list
        source_digest_sha256: cfdd12f4f5e276c06172ce91231a6cc8c821d4b79cab020e1ba492735904278d
        destination_digest_sha256: cfdd12f4f5e276c06172ce91231a6cc8c821d4b79cab020e1ba492735904278d
        digest_match: true
    live_referrers_before_cutover: 1
  - record: MVP-42 RelayCTX short-term runtime injection preflight
    recorded_on: 2026-06-06
    source_pr: 236
    source_origin_commit: 8de6227ed743a13817831bf141220ff9b30b26c4
    source_commit: 52893c76bc311d9586d31095ab5c8c98a6e145e4
    old_path: docs/mvp/mvp42_relayctx_short_term_runtime_injection_preflight.md
    source_blob_sha: 9594f8b182b4691b0bcf048abd68b68cfaec5e74
    source_content_sha256: b9d7267bcf76634175b003652aa55d82dff8c37dc3f5a2d78c5d8c31fe1f2c38
    post_source_modification_commits: []
    pre_cutover_blob_sha: 9594f8b182b4691b0bcf048abd68b68cfaec5e74
    pre_cutover_content_sha256: b9d7267bcf76634175b003652aa55d82dff8c37dc3f5a2d78c5d8c31fe1f2c38
    new_canonical_path: docs/evidence/implementation/mvp42_relayctx_short_term_runtime_injection_preflight.md
    exact_source_snapshot: docs/evidence/implementation/mvp42_relayctx_short_term_runtime_injection_preflight-source.txt
    exact_source_blob_sha: 9594f8b182b4691b0bcf048abd68b68cfaec5e74
    advisory_verification: advisory_blob_sha256_confirmed_correct
    block_disposition:
      title_and_intro: historical_evidence
      scope_bullets: current_absorb_required_code_derived_scoped_to_preflight_artifact_only_since_mvp43_apply_now_exists
      artifact_section: current_absorb_required_verbatim
      forward_path_paragraph: procedure_or_smoke_history_prediction_since_fulfilled
    absorption_required: true
    absorption_destination: docs/contracts/relayctx_short_term_runtime_contract.md
    absorbed_blocks:
      - block: artifact_section
        source_digest_sha256: 35df4563d5c09f4655c479e21a8807634fae27b98c780dbe3f61ff1e59b8232a
        destination_digest_sha256: 35df4563d5c09f4655c479e21a8807634fae27b98c780dbe3f61ff1e59b8232a
        digest_match: true
    live_referrers_before_cutover: 1
  - record: MVP-43 RelayCTX short-term runtime injection apply gate
    recorded_on: 2026-06-06
    source_pr: 237
    source_origin_commit: 8eabaf1c46fbc46b1628e957fe949a40f8f80f9f
    source_commit: d76e8e623dddd8b437ee76597014c354bbce17d6
    old_path: docs/mvp/mvp43_relayctx_short_term_runtime_injection_apply_gate.md
    source_blob_sha: dfce2f4a7cde838749791e8ac91cc213a2a0eb55
    source_content_sha256: 7227d7438c8fa49b13fa0c3854676800636fd95169248c747752a27bfed30850
    post_source_modification_commits:
      - commit: e39f846fa8e015b4f2810f96b4b59283153a2aa2
        recorded_on: 2026-06-11
        change: reworded_non_goals_clause_delete_compress_reconstruct_openwebui_messages_to_alter_openwebui_message_history_and_moved_to_current_path
      - commit: 90025c9645c06ee5aa87955cab9a899064b8b2af
        recorded_on: 2026-06-11
        change: removed_legacy_old_path
    pre_cutover_blob_sha: 628e58946a34e277fa3a07bed7219dd2ce57b70f
    pre_cutover_content_sha256: acc1f209e667acd3e6526c8ce1464b2d4101371e75e73e1a571f2f470da00c39
    new_canonical_path: docs/evidence/implementation/mvp43_relayctx_short_term_runtime_injection_apply_gate.md
    exact_source_snapshot: docs/evidence/implementation/mvp43_relayctx_short_term_runtime_injection_apply_gate-source.txt
    exact_source_snapshot_matches: pre_cutover_blob_not_source_commit_blob
    exact_source_blob_sha: 628e58946a34e277fa3a07bed7219dd2ce57b70f
    advisory_verification: advisory_blob_sha256_confirmed_correct_for_pre_cutover_state_only
    source_commit_and_pre_cutover_blob_are_different_versions_not_paired_as_same: true
    block_disposition:
      title_and_intro: current_already_covered_vague_framing_only
      safety_gate_flag_names_and_defaults: current_already_covered_by_config_py_plus_absorbed_with_third_field
      gate_condition_paragraph_4_conditions: current_absorb_required_code_derived_rewrite_12_apply_tier_5_preflight_tier_13_distinct_union_confirmed_incomplete_as_warned
      inserted_content_claims: current_already_covered_plus_current_absorb_required_structural_detail_addition
      non_goals_section: current_absorb_required_verbatim_core_clause
      mvp44_forward_looking_line: procedure_or_smoke_history
      ctx_repack_ordering_bug_history: not_in_source_cross_linked_to_project_status_and_pipeline_responsibility_design_not_duplicated
    absorption_required: true
    absorption_destination: docs/contracts/relayctx_short_term_runtime_contract.md
    absorbed_blocks:
      - block: non_goals_core_clause
        note: forward_looking_mvp44_roadmap_sentence_intentionally_excluded_as_procedure_or_smoke_history
        source_digest_sha256: 16e5c9c18adaad3f2c750add44d5141147e98ee77448b338deac42c26011f508
        destination_digest_sha256: 16e5c9c18adaad3f2c750add44d5141147e98ee77448b338deac42c26011f508
        digest_match: true
    code_derived_additions:
      - block: full_blocked_reason_taxonomy
        delta: replaced_4_condition_prose_with_12_apply_tier_and_5_preflight_tier_reason_strings_13_distinct_union_no_verbatim_source_exists
        validation: scripts/relaylm_relayctx_short_term_runtime_injection_apply_smoke.py, scripts/relaylm_ctx_repack_final_gate_smoke.py
      - block: config_flags_table
        delta: added_relayctx_short_term_runtime_injection_token_budget_and_config_memory_chars_per_token_dependency_not_named_in_old_doc
        validation: relaylm/config.py, relaylm/relayctx_repack.py
      - block: insertion_mechanics
        delta: added_exact_message_role_position_and_content_structure_never_stated_in_old_doc
        validation: scripts/relaylm_relayctx_short_term_runtime_injection_apply_smoke.py
    live_referrers_before_cutover: 1
verification:
  old_paths_removed_in_pr_tree: true
  exact_pre_cutover_blobs_reused: true
  canonical_evidence_wrappers_added: 4
  source_head_merge_and_pre_cutover_equal_records: 3
  source_to_pre_cutover_diff_records: 1
  apply_gate_delta_is_e39f846_non_goals_clause_reword_plus_path_move: true
  post_source_modification_commits_total: 2
  advisory_records_independently_reverified: 4
  advisory_records_confirmed_correct: 4
  advisory_records_corrected: 0
  source_pr_newly_established_not_previously_recorded: 4
  live_dependency_referrer_files_at_frozen_baseline: 1
  live_dependency_link_occurrences_at_frozen_baseline: 4
  live_dependency_referrer_files_updated: 1
  live_dependency_link_occurrences_retargeted: 4
  implementation_evidence_index_files_updated: 1
  new_evidence_index_entries_added: 4
  mvp_index_entries_updated: 4
  contracts_index_files_updated: 1
  new_contract_files_added: 1
  shared_index_files_updated: 3
  implementation_evidence_index_updated: true
  mvp_evidence_index_updated: true
  contracts_index_updated: true
  new_canonical_contract_created: true
  new_canonical_contract_path: docs/contracts/relayctx_short_term_runtime_contract.md
  absorbed_verbatim_blocks: 4
  absorbed_verbatim_blocks_exact_digest_match: 4
  code_derived_absorbed_blocks: 7
  absorption_destination_file: docs/contracts/relayctx_short_term_runtime_contract.md
  absorption_destination_is_new_current_authority_file: true
  historical_old_path_string_occurrences_preserved_in_exact_snapshots: 0
  historical_old_path_string_occurrences_preserved_as_migration_identifiers_in_wrappers: 4
  compileall: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  documentation_current_boundary_smoke: passed
  relayctx_short_term_runtime_contract_smoke: passed
  repository_wide_stage_order_verified: relaymem_retrieval_to_relaymem_runtime_injection_to_relayctx_extraction_to_assembly_to_preflight_to_apply_to_token_budget_truncation
  internal_relayctx_artifact_dependency_verified: extraction_to_assembly_to_preflight_to_apply
  disabled_builder_none_semantics_verified: true
  stage4_forwarded_payload_input_verified: true
  apply_tier_blocked_reason_count: 12
  preflight_tier_blocked_reason_count: 5
  blocked_reason_distinct_union_count: 13
  payload_mutation_disabled_reachable_apply_condition: apply_enabled_true_and_dry_run_only_true_with_blocked_reason
  consolidated_smoke_contract: passed
  relayctx_short_term_extraction_dry_run_smoke: pre_existing_local_fixture_failure_verified_against_base
  relayctx_short_term_block_assembly_dry_run_smoke: pre_existing_local_fixture_failure_verified_against_base
  relayctx_short_term_runtime_injection_preflight_smoke: pre_existing_local_fixture_failure_verified_against_base
  relayctx_short_term_runtime_injection_apply_smoke: pre_existing_local_fixture_failure_verified_against_base
  ctx_repack_final_gate_smoke: passed
  openwebui_lmstudio_config_smoke: passed
  git_diff_check: passed
  no_canonical_record_selects_unrelated_runtime_group: true
  all_github_actions: passed
  codex_review: unavailable_usage_limit_reached
  unresolved_review_threads: 0
```

The four canonical records preserve the RelayCTX short-term runtime chain (extraction dry-run, block assembly dry-run, runtime injection preflight, and gated apply), an implemented chronological chain confirmed still live in `relaylm/diagnostics.py`, `relaylm/relayctx_repack.py`, and `relaylm/managed_chat_runtime.py`. All four advisory pre-cutover blob/SHA-256 values were independently reverified and confirmed correct; the first three records had zero content drift since their source PRs (#234, #235, #236, all merged 2026-06-06), with only a pure path-rename intervening. The fourth record (apply gate, PR #237) is the one true `split`-shaped record in this batch: its source-PR blob and its pre-cutover blob are different versions and are not paired as the same version — a same-day-plus-five-days commit (`e39f846fa8e015b4f2810f96b4b59283153a2aa2`) reworded one non-goals clause before a companion commit removed the legacy path, and this receipt records both the source and the pre-cutover content separately, matching the corrected provenance pattern established in Cutovers 1C-30 and 1C-31. All four records had exactly one live referrer before this cutover (the shared `docs/mvp/README.md` "Retained focused historical notes" index), retargeted in this same PR to the new canonical evidence paths.

Because the audit found the current four-stage contract fragmented across `docs/config_schema.md` (flag defaults only), `docs/architecture/pipeline_responsibility_design.md` (stage ordering only), and `docs/contracts/context_compiler_contract.md` (conceptual "RelayCTX working state" only, with a stale, unreconciled target `ContextBlock` field-name example), a new canonical contract was created at `docs/contracts/relayctx_short_term_runtime_contract.md`. Four blocks were transferred byte-verbatim into it with matching normalized source/destination SHA-256 digests (MVP-41's scope bullets and priority-order list, MVP-42's artifact-section paragraph, and MVP-43's non-goals core clause with its forward-looking MVP-44 roadmap sentence intentionally excluded as procedure/smoke history, not current authority). Seven further blocks required a code-derived rewrite rather than verbatim transfer because current code has evolved or the old text under-specified current behavior: MVP-40's classification-determinism guarantee was generalized from a single-stage claim to the whole chain; MVP-41's artifact section gained a code-derived note that its token-budget hint is a hardcoded constant, not config-driven; MVP-42's non-mutation scope claim was narrowed to the preflight artifact only, since MVP-43's apply path (which postdates MVP-42) can now mutate the backend payload when explicitly enabled; and MVP-43 required a full code-derived rewrite of its blocked-reason taxonomy (13 distinct reasons across two tiers, replacing the old 4-condition prose list, exactly as the task brief warned was incomplete), its config-flag table (adding the previously-unnamed `relayctx_short_term_runtime_injection_token_budget` key and its `config.memory.chars_per_token` dependency), and its insertion mechanics (exact message role, position, and content structure, none of which the old doc stated). The existing stage-ordering rule in `docs/architecture/pipeline_responsibility_design.md` §9 is cross-linked, not duplicated. No compatibility path, redirect, or runtime behavior change is introduced. Final review corrected the repository-wide order to RelayMEM retrieval -> RelayMEM runtime CTX/snippet injection -> RelayCTX extraction -> assembly -> preflight -> apply -> token-budget truncation, while retaining extraction -> assembly -> preflight -> apply as the internal RelayCTX artifact dependency. The corrected default-off artifact-presence rules, Stage 4 forwarded-payload input, 12 apply-tier reasons, 5 preflight-tier reasons, 13-name distinct union, and reachable payload_mutation_disabled condition are pinned by scripts/relaylm_relayctx_short_term_runtime_contract_smoke.py. All 14 triggered GitHub Actions workflows on correction head 7298526f36c5ddc59db0b6de028679000b88ed36 completed successfully; Codex review was unavailable because the usage limit was reached, and there were zero unresolved review threads.

### C1C33-001 — RelayINT quick-clarification chain and PipelineNodeResult scaffold

```yaml
cutover_pr: pending
merged_commit: pending
record_count: 4
cutover_recorded_on: 2026-07-14
disposition: split
records:
  - record: MVP-45 RelayINT fast path dry-run
    recorded_on: 2026-06-07
    source_pr: 239
    source_origin_commit: 0d44478b68ca1e61d553120eb4cecc43c79cc836
    source_commit: 8e821502983fec3046000855af518e0b4541e549
    old_path: docs/mvp/mvp45_relayint_fast_path_dry_run.md
    original_old_path: docs/mvp45_summary.md
    source_blob_sha: dd861779fa995405745873c7b03372a4e1549fb4
    source_content_sha256: 471df4dece5469b147a22747060b65424407f2960044df6a7f851cd69843b0fb
    post_source_modification_commits:
      - commit: a044b42cb01be024bd2efe22a6446409bd067df1
        recorded_on: 2026-06-11
        change: pure_path_rename_no_content_change
      - commit: dd23f437ccede1a1aee22e1c1afb148fea9fcccc
        recorded_on: 2026-06-11
        change: removed_legacy_old_path_docs_mvp45_summary_md
    pre_cutover_blob_sha: dd861779fa995405745873c7b03372a4e1549fb4
    pre_cutover_content_sha256: 471df4dece5469b147a22747060b65424407f2960044df6a7f851cd69843b0fb
    new_canonical_path: docs/evidence/implementation/mvp45_relayint_fast_path_dry_run.md
    exact_source_snapshot: docs/evidence/implementation/mvp45_relayint_fast_path_dry_run-source.txt
    exact_source_blob_sha: dd861779fa995405745873c7b03372a4e1549fb4
    advisory_verification: advisory_blob_sha256_confirmed_correct
    block_disposition:
      completed_scope: current_already_covered_by_relayint_mvp_design_and_new_runtime_contract
      design_intent: current_absorb_required_acg4_relocation_not_previously_documented
      runtime_safety_bullets: current_already_covered
      main_validation: procedure_or_smoke_history
      next_phase: superseded_or_incorrect_for_current_mvp46_47_and_pm_d6_already_shipped
    absorption_required: true
    absorption_destination: docs/contracts/relayint_quick_clarification_runtime_contract.md
    live_referrers_before_cutover: 1
  - record: MVP-46 RelayINT quick clarification preflight
    recorded_on: 2026-06-07
    source_pr: 240
    source_origin_commit: 3c425dbc2f14f7ee943e73608f3f41c95a040fb6
    source_commit: 837ef24e53a945fbf3bd380d32e34ec3973de2c0
    old_path: docs/mvp/mvp46_relayint_quick_clarification_preflight.md
    original_old_path: docs/mvp46_summary.md
    source_blob_sha: 95c1302b91e7c80557017da82cd60d69ecb1da51
    source_content_sha256: 00f5a5eadc363c2bfe37d006222bf7672454982a8ab99c88b1b4548d8f284de8
    post_source_modification_commits:
      - commit: 10f1717e7af26e9bed0d1dbeaee59cb192641002
        recorded_on: 2026-06-11
        change: pure_path_rename_no_content_change
      - commit: 05fe270b3b352636e4943eab7574b1e318f22417
        recorded_on: 2026-06-11
        change: removed_legacy_old_path_docs_mvp46_summary_md
    pre_cutover_blob_sha: 95c1302b91e7c80557017da82cd60d69ecb1da51
    pre_cutover_content_sha256: 00f5a5eadc363c2bfe37d006222bf7672454982a8ab99c88b1b4548d8f284de8
    new_canonical_path: docs/evidence/implementation/mvp46_relayint_quick_clarification_preflight.md
    exact_source_snapshot: docs/evidence/implementation/mvp46_relayint_quick_clarification_preflight-source.txt
    exact_source_blob_sha: 95c1302b91e7c80557017da82cd60d69ecb1da51
    advisory_verification: advisory_blob_sha256_confirmed_correct
    block_disposition:
      completed_scope: current_already_covered
      design_intent: current_already_covered_content_free_field_list_matches_code
      runtime_safety_bullets: current_already_covered
      main_validation: procedure_or_smoke_history_plus_two_later_scene_gate_assertions_not_in_source
      next_phase: current_already_covered_by_different_doc_mvp47_shipped_plan_only_not_user_visible
    absorption_required: true
    absorption_destination: docs/contracts/relayint_quick_clarification_runtime_contract.md
    live_referrers_before_cutover: 1
  - record: MVP-47 RelayINT quick clarification apply plan
    recorded_on: 2026-06-11
    source_pr: 241
    source_origin_commit: 24af958af4eb91c6e6fe50b15cde903d46e153e0
    source_commit: 24af958af4eb91c6e6fe50b15cde903d46e153e0
    source_merge_strategy: squash_merge_source_and_origin_commit_identical
    old_path: docs/mvp/mvp47_relayint_quick_clarification_apply_plan.md
    original_old_path: docs/mvp47_summary.md
    source_blob_sha: 251684f549d2b4bbf3b2e8b9fe436d38868c40e3
    source_content_sha256: f883722043526c5f47dd86dba13be693e2f179208389fb6fbc29317cd99b072d
    post_source_modification_commits:
      - commit: a5a8907408f0be9fd5a2d56c2c91875527487b6f
        recorded_on: 2026-06-11
        change: pure_path_rename_no_content_change
      - commit: 50817c8f5d7e1f18efb6ca7dee3966948e195d1a
        recorded_on: 2026-06-11
        change: removed_legacy_old_path_docs_mvp47_summary_md
    pre_cutover_blob_sha: 251684f549d2b4bbf3b2e8b9fe436d38868c40e3
    pre_cutover_content_sha256: f883722043526c5f47dd86dba13be693e2f179208389fb6fbc29317cd99b072d
    new_canonical_path: docs/evidence/implementation/mvp47_relayint_quick_clarification_apply_plan.md
    exact_source_snapshot: docs/evidence/implementation/mvp47_relayint_quick_clarification_apply_plan-source.txt
    exact_source_blob_sha: 251684f549d2b4bbf3b2e8b9fe436d38868c40e3
    advisory_verification: advisory_blob_sha256_confirmed_correct
    block_disposition:
      completed_scope: current_already_covered
      design_intent: current_already_covered
      runtime_safety_bullets: current_already_covered_phase4_plan_only_unconditional_in_code
      main_validation: procedure_or_smoke_history
      deferred_to_phase6: current_already_covered_still_deferred_no_mvp49_or_later_apply_shipped
    absorption_required: true
    absorption_destination: docs/contracts/relayint_quick_clarification_runtime_contract.md
    code_derived_additions:
      - block: request_compatibility_gate_full_reason_list
        delta: enumerated_n_token_limit_logprobs_stop_reasons_not_individually_named_in_source
        validation: scripts/relaylm_relayint_quick_clarification_apply_smoke.py
      - block: apply_block_reasons_full_taxonomy
        delta: replaced_prose_summary_with_19_exact_block_reason_strings_from_code
        validation: scripts/relaylm_relayint_quick_clarification_apply_smoke.py
    live_referrers_before_cutover: 1
  - record: MVP-48 pipeline node result scaffold
    recorded_on: 2026-06-12
    source_pr: none
    source_pr_note: direct_push_documentation_commit_not_part_of_any_pull_request
    related_code_pr: 245
    related_code_pr_note: pr_245_diff_does_not_include_this_doc_file_not_treated_as_source
    source_origin_commit: 69cecf1841e54e95d18868559e03686c5e60484f
    source_commit: 69cecf1841e54e95d18868559e03686c5e60484f
    old_path: docs/mvp/mvp48_pipeline_node_result_scaffold.md
    original_old_path: docs/mvp/mvp48_pipeline_node_result_scaffold.md
    source_blob_sha: 4fe7ee9ce200ab84055d0476fc06b0e13893d988
    source_content_sha256: 2233a265198a33bfb2dfd917b78ecb1861c5641b6e597a50403fc1bb67150f3d
    post_source_modification_commits: []
    pre_cutover_blob_sha: 4fe7ee9ce200ab84055d0476fc06b0e13893d988
    pre_cutover_content_sha256: 2233a265198a33bfb2dfd917b78ecb1861c5641b6e597a50403fc1bb67150f3d
    new_canonical_path: docs/evidence/implementation/mvp48_pipeline_node_result_scaffold.md
    exact_source_snapshot: docs/evidence/implementation/mvp48_pipeline_node_result_scaffold-source.txt
    exact_source_blob_sha: 4fe7ee9ce200ab84055d0476fc06b0e13893d988
    advisory_verification: advisory_blob_sha256_confirmed_correct
    block_disposition:
      completed_scope: current_already_covered_plus_superseded_emitter_list
      design_intent: current_already_covered
      runtime_safety_bullets_non_relayref: current_already_covered
      runtime_safety_relayref_compatibility_boundary: superseded_or_incorrect_for_current_by_pm_d6
      main_validation: procedure_or_smoke_history
      phase_completion: historical_evidence
      deferred_work: partially_superseded_relayctx_unpack_phase5_already_shipped
      next_phase: superseded_or_incorrect_for_current_phase5_already_shipped
    absorption_required: true
    absorption_destination: docs/contracts/pipeline_node_result_contract.md
    pm_d6_supersession_confirmed: true
    pm_d6_current_identifiers:
      native_artifact_key: relayint_intent_artifact
      native_schema: relayint.intent.v1
      native_node_name: relayint_reference_intent
      legacy_compatibility_node_name: relayint_reference_repair
    live_referrers_before_cutover: 1
verification:
  old_paths_removed_in_pr_tree: true
  exact_pre_cutover_blobs_reused: true
  canonical_evidence_wrappers_added: 4
  source_head_merge_and_pre_cutover_equal_records: 4
  source_to_pre_cutover_diff_records: 0
  post_source_modification_commits_total: 4
  post_source_modification_commits_are_pure_renames: true
  advisory_records_independently_reverified: 4
  advisory_records_confirmed_correct: 4
  advisory_records_corrected: 0
  source_pr_newly_established_not_previously_recorded: 3
  source_pr_none_direct_push_records: 1
  live_dependency_referrer_files_at_frozen_baseline: 1
  live_dependency_link_occurrences_at_frozen_baseline: 4
  live_dependency_referrer_files_updated: 1
  live_dependency_link_occurrences_retargeted: 4
  implementation_evidence_index_files_updated: 1
  new_evidence_index_entries_added: 4
  mvp_index_entries_updated: 4
  contracts_index_files_updated: 1
  new_contract_files_added: 2
  shared_index_files_updated: 3
  implementation_evidence_index_updated: true
  mvp_evidence_index_updated: true
  contracts_index_updated: true
  new_canonical_contracts_created: 2
  new_canonical_contract_paths:
    - docs/contracts/relayint_quick_clarification_runtime_contract.md
    - docs/contracts/pipeline_node_result_contract.md
  relayint_coverage_matrix_separate_from_pipeline_node_result_coverage_matrix: true
  pm_d6_relayref_supersession_recorded_separately: true
  absorbed_verbatim_blocks: 0
  code_derived_absorbed_blocks: 2
  absorption_destination_files:
    - docs/contracts/relayint_quick_clarification_runtime_contract.md
    - docs/contracts/pipeline_node_result_contract.md
  historical_old_path_string_occurrences_preserved_in_exact_snapshots: 0
  historical_old_path_string_occurrences_preserved_as_migration_identifiers_in_wrappers: 4
  compileall: passed
  documentation_link_check: passed
  documentation_semantic_audit: passed
  documentation_current_boundary_smoke: passed
  relayint_fast_path_dry_run_smoke: pre_existing_local_fixture_failure_verified_against_base
  relayint_quick_clarification_preflight_smoke: pre_existing_local_fixture_failure_verified_against_base
  relayint_quick_clarification_apply_smoke: passed
  acg4_reference_intent_analyzer_smoke: passed
  pipeline_node_result_smoke: passed
  pipeline_context_node_results_smoke: passed
  pipeline_node_results_runtime_smoke: passed
  consolidated_smoke_contract: passed
  git_diff_check: passed
  no_canonical_record_selects_unrelated_runtime_group: true
  all_github_actions: pending_final_remote_head
  codex_review: pending_final_remote_head
  unresolved_review_threads: pending_final_remote_head
```

The four canonical records split into two independent authority groups, as the task brief required: the first three (MVP-45 fast-path dry-run, MVP-46 preflight, MVP-47 apply plan) form one implemented chronological RelayINT plan-only chain confirmed still live in `relaylm/relayint.py`; the fourth (MVP-48) introduces the unrelated, cross-cutting `PipelineNodeResult` shared type and was not forced into the RelayINT contract merely because its example emitters include RelayINT node names. All four advisory pre-cutover blob/SHA-256 values were independently reverified via the GitHub API (not copied) and confirmed correct. All four records have zero content drift from their source commit through today: MVP-45/46/47 each received only a same-batch pure path-rename (`docs/mvp4N_summary.md` -> `docs/mvp/mvp4N_...md`, all on 2026-06-11, verified by comparing the add-commit and delete-commit patches byte-for-byte); MVP-48 was never renamed and has no post-source modification commits at all. MVP-47 is a squash-merged PR (#241): its source commit and origin/merge commit are identical, and its pre-merge branch history (an internal rewrite from a 63-line draft to the final 69-line plan-only version) is not reachable from `main` and is correctly excluded from provenance. MVP-48 has no source pull request — it is a direct-push documentation commit (`69cecf1841e54e95d18868559e03686c5e60484f`) 16 minutes after the related code PR #245 merged; PR #245's diff does not include the doc file, so PR #245 is recorded as a related, non-source PR rather than guessed as the source. Source PR numbers #239, #240, and #241 were newly established from GitHub merge-commit history and cross-verified against `pull_request_read`; none were guessed. Each of the four records had exactly one live referrer before this cutover (the shared `docs/mvp/README.md` "Retained focused historical notes" index), retargeted in this same PR to the new canonical evidence paths with historical-authority disclaimers matching the MVP-40-43 pattern.

Because the audit found the RelayINT quick-clarification chain's exact candidate-action/clarification-type/blocked-reason taxonomies, request-compatibility-gate reasons, and scene-gate reasons nowhere fully enumerated outside `relaylm/relayint.py` itself (`docs/architecture/relayint_mvp_design.md` covers the chain only at a narrative/example level, and `docs/config_schema.md` covers only flag defaults), a new canonical contract was created at `docs/contracts/relayint_quick_clarification_runtime_contract.md`. It required two code-derived additions rather than verbatim transfer, since MVP-47's source prose only summarized the request-compatibility gate and the apply-tier block-reason list rather than enumerating them: the full 13-name request-compatibility-gate reason set and the full 19-name apply-plan `block_reasons` taxonomy (including the always-appended `phase4_plan_only` reason that forces `apply_allowed` false today) were both written from direct code inspection of `build_relayint_request_compatibility_gate()` and `build_relayint_quick_clarification_apply_plan()`. Separately, because MVP-48's `PipelineNodeResult` scaffold had no exact current contract outside itself (`docs/architecture/pipeline_responsibility_design.md` and `docs/architecture/audit_trace_content_free_contract.md` only reference the type in passing), a second new canonical contract was created at `docs/contracts/pipeline_node_result_contract.md`, owning the exact frozen-dataclass shape, shallow-detachment semantics of `to_log_dict()`, request-local best-effort collection, and the current 16-node `PIPELINE_NODE_PROJECTORS` emitter list — a strict superset of MVP-48's stale three-node list, now spanning client-instruction, RelayINT, RelayCTX, and RelayMEM-SLP nodes. MVP-48's "historical RelayINT / RelayREF compatibility boundary" section (`runtime compatibility key: relayref_artifact`; `historical source node: relayref`) was independently confirmed superseded by PM-D6 (`docs/architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md`, `relaylm_status: current`, `complete` per `docs/PROJECT_STATUS.md`): RelayINT's live artifact key is `relayint_intent_artifact` (schema `relayint.intent.v1`), and `relaylm/pipeline_node_adapter.py` now synthesizes a native `relayint_reference_intent` node alongside the legacy-shaped `relayint_reference_repair` node, which is retained only as a trace-shape compatibility identifier with no real RelayREF data dependency. This superseded section is recorded as history in the MVP-48 evidence wrapper and is explicitly excluded from both new contracts. No compatibility path, redirect, or runtime behavior change is introduced.

## Pending batches

- Cutover 1C: remaining implementation, wave, evaluation, and release evidence migration.
- Later cutovers: architecture synthesis, exact contract reconstruction, old-tree removal, and final invariant enforcement.

## Freeze boundary

This ledger remains `current` while cutover PRs are being merged. At final cutover completion it must be changed to `frozen`, all `pending` fields must be resolved, and every baseline Markdown source must have a final disposition.

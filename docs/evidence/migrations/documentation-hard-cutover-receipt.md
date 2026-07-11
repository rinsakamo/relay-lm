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
merged_commit: pending
old_path: docs/architecture/phase_i3_validation_receipt.md
old_blob_sha: 710bf4dfb98e1b824751dc071fd206b7c4b9afda
old_content_sha256: 8f5bd9b650a78838a93ee870dbbec99c112ba3ab55d27ceafda2767544139036
source_commit: 74b308f341cb049e6adebbe2b0c959950198739a
source_pr: 379
disposition: evidence_retained
new_canonical_path: docs/evidence/evaluations/phase_i3_validation_receipt.md
verification:
  old_path_removed_in_pr_tree: true
  current_filename_search_dependencies: 0
  canonical_evidence_metadata_added: true
  validation_conclusion_changed: false
  documentation_link_check_required: true
```

This move changes placement and lifecycle metadata only. The recorded Phase I-3 verification results and privacy statement remain substantively unchanged.

## Pending batches

- Cutover 1C: remaining implementation, wave, evaluation, and release evidence migration.
- Later cutovers: architecture synthesis, exact contract reconstruction, old-tree removal, and final invariant enforcement.

## Freeze boundary

This ledger remains `current` while cutover PRs are being merged. At final cutover completion it must be changed to `frozen`, all `pending` fields must be resolved, and every baseline Markdown source must have a final disposition.

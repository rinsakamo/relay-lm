# RelaySOUL Approval Summary Contract

This contract defines a content-free approval summary artifact that compares patch-candidate dry-run output and revision rollback summary output.

## Goal

Before approval execution, RelaySOUL should be able to evaluate whether a patch candidate and revision metadata are consistent enough to proceed.

## Input artifacts

- RelaySOUL patch candidate dry-run artifact
- RelaySOUL rollback summary artifact

## Approval summary fields

- `approval_status`
- `warning_reasons`
- `blocking_reasons`
- `patch_candidate_id`
- `revision_id`
- `mode`
- `target_files`
- `changed_files`
- `target_changed_file_mismatch`
- `stable_prefix_changed`
- `content_free`

## Mismatch rules

- patch dry-run missing -> `missing_patch_dry_run`
- rollback summary missing -> `missing_rollback_summary`
- patch candidate id mismatch -> `patch_candidate_id_mismatch`
- mode mismatch -> `mode_mismatch`
- target files vs changed files mismatch -> `target_changed_file_mismatch`
- one-sided non-empty file lists (target only or changed only) are treated as `target_changed_file_mismatch`
- empty-string identity fields are still compared when present (not skipped by truthiness)

## Warning and blocking rules

- patch dry-run status `blocked` -> blocking `patch_dry_run_blocked`
- rollback summary status `blocked` -> blocking `rollback_summary_blocked`
- patch dry-run status `warning` -> warning `patch_dry_run_warning`
- rollback summary status `warning` -> warning `rollback_summary_warning`
- stable prefix changed -> warning `stable_prefix_changed`

## Safety constraints

This MVP-14C contract is dry-run-only:

- no approval execution
- no patch apply
- no revision apply
- no rollback execution
- no file write
- no model call
- no persona/memory/patch body content in artifacts

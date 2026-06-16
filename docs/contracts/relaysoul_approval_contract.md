# RelaySOUL Approval Summary Contract

## Status

This document describes the current implemented `mvp-soul-0` approval-summary dry run.

Producer:

```text
relaylm.relaysoul_approval.build_relaysoul_approval_summary
```

Result type:

```text
relaylm.relaysoul_approval.RelaySOULApprovalSummary
```

The result is content-free readiness metadata. It does not perform approval, patch application, rollback, persistence, file writes, or model calls.

## Inputs

- RelaySOUL patch-candidate dry-run artifact
- RelaySOUL rollback-summary artifact

These are current compatibility artifacts. Their file allowlists and field names follow the implemented `mvp-soul-0` schema until a versioned migration is implemented.

## Current fields

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

## Current mismatch rules

- missing patch dry run -> `missing_patch_dry_run`
- missing rollback summary -> `missing_rollback_summary`
- patch candidate ID mismatch -> `patch_candidate_id_mismatch`
- mode mismatch -> `mode_mismatch`
- target files and changed files differ -> `target_changed_file_mismatch`
- one-sided non-empty file lists are also a mismatch
- present empty-string identity fields are compared rather than skipped

## Current warning and blocking rules

- patch dry-run status `blocked` -> `patch_dry_run_blocked`
- rollback-summary status `blocked` -> `rollback_summary_blocked`
- patch dry-run status `warning` -> `patch_dry_run_warning`
- rollback-summary status `warning` -> `rollback_summary_warning`
- stable-prefix change -> `stable_prefix_changed`

A result with no blocking reasons means only that this comparison passed. A separate explicit-approval and freshness path is required before any future execution.

## Target migration

The target RelaySOUL migration must carry mode, target-file classes, evidence references, schema version, and approval state across candidate, revision, approval, apply, rollback, and storage stages. The current five-file compatibility allowlist must move to the three-file target ownership boundary as one coordinated migration.

See the [Current / Target / Migration Guide](../architecture/current_target_migration_guide.md).

## Safety constraints

- diagnostics-only,
- no patch or revision apply,
- no rollback execution,
- no storage write,
- no model call,
- no persona, memory, feedback, prompt, response, or patch body content.

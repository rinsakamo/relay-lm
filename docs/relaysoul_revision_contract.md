# RelaySOUL Revision Metadata / Rollback Contract

This contract defines a content-free metadata artifact for persona revisions and a dry-run rollback summary.

## Goal

After patch-candidate approval, RelaySOUL should produce structured revision metadata that can be evaluated for rollback readiness without applying changes.

## Persona revision fields

- `revision_id`
- `parent_revision_id`
- `mode`
- `changed_files`
- `feedback_ids`
- `patch_candidate_id`
- `patch_dry_run_status`
- `stable_prefix_hash_before`
- `stable_prefix_hash_after`
- `compile_dry_run_status`
- `applied_by`
- `rollback_available`

## Rollback summary fields

- `rollback_status`
- `warning_reasons`
- `blocking_reasons`
- `revision`
- `stable_prefix_changed`
- `content_free`

## Mode and changed-file rules

Allowed modes:

- `character_creation`
- `calibration`
- `normal_chat`

Allowed changed files:

- `SOUL.md`
- `OUTPUT_POLICY.md`
- `RELATIONSHIP_ANCHOR.md`
- `STABLE_MEMORY_SUMMARY.md`
- `SCENE_STATE.md`

Unsupported mode or changed file yields blocking diagnostics.

Additional guard:

- `normal_chat` with `SOUL.md` in `changed_files` is blocked (`soul_patch_not_allowed_in_normal_chat`).

## Stable prefix hash before/after

`stable_prefix_hash_before` and `stable_prefix_hash_after` indicate whether the stable persona prefix changed across revisions.
A value change does not block rollback by itself, but is reported as a warning (`stable_prefix_changed`).

## Safety constraints

This MVP-14B contract is metadata-only and dry-run-only:

- no revision apply
- no rollback execution
- no file write
- no model call
- no persona/memory/patch body content in contract artifacts

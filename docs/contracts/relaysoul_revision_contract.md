# RelaySOUL Revision Metadata / Rollback Contract

## Purpose

This document separates the **current implemented `mvp-soul-0` contract** from the **target durable-persona ownership boundary**.

Do not implement a consumer from the target section while reading current `mvp-soul-0` artifacts. A later migration must update implementation, examples, smoke tests, and every approval/apply/rollback stage together.

## Current implemented contract: `mvp-soul-0`

The current implementation is defined by `relaylm/relaysoul_revision.py` and the existing RelaySOUL dry-run scripts.

### Current revision fields

`RelaySOULPersonaRevision` currently contains:

```text
revision_id
parent_revision_id
mode
changed_files
feedback_ids
patch_candidate_id
patch_dry_run_status
stable_prefix_hash_before
stable_prefix_hash_after
compile_dry_run_status
applied_by
rollback_available
```

The current content-free log projection preserves these field names.

### Current modes

```text
character_creation
calibration
normal_chat
```

### Current changed-file allowlist

The current toolchain accepts:

```text
SOUL.md
OUTPUT_POLICY.md
RELATIONSHIP_ANCHOR.md
STABLE_MEMORY_SUMMARY.md
SCENE_STATE.md
```

This allowlist is a historical implementation contract, not the desired final ownership model.

### Current normal-chat gate

The current revision validator blocks only:

```text
normal_chat + SOUL.md
  -> soul_patch_not_allowed_in_normal_chat
```

It does **not** yet block every other target in `normal_chat`.

### Current rollback summary

The current rollback summary shape is:

```yaml
rollback_summary:
  rollback_status: ok | warning | blocked
  warning_reasons: []
  blocking_reasons: []
  revision:
    revision_id: "..."
    parent_revision_id: "..."
    mode: calibration
    changed_files: []
    feedback_ids: []
    patch_candidate_id: null
    patch_dry_run_status: ok
    stable_prefix_hash_before: "..."
    stable_prefix_hash_after: "..."
    compile_dry_run_status: ok
    applied_by: null
    rollback_available: true
  stable_prefix_changed: false
  content_free: true
```

Current validation also:

- blocks unsupported modes/files,
- blocks unavailable rollback,
- blocks `patch_dry_run_status=blocked`,
- warns on missing parent revision,
- warns on stable-prefix changes,
- warns when compile dry-run status is neither `None` nor `ok`.

## Target ownership boundary

The target RelaySOUL revision boundary is narrower:

```text
SOUL.md
OUTPUT_POLICY.md
RELATIONSHIP_ANCHOR.md
```

Target ownership excludes:

```text
SCENE_STATE.md / request-local scene state -> RelaySCN
STABLE_MEMORY_SUMMARY.md / compiled memory -> RelaySLP and RelayMEM
current affect state -> RelayEMO
short-term working state -> RelayCTX
```

This target boundary is normative architecture direction but is **not fully implemented by this docs-only PR**.

## Target normal-chat posture

After migration:

```text
normal_chat
  -> candidate/proposal metadata allowed
  -> apply blocked for every durable persona source
```

Recommended target reason:

```text
persona_apply_not_allowed_in_normal_chat
```

## Target revision metadata: proposed v1

A future typed v1 may use:

```text
schema_version
revision_id
parent_revision_id
mode
changed_files
evidence_refs
evidence_count
patch_candidate_id
approval_required
approval_status
patch_dry_run_status
compile_dry_run_status
budget_delta_class
stable_prefix_hash_before
stable_prefix_hash_after
stable_prefix_changed
applied_by_class
applied_at
rollback_available
blocking_reason_ids
warning_reason_ids
```

This is a migration target, not the current `mvp-soul-0` wire shape.

## Required migration scope

The 3-file allowlist and all-normal-chat apply block must be changed atomically across:

1. patch prompt generation,
2. patch candidate parser,
3. temporary revision compiler,
4. revision metadata validator,
5. approval package,
6. approval decision,
7. apply plan,
8. rollback plan,
9. persistence/storage preflight,
10. examples and smoke tests.

`mode` must remain available through the approval/apply chain so the final apply gate can enforce the normal-chat prohibition.

Until that migration lands, current tools may still accept `SCENE_STATE.md` and `STABLE_MEMORY_SUMMARY.md`; consumers must not mistake this compatibility behavior for target ownership approval.

## Target apply preconditions

After migration, apply should require:

- supported persona mode and target file,
- mode permits apply,
- explicit approval is valid,
- parent revision matches current revision,
- patch candidate is valid and lineage-linked,
- compile dry-run succeeds,
- persona-source budget passes,
- persona invariants/drift guards pass,
- stable-prefix impact is understood,
- persistence destination and rollback snapshot are ready.

Failure remains fail-closed and performs no file mutation.

## Protected evidence boundary

Both current and target metadata contracts must not contain:

- preferred/rejected response text,
- freeform feedback text,
- patch prompt or patch body,
- model/renderer output text,
- persona or memory source bodies,
- raw client messages.

Those belong to a separate protected calibration domain referenced by typed IDs.

## Dry-run posture

A dry-run artifact must clearly indicate that no mutation occurred. A future v1 should expose fields equivalent to:

```text
apply_attempted=false
apply_performed=false
rollback_performed=false
content_free=true
```

Current `mvp-soul-0` artifacts may use different field placement/names; consumers must follow the implemented schema.

## Non-goals

This contract does not:

- claim the target v1 schema is already implemented,
- apply or rollback persona files by itself,
- authorize scene/memory files as final RelaySOUL ownership,
- permit silent normal-chat persona mutation,
- store calibration/patch content,
- bypass approval and version lineage.

# RelaySOUL Revision Metadata / Rollback Contract

## Purpose

This contract defines content-free metadata for durable persona revisions and rollback readiness.

RelaySOUL revisions apply only to approved durable persona sources:

- `SOUL.md`,
- `OUTPUT_POLICY.md`,
- `RELATIONSHIP_ANCHOR.md`.

`SCENE_STATE.md`, request-local scene state, affect state, RelayCTX working state, and `STABLE_MEMORY_SUMMARY.md` are outside RelaySOUL revision ownership.

## Persona revision fields

Required or recommended content-free fields:

- `schema_version`,
- `revision_id`,
- `parent_revision_id`,
- `mode`,
- `changed_files`,
- `evidence_refs`,
- `evidence_count`,
- `patch_candidate_id`,
- `approval_required`,
- `approval_status`,
- `patch_dry_run_status`,
- `compile_dry_run_status`,
- `budget_delta_class`,
- `stable_prefix_hash_before`,
- `stable_prefix_hash_after`,
- `stable_prefix_changed`,
- `applied_by_class`,
- `applied_at`,
- `rollback_available`,
- `blocking_reason_ids`,
- `warning_reason_ids`.

IDs and hashes are allowed only when they are typed identifiers and do not encode content.

## Modes

Allowed modes:

- `character_creation`,
- `calibration`,
- `normal_chat`.

Mode controls proposal/apply posture, not target ownership.

### `character_creation`

May propose and apply any allowed persona file after explicit approval, compile dry-run, budget/invariant checks, versioning, and rollback preparation.

### `calibration`

May propose and apply allowed persona files after explicit approval. `OUTPUT_POLICY.md` and `RELATIONSHIP_ANCHOR.md` are preferred; `SOUL.md` requires explicit durable-identity justification.

### `normal_chat`

Proposal-only.

```text
normal_chat
  -> candidate/proposal metadata allowed
  -> apply blocked for every persona source
```

Required blocking reason for an apply attempt:

```text
persona_apply_not_allowed_in_normal_chat
```

## Allowed changed files

```text
SOUL.md
OUTPUT_POLICY.md
RELATIONSHIP_ANCHOR.md
```

Unsupported changed files yield blocking diagnostics.

Examples:

```text
SCENE_STATE.md
  -> relay_scn_state_not_persona_revision

STABLE_MEMORY_SUMMARY.md
  -> relaymem_state_not_persona_revision
```

## Apply preconditions

Apply is allowed only when all required gates pass:

- supported mode and target file,
- mode permits apply,
- explicit approval is valid,
- parent revision matches the current revision,
- patch candidate is valid and lineage-linked,
- compile dry-run succeeds,
- persona-source budget passes,
- persona invariants/drift guards pass,
- stable-prefix impact is understood,
- persistence destination and rollback snapshot are ready.

Failure is fail-closed and performs no file mutation.

## Rollback summary

Content-free rollback fields:

- `rollback_status`,
- `revision_id`,
- `parent_revision_id`,
- `changed_file_classes`,
- `stable_prefix_changed`,
- `rollback_available`,
- `blocking_reason_ids`,
- `warning_reason_ids`,
- `content_free`.

Rollback metadata must not contain persona-source bodies or patch text.

## Protected evidence boundary

The revision record may reference protected calibration evidence by typed IDs, but must not include:

- preferred/rejected response text,
- freeform feedback text,
- patch prompt or patch body,
- model/renderer output text,
- persona or memory source bodies,
- raw client messages.

Those belong to a separate protected calibration domain.

## Stable-prefix hash

`stable_prefix_hash_before` and `stable_prefix_hash_after` indicate whether approved persona-source compilation changed the stable prefix.

A change is observable metadata, not an automatic block. Policy may warn or require stronger review for large/high-risk revisions.

## Dry-run posture

A dry-run artifact may evaluate all gates without apply or rollback execution.

It must clearly record:

```text
apply_attempted=false
apply_performed=false
rollback_performed=false
content_free=true
```

## Non-goals

This contract does not:

- apply or rollback persona files by itself,
- own scene, affect, context, or memory state,
- allow normal-chat persona mutation,
- store calibration/patch content,
- bypass explicit approval and version lineage.

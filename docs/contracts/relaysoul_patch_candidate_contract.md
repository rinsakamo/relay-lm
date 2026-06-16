# RelaySOUL Patch Candidate Dry-Run Contract

## Status

This is the **current compatibility** contract for the diagnostics-only `mvp-soul-0` patch-candidate helper.

Current producer:

```text
relaylm.relaysoul_patch.build_relaysoul_patch_candidate_dry_run
```

Current result type:

```text
relaylm.relaysoul_patch.RelaySOULPatchDryRun
```

This contract does not generate patch text, apply a patch, write files, or call a model.

The target three-file RelaySOUL ownership boundary is documented in [RelaySOUL Patch Schema](relaysoul_patch_schema.md), [RelaySOUL Design](../relaysoul/relaysoul_design.md), and the [Current / Target / Migration Guide](../architecture/current_target_migration_guide.md).

## Goal

Before any patch generation or apply step, RelaySOUL evaluates whether a metadata-only patch candidate is structurally allowed and how existing RelayLM runtime diagnostics may affect review priority.

## Current candidate fields

- `candidate_id`
- `mode` (`character_creation`, `calibration`, `normal_chat`)
- `target_files`
- `feedback_ids`
- `feedback_labels`
- `freeform_notes_present`

These fields are metadata-only. Patch bodies and freeform evidence remain in a separate protected calibration domain.

## Current compatibility target-file rules

The implemented `mvp-soul-0` helper accepts:

- `SOUL.md`
- `OUTPUT_POLICY.md`
- `RELATIONSHIP_ANCHOR.md`
- `STABLE_MEMORY_SUMMARY.md`
- `SCENE_STATE.md`

Unsupported target files produce `unsupported_target_file`.

The five-file allowlist is historical compatibility behavior. It is not the target RelaySOUL ownership model. Target ownership excludes `STABLE_MEMORY_SUMMARY.md` and `SCENE_STATE.md`; migration must update every patch/revision/approval/apply/rollback/storage consumer and smoke test together.

## Current mode rules

Allowed modes:

- `character_creation`
- `calibration`
- `normal_chat`

Unsupported modes produce `unsupported_mode`.

Current central guard:

```text
normal_chat + SOUL.md
  -> soul_patch_not_allowed_in_normal_chat
```

Current compatibility does not yet block every durable persona target in `normal_chat`. The target behavior is proposal-only normal chat with apply prohibited for all durable persona sources.

## Runtime feedback relationship

Dry-run may consume:

- `relaysoul_runtime_feedback_summary`
- `persona_source_budget_diagnostics`

If runtime feedback status is warning, dry-run emits `runtime_feedback_warning`.
If persona-source budget status is warning, dry-run emits `persona_source_budget_warning`.

## Output and content boundary

The current output is content-free metadata containing status, reason IDs, candidate identifiers/classes, target classes, budget status, and stable-prefix presence.

It must not contain:

- patch text,
- persona or memory source bodies,
- preferred/rejected response text,
- raw user messages,
- prompt or backend response content.

## Required migration

The target migration must update atomically:

1. target-file allowlists,
2. mode propagation,
3. all-normal-chat apply prohibition,
4. patch and revision schemas,
5. approval/apply/rollback/storage consumers,
6. protected candidate versus content-free projection types,
7. examples and smoke tests,
8. explicit schema/version compatibility handling.

## Safety constraints

- diagnostics-only,
- no patch generation,
- no patch apply,
- no file write,
- no model API call,
- no persona/memory/patch body content in the artifact.

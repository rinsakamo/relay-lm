# RelaySOUL Patch Compile Dry-Run Contract

## Status

This is the current `mvp-soul-0` diagnostics-only comparison between RelaySOUL patch-candidate metadata and RelayLM compile diagnostics.

Current producer:

```text
relaylm.relaysoul_compile_dry_run.build_relaysoul_patch_compile_dry_run
```

Current result type:

```text
relaylm.relaysoul_compile_dry_run.RelaySOULPatchCompileDryRun
```

It consumes `CompiledRequest.to_log_dict()` output. It does not create/apply a temporary revision, change runtime compilation, write persona files, or call a model.

## Current inputs

- RelaySOUL patch-candidate dry-run artifact,
- RelayLM current compile log.

## Current compatibility mapping

```text
SOUL.md                   -> character_soul_anchor
OUTPUT_POLICY.md          -> character_output_policy
RELATIONSHIP_ANCHOR.md    -> relationship_anchor
STABLE_MEMORY_SUMMARY.md  -> stable_memory_summary
SCENE_STATE.md            -> scene_state
```

The final two mappings are current five-file compatibility behavior, not target RelaySOUL ownership.

## Current output fields

- compile dry-run status,
- warning/blocking reason IDs,
- patch candidate ID,
- target files/block IDs,
- missing block IDs,
- stable/dynamic target classes,
- persona-budget warning,
- stable-prefix hash presence,
- `content_free`.

## Current rules

- missing patch dry run or compile log blocks,
- `compiler_used != true` blocks,
- unsupported target files block,
- upstream warning/blocked state is propagated,
- a missing observed target block warns,
- persona-source budget warning is propagated.

A successful result means only that this metadata comparison passed. It is not approval or apply permission.

## Target migration

The three-file RelaySOUL migration must update the target mapping, current compiler relationship, revision/approval/apply consumers, schema versions, and smoke fixtures together. Future target-renderer validation remains separate from this current metadata-only comparison.

## Safety constraints

- dry-run-only,
- no patch generation/apply,
- no persona source write,
- no runtime compile behavior change,
- no model call,
- no persona/memory/feedback/prompt/response/patch body content.

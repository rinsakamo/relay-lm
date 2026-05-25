# RelaySOUL Patch Compile Dry-Run Contract

This contract defines a content-free dry-run check that compares a RelaySOUL patch candidate with RelayLM compile diagnostics.

## Goal

Before patch apply, RelaySOUL can validate whether patch targets are observable in compile artifacts and whether stability/budget signals indicate caution.

## Input artifacts

- RelaySOUL patch dry-run artifact
- RelayLM `CompiledRequest.to_log_dict()` output

## Target file to block mapping

- `SOUL.md` -> `character_soul_anchor`
- `OUTPUT_POLICY.md` -> `character_output_policy`
- `RELATIONSHIP_ANCHOR.md` -> `relationship_anchor`
- `STABLE_MEMORY_SUMMARY.md` -> `stable_memory_summary`
- `SCENE_STATE.md` -> `scene_state`

## Interpretation

- `stable_prefix_target_files` indicates patch targets that are in stable prefix blocks.
- `dynamic_target_files` indicates patch targets that are dynamic suffix blocks.
- `missing_target_block_ids` indicates mapped targets that were not observed in `context_block_summary.block_ids`.

## Warning and blocking rules

- missing patch dry-run or compile log blocks the dry-run contract.
- unsupported target files block the dry-run contract.
- patch status `warning`/`blocked` is propagated.
- target block missing from compile is warning.
- persona source budget warning is propagated from compile diagnostics.

## Safety constraints

This MVP-15B contract is dry-run-only:

- no patch generation
- no patch apply
- no persona source file write
- no runtime compile behavior change
- no model call
- no persona/memory/patch body content

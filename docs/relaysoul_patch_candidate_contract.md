# RelaySOUL Patch Candidate Dry-Run Contract

This contract defines a content-free dry-run artifact for RelaySOUL patch-candidate evaluation.

## Goal

Before any patch generation or apply step, RelaySOUL should be able to evaluate whether a patch candidate is structurally allowed and how existing RelayLM runtime diagnostics may affect review priority.

## Candidate fields

- `candidate_id`
- `mode` (`character_creation`, `calibration`, `normal_chat`)
- `target_files`
- `feedback_ids`
- `feedback_labels`
- `freeform_notes_present`

## Target file rules

Allowed target files:

- `SOUL.md`
- `OUTPUT_POLICY.md`
- `RELATIONSHIP_ANCHOR.md`
- `STABLE_MEMORY_SUMMARY.md`
- `SCENE_STATE.md`

Unsupported target files produce `unsupported_target_file` blocking reason.

## Mode rules

Allowed modes:

- `character_creation`
- `calibration`
- `normal_chat`

Unsupported modes produce `unsupported_mode` blocking reason.

Additional guard:

- `normal_chat` with `SOUL.md` target is blocked with `soul_patch_not_allowed_in_normal_chat`.

## Runtime feedback relationship

Dry-run may incorporate these existing RelayLM diagnostics:

- `relaysoul_runtime_feedback_summary`
- `persona_source_budget_diagnostics`

If runtime feedback status is warning, dry-run emits `runtime_feedback_warning`.
If persona source budget status is warning, dry-run emits `persona_source_budget_warning`.

## Safety constraints

This MVP contract is diagnostics-only:

- no patch generation
- no patch apply
- no file write
- no model API call
- no persona/memory content in dry-run artifact

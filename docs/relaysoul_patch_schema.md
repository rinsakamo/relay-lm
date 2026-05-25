# RelaySOUL Patch Schema (MVP-SOUL-0)

This document defines the first dry-run contract artifacts for RelaySOUL.

MVP-SOUL-0 is **schema-only**: RelaySOUL can collect feedback and generate patch candidates, but RelayLM runtime behavior must not change and no patch is auto-applied.

## Scope

RelaySOUL is the human-in-the-loop persona source calibration layer. RelayLM remains the runtime/compiler/diagnostics layer.

This MVP introduces three JSON artifacts:

1. `examples/relaysoul/feedback_examples.json`
2. `examples/relaysoul/patch_candidates.json`
3. `examples/relaysoul/persona_revision.json`

These artifacts are documentation/examples for contract shape and dry-run integration planning.

## 1) feedback_examples.json

Purpose:

- Capture natural-language preferred/rejected response pairs.
- Preserve calibration metadata (`calibration_id`, `prompt_kind`, `character_id`, `user_id`, `scene_id`).
- Keep lightweight labels/notes as patch evidence.

Contract intent:

- Feedback is evidence for patch proposal generation.
- Feedback alone does not mutate persona files.

## 2) patch_candidates.json

Purpose:

- Represent model-generated patch candidates in dry-run form.
- Store target, operation, rationale, patch text, provenance, and risk/approval gating fields.

Required posture:

- Patch candidates are **never auto-applied** in MVP-SOUL-0.
- `requires_user_approval` is explicit and can be `true` even in calibration mode.
- `SOUL.md` candidates are expected to be higher risk and approval-gated by default.

Contract fields support future gates:

- `budget_effect`: expected impact against Persona Source Budget.
- `stable_prefix_change_expected`: whether stable prefix hash changes are expected.
- `source_feedback_ids`: traceability to user preference evidence.

## 3) persona_revision.json

Purpose:

- Store metadata for a profile-level persona revision record.
- Track lineage, dry-run compile result, hash transition, and rollback availability.

Important:

- This file is metadata only.
- It is **not** a runtime mutation mechanism.
- It does not execute apply/rollback operations.

## MVP-SOUL-0 safety and gating model

RelaySOUL patch application is out of scope for this MVP. Later phases should gate apply decisions with RelayLM diagnostics and runtime safety checks, including:

1. **Persona Source Budget checks**  
   Ensure proposed edits do not unboundedly grow `SOUL.md`, `OUTPUT_POLICY.md`, `RELATIONSHIP_ANCHOR.md`, `STABLE_MEMORY_SUMMARY.md`, and `SCENE_STATE.md`.

2. **Stable prefix hash checks**  
   Use `stable_prefix_hash_before`/`stable_prefix_hash_after` and expected prefix impact to detect large identity-shifting deltas.

3. **Compile dry-run and token diagnostics**  
   Run compile dry-run before apply to confirm layout validity and token pressure impact.

4. **trace_runtime diagnostics**  
   Use runtime trace evidence to verify that patch effects match observed user feedback without regressions.

5. **Memory adapter conflict diagnostics**  
   Block or flag apply when memory adapter conflict diagnostics suggest contradictory or unsafe context interactions.

## Distillation policy

Persona Source Distillation should remain an **optional fallback only** for budget compression or consolidation.

Default path:

- user feedback -> patch candidate generation -> user review/approval -> revision metadata

Non-default fallback path:

- distillation/compression step when explicit budget pressure or maintenance need exists

## Terminology

Use `SCENE_STATE.md` / `scene_state` terminology for dynamic situation state.

Do not introduce new `ROOM_STATE.md` terminology in RelaySOUL patch contracts.

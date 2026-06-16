# RelaySOUL Patch Schema

## Purpose

This document separates the **current implemented `mvp-soul-0` patch-candidate contract** from the **target durable-persona ownership and projection model**.

The target sections define architecture direction. They do not claim that current scripts already emit or validate the proposed v1 shapes.

## Current implemented contract: `mvp-soul-0`

The current parser is implemented by `scripts/relaylm_relaysoul_patch_candidate_dry_run.py`.

### Current target-file allowlist

```text
SOUL.md
OUTPUT_POLICY.md
RELATIONSHIP_ANCHOR.md
STABLE_MEMORY_SUMMARY.md
SCENE_STATE.md
```

This is historical compatibility behavior. It is broader than the target RelaySOUL ownership boundary.

### Current required candidate fields

Each current candidate requires:

```text
target_file
target_block
operation
reason
patch_text
source_feedback_ids
risk_level
requires_user_approval
budget_effect
stable_prefix_change_expected
```

Current allowed `risk_level` values:

```text
low
medium
high
```

Current special validation for `SOUL.md`:

```text
risk_level=high
requires_user_approval=true
```

The current parser does not yet enforce an all-persona-file `normal_chat` apply prohibition because mode is not part of this candidate wire shape.

### Current artifact shape

```yaml
patch_candidates:
  schema_version: mvp-soul-0
  artifact_type: patch_candidates
  source_model_response: examples/relaysoul/model_response_patch_candidates.json
  items:
    - target_file: OUTPUT_POLICY.md
      target_block: tone
      operation: replace
      reason: "..."
      patch_text: "..."
      source_feedback_ids:
        - feedback-1
      risk_level: medium
      requires_user_approval: true
      budget_effect: neutral
      stable_prefix_change_expected: true
  candidate_count: 1
  warnings: []
```

This artifact is content-bearing because it includes `reason` and `patch_text`. It must remain in the protected calibration/tooling domain.

### Current patch prompt

The current patch-prompt dry-run still accepts and renders:

- `SOUL.md`,
- `OUTPUT_POLICY.md`,
- `RELATIONSHIP_ANCHOR.md`,
- `STABLE_MEMORY_SUMMARY.md`,
- `SCENE_STATE.md`.

It may recommend `SCENE_STATE.md` for temporary mood/situation changes. That behavior is part of the current legacy toolchain and must be migrated before the target ownership boundary is enforceable.

## Protected calibration evidence

Current and future RelaySOUL tooling may use protected content-bearing evidence:

- preferred/rejected response samples,
- freeform feedback and rationale,
- explicit persona-creation text,
- current persona-source bodies,
- patch prompts and patch text,
- renderer sample outputs.

This domain is not `content_free` and must not be copied into generic runtime trace records.

A content-free evidence projection may expose only:

```yaml
calibration_projection:
  schema_version: relaysoul.calibration_projection.v1
  calibration_id: calib_004
  mode: calibration
  prompt_kind_class: response_style
  preferred_sample_present: true
  rejected_sample_present: true
  feedback_label_count: 2
  evidence_source_class: explicit_user_feedback
  content_free: true
```

This projection is a target form, not the current patch-candidate artifact.

## Target ownership boundary

The target RelaySOUL patch allowlist is:

```text
SOUL.md
OUTPUT_POLICY.md
RELATIONSHIP_ANCHOR.md
```

Target routing for excluded state:

```text
SCENE_STATE.md / temporary role, setting, task, constraint -> RelaySCN
STABLE_MEMORY_SUMMARY.md / durable factual memory -> RelaySLP and RelayMEM
current affect/expression state -> RelayEMO
short-term topic/question/referents -> RelayCTX
```

## Target patch candidate: proposed v1

A future protected candidate may use:

```yaml
patch_candidate:
  schema_version: relaysoul.patch_candidate.v1
  patch_candidate_id: soulpatch_0017
  mode: calibration
  target_file: OUTPUT_POLICY.md
  operation: replace_or_consolidate
  rationale: "..."
  patch_text: "..."
  source_evidence_refs:
    - calib_004
  requires_user_approval: true
  risk_class: medium
  budget_effect:
    token_delta_estimate: 24
  stable_prefix_change_expected: true
```

This is not the current `mvp-soul-0` field set.

A future content-free projection may use:

```yaml
patch_candidate_projection:
  schema_version: relaysoul.patch_candidate_projection.v1
  patch_candidate_id: soulpatch_0017
  mode: calibration
  target_file_class: output_policy
  operation_class: replace_or_consolidate
  source_evidence_count: 1
  requires_user_approval: true
  risk_class: medium
  budget_delta_class: small_increase
  stable_prefix_change_expected: true
  content_free: true
```

Generic diagnostics receive the projection, not the protected candidate body.

## Target mode rules

### `character_creation`

Broad persona exploration is allowed, but every apply still requires explicit approval, versioning, compile dry-run, and rollback readiness.

### `calibration`

Prefer `OUTPUT_POLICY.md` and `RELATIONSHIP_ANCHOR.md`. `SOUL.md` requires explicit durable identity/value justification.

### `normal_chat`

Target behavior:

```text
candidate/proposal allowed
apply prohibited for every durable persona source
```

Recommended target reason:

```text
persona_apply_not_allowed_in_normal_chat
```

This prohibition is not yet enforceable end-to-end because current patch/approval/apply artifacts do not consistently carry mode.

## Required migration scope

The target v1 migration must update together:

1. patch prompt inputs and target rules,
2. patch-candidate required fields and allowlist,
3. examples and fixtures,
4. temporary revision compiler,
5. revision metadata,
6. approval package and decision,
7. apply/rollback plans,
8. persistence/storage preflight,
9. smoke tests,
10. generic content-free projections.

The migration must carry `mode` and typed evidence references through the whole chain.

## Safety invariants

Both current and target designs require:

- no automatic patch apply,
- protected storage for patch/evidence content,
- `SOUL.md` high-risk approval gating,
- source lineage,
- budget and stable-prefix impact checks,
- target-renderer compile dry-run,
- rollback readiness,
- fail-closed handling on malformed candidates.

## Non-goals

This document does not:

- claim the target v1 shape is implemented,
- execute apply or rollback,
- make legacy scene/memory targets final RelaySOUL ownership,
- mark content-bearing candidates as content-free,
- expose protected calibration artifacts through generic diagnostics.

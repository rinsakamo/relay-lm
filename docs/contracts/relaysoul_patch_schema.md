# RelaySOUL Patch Schema

## Purpose

This document defines the dry-run contract for RelaySOUL calibration evidence, persona-source patch candidates, and revision metadata.

RelaySOUL patch targets are limited to approved durable persona sources:

```text
SOUL.md
OUTPUT_POLICY.md
RELATIONSHIP_ANCHOR.md
```

Scene state, affect state, RelayCTX working state, and compiled memory are not RelaySOUL patch targets.

## Artifact domains

RelaySOUL uses two distinct domains.

### Protected content-bearing calibration domain

May contain:

- preferred/rejected response samples,
- freeform feedback and rationale,
- explicit persona-creation text,
- current persona-source bodies,
- patch prompts and patch text,
- renderer sample outputs.

This domain requires explicit access/retention policy and must not be copied into generic runtime trace records.

### Content-free metadata domain

May contain:

- calibration/evidence/candidate/revision IDs,
- mode,
- target source class,
- operation class,
- evidence count,
- approval requirement/status,
- risk class,
- budget effect class,
- stable-prefix-change boolean,
- compile/apply/rollback status,
- blocking/warning reason IDs.

## 1. Calibration evidence

A protected evidence object may contain content-bearing samples.

Conceptual fields:

```yaml
calibration_evidence:
  schema_version: relaysoul.calibration_evidence.v1
  calibration_id: calib_004
  mode: calibration
  character_namespace: character:mili
  prompt_kind: stuck_user_response
  preferred_response: "..."
  rejected_response: "..."
  feedback_labels:
    - warm
    - not_businesslike
  freeform_note: "..."
  created_by_class: user
```

Rules:

- evidence does not mutate persona files,
- raw user/client IDs should be replaced by scoped namespaces or protected references,
- evidence is not marked `content_free`,
- one inferred mood or transient scene is insufficient durable evidence.

Its content-free projection may contain only:

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

## 2. Patch candidate

Conceptual protected shape:

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

Allowed `target_file` values:

```text
SOUL.md
OUTPUT_POLICY.md
RELATIONSHIP_ANCHOR.md
```

Blocked target examples:

```text
SCENE_STATE.md
  -> relay_scn_state_not_persona_target

STABLE_MEMORY_SUMMARY.md
  -> relaymem_state_not_persona_target
```

Rules:

- patch candidates are never auto-applied,
- `SOUL.md` is high-risk and approval-gated,
- `normal_chat` candidates are proposal-only,
- patch text remains protected,
- target classification must explain why a faster runtime layer is insufficient.

Content-free candidate projection:

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

## 3. Persona revision metadata

Persona revision metadata is content-free and stores lineage/gate results, not source or patch bodies.

```yaml
persona_revision:
  schema_version: relaysoul.persona_revision.v1
  revision_id: 0017
  parent_revision_id: 0016
  mode: calibration
  changed_files:
    - OUTPUT_POLICY.md
  patch_candidate_ids:
    - soulpatch_0017
  evidence_count: 1
  approval_status: approved
  compile_dry_run_status: ok
  stable_prefix_changed: true
  rollback_available: true
  content_free: true
```

Detailed fields remain defined in [RelaySOUL Revision Metadata / Rollback Contract](relaysoul_revision_contract.md).

## Mode rules

### `character_creation`

Broad persona exploration is allowed, but every apply still requires explicit approval, versioning, compile dry-run, and rollback readiness.

### `calibration`

Prefer output/relationship policy targets. `SOUL.md` requires explicit durable identity/value justification.

### `normal_chat`

```text
candidate/proposal allowed
apply prohibited for every persona source
```

Required block reason:

```text
persona_apply_not_allowed_in_normal_chat
```

## Safety and gating

Future apply paths must check:

1. target ownership,
2. mode/apply permission,
3. explicit approval,
4. source lineage,
5. persona invariant/drift guards,
6. source budget,
7. compile dry-run against the target renderer,
8. stable-prefix impact,
9. revision parent/idempotency,
10. rollback readiness.

Any failed gate performs no persona mutation.

## Trace boundary

Default runtime trace/audit artifacts must not contain:

- preferred/rejected response text,
- feedback/freeform notes,
- patch prompts or patch text,
- persona/memory bodies,
- renderer sample text,
- raw client messages.

Only the content-free projections may enter generic diagnostics.

## Distillation

Persona source distillation is an optional protected candidate-generation step for budget compression or conflict reconciliation.

It does not change target ownership, approval requirements, or target-renderer validation.

## Non-goals

This schema does not:

- execute apply or rollback,
- treat scene/memory state as persona files,
- permit normal-chat persona mutation,
- mark content-bearing evidence as content-free,
- expose protected calibration artifacts through generic diagnostics.

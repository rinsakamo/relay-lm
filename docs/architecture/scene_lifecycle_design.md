# Scene Lifecycle Design

## Purpose

This document separates the current RelaySCN v0 helper from the target scene lifecycle.

Use [RelaySCN MVP Scene Policy](relayscn_mvp_scene_policy.md) for detailed current behavior and [Pipeline Implementation Plan](pipeline_implementation_plan.md) for sequencing.

## Ownership

```text
RelaySCN  scene interpretation and scene/persistence policy
RelayCTX  short-term conversation working state
RelayEMO  affect and transient expression state
RelayRUN  runtime transition/checkpoint orchestration
```

Scene state must not become a container for affect, transcript history, durable memory, or RelayCTX working state.

## Current implemented RelaySCN v0

Producer:

```text
relaylm.relayscn.build_relayscn_scene_policy_artifact
```

Current schemas:

```text
relayscn.scene_state.v0
relayscn.scene_policy.v0
relayscn.scene_policy_artifact.v0
```

Current runtime compatibility order:

```text
request/profile compilation
  -> Input-side RelayEMO
  -> RelaySCN v0
  -> RelayINT compatibility artifacts
  -> RelayMEM Retrieval
```

Current source precedence:

1. explicit request metadata/payload scene state,
2. RelayEMO artifact `scene_state`,
3. lightweight message heuristic,
4. unknown/fail-closed state.

The RelayEMO fallback and EMO-before-SCN order are current compatibility behavior, not target ownership.

Current normalized v0 state includes:

```yaml
schema_version: relayscn.scene_state.v0
scene_type: design_talk
confidence: 0.78
stability: 0.72
signals: []
is_estimate: true
recovery_mode: false
user_confirmation_required: false
```

Current policy includes scene-specific CTX/EMO/MEM/SLP gates, persistence blocking, reason IDs, and `diagnostics_required`.

The broad runtime artifact is request-local and may contain semantic scene content. Persisted trace requires a typed content-free projection.

## Target canonical order

```text
canonicalized current evidence
  -> Input-side RelaySCN
  -> Input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval
  -> RelayCTX Repack
  -> Main LLM
  -> RelayCTX Unpack
  -> RelayREF
  -> Return-side RelayEMO
  -> Output-side RelaySCN
```

## Target scene concepts

### `scene_id`

Operational/semantic identifier for the active situation. It may span turns but does not contain scene semantics by itself.

### `scene_state`

Request-local normalized scene semantics.

The following is a target v1 example, not the current wire shape:

```yaml
scene_state:
  schema_version: relayscn.scene_state.v1
  scene_type: implementation_work
  confidence: 0.88
  stability: 0.81
  previous_scene_type: design_talk
  transition_reason_class: user_requested_implementation
  scene_role:
    role_name: implementation_assistant
    role_scope: scene
    role_source: current_user_or_validated_instruction
  scene_context:
    setting: relaylm_repository
    task: implement_reviewed_change
  scene_constraints:
    - constraint_type: preserve_fail_closed_behavior
      value: true
  task_state: implementation_active
  safety_sensitivity: low
  formality: medium
  memory_scope: current_project
  expression_allowance: suppressed
  recovery_mode: false
  user_confirmation_required: false
```

Do not place in `scene_state`:

- mood or raw affect,
- current-topic notes/open questions/referents,
- transcript-shaped recent turns,
- memory page bodies.

### `scene_policy`

Target request-local policy resolved from scene state.

```yaml
scene_policy:
  schema_version: relayscn.scene_policy.v1
  relayctx_mode: repo_task
  relayemo_expression_policy: light
  relaymem_retrieval_scope: current_project
  relaymem_update_gate: allowed_dry_run
  relaysoul_update_gate: blocked
  persistence_block: false
  user_confirmation_required: false
  diagnostics_required: true
```

This is a target example. Current consumers use v0 fields.

### `scene_role`, `scene_context`, and `scene_constraints`

- `scene_role` describes what the character is doing now, not who it is durably.
- `scene_context` is bounded setting/task/participant information, not a second transcript.
- `scene_constraints` are temporary lower-authority rules and cannot override runtime/safety policy.

### `session_id` and `room_id`

Session is operational; scene is semantic. `room_id` is optional host metadata and is not prompt text by default.

## Target source precedence

1. trusted route/operator scene configuration,
2. validated current client-instruction artifact,
3. route-approved request metadata,
4. previous approved continuation state,
5. current-turn estimate,
6. safe default/unknown.

Raw client system/developer messages remain evidence rather than scene state.

## Lifecycle

### Start

A scene starts from trusted configuration, approved metadata, a validated instruction artifact, or current-turn evidence.

### Update and continuation

A scene updates when task, setting, participants, role, safety posture, or required policy changes. Topic continuity alone may remain RelayCTX working state.

### Transition

A transition occurs when situation or policy materially changes. A changed instruction hash is evidence, not the semantic transition itself.

### End

Ending a scene does not delete memory, persist temporary constraints, mutate persona sources, or promote a scene role into RelaySOUL.

## Target output-side RelaySCN

Output-side RelaySCN is planned and normally prepares next-turn state after Unpack, RelayREF, and Return-side RelayEMO.

A target projection may record transition presence, confidence band, apply timing, and reason class. It is not a general output rewriter.

Immediate current-response handling is limited to invalid output, leakage, safety-critical, or recovery-critical cases through explicit future gates.

## Runtime-private versus content-free

Runtime-private scene artifacts may contain normalized role, setting, task, participants, and constraints.

Default projections may contain:

- scene source/type classes,
- confidence/stability bands,
- role/context presence flags,
- constraint count,
- policy booleans/classes,
- persistence reason IDs/counts,
- transition presence/timing.

They must not contain semantic role names, task/setting text, participant values, constraint values, prompt fragments, or visible response text.

## Required migration

Update together:

1. input-side SCN before EMO,
2. remove normalized scene ownership from RelayEMO,
3. replace the RelayEMO scene-state fallback with bounded evidence where needed,
4. introduce versioned v1 state/policy schemas,
5. update app/PipelineContext order,
6. update policy consumers and persistence gates,
7. add typed projections,
8. update RelaySCN/EMO/Retrieval/integration smoke tests,
9. preserve explicit v0 compatibility handling.

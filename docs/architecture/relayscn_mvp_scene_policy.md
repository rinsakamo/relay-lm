# RelaySCN MVP Scene Policy

## Purpose

RelaySCN is RelayLM's scene controller.

```text
scene evidence
  -> scene_state
  -> scene_policy
```

This document separates the **current implemented RelaySCN v0 helper** from the **target request-local RelaySCN ownership and pipeline order**.

Current implementation phase and sequencing live in [Pipeline Implementation Plan](pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md).

## Current implemented RelaySCN v0

The current helper is `build_relayscn_scene_policy_artifact()` in `relaylm/relayscn.py`.

### Current runtime order

The current `app.py` request path runs approximately:

```text
request/profile compilation
  -> Input-side RelayEMO
  -> RelaySCN v0
  -> RelayINT compatibility/reference-repair artifacts
  -> RelayMEM Retrieval
  -> later pipeline phases
```

Thus the current implementation still runs RelayEMO before RelaySCN and passes the RelayEMO artifact into RelaySCN.

### Current scene-source precedence

Current RelaySCN v0 chooses scene state in this order:

```text
1. explicit request metadata / payload scene state
2. RelayEMO artifact scene_state
3. lightweight current-message heuristic
4. unknown/fail-closed state
```

The `relayemo_artifact` fallback is a legacy compatibility dependency and not the target ownership model.

### Current v0 scene-state shape

The current normalized state contains fields equivalent to:

```yaml
scene_state:
  schema_version: relayscn.scene_state.v0
  scene_type: design_talk
  confidence: 0.78
  stability: 0.72
  signals:
    - heuristic_reason
  is_estimate: true
  recovery_mode: false
  user_confirmation_required: false
```

Current v0 does not yet provide the richer target fields for:

- `previous_scene_type`,
- typed transition reason class,
- typed `scene_role`,
- typed `scene_context`,
- typed `scene_constraints`,
- task state,
- safety sensitivity,
- formality,
- memory scope as scene-state content,
- expression allowance as scene-state content.

### Current v0 policy shape

The current policy uses:

```text
relayscn.scene_policy.v0
```

and includes fields equivalent to:

```yaml
scene_policy:
  relayctx_mode: design_compact
  relayemo_marker_policy: light
  relayemo_expression_policy: light
  relaymem_retrieval_scope: project_context
  relaymem_update_gate: allowed_dry_run
  relaysoul_update_gate: proposal_only
  slp_mode: optional
  user_confirmation_required: false
  output_rewrite_allowed: false
  persistence_block: false
  persistence_block_reasons: []
  diagnostics_required: true
```

The current helper is diagnostics-oriented and returns a broad runtime artifact with `diagnostics_only: true`. The generic persisted trace must still use typed content-free projection rules rather than copying arbitrary semantic fields.

### Current persistence reasons

Current v0 may block persistence for:

- unknown scene,
- recovery,
- medical/safety scene,
- formal-document scene,
- user confirmation requirement,
- confidence/stability below current thresholds,
- selected signal strings such as unresolved contradiction/reference or recovery-derived output.

Threshold values and exact signal handling remain implementation/configuration details.

## Target canonical runtime order

The target architecture is:

```text
Client payload canonicalization
  -> current user turn
  -> bounded current client instruction evidence

Input-side RelaySCN
  -> request-local scene_state
  -> scene_policy

Input-side RelayEMO
RelayINT
RelayMEM Retrieval, when allowed
RelayCTX Repack
Main LLM
RelayCTX Unpack
RelayREF
Return-side RelayEMO
Output-side RelaySCN
User / TTS / Avatar output
```

In the target model, RelaySCN creates the normalized scene and policy before RelayEMO applies scene-constrained affect/expression behavior.

RelayEMO may provide bounded affect-related evidence for a future/next classification cycle, but it does not own normalized `scene_state`.

RelayREF is post-generation only. Same-turn input-side RelaySCN and Retrieval do not consume output-side RelayREF observations.

## Target responsibility boundary

RelaySCN owns:

- scene type,
- current role,
- compact setting/task/participants,
- bounded scene constraints,
- task state,
- safety sensitivity,
- formality,
- allowed memory scope,
- expression allowance policy,
- recovery state,
- confirmation requirement,
- persistence gates,
- next-turn transition policy.

RelaySCN does not own:

- raw affect or mood state,
- current-topic/open-question working memory,
- transcript continuity,
- reference resolution,
- memory retrieval/writes,
- durable persona revision,
- prompt block layout,
- general output rewriting.

## Target `scene_state` v1

A future typed shape may use:

```yaml
scene_state:
  schema_version: relayscn.scene_state.v1
  scene_type: design_talk
  confidence: 0.82
  stability: 0.74
  previous_scene_type: casual_chat
  transition_reason_class: user_started_architecture_discussion
  scene_role:
    role_name: architecture_reviewer
    role_scope: scene
    role_source: validated_client_instruction
    confidence: 0.91
  scene_context:
    setting: relaylm_design_session
    task: architecture_discussion
    participants:
      - user
      - assistant
  scene_constraints:
    - constraint_type: concise_progress_updates
      value: true
  task_state: architecture_discussion
  safety_sensitivity: low
  formality: low
  memory_scope: project_context
  expression_allowance: light
  recovery_mode: false
  user_confirmation_required: false
```

This is a target schema, not the current `relayscn.scene_state.v0` wire shape.

Do not place these component-owned values into target `scene_state`:

- RelayEMO affect estimates or mood,
- RelayCTX topic/open questions/recent points,
- referable items or unresolved slots,
- memory-page bodies,
- transcript-shaped recent turns.

## Target `scene_policy` v1

A future typed shape may use:

```yaml
scene_policy:
  schema_version: relayscn.scene_policy.v1
  relayctx_mode: design_compact
  relayemo_marker_policy: light
  relayemo_expression_policy: light
  relaymem_retrieval_scope: project_context
  relaymem_update_gate: allowed_dry_run
  relaysoul_update_gate: proposal_only
  client_instruction_apply_mode: cached
  client_scene_role_allowed: true
  client_scene_constraints_allowed: true
  durable_persona_candidate_allowed: false
  slp_mode: optional
  persistence_block: false
  user_confirmation_required: false
  output_rewrite_allowed: false
  diagnostics_required: true
```

Downstream components consume normalized policy, not raw client instructions.

## Target scene source precedence

Recommended target precedence:

```text
1. trusted route/operator scene configuration
2. validated current client-instruction cache artifact
3. route-approved request metadata
4. previous approved continuation state
5. current-turn heuristic/estimate
6. safe default / unknown
```

Raw client `system` or `developer` messages remain evidence, not scene state.

## Authority order

```text
1. RelayLM runtime / safety policy
2. approved RelaySOUL
3. approved durable output/relationship policy
4. RelaySCN scene policy
5. compatible client-derived role/context/constraints
6. current user request
```

A client-derived constraint cannot authorize tools, disable safety, force retrieval, mutate memory/persona, or promote temporary style into durable policy.

## Output-side RelaySCN

Output-side RelaySCN consumes validated post-generation observations after RelayCTX Unpack, RelayREF, and Return-side RelayEMO.

Target behavior separates:

- lightweight current-response safety gating before external emission,
- response-complete next-turn scene/recovery/persistence observation.

It is not a general output rewriter.

## Runtime-private artifact versus projection

### Runtime-private scene artifact

May contain normalized role names, setting/task/participants, constraints, and transition candidates required by downstream runtime components.

### Content-free scene projection

Default persisted diagnostics may contain only:

- scene source/type classes,
- confidence/stability bands,
- role/context presence,
- constraint counts,
- policy booleans/classes,
- persistence reason IDs/counts,
- transition presence/timing.

It must not contain role names, setting/task text, participant values, constraint values, prompt fragments, or visible response text.

## Required migration scope

A future implementation migration should update together:

1. remove normalized scene ownership from RelayEMO,
2. run input-side RelaySCN before RelayEMO,
3. replace the RelayEMO `scene_state` fallback with bounded evidence hints where needed,
4. introduce typed `scene_state.v1` and `scene_policy.v1`,
5. update app/PipelineContext node ordering,
6. update persistence and downstream policy consumers,
7. add typed content-free scene projections,
8. update RelaySCN, RelayEMO, Retrieval, and integration smoke tests,
9. preserve v0 compatibility through explicit schema/version handling.

## Summary

```text
current
  RelayEMO -> RelaySCN v0
  explicit metadata -> RelayEMO scene_state -> heuristic

target
  canonicalized evidence -> RelaySCN v1 state/policy
  -> scene-constrained RelayEMO
  -> INT / MEM / CTX
```

# Scene Lifecycle Design

## Scope

This document defines the lifecycle and ownership of:

- `scene_id`,
- `scene_state`,
- `scene_policy`,
- `scene_role`,
- `scene_context`,
- `scene_constraints`,
- `session_id`,
- optional `room_id`.

RelaySCN owns scene interpretation and scene-policy resolution. RelayRUN owns runtime transition/checkpoint orchestration. RelayCTX owns short-term conversation working state. RelayEMO owns affect state.

This document does not define standalone `RelayPLC` or `RelayTRC` components.

## Core boundary

```text
RelaySCN
  what situation is active and what policy follows

RelayCTX working state
  what the conversation is currently discussing or waiting on

RelayEMO
  current affect estimate and expression state

RelayRUN
  how runtime transition/recovery is executed and recorded
```

Scene state must not become a catch-all container for affect, short-term conversation history, or durable memory.

## Definitions

### `scene_id`

A metadata identifier for the current semantic situation or scenario.

Examples:

- `default_chat`,
- `debugging_session`,
- `stream_qna`,
- `roleplay_cafe_scene`,
- `technical_support_mode`.

A scene may span several turns and may be resumed across sessions when an operator or approved state explicitly reuses it.

### `scene_state`

Request-local normalized scene semantics.

Recommended fields:

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
    confidence: 0.92
  scene_context:
    setting: relaylm_repository
    task: implement_reviewed_change
    participants:
      - user
      - assistant
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

RelaySCN-owned fields describe the situation and policy inputs.

Do not store these in `scene_state` as owned semantic state:

- current mood or raw affect estimate,
- current topic notes,
- open questions,
- recently discussed points,
- referable items,
- unresolved slots,
- transcript-shaped recent turns,
- memory page bodies.

Those belong to RelayEMO, RelayCTX working state, or RelayMEM.

### `scene_policy`

A request-local downstream policy resolved from scene state.

```yaml
scene_policy:
  schema_version: relayscn.scene_policy.v1
  relayctx_mode: repo_task
  relayemo_marker_policy: suppress
  relayemo_expression_policy: light
  relaymem_retrieval_scope: current_project
  relaymem_update_gate: allowed_dry_run
  relaysoul_update_gate: blocked
  slp_mode: optional
  persistence_block: false
  user_confirmation_required: false
  output_rewrite_allowed: false
  diagnostics_required: true
```

Downstream components consume policy fields, not raw client instructions.

### `scene_role`

The function performed by the character in the current turn or scene.

```text
RelaySOUL
  who the character is durably

scene_role
  what the character is doing now
```

`scene_role` is not the OpenAI message `role` field and must not be silently promoted into RelaySOUL.

Allowed initial scopes:

```text
turn
scene
```

### `scene_context`

Compact setting, task, participants, and active situation.

It must remain bounded and must not become a second conversation transcript or a copy of RelayCTX working memory.

### `scene_constraints`

Bounded temporary rules for the current turn or scene.

Examples:

- ask at most one clarification question,
- keep spoken response short,
- require evidence before asserting a project status,
- suppress roleplay in a formal-document scene.

They are lower authority than runtime/safety policy and approved durable persona policy.

### `session_id`

Operational identifier for a runtime conversation/session run.

Session is operational; Scene is semantic.

### `room_id`

Optional external host metadata such as a frontend conversation, room, stream, stage, or channel identifier.

It may support scoping and diagnostics but should not become prompt text by default. External IDs remain potentially sensitive and should be omitted, redacted, or transformed in persisted diagnostics according to operator policy.

## Source precedence

Recommended precedence:

```text
1. trusted route/operator scene configuration
2. validated current client-instruction cache artifact
3. route-approved request metadata
4. previous approved scene-continuation state
5. current-turn heuristic or estimate
6. safe default / unknown
```

Raw client `system` or `developer` messages are evidence, not scene state. They must pass the Client Instruction Authority flow before affecting RelaySCN.

## Canonical runtime order

```text
Client payload canonicalization
  -> current user turn
  -> current client instruction evidence

Input-side RelaySCN
  -> scene_state
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

RelayREF is post-generation only. It does not guide same-turn input-side scene classification or memory retrieval.

## Lifecycle

### Scene start

A scene starts when trusted configuration, approved metadata, a validated instruction artifact, or current-turn evidence establishes a situation.

Missing scene metadata should not block ordinary compatible chat unless safe interpretation requires a specific role or context.

### Scene update

A scene may update when:

- the task changes,
- the setting or participants change,
- a temporary role changes,
- a validated client-instruction identity changes,
- recovery or safety policy changes.

Conversation-topic continuity alone does not require a new scene. RelayCTX may update its working state while RelaySCN remains stable.

### Scene continuation

A scene continues while the semantic situation and applicable policy remain sufficiently stable.

Repeated identical client prompts may confirm a validated scene source but must not create repeated transitions or durable persona proposals.

### Scene transition

A transition occurs when context, role, memory scope, safety posture, or required output policy materially changes.

A changed instruction hash is only evidence. The validated semantic interpretation determines whether a transition occurred.

### Scene end

A scene ends when the host/operator resets it, a new semantic situation starts, or recovery clears and a new approved state is established.

Ending a scene must not automatically:

- delete memories,
- persist temporary constraints,
- mutate persona sources,
- promote a scene role into RelaySOUL.

## Output-side RelaySCN

Output-side RelaySCN consumes validated observations after RelayCTX Unpack, RelayREF, and Return-side RelayEMO.

It normally emits next-turn transition state:

```yaml
output_scene_observation:
  scene_changed: false
  next_scene_candidate_present: true
  confidence_band: medium
  apply_timing: next_turn
  transition_reason_class: assistant_suggested_next_task
```

Immediate transition is limited to:

- safety-critical escalation,
- leakage/invalid-output handling,
- recovery/context-repair escalation,
- high wrong-continuation risk.

Output-side RelaySCN is not a general output rewriter.

## Runtime artifact versus projection

### Runtime-private artifact

May contain normalized role names, setting/task/participants, constraint values, and other semantic content needed by RelayCTX.

It remains request-local or protected by an explicit cache/storage contract.

### Content-free diagnostic projection

May contain:

- scene-state source class,
- scene type class,
- presence flags,
- confidence/stability bands,
- role scope/source class,
- constraint count,
- cache status,
- policy booleans,
- persistence block reasons/counts.

It must not contain role names, setting/task text, participant values, constraint values, transition-reason text, prompt fragments, or visible response text.

## Legacy Room compatibility

`room_state` may remain a compatibility alias for `scene_state` only when `scene_state` is unset.

Legacy `room_anchor` content should be reclassified:

```text
shared fixed rules -> common_runtime_policy
character expression rules -> OUTPUT_POLICY.md
relationship principles -> RELATIONSHIP_ANCHOR.md
dynamic situation -> scene_state
current function -> scene_role
external host identity -> room_id metadata
```

## Memory implications

Scene policy may constrain retrieval and persistence, but scene state itself is not a memory record.

Retrieval only reads. RelaySLP may later inspect governed scene summaries when producing memory candidates. Scene transition or end does not itself authorize a memory write.

## Non-goals

Scene lifecycle does not own:

- affect estimation,
- current-topic/open-question working memory,
- memory retrieval implementation,
- memory writes,
- durable persona mutation,
- backend routing,
- output rewriting,
- trace storage of semantic scene content.

## Summary

```text
scene evidence
  -> RelaySCN scene_state
  -> RelaySCN scene_policy
  -> downstream constraints

conversation continuity -> RelayCTX
current affect -> RelayEMO
runtime transition/checkpoint -> RelayRUN
```

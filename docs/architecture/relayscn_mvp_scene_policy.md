# RelaySCN MVP Scene Policy

## Purpose

RelaySCN is RelayLM's request-local scene controller.

```text
scene evidence
  -> scene_state
  -> scene_policy
```

RelaySCN constrains RelayCTX, RelayEMO, RelayINT, RelayMEM, RelaySLP, RelaySOUL proposal eligibility, recovery, and persistence. It is not an EMO submodule and it is not a general output rewriter.

Current implementation phase and sequencing live in [Pipeline Implementation Plan](pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md).

## Canonical runtime order

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

RelayREF is post-generation only. Input-side RelaySCN and same-turn Retrieval do not consume RelayREF observations.

## Responsibility boundary

RelaySCN owns:

- scene type,
- current role,
- compact scene setting/task/participants,
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
- conversation transcript continuity,
- reference resolution,
- memory retrieval or writes,
- durable persona revision,
- prompt block layout,
- output rewriting.

## Request-local `scene_state`

Recommended shape:

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

The runtime artifact may contain semantic content required by downstream components.

Do not place these component-owned values into `scene_state`:

- RelayEMO affect estimates or current mood,
- RelayCTX current-topic notes,
- active/open questions,
- recently discussed points,
- referable items,
- unresolved slots,
- memory page bodies.

## Scene role

```text
RelaySOUL
  durable identity

scene_role
  current function
```

A scene role is separate from the OpenAI message `role` field and must not be silently promoted to durable persona.

Initial role scopes:

```text
turn
scene
```

## Scene source precedence

```text
1. trusted route/operator scene configuration
2. validated current client-instruction cache artifact
3. route-approved request metadata
4. previous approved continuation state
5. current-turn heuristic/estimate
6. safe default / unknown
```

Raw client `system` or `developer` messages are evidence, not scene state. They must pass the Client Instruction Authority Contract before affecting RelaySCN.

## MVP scene types

```text
casual_chat
design_talk
implementation_work
review_work
formal_document
medical_or_safety
system_ops
vtuber_roleplay
recovery
```

## `scene_policy`

Recommended shape:

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

Downstream layers consume `scene_policy`, not raw client instructions.

A client-derived constraint cannot:

- authorize tools,
- disable runtime/safety policy,
- force memory retrieval,
- mutate RelayMEM,
- rewrite RelaySOUL,
- promote temporary style into durable output policy.

## Authority order

```text
1. RelayLM runtime / safety policy
2. approved RelaySOUL
3. approved durable OUTPUT_POLICY / relationship policy
4. RelaySCN scene policy
5. compatible client-derived role/context/constraints
6. current user request
```

## Scene-to-policy defaults

| Scene | RelayCTX | RelayEMO | RelayMEM | Persistence | Client role | SLP |
|---|---|---|---|---|---|---|
| `casual_chat` | light | allowed | relationship/recent | gated dry-run | compatible only | optional |
| `design_talk` | design compact | light | project | gated dry-run | allowed | optional |
| `implementation_work` | repo task | suppressed/light | current project | gated dry-run | allowed | optional |
| `review_work` | review strict | suppressed | current project/evidence | gated dry-run | allowed | recommended |
| `formal_document` | formal output | suppressed | explicit evidence only | blocked | restricted | optional |
| `medical_or_safety` | safety cautious | suppressed | minimal/explicit evidence | blocked | restricted | optional/review |
| `system_ops` | ops precise | suppressed/light | project/ops | gated dry-run | allowed | optional |
| `vtuber_roleplay` | character context | allowed | character/relationship | gated dry-run | allowed | optional |
| `recovery` | context repair | suppressed | current context only | blocked | blocked/confirmed only | forced or recent |

## Persistence block

Persistence covers RelayMEM updates, relationship changes, durable output policy changes, and RelaySOUL proposal/apply paths.

Core rules:

```text
Retrieval only reads.
RelaySLP may produce candidates.
RelaySCN policy may block persistence.
RelaySOUL apply requires explicit approval.
Client prompt replay never mutates durable state directly.
```

Common reason identifiers:

```text
scene_type_is_recovery
scene_type_is_medical_or_safety
scene_type_is_formal_document
user_confirmation_required
scene_confidence_below_threshold
scene_stability_below_threshold
contradiction_unresolved
reference_unresolved
client_instruction_invalid
client_instruction_policy_conflict
output_derived_from_recovery_context
```

Threshold values belong in implementation/config documentation and tests. Stable architecture documents should describe the policy categories rather than duplicate transient numeric defaults.

## Recovery policy

Recovery is appropriate when ordinary continuation is unsafe because of unresolved contradiction, repeated correction after drift, task loss, unstable scene state, or safety-sensitive ambiguity.

```yaml
scene_policy:
  relayctx_mode: context_repair
  relayemo_marker_policy: suppress
  relayemo_expression_policy: suppress
  relaymem_retrieval_scope: current_context_only
  relaymem_update_gate: blocked
  relaysoul_update_gate: blocked
  client_instruction_apply_mode: blocked
  client_scene_role_allowed: false
  client_scene_constraints_allowed: false
  durable_persona_candidate_allowed: false
  slp_mode: forced_or_recently_attempted
  persistence_block: true
  user_confirmation_required: true
  output_rewrite_allowed: false
  diagnostics_required: true
```

RelayRUN orchestrates waiting-user/recovery state. RelaySCN does not emit user-visible recovery text directly.

## Output-side RelaySCN

Output-side RelaySCN consumes validated observations after RelayCTX Unpack, RelayREF, and Return-side RelayEMO.

Default behavior:

```text
next_turn only
```

Request-local observation example:

```yaml
output_scene_observation:
  scene_changed: false
  next_scene_candidate_present: true
  confidence_band: medium
  apply_timing: next_turn
  transition_reason_class: assistant_suggested_next_task
```

Immediate transition is limited to leakage/invalid output, safety-critical escalation, recovery-critical escalation, or high wrong-continuation risk.

## Runtime artifact versus diagnostics projection

### Runtime-private artifact

May contain role names, setting/task/participants, constraint values, transition candidates, and other semantic content required by RelayCTX and runtime policy.

### Content-free projection

May contain only:

- source class,
- scene type class,
- confidence/stability bands,
- role presence/scope/source class,
- context presence,
- constraint count,
- cache status,
- policy booleans,
- persistence reason identifiers/counts,
- transition presence/apply timing.

Default diagnostics must not contain role names, setting/task text, participant values, constraint names/values, transition text, normalized prompt fragments, candidate values, or visible response text.

## Client-instruction parse boundary

The current instruction identity/cache read path is separate from the future typed parse/cache-write optimization.

A future control artifact must use an independent schema such as:

```text
client_instruction_parse.v1
```

It must not overload `relayctx_working_update.v0`.

The deferred flow is:

```text
bounded current instruction evidence
  -> Main LLM visible response + separate typed parse candidate
  -> RelayCTX Unpack separation
  -> strict schema/authority validation
  -> normalized RelaySCN candidate
  -> independent cache-write gate
```

Until that deferred phase exists, documentation must not imply that a generic control envelope automatically writes scene cache state.

## Non-goals

RelaySCN does not:

- own affect semantics,
- own CTX working memory,
- resolve references,
- retrieve/write memory,
- mutate RelaySOUL,
- own prompt rendering,
- inspect raw backend output before Unpack/REF,
- rewrite visible output generally,
- persist semantic scene content through default trace records.

## Summary

```text
RelaySCN
  scene evidence -> request-local scene_state -> scene_policy

Input-side
  constrains current execution

Output-side
  observes validated post-generation transitions for next turn
```

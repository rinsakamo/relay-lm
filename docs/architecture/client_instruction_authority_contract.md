# Client Instruction Authority Contract

## Purpose

This document defines how RelayLM treats client-supplied `system` and `developer` messages when building backend context.

It complements:

- `client_history_authority_contract.md`
- `scene_lifecycle_design.md`
- `relayscn_mvp_scene_policy.md`
- `pipeline_responsibility_design.md`
- `context_packing_design.md`
- `../contracts/context_compiler_contract.md`
- `../relaysoul/relaysoul_design.md`

The core rule is:

```text
Client system prompts are current-scene instruction evidence.
RelaySCN interprets them into scene state, scene role, and scene constraints.
They are not RelaySOUL and must not silently redefine durable identity.
```

## Authority boundaries

```text
RelaySOUL
  durable identity, values, worldview, and persona invariants

RelaySCN
  current situation, active role, task frame, temporary mode,
  participants, and scene-specific response constraints

RelayCTX
  compiles the authoritative SOUL plus current SCN state
  into the backend-bound context
```

A current scene role describes **what the character is doing now**, not **who the character permanently is**.

Example:

```text
RelaySOUL:
  warm, curious companion with stable values and identity

RelaySCN.scene_role:
  technical reviewer for the current pull request
```

The role may change from `technical reviewer` to `stream host`, `interviewer`, or `cafe staff` without mutating the durable character core.

## SCN-first client instruction processing

For RelayLM-managed routes, client `system` and `developer` messages should be extracted before prior frontend history is discarded and passed to Input-side RelaySCN as low-trust instruction evidence.

RelaySCN should classify the usable content into current-turn and current-scene fields such as:

```yaml
scene_state:
  scene_type: vtuber_roleplay
  scene_role:
    role_name: cafe_staff
    role_source: client_system
    role_scope: scene
  task_state: customer_conversation
  scene_context:
    setting: virtual_cafe
    participants:
      - character
      - viewer
  scene_constraints:
    - remain_in_current_role
    - use_short_spoken_responses
  confidence: 0.82
  stability: 0.70
```

`scene_role` is a semantic runtime role. It is not the OpenAI message `role` field.

The preferred conceptual split is:

```text
"You are the interviewer for this session."
  -> scene_role

"Ask one question at a time."
  -> scene_constraints / scene_policy

"We are conducting a technical hiring interview."
  -> scene_context / task_state

"Your permanent name, values, and identity are ..."
  -> durable persona candidate evidence only
     never direct SOUL mutation
```

## Existing SOUL

When an approved `SOUL.md` or RelaySOUL revision exists:

- RelayLM uses it as the authoritative durable persona core.
- RelaySCN may derive a current `scene_role` from the client instruction.
- Scene role and temporary constraints may guide current behavior.
- Client instructions do not overwrite the stable persona prefix.
- A conflict is resolved in favor of safety/runtime policy and RelaySOUL identity.
- Any durable persona change requires a RelaySOUL proposal, validation, approval, revision, and rollback path.

```text
existing SOUL
  + client system prompt

  -> RelaySCN scene_role / scene_context / scene_constraints
  -> RelayCTX compiles SOUL + SCN
  -> no silent SOUL mutation
```

## Missing SOUL

When a RelayLM-managed route has no usable SOUL source, the client system prompt still enters through RelaySCN first.

```text
SOUL missing
  + client system prompt

  -> build temporary SCN scene_role and constraints
  -> use them for the current request
  -> separately determine whether durable persona evidence exists
  -> optionally create a RelaySOUL proposal
```

This lets the first request retain the frontend character role without pretending that the entire client prompt is a durable persona source.

The system prompt must not be copied wholesale into `SOUL.md`.

## RelaySOUL creation when SOUL is missing

The wider product policy remains:

```text
Use SOUL when it exists.
When it does not exist, create a persona source and use it.
```

However, creation is separate from SCN ingestion.

RelaySOUL may use only the durable identity fragments detected in client instruction evidence as one candidate source. It may also use route metadata, explicit character-creation input, and approved operator/user preferences.

Classification boundary:

```text
SOUL.md
  durable identity, values, worldview, invariants

OUTPUT_POLICY.md
  durable expression and response-shape policy

RELATIONSHIP_ANCHOR.md
  durable relationship expectations

SCENE_STATE.md / scene_role
  current role, setting, task, scenario, temporary style,
  and current response constraints
```

A role remains in RelaySCN unless the user explicitly establishes that role as part of permanent character identity.

A temporary style remains in SCN unless the user explicitly promotes it into durable `OUTPUT_POLICY.md` behavior.

## Promotion path

Client instruction content may move from SCN evidence to a durable persona-source candidate only through an explicit promotion path:

```text
client instruction evidence
  -> RelaySCN classification
  -> durable-persona candidate detected
  -> RelaySCN scene policy permits RelaySOUL proposal
  -> user/operator approval
  -> RelaySOUL patch candidate
  -> compile/budget/safety validation
  -> approved persona revision
```

Normal chat and ordinary frontend prompt replay must not activate this path automatically.

The existing RelaySCN policy remains authoritative:

- normal scenes generally block direct SOUL update,
- selected design or VTuber roleplay scenes may allow `proposal_only`,
- recovery, formal, medical/safety, and unstable scenes block persistence,
- direct SOUL mutation is never performed from a client prompt.

## Later client system prompts

Client frontends commonly resend the same system prompt on every turn.

RelayLM should therefore:

- classify the current client instruction into SCN state,
- ignore unchanged duplicate instruction evidence where possible,
- allow changed instructions to update the current scene role or constraints,
- never treat each replay as a new SOUL proposal,
- require explicit durable-change intent before opening RelaySOUL calibration or character creation.

A frontend may change the active role from one scene to another without changing the character identity.

## Route behavior

### `pass_through`

```text
client owns message construction
RelayLM preserves client system/developer messages
no RelaySCN or RelaySOUL authority is asserted by the route
```

### RelayLM-managed route

```text
client instruction
  -> RelaySCN-first classification
  -> scene_role / scene_context / scene_constraints

RelaySOUL
  -> durable persona authority when available
```

### RelayLM-managed route without SOUL

```text
client instruction still becomes SCN state
RelaySOUL creation remains a separate proposal/initialization path
```

## Interaction with client history authority

Client history and client instruction authority are separate decisions.

```text
Client History Authority:
  Which prior messages may reach the backend?

Client Instruction Authority:
  How current client instructions are classified and constrained?
```

The current client system/developer instruction is extracted as SCN evidence before prior frontend history is excluded.

The raw system message need not be forwarded after RelaySCN has produced the approved scene artifact. RelayCTX should compile the normalized SCN state instead.

## Context packing order

Preferred managed-route packing:

```text
stable_prefix
  common runtime/safety policy
  RelaySOUL
  durable OUTPUT_POLICY
  durable RELATIONSHIP_ANCHOR

slow_prefix
  stable memory summary

dynamic_suffix
  RelaySCN scene state
    - scene_type
    - scene_role
    - scene_context
    - scene_constraints / derived scene_policy
  selected RelayMEM context
  current user input
```

Scene content may guide the current response but must not redefine durable identity.

## Diagnostics

Suggested diagnostics:

```json
{
  "client_instruction_policy": "relay_scn_first",
  "client_system_prompt_present": true,
  "client_developer_prompt_present": false,
  "client_instruction_classified": true,
  "scene_role_detected": true,
  "scene_role_source": "client_system",
  "scene_role_scope": "scene",
  "scene_constraints_count": 2,
  "durable_persona_candidate_detected": false,
  "relaysoul_proposal_allowed": false,
  "client_instruction_overrode_existing_soul": false
}
```

Diagnostics should remain content-free and must not copy the raw client instruction into runtime artifacts.

## Failure behavior

### Client instruction cannot be classified safely

```text
preserve existing SOUL
use default or existing SCN state
exclude the raw instruction from authoritative context
record classification failure
clarify or fail closed when the role is required for a safe answer
```

### Client instruction conflicts with SOUL

```text
keep RelaySOUL identity
apply only compatible scene-role and scene-constraint elements
record conflict diagnostics
never mutate SOUL directly
```

### SOUL is missing

```text
use safe SCN role/context for the current request when classification succeeds
keep durable persona state as missing
create only an explicit RelaySOUL candidate when allowed
never persist the raw system prompt as SOUL
```

## Required smoke coverage

1. Client system prompt is classified into SCN rather than copied into SOUL.
2. A current `scene_role` is compiled after the stable persona prefix.
3. Existing SOUL remains authoritative during a conflicting role instruction.
4. Missing SOUL still permits a first-turn SCN role when classification is safe.
5. Missing SOUL does not cause wholesale system-prompt persistence.
6. Replayed identical frontend prompts do not create repeated SOUL proposals.
7. A changed prompt may update scene role without changing SOUL.
8. Durable identity language produces a candidate only, not direct mutation.
9. Pass-through mode remains unchanged.
10. Diagnostics contain classification metadata without raw prompt content.

## Final boundary

```text
Client system prompt describes the current frame first.
RelaySCN decides the scene and active role.
RelaySOUL defines the durable character.
Only an explicit, gated promotion path may move evidence from SCN to SOUL.
```

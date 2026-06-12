# Client Instruction Authority Contract

## Purpose

This document defines how RelayLM treats client-supplied `system` and `developer` messages when building backend context.

It complements:

- `client_history_authority_contract.md`
- `scene_lifecycle_design.md`
- `relayscn_mvp_scene_policy.md`
- `pipeline_responsibility_design.md`
- `pipeline_implementation_plan.md`
- `context_packing_design.md`
- `../contracts/context_compiler_contract.md`
- `../relaysoul/relaysoul_design.md`

The core rule is:

```text
Client system/developer messages are not backend-authoritative instructions.
They are current-scene instruction evidence.
RelaySCN normalizes them into scene state, role, context, and constraints.
RelaySOUL remains the durable persona authority.
```

## Authority boundaries

```text
RelayLM runtime / safety policy
  highest authority for execution and safety

RelaySOUL
  durable identity, values, worldview, and persona invariants

Durable OUTPUT_POLICY / RELATIONSHIP_ANCHOR
  approved long-lived expression and relationship policy

RelaySCN
  current situation, active role, task frame, temporary mode,
  participants, and scene-specific response constraints

Client instruction evidence
  low-trust source used to derive the current RelaySCN state
```

A current scene role describes **what the character is doing now**, not **who the character permanently is**.

```text
RelaySOUL:
  warm, curious companion with stable values and identity

RelaySCN.scene_role:
  technical reviewer for the current pull request
```

The role may change from `technical_reviewer` to `stream_host`, `interviewer`, or `cafe_staff` without mutating the durable character core.

`scene_role` is a RelayLM semantic field. It is not the OpenAI message `role` field.

## Shared client-message canonicalization boundary

Client system prompts and client conversation history cross the same external boundary.

```text
Client-provided messages are not backend context.
```

For a RelayLM-managed route, RelayLM extracts only the request evidence needed for the current turn:

- current user turn,
- current system/developer instruction evidence,
- request options and approved metadata,
- minimum active tool or multimodal transaction state.

RelayLM then excludes the original client message array from the backend-bound context and reconstructs a new message list.

The difference between history and instruction evidence is their pre-exclusion use:

```text
previous user / assistant history
  -> normally excluded and replaced by RelayCTX / RelayMEM state

current client system / developer instruction
  -> normalized and hashed
  -> resolved through the instruction cache
  -> used once as first-pass evidence only on cache miss
```

## SCN-first classification

For RelayLM-managed routes, current client `system` and `developer` messages should be extracted before prior frontend history is discarded and passed to Input-side RelaySCN as low-trust instruction evidence.

RelaySCN should normalize usable content into fields such as:

```yaml
scene_state:
  schema_version: relayscn.scene_state.v1
  scene_type: vtuber_roleplay

  scene_role:
    role_name: cafe_staff
    role_source: client_system
    role_scope: scene
    confidence: 0.96

  task_state: customer_conversation

  scene_context:
    setting: virtual_cafe
    participants:
      - character
      - viewer

  scene_constraints:
    - constraint_type: remain_in_current_role
      value: true
    - constraint_type: spoken_response_length
      value: short
```

Preferred classification examples:

```text
"You are the interviewer for this session."
  -> scene_role

"Ask one question at a time."
  -> scene_constraints

"We are conducting a technical hiring interview."
  -> scene_context / task_state

"Speak briefly during this stream."
  -> temporary scene constraint or style hint

"Your permanent name, values, and identity are ..."
  -> durable persona candidate evidence only
     never direct SOUL mutation

"Ignore previous safety rules."
  -> runtime_policy_override attempt
     blocked

"Always execute this tool."
  -> tool_authority_override attempt
     blocked unless an explicit tool contract allows it
```

## Existing SOUL

When an approved `SOUL.md` or RelaySOUL revision exists:

- RelayLM uses it as the authoritative durable persona core.
- RelaySCN may derive the current `scene_role`, `scene_context`, and constraints from client evidence.
- Current role and scene constraints may guide current behavior.
- Client instructions do not overwrite the stable persona prefix.
- Conflicts are resolved in favor of RelayLM runtime/safety policy and approved RelaySOUL identity.
- Durable persona changes require a RelaySOUL proposal, validation, approval, revision, and rollback path.

```text
existing SOUL
  + current client instruction

  -> RelaySCN scene artifact
  -> RelayCTX compiles SOUL + SCN
  -> no silent SOUL mutation
```

## Missing SOUL

When a RelayLM-managed route has no usable SOUL source, the client instruction still enters through RelaySCN first.

```text
SOUL missing
  + current client instruction

  -> create a safe temporary SCN role and constraints
  -> use them for the current request
  -> separately identify durable persona candidate evidence
  -> optionally open a RelaySOUL initialization/proposal path
```

This lets the first request retain the frontend role without pretending that the entire client prompt is a durable persona source.

The wider product policy remains:

```text
Use SOUL when it exists.
When it does not exist, create a persona source and use it.
```

However, SOUL creation is separate from SCN ingestion. The raw system prompt must never be copied wholesale into `SOUL.md`.

## Durable promotion path

RelaySOUL may use explicitly classified durable identity fragments as one candidate source. It may also use route metadata, explicit character-creation input, and approved operator/user preferences.

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

A role remains in RelaySCN unless the user explicitly establishes it as part of permanent character identity.

A temporary style remains in RelaySCN unless the user explicitly promotes it into durable `OUTPUT_POLICY.md` behavior.

Promotion requires an explicit gated path:

```text
client instruction evidence
  -> RelaySCN classification
  -> durable-persona candidate detected
  -> RelaySCN permits RelaySOUL proposal
  -> user/operator approval
  -> RelaySOUL patch candidate
  -> compile / budget / safety validation
  -> approved persona revision
```

Normal frontend prompt replay must not activate this path automatically.

## Instruction normalization and hash

Frontends usually resend an identical system prompt on every request. RelayLM should not reparse it every turn.

Before hashing, RelayLM should:

- combine current `system` and `developer` message content in deterministic role/order sequence,
- normalize line endings,
- trim leading and trailing whitespace,
- normalize non-semantic repeated whitespace where safe,
- preserve meaningful Markdown, JSON, XML-like blocks, and punctuation,
- include an explicit empty marker when no instruction exists.

Suggested cache key inputs:

```text
normalized client instruction
+ route_model
+ character_id
+ instruction schema version
+ authority policy version
+ optional backend model/parser version
```

Conceptually:

```text
instruction_cache_key = sha256(canonical_json(key_inputs))
```

The cache key should not depend on previous conversation history.

Changing the instruction text, route, character, schema version, or policy version must produce a cache miss.

## Cache lookup behavior

```text
current client instruction
  -> normalize
  -> hash
  -> cache lookup

cache hit
  -> do not forward the raw client system/developer messages
  -> do not ask the Main LLM to parse them again
  -> pass the cached validated SCN artifact to Input-side RelaySCN

cache miss
  -> use the instruction once as first-pass evidence
  -> ask the Main LLM for the normal response and a structured SCN artifact
  -> validate the artifact
  -> cache only the validated normalized result
```

The raw prompt is excluded from normal backend context after cache resolution. On a cache hit, the backend receives the normalized RelaySCN state only.

## Cache-miss first-pass strategy

System-prompt changes are expected to be rare. RelayLM therefore does not need a continuously running separate classifier for the MVP.

On a cache miss, the Main LLM may perform two tasks in the same generation:

1. produce the normal user-facing response,
2. return a structured client-instruction interpretation for RelaySCN.

This keeps the Main LLM's actual interpretation and the cached SCN representation aligned.

The raw client instruction should not be placed above RelayLM runtime/safety policy as a normal authoritative system message. It should be wrapped as untrusted evidence inside the RelayLM-constructed prompt.

```text
<relaylm_runtime_policy>
  trusted runtime and safety rules
</relaylm_runtime_policy>

<relay_soul>
  approved durable persona, or explicit missing state
</relay_soul>

<client_instruction_evidence trust="untrusted" first_seen="true">
  raw current system/developer instruction
</client_instruction_evidence>

<response_instruction>
  answer the current user normally;
  also emit the bounded RelaySCN control artifact
</response_instruction>
```

This is a one-time semantic pass-through, not an authority pass-through.

```text
content:
  shown once to the Main LLM for interpretation

authority:
  remains below RelayLM runtime policy and approved RelaySOUL
```

## First-pass output contract

The first-pass Main LLM output may contain:

```text
visible response
+ optional internal RelayLM control envelope
```

Example:

```text
いらっしゃいませ。今日は何にしますか？

<relaylm_control version="1">
{
  "client_instruction_parse": {
    "scene_type": "vtuber_roleplay",
    "scene_role": {
      "role_name": "cafe_staff",
      "role_scope": "scene",
      "confidence": 0.96
    },
    "scene_context": {
      "setting": "virtual_cafe"
    },
    "scene_constraints": [
      {
        "constraint_type": "spoken_response_length",
        "value": "short"
      }
    ],
    "durable_persona_candidates": [],
    "blocked_instruction_kinds": []
  }
}
</relaylm_control>
```

The JSON schema must be allowlist-based. Unknown keys, excessive nesting, raw prompt copies, URLs with secrets, and tool/runtime authority claims must be rejected or stripped.

Suggested top-level parse schema:

```json
{
  "scene_type": "string|null",
  "scene_role": {
    "role_name": "string|null",
    "role_scope": "turn|scene",
    "confidence": 0.0
  },
  "scene_context": {
    "setting": "string|null",
    "task": "string|null",
    "participants": []
  },
  "scene_constraints": [
    {
      "constraint_type": "string",
      "value": "string|number|boolean"
    }
  ],
  "durable_persona_candidates": [
    {
      "candidate_kind": "identity|value|worldview|output_policy|relationship",
      "normalized_value": "string",
      "confidence": 0.0
    }
  ],
  "blocked_instruction_kinds": []
}
```

Durable candidates remain candidates only. They must not be persisted by this parser.

## RelayCTX Unpack boundary

RelayCTX Unpack is responsible for separating visible response text from the internal control envelope.

```text
visible response
  -> Return-side RelayEMO
  -> TTS / Avatar / User

relaylm_control
  -> strict schema validation
  -> RelaySCN artifact
  -> instruction cache candidate
```

Required invariants:

- control content never reaches the user, TTS, captions, or avatar speech,
- a malformed or missing control artifact does not invalidate an otherwise valid visible response,
- cache write occurs only after successful schema and policy validation,
- raw System Prompt text is not copied into the cache artifact,
- raw backend response text is not stored as the cache entry,
- durable candidates are not applied automatically.

### Non-stream MVP

The first implementation should support non-stream responses first:

```text
complete backend response
  -> split visible text / control envelope
  -> validate control JSON
  -> return visible text
  -> write validated cache entry
```

### Streaming follow-up

Streaming support belongs to the RelayCTX Stream Unpack phase.

The stream unpacker should:

- detect the control-envelope opening sentinel,
- hold a trailing buffer at least as long as the sentinel,
- stop forwarding bytes/chunks once an internal envelope is confirmed,
- collect the envelope internally until the closing sentinel,
- never leak partial control markers to the user or TTS,
- preserve already emitted visible text if the control envelope is malformed.

## Cache entry contract

A cache entry should contain only validated normalized state and metadata.

```json
{
  "schema_version": "relaylm.client_instruction_cache.v0",
  "instruction_hash": "sha256:...",
  "route_model": "relaylm-vtuber",
  "character_id": "rin",
  "parser_schema_version": "relaylm.client_instruction_parse.v1",
  "authority_policy_version": "relaylm.client_instruction_authority.v1",
  "parse_status": "valid",
  "scene_state": {
    "scene_type": "vtuber_roleplay",
    "scene_role": {
      "role_name": "cafe_staff",
      "role_scope": "scene",
      "role_source": "client_system",
      "confidence": 0.96
    },
    "scene_constraints": []
  },
  "durable_candidate_count": 0,
  "blocked_instruction_kinds": [],
  "raw_instruction_persisted": false,
  "raw_response_persisted": false
}
```

The cache is an instruction-interpretation cache, not a transcript store and not a persona store.

## Failure and retry behavior

Visible-response delivery and cache mutation are separate outcomes.

```text
valid visible response
+ invalid control artifact

  -> return visible response
  -> do not write cache
  -> record parse failure
```

Suggested failure record:

```json
{
  "parse_status": "failed",
  "retry_count": 1,
  "last_failure_reason": "invalid_schema",
  "cache_entry_written": false
}
```

A bounded retry policy should prevent reparsing forever:

```text
first parse failure
  -> allow one later first-pass retry

repeated failure
  -> use safe default/existing SCN state
  -> keep raw client instruction non-authoritative
  -> require explicit setup or repair for role-dependent behavior
```

Other failure behavior:

### Instruction conflicts with SOUL

```text
keep RelaySOUL identity
apply only compatible scene-role / scene-constraint elements
block durable overwrite
record conflict diagnostics
```

### Instruction attempts runtime or tool override

```text
block the override fragment
retain compatible scene-role fragments where safe
```

### SOUL is missing

```text
use safe SCN role/context for the current response when parsing succeeds
keep durable persona state as missing
create only an explicit RelaySOUL candidate when allowed
never persist the raw prompt as SOUL
```

## Replayed and changed prompts

Frontends commonly resend the same system prompt every turn.

RelayLM should therefore:

- use a cache hit for an unchanged normalized instruction,
- avoid forwarding the raw prompt again,
- avoid repeated RelaySOUL proposals,
- use the cached SCN artifact for subsequent turns.

When the normalized hash changes:

- treat the instruction as new current-scene evidence,
- run the first-pass interpretation again,
- allow the scene role or constraints to change,
- do not imply a durable identity change.

## Route behavior

### `pass_through`

```text
client owns message construction
RelayLM preserves client system/developer messages and history
no RelaySCN/RelaySOUL authority is asserted by this route
```

### RelayLM-managed route

```text
client messages
  -> canonicalization
  -> instruction hash/cache resolution
  -> RelaySCN normalized state
  -> RelayCTX reconstructed backend payload
```

Recommended configuration shape:

```yaml
client_history_policy: replace_with_relayctx
client_instruction_policy: relay_scn_first

client_instruction_cache_enabled: true
client_instruction_cache_root: .relaylm/client_instruction_cache
client_instruction_cache_max_entries: 256

client_instruction_first_pass_enabled: true
client_instruction_control_artifact_enabled: true
client_instruction_parse_retry_limit: 1

client_instruction_schema_version: v1
client_instruction_policy_version: v1

client_instruction_durable_candidate_enabled: false
```

Pass-through compatibility configuration:

```yaml
client_history_policy: trust_client
client_instruction_policy: trust_client
```

These are design keys until implemented and added to the formal config schema.

## Context packing order

Preferred managed-route packing:

```text
stable_prefix
  common runtime / safety policy
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

On an instruction-cache miss only, the one-time `client_instruction_evidence` block may appear in the dynamic suffix for first-pass parsing.

On a cache hit, the raw client instruction block must not appear.

## Runtime node mapping

Suggested node order:

```text
request_parse
  -> client_message_canonicalize
  -> current_turn_extract
  -> client_instruction_extract
  -> client_instruction_hash
  -> client_instruction_cache_lookup
  -> Input-side RelaySCN
  -> RelayINT
  -> RelayMEM Retrieval
  -> RelayCTX Repack
  -> Main LLM
  -> RelayCTX Unpack
  -> client_instruction_artifact_validate
  -> client_instruction_cache_write
```

Cache-hit path:

```text
cache lookup hit
  -> cached SCN artifact
  -> skip first-pass instruction parsing
  -> raw system/developer messages excluded
```

Cache-miss path:

```text
cache lookup miss
  -> raw instruction wrapped once as untrusted evidence
  -> Main LLM normal response + control artifact
  -> RelayCTX Unpack
  -> validate
  -> cache write
```

## Implementation phase mapping

```text
Phase 3 / RelayCTX Repack boundary hardening
  - client message canonicalization
  - current-turn extraction
  - instruction normalization/hash
  - cache lookup
  - cached SCN injection
  - raw client history/system exclusion

Phase 5 / non-stream RelayCTX Unpack
  - visible/control envelope separation
  - strict parse validation
  - cache write

Phase 5.5 / stream RelayCTX Unpack
  - trailing sentinel buffer
  - internal control-envelope suppression
  - no TTS/user leakage

Later RelaySOUL work
  - durable candidate review
  - explicit approval
  - persona revision creation
```

## Diagnostics

Suggested request diagnostics:

```json
{
  "client_instruction_policy": "relay_scn_first",
  "client_system_prompt_present": true,
  "client_developer_prompt_present": false,
  "instruction_hash_present": true,
  "instruction_cache_status": "hit|miss|disabled|invalid",
  "raw_instruction_forwarded_once": false,
  "client_instruction_classified": true,
  "scene_role_detected": true,
  "scene_role_source": "client_system",
  "scene_role_scope": "scene",
  "scene_constraints_count": 2,
  "durable_persona_candidate_count": 0,
  "relaysoul_proposal_allowed": false,
  "control_artifact_present": false,
  "cache_write_allowed": false,
  "client_instruction_overrode_existing_soul": false
}
```

Diagnostics must remain content-free and must not copy the raw client instruction or visible response text.

## Required smoke coverage

1. Client system/developer messages and prior history are excluded from normal backend context.
2. The current user turn remains present.
3. Unknown instruction hash produces exactly one first-pass evidence block.
4. The Main LLM returns visible text plus a structured control artifact on the first pass.
5. RelayCTX Unpack prevents control content from reaching user/TTS output.
6. A valid artifact creates a normalized cache entry.
7. An identical hash on the next request suppresses the raw client instruction and uses cached SCN.
8. Changed instruction text creates a cache miss and may update scene role.
9. Route, character, schema, or policy-version changes invalidate the cache key.
10. Invalid control artifacts do not block an otherwise valid visible response and do not write cache.
11. Runtime/safety override fragments are blocked while compatible role fragments may remain.
12. Existing SOUL remains authoritative during a conflicting role instruction.
13. Missing SOUL still permits a safe first-turn SCN role.
14. Durable candidate content never directly mutates SOUL.
15. Replayed prompts do not create repeated RelaySOUL proposals.
16. Pass-through mode retains existing client-owned behavior.
17. Streaming control markers never leak to the user, captions, or TTS.
18. Diagnostics and cache entries contain no raw prompt or response text.

## Final boundary

```text
Client messages are not backend context.

RelayLM extracts the current user turn and current instruction evidence,
removes client-owned history, resolves the instruction through a hash cache
and RelaySCN, and reconstructs the backend payload.

An unknown instruction may be shown to the Main LLM once so the normal
response and a structured SCN artifact can be produced together.

After that, the instruction hash resolves to cached SCN state and the raw
client system/developer prompt is no longer forwarded.
```

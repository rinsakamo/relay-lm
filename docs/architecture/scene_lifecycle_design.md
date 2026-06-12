# Scene Lifecycle Design

## Scope

This document defines how RelayLM should treat `scene_id`, `scene_state`, `scene_role`, `scene_context`, `scene_constraints`, `session_id`, and `room_id`.

It is a docs-only design note. It does not introduce runtime behavior changes.

## Goal

RelayLM treats Scene as the preferred dynamic situation concept. Room remains optional external host metadata.

```text
scene_id
  identifies the conversational situation or scenario

scene_state
  normalized dynamic prompt content for the current situation

scene_role
  identifies what function the character is performing in this scene

scene_context
  describes the current setting, task, participants, and situation

scene_constraints
  describes bounded response rules for this scene

session_id
  identifies a runtime conversation/session run

room_id
  optional external host metadata such as a room, stream, channel,
  or frontend conversation space
```

## Non-goals

This design does not add:

- automatic scene detection,
- runtime client-instruction parsing,
- instruction cache persistence,
- memory database writes,
- persona source mutation,
- forced `room_id` prompt blocks,
- hard request rejection when scene metadata is missing,
- automatic rewriting of legacy `room_anchor`,
- backend routing changes.

## Definitions

### `scene_id`

`scene_id` is a metadata identifier for the current conversational situation.

Examples:

- `default_chat`,
- `debugging_session`,
- `stream_qna`,
- `roleplay_cafe_scene`,
- `technical_support_mode`.

A scene may span multiple turns and may also span multiple sessions when the host or operator intentionally reuses it.

### `scene_state`

`scene_state` is normalized dynamic prompt content that describes the current situation.

It may include:

- current topic,
- current mood,
- open questions,
- recently discussed points,
- active viewer or group state,
- temporary scenario or mode,
- active role,
- scene setting and participants,
- scene-specific response constraints.

`scene_state` belongs in the dynamic suffix, not the stable persona prefix.

### `scene_role`

`scene_role` identifies what the character is doing in the current scene.

Examples:

- `technical_reviewer`,
- `stream_host`,
- `technical_interviewer`,
- `cafe_staff`,
- `game_commentator`.

A scene role is not durable identity.

```text
RelaySOUL:
  who the character is

scene_role:
  what the character is doing now
```

`scene_role` is also distinct from the OpenAI message `role` field.

Suggested shape:

```yaml
scene_role:
  role_name: technical_reviewer
  role_scope: scene
  role_source: client_instruction_cache
  confidence: 0.94
```

`role_scope` should initially be limited to:

```text
turn
scene
```

A role must not be silently promoted to durable persona state.

### `scene_context`

`scene_context` describes the present semantic setting.

Suggested fields:

```yaml
scene_context:
  setting: pull_request_review
  task: review_changed_files
  participants:
    - reviewer
    - repository_owner
```

Scene context may include:

- setting,
- current task,
- participants,
- event or stream segment,
- active object or document,
- current interaction mode.

It should remain compact and must not become a second conversation transcript.

### `scene_constraints`

`scene_constraints` contains normalized, bounded rules that apply only to the current turn or scene.

Example:

```yaml
scene_constraints:
  - constraint_type: ask_at_most_one_question
    value: true
  - constraint_type: spoken_response_length
    value: short
```

Typical sources include:

- route/profile configuration,
- operator-provided scene state,
- validated cached interpretation of the current client system/developer prompt,
- current scene transition policy.

Scene constraints are lower authority than RelayLM runtime/safety policy and approved durable persona policy.

### `session_id`

`session_id` identifies a runtime conversation/session run.

A new session may start when:

- the frontend starts a new chat,
- the stream starts or restarts,
- the user opens a new conversation thread,
- the adapter or operator explicitly resets session scope.

Session is operational. Scene is semantic.

### `room_id`

`room_id` is optional external host metadata.

Examples:

- frontend room ID,
- livestream channel ID,
- group chat ID,
- OpenWebUI conversation ID,
- Open-LLM-VTuber room or stage identity.

`room_id` may support scoping, diagnostics, and future memory boundaries, but it should not become prompt text by default.

## Boundary summary

```text
character_id:
  which durable persona is speaking

user_id / user_type:
  who the conversation counterpart is

scene_id:
  what semantic situation the conversation is in

scene_role:
  what role the character performs in that situation

scene_context:
  current setting, task, and participants

scene_constraints:
  temporary rules for the current situation

session_id:
  which runtime conversation run this is

room_id:
  where the conversation is hosted
```

## Scene-state source precedence

RelaySCN may receive scene evidence from several sources.

Recommended precedence:

```text
1. explicit trusted route/operator scene configuration
2. validated instruction-cache artifact for the current client instruction hash
3. explicit request metadata allowed by route policy
4. previous approved scene continuation state
5. current-turn heuristic/estimate
6. safe default or unknown scene
```

Raw client system/developer messages are not scene state by themselves. They must first pass the client-instruction authority flow:

```text
client instruction
  -> normalize / hash
  -> cache hit: validated cached SCN artifact
  -> cache miss: one-time Main LLM interpretation
  -> schema and policy validation
  -> normalized RelaySCN state
```

On a cache hit, the raw prompt is not compiled into backend context.

## Lifecycle

### 1. Scene start

A scene starts when the host, route, adapter, operator, or validated client-instruction artifact establishes a situation.

Initial MVP behavior may use:

```text
scene_id: default
scene_state: optional configured/cached state or none
```

Missing scene metadata should not block ordinary chat forwarding unless the active task requires a role or context for safe interpretation.

### 2. Scene update

`scene_state` may update when the current situation changes.

Examples:

- topic changes,
- open questions change,
- stream segment changes,
- roleplay scenario advances,
- temporary mode changes,
- group conversation state changes,
- client system/developer instruction hash changes,
- a new validated instruction artifact changes `scene_role` or constraints.

Scene updates are dynamic and must not rewrite stable persona files.

An unchanged instruction hash should reuse the cached SCN representation and should not create a new scene transition or RelaySOUL proposal by itself.

### 3. Scene continuation

A scene continues while the semantic situation remains the same.

The session may continue under the same scene, or a new session may reuse it when the host intentionally resumes it.

Repeated frontend system prompts with the same normalized hash normally confirm the current scene; they do not create new durable persona evidence.

### 4. Scene transition

A scene transition occurs when the current situation should be treated as different for context, memory scope, role, or diagnostics.

Examples:

```text
stream_qna -> technical_support_mode
roleplay_cafe_scene -> normal_chat
debugging_session -> release_planning
technical_interviewer -> normal_companion_role
```

A changed client instruction hash may propose a transition, but the validated semantic result determines whether a transition actually occurred.

Transition detection may be manual or host-provided in the MVP. Automatic transition detection remains future work.

### 5. Scene end

A scene ends when the host or operator closes the situation, resets scope, or starts a different semantic context.

Ending a scene should not automatically:

- delete memories,
- mutate persona sources,
- promote the prior scene role into RelaySOUL,
- preserve temporary client-derived constraints as durable policy.

## Client instruction and SOUL boundary

Client instruction content is SCN-first evidence.

```text
current role / setting / task / temporary constraint
  -> RelaySCN

durable name / identity / values / worldview candidate
  -> candidate evidence only
  -> explicit RelaySOUL proposal path when allowed
```

A client-derived scene role may guide current behavior even when SOUL is missing. This does not make the role a durable persona source.

Safety rule:

```text
Scene content may guide the current response,
but it must not redefine durable character identity.
```

## Scene-state placement

`scene_state` should be compiled after stable persona sources.

```text
stable_prefix
  common_runtime_policy
  SOUL.md
  OUTPUT_POLICY.md
  RELATIONSHIP_ANCHOR.md

slow_prefix
  STABLE_MEMORY_SUMMARY.md

dynamic_suffix
  normalized SCENE_STATE / scene_state
    - scene_type
    - scene_role
    - scene_context
    - scene_constraints
  retrieved_memory
  current user input
```

On an unknown client-instruction hash only, a one-time untrusted instruction-evidence block may also appear in the dynamic suffix for first-pass Main LLM interpretation. It must be absent on a cache hit.

## Legacy Room compatibility

### `room_state`

`room_state` is a legacy alias for `scene_state`.

If `scene_state` is unset and `room_state` exists, runtime may map `room_state` into `scene_state` for compatibility.

### `room_anchor`

`room_anchor` is optional legacy compatibility metadata. It may still appear in old configs, but it should not be required.

New designs should reclassify legacy room content by role:

```text
fixed shared constraints -> common_runtime_policy
character expression constraints -> OUTPUT_POLICY.md
relationship expectations -> RELATIONSHIP_ANCHOR.md
dynamic situation content -> SCENE_STATE.md / scene_state
current functional role -> scene_role
external host identity -> room_id metadata
```

## Memory scope implications

Scene can inform future memory retrieval, but scene state itself is not a memory record.

Suggested future memory scope dimensions:

```text
character_id
user_id / user_type
scene_id
session_id
room_id
memory_namespace
```

MVP safety rule: scene-aware memory scope should be diagnostics or candidate-selection metadata first. It should not cause memory writes until the memory-write path has explicit gates.

## Runtime compile implications

The Runtime Compile Gate should treat scene metadata as optional but useful.

- missing `scene_id` -> continue with default or null scene metadata,
- missing `scene_state` -> compile without a scene block,
- present validated `scene_state` -> place it in the dynamic suffix,
- cache-hit client instruction -> use cached normalized SCN state and exclude raw instruction,
- cache-miss client instruction -> permit one bounded untrusted evidence block only when first-pass parsing is enabled,
- present `room_id` -> keep it as metadata unless explicitly configured otherwise.

Compile diagnostics should record scene fields and their source without storing raw client instruction content.

## Diagnostics

Suggested fields:

```yaml
scene_id: default
scene_state_source: client_instruction_cache
scene_state_present: true
scene_role_present: true
scene_role_name: technical_reviewer
scene_role_scope: scene
scene_role_source: client_system
scene_context_present: true
scene_constraints_count: 2
client_instruction_hash_present: true
client_instruction_cache_status: hit
session_id: session_001
room_id: openwebui_conversation_123
scene_transition_detected: false
scene_fallback_reason: null
```

Diagnostics should not be inserted into stable prompt prefixes and should not include raw prompt content.

## Minimal MVP target

A minimal scene lifecycle implementation should support:

1. optional `scene_id` metadata,
2. optional normalized `scene_state` prompt content,
3. optional `scene_role`,
4. optional compact `scene_context`,
5. bounded `scene_constraints`,
6. validated client-instruction cache as a scene source,
7. legacy `room_state -> scene_state` alias,
8. optional `room_id` external host metadata,
9. content-free diagnostics for scene presence and source,
10. no hard failure when optional scene metadata is missing.

## Future extensions

Future work can add:

- explicit scene transition events,
- scene-aware memory retrieval scope,
- scene compression under token pressure,
- scene summary generation,
- operator-visible scene diagnostics,
- scene handoff between frontends,
- scene-specific compile-gate thresholds,
- automatic role-transition detection,
- RelayTRC lineage for scene transitions.

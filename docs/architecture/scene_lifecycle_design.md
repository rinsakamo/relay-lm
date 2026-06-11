# Scene Lifecycle Design

## Scope

This document defines how RelayLM should treat `scene_id`, `scene_state`, `session_id`, and `room_id`.

It is a docs-only design note. It does not introduce runtime behavior changes.

## Goal

RelayLM now treats Scene as the preferred dynamic situation concept. Room should remain optional external host metadata.

This design fixes the boundary:

```text
scene_id
  identifies the conversational situation or scenario

scene_state
  dynamic prompt content for the current situation

session_id
  identifies a runtime conversation/session run

room_id
  optional external host metadata such as a room, stream, channel, or frontend conversation space
```

## Non-goals

This design does not add:

- automatic scene detection
- memory database writes
- persona source mutation
- forced `room_id` prompt blocks
- hard request rejection when scene metadata is missing
- automatic rewriting of legacy `room_anchor`
- backend routing changes

## Definitions

### scene_id

`scene_id` is a metadata identifier for the current conversational situation.

Examples:

- `default_chat`
- `debugging_session`
- `stream_qna`
- `roleplay_cafe_scene`
- `technical_support_mode`

A scene may span multiple turns and may also span multiple sessions if the host or operator intentionally reuses it.

### scene_state

`scene_state` is dynamic prompt content that describes the current situation.

It may include:

- current topic
- current mood
- open questions
- recently discussed points
- active viewer or group state
- temporary scenario or mode
- scene-specific response constraints

`scene_state` is prompt content. It belongs in the dynamic suffix, not stable persona prefix.

### session_id

`session_id` identifies a runtime conversation/session run.

A new session may start when:

- the frontend starts a new chat
- the stream starts or restarts
- the user opens a new conversation thread
- the adapter or operator explicitly resets session scope

Session is operational. Scene is semantic.

### room_id

`room_id` is optional external host metadata.

Examples:

- frontend room ID
- livestream channel ID
- group chat ID
- OpenWebUI conversation ID
- Open-LLM-VTuber room or stage identity

`room_id` should be available for scoping, diagnostics, and future memory boundaries, but it should not become prompt text by default.

## Boundary summary

```text
character_id:
  which persona is speaking

user_id / user_type:
  who the conversation counterpart is

scene_id:
  what situation the conversation is in

scene_state:
  current dynamic situation content

session_id:
  which runtime conversation run this is

room_id:
  where the conversation is hosted
```

## Lifecycle

### 1. Scene start

A scene starts when the host, route, adapter, or operator establishes a situation.

Initial MVP behavior may use a default scene:

```text
scene_id: default
scene_state: optional configured file or none
```

Missing scene metadata should not block normal chat forwarding.

### 2. Scene update

`scene_state` may update when the current situation changes.

Examples:

- topic changes
- open questions change
- stream segment changes
- roleplay scenario advances
- temporary mode changes
- group conversation state changes

Scene updates are dynamic and should not rewrite stable persona files.

### 3. Scene continuation

A scene continues while the situation remains semantically the same.

The session may continue under the same scene, or a new session may reuse the same scene if the host intentionally resumes it.

### 4. Scene transition

A scene transition happens when the current situation should be treated as different for context, memory scope, or diagnostics.

Transition examples:

```text
stream_qna -> technical_support_mode
roleplay_cafe_scene -> normal_chat
debugging_session -> release_planning
```

Transition detection may be manual or host-provided in the MVP. Automatic scene detection is future work.

### 5. Scene end

A scene ends when the host or operator closes the situation, resets scope, or starts a different semantic context.

Ending a scene should not automatically delete memories or mutate persona sources.

## Scene state placement

`scene_state` should be compiled after stable persona sources.

Preferred placement:

```text
stable_prefix
  common_runtime_policy
  SOUL.md
  OUTPUT_POLICY.md
  RELATIONSHIP_ANCHOR.md

slow_prefix
  STABLE_MEMORY_SUMMARY.md

dynamic_suffix
  SCENE_STATE.md / scene_state
  retrieved_memory
  recent_turns
  latest_input
```

Safety rule: scene content may guide the current response, but should not redefine the character identity.

## Legacy Room compatibility

### room_state

`room_state` is a legacy alias for `scene_state`.

If `scene_state` is unset and `room_state` exists, runtime may map `room_state` into `scene_state` for compatibility.

### room_anchor

`room_anchor` is optional legacy compatibility metadata. It may still appear in old configs, but it should not be required.

New designs should reclassify legacy room content by role:

```text
fixed shared constraints -> common_runtime_policy
character expression constraints -> OUTPUT_POLICY.md
relationship expectations -> RELATIONSHIP_ANCHOR.md
dynamic situation content -> SCENE_STATE.md / scene_state
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

MVP safety rule: scene-aware memory scope should be diagnostic or candidate-selection metadata first. It should not cause memory writes until the memory write path has explicit gates.

## Runtime compile implications

The Runtime Compile Gate should treat scene metadata as optional but useful.

- missing `scene_id` -> continue with default or null scene metadata
- missing `scene_state` -> compile without scene block
- present `scene_state` -> place in dynamic suffix
- present `room_id` -> keep as metadata unless explicitly configured otherwise

Compile diagnostics should record scene fields when available.

## Diagnostics

Suggested diagnostics fields:

```yaml
scene_id: default
scene_state_source: ./scenes/default/SCENE_STATE.md
scene_state_present: true
session_id: session_001
room_id: openwebui_conversation_123
scene_transition_detected: false
scene_fallback_reason: null
```

Diagnostics should not be inserted into stable prompt prefixes.

## Minimal MVP target

A minimal scene lifecycle implementation should support:

1. optional `scene_id` metadata
2. optional `scene_state` prompt content
3. legacy `room_state -> scene_state` alias
4. optional `room_id` external host metadata
5. diagnostics for scene presence and source
6. no hard failure when scene metadata is missing

## Future extensions

Future work can add:

- explicit scene transition events
- scene-aware memory retrieval scope
- scene compression under token pressure
- scene summary generation
- operator-visible scene diagnostics
- scene handoff between frontends
- scene-specific compile gate thresholds
- RelayTRC lineage for scene transitions

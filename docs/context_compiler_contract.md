# RelayLM Context Compiler Contract

RelayLM should treat prompt construction as context compilation, not simple prompt concatenation.

The context compiler turns route, character, memory, room/scene, and request information into an OpenAI-compatible message list.

## Goals

The compiler should preserve:

- persona stability
- memory usefulness
- low latency
- TTS/Live2D-friendly output
- backend prefix/KV cache reuse
- final-response naturalness for persona-oriented conversations

## Inputs

The compiler receives:

- runtime mode
- route config
- character profile
- common runtime policy
- room anchor
- room/scene state
- incoming OpenAI-compatible messages
- lightweight memory candidates
- optional retrieved memory, RAG, or spill chunks
- optional agent result summary for final-response shaping
- token budget hints

## Output

The compiler returns:

- OpenAI-compatible `messages`
- selected backend model
- packing diagnostics for logs and debugging

Initial output strategy:

```text
system:
  compiled RelayLM context

recent user/assistant turns:
  bounded recent turns when preserved outside the compiled block

latest user:
  latest input near the end
```

The first implementation may put the full compiled context into one system message. Backend adapters may later split the layout differently for models that benefit from separate system, developer, or user blocks.

## Stability groups

The compiler should group context blocks by stability.

```text
stable_prefix
  common_runtime_policy
  character_soul_anchor
  character_output_policy
  relationship_anchor
  room_anchor

slow_prefix
  stable_memory_summary
  durable_user_memory
  durable_character_memory

dynamic_suffix
  room_state / scene_state
  retrieved_memory
  retrieved_rag
  agent_result_summary
  tool_observations
  recent_turns
  latest_input
  response_instruction
```

### Stable Persona Prefix

Stable persona prefix blocks should remain byte-for-byte stable when possible.

Rules:

- no timestamps
- no memory counts
- no random IDs
- no current topic
- no retrieved snippets
- no volatile metadata

Purpose:

- preserve character identity
- improve per-character prefix/KV cache reuse
- avoid dynamic memory changing the character's personality
- provide the source prefix for future Persona Anchor KV

### Slow Memory Prefix

Slow prefix blocks may change, but not every turn.

Examples:

- relationship anchor
- durable user facts
- durable character facts
- stable memory summary

Update cadence should be slow, such as after a stream, after a session, or when a durable fact changes.

### Dynamic Conversation Context

Dynamic suffix blocks may change every turn.

Examples:

- current topic
- scene state
- room mood
- retrieved memories
- RAG evidence
- agent result summaries
- tool observations for final natural-language response synthesis
- recent turns
- latest user input

Dynamic content should appear after SOUL and OUTPUT_POLICY so memory/RAG/tool observations do not override persona.

## Persona Anchor KV

Persona Anchor KV is the backend-specific runtime representation of the stable persona prefix. The source of truth remains the persona files and rendered prompt text. RelayLM should optimize layout and diagnostics for a stable persona prefix without mutating backend KV cache in the MVP.

## ContextBlock

The compiler should use an internal block representation before rendering to messages.

Suggested fields:

```yaml
block_id: character_soul_anchor
block_type: character_soul_anchor
stability_class: stable_prefix
source: ./characters/mili/SOUL.md
content: "..."
token_budget_hint: 800
include_in_prefix_cache_target: true
```

### block_id

Stable identifier for diagnostics.

Examples:

- `common_runtime_policy`
- `character_soul_anchor`
- `character_output_policy`
- `relationship_anchor`
- `room_anchor`
- `stable_memory_summary`
- `room_state`
- `retrieved_memory`
- `retrieved_rag`
- `agent_result_summary`
- `tool_observations`
- `recent_turns`
- `latest_input`
- `response_instruction`

### block_type

Semantic role of the block.

This should be stable across implementations so logs and tests remain readable.

### stability_class

One of:

- `stable_prefix`
- `slow_prefix`
- `dynamic_suffix`

### source

Human-readable source reference.

Examples:

- config path
- incoming system prompt
- local memory store
- RAG source
- external memory adapter
- agent framework result
- OpenAI request messages

### content

Rendered text content.

The compiler should avoid injecting dynamic metadata into stable blocks.

### token_budget_hint

Approximate token budget for this block.

The first implementation may use character counts or skip enforcement. Later implementations should use tokenizer-aware budgeting.

### include_in_prefix_cache_target

Boolean hint for whether this block should be kept stable for backend prefix/KV reuse.

This does not mutate backend KV cache. It only guides layout and diagnostics.

## Rendering strategy

RelayLM should start with simple XML-like tags.

```xml
<relaylm_context version="1">
  <common_runtime_policy>...</common_runtime_policy>
  <character_soul_anchor>...</character_soul_anchor>
  <character_output_policy>...</character_output_policy>
  <relationship_anchor>...</relationship_anchor>
  <room_anchor>...</room_anchor>
  <stable_memory_summary>...</stable_memory_summary>
  <room_state>...</room_state>
  <retrieved_memory>...</retrieved_memory>
  <retrieved_rag>...</retrieved_rag>
  <agent_result_summary>...</agent_result_summary>
  <recent_turns>...</recent_turns>
  <latest_input>...</latest_input>
  <response_instruction>...</response_instruction>
</relaylm_context>
```

Tags should be limited and stable. Do not use tokenizer-specific special tokens in the MVP.

Machine-facing contracts such as memory adapter output, fusion plans, diagnostics, traces, and agent/tool protocol payloads should remain JSON/dataclass-shaped. JSON is for machine contracts; tags are for persona/context conditioning.

## OpenAI message packing

Initial strategy:

1. Extract incoming system prompt as fallback SOUL if configured SOUL is absent.
2. Extract latest user input.
3. Preserve bounded recent turns.
4. Compile stable prefix, slow prefix, and dynamic suffix.
5. Send the compiled context as a system message.
6. Keep latest user input near the end.

For `pass_through`, skip compilation and preserve messages.

For `memory_light`, compile stable character blocks and lightweight memory.

For `memory_full`, compile full memory/RAG/spill/compression results with budget control.

For future agent integrations, internal planning/tool/structured-output requests should default to pass-through. Final natural-language responses may use persona/context repacking.

## Room anchor, room state, and scene state

`room_anchor` is fixed room protocol and constraints only.

Examples:

- this is a live conversation room
- keep replies speakable
- avoid exposing internal retrieval tags
- handle multiple speakers according to configured rules

`room_state` is dynamic.

Examples:

- current topic
- current stream mood
- open questions
- recently discussed points
- active viewer or group state

`scene_id` and scene state identify the conversational situation or scenario. `room_id` identifies the channel, room, stream, or frontend conversation space. `room_id` is where the conversation is hosted; `scene_id` is what situation the conversation is in.

Do not place room state or scene state into stable prefix.

## Identity and scope boundaries

RelayLM should use simple operator-facing identity names:

- `character_id`: which persona is speaking.
- `user_id`: the conversation counterpart identity. This may represent a registered user, guest, viewer, operator, anonymous visitor, or agent caller.
- `user_type`: the identity class, such as `user`, `guest`, `viewer`, `operator`, `anonymous`, or `agent`.
- `room_id`: the channel, room, stream, or frontend conversation space.
- `scene_id`: the conversational situation or scenario.
- `session_id`: the current conversation/session run.

These fields should be available to memory adapters and diagnostics so memory does not leak across users, scenes, rooms, characters, or agent callers.

## Character and cache boundaries

Cross-character KV cache sharing should be treated as limited.

The main target is per-character prefix stability:

- stable character files
- stable cache namespace
- stable model route
- stable backend model mapping
- stable persona prefix hash

Per-character RelayLM instances may be used for speed-sensitive deployments. Single-proxy routing remains the onboarding default.

## Diagnostics

The compiler should eventually log:

- selected route
- character ID
- user ID and user type when available
- room ID, scene ID, and session ID when available
- runtime mode
- block IDs
- stability classes
- approximate token or character budgets
- whether pass-through or compilation was used
- fallback SOUL source
- omitted blocks and reasons
- stable prefix hash and prefix stability changes

Diagnostics should not be inserted into stable prompt prefixes.
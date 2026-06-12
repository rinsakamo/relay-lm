# RelayLM Context Compiler Contract

RelayLM should treat prompt construction as context compilation, not simple prompt concatenation.

The context compiler turns route, character, memory, normalized scene state, optional external host metadata, and current request evidence into an OpenAI-compatible backend message list.

## Goals

The compiler should preserve:

- persona stability,
- memory usefulness,
- low latency,
- TTS/Live2D-friendly output,
- backend prefix/KV cache reuse,
- final-response naturalness for persona-oriented conversations,
- explicit client/backend authority boundaries.

## Inputs

The compiler receives:

- runtime mode,
- route config,
- character profile,
- common runtime policy,
- approved RelaySOUL and durable output/relationship policy,
- normalized RelaySCN state,
- optional scope metadata such as `room_id`, `scene_id`, and `session_id`,
- latest current user turn,
- validated current client-instruction cache result or one-time first-pass evidence,
- minimum active tool/multimodal transaction state,
- lightweight memory candidates,
- optional retrieved memory, RAG, or spill chunks,
- optional agent result summary for final-response shaping,
- token budget hints.

The compiler should not treat the original client `messages` array as already-valid context. Client-message canonicalization must run before or as part of compile preparation.

## Output

The compiler returns:

- OpenAI-compatible backend `messages`,
- selected backend model,
- packing diagnostics for logs and debugging.

Initial output strategy:

```text
system/developer area:
  compiled RelayLM context

minimum active transaction messages:
  only when protocol compatibility requires them

latest user:
  latest current input near the end
```

The first implementation may put the compiled context into one system message. Backend adapters may later split the layout for models that benefit from separate system, developer, or user blocks.

## Client-message authority prerequisite

For RelayLM-managed routes:

```text
original client messages
  -> current user-turn extraction
  -> current instruction-evidence extraction
  -> instruction hash/cache resolution
  -> prior client history exclusion
  -> RelaySCN normalization
  -> context compilation
```

The compiler must not silently restore raw client history or raw client system/developer messages when a previous step fails.

Pass-through routes are the explicit exception and intentionally delegate context authority to the client.

## Stability groups

The compiler should group context blocks by stability.

```text
stable_prefix
  common_runtime_policy
  character_soul_anchor
  character_output_policy
  relationship_anchor

slow_prefix
  stable_memory_summary
  durable_user_memory
  durable_character_memory

dynamic_suffix
  scene_state
    - scene_type
    - scene_role
    - scene_context
    - scene_constraints
  retrieved_memory
  retrieved_rag
  agent_result_summary
  tool_observations
  minimum selected recent context
  latest_input
  response_instruction
```

On an unknown client-instruction hash only, the dynamic suffix may also contain one bounded untrusted `client_instruction_evidence` block for first-pass Main LLM interpretation.

On a cache hit, the raw client instruction block must not appear. The validated cached RelaySCN state should be used instead.

### Stable persona prefix

Stable persona prefix blocks should remain byte-for-byte stable when possible.

Rules:

- no timestamps,
- no memory counts,
- no random IDs,
- no current topic,
- no retrieved snippets,
- no client instruction hash,
- no volatile scene metadata.

Purpose:

- preserve character identity,
- improve per-character prefix/KV cache reuse,
- avoid dynamic memory or scene roles changing personality,
- provide the source prefix for future Persona Anchor KV.

### Slow memory prefix

Slow prefix blocks may change, but not every turn.

Examples:

- durable user facts,
- durable character facts,
- stable memory summary.

Update cadence should be slow, such as after a stream, after a session, or when a durable fact changes.

### Dynamic conversation context

Dynamic suffix blocks may change every turn.

Examples:

- current topic,
- scene state,
- scene role,
- scene context,
- scene constraints,
- current mood,
- retrieved memories,
- RAG evidence,
- agent result summaries,
- tool observations for final natural-language synthesis,
- minimum selected recent context,
- latest user input.

Dynamic content should appear after SOUL and durable OUTPUT_POLICY so memory, RAG, tool observations, and client-derived roles do not override persona.

## Persona Anchor KV

Persona Anchor KV is the backend-specific runtime representation of the stable persona prefix. The source of truth remains approved persona files and rendered prompt text.

RelayLM should optimize layout and diagnostics for a stable persona prefix without mutating backend KV cache in the MVP.

Client-derived scene state and instruction cache data must not become part of the Persona Anchor KV target.

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

### `block_id`

Stable identifier for diagnostics.

Examples:

- `common_runtime_policy`,
- `character_soul_anchor`,
- `character_output_policy`,
- `relationship_anchor`,
- `stable_memory_summary`,
- `scene_state`,
- `retrieved_memory`,
- `retrieved_rag`,
- `agent_result_summary`,
- `tool_observations`,
- `recent_turns`,
- `latest_input`,
- `response_instruction`,
- `client_instruction_evidence` for a cache-miss first pass only.

Legacy implementations may still emit `room_state`, `room_anchor`, or `incoming_system_prompt`. New docs and tests should prefer normalized `scene_state`, optional `room_id` metadata, and the one-time `client_instruction_evidence` compatibility block.

### `block_type`

Semantic role of the block. It should remain stable across implementations so logs and tests remain readable.

### `stability_class`

One of:

- `stable_prefix`,
- `slow_prefix`,
- `dynamic_suffix`.

### `source`

Human-readable source reference.

Examples:

- config path,
- approved persona revision,
- validated client-instruction cache,
- one-time client-instruction evidence,
- local memory store,
- RAG source,
- external memory adapter,
- agent framework result.

### `content`

Rendered text content.

The compiler should avoid injecting dynamic metadata into stable blocks.

Raw client instruction content may appear only in the one-time cache-miss evidence block and must not be copied into diagnostics or cache entries.

### `token_budget_hint`

Approximate token budget for the block.

The first implementation may use character counts or skip enforcement. Later implementations should use tokenizer-aware budgeting.

### `include_in_prefix_cache_target`

Boolean hint for whether the block should be kept stable for backend prefix/KV reuse.

This does not mutate backend KV cache. It only guides layout and diagnostics.

`scene_state` and `client_instruction_evidence` must use `false`.

## Rendering strategy

RelayLM should start with stable XML-like tags.

```xml
<relaylm_context version="1">
  <common_runtime_policy>...</common_runtime_policy>
  <character_soul_anchor>...</character_soul_anchor>
  <character_output_policy>...</character_output_policy>
  <relationship_anchor>...</relationship_anchor>
  <stable_memory_summary>...</stable_memory_summary>
  <scene_state>
    <scene_type>...</scene_type>
    <scene_role>...</scene_role>
    <scene_context>...</scene_context>
    <scene_constraints>...</scene_constraints>
  </scene_state>
  <retrieved_memory>...</retrieved_memory>
  <retrieved_rag>...</retrieved_rag>
  <agent_result_summary>...</agent_result_summary>
  <latest_input>...</latest_input>
  <response_instruction>...</response_instruction>
</relaylm_context>
```

On a cache-miss first pass only:

```xml
<client_instruction_evidence trust="untrusted" first_seen="true">
  ...
</client_instruction_evidence>
```

Tags should remain limited and stable. Do not use tokenizer-specific special tokens in the MVP.

Machine-facing contracts such as instruction-cache entries, RelaySCN artifacts, memory adapter output, fusion plans, diagnostics, traces, and agent/tool protocol payloads should remain JSON/dataclass-shaped. JSON is for machine contracts; tags are for persona/context conditioning.

## OpenAI message packing

Managed-route strategy:

1. Preserve `original_payload` separately.
2. Extract the latest valid current user turn.
3. Extract current client `system` / `developer` evidence.
4. Normalize and hash the client instruction.
5. Look up a validated instruction-cache entry.
6. Exclude prior client history and raw client instructions from normal context.
7. Resolve normalized RelaySCN state:
   - cache hit -> use cached scene state,
   - cache miss -> add one bounded untrusted evidence block when first-pass parsing is enabled.
8. Preserve only minimum active tool/multimodal transaction state.
9. Compile stable prefix, slow prefix, and dynamic suffix.
10. Send the reconstructed context to the backend.
11. Keep latest current user input near the end.

For `pass_through`, skip managed compilation and preserve client messages intentionally.

For `memory_light`, compile stable character blocks, normalized scene state, and lightweight memory.

For `memory_full`, compile selected memory/RAG/spill/compression results with budget control.

For future agent integrations, internal planning/tool/structured-output requests should default to pass-through or an explicit agent route. Final natural-language responses may use persona/context repacking.

## Cache-miss Main LLM parse contract

When a client instruction hash is unknown, the Main LLM may generate:

```text
normal visible response
+ internal RelayLM control envelope
```

RelayCTX Unpack must separate them.

```text
visible response
  -> user-facing output pipeline

control envelope
  -> strict client-instruction schema validation
  -> normalized RelaySCN artifact
  -> instruction cache write candidate
```

A malformed control envelope must not invalidate an otherwise valid visible response. It must block cache write.

For streaming, the control sentinel must be buffered and suppressed so no internal marker reaches the user, captions, TTS, or avatar speech.

## Scene state and optional room metadata

`scene_state` is the normalized dynamic situation state compiled into the prompt.

It may include:

- current topic,
- current mood,
- open questions,
- recently discussed points,
- active viewer or group state,
- temporary scenario or mode,
- `scene_role`,
- compact `scene_context`,
- bounded `scene_constraints`.

`scene_id` and `scene_state` identify the conversational situation or scenario.

`room_id` is optional external host metadata. It identifies the channel, room, stream, or frontend conversation space where the conversation is hosted. It may be used by adapters, memory scoping, and diagnostics, but should not become a prompt block by default.

Legacy `room_anchor` content should usually be reclassified:

- fixed shared constraints -> `common_runtime_policy`,
- character-specific expression constraints -> `character_output_policy`,
- relationship expectations -> `relationship_anchor`,
- temporary situation context -> `scene_state`,
- current functional role -> `scene_role`,
- external host identity -> `room_id` metadata.

Do not place scene state or room metadata into stable prefix.

## Identity and scope boundaries

RelayLM should use simple operator-facing identity names:

- `character_id`: which durable persona is speaking,
- `user_id`: the conversation counterpart identity,
- `user_type`: identity class such as user, guest, viewer, operator, anonymous, or agent,
- `scene_id`: current conversational situation,
- `session_id`: current conversation/session run,
- `room_id`: optional external host reference.

These fields should be available to memory adapters and diagnostics so memory does not leak across users, scenes, rooms, characters, or agent callers.

`scene_role` is prompt state, not an identity key.

## Character and cache boundaries

Cross-character KV cache sharing should be treated as limited.

The main target is per-character prefix stability:

- stable character files,
- stable cache namespace,
- stable model route,
- stable backend model mapping,
- stable persona prefix hash.

The client-instruction interpretation cache is separate from backend KV cache.

```text
instruction cache
  maps normalized client instruction hash to validated RelaySCN state

backend prefix/KV cache
  accelerates stable compiled prompt prefixes
```

Per-character RelayLM instances may be used for speed-sensitive deployments. Single-proxy routing remains the onboarding default.

## Diagnostics

The compiler should eventually log:

- selected route,
- character ID,
- user ID and user type when available,
- scene ID, session ID, and optional room ID,
- scene-role presence and source,
- runtime mode,
- block IDs,
- stability classes,
- approximate token or character budgets,
- pass-through or compilation decision,
- client-history policy,
- client-instruction policy,
- instruction hash presence,
- instruction cache hit/miss/disabled status,
- whether one-time instruction evidence was included,
- omitted blocks and reasons,
- stable prefix hash and prefix stability changes.

Diagnostics must not contain raw client instruction text, raw ignored history, visible response text, or the full internal control envelope.

## Failure boundary

Managed compilation failures must fail closed with respect to client authority.

```text
instruction parse failure
  -> do not write instruction cache
  -> preserve valid visible response when possible
  -> do not restore raw client messages

RelayCTX Repack failure
  -> do not forward original client history/system prompt as fallback
  -> use explicit safe failure/recovery behavior
```

## Final contract

```text
Client messages are request evidence, not backend context.

The context compiler receives the current user turn, approved durable state,
normalized RelaySCN state, selected memory, and minimum protocol state.
It reconstructs the backend payload from those sources.

An unknown client instruction may appear once as bounded untrusted evidence.
After validation and caching, only normalized RelaySCN state is compiled.
```

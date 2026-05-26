# RelayLM Config Schema

This document defines the initial YAML config shape for the RelayLM runtime MVP.

The schema should support URL-swap onboarding first, then grow into memory-aware context packing.

## Example

```yaml
mode: pass_through

listen:
  host: 127.0.0.1
  port: 8090

common_runtime_policy: ./policies/common_runtime_policy.md

backends:
  vllm_main:
    type: openai_compatible
    base_url: http://127.0.0.1:8000/v1
    api_key: dummy
    default_model: Qwen/Qwen2.5-Coder-7B-Instruct-AWQ

model_routes:
  relaylm-mili:
    character_id: mili
    backend: vllm_main
    backend_model: Qwen/Qwen2.5-Coder-7B-Instruct-AWQ
    mode: memory_light
    cache_namespace: character/mili
    memory_namespace: character/mili

  relaylm-zero:
    character_id: zero
    backend: vllm_main
    backend_model: Qwen/Qwen2.5-Coder-7B-Instruct-AWQ
    mode: pass_through
    cache_namespace: character/zero
    memory_namespace: character/zero

characters:
  mili:
    soul: ./characters/mili/SOUL.md
    output_policy: ./characters/mili/OUTPUT_POLICY.md
    room_anchor: ./rooms/default/ROOM_ANCHOR.md
    relationship_anchor: ./characters/mili/RELATIONSHIP_ANCHOR.md
    stable_memory_summary: ./characters/mili/STABLE_MEMORY_SUMMARY.md
    scene_state: ./scenes/default/SCENE_STATE.md

memory:
  default_store: local_jsonl
  stores:
    local_jsonl:
      type: jsonl
      path: ./memory
```

## Top-level fields

### mode

Default runtime mode.

Allowed initial values:

- `pass_through`
- `memory_light`
- `memory_full`

A route-level mode may override this value.

### listen

Server bind settings.

```yaml
listen:
  host: 127.0.0.1
  port: 8090
```

The default port should be easy to use as an Open-LLM-VTuber OpenAI-compatible API URL:

```text
http://localhost:8090/v1
```

### common_runtime_policy

Path to a short shared policy block used by all characters.

This should include shared constraints such as:

- do not reveal internal tags
- keep responses suitable for TTS
- avoid overly long paragraphs unless requested
- return speakable final text

This is not a character identity file.

### scene state and room metadata

`scene_state` is the preferred dynamic situation file for context compilation.

It may include:

- current topic
- current stream mood
- open questions
- recent stream state
- current group conversation state
- temporary scenario or mode

Because it is dynamic, it should appear after stable prefix blocks in the compiled context.

`room_id` may be used as optional scope metadata for an external host such as a channel, room, stream, or frontend conversation space. It is not a prompt block by default.

Current runtime compatibility note: `room_anchor` is still required by `CharacterConfig` in current releases, so runnable config examples should keep it until the runtime makes it optional or provides a migration alias. New designs should avoid putting dynamic topic, mood, viewer question, recent event, or volatile stream state into `room_anchor`.

Legacy `room_anchor` content should usually move to `common_runtime_policy`, `character_output_policy`, `relationship_anchor`, `scene_state`, or optional `room_id` metadata depending on its role.

## backends

`backends` defines OpenAI-compatible upstream servers.

```yaml
backends:
  vllm_main:
    type: openai_compatible
    base_url: http://127.0.0.1:8000/v1
    api_key: dummy
    default_model: Qwen/Qwen2.5-Coder-7B-Instruct-AWQ
```

Initial backend type:

- `openai_compatible`

Future backend adapters may add backend-specific capabilities, but the MVP should only depend on normal OpenAI-compatible chat completion semantics.

## model_routes

`model_routes` maps incoming OpenAI-compatible `model` names to RelayLM runtime routes.

```yaml
model_routes:
  relaylm-mili:
    character_id: mili
    backend: vllm_main
    backend_model: Qwen/Qwen2.5-Coder-7B-Instruct-AWQ
    mode: memory_light
    cache_namespace: character/mili
    memory_namespace: character/mili
```

Fields:

- `character_id`: character profile key
- `backend`: backend key
- `backend_model`: model name sent to the backend
- `mode`: optional route-level mode override
- `cache_namespace`: namespace used for prefix/cache-aware layout and future metrics
- `memory_namespace`: namespace used for character/viewer memory

Model-name routing is the preferred MVP mechanism because it requires no Open-LLM-VTuber code changes.

## characters

`characters` defines character profile files.

```yaml
characters:
  mili:
    soul: ./characters/mili/SOUL.md
    output_policy: ./characters/mili/OUTPUT_POLICY.md
    room_anchor: ./rooms/default/ROOM_ANCHOR.md
    relationship_anchor: ./characters/mili/RELATIONSHIP_ANCHOR.md
    stable_memory_summary: ./characters/mili/STABLE_MEMORY_SUMMARY.md
    scene_state: ./scenes/default/SCENE_STATE.md
```

### soul

`SOUL.md` defines the character identity, values, worldview, personality, and stable speaking identity.

It should not contain volatile data such as timestamps, retrieved memory, memory counts, or current topics.

### output_policy

`OUTPUT_POLICY.md` defines how the character expresses itself.

It may include:

- emotional style
- response length
- TTS-friendly style
- Live2D expression tendencies
- casual mode, technical mode, MC mode, or other expression modes

This is character-specific.

### room_anchor

Current-runtime required legacy field for fixed room constraints.

Keep this field in runnable examples until `room_anchor` becomes optional or a migration alias is implemented. It should not contain dynamic scene information such as current topic, mood, recent events, current viewer question, or volatile stream state.

### relationship_anchor

Stable relationship context with the viewer, user, or relevant counterpart.

It should change slowly and should not be rewritten every turn.

### stable_memory_summary

Durable memory facts and ongoing long-term context.

This is separate from relationship tone.

### scene_state

Dynamic current scene state.

This may include:

- current topic
- current stream mood
- open questions
- recent stream state
- current group conversation state
- temporary scenario or mode

Because it is dynamic, it should appear after stable prefix blocks in the compiled context.

## memory

Initial memory config should allow a lightweight local store.

```yaml
memory:
  default_store: local_jsonl
  stores:
    local_jsonl:
      type: jsonl
      path: ./memory
```

The first runtime should support simple local memory or no memory. Embeddings, vector databases, rerankers, and summarizers should be later extensions behind the same memory interface.

## Config design rules

- Prefer explicit model routes over prompt inference.
- Keep character profile paths stable.
- Keep cache and memory namespaces first-class.
- Allow per-route mode overrides.
- Prefer `scene_state` for dynamic context and keep `room_id` as optional external host metadata.
- Keep `room_anchor` in runnable examples until runtime compatibility makes it optional.
- Do not require SOUL files for pass-through compatibility.
- Use incoming system prompts as a fallback SOUL source when character files are absent.

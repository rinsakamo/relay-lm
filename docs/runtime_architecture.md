# RelayLM Runtime Architecture

RelayLM is a persona-specialized OpenAI-compatible Memory Context Proxy for Open-LLM-VTuber and other local LLM frontends.

The first runtime goal is URL-swap compatibility:

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible backend
```

RelayLM should make an AI character feel memoryful, persona-stable, and conversationally continuous while keeping the frontend unchanged.

RelayLM is not an agent framework or a memory database. It controls what the backend model sees before generation so persona, relationship, memory, and recent context can be shaped without taking over tool workflows or memory-product responsibilities.

## Runtime layers

RelayLM should keep the runtime split into explicit layers so the initial pass-through proxy can grow into memory-aware context packing without a rewrite.

```text
OpenAI-compatible API layer
  -> Routing layer
  -> Character profile layer
  -> Memory / retrieval layer
  -> Context compiler layer
  -> Backend adapter layer
```

### OpenAI-compatible API layer

Responsibilities:

- expose `/v1/chat/completions`
- expose `/v1/models`
- accept OpenAI-compatible request bodies from Open-LLM-VTuber
- preserve streaming behavior for low-latency speech
- return backend-compatible error payloads where practical

This layer should not own memory, persona loading, retrieval, or backend-specific optimization.

### Routing layer

Responsibilities:

- resolve the incoming `model` name to a RelayLM route
- select the backend
- select the character profile
- select the cache namespace and memory namespace
- map the RelayLM model name to the backend model name when configured

Model-name routing is the primary MVP mechanism because Open-LLM-VTuber can change the model field without code changes.

### Character profile layer

Responsibilities:

- load character identity and expression policy
- resolve `SOUL.md`
- resolve `OUTPUT_POLICY.md`
- resolve relationship anchors and stable memory summaries
- expose a stable profile object to the context compiler

`SOUL.md` and `OUTPUT_POLICY.md` should stay separate:

```text
SOUL = who the character is
OUTPUT_POLICY = how the character speaks and emotionally manifests
```

Incoming Open-LLM-VTuber system prompts may be used as a fallback SOUL source, but configured character files should be preferred when present.

Recommended priority:

```text
1. route-configured SOUL.md
2. incoming system prompt
3. empty fallback
```

### Memory / retrieval layer

Responsibilities:

- provide lightweight character/viewer memory for `memory_light`
- provide RAG, spill, compression, or heavier retrieval for `memory_full`
- keep realtime speech latency in mind
- avoid expensive synchronous work in the default VTuber path

The first memory implementation should be simple and local. Embeddings, rerankers, and summarizers should be follow-ups behind the same interface.

External memory systems may specialize in user facts, episodic recall, temporal relationship memory, procedural persona updates, or external knowledge. RelayLM should normalize, arbitrate, and repack those outputs rather than expose all memory output directly to the backend model.

### Context compiler layer

Responsibilities:

- convert character profile, memory, room/scene state, recent turns, and latest input into a stable context layout
- preserve persona stability
- keep stable blocks byte-for-byte stable when possible
- put dynamic content later in the prompt
- emit an OpenAI-compatible message list for the backend adapter

RelayLM should treat prompt construction as context compilation rather than concatenation.

The compiled prompt should use tags for persona and conversation context. Machine contracts such as adapter results, diagnostics, traces, and tool protocols should remain JSON/dataclass-shaped. In short: JSON is for machine contracts; tags are for persona/context conditioning.

### Backend adapter layer

Responsibilities:

- forward non-streaming requests to OpenAI-compatible backends
- forward streaming SSE chunks without breaking Open-LLM-VTuber latency expectations
- adapt model names and headers
- preserve pass-through fields such as `temperature`, `tools`, and sampling parameters when possible

Backend-specific optimization should be hidden behind adapters. vLLM and SGLang are important long-term targets, but the MVP should work with any OpenAI-compatible backend.

## Mode contract

RelayLM modes define how much of the runtime stack is active.

### pass_through

Purpose:

- verify URL-swap integration
- test `/v1/models`
- test `/v1/chat/completions`
- test streaming SSE forwarding

Behavior:

- use routing and backend adapter
- do not modify messages
- map model name to backend model when configured
- forward common OpenAI-compatible fields transparently

### memory_light

Purpose:

- add useful memory while preserving low latency
- make AI characters feel more continuous without heavy RAG

Behavior:

- preserve stable character blocks
- keep bounded recent turns
- add lightweight character/viewer memory
- avoid heavy retrieval, rerankers, or compression in the synchronous path

### memory_full

Purpose:

- perform full budget-aware context compilation
- support memory, RAG, spill, and compression

Behavior:

- compile SOUL, OUTPUT_POLICY, relationship anchors, room/scene state, retrieved memory, recent turns, and latest input
- enforce token budgets
- support retrieval and compression behind explicit interfaces
- keep stable prefix blocks before dynamic retrieved content

### future persona_finalizer

Purpose:

- shape only final natural-language responses from an external agent framework
- preserve the agent result while applying persona, relationship, memory, and output policy

Default agent integration should pass through planning, tool calls, tool observations, and structured output. Persona/context repacking should apply to final natural-language answers or normal chat turns.

## Routing modes

RelayLM should support both routing styles.

### Single proxy mode

One RelayLM instance serves multiple characters and routes by model name.

This is the onboarding-first mode.

### Per-character instance mode

Each character has a dedicated RelayLM server, port, and cache namespace.

This is the speed-first mode. It improves prefix stability and reduces cross-character cache interference.

## Runtime non-goals for the first implementation

The first runtime implementation should not include:

- direct KV-cache mutation
- engine scheduler changes
- Live2D control
- ASR or TTS
- heavy RAG in the default synchronous path
- full tracing or lineage storage
- agent tool-workflow orchestration beyond transparent pass-through
- post-generation rewriting of streamed responses

These can be added after URL-swap streaming compatibility is stable. RelayLM should prefer context transformation before generation over response rewriting after generation.
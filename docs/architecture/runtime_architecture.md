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

This layer view is deployment- and integration-oriented. It complements, but does not replace, the canonical semantic/runtime pipeline vocabulary in [Pipeline Responsibility Design](pipeline_responsibility_design.md): RelaySCN, RelayEMO, RelayINT, RelayMEM, RelayCTX, RelayREF, RelayRUN, and RelaySLP.

## Terminology boundary notes

- `route`: RelayLM-internal mapping from incoming `model` value to runtime config bundle.
- `mode`: prompt-assembly behavior profile (`pass_through`, `memory_light`, `memory_full`).
- `backend`: actual model-serving endpoint and engine family behind adapter forwarding.

These three terms should stay distinct: route chooses configuration, mode chooses compilation behavior, backend chooses execution target.

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

RelayMEM boundary:

- RelayMEM proposes memory candidates and retrieval candidates.
- RelayMEM does not finalize prompt packing.
- RelayMEM does not version persona-source artifacts.

### Context compiler layer

Responsibilities:

- convert character profile, memory, room/scene state, recent turns, and latest input into a stable context layout
- preserve persona stability
- keep stable blocks byte-for-byte stable when possible
- put dynamic content later in the prompt
- emit an OpenAI-compatible message list for the backend adapter

RelayLM should treat prompt construction as context compilation rather than concatenation.

RelayCTX boundary:

- RelayCTX packs selected context into the compiled runtime prompt shape.
- RelayCTX consumes policy and memory selections but does not own scene or persistence policy decisions.
- RelayCTX Repack owns prompt-layout and token-budget application decisions.
- RelayCTX output is runtime compiled context, not a RelaySOUL artifact.

The compiled prompt should use tags for persona and conversation context. Machine contracts such as adapter results, diagnostics, traces, and tool protocols should remain JSON/dataclass-shaped. In short: JSON is for machine contracts; tags are for persona/context conditioning.

### Backend adapter layer

Responsibilities:

- forward non-streaming requests to OpenAI-compatible backends
- forward streaming SSE chunks without breaking Open-LLM-VTuber latency expectations
- adapt model names and headers
- preserve pass-through fields such as `temperature`, `tools`, and sampling parameters when possible

Backend-specific optimization should be hidden behind adapters. vLLM and SGLang are important long-term targets, but the MVP should work with any OpenAI-compatible backend.

Relay Adapter boundary:

- preserve OpenAI-compatible frontend/backend interoperability.
- preserve request/response compatibility and streaming semantics.
- avoid changing persona policy or memory decisions.
- remain a transport/integration boundary rather than a semantic pipeline stage.

Policy and runtime decision boundary:

- RelaySCN resolves scene, safety-sensitivity, expression, memory-scope, and persistence policy.
- RelayINT owns pre-action intent, ambiguity, clarification, and semantic proceed/block decisions.
- RelayCTX Repack owns prompt construction and token-budget degradation.
- RelayRUN owns runtime orchestration, transport/runtime fallback and recovery routing, checkpoints, trace artifacts, and node-state reporting.
- The Runtime Compile Gate is a request-local decision phase that consumes route, mode, preflight, scene-policy, and budget outcomes; it is not a standalone `RelayPLC` component.

Boundary-first safety:

- RelayLM should not rely on disclaimers as the primary safety mechanism.
- For safety-sensitive scenes such as `medical_or_safety`, RelaySCN should first resolve a restrictive runtime `scene_policy`.
- That policy should constrain context packing, allowed answer shapes, blocked answer shapes, persistence, and final output inspection before user-facing rendering.
- The goal is not to generate a risky answer and append a disclaimer; the goal is to avoid unsafe answer shapes before final rendering.
- Example blocked answer shapes include diagnosis claims, prescription or dosage instructions, emergency reassurance, and treatment plan overrides.
- Example allowed answer shapes include general information, symptom triage questions, red flags or when to seek care, and preparation for consultation.

Core handoff rule:

`MEM proposes candidates -> SCN resolves scene/persistence policy -> INT decides whether to proceed -> CTX packs selected context and applies token budgets -> RUN orchestrates runtime fallback/recovery and records trace/checkpoint artifacts -> adapters preserve API/backend compatibility`.

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

# RelayLM Runtime Architecture

RelayLM is an OpenAI-compatible Memory Context Proxy for local LLM frontends.

The primary local MVP path is:

```text
OpenWebUI
  -> RelayLM /v1/chat/completions
  -> LM Studio /v1/chat/completions
```

An optional real-time profile is:

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible backend
```

RelayLM should make an AI character feel memoryful, persona-stable, and conversationally continuous while keeping the frontend unchanged.

RelayLM is not an agent framework or a memory database. It controls what the backend model sees before generation so persona, relationship, memory, and recent context can be shaped without taking over tool workflows or external memory-product responsibilities.

## Runtime layers

RelayLM keeps the runtime split into explicit layers so pass-through compatibility and memory-aware context packing share one architecture.

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

- expose `/v1/chat/completions`,
- expose `/v1/models`,
- accept OpenAI-compatible request bodies from supported local frontends,
- preserve streaming behavior for real-time profiles,
- return backend-compatible error payloads where practical.

This layer does not own memory, persona loading, retrieval, or backend-specific optimization.

### Routing layer

Responsibilities:

- resolve the incoming `model` name to a RelayLM route,
- select the backend,
- select the character profile,
- select the cache namespace and memory namespace,
- map the RelayLM model name to the backend model name when configured.

Model-name routing is the primary MVP mechanism because supported frontends can change the model field without RelayLM-specific code changes.

### Character profile layer

Responsibilities:

- load approved character identity and expression policy,
- resolve `SOUL.md`,
- resolve `OUTPUT_POLICY.md`,
- resolve relationship anchors and stable memory summaries,
- expose a stable profile object to RelayCTX Repack.

`SOUL.md` and `OUTPUT_POLICY.md` stay separate:

```text
SOUL = who the character is
OUTPUT_POLICY = how the character speaks and emotionally manifests
```

Authority boundary:

```text
RelayLM runtime / capability policy
  -> highest execution and side-effect authority

approved RelaySOUL / route-configured SOUL.md
  -> durable persona authority

approved OUTPUT_POLICY / relationship anchors
  -> durable expression and relationship policy

RelaySCN
  -> current role, task, scene, and temporary constraints

client system/developer evidence
  -> bounded low-trust evidence for current-scene interpretation
```

Client-supplied `system` and `developer` messages are not fallback SOUL sources and are not forwarded as backend-authoritative instructions on managed routes. Input-side RelaySCN may normalize bounded current instruction evidence into a temporary scene role, context, or constraint. When no approved SOUL exists, RelayLM may use a safe temporary RelaySCN state for the current request and open a separate gated RelaySOUL initialization or proposal path; it must not copy the raw client prompt into `SOUL.md`.

Detailed authority rules live in [Client Instruction Authority Contract](client_instruction_authority_contract.md).

### Memory / retrieval layer

Responsibilities:

- provide lightweight approved character/viewer memory for `memory_light`,
- provide bounded RAG, spill, compression, or heavier retrieval for `memory_full`,
- keep real-time latency in mind,
- avoid expensive synchronous work in latency-sensitive profiles,
- preserve source, scope, confidence, and policy metadata for downstream selection.

The synchronous retrieval implementation should remain simple, local-first, and bounded. Embeddings, rerankers, and summarizers may be added behind the same read interface when needed.

External memory systems may specialize in user facts, episodic recall, temporal relationship memory, procedural persona updates, or external knowledge. RelayLM should normalize, arbitrate, and repack approved retrieval outputs rather than expose all external memory output directly to the backend model.

RelayMEM Retrieval boundary:

- reads approved memory evidence for the current response,
- obeys RelaySCN memory scope and RelayINT retrieval intent,
- returns bounded retrieval candidates or blocks,
- does not finalize prompt packing,
- does not mutate MEM or SOUL.

RelaySLP boundary:

- runs outside the latency-critical normal response path,
- extracts and compiles deferred memory or SOUL candidates from governed evidence,
- emits held, rejected, update, or proposal candidates through explicit gates,
- does not answer the current turn or bypass persistence approval.

### Context compiler layer

Responsibilities:

- convert approved character profile, RelaySCN state, approved memory evidence, selected RelayLM-owned recent context, and current-turn evidence into a stable context layout,
- preserve persona stability,
- keep stable blocks byte-for-byte stable when possible,
- put dynamic evidence later in the prompt,
- emit an OpenAI-compatible message list for the backend adapter.

Client-provided message arrays are request evidence, not automatically trusted backend context.

#### Current compatibility behavior

- explicit `pass_through` routes preserve compatible client-owned messages,
- the default `memory_light` compatibility path may retain prior client user/assistant history in the backend-bound message list,
- current streaming remains primarily backend forwarding.

#### Current bounded managed apply

- `client_history_exclusion_apply.v0` is default-off,
- actual apply requires `client_history_exclusion_apply_enabled=true` and `client_history_exclusion_apply_dry_run_only=false`,
- the current apply supports managed `memory_light` requests only when client `system`/`developer` messages are absent,
- unsupported managed requests fail closed rather than restoring raw client context,
- `pass_through` remains an explicit exemption.

#### Target managed reconstruction

```text
validated current user turn
+ bounded current instruction evidence
+ RelayLM-owned profile / scene / context / memory state
+ minimum active transaction state
  -> newly constructed backend-bound message list
```

The complete target path extracts current request evidence and reconstructs backend context from RelayLM-owned state according to the client-authority contracts. It is broader than the current no-instruction apply slice.

RelayLM treats prompt construction as context compilation rather than concatenation.

RelayCTX boundary:

- RelayCTX packs selected context into the compiled runtime prompt shape,
- RelayCTX consumes policy and memory selections but does not own scene or persistence policy decisions,
- RelayCTX Repack owns prompt-layout and token-budget application decisions,
- RelayCTX output is runtime compiled context, not a RelaySOUL artifact.

The compiled prompt should use tags for persona and conversation context. Machine contracts such as adapter results, diagnostics, traces, and tool protocols should remain JSON/dataclass-shaped. In short: JSON is for machine contracts; tags are for persona/context conditioning.

### Backend adapter layer

Responsibilities:

- forward non-streaming requests to OpenAI-compatible backends,
- forward streaming SSE chunks without breaking frontend latency expectations,
- adapt model names and headers,
- preserve pass-through fields such as `temperature`, `tools`, and sampling parameters when possible.

Backend-specific optimization should be hidden behind adapters. vLLM and SGLang are important long-term targets, but the MVP should work with any OpenAI-compatible backend.

Relay Adapter boundary:

- preserve OpenAI-compatible frontend/backend interoperability,
- preserve request/response compatibility and streaming semantics,
- avoid changing persona policy or memory decisions,
- remain a transport/integration boundary rather than a semantic pipeline stage.

Policy and runtime decision boundary:

- RelaySCN resolves scene, expression, memory-scope, persistence policy, and optional pre-generation model/profile selection.
- RelayINT owns pre-action intent, ambiguity, clarification, and semantic proceed/block decisions before an action is authorized.
- RelayCTX Repack owns prompt construction and token-budget degradation.
- RelayRUN owns runtime orchestration, transport/runtime fallback and recovery routing, checkpoints, trace artifacts, and node-state reporting.
- The Runtime Compile Gate is a request-local decision phase that consumes route, mode, preflight, scene-policy, and budget outcomes; it is not a standalone `RelayPLC` component.

## Conversation content and capability boundary

RelayLM does not treat ordinary natural-language conversation as an executable capability.

```text
ordinary generated text
  -> model / RelaySOUL / OUTPUT_POLICY responsibility
  -> no mandatory RelayLM semantic censorship or rewrite

requested side effect
  -> typed capability contract
  -> explicit authority and bounded inputs
  -> fail-closed runtime gate
```

The core runtime does not add a universal post-generation classifier, secondary moderation LLM, or meaning-changing rewrite step for teasing, insults, arguments, adult-oriented tone, politics, or other open-ended conversation judgments. Generated conversation depends on the selected model, approved character profile, context, and user configuration. A recommended model profile verifies compatibility and expected default behavior; it does not certify or guarantee content.

RelayLM governs tool calls, code or command execution, filesystem and protected-data access, credentials, network actions, persistence, configuration changes, MEM mutation, RelaySOUL mutation, and other externally observable or irreversible side effects. These capabilities do not inherit authority from natural-language output.

Text that contains code, a command, or a request to perform an action remains text unless RelayLM or an attached adapter attempts to interpret it as an executable capability. At that point, the typed capability gate applies. Malformed structured output may be rejected as a protocol error, but RelayLM must not silently replace it with a semantically rewritten answer.

These gates define the required RelayLM-owned authority path, not an absolute guarantee for arbitrary external clients, backends, plugins, or future adapters. Any integration that executes a side effect without routing it through the typed capability gate is outside RelayLM's governed execution boundary.

Safety-sensitive routes may select a more suitable model, prompt profile, tool policy, retrieval scope, or capability set before generation. They must not imply that RelayLM universally inspects and guarantees the semantic acceptability of every final conversational response.

Optional content or presentation filters required by a frontend, broadcast platform, age profile, or deployment policy belong in explicit client or adapter layers rather than the canonical RelayLM conversation path.

The canonical product principle is defined in [AI Character Product Principles](ai_character_product_principles.md#conversation-content-and-capability-authority).

Core handoff rule:

```text
RelaySCN resolves scene and persistence policy
  -> RelayINT decides whether to proceed and whether retrieval is needed
  -> RelayMEM Retrieval returns approved evidence
  -> RelayCTX packs selected context and applies token budgets
  -> RelayRUN orchestrates runtime fallback/recovery and records trace/checkpoint artifacts
  -> adapters preserve API/backend compatibility

Out-of-band:
  governed evidence -> RelaySLP -> gated MEM updates / SOUL proposals
```

## Mode contract

RelayLM modes define how much of the runtime stack is active.

### pass_through

Purpose:

- verify URL-swap integration,
- test `/v1/models`,
- test `/v1/chat/completions`,
- test streaming SSE forwarding.

Behavior:

- use routing and backend adapter,
- do not modify messages,
- map model name to backend model when configured,
- forward common OpenAI-compatible fields transparently.

### memory_light

Purpose:

- add useful memory while preserving low latency,
- make AI characters feel more continuous without heavy RAG.

Behavior:

- preserve stable character blocks,
- keep bounded RelayLM-owned selected recent context,
- add lightweight approved character/viewer memory,
- avoid heavy retrieval, rerankers, or compression in the synchronous path.

### memory_full

Purpose:

- perform full budget-aware context compilation,
- support memory, RAG, spill, and compression.

Behavior:

- compile SOUL, OUTPUT_POLICY, relationship anchors, RelaySCN state, approved retrieved memory, selected RelayLM-owned recent context, and current-turn evidence,
- enforce token budgets,
- support retrieval and compression behind explicit interfaces,
- keep stable prefix blocks before dynamic retrieved content.

### optional persona_finalizer profile

Purpose:

- shape only final natural-language responses from an external agent framework,
- preserve the agent result while applying persona, relationship, memory, and output policy.

Default agent integration should pass through planning, tool calls, tool observations, and structured output. Persona/context repacking should apply to final natural-language answers or normal chat turns.

## Routing modes

RelayLM supports both routing styles.

### Single proxy mode

One RelayLM instance serves multiple characters and routes by model name.

This is the onboarding-first mode.

### Per-character instance mode

Each character has a dedicated RelayLM server, port, and cache namespace.

This is the speed-first mode. It improves prefix stability and reduces cross-character cache interference.

## Runtime ownership non-goals

RelayLM does not own:

- direct KV-cache mutation or backend engine scheduler changes,
- frontend UI behavior,
- Live2D control,
- ASR or TTS model runtimes,
- heavy RAG in the default synchronous path,
- general agent tool-workflow orchestration beyond compatibility-preserving pass-through,
- universal semantic censorship or content guarantees for ordinary model-generated conversation.

RelayLM does own authority-bounded context construction, visible/internal output separation, protocol-valid output segmentation, and typed capability gates before external tools, TTS, avatar, network, persistence, or other side-effect consumers receive data. Current implementation status and sequencing for those boundaries live only in [Pipeline Implementation Plan](pipeline_implementation_plan.md).
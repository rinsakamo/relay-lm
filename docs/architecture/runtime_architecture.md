# Transitional Runtime Integration and Mode Note

## Status

This path is a closed transitional current-implementation and integration note governed by `records/documentation/transitional-assets.json`. Canonical RelayLM system context is [RelayLM System Overview](system-overview.md), canonical component ownership and target order are [Pipeline Responsibilities](pipeline-responsibilities.md), mode-specific runtime dataflow is [Request / Response Pipeline](runtime/request-response-pipeline.md), and compile/checkpoint responsibility is [Runtime Compile and Checkpoint Architecture](runtime/compile-and-checkpoint.md).

This page no longer owns repository-wide runtime architecture. It must not gain new consumers. Its path remains in the onboarding workflow trigger and in existing documentation links until D2-B2b moves each consumer to the smallest owning authority.

## Current external topology

The primary local integration remains:

```text
OpenWebUI or another supported OpenAI-compatible frontend
  -> RelayLM /v1/chat/completions
  -> LM Studio or another OpenAI-compatible backend
```

An optional realtime profile may use Open-LLM-VTuber or another adapter-facing frontend. RelayLM preserves OpenAI-compatible request/response and streaming transport while adding explicit managed context, memory, character, and runtime boundaries where configured.

## Current protocol surface

The onboarding-compatible surface includes:

- `/v1/models` for supported model/route discovery;
- `/v1/chat/completions` for non-streaming and streaming requests;
- backend model-name mapping where configured;
- compatible forwarding of common sampling and request fields, including active tool or structured transaction state when supported;
- OpenAI-compatible errors and SSE transport where practical.

Transport compatibility does not grant the adapter persona, relationship, scene, memory, or persistence authority.

## Current terminology

These terms remain distinct:

```text
route
  RelayLM mapping from the incoming model identity to a runtime configuration bundle

mode
  prompt/context assembly and managed-runtime behavior profile

backend
  the model-serving endpoint and engine selected for forwarding
```

A route selects configuration, a mode selects managed behavior, and a backend executes the model request. These terms do not transfer semantic scene, memory, persona, or relationship authority.

## Current integration layers

Current implementation exposes the following integration-oriented layers:

```text
OpenAI-compatible API
  -> route and backend selection
  -> configured character/profile loading
  -> optional memory and retrieval inputs
  -> context compilation and managed payload gates
  -> backend adapter and streaming transport
```

Canonical semantic component responsibility inside these layers is owned by the new pipeline page. Layer names describe integration and deployment structure only.

## Current mode posture

### `pass_through`

`pass_through` is an explicit delegated-authority compatibility route. It preserves compatible client-owned message context and common OpenAI-compatible fields while routing to the configured backend. A compile failure on a managed route is not permission to enter pass-through.

### `memory_light`

`memory_light` is the primary low-latency managed compatibility profile. Current behavior may combine configured character/profile sources, bounded memory or selected recent context, default-off history-exclusion gates, and the current profile compiler. Exact current apply behavior is owned by code, implemented schema/version, current contracts, and Project Status.

### `memory_full`

`memory_full` names the heavier budget-aware managed profile direction for broader retrieval, RAG, spill, or compression. The name does not prove that every target RelayCTX, Retrieval, or compression handoff is implemented or default-on.

### Optional response-finalization profiles

An optional persona-finalization profile may shape a final natural-language answer from an external agent or tool framework while preserving planning, tool calls, tool observations, and structured transaction output through compatibility paths. Persona finalization is not the canonical ordinary conversation path and does not acquire tool-execution authority.

Presentation, TTS, avatar, or other response-finalization profiles remain separately governed. Adapter support does not make them default-on core behavior.

## Current routing styles

### Single-proxy mode

One RelayLM instance may serve multiple configured characters or routes and select them through the incoming model identity. This is the onboarding-first topology.

### Per-character instance mode

A deployment may use a dedicated RelayLM process, port, and cache or memory namespace for each character. This is a speed- and prefix-stability-oriented topology, not a different semantic authority model.

Exact deployment commands and configuration fields belong in configuration/reference and integration guidance.

## Current authority and compatibility rules

- client-provided messages are request evidence on managed routes, not automatic SOUL, relationship, scene, or memory authority;
- explicit pass-through remains the delegated-context exception;
- current managed reconstruction and history exclusion remain bounded by their implemented gates and supported request shapes;
- RelayMEM Retrieval is read-only in the interactive path;
- RelayCTX owns selected context construction and token-budget handling, not semantic policy;
- RelayRUN owns orchestration, fallback/recovery routing, checkpoints, and trace, not persona or response meaning;
- backend adapters preserve protocol and transport rather than deciding character behavior;
- current completion is determined by Project Status, code, schema/version, and focused validation.

Exact client-instruction, compile, fallback, context, and checkpoint rules remain in their owning contracts.

## Conversation and capability boundary

Ordinary generated conversation is model output shaped by the selected model, approved character sources, managed context, and user configuration. RelayLM does not treat natural-language text as an executable capability merely because it contains code or a command.

Tool execution, filesystem and protected-data access, credentials, network actions, persistence, memory mutation, character-source mutation, and other externally observable side effects require typed owning authority and fail-closed gates. Product-level conversation principles remain in [AI Character Product Principles](ai_character_product_principles.md).

## Current integration non-ownership

This integration layer does not own frontend UI behavior, Live2D control, ASR or TTS model runtimes, backend KV-cache or scheduler internals, heavy synchronous RAG policy, or general external-agent tool orchestration. Those responsibilities remain in their owning adapters, services, backends, or domain authorities.

## Removal gate

Delete this path after D2-B2b moves system, pipeline, mode, configuration, onboarding, and integration consumers to their canonical owners; updates the onboarding workflow trigger; passes generic authority and link validation; and records the retired path in the manifest. Historical wording remains recoverable through Git.

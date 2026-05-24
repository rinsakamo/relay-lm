# Persona-Specialized Proxy Design

This note consolidates the post-MVP-12 design direction for RelayLM.

RelayLM remains an OpenAI-compatible proxy, not a language model, memory database, or agent framework. Its product role is to sit between conversation frontends and LLM backends, gather persona, memory, room/scene state, recent turns, and external context through adapters, then reshape them into a token-budgeted, persona-stable, KV-reuse-aware context layout.

## Definition

RelayLM is a persona-specialized OpenAI-compatible conversation proxy.

It does not replace memory systems, agent frameworks, or inference engines. RelayLM controls what the backend model sees before generation so the response can preserve persona, relationship continuity, and conversational warmth under token and latency constraints.

## Core design goals

- Preserve persona consistency under truncation.
- Keep the stable persona prefix byte-for-byte stable where possible.
- Repack memory and external context into explicit conversation tags.
- Keep JSON/tool protocols separate from persona tags.
- Use external memory systems as specialized cognitive modules rather than reimplementing them inside RelayLM.
- Evaluate the product not only by task success, but by whether the user wants to keep talking.

## Non-goals

RelayLM should not own the full memory intelligence stack. It should not become a vector database, embedding service, reranker, ASR/TTS system, Live2D controller, autonomous tool workflow runner, or backend KV-cache mutator.

For agent integrations, the default stance is pass-through for planning, tool selection, tool observation, and structured output phases. RelayLM should apply persona/context repacking primarily to final natural-language responses or normal chat turns.

## Persona source files

RelayLM treats persona as layered source material:

- `SOUL.md`: persona core, values, worldview, and durable identity.
- `OUTPUT_POLICY.md`: expression mode, tone, emotional manifestation, TTS-friendly style, and response style.
- `RELATIONSHIP_ANCHOR.md`: slow-changing relationship state between the character and the user/viewer.
- `STABLE_MEMORY_SUMMARY.md`: durable memory summary and long-term context.
- `SCENE_STATE.md`: dynamic current situation, topic, mood, and temporary conversational context.

These files should not all update at the same speed. `SOUL.md` is the slowest and should normally require explicit approval for changes. `RELATIONSHIP_ANCHOR.md` and stable memory may grow from repeated interaction. `SCENE_STATE.md` may change every session or turn.

## Persona Anchor KV

Persona Anchor KV is the backend-specific runtime representation of the stable persona prefix.

The source of truth remains the persona files and compiled prompt text. During prefill, the backend model materializes the stable persona prefix into KV cache. That cache is not portable across models, tokenizers, prompts, or engines, but it acts as the latent conditioning state through which the model maintains character behavior during decoding.

RelayLM therefore treats the stable persona prefix as the highest-value anchor for KV reuse:

```text
SOUL.md / OUTPUT_POLICY.md / RELATIONSHIP_ANCHOR.md
  -> tagged stable persona prefix
  -> backend-specific Persona Anchor KV
  -> persona-conditioned decoded response
```

## Context hierarchy

RelayLM should organize compiled context into three broad tiers.

### Stable Persona Prefix

- `common_runtime_policy`
- `character_soul_anchor`
- `character_output_policy`
- `relationship_anchor`

This tier should be stable and cache-friendly. It should not contain timestamps, volatile memory counts, retrieved snippets, current topics, random identifiers, or transient diagnostics.

### Slow Memory Prefix

- `stable_memory_summary`
- durable user memory
- durable character memory
- durable relationship facts

This tier may change slowly after session boundaries, explicit corrections, or confirmed durable facts.

### Dynamic Conversation Context

- `scene_state`
- `retrieved_memory`
- `retrieved_rag`
- `agent_result_summary`
- `tool_observations` when needed for final response synthesis
- `recent_turns`
- `latest_input`
- `response_instruction`

This tier may change every turn and should remain after persona anchors so memory/RAG/tool observations do not override persona identity.

## Memory systems as cognitive modules

RelayLM should treat memory products as specialized cognitive modules:

- LangMem-like systems: persona/profile/procedural memory evolution and patch candidates.
- Mem0-like systems: lightweight user facts, preferences, and searchable long-term memories.
- Zep/Graphiti-like systems: temporal relationship memory, graph relations, and conflict/supersession tracking.
- Local seed/SQLite stores: reference, fallback, debug, and offline memory.
- RAG/LlamaIndex/Haystack-like systems: external knowledge and documents.
- MCP-style connectors: external data/tool sources that may feed context adapters.

RelayLM arbitrates and repacks their outputs into a conversation-ready tagged context. It should not expose all memory output directly to the model without scope, confidence, and budget checks.

## JSON versus tags

RelayLM should use JSON or dataclasses for machine contracts:

- Memory adapter results
- Fusion plans
- Repack plans
- Diagnostics
- Trace metadata
- Tool and agent protocol payloads

RelayLM should use XML-like tags for the compiled prompt body that the LLM reads:

```xml
<character_soul_anchor>...</character_soul_anchor>
<character_output_policy>...</character_output_policy>
<relationship_anchor>...</relationship_anchor>
<stable_memory_summary>...</stable_memory_summary>
<scene_state>...</scene_state>
<retrieved_memory>...</retrieved_memory>
<recent_turns>...</recent_turns>
<latest_input>...</latest_input>
```

In short: JSON is for machine contracts; tags are for persona/context conditioning.

## Scope identity

RelayLM should keep scope fields simple for config and operators:

- `character_id`: which persona is speaking.
- `user_id`: the conversation counterpart identity. Despite the name, this may represent a registered user, guest, viewer, operator, anonymous visitor, or agent caller.
- `user_type`: disambiguates `user`, `guest`, `viewer`, `operator`, `anonymous`, or `agent`.
- `room_id`: the channel, room, stream, or frontend conversation space.
- `scene_id`: the conversational situation or scenario.
- `session_id`: the current conversation/session run.

`room_id` is where the conversation is hosted. `scene_id` is what situation the conversation is in.

## Persona backpropagation

Persona backpropagation is the future process that turns conversation traces into patch candidates for memory and persona files.

It is not gradient descent over model weights. It is a controlled update pipeline:

```text
conversation trace
  -> reflection / extraction
  -> memory or persona patch candidate
  -> persona_plasticity gate
  -> safety / drift guard
  -> optional human approval
  -> profile file update
  -> new stable persona prefix
```

Suggested update speed:

- `scene_state`: fast, often automatic.
- `stable_memory_summary`: medium, candidate-based.
- `RELATIONSHIP_ANCHOR.md`: medium-slow, rate-gated.
- `OUTPUT_POLICY.md`: slow, explicit feedback or repeated evidence.
- `SOUL.md`: very slow, candidate-only by default, explicit approval recommended.

`persona_plasticity` is the configuration or inferred trait controlling how quickly relationship, expression, and persona files may change. It should always be paired with drift guards and persona invariants.

## Agent integration

When RelayLM is used with an agent framework, the default integration should avoid interfering with internal agent operations.

Recommended policy:

```text
agent planning/tool calls/structured output -> pass_through
agent final natural-language answer        -> persona/context repacking
normal chat turn                            -> memory_light or memory_full
```

RelayLM may later define a `persona_finalizer` style mode for final natural-language answer shaping. This mode should preserve the agent result while applying persona, relationship, and memory style to the final response.

## Evaluation axis

Task-oriented agents are evaluated by usefulness and task completion. RelayLM should also be evaluated by whether the user wants to keep talking.

Technical stability metrics:

- token budget stability
- latest-input preservation
- stable-prefix hash stability
- route and namespace isolation
- memory leakage prevention
- latency comfort

Persona experience metrics:

- persona consistency
- relationship continuity
- memory warmth
- conversation stickiness
- non-creepiness
- growth feeling
- emotional appropriateness

## Future design risks

Important future design areas include:

- forget/delete propagation across memory adapters and profile files
- persona versioning and rollback
- multi-memory conflict resolution
- memory disclosure policy
- persona invariants
- prompt-injection boundaries for retrieved memory/RAG
- backend capability differences for prefix cache and structured output
- streaming-safe context transformation before generation rather than post-generation rewriting

## Current implementation boundary

After MVP-12, RelayLM has pass-through proxying, profile compilation, manual seed memory selection, token-policy diagnostics, and gated message-level token budget truncation. This design note does not require runtime behavior changes. The next implementation steps should be adapter-boundary and repacking dry-runs before any heavy memory product integration.
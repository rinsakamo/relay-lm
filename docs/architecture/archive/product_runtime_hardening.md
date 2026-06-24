# RelayLM Product Runtime Hardening

This document captures design points that should be settled before RelayLM grows beyond a pass-through proxy.

PR #2 defined runtime layers, config shape, and the context compiler contract. This document raises the design level from code structure to product behavior: how RelayLM remains useful, fast, safe, and persona-stable as memory and retrieval are added.

## Product invariant

RelayLM's first product value is not generic RAG.

The invariant is:

> Open-LLM-VTuber users can swap the OpenAI-compatible API URL to RelayLM and the character feels more memoryful and persona-stable without frontend changes.

This means every feature should be judged by:

- Does it preserve URL-swap compatibility?
- Does it keep first-speech latency acceptable?
- Does it improve character continuity?
- Does it avoid making the character sound like a generic assistant?
- Does it avoid requiring Open-LLM-VTuber code changes?

## Product milestone plan

RelayLM should move from connection reliability to persona stability before adding heavier memory or RAG.

```text
MVP-0: OpenAI-compatible pass-through proxy
MVP-1: model routing, config, and runtime diagnostics
MVP-2: persona-stable context compiler
MVP-3: memory_light with local memory
MVP-4: safe memory write lifecycle
MVP-5: memory_full with RAG and compression
```

### MVP-0: OpenAI-compatible pass-through proxy

Goal:

- Open-LLM-VTuber can change its OpenAI-compatible `base_url` to RelayLM without breaking chat.

Scope:

- FastAPI server
- `/v1/models`
- `/v1/chat/completions`
- streaming SSE forwarding
- non-streaming JSON forwarding
- backend adapter seam
- minimal config loading

Out of scope:

- memory
- RAG
- SOUL / OUTPUT_POLICY loading
- context compilation
- embeddings
- database storage

### MVP-1: model routing, config, and runtime diagnostics

Goal:

- incoming model names resolve to stable RelayLM routes.

Scope:

- `model_routes`
- backend model mapping
- `character_id`
- `cache_namespace`
- `memory_namespace`
- mode resolution
- request diagnostics
- fallback reason field

Out of scope:

- prompt mutation
- memory retrieval
- memory writes

### MVP-2: persona-stable context compiler

Goal:

- RelayLM can compile stable character context without making dynamic memory override persona.

Scope:

- `SOUL.md`
- `OUTPUT_POLICY.md`
- `common_runtime_policy`
- `room_anchor`
- incoming system prompt fallback
- bounded recent turns
- compiled system message
- stable prefix / slow prefix / dynamic suffix diagnostics

Out of scope:

- heavy memory retrieval
- vector search
- summarization
- automatic memory writes

### MVP-3: memory_light with local memory

Goal:

- make the character feel like it remembers useful facts while preserving realtime speech latency.

Scope:

- local JSONL memory
- viewer memory
- character memory
- simple keyword or recent-N memory selection
- memory block insertion
- missing memory fallback
- memory candidate logging

Out of scope:

- embeddings
- vector database
- rerankers
- LLM-based summarization in the synchronous path

### MVP-4: safe memory write lifecycle

Goal:

- allow memory updates without letting wrong or low-confidence memories immediately affect character behavior.

Scope:

- memory candidate state
- accepted / summarized / active / archived states
- confidence field
- source turn reference
- conservative activation
- post-response async memory extraction path
- memory write diagnostics

Out of scope:

- mandatory autonomous memory activation
- long-term summarization quality optimization
- multi-user memory governance beyond the namespace model

### MVP-5: memory_full with RAG and compression

Goal:

- support longer-term memory, RAG, spilled context, and budget-aware packing after realtime and persona foundations are stable.

Scope:

- embeddings
- vector search
- retrieved memory and RAG chunks
- token budget control
- compression hooks
- fallback to `memory_light`
- retrieval diagnostics

Out of scope:

- direct backend KV-cache mutation
- engine scheduler changes
- implementing or replacing backend KV-cache infrastructure

## Authority order

RelayLM needs an explicit authority order so memory and RAG do not override character identity.

Recommended authority order:

```text
1. safety / runtime constraints
2. SOUL.md or configured character identity
3. OUTPUT_POLICY.md
4. relationship anchor
5. stable memory summary
6. room anchor
7. room state
8. retrieved memory / RAG / spill chunks
9. recent turns
10. latest user input
```

Notes:

- `SOUL.md` should define identity and values.
- `OUTPUT_POLICY.md` should define expression and emotional manifestation.
- memory is evidence, not authority over identity.
- RAG is evidence, not a replacement persona.
- latest user input should control the immediate answer but should not rewrite stable identity.

## Memory lifecycle

Memory should not be written synchronously on every streamed response by default.

Use a two-path model:

```text
synchronous path:
  route -> compile -> forward stream

asynchronous path:
  observe -> extract candidates -> validate -> store -> summarize later
```

### Synchronous path

Allowed in realtime path:

- route lookup
- profile loading from cache
- bounded recent turns
- cheap local memory lookup
- context compilation
- streaming forward

Avoid in realtime path by default:

- embedding generation
- reranking
- summarization
- long database transactions
- multi-hop retrieval
- LLM-based memory extraction

### Asynchronous path

The async path may do heavier work after the response:

- extract candidate memory facts
- update viewer facts
- update relationship anchors slowly
- refresh stable summaries
- build embeddings
- precompute retrieval candidates

The first implementation may only log candidates and write JSONL memory manually or conservatively.

## Memory write safety

Memory writes should be conservative because wrong memory can damage persona continuity.

Recommended write states:

```text
candidate
  -> accepted
  -> summarized
  -> active
  -> archived
```

Suggested fields:

```yaml
memory_id: viewer:default:000001
namespace: character/mili
subject: viewer/default
source_turn_id: turn-123
kind: preference | fact | relationship | ongoing_topic | correction
confidence: 0.0
status: candidate | accepted | summarized | active | archived
content: "..."
created_at: "..."
updated_at: "..."
```

Initial MVP can avoid timestamps in prompt prefixes while still keeping timestamps in storage metadata.

## Identity and namespace model

RelayLM should not assume there is only one user or one character.

Minimum identity axes:

- `character_id`
- `viewer_id`
- `room_id`
- `session_id`
- `memory_namespace`
- `cache_namespace`

Recommended default behavior:

- if no viewer ID is provided, use `viewer/default`
- if no room ID is provided, use `room/default`
- session state should be volatile
- relationship anchors should be durable but slow-changing
- cache namespace should usually be per character

## Latency profiles

VTuber use needs fast first speech, so modes should imply latency posture.

```text
pass_through:
  target: connection and streaming compatibility
  sync retrieval: none

memory_light:
  target: realtime character continuity
  sync retrieval: cheap local lookup only

memory_full:
  target: quality and long-context behavior
  sync retrieval: allowed but budgeted
```

RelayLM should be able to fall back from `memory_full` to `memory_light`, and from `memory_light` to `pass_through`, when retrieval or packing fails.

## Fallback behavior

Fallback must be normal product behavior, not an exceptional crash path.

Recommended fallback ladder:

```text
memory_full
  -> memory_light
  -> pass_through
  -> backend error
```

Fallback reasons should be logged:

- route_not_found
- backend_unavailable
- profile_load_failed
- memory_store_unavailable
- context_budget_exceeded
- compiler_error
- retrieval_timeout
- streaming_forward_error

For Open-LLM-VTuber onboarding, `pass_through` should be the strongest reliability baseline.

## OpenAI compatibility scope

The MVP should explicitly support:

- `GET /v1/models`
- `POST /v1/chat/completions`
- `stream: true`
- `stream: false`
- `model`
- `messages`
- common sampling fields

Initial transparent pass-through fields:

- `temperature`
- `top_p`
- `max_tokens`
- `presence_penalty`
- `frequency_penalty`
- `stop`
- `tools`
- `tool_choice`

Initial limitations:

- tool calls are passed through, not context-compiled
- vision content is passed through or treated as non-repackable
- embeddings endpoint is not required for MVP
- responses endpoint is not required for MVP

## Evaluation criteria

RelayLM needs product-level acceptance tests, not only unit tests.

### Pass-through acceptance

- Open-LLM-VTuber can point `base_url` to RelayLM.
- `/v1/models` returns configured RelayLM model IDs.
- non-streaming chat forwards to backend.
- streaming chat forwards SSE chunks without buffering the full response.
- model route maps RelayLM model to backend model.

### Persona acceptance

- SOUL remains before memory/RAG.
- OUTPUT_POLICY remains before dynamic content.
- memory insertion does not change character identity.
- latest user input remains near the end.
- internal tags are not revealed in normal output.

### Memory acceptance

- `memory_light` can insert a small number of local memories.
- missing memory store falls back cleanly.
- memory candidates can be logged without becoming active immediately.
- wrong or low-confidence memory can stay inactive.

### Latency acceptance

- pass-through adds minimal overhead.
- memory_light does not perform heavy synchronous retrieval.
- streaming begins without waiting for post-response memory extraction.

## Observability

RelayLM should log product-relevant decisions without leaking prompt internals by default.

Recommended debug fields:

- request_id
- route_model
- backend_model
- character_id
- mode_requested
- mode_applied
- fallback_reason
- stream_enabled
- compiler_used
- block_ids
- approximate_input_size
- memory_candidate_count
- retrieved_memory_count

Do not insert diagnostics into stable prompt prefixes.

## Privacy and local-first posture

RelayLM will handle persona, viewer memory, and conversation history.

Initial posture:

- local-first storage
- explicit memory namespace
- no external memory service required for MVP
- no hidden remote telemetry
- config-visible backend URLs
- easy memory file deletion

For hosted APIs or remote backends, RelayLM should make clear that compiled memory is sent to the backend as part of the prompt.

## Design implications for implementation

The first runtime PR should still be pass-through, but it should preserve these seams:

- route object
- mode resolution
- backend adapter
- character profile placeholder
- context compiler placeholder
- fallback reason field
- request diagnostics field

Do not hard-code FastAPI handlers directly to a backend URL in a way that bypasses these seams.

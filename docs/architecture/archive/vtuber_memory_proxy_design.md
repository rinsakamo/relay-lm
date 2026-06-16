# RelayLM VTuber Memory Proxy Design

RelayLM's first product target is an OpenAI-compatible memory and context proxy for Open-LLM-VTuber.

The goal is not to replace Open-LLM-VTuber. Open-LLM-VTuber should continue to own the UI, Live2D, ASR, TTS, character switching, and conversation experience. RelayLM should sit between Open-LLM-VTuber and the LLM backend.

```text
Open-LLM-VTuber
  -> RelayLM OpenAI-compatible proxy
  -> vLLM / SGLang / Ollama / LM Studio / other backend
```

## Product value

RelayLM should make an AI VTuber feel like it remembers unusually well.

The user-facing value is:

- existing Open-LLM-VTuber users can swap the API URL
- characters can use long-term memory without the frontend managing long context
- recent turns, viewer memory, character soul, and selected RAG context can be repacked into a safe effective context
- characters should remain persona-stable even when retrieved memory or RAG context changes
- context layout should be stable enough to help backend engines reuse prefix/KV cache

## Non-goals for the first product

The initial RelayLM product should not implement:

- Live2D control
- ASR or TTS
- UI
- a full agent framework
- direct KV-cache mutation
- engine scheduler changes
- runtime attention changes
- full lineage/RDBMS tracing

Those may become integrations later, but the first product should remain a thin proxy.

## Modes

RelayLM should support staged modes so users can diagnose connection and latency issues.

### pass_through

RelayLM forwards OpenAI-compatible requests to the backend without changing messages.

Purpose:

- verify URL swap works
- isolate RelayLM from backend or Open-LLM-VTuber failures
- keep the first onboarding step simple

### memory_light

RelayLM inserts lightweight character/viewer memory while preserving low latency.

Suggested behavior:

- preserve the incoming system/persona prompt
- keep recent turns bounded
- add a small number of JSONL or local memory entries
- use XML-like structural tags
- avoid rerankers, small LLM scorers, or heavy document RAG in the synchronous path

### memory_full

RelayLM performs budget-aware context repacking.

Suggested behavior:

- retrieve from memory, optional RAG, and spilled context
- compress older context when needed
- structure the prompt with SOUL, output policy, relationship anchor, room state, retrieved memory, recent turns, and latest input
- keep fixed anchors stable for prefix reuse

## Backend stance

RelayLM should be backend-agnostic at the proxy boundary.

Supported class:

- OpenAI-compatible chat completions backend

Initial recommended backends:

- vLLM for production-style local serving and future RelayKV alignment
- SGLang for future runtime/cache research alignment
- LM Studio, Ollama, llama.cpp server, OpenRouter, or hosted APIs as compatibility targets

The proxy should initially depend only on normal chat completion semantics. Backend-specific optimizations should be added behind adapters.

## Latency posture

VTuber use needs fast first speech. RelayLM should not run heavy retrieval or small-model scoring on every turn by default.

Recommended split:

- synchronous path: pass-through, short memory lookup, packing, streaming forward
- asynchronous path: memory extraction, summaries, embeddings, warm cache, long-term memory updates

Future optimization:

- ASR partial-transcript prefetch
- query-aware memory warmup
- speculative context repacking

## Character routing

RelayLM should support both routing styles.

### Single proxy mode

One RelayLM server receives all characters and routes by `model` name.

```yaml
model_routes:
  relaylm-mili:
    character_id: mili
    backend: vllm_main
  relaylm-zero:
    character_id: zero
    backend: vllm_main
```

This is best for onboarding.

### Per-character instance mode

Each character gets a separate RelayLM server/port/cache namespace.

This is best for speed, cache isolation, and debugging.

```text
Mili  -> RelayLM :8091 -> backend A
Zero  -> RelayLM :8092 -> backend B
```

RelayLM should support both because character-specific prefixes are usually large and cross-character KV cache sharing is limited.

# AI Character Product Principles

## Purpose

This document preserves the product-level principles that distinguish RelayLM from a generic RAG proxy.

RelayLM remains an OpenAI-compatible runtime proxy. Its product role is to improve persona stability, relationship continuity, memory usefulness, and conversational comfort while preserving frontend compatibility and low-latency generation.

Detailed runtime ownership remains defined by [Pipeline Responsibility Design](pipeline_responsibility_design.md). Context layout remains defined by [Context Packing Design](context_packing_design.md). Open-LLM-VTuber setup remains defined by [Open-LLM-VTuber Integration Design](open_llm_vtuber_integration.md).

## Product invariant

RelayLM should make an AI character feel continuous without pretending that the character has perfect memory or unrestricted knowledge.

The first product contract is:

> A user can replace the OpenAI-compatible API URL with RelayLM and experience better persona continuity and memory behavior without changing the frontend's conversation, TTS, ASR, or avatar ownership.

RelayLM is successful only when memory and context improvements preserve the character rather than turning it into a generic assistant.

## Product value hierarchy

When product goals conflict, prefer this order:

1. preserve safety and user control,
2. preserve character identity and relationship boundaries,
3. preserve the latest user request and conversational coherence,
4. preserve first-response and first-speech latency,
5. add useful memory and external context,
6. add heavier retrieval or compression only when the earlier goals remain intact.

More retrieved context is not automatically a better product outcome.

## Conversation experience evaluation

RelayLM should be evaluated on two separate axes.

### Technical stability

- URL-swap and OpenAI-compatible behavior,
- latest-input preservation,
- stable-prefix consistency,
- route and namespace isolation,
- memory leakage prevention,
- fallback reliability,
- first-token and first-speech latency,
- streaming continuity.

### Character experience

- persona consistency,
- relationship continuity,
- memory warmth,
- conversation stickiness,
- non-creepiness,
- growth feeling,
- emotional appropriateness,
- correction and forgetting behavior.

These are product-quality signals, not permission to manipulate engagement.

`conversation_stickiness` means that the user wants to continue because the character remains coherent, responsive, and comfortable to talk with. It must not be optimized through pressure, dependency cues, guilt, false urgency, or concealment of system limitations.

`memory_warmth` means that recalled information improves continuity or care without feeling like surveillance. A memory can be factually correct and still fail this criterion when it is disclosed at the wrong time, with excessive specificity, or outside the current scene's allowed memory scope.

`growth_feeling` means that approved relationship, memory, and expression changes create understandable continuity over time. It must not imply silent SOUL mutation or irreversible personality drift.

## Evaluation method

Product evaluation should combine deterministic checks with repeated conversation sessions.

Recommended evidence:

- fixed prompt suites for persona and memory regression,
- paired responses with and without retrieved memory,
- user correction and forgetting scenarios,
- long-session continuity checks,
- scene transitions and recovery scenarios,
- subjective user ratings with short reason labels,
- latency measurements for first token, first sentence, and first TTS enqueue.

A single task-success score is insufficient. RelayLM may answer correctly while still damaging persona continuity, disclosing memory awkwardly, or responding too slowly for a realtime character.

## Realtime VTuber latency posture

AI VTuber use prioritizes fast first speech over maximum retrieval depth.

The normal split is:

```text
synchronous path:
  scope / route / scene / intent
  -> cheap approved retrieval
  -> bounded RelayCTX Repack
  -> streaming backend forward
  -> Stream Unpack / segmentation
  -> first TTS-safe chunk

asynchronous or deferred path:
  memory extraction and consolidation
  -> embeddings / index maintenance
  -> summary refresh
  -> cache or retrieval warmup
  -> RelaySLP candidates
```

The synchronous path should not run expensive rerankers, summarizers, multi-hop retrieval, or extra LLM scoring by default.

## Prefetch and speculation rules

Future optimizations may include:

- query-aware memory warmup,
- ASR partial-transcript prefetch when an external adapter provides it,
- speculative candidate loading,
- speculative context-plan preparation.

They remain optional optimizations and must obey these rules:

- prefetch must not become a core ASR dependency,
- partial transcripts and speculative candidates are untrusted evidence,
- speculative work must not mutate MEM, SOUL, or user-visible state,
- final selection must use the confirmed current input and current scene policy,
- cancelled or superseded speculation must be discardable,
- prefetch failure must fall back to the ordinary synchronous path,
- speculation must not delay first speech when its result is not ready.

## Routing and cache posture

RelayLM supports both deployment styles:

- a single proxy routing multiple characters by model/route identity,
- per-character instances with separate ports and cache namespaces.

The first is onboarding-oriented. The second may improve cache isolation, diagnostics, and stable-prefix reuse. Neither deployment style changes semantic ownership: RelaySCN, RelayINT, RelayMEM, RelayCTX, RelayREF, RelayRUN, and RelaySLP retain the same responsibilities.

## Agent and tool boundary

Agent planning, tool calls, tool observations, and structured-output phases should normally pass through unchanged. Persona/context conditioning should target ordinary chat turns or the final natural-language response after the agent result is stable.

RelayLM must not make tool protocol payloads look like persona prompt blocks, and persona styling must not alter the semantic content of an agent result.

## Product non-goals

These principles do not make RelayLM:

- an engagement-optimization system,
- a replacement for the frontend UI, TTS, ASR, or avatar runtime,
- a general agent framework,
- a vector database or memory product,
- a direct KV-cache controller,
- an authority that silently rewrites character identity.

## Summary

RelayLM should improve the feeling of continuity by combining conservative memory use, stable persona conditioning, scene-aware expression, and realtime latency discipline.

The target is not simply a character that remembers more. The target is a character that remembers appropriately, stays recognizably itself, responds soon enough to feel present, and remains easy for the user to correct or redirect.

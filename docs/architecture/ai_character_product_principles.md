# AI Character Product Principles

## Purpose

This document preserves the product principles that distinguish RelayLM from a generic RAG proxy.

RelayLM remains an OpenAI-compatible runtime proxy. Its product role is to improve persona stability, relationship continuity, memory usefulness, expression appropriateness, and conversational comfort while preserving frontend compatibility and low-latency generation.

Detailed component ownership remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md). Context layout remains in [Context Packing Design](context_packing_design.md). Current implementation state remains in [Project Status](../PROJECT_STATUS.md).

## Product invariant

RelayLM should make an AI character feel continuous without pretending that the character has perfect memory, unrestricted knowledge, or autonomous permission to rewrite its identity.

The basic product contract is:

> A user can point an OpenAI-compatible frontend at RelayLM and experience better persona continuity and memory behavior without RelayLM taking ownership of the frontend UI, input, display history, TTS engine, ASR engine, or avatar runtime.

## Frontend ownership versus context authority

These are separate boundaries.

```text
frontend
  owns UI, user input, visible conversation display/storage,
  interruption controls, TTS/avatar integration, and local presentation

RelayLM managed route
  owns backend-bound context construction,
  client-history/instruction authority normalization,
  visible/internal output separation,
  and adapter-safe output approval
```

A frontend may display its full conversation history while RelayLM excludes that history from the managed backend payload and reconstructs context from RelayLM-owned state.

Explicit `pass_through` routes remain the delegated-authority exception.

## Product value hierarchy

When goals conflict, prefer this order:

1. safety and user control,
2. character identity and relationship boundaries,
3. latest user request and conversational coherence,
4. visible/internal output integrity,
5. first-response and first-speech latency,
6. useful memory and external context,
7. heavier retrieval/compression only when earlier goals remain intact.

More retrieved or remembered content is not automatically better.

## Durable character voice and transient expression

```text
approved RelaySOUL / OUTPUT_POLICY
  durable identity and character voice

Main LLM
  persona-consistent semantic response

RelayEMO
  bounded transient affect/expression hints

external adapters
  TTS/avatar execution
```

Return-side expression must not become hidden meaning-changing rewriting or a second persona generator.

## Character experience

Evaluate separately from technical task success:

- persona consistency,
- relationship continuity,
- memory warmth,
- conversation stickiness without manipulation,
- non-creepiness,
- gradual/reversible growth feeling,
- emotional appropriateness,
- correction and forgetting behavior.

`conversation_stickiness` means the user wants to continue because the character is coherent, responsive, and comfortable—not because of pressure, dependency cues, guilt, false urgency, or concealed limitations.

`memory_warmth` means recalled information improves continuity without feeling like surveillance. Correct memory can still be inappropriate when disclosed with excessive specificity, wrong timing, or outside the allowed scene scope.

`growth_feeling` means approved memory, relationship, and expression changes accumulate coherently. It does not permit silent RelaySOUL mutation.

## Technical stability

Evaluate:

- URL-swap and OpenAI-compatible behavior,
- latest-input preservation,
- managed context reconstruction,
- stable-prefix consistency,
- route/namespace isolation,
- memory and internal-data leakage prevention,
- fallback/recovery reliability,
- first-token/first-safe-speech latency,
- streaming continuity,
- duplicate-emission prevention.

## Evaluation method

Use deterministic checks plus repeated conversation sessions:

- fixed persona/memory regression suites,
- paired responses with/without approved memory,
- user correction and forgetting cases,
- long-session continuity,
- scene transitions and recovery,
- renderer/model comparisons,
- subjective ratings with short reason labels,
- first-token, first-safe-segment, and first-TTS-enqueue timing.

Protected response/feedback samples belong to explicit evaluation/calibration storage, not generic runtime trace.

## Realtime path

```text
synchronous:
  route / authority / scene / affect / intent
  -> bounded approved retrieval
  -> RelayCTX Repack
  -> streaming backend
  -> Stream Unpack / segmentation
  -> REF / EMO / output SCN / RUN gates
  -> first safe TTS chunk

out-of-band:
  governed evidence
  -> RelaySLP candidate extraction/classification
  -> persistence and approval gates
  -> compiled memory/summary/index updates
  -> optional retrieval-cache warmup
```

RelaySLP owns candidate creation and governed memory compilation. Embeddings, index maintenance, summary refresh, and cache warmup are downstream maintenance/apply steps, not predecessors that create SLP candidates.

The synchronous path should not run expensive rerankers, summarizers, multi-hop retrieval, or extra LLM scoring by default.

## Prefetch and speculation

Future optimizations may include query-aware memory warmup, external ASR partial-transcript prefetch, speculative candidate loading, or context-plan preparation.

Rules:

- optional only,
- untrusted until the confirmed input and current scene policy are available,
- no MEM/SOUL/user-visible mutation,
- discardable when superseded,
- no first-speech delay when results are unavailable,
- ordinary synchronous fallback remains valid.

## Memory, relationship, and persona growth

- Retrieval reads only.
- RelaySLP compiles memory candidates through gates.
- Relationship/output-policy changes enter RelaySOUL calibration/revision workflows.
- Normal chat may surface proposals but does not apply persona revisions.
- Core identity changes require explicit approval and rollback.
- Temporary scene/affect state never automatically becomes durable personality.

## TTS and Avatar boundary

RelayLM owns safe output segmentation and engine-neutral expression hints before external consumers receive data.

It does not own:

- speech synthesis execution,
- Live2D expression/motion files,
- avatar runtime scheduling,
- ASR processing.

Text/caption output remains available when TTS/Avatar adapters fail.

## Agent and tool boundary

Agent planning, tool calls, observations, and structured-output phases normally pass through unchanged. Persona/context conditioning targets ordinary chat or an already-stable final natural-language result.

Persona or expression handling must not alter tool protocol payloads, code, commands, structured data, or the semantic result of an agent action.

## Product non-goals

RelayLM is not:

- an engagement-optimization or dependency system,
- a replacement for frontend UI/TTS/ASR/avatar execution,
- a general agent framework,
- a vector database product,
- a direct KV-cache controller,
- an authority that silently rewrites character identity,
- a reason to forward untrusted frontend history as managed backend context.

## Summary

RelayLM should help a character remember appropriately, stay recognizably itself, express transient emotion safely, respond soon enough to feel present, and remain easy for the user to correct or redirect.

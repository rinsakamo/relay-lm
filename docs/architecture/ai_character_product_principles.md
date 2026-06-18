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

## Conversation content and capability authority

RelayLM separates ordinary conversation content from executable capability authority.

> Conversation content is model-owned. Capability execution is RelayLM-governed.

Ordinary natural-language output is determined by the selected model, approved RelaySOUL and OUTPUT_POLICY, current context, and user-controlled configuration. RelayLM does not add a mandatory semantic censorship layer that classifies, suppresses, rewrites, regenerates, or guarantees conversation based on offensiveness, provocation, adult tone, political viewpoint, or similar open-ended content judgments.

This means:

- teasing, insults, arguments, coarse language, adult-oriented tone, and other ordinary conversational expression remain model/SOUL behavior,
- a recommended model profile is a tested compatibility and default-behavior profile, not a guarantee or certification of generated content,
- RelayREF, RelayEMO, RelaySCN, RelaySLP, and output adapters must not become hidden second-pass content moderators or persona-normalization models,
- the synchronous path must not spend latency or compute on a universal secondary LLM or semantic classifier for ordinary conversation,
- malformed protocol output may fail technically, but RelayLM must not replace it with a semantically rewritten answer.

RelayLM does govern capabilities and side effects:

- tool invocation and tool-transaction preservation,
- code or command execution,
- filesystem and protected-data access,
- credential and secret access,
- network access and external API actions,
- persistence, configuration, MEM, and RelaySOUL mutation,
- other externally observable or irreversible side effects.

Capability requests require typed contracts, explicit authority, bounded inputs, and fail-closed gates. A text response that merely contains code, a command, or a request to perform an action remains conversation content. The capability boundary applies only when RelayLM or an attached adapter would interpret that output as an executable action.

Capability gates define RelayLM's required authority boundary and fail-closed behavior; they are not a mathematical proof that every backend, frontend, or future adapter is bug-free or impossible to bypass. An integration that executes tools, code, network actions, persistence, or other side effects outside RelayLM-owned typed gates is outside the RelayLM core guarantee.

RelayCTX Repack and RelayCTX Unpack are core protocol-boundary operations, not semantic censorship. On managed routes, Repack may attach RelayLM-owned SOUL, MEM, RelaySCN, and CTX context to the backend-bound payload. Unpack may separate explicit internal update blocks from user-visible text. These operations maintain the boundary between user-visible conversation and RelayLM-owned internal state; they must not judge, suppress, or rewrite ordinary conversation content based on meaning.

RelayEMO expression markers are optional presentation decoration. They must remain separable from the canonical conversation/capability boundary and must not be treated as required content safety, censorship, or protocol separation.

Optional presentation filters for a specific frontend, broadcast platform, age profile, or deployment policy belong outside the RelayLM core conversation path. They must be explicit adapters or client features rather than concealed mutation of the canonical character response.

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
- first-token/first-adapter-ready-speech latency,
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
- first-token, first-adapter-ready-segment, and first-TTS-enqueue timing.

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
  -> first adapter-ready TTS chunk

out-of-band:
  governed evidence
  -> RelaySLP candidate extraction/classification
  -> persistence and approval gates
  -> compiled memory/summary/index updates
  -> optional retrieval-cache warmup
```

RelaySLP owns candidate creation and governed memory compilation. Embeddings, index maintenance, summary refresh, and cache warmup are downstream maintenance/apply steps, not predecessors that create SLP candidates.

The synchronous path should not run expensive rerankers, summarizers, multi-hop retrieval, extra LLM scoring, or universal semantic moderation by default.

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

RelayLM owns protocol-valid output segmentation and engine-neutral expression hints before external consumers receive data.

It does not own:

- speech synthesis execution,
- Live2D expression/motion files,
- avatar runtime scheduling,
- ASR processing.

Text/caption output remains available when TTS/Avatar adapters fail.

## Agent and tool boundary

Agent planning, tool calls, observations, and structured-output phases normally pass through unchanged. Persona/context conditioning targets ordinary chat or an already-stable final natural-language result.

Persona or expression handling must not alter tool protocol payloads, code, commands, structured data, or the semantic result of an agent action.

Tool calls, code execution, commands, protected-data access, network actions, and mutations remain capability requests even when proposed by ordinary conversation. They do not inherit authority from natural-language output and must pass their own typed runtime gates.

## Product non-goals

RelayLM is not:

- an engagement-optimization or dependency system,
- a replacement for frontend UI/TTS/ASR/avatar execution,
- a general agent framework,
- a vector database product,
- a direct KV-cache controller,
- an authority that silently rewrites character identity,
- a universal semantic censor or guarantor of model-generated conversation,
- a reason to forward untrusted frontend history as managed backend context.

## Summary

RelayLM should help a character remember appropriately, stay recognizably itself, express transient emotion coherently, respond soon enough to feel present, and remain easy for the user to correct or redirect. It governs what the character can execute, access, or mutate without silently governing what the character is allowed to say.
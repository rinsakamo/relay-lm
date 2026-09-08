# LM Studio semantic-first Stage R qualification

This reference defines the repository-owned minimum-sufficient LM Studio Stage R qualification path for RelayLM Core 1.0.

## Purpose

The semantic-first capsule exists to keep evaluation admission from becoming the experiment. Stable non-secret binding facts are declared by the physical transaction, while effective runtime behavior is established by the actual semantic requests and their evidence.

## Admission contract

- The transaction declares the intended LM Studio request model, loaded instance identity, model artifact identity, tokenizer identity when available, quantization, effective context window, and exposed reasoning options.
- The capsule performs no provider-native model inventory request, OpenAI-compatible model-list request, dedicated reasoning probe, or other content-free HTTP preflight.
- The first provider request emitted by the capsule is actual Stage R semantic work through the production OpenAI-compatible two-pass provider.
- Current Core 1.0 reasoning OFF is requested through the existing production realization and must serialize as `reasoning_effort=none`.
- Declared stable binding facts are not completion evidence. Actual request/response evidence remains authoritative for whether the provider was reachable and whether the requested runtime behavior was realized.

## Physical-execution ownership boundary

RelayLM v1 adopts the host-owned physical-execution invariant crystallized by the RelayLM v2 physical procedure:

> **Controller observes and assembles. Host validates and freezes.**

For this LM Studio semantic-first path, that invariant specializes as follows.

Before host entry, the controller may reconstruct fresh repository authority, select an isolated exact checkout, assemble stable non-secret binding declarations from current non-provider-HTTP local/operator evidence, create fresh artifact roots, and validate deterministic argument/repository shape.

The controller or a child evaluation harness must not implement a second host around the repository-owned semantic-first capsule. In particular it must not:

- add provider HTTP model-list, health, dummy-completion, reasoning, or capability probes;
- use a generic capability descriptor as a pre-provider admission veto for an explicit production request;
- convert absence of an independent capability attestation into a negative live provider fact;
- duplicate parser, source-validation, Validator, semantic-acceptance, or runtime-realization checks before the owning request path runs;
- move a failure observed at the real semantic boundary into a new controller-side preflight on a later transaction.

A child diagnostic may change only its owner-authorized diagnostic representation. If it explicitly requests `CognitionStructuredOutputMode.NATIVE`, the real Pass 2 request is the capability boundary. A generic adapter descriptor that reports `structured_output=false` because no independent native structured-output attestation source exists is not permission to stop before that request.

The reusable procedure is materialized at `.ai/skills/lm-studio-semantic-first-preflight/SKILL.md`.

> **Do not implement a second host outside the host.**

## Bounded execution

The capsule executes the current provider-neutral Stage R semantic authority without changing prompts, fixtures, decoding, structured-output schema, Validator behavior, State semantics, Continuity semantics, or Crystallization semantics.

After each scenario, the execution and deterministic-boundary artifacts are persisted before continuation is decided. The scenario sequence stops immediately when the execution records either:

- an actual provider request failure; or
- an explicit two-pass Pass 2 failure.

A deterministic semantic boundary failure is still evidence and is not itself converted into a provider failure by this harness.

The capsule performs no retry, fallback, provider restart, model reload, model substitution, prompt repair, parser relaxation, reasoning escalation, or semantic tuning.

## Completion evidence

Every successful non-streaming semantic completion is passively observed after the existing production provider receives and decodes the HTTP response and before the unchanged production parser consumes the returned envelope. This observation adds no provider request and does not modify the request or response envelope.

For each completion, the capsule persists a create-once sanitized observation containing:

- deterministic completion sequence index and Pass boundary (`conversation` or `extraction`);
- successful HTTP-completion observation and provider finish reason when present;
- provider-supplied prompt, completion, and total token counts when present;
- provider-supplied `completion_tokens_details.reasoning_tokens` when present, together with whether that field was supplied;
- only the presence class `absent`, `empty`, or `nonempty` for `message.reasoning` and `message.reasoning_content`.

Hidden reasoning text is never persisted by this evidence surface. A nonempty reasoning field is recorded only as `nonempty`.

The Stage R summary names every completion-observation artifact and maps each scenario to the observations produced while that scenario executed. Because observations are written immediately after successful provider responses, a later parser or evaluation boundary cannot erase already-produced runtime evidence.

## Evidence interpretation

A connection failure on the first semantic request is `INCONCLUSIVE` for Core semantics because no valid model completion exists. A valid completion may proceed through the ordinary Stage R semantic review.

For a qualification whose current owner requires effective reasoning OFF to be demonstrated from completion evidence, `reasoning_effort=none` on the request is necessary but not sufficient by itself. The owner may require authoritative `reasoning_tokens == 0` plus no `nonempty` `reasoning` or `reasoning_content` observation. If the response evidence required by that owner is absent or ambiguous, the qualification fails closed as `INCONCLUSIVE`; the capsule does not infer effective OFF from output style or from the request wire alone.

Any terminal qualification verdict remains owned by the applicable actual-model qualification Issue; this harness only guarantees the minimum-sufficient execution contract and bounded evidence capture.

## Scope

This is evaluation-only machinery. It must not alter the Core semantic fingerprint. Changes to State, Continuity, cognition prompts, Crystallization, provider production behavior, or acceptance criteria require their own semantic owner and qualification transaction.

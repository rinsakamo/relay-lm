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

## Bounded execution

The capsule executes the current provider-neutral Stage R semantic authority without changing prompts, fixtures, decoding, structured-output schema, Validator behavior, State semantics, Continuity semantics, or Crystallization semantics.

After each scenario, the execution and deterministic-boundary artifacts are persisted before continuation is decided. The scenario sequence stops immediately when the execution records either:

- an actual provider request failure; or
- an explicit two-pass Pass 2 failure.

A deterministic semantic boundary failure is still evidence and is not itself converted into a provider failure by this harness.

The capsule performs no retry, fallback, provider restart, model reload, model substitution, prompt repair, parser relaxation, reasoning escalation, or semantic tuning.

## Evidence interpretation

A connection failure on the first semantic request is `INCONCLUSIVE` for Core semantics because no valid model completion exists. A valid completion may proceed through the ordinary Stage R semantic review. Any terminal qualification verdict remains owned by the applicable actual-model qualification Issue; this harness only guarantees the minimum-sufficient execution contract and bounded evidence capture.

## Scope

This is evaluation-only machinery. It must not alter the Core semantic fingerprint. Changes to State, Continuity, cognition prompts, Crystallization, provider production behavior, or acceptance criteria require their own semantic owner and qualification transaction.

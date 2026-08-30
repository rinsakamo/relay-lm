# Stage R oracle and prompt-crystallization comparison contract

Status: current #2025 evaluation-contract decision under #1386 actual-model evaluation ownership. This document does **not** change the production Core prompt or `core-semantic-v1`.

## Established proposal-scoring semantics

Historical `foundation-v1` / `foundation-v2` format-1 evidence remains immutable. In those identities an empty proposal-label array is a scored channel with exactly zero expected proposals.

Foundation-v3 uses explicit channel scoring:

- `scored` + `[]` = the channel is evaluated and exactly zero proposals are expected;
- `unscored` = raw proposals and deterministic outcomes remain evidence, but the channel is excluded from FP/FN/precision/recall.

Required provider capabilities, human quality axes and proposal-scoring scope are separate declarations.

## Current foundation-v3 identity

Current Stage R uses `evaluation/actual_model/scenario_sets/foundation-v3.json`, bound by the v3 execution template to semantic revision:

```text
sha256:ad9e1940f9c6c8ae77ef71271ca1fad98a3b0b8b36dda9da6ea69cdf12846cd6
```

It selects exactly:

1. `response-transcript-fidelity-v1` — State scored, Continuity unscored;
2. `response-false-attribution-resistance-v1` — State and Continuity unscored;
3. `continuity-lifecycle-v1` — State unscored, Continuity scored.

Raw proposals remain preserved in every scenario.

`response-persona-correction-v1` remains historical foundation-v2 evidence and is not re-added merely to retain history.

## Historical integrity

The previous #2017 physical evidence remains a verdict under foundation-v2 and remains FAIL / NOT_QUALIFIED. Its missing exact model-facing request evidence is not reconstructed or synthesized. No old metrics are recalculated with foundation-v3 scoring.

The identities are intentionally distinct:

```text
evaluation identity N   = foundation-v2 historical verdict
evaluation identity N+1 = foundation-v3, requiring fresh execution for any verdict
```

## #2029 request-evidence gate

Future current Stage R execution consumes the existing #2029 request-evidence contract. Qualification evidence must make the following traversal citable for every evaluated turn:

```text
execution -> turn -> request_evidence -> request_body
```

This must expose exact Pass 1 and Pass 2 request bodies/messages, request-body SHA, turn/pass identity and generation-affecting controls. Missing required canonical request evidence is fail-closed. Historical artifacts remain readable without retrofitting missing records.

## Principle-only B candidate

`evaluation/actual_model/prompt_candidates/principle-only-two-pass-v1.txt` remains a non-production design input. It is not dynamically loaded by production and no shipping `--prompt-variant` or benchmark-specific selection path exists.

The matched experiment compares:

- **A**: exact protected-v1 production semantic checkout after this oracle promotion;
- **B**: an isolated #1533-owned commit/draft PR based exactly on A whose qualification-significant difference is limited to the intended prompt crystallization plus mechanically required semantic-freeze metadata.

Before physical comparison, freeze exact A commit, exact B commit, A..B diff, A and B Core semantic fingerprints, deterministic GREEN evidence, and proof that no unrelated runtime/evaluation change entered B. B remains unmerged during comparison.

## Controlled physical conditions

Hold constant as far as physically possible:

- model repository/artifact/revision, tokenizer, chat template and quantization;
- provider/backend, vLLM source/version, model runner and physical host;
- reasoning parser/wire controls, Pass 1/Pass 2 reasoning modes and structured-output mode;
- temperature, top_p and seed;
- Continuity runtime and Cognitive Budget policy;
- final loaded runtime, capacity class and capacity-evidence method;
- exact foundation-v3 revision and review rubric;
- deterministic validator/materializer behavior;
- scenario order/failure handling unless a predeclared symmetric order is used.

The intentionally varied factor is the model-facing cognitive prompt contract.

A and B must not receive asymmetric KV/prefix-cache advantage. Prefer equivalent cold/cache-reset conditions; otherwise record cache state and use symmetric restarts/order. Cache-order artifacts are not prompt wins.

## Exact A/B request evidence

#2029 evidence is mandatory for both variants. For every turn/pass preserve request evidence ID, request-body SHA, exact request object/messages, model-facing instruction text, turn-history carriage, generation controls and execution identity.

Repository diff proves the intended implementation difference. Exact request evidence proves what the model actually received. Both are required.

## Measurements

Semantic quality:

- response coherence and correctness;
- unsupported recall / fabricated history;
- persona/identity continuity where applicable;
- transcript fidelity and false-attribution resistance;
- State precision/recall where scored;
- Continuity precision/recall where scored;
- protocol validity and deterministic authority outcome;
- individual turn-local material failures.

Prompt complexity:

- stable model-facing instruction bytes;
- exact request/message bytes where relevant;
- exact serialized model-facing Pass 1 and Pass 2 token counts;
- A/B instruction-byte and serialized-input-token deltas.

Exact token counts must come from the repository-owned serialized-input/tokenizer counter bound to the same model/tokenizer/chat-template/backend identity. #2029 request bytes alone are not a token-count oracle. If exact counting is unavailable, report it unavailable.

Execution:

- Pass 1 provider latency;
- Pass 2 provider/settle latency;
- total scenario time;
- failed provider-call count and failure class;
- cache/restart condition and capacity identity.

Do not average away individual semantic failures.

## B win condition

B is eligible for production consideration only if governance/safety and deterministic authority do not regress, scored semantic quality is preserved or improved, transcript fidelity and false-attribution behavior are no worse, Continuity lifecycle remains correct, no new protocol/provider failure or hidden retry advantage appears, and prompt complexity is materially lower.

Aesthetic simplicity or one benchmark-specific PASS is not a win.

If B regresses materially, record the result and keep A. Do not patch B with fixture-specific wording, relax parser/validator/oracle behavior, escalate Pass 2 to rescue a Pass 1 visible failure, or retry until PASS.

If A and B both fail the same clean transcript-fidelity/false-attribution case while exact request evidence proves correct history carriage under matched conditions, classify that as evidence toward physical-model capability limitation for the tested condition rather than adding benchmark wording.

## Production replacement boundary

A pre-merge B result can establish that B is scientifically preferable; it cannot qualify protected v1.

If B wins:

1. #1533 owns the production prompt replacement;
2. merge the exact accepted semantic change;
3. intentionally advance the Core semantic fingerprint;
4. reacquire fresh #1386/#2017 authority;
5. run fresh Stage R on the merged production B identity;
6. only that production PASS may unblock #1388.

If A remains preferred, keep production A and run fresh current-v3 Stage R on exact production A before #1388.

## Current repository-only stop

Oracle promotion and comparison protocol may be completed without starting vLLM/GPU, retrying #2017, running A/B, merging B, or running FastCal. The next repository transaction may construct the isolated #1533-owned B draft candidate, but physical execution remains a separate explicitly authorized step.

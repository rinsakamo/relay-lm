# Gemma 4 synthetic cache-boundary × SWA-cache matrix

Diagnostic only. This probe is independent of RelayLM RC1 and production cache policy.

## Why this probe exists

The historical #2947 request bodies are no longer recoverable from retained evidence: the provider ledger preserves hashes and metadata, not complete request bodies. Reconstructing those prompts through a current RelayLM compiler would introduce a new variable.

Therefore this probe deliberately stops trying to reproduce the historical semantic fixture. It tests the lower-level mechanism with a new, self-contained token-array fixture that is created once, hashed, frozen, and then reused byte-for-byte across all conditions.

Questions:

1. Does maximum-LCP reuse remain numerically different from a cold prefill after the unnecessary checkpoint rollback is suppressed?
2. Does limiting reuse to a complete physical `n_ubatch` boundary remove that difference?
3. Independently, does `--swa-full` remove or materially reduce the difference while keeping maximum-LCP reuse?

## Physical identity

Use the same model/runtime family as the successful rollback diagnostic:

- llama.cpp: `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`
- model: Gemma 4 12B IT Q4_K_M
- GGUF SHA256: `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`
- context: 8192
- slots: 1
- `-ngl 999`
- `--no-context-shift`
- `--flash-attn on`
- `n_batch = 2048`
- `n_ubatch = 512`
- greedy / temperature zero
- one generated token for every measured request
- top probabilities/logprobs enabled, target top-N = 20 (minimum 5 if exact build limits it)

`--flash-attn on` is part of the frozen physical identity for every arm and every paired cold control. Do not use `auto` or `off` inside this probe. Before any measured generation, retain startup evidence showing that the server accepted the option and that Flash Attention is actually enabled for the loaded model/backend. If the exact build rejects the option, cannot enable Flash Attention, or exits before readiness, stop `PHYSICAL_PROBE_UNSPENT`.

Use fresh temporary llama.cpp checkouts/builds. Never touch the primary dirty checkout.

## Startup-only readiness gate

Server startup, model load, health checking, and failure diagnosis before the first measured one-token generation are mechanical and do not consume the semantic probe budget.

For every server lifetime, before sending any measured prompt:

1. retain the complete command line;
2. redirect and retain complete stdout/stderr from process start;
3. retain the process exit code if it exits;
4. confirm the expected TCP port is free before launch and owned by the new server after launch;
5. wait only for a bounded readiness condition; health polling itself is not inference;
6. confirm model load, CUDA/backend initialization, `n_batch=2048`, `n_ubatch=512`, context=8192, slots=1, context shift disabled, and Flash Attention enabled from server evidence;
7. do not send fixture, completion, token-generation, warmup-generation, or semantic requests as a readiness test.

If readiness fails before any measured generation, retain the startup log and classify `PHYSICAL_PROBE_UNSPENT`. A new separately-started attempt after diagnosing a purely mechanical startup failure is permitted because no measured inference occurred; it is not a semantic retry/replay. The terminal record must preserve every pre-inference startup attempt and its reason. Do not alter fixture bytes, model bytes, source revision, patches, inference parameters, or matrix design while doing mechanical startup diagnosis.

## Diagnostic patches

### Maximum-reuse patch

`diagnostics/llama-cpp/e2d2c0d6-gemma4-swa-live-prefix-diagnostic.patch`

SHA256:

`cfb1a054ec5b89e7a271c2042ee6135a876d0f18d7f357d819224df06ac833f4`

This suppresses only the already-demonstrated unnecessary live-SWA checkpoint rollback. It leaves maximum LCP reuse intact.

### Aligned-reuse patch

`diagnostics/llama-cpp/e2d2c0d6-gemma4-swa-ubatch-aligned-reuse-diagnostic.patch`

SHA256:

`cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a`

This contains the same rollback suppression plus:

`aligned_reuse = floor(LCP / n_ubatch) * n_ubatch`

Do not stack the two patches. Each arm uses a clean exact checkout with exactly one patch.

## Synthetic frozen token fixture

Do not use RelayLM, a chat template, historical payload reconstruction, or a current compiler.

Build the fixture mechanically before measured inference:

1. Tokenize a deterministic recorded plain-text corpus with the exact model tokenizer, without generation. Retain the source bytes and SHA256.
2. Let the resulting deterministic token list be `T`, with at least 5200 ordinary token IDs.
3. `P = T[0:865]`.
4. `WA = T[865:883]`; `warm = P + WA`, exactly 883 tokens.
5. Find the first `j >= 1024` such that `T[j] != WA[0]` and at least 2062 tokens remain.
6. `target = P + T[j:j+2062]`, exactly 2927 tokens.
7. Assert `LCP(warm, target) == 865`.
8. Persist `warm-token-ids.json` and `target-token-ids.json` plus SHA256 before measured inference.

The numeric arrays are the fixture authority after this point. No subsequent tokenization is allowed for measured requests.

Required geometry:

- warm length = 883
- target length = 2927
- LCP = 865
- `n_swa = 1024`
- `n_ubatch = 512`

This does not claim semantic equivalence to #2947.

## Matrix and paired controls

Each arm uses its own fresh warm-target server and its own fresh cold-control server. All six measured server lifetimes use `--flash-attn on`.

### Arm M — compact SWA, maximum reuse

Binary/config:

- exact e2d2
- maximum-reuse patch only
- default compact SWA cache
- no `--swa-full`
- `--flash-attn on`

Warm-target:

- M0: `warm`, `cache_prompt=true`, one token
- M1: `target`, `cache_prompt=true`, one token + top probabilities

M1 hard path:

- LCP = 865
- no rollback to 366
- `cache_n/n_past = 865`
- prompt eval = 2062

Fresh paired cold server, identical binary/config:

- MC: `target`, `cache_prompt=false`
- reuse = 0
- prompt eval = 2927

### Arm A — compact SWA, 512-aligned reuse

Binary/config:

- exact e2d2
- aligned-reuse patch only
- default compact SWA cache
- no `--swa-full`
- `--flash-attn on`

Warm-target:

- A0: `warm`, `cache_prompt=true`, one token
- A1: `target`, `cache_prompt=true`, one token + top probabilities

A1 hard path:

- raw LCP = 865
- no rollback to 366
- effective `cache_n/n_past = 512`
- prompt eval = 2415

Fresh paired cold server, identical binary/config:

- AC: `target`, `cache_prompt=false`
- reuse = 0
- prompt eval = 2927

### Arm F — full-size SWA cache, maximum reuse

Binary/config:

- exact e2d2
- maximum-reuse patch only
- `--swa-full`
- `--flash-attn on`

Warm-target:

- F0: `warm`, `cache_prompt=true`, one token
- F1: `target`, `cache_prompt=true`, one token + top probabilities

F1 hard path:

- raw LCP = 865
- no rollback to 366
- maximum reuse = 865
- `cache_n/n_past = 865`
- prompt eval = 2062

Fresh paired cold server, identical config including `--swa-full` and `--flash-attn on`:

- FC: `target`, `cache_prompt=false`
- reuse = 0
- prompt eval = 2927

If an arm does not exercise its hard path after inference begins, retain it as `PROBE_NOT_EXERCISED`; do not repair or rerun that arm.

## Measurements

For M1/MC, A1/AC, and F1/FC retain:

- exact numeric prompt-array SHA256
- exact serialized request SHA256
- first generated token ID/text
- top-N token IDs and reported logprobs/probabilities
- top-1/top-2 margin
- per-token delta on the intersection of top-N sets
- maximum absolute reported delta on that intersection
- `cache_n/n_past`
- prompt-eval count and timing
- checkpoint search/restore events
- complete raw response
- complete llama-server log
- explicit Flash Attention startup evidence

Also retain source revision, patch SHA, binary SHA, model SHA, command line, GPU identity, fixture source bytes/hash, token-array hashes, and exact request counters.

Do not impose an arbitrary numerical tolerance. Report API-visible exact equality separately from measured deltas.

## Interpretation

Evaluate each arm only against its paired cold control:

- `M_equal = M1 == MC` at API-reported first-token/top-N values
- `A_equal = A1 == AC`
- `F_equal = F1 == FC`

Also report first-token-ID equality separately from logprob equality.

Primary patterns:

### `ALIGNMENT_EXPLAINS_RESIDUAL_DRIFT`

`M_equal = false` and `A_equal = true`.

### `SWA_FULL_EXPLAINS_RESIDUAL_DRIFT`

`M_equal = false`, `F_equal = true`, `A_equal = false`.

### `BOTH_ALIGNMENT_AND_SWA_FULL_RESTORE_IDENTITY`

`M_equal = false`, `A_equal = true`, `F_equal = true`.

### `NEITHER_INTERVENTION_RESTORES_IDENTITY`

`M_equal = false`, `A_equal = false`, `F_equal = false`.

### `SYNTHETIC_FIXTURE_SHOWS_NO_BASELINE_DRIFT`

`M_equal = true`.

### `PROBE_NOT_EXERCISED`

Inference began but a required hard path prediction failed.

### `PHYSICAL_PROBE_UNSPENT`

Any required source/patch/model/build/fixture/startup/Flash-Attention identity fails before the first measured inference request.

## Mechanism note

This probe does not assume that Online Softmax is the unique cause of cache/cold drift. Flash Attention commonly uses tiled/online normalization machinery, but the tested mechanism is broader: different physical batch/tile/reduction/kernel provenance may produce small floating-point differences in cached hidden/KV states. `n_ubatch` alignment tests whether restoring the same physical prefill boundary removes the API-visible residual under a fixed Flash Attention path. A later `--flash-attn off` discriminator is only justified if this matrix exercises baseline drift and leaves ambiguity; do not add it to this spend.

## Accounting

Fixture construction, tokenization, hashing, patch checks, compilation, model load, server startup, readiness polling, and startup-failure diagnosis are mechanical and do not consume the semantic probe budget.

The first measured one-token generation begins the probe. After that:

- no retry
- no replay
- no reseed
- no fallback
- no repair
- no replacement fixture
- no parameter tuning

A failure after first measured generation is exercised/partial, not `UNSPENT`.

## Boundaries

- protected RelayLM `v1` mutation = 0
- production code/cache policy mutation = 0
- RC1 action = 0
- #2934 rerun = 0
- #2947 rerun = 0
- historical prompt reconstruction = 0
- upstream submission = 0
- primary dirty checkout mutation = 0

This is a mechanism probe, not a production qualification or a claim that `--swa-full`, ubatch-aligned reuse, or Flash Attention configuration is generally safe.
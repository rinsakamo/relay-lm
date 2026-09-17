# Gemma 4 synthetic cache-boundary × SWA-cache matrix

Diagnostic only. This probe is independent of RelayLM RC1 and production cache policy.

## Why this probe exists

The historical #2947 request bodies are no longer recoverable from retained evidence: the provider ledger preserves hashes and metadata, not complete request bodies. Reconstructing those prompts through a current RelayLM compiler would introduce a new variable.

Therefore this probe deliberately stops trying to reproduce the historical semantic fixture. It tests the lower-level mechanism with a new, self-contained token-array fixture that is created once, hashed, frozen, and then reused byte-for-byte across all conditions.

The questions are:

1. Does maximum-LCP reuse remain numerically different from a cold prefill after the unnecessary checkpoint rollback is suppressed?
2. Does limiting reuse to a complete physical `n_ubatch` boundary remove that difference?
3. Independently, does `--swa-full` remove or materially reduce the difference while keeping maximum-LCP reuse?

## Physical identity

Use the same physical identity as the successful rollback diagnostic:

- llama.cpp: `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`
- model: Gemma 4 12B IT Q4_K_M
- GGUF SHA256: `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`
- context: 8192
- slots: 1
- `-ngl 999`
- `--no-context-shift`
- `n_batch = 2048`
- `n_ubatch = 512`
- greedy / temperature zero
- one generated token for every measured request
- top probabilities/logprobs enabled, target top-N = 20 (minimum 5 if exact build limits it)

Use fresh temporary llama.cpp checkouts/builds. Never touch the primary dirty checkout.

## Diagnostic patches

### Maximum-reuse patch

`diagnostics/llama-cpp/e2d2c0d6-gemma4-swa-live-prefix-diagnostic.patch`

SHA256:

`cfb1a054ec5b89e7a271c2042ee6135a876d0f18d7f357d819224df06ac833f4`

This only suppresses the already-demonstrated unnecessary live-SWA checkpoint rollback. It leaves maximum LCP reuse intact.

### Aligned-reuse patch

`diagnostics/llama-cpp/e2d2c0d6-gemma4-swa-ubatch-aligned-reuse-diagnostic.patch`

SHA256:

`cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a`

This contains the same rollback suppression plus the diagnostic cap:

`aligned_reuse = floor(LCP / n_ubatch) * n_ubatch`

Do not stack these patches. Each arm uses a clean exact checkout with exactly one patch.

## Synthetic frozen token fixture

Do not use RelayLM, a chat template, historical payload reconstruction, or a current compiler.

The exact e2d2 server accepts numeric token arrays directly as `prompt` input. Build the fixture mechanically before any measured inference:

1. Start an exact unpatched tokenizer-capable server or use the exact model tokenizer without generation.
2. Tokenize a deterministic, recorded plain-text corpus long enough to yield at least 5200 ordinary token IDs. The source text bytes and SHA256 must be retained.
3. Let the resulting deterministic token list be `T`.
4. Define shared prefix `P = T[0:865]`.
5. Define warm suffix `WA = T[865:883]`, so `warm = P + WA` has exactly 883 tokens.
6. Find the first index `j >= 1024` for which `T[j] != WA[0]` and enough tokens remain for 2062 tokens.
7. Define `target = P + T[j:j+2062]`, so target has exactly 2927 tokens.
8. Assert mechanically that `LCP(warm, target) == 865`.
9. Persist `warm-token-ids.json` and `target-token-ids.json` and their SHA256 values before measured inference.

The numeric arrays themselves are the fixture authority after this point. No subsequent tokenization is allowed for measured requests.

This fixture intentionally preserves the historical geometry only:

- warm length = 883
- target length = 2927
- LCP = 865
- `n_swa = 1024`
- `n_ubatch = 512`

It does not claim semantic equivalence to #2947.

## Matrix and paired controls

Use three independent arms. Each arm gets its own fresh warm-target server and its own fresh cold-control server so patch/configuration differences cannot contaminate the control.

### Arm M — compact SWA, maximum reuse

Binary/config:

- exact e2d2
- maximum-reuse patch only
- default compact SWA cache; no `--swa-full`

Warm-target server:

- M0: `warm`, `cache_prompt=true`, one token
- M1: `target`, `cache_prompt=true`, one token + top probabilities

Hard path prediction for M1:

- LCP = 865
- no rollback to 366
- `cache_n/n_past = 865`
- prompt eval = 2062

Fresh cold-control server with identical binary/config:

- MC: `target`, `cache_prompt=false`, one token + top probabilities
- `cache_n/n_past = 0`
- prompt eval = 2927

### Arm A — compact SWA, 512-aligned reuse

Binary/config:

- exact e2d2
- aligned-reuse patch only
- default compact SWA cache; no `--swa-full`

Warm-target server:

- A0: `warm`, `cache_prompt=true`, one token
- A1: `target`, `cache_prompt=true`, one token + top probabilities

Hard path prediction for A1:

- raw LCP = 865
- no rollback to 366
- effective `cache_n/n_past = 512`
- prompt eval = 2415

Fresh cold-control server with identical binary/config:

- AC: `target`, `cache_prompt=false`, one token + top probabilities
- `cache_n/n_past = 0`
- prompt eval = 2927

### Arm F — full-size SWA cache, maximum reuse

Binary/config:

- exact e2d2
- maximum-reuse patch only
- add `--swa-full`

Warm-target server:

- F0: `warm`, `cache_prompt=true`, one token
- F1: `target`, `cache_prompt=true`, one token + top probabilities

Required before interpretation:

- raw LCP = 865
- no rollback to 366
- maximum reuse remains 865
- `cache_n/n_past = 865`
- prompt eval = 2062

Fresh cold-control server with identical binary/config including `--swa-full`:

- FC: `target`, `cache_prompt=false`, one token + top probabilities
- `cache_n/n_past = 0`
- prompt eval = 2927

If the F arm does not exercise maximum reuse 865, classify the arm as not exercised rather than repairing it.

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

Also retain source revision, patch SHA, patched binary SHA, model SHA, command line, GPU identity, fixture source bytes/hash, token-array files/hashes, and exact request counters.

Do not impose an arbitrary numerical tolerance. Report exact API-visible equality separately from measured deltas.

## Interpretation

Evaluate each arm only against its paired cold control:

- `M_equal = reported first-token/top-N result of M1 equals MC`
- `A_equal = reported first-token/top-N result of A1 equals AC`
- `F_equal = reported first-token/top-N result of F1 equals FC`

Also report whether first-token ID matches even when reported logprobs differ.

Primary factual patterns:

### `ALIGNMENT_EXPLAINS_RESIDUAL_DRIFT`

`M_equal = false` and `A_equal = true`.

This strongly supports partial-physical-ubatch provenance as the residual cache/cold difference for this fixture.

### `SWA_FULL_EXPLAINS_RESIDUAL_DRIFT`

`M_equal = false` and `F_equal = true`, while `A_equal = false`.

This supports compact SWA cache/state machinery as the stronger explanation for this fixture.

### `BOTH_ALIGNMENT_AND_SWA_FULL_RESTORE_IDENTITY`

`M_equal = false`, `A_equal = true`, and `F_equal = true`.

Both interventions independently remove the reported residual difference; do not infer which mechanism is uniquely causal without another discriminator.

### `NEITHER_INTERVENTION_RESTORES_IDENTITY`

`M_equal = false`, `A_equal = false`, and `F_equal = false`.

The residual difference is not explained by either tested mechanism alone.

### `SYNTHETIC_FIXTURE_SHOWS_NO_BASELINE_DRIFT`

`M_equal = true`.

The synthetic fixture does not reproduce the residual phenomenon and cannot discriminate the mechanisms, regardless of A/F results.

### `PROBE_NOT_EXERCISED`

Inference began, but one or more hard path predictions failed for the affected arm.

### `PHYSICAL_PROBE_UNSPENT`

Any required source/patch/model/build/fixture identity fails before the first measured inference request.

## Accounting

Fixture text construction, tokenization, hashing, patch apply checks, compilation, and model-load/preflight are mechanical and do not consume the semantic probe budget.

The first measured one-token generation begins the probe. After that:

- no retry
- no replay
- no reseed
- no fallback
- no repair
- no replacement fixture
- no parameter tuning

A failure after the first measured generation is retained as an exercised/partial probe, not converted back to UNSPENT.

## Boundaries

- protected RelayLM `v1` mutation = 0
- production code/cache policy mutation = 0
- RC1 action = 0
- #2934 rerun = 0
- #2947 rerun = 0
- historical prompt reconstruction = 0
- upstream submission = 0
- primary dirty checkout mutation = 0

This is a mechanism probe, not a production qualification or a claim that `--swa-full` or ubatch-aligned reuse is generally safe.
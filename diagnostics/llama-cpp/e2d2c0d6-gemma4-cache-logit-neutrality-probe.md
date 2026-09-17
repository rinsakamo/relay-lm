# Gemma 4 residual cache/cold logit-neutrality probe

Diagnostic only. This is independent of RelayLM RC1 and does not change production cache policy.

## Question

After suppressing the unnecessary SWA checkpoint rollback that caused #2947 buffered Pass2 failure, does `cache_prompt=true` still change the next-token logits relative to a cold `cache_prompt=false` evaluation of the same target prompt?

This targets the residual difference observed after the rollback discriminator:

- historical cold buffered Pass2: ~96 completion tokens / `stop`
- patched cache-on buffered Pass2: 179 completion tokens / `stop`

The fatal structured-output failure was removed, but the trajectories were not identical.

## Current leading mechanism

The target server uses `n_ubatch = 512`.

The warm source prompt is 883 tokens, so prompt ingestion is expected to end with a partial physical ubatch (approximately `512 + 371`). The target buffered Pass2 is 2927 tokens, whose cold ingestion continues with full 512-token ubatches. Therefore the shared prefix region after token 512 is computed under different matrix shapes in the warm and cold paths.

llama.cpp documents that backend logits are not guaranteed bit-for-bit identical for different batch sizes, and upstream discussion attributes this to floating-point rounding changes caused by different matrix shapes. Current upstream issue #28368 independently reports measurable Gemma 4 logprob changes when toggling `cache_prompt` alone on an otherwise-identical warmed server.

This probe measures the phenomenon directly before attempting any second fix.

## Physical identity

Use the same exact physical identity as the successful checkpoint diagnostic:

- llama.cpp revision: `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`
- corrected rollback diagnostic patch SHA256: `cfb1a054ec5b89e7a271c2042ee6135a876d0f18d7f357d819224df06ac833f4`
- model: Gemma 4 12B IT Q4_K_M
- GGUF SHA256: `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`
- context: 8192
- slots: 1
- `-ngl 999`
- `--no-context-shift`
- reasoning: none
- `n_batch = 2048`
- `n_ubatch = 512`

Use a fresh temporary llama.cpp checkout/build. Do not touch the primary dirty checkout.

## Source requests

Use the exact upstream g1 and g2 request bodies retained by the successful diagnostic's `provider-request-ledger.json`. Do not reconstruct messages from memory.

Before inference, verify that the probe version of g1 still tokenizes to 883 prompt tokens and the probe version of g2 still tokenizes to 2927 prompt tokens. If prompt identity changes, stop `UNSPENT`.

For the probe requests, keep prompt-affecting fields identical. Generation-only changes are allowed solely to expose next-token probabilities:

- `max_tokens = 1`
- greedy/temperature-zero behavior
- `logprobs = true`
- `top_logprobs = 20` (or the maximum supported value no smaller than 5)

If the OpenAI-compatible route cannot expose top logprobs without changing prompt tokenization, use llama-server `/apply-template` + `/tokenize` to prove exact prompt-token identity, then `/completion` with the exact token-id array, `n_predict=1`, `n_probs=20`, and greedy sampling.

Do not silently switch prompt representations without proving exact token-id equality.

## Fixed transaction sequence

One fresh patched llama-server process. No retries/replays.

1. **Warm source W0** — send the exact g1 prompt with `cache_prompt=true` and one-token generation. This exists only to populate the live KV using the 883-token prompt-processing shape.
2. **Warm target W1** — send the target g2 probe with `cache_prompt=true`. Require:
   - LCP = 865
   - no checkpoint rollback to 366
   - `cache_n/n_past = 865`
   - prompt eval = 2062 tokens
   - capture first generated token and top-logprobs.
3. **Cold target C1** — on the same process, send the byte-identical target probe except `cache_prompt=false`. Require:
   - prompt eval = 2927 tokens
   - no reused prefix
   - capture first generated token and top-logprobs.

`W1` and `C1` must differ only in `cache_prompt`.

The sequence is fixed. Do not reverse the order, add a second warm-up, or rerun any request.

## Measurements

For W1 and C1 record:

- exact serialized request SHA256
- prompt token-id SHA256
- first generated token id/text
- top-N token ids and logprobs
- top-1/top-2 margin
- per-token logprob delta for the intersection of both top-N sets
- maximum absolute observed logprob delta in that intersection
- `cache_n/n_past`
- prompt-eval token count/time
- checkpoint search/restore events

Also retain the complete llama-server log and raw response payloads.

## Interpretation

Do not impose an arbitrary tolerance or call any non-zero delta a correctness bug.

Classify factually:

### `FIRST_TOKEN_IDENTICAL_REPORTED_LOGITS_IDENTICAL`

The same top-N ids/logprobs are identical to the precision reported by the API.

### `FIRST_TOKEN_IDENTICAL_LOGITS_DIFFER`

The greedy first token is the same, but one or more reported logits/logprobs differ. This directly confirms residual numerical non-neutrality while showing it has not crossed the first-token decision boundary for this prompt.

### `FIRST_TOKEN_FLIPS_WITH_CACHE_REUSE`

The greedy first token differs between W1 and C1. This demonstrates that cache reuse crosses a decision boundary immediately for this exact prompt even after removing the checkpoint rollback.

### `PROBE_NOT_EXERCISED`

Expected prompt identity, LCP=865, rollback suppression, or cache counts are not observed.

### `PHYSICAL_PROBE_UNSPENT`

Any pre-inference identity/build/request-shape requirement fails.

A result showing numerical non-neutrality is not by itself proof of a second server-state bug: llama.cpp currently documents backend-dependent non-bit-identical logits for different batch sizes. The next discriminator, only if warranted, is to control physical ubatch shape (for example an aligned-prefix or `n_ubatch=1` small probe) to separate ordinary floating-point batch-shape drift from an additional cache-state correctness defect.

## Hard boundaries

- RelayLM protected `v1` mutation = 0
- production code/policy mutation = 0
- RC1 action = 0
- #2934 rerun = 0
- #2947 rerun = 0
- upstream submission = 0
- primary dirty checkout mutation = 0
- retries/replays/reseeds/fallbacks = 0

The existing rollback diagnostic patch remains diagnostic-only and is not promoted to production by this probe.

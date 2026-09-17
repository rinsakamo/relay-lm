# Gemma 4 physical-ubatch-aligned cache reuse discriminator

Diagnostic only. Independent of RelayLM RC1 and production cache policy.

## Question

Does limiting live prompt-cache reuse to complete `n_ubatch` boundaries remove the
residual cold/cache numerical difference that remained after the checkpoint
rollback failure was repaired?

The successful prior diagnostic proved that suppressing the unnecessary
`865 -> 366` checkpoint rollback changes buffered Pass2 from `length` / parser
failure to `stop` / valid structured materialization. It did not restore the
historical cold trajectory: patched max-reuse g2 produced 179 completion tokens,
while historical cold g2 produced about 96.

## Mechanism under test

For the exact target runtime:

- `n_batch = 2048`
- `n_ubatch = 512`
- warm source prompt = 883 tokens
- target prompt = 2927 tokens
- target LCP after warm source = 865 tokens

Maximum reuse keeps 865 tokens. Tokens in the shared prefix after position 511
were therefore originally computed as part of the warm source's final partial
physical ubatch, whereas a cold target prefill computes those positions in full
512-token physical ubatches.

The diagnostic cap is:

`aligned_reuse = floor(LCP / n_ubatch) * n_ubatch`

For this case:

`floor(865 / 512) * 512 = 512`

After reusing exactly 512 tokens, the target's recomputed positions have the
same physical ubatch boundaries as cold prefill:

- cold target: `[0,511] [512,1023] [1024,1535] [1536,2047] [2048,2559] [2560,2926]`
- aligned reuse recomputes:
  `[512,1023] [1024,1535] [1536,2047] [2048,2559] [2560,2926]`

The server-level logical prompt batches are also compatible with this:
cold `2048 + 879`, aligned-reuse remainder `2048 + 367`.

## Diagnostic patch

Target llama.cpp revision:

`e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`

Combined patch SHA256:

`cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a`

The combined patch contains both:

1. the previously successful narrow live-SWA checkpoint-rollback suppression;
2. the new live-prefix cap to the largest positive complete `n_ubatch`.

Apply this combined patch to a clean exact source checkout. Do **not** apply the
older rollback patch first.

## Physical identity

Use the same physical identity as the successful rollback diagnostic:

- model: Gemma 4 12B IT Q4_K_M
- GGUF SHA256:
  `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`
- WSL2 / RTX 3060 12 GB
- context = 8192
- slots = 1
- `-ngl 999`
- `--no-context-shift`
- reasoning = none
- `n_batch = 2048`
- `n_ubatch = 512`

Use a fresh temporary checkout/build. Never touch the primary dirty checkout.

## Exact prompt identity

Use the exact g1 and g2 prompt/request material retained by the successful
diagnostic evidence. Do not reconstruct the messages from memory.

Before semantic inference:

- g1 prompt tokens must equal 883;
- g2 prompt tokens must equal 2927;
- the g2 probe prompt-token-id SHA must be identical between cache-on and
  cache-off target requests.

If identity cannot be proved, stop `PHYSICAL_PROBE_UNSPENT`.

## Fixed probe sequence

Run one fresh patched llama-server process. No retries, replay, reseed, fallback,
or repair.

### W0 — warm source

Send exact g1 prompt with `cache_prompt=true`, greedy behavior, and one generated
token. Its purpose is only to establish the 883-token warm computation path.

### W1 — aligned cache target

Send exact g2 target prompt with:

- `cache_prompt=true`
- greedy / temperature zero
- one generated token
- top logprobs enabled

Hard path predictions:

- LCP = 865
- old `[0,366]` checkpoint restore absent
- reuse is capped from 865 to **512**
- `cache_n/n_past = 512`
- prompt eval = **2415** tokens
- capture first token and top-N logprobs

### C1 — cold target

On the same process, send the byte-identical target probe except:

- `cache_prompt=false`

Hard path predictions:

- reused prefix = 0
- prompt eval = **2927** tokens
- capture first token and top-N logprobs

W1 and C1 must differ only in `cache_prompt`.

## Measurements

For W1 and C1 retain:

- exact serialized request SHA256
- prompt-token-id SHA256
- first generated token id/text
- top-N token ids and logprobs
- top-1/top-2 margin
- logprob deltas for intersecting top-N tokens
- maximum absolute reported logprob delta
- `cache_n/n_past`
- prompt-eval token count and timing
- checkpoint search/restore events
- complete raw response payload
- complete llama-server log

Also retain source/patch/build/model identities and transaction counters.

## Classifications

### `UBATCH_ALIGNMENT_RESTORES_REPORTED_LOGIT_IDENTITY`

W1 exercises reuse=512 / prompt-eval=2415, and W1/C1 return the same first token
and identical top-N ids/logprobs to the precision reported by the API.

This strongly supports physical ubatch-shape mismatch as the residual
cold/cache difference for this prompt.

### `UBATCH_ALIGNMENT_PRESERVES_TOKEN_BUT_LOGITS_DIFFER`

The first token is the same but reported logprobs still differ.

Physical ubatch alignment is not sufficient to make reuse numerically neutral.
Do not infer an additional state bug yet; measure the remaining delta first.

### `UBATCH_ALIGNMENT_STILL_FLIPS_FIRST_TOKEN`

The greedy first token differs between W1 and C1 despite aligned physical
boundaries.

The residual difference is stronger than the proposed partial-ubatch mechanism
can explain by itself; a further cache/state/backend discriminator is required.

### `PROBE_NOT_EXERCISED`

Any hard path prediction fails after inference begins, including LCP, rollback
suppression, reuse=512, or prompt-eval=2415.

### `PHYSICAL_PROBE_UNSPENT`

Any required source, patch, model, prompt, build, or request identity fails
before inference begins.

## Boundaries

- RelayLM protected `v1` mutation = 0
- production code/policy mutation = 0
- RC1 action = 0
- #2934 rerun = 0
- #2947 rerun = 0
- upstream submission = 0
- primary dirty checkout mutation = 0
- control-generation replay = 0
- retries/reseeds/fallbacks = 0

This diagnostic tests an alignment strategy. It does not establish that
ubatch-aligned cache reuse is a general production-safe policy.

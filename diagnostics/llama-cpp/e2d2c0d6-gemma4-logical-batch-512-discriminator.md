# Gemma 4 logical-batch-512 cache discriminator

Diagnostic only. This follows the completed synthetic matrix whose primary classification was `NEITHER_INTERVENTION_RESTORES_IDENTITY`.

## Purpose

The previous aligned arm fixed the reuse boundary to `n_ubatch = 512`, but the server still used `n_batch = 2048`. Exact source inspection shows that server prompt processing submits at most `n_batch` tokens per logical `llama_decode()` call, while `llama_batch_allocr::split_equal()` then splits each logical batch into ubatches.

Therefore the previous aligned comparison still differed at the logical decode boundary:

- cold: positions `0..2047` were processed inside the same logical decode, as four 512-token ubatches;
- aligned reuse: after reusing `0..511`, position `512` started a new logical decode.

This discriminator changes only the logical batch width so that `n_batch == n_ubatch == 512`.

Expected chunk geometry:

```text
warm 883  : 512 | 371
cold 2927 : 512 | 512 | 512 | 512 | 512 | 367
reuse512  :       512 | 512 | 512 | 512 | 367
```

Thus both the physical ubatch boundary and the logical decode boundary are aligned after the reused prefix.

## Frozen identities

Keep the same exact source/model/fixture as the completed matrix:

- llama.cpp: `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`
- model SHA256: `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`
- aligned patch SHA256: `cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a`
- aligned binary from the completed matrix if and only if its hash remains `4d02da9c2178f6b0ac67a6a3a0e663b64a08010f7b1a4983e3c0b8cc190ee157`
- corpus SHA256: `4ffd2967dc487d6c4fd4de94e66a017fdf452399105c08093ebbcf0ecfc13936`
- corpus bytes: `113853`
- warm token IDs SHA256: `c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2`
- target token IDs SHA256: `549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e`
- warm length: 883
- target length: 2927
- LCP: 865

Do not regenerate, retokenize, or replace the fixture.

## Runtime

Use the aligned-reuse binary and default compact SWA.

Fixed configuration:

```text
context = 8192
parallel = 1
gpu layers = 999
context shift = disabled
n_batch = 512
n_ubatch = 512
--flash-attn on
--log-verbosity 4
temperature = 0
greedy
1 generated token per measured request
```

Do not use `--swa-full` and do not add `--flash-attn off` in this discriminator.

The only intended physical change relative to the completed aligned arm is `n_batch: 2048 -> 512`.

## Preflight

Before measured generation, retain startup evidence for:

```text
n_ctx = 8192
n_batch = 512
n_ubatch = 512
flash_attn = enabled
health = HTTP 200
```

Also retain exact argv, GPU/device, source revision, binary/model/patch hashes, and port ownership.

A startup or identity failure before L0 does not exercise this discriminator.

## Exactly-once requests

Use fresh server lifetimes as stated below. No retry/replay/reseed/fallback/repair/parameter tuning after L0.

### L0 — warm

Fresh aligned-reuse server, compact SWA:

```text
prompt = frozen warm numeric token array
cache_prompt = true
max generated tokens = 1
temperature = 0
```

### L1 — aligned reuse

Same server:

```text
prompt = frozen target numeric token array
cache_prompt = true
max generated tokens = 1
temperature = 0
top-N logprobs/probabilities enabled
```

Required path:

```text
raw LCP = 865
checkpoint rollback to 366 = absent
effective reuse = 512
prompt eval = 2415
```

### LC — cold

Fresh aligned-reuse server with identical configuration:

```text
prompt = frozen target numeric token array
cache_prompt = false
max generated tokens = 1
temperature = 0
same top-N settings
```

Required path:

```text
reuse = 0
prompt eval = 2927
```

## Required comparison

Compare only `L1` against `LC`.

Retain:

- first generated token ID/text
- API-reported top-N token IDs and logprobs/probabilities
- top1/top2 margin
- exact equality of the reported top-N structure
- per-token deltas on the intersection
- maximum absolute reported delta
- cache_n / n_past
- prompt-eval token count and timing
- complete server logs and raw responses
- exact request SHA256 and prompt-array SHA256

Do not introduce an arbitrary floating-point tolerance.

## Classification

Exactly one:

### `LOGICAL_BATCH_ALIGNMENT_RESTORES_IDENTITY`

`L1 == LC` at the API-reported first-token/top-N level.

Interpretation: the previous `n_ubatch` alignment was insufficient because the logical `llama_decode()` boundary remained different. This supports logical batch / compute-provenance sensitivity. It does not by itself prove a specific CUDA or Flash-Attention kernel mechanism.

### `LOGICAL_BATCH_ALIGNMENT_DOES_NOT_RESTORE_IDENTITY`

`L1 != LC` while the required reuse/cold paths were exercised.

Interpretation: matching both `n_batch` and `n_ubatch` boundaries is insufficient. The next discriminator should directly compare retained prefix KV state/bytes (or a stable per-layer digest) before adding a Flash-Attention-off arm.

### `PROBE_NOT_EXERCISED`

Measured inference began but a required path prediction failed.

### `PHYSICAL_PROBE_UNSPENT`

Only if failure occurs before L0.

## Boundaries

- do not rerun the completed 9-request M/A/F matrix
- do not rerun #2934 or #2947
- protected `v1` mutation = 0
- production/cache-policy mutation = 0
- RC1 action = 0
- primary dirty checkout mutation = 0
- upstream submission = 0

This is a narrow physical-mechanism discriminator, not a production qualification or release PASS.

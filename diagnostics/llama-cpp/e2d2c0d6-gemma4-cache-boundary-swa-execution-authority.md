# Gemma 4 cache-boundary × SWA matrix — execution authority

Diagnostic only. This document is the current execution reconciliation for the synthetic cache-boundary × SWA-cache matrix. It does not change the scientific question, fixture token arrays, model bytes, llama.cpp revision, diagnostic patches, cache semantics, or matrix arms.

Read together with:

- `diagnostics/llama-cpp/e2d2c0d6-gemma4-cache-boundary-swa-matrix-validation.md`
- `diagnostics/llama-cpp/e2d2c0d6-gemma4-cache-boundary-swa-startup-recovery.md`
- `diagnostics/llama-cpp/e2d2c0d6-gemma4-cache-boundary-swa-flash-attn-evidence-recovery.md`
- `diagnostics/llama-cpp/e2d2c0d6-gemma4-cache-boundary-swa-startup-preflight.sh`

Where earlier diagnostic documents conflict with this reconciliation on the two corrected metadata/observability points below, this document wins.

## Current state before the next run

The matrix remains `PHYSICAL_PROBE_UNSPENT`.

No measured request has been sent:

- measured generation count = 0
- semantic inference started = false
- retry/replay/reseed/fallback/repair = 0
- fixture replacement = 0
- parameter tuning = 0

The most recent Arm M startup-only preflight reached model load, GPU residency, listen, and `/health` HTTP 200 but was classified `FLASH_ATTN_EVIDENCE_MISSING` because the required context INFO lines were not captured at `--log-verbosity 3`.

That result is observability evidence only. It is not evidence that Flash Attention was disabled, and it does not exercise the cache/SWA/ubatch hypotheses.

## Corrected frozen fixture metadata

The retained corpus is authoritative by bytes and SHA256. The prior `113854` byte count was an off-by-one metadata error.

Correct retained corpus identity:

- corpus bytes: `113853`
- corpus SHA256: `4ffd2967dc487d6c4fd4de94e66a017fdf452399105c08093ebbcf0ecfc13936`
- tokenized corpus length: `28800`
- warm length: `883`
- target length: `2927`
- LCP: `865`
- target suffix source index `j`: `1024`
- warm token IDs SHA256: `c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2`
- target token IDs SHA256: `549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e`

This correction does not authorize corpus regeneration. Do not replace or retokenize the fixture. A hash mismatch still stops pre-inference as `PHYSICAL_PROBE_UNSPENT`.

## Flash Attention observability correction

Keep Flash Attention physically fixed as:

`--flash-attn on`

Use:

`--log-verbosity 4`

for the revised startup preflight and for every measured server lifetime in all M/A/F arms and paired cold controls.

The verbosity change is observability-only. It must not be treated as inference parameter tuning.

Required non-generative Arm M evidence before M0:

- `/health` HTTP 200
- intended RTX 3060/CUDA backend/device loaded
- `n_ctx = 8192`
- `n_batch = 2048`
- `n_ubatch = 512`
- `flash_attn = enabled`

The exact target source maps forced `--flash-attn on` to enabled, non-auto context state and logs these context values at INFO level. For the frozen Gemma 4 graph path, `flash_attn = enabled` is sufficient pre-inference evidence that graph construction is configured for the Flash Attention branch when attention is evaluated.

Do not require direct CUDA Flash Attention kernel-launch evidence before M0; direct dispatch requires graph execution and belongs to measured evidence.

## Revised preflight invocation

For Arm M, with no `--swa-full`:

```bash
bash diagnostics/llama-cpp/e2d2c0d6-gemma4-cache-boundary-swa-startup-preflight.sh \
  "$OUT_DIR" \
  "$MAX_REUSE_LLAMA_SERVER" \
  "$MODEL_GGUF" \
  18101 \
  --log-verbosity 4
```

If 18101 is occupied before launch, selecting one free loopback port is mechanical and allowed. Record the chosen port.

If required startup evidence is still absent, stop without M0 and retain `PHYSICAL_PROBE_UNSPENT`. Do not increase verbosity again, change FA mode, rebuild fixture, alter batch geometry, or tune parameters in that run.

## Spend transition and continuation

If the revised M preflight reaches `READY_NON_GENERATIVE`, do not terminate the task merely for another authorization boundary.

Terminate the preflight server, then launch a fresh measured Arm M server with the same frozen physical configuration including `--flash-attn on` and `--log-verbosity 4`.

Send M0 exactly once.

M0 is the first measured one-token generation and is the exact transition from `PHYSICAL_PROBE_UNSPENT` to spent/exercised scientific probe state.

After M0:

- retry = 0
- replay = 0
- reseed = 0
- fallback = 0
- repair = 0
- fixture replacement = 0
- parameter tuning = 0

Then execute the matrix exactly once according to the primary matrix validation:

1. M0 -> M1 on the same maximum-reuse compact-SWA server.
2. MC on a fresh paired cold maximum-reuse compact-SWA server.
3. A0 -> A1 on a fresh aligned-reuse compact-SWA server.
4. AC on a fresh paired cold aligned-reuse compact-SWA server.
5. F0 -> F1 on a fresh maximum-reuse server with `--swa-full`.
6. FC on a fresh paired cold maximum-reuse server with `--swa-full`.

Every server lifetime uses:

- exact llama.cpp `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`
- context 8192
- slots 1
- GPU layers 999
- no context shift
- batch 2048
- ubatch 512
- `--flash-attn on`
- `--log-verbosity 4`
- greedy / temperature zero
- exactly one generated token for each measured request
- frozen numeric prompt arrays

Do not add a `--flash-attn off` discriminator to this spend.

## Required hard paths

Arm M target M1:

- raw LCP = 865
- checkpoint rollback to 366 absent
- effective reuse/cache_n/n_past = 865
- prompt eval = 2062

Arm A target A1:

- raw LCP = 865
- checkpoint rollback to 366 absent
- effective reuse/cache_n/n_past = 512
- prompt eval = 2415

Arm F target F1:

- raw LCP = 865
- checkpoint rollback to 366 absent
- effective reuse/cache_n/n_past = 865
- prompt eval = 2062

Paired cold controls MC/AC/FC:

- reuse = 0
- prompt eval = 2927

If a hard path is not exercised after M0, do not repair or rerun. Classify according to the matrix validation as exercised/partial (`PROBE_NOT_EXERCISED` where applicable), never `PHYSICAL_PROBE_UNSPENT` after M0.

## Interpretation boundary

Compare only paired conditions:

- M1 vs MC
- A1 vs AC
- F1 vs FC

Keep first-token equality separate from API-reported top-N/logprob equality and from non-zero numerical deltas.

Do not introduce an arbitrary floating-point tolerance.

Do not assume Online Softmax is the unique cause. The tested mechanism remains broader physical compute provenance under fixed Flash Attention: ubatch/tile shape, online normalization/reduction ordering, backend kernel behavior, and cached hidden/KV trajectory.

## Repository boundaries

- protected `v1` mutation = 0
- production code/cache policy mutation = 0
- RC1 action = 0
- #2934 rerun = 0
- #2947 rerun = 0
- historical prompt reconstruction = 0
- primary dirty checkout mutation = 0
- upstream submission = 0

This execution is a diagnostic physical mechanism probe, not production qualification.

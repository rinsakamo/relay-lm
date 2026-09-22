# Gemma4 KV segmentation source-causal narrowing

Status: `SOURCE_CAUSAL_MODEL_NARROWED_NUMERIC_MAGNITUDE_PENDING`

This document is diagnostic-branch authority only. It does not authorize a new GPU run, scientific campaign execution, FA-OFF, protected `v1` mutation, or upstream submission.

## Frozen subject

- llama.cpp: `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d` / tree `6d39fd93dc91fc0a4bc86dffe9782d4f26318004`
- model SHA256: `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`
- runtime of interest: `n_batch=512`, `n_ubatch=512`, Flash Attention ON, `ctx=8192`, base KV 8192, SWA KV 1536

Measured facts remain owned by the existing measured authorities: prior fixture-v2 gave `W == W2`, `W == R`, `W != C2927`; segmentation control later gave `W == W2 == C883` across all 96 canonical K/V payloads.

## 1. Segmentation reaches the model

Frozen `tools/server/server-context.cpp` implements trailing checkpoint offsets `{4 + n_ubatch, 4}` and calls `llama_decode()` on the resulting batch view. With `n_batch=n_ubatch=512`, the 883-token prompt is physically decoded as `371 -> 508 -> 4`, while the 2927-token prompt fills a normal first 512-token batch. The confounder therefore reaches actual `llama_decode()` input shape.

Frozen `src/llama-kv-cache-iswa.cpp` does not erase this distinction: relevant batches are already <= 512, and the unified iSWA allocator preserves those widths as ubatches before preparing base and SWA cache contexts.

## 2. Graph topology is width-sensitive

`src/llama-context.cpp` builds graph parameters from each ubatch. Graph reuse checks include `ubatch.n_tokens`, `n_seq_tokens`, `n_seqs`, and `n_seqs_unq`; position-input reuse is also extent-sensitive. Thus 371, 508, and 512 are distinct graph/backend scheduling surfaces. There is no separate checkpoint semantic flag passed into Gemma4 mathematics.

Logical positions themselves remain explicit: the server assigns positions, graph input copies ubatch positions, and the diagnostic dump validates logical positions 0..511.

## 3. Simple physical-layout artifact is strongly disfavored

The logical-prefix dump synchronizes the backend, enumerates live KV cells, sorts them by logical position, validates contiguous requested positions, and then reads each physical row into canonical logical order. Its manifest records the actual GGML storage type and row size. Therefore different physical cell ordering is not a sufficient explanation for prior byte divergence.

Stored representation versus decoded numerical value remains unresolved until raw payloads are numerically interpreted using the manifest dtype.

## 4. Earliest mismatch is before Flash Attention output

The prior first differing payload was `swa.layer-0.K.bin`; the cache record uses the original transformer layer id, so this is transformer layer 0.

Frozen `src/models/gemma4.cpp` computes layer-0 K/V through input embedding/scale, attention RMS normalization, QKV or K/V projection, K/V normalization, and K RoPE, then the graph writes K/V to cache. Only after those cache writes does the attention path invoke `ggml_flash_attn_ext(...)` when enabled.

Therefore layer-0 Flash Attention output cannot originate the observed layer-0 stored-K difference. Flash Attention can still propagate or amplify a pre-existing numerical difference into later layers.

V does not pass through K RoPE. Since the prior W/C2927 comparison reported all 96 K/V payloads different, a K-only RoPE explanation is insufficient for the whole observation.

## 5. Projection is the highest-value early numerical candidate

CUDA RMS normalization reduces within each token row; changing token count primarily changes the row/block count rather than the hidden-dimension reduction domain for a fixed row. Cache `SET_ROWS` is likewise row/index oriented. These facts weaken those operations as the primary cross-token shape-sensitive origin.

The dense projection path is different: Gemma4 projection matrix N is the current token count.

For supported quantized weights on Ampere, frozen CUDA can use MMQ for both widths. The important shape dependence is inside MMQ itself:

1. `mul_mat_q_switch_J()` chooses tile width J from `args.ncols_max`.
2. `launch_mul_mat_q()` computes `ntx = ceil(ncols_max / J)`.
3. Frozen Ampere Q4_K MMQ configurations use `stream_k=true` for supported J configurations.
4. The stream-K kernel partitions a continuous i/j/k work space whose total contains `ntx * nty * blocks_per_ne00`.
5. Partition crossings write partial sums to a fixup buffer; `mul_mat_q_stream_k_fixup` later accumulates them with floating-point `+=`.

Consequently, changing decode width can change K-dimension partition/fixup grouping and floating accumulation order even when the same broad MMQ kernel family is used. This is a concrete frozen-source mechanism for byte-level drift.

This is not yet proof that the measured layer-0 projection used this exact MMQ path. The committed measured evidence does not preserve the layer-0 projection tensor type or its actual MMQ/cuBLAS launch identity. The model-level `Q4_K_M` label is not substituted for tensor-level evidence. If the projection tensor is non-quantized, the large-width CUDA path instead reaches cuBLAS, where matrix N still differs but the runtime algorithm was not captured.

## Hypothesis status

| Hypothesis | Status | Reason |
| --- | --- | --- |
| H1 decode-width-dependent projection accumulation | strongest live candidate, not proven | exact MMQ stream-K mechanism exists; cuBLAS also sees different N; runtime tensor/launch identity absent |
| H2 hidden ubatch repartition | supported only as part of segmentation | iSWA preserves relevant <=512 widths; no hidden normalization to one common width found |
| H3 checkpoint-specific mathematical state | weakened | checkpoint changes decode boundaries, but no checkpoint semantic flag enters Gemma4 graph |
| H4 physical KV slot/order artifact | simple form effectively falsified | dump canonicalizes cells by logical position |
| H5 wrong logical positions / RoPE | strongly contradicted as general explanation | positions copied explicitly; V has no K RoPE; all K/V files differed |
| H6 stored-representation difference | unresolved | byte evidence alone does not give numerical magnitude |
| H7 cache `SET_ROWS` as primary cause | weak | row/index-oriented write; may still convert storage type |
| H8 attention path explains later layers | plausible propagation only | cannot originate layer-0 K/V because cache write precedes layer-0 attention output |

## Current classification

`D — CURRENT_EVIDENCE_CANNOT_YET_DISTINGUISH_NUMERICAL_DRIFT_FROM_MATERIAL_VALUE_DIFFERENCE`

D is now narrow. A simple B-style row-order/layout artifact is strongly disfavored. A C-style future-suffix or wrong-position semantic effect is contradicted by the segmentation control and position path. A has a concrete source mechanism but is not promoted to measured fact without numerical magnitude or equivalent tensor/backend identity evidence.

## Single next discriminator

First choice is zero-GPU and consumes no new transaction: if the already-consumed W and C2927 P512 raw dump directories still exist, decode them using the manifest-recorded dtype and report byte-difference density, differing logical positions, max/mean absolute error, relative error, and ULP-like distance for supported scalar storage types, split by base/SWA, K/V, and layer.

Tiny widespread finite drift would strongly support A. Equal decoded numerical values with different stored representation would support B. Large structured value differences beginning at a computation boundary would keep C live and identify the next instrumentation target.

If those raw dumps no longer exist, do not replay the historical probe. Any future physical discriminator requires separate authority and should keep Flash Attention ON while capturing layer-0 projection tensor type/backend launch identity together with canonical K/V under two decode widths.

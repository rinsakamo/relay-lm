# Gemma4 layer-0 projection-origin discriminator

Status: `LAYER0_PROJECTION_ORIGIN_DISCRIMINATOR_DESIGNED_NOT_AUTHORIZED`

This document is diagnostic-branch authority only. It designs the smallest remaining physical discriminator after the consumed logical-prefix KV evidence, zero-GPU numerical post-hoc analysis, source causal narrowing, and static historical MMQ qualification. It does **not** authorize a GPU run, model load, server start, HTTP request, historical replay, FA-OFF arm, scientific campaign execution, protected `v1` mutation, or upstream submission.

## Frozen subject and established evidence

Frozen llama.cpp subject:

- HEAD: `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`
- tree: `6d39fd93dc91fc0a4bc86dffe9782d4f26318004`

Frozen model:

- Gemma 4 12B IT Q4_K_M
- SHA256: `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`

Runtime identity to preserve:

- `ctx=8192`
- `parallel=1`
- `n_batch=512`
- `n_ubatch=512`
- `gpu-layers=999`
- context shift disabled
- Flash Attention ON
- compact SWA
- cache K/V F16

Existing consumed raw evidence remains the authority for the historical observation. No historical runner is to be replayed.

Established facts:

- `W == W2`
- `W == R`
- `W != C2927`
- segmentation control: `W == W2 == C883`
- all 96 W/C canonical KV payload files differ
- W/C numerical difference is material overall
- layer-0 SWA seed is tiny: K max 2 ULP / V max 3 ULP in stored F16
- layer 1 amplifies the difference strongly
- canonical logical positions and physical KV cell mapping match
- layer-0 Q/K/V projections are separate
- layer-0 K weight = Q4_K; V weight = Q6_K
- historical CUDA build/device evidence statically qualifies MMQ, J=128, and stream-K for these projection shapes
- activation quantization is row-local with respect to token width
- the actual measured causal origin is still unproven

Physical segmentation relevant to logical positions 0..511:

```text
warm W:
  positions   0..370 -> width 371, physical columns   0..370
  positions 371..511 -> width 508, physical columns   0..140

cold C:
  positions   0..511 -> width 512, physical columns   0..511
```

The remaining causal question is therefore:

> Were shared-token layer-0 activations already different before the separate K/V projection matmuls, or do the first observable numerical differences appear at those projection outputs?

## Minimal observation surface

Observe only three already-existing graph tensors for transformer layer 0:

1. `attn_norm-0`
   - output of layer-0 attention RMS normalization;
   - direct shared activation input to Q/K/V projection;
   - pre-projection observation.

2. `Kcur-0`
   - separate K projection result immediately after `build_lora_mm(layer.wk, cur, ...)`;
   - before reshape, K RMS norm, RoPE, and KV cache write.

3. `Vcur-0`
   - separate V projection result immediately after `build_lora_mm(layer.wv, cur, ...)`;
   - before reshape, V RMS norm, and KV cache write.

Do not use post-norm or post-RoPE tensors to decide the projection boundary.

The observation must preserve the exact F32 rows, not only F16 cache values.

## Non-perturbing instrumentation design

Do not use `llama_context_params.cb_eval` for the primary apparatus. At the frozen scheduler revision an eval callback divides backend graph execution at requested nodes and synchronizes at observation boundaries. That is useful for debugging but would itself alter graph execution grouping around the operation being diagnosed.

Instead:

1. During graph construction, when and only when the diagnostic environment is enabled, mark `attn_norm-0`, `Kcur-0`, and `Vcur-0` with `ggml_set_output()`.
2. This preserves their buffers from allocator reuse without inserting arithmetic graph nodes.
3. Execute the graph normally with no eval callback.
4. Only **after the entire ubatch graph compute returns**, synchronize the scheduler once and copy the preserved tensor rows to host.
5. Record the exact `llama_ubatch.pos[]` logical position for every dumped row.

The output flag changes tensor lifetime/allocation and can therefore not be assumed non-perturbing a priori. The physical result is admissible only if the final canonical KV payloads reproduce the historical raw evidence exactly; see the integrity gate below.

## Exact ubatches to retain

Ignore every graph except these exact position/width tuples:

```text
W:
  n_tokens=371, positions=0..370
  n_tokens=508, positions=371..878

C:
  n_tokens=512, positions=0..511
```

The diagnostic must validate `n_pos == 1`, one sequence, consecutive positions, and exact tensor geometry before writing.

The warm width-508 dump contains positions beyond the comparison prefix because they are part of the real physical ubatch. They must not be removed before compute. Post-hoc comparison uses only logical positions 371..511 from this dump.

No artificial padding, slicing before projection, alternate batching, or synthetic matmul is allowed.

## Canonical dump format

For each selected ubatch, create a fresh non-existing directory named from the server label, exact logical range, and width.

Retain:

- `positions.tsv`: physical column -> logical position;
- `manifest.tsv`: tensor name, GGML type, dimensions, strides, canonical row bytes, row count;
- `attn_norm-0.bin`;
- `Kcur-0.bin`;
- `Vcur-0.bin`.

Each payload is canonicalized as one logical-token row after another. For a tensor shaped `[features, n_tokens]`, copy exactly `ggml_row_size(type, ne[0])` bytes from each physical token column using its actual stride. Do not serialize padding bytes.

Require all three observed tensors to be F32. Any other type is terminal apparatus failure; do not add an ad-hoc decoder.

Refuse to overwrite an existing dump directory or payload.

## Physical request surface

The eventual authorized transaction needs only two measured requests.

### W

Fresh server lifetime:

- exact frozen warm request;
- `cache_prompt=true`;
- one generated token;
- temperature 0.

Required graph observations:

- W 0..370 / width 371;
- W 371..878 / width 508.

Required existing canonical KV observation:

- `W-P512` for logical positions 0..511.

### C

Second fresh server lifetime with identical configuration:

- exact frozen cold target request;
- `cache_prompt=false`;
- one generated token;
- temperature 0.

Required graph observation:

- C 0..511 / width 512.

Required existing canonical KV observation:

- `C-P512` for logical positions 0..511.

No reuse request, W2 request, FA-OFF arm, or additional prompt is part of this discriminator.

## Instrumentation-integrity gate

Before interpreting pre/post projection tensors, compare the new instrumented canonical KV dumps byte-for-byte against the surviving consumed historical raw evidence:

```text
new W-P512 == historical WR-P512
new C-P512 == historical C-P512
```

Comparison includes:

- cells logical-position mapping;
- manifests;
- all 96 canonical K/V payload files.

If either comparison differs, classify:

`INSTRUMENTATION_PERTURBED_SUBJECT`

and stop. Do not use the projection dumps for a causal claim and do not retry with modified instrumentation in the same transaction.

This gate is what allows a buffer-lifetime diagnostic to be interpreted against the historical subject rather than silently defining a new numerical subject.

## Canonical logical-position comparison

Build a logical-position map from the F32 dumps.

For W positions 0..511:

```text
0..370   <- W width-371 columns 0..370
371..511 <- W width-508 columns 0..140
```

For C positions 0..511:

```text
0..511 <- C width-512 columns 0..511
```

For each of `attn_norm-0`, `Kcur-0`, and `Vcur-0`, compare exact F32 bytes and report:

- differing logical rows;
- differing elements;
- first/last differing logical position;
- max absolute error;
- mean absolute error;
- max relative error;
- exact F32 bit-distance / ULP-like distance;
- segment A (0..370) and segment B (371..511) separately.

No arbitrary tolerance participates in the primary classification.

## Primary classification

After and only after the instrumentation-integrity gate passes:

### `LAYER0_PROJECTION_NUMERICAL_ORIGIN_OBSERVED`

Required:

- `attn_norm-0(W) == attn_norm-0(C)` bit-for-bit for all logical positions 0..511; and
- `Kcur-0` and/or `Vcur-0` differs for at least one shared logical position.

Interpretation:

The earliest observed difference across this boundary appears in the layer-0 projection surface. Combined with the already-qualified historical dispatcher, this strongly localizes the seed to projection execution, but does not distinguish MMQ activation representation, MMA accumulation, stream-K partition/fixup, or another implementation detail inside that projection path.

Do not rename this to `STREAM_K_CAUSAL_ORIGIN_PROVEN`.

### `LAYER0_PREPROJECTION_DIFFERENCE_OBSERVED`

`attn_norm-0` already differs for at least one shared logical position.

Interpretation:

The causal origin is earlier than the K/V projections. Do not attribute the seed to MMQ projection.

### `LAYER0_PROJECTION_OUTPUT_IDENTICAL_ORIGIN_LATER`

`attn_norm-0`, `Kcur-0`, and `Vcur-0` are all bit-identical over positions 0..511 while the integrity-gated final KV state still reproduces the historical W/C difference.

Interpretation:

The earliest origin lies after the raw projection output and before/in cache-visible K/V formation. Continue only with a separately designed later-boundary discriminator.

### `LAYER0_PROJECTION_PARTIAL_OR_AMBIGUOUS`

Use only if the observations are complete and integrity-valid but do not fit the cases above.

## Fail-closed terminal conditions

A future physical wrapper must stop without causal classification if any of the following occurs:

- frozen source/model/fixture identity mismatch;
- required historical raw evidence absent;
- preflight startup identity mismatch;
- diagnostic patch/build identity mismatch;
- an expected ubatch observation is missing or duplicated;
- positions are non-contiguous or unexpected;
- observed tensor type/shape differs from contract;
- canonical KV integrity gate fails;
- request path/timing counters do not match the intended warm/cold path;
- any output path already exists;
- any retry/replay would be required.

Before the first W POST, failures are unspent. At or after the first W POST, the physical transaction is consumed. No retry, repair, alternate patch, reseed, or replay is authorized by a failed transaction.

## Separation from scientific spend

Must remain zero:

- `scientific --execute`;
- #2965 campaign invocation;
- campaign queue/receipt/lease/spend mutation;
- #2964 mutation;
- protected `v1` mutation;
- `main`, `v2`, or `relay-theory` mutation;
- production/cache-policy mutation;
- primary dirty checkout mutation;
- FA-OFF;
- upstream submission.

## Next repository step

Materialize and statically self-test:

1. a diagnostic-only frozen-source patch implementing output preservation + post-graph F32 dump;
2. a zero-GPU post-hoc comparator implementing the integrity gate and logical-position reconstruction;
3. a build/preflight wrapper proving no generation occurs during apparatus qualification.

Only after those deterministic surfaces pass should a **separate execution authority** pin their exact hashes and authorize one exactly-once W/C transaction.

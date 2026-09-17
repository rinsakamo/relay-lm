# Gemma 4 retained-prefix KV provenance probe

Diagnostic only. This follows the completed logical-batch discriminator whose primary classification was:

`LOGICAL_BATCH_ALIGNMENT_DOES_NOT_RESTORE_IDENTITY`

Observed terminal result from that discriminator:

- L0: cache_n=0, prompt eval=883, first token 607 (" with")
- L1: cache_n=512, prompt eval=2415, first token 1343 (" through")
- LC: cache_n=0, prompt eval=2927, first token 1343 (" through")
- L1 vs LC top-N exact identity: false
- intersection: 19/20
- L1-only token: 874
- LC-only token: 236779
- top1/top2 margin: L1 1.4165006876, LC 1.8059202731
- max |delta logprob|: 1.3422279358 at token 2195
- top1 delta logprob: -0.2859993279

The first token happened to agree, but API-visible numerical identity did not.

## Goal

Determine whether the retained prefix KV values themselves already differ, or whether identical retained KV state leads to divergent continuation.

This probe keeps Flash Attention ON. Flash Attention OFF is not a production-target discriminator for this line because the intended practical configuration requires Flash Attention.

## Frozen identities

Keep the same source/model/fixture and aligned-reuse semantics:

- llama.cpp: `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`
- model SHA256: `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`
- aligned diagnostic patch semantics: reuse exactly 512 for this fixture
- corpus SHA256: `4ffd2967dc487d6c4fd4de94e66a017fdf452399105c08093ebbcf0ecfc13936`
- corpus bytes: `113853`
- warm token IDs SHA256: `c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2`
- target token IDs SHA256: `549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e`
- warm length: 883
- target length: 2927
- LCP: 865

Do not regenerate, retokenize, or replace the fixture.

## Runtime

Keep:

```text
context = 8192
parallel = 1
gpu layers = 999
context shift = disabled
n_batch = 512
n_ubatch = 512
--flash-attn on
--log-verbosity 4
compact SWA
temperature = 0
greedy
```

Do not add `--flash-attn off`.

## Instrumentation rule

Instrumentation must be observational only.

Do not insert hashing or comparison nodes into the compute graph.

After the relevant `llama_decode()` has completed, synchronize the context and read KV storage through backend tensor reads.

Dump raw bytes; compute SHA256 outside llama.cpp.

For each dump point:

- inspect only logical positions 0..511 for the active sequence;
- order rows by logical position, not physical cell index;
- dump base/non-SWA and SWA caches separately;
- dump every participating layer separately;
- dump K and V separately;
- also retain a cell/layout metadata file containing at least logical position -> physical cell index and cache head/state useful for interpretation;
- reject missing, duplicate, or non-contiguous logical positions instead of silently hashing a partial prefix.

With Flash Attention enabled on this target, the V cache is expected to be non-transposed. The instrumentation must fail closed if the physical layout does not match the dump implementation's assumptions.

## Four observation points

### W512

Warm/reuse server, during L0.

Immediately after the first 512-token logical decode has successfully completed and the context is synchronized, before positions >=512 are decoded.

This captures the KV values originally generated for positions 0..511 in the warm request.

Suggested dump tag:

`WR-P512`

### R512

Same warm/reuse server, at the beginning of L1.

After aligned reuse has selected 512 and after the suffix has been removed from memory, but before any new target token at position >=512 is decoded.

This captures the actually retained prefix after reuse/truncation.

Suggested dump tag:

`WR-R512`

### W2-512 — fresh reproducibility control

A second fresh server, using the same instrumented binary and exact runtime as W512.

Run the same warm request once. Capture the first 512-token prefix exactly as W512, under tag:

`WR2-P512`

This is not a retry. It is a predeclared independent fresh-run reproducibility control.

Interpret W512 vs C512 only if W512 == W2-512 at the KV-payload level.

### C512

Fresh cold server, during LC.

Immediately after the first 512-token logical decode has successfully completed and the context is synchronized, before positions >=512 are decoded.

Suggested dump tag:

`C-P512`

## Measured requests

Use exactly:

1. L0 warm, cache_prompt=true
2. L1 target, cache_prompt=true, effective reuse=512
3. L0R warm on a second fresh server, cache_prompt=true — reproducibility control
4. LC target on a third fresh server, cache_prompt=false

Each once. L0R is a distinct predeclared control, not a retry.

Retain the API response and logs again because the instrumented binary is a distinct physical artifact. Do not assume the previous L1/LC numerical result automatically transfers to the instrumented binary.

No retry/replay/reseed/fallback/repair/parameter tuning after L0.

## Digest comparison

Use:

`diagnostics/llama-cpp/e2d2c0d6-gemma4-kv-prefix-digest-compare.py`

against a root containing:

- `WR-P512/`
- `WR-R512/`
- `WR2-P512/`
- `C-P512/`

The comparator hashes all per-layer K/V binary dumps independently.

Layout metadata hashes are reported separately and must not be conflated with KV value equality.

## Primary KV classifications

Exactly one KV-state classification:

### PREFIX_DUMP_NOT_REPRODUCIBLE

W512 != W2-512 in one or more per-layer K/V byte streams.

Interpretation:

The identical fresh warm-prefix observation is not byte-reproducible across independent server lifetimes. Do not attribute W512 vs C512 to cache/request-shape causality. Preserve the mismatch localization and investigate backend/run-to-run determinism while keeping Flash Attention ON.

### PREFIX_KV_GENERATION_DIFFERS

W512 == W2-512, but W512 != C512 in one or more per-layer K/V byte streams.

Interpretation:

The same logical prefix positions 0..511 are already encoded differently when computed in the two request histories, even after matching n_batch=n_ubatch=512. The next investigation should identify the earliest differing layer/tensor and then trace the compute provenance producing that K/V row difference.

### RETAINED_PREFIX_KV_MUTATED_BY_REUSE

W512 == W2-512 == C512, but R512 != W512.

Interpretation:

The prefix is generated reproducibly, but cache-reuse/truncation mutates retained K/V values. Focus on seq_rm/reuse/cache maintenance rather than attention continuation.

### PREFIX_KV_IDENTICAL_THROUGH_REUSE

W512 == W2-512 == R512 == C512 for all dumped per-layer K/V bytes.

Interpretation:

Retained prefix K/V itself is byte-identical. If instrumented L1 vs LC still differs, the causal region is downstream of retained prefix storage: continuation graph inputs/masks/indexing/kernel execution/scheduler state or another non-KV state.

### PROBE_NOT_EXERCISED

A required dump point, exact reuse path, or byte-comparison precondition was not reached.

## Secondary localization

If KV differs, report:

- first cache class: base or SWA
- first model layer with a mismatch
- K or V
- count of mismatching per-layer files
- whether cell/layout metadata also differs

Do not infer a specific Flash-Attention kernel mechanism from a KV mismatch alone.

## Boundaries

- Flash Attention remains ON throughout.
- Do not run an FA-OFF arm.
- Do not rerun the completed 9-request M/A/F matrix.
- Do not rerun #2934 or #2947.
- protected v1 mutation = 0
- production/cache-policy mutation = 0
- RC1 action = 0
- primary dirty checkout mutation = 0
- upstream submission = 0

This is a physical-mechanism diagnostic, not production qualification or release PASS.

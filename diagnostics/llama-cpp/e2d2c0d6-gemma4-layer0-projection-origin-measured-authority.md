# Gemma4 layer-0 projection-origin exactly-once measured authority

Diagnostic only. This authority is separate from the protected `v1` scientific campaign and from all previously consumed KV probes.

## Status

`TERMINAL_CONSUMED_LAYER0_PREPROJECTION_DIFFERENCE_OBSERVED`

Authority generation:

`layer0-projection-origin-20260922-a5d767da`

This authority permits **at most one** invocation of the dedicated execute-once wrapper described below.

It authorizes exactly two measured completion requests:

1. W = the committed fixture-v2 `L0.request.json` on a fresh server.
2. C = the committed fixture-v2 `LC.request.json` on a second fresh server.

It does **not** authorize L1, L0R, WR2, cache-reuse measurement, FA-OFF, historical runner replay, scientific campaign execution, or any third measured request.

No measured execution has occurred under this authority at authoring time.

## Fresh repository authority at authoring

Code head immediately before this authority commit:

```text
diagnostic head =
97939c9df57fbb4d4a0c24f4f7202222b189eb12

diagnostic tree =
aa4ba93dc71643a18ef71d29a191d97f0fb21c99

v1 head =
671893aafcb353395e8f4dcb3849c2a678e2930e

v1 tree =
eecc3e5d96480eec8f1ffba60bc1561b89e46076

open PRs targeting v1 = 0
open PRs for diagnostic branch = 0
ruleset 20931403 = active
```

Current repository authority always overrides this snapshot. Before execution, reacquire current remote diagnostic/v1 authority and stop if a newer conflicting measured authority or terminal exists.

## Exact code surface

Required Git blob identities:

```text
measured runner =
02713c8950977bb8b25f210ea1ef8d0b71ae1bf0

measured runner selftest =
984ab9aae269eff22c9324ab9d7d0e47921ba563

execute-once wrapper =
3da540e932008895856cfe774b1414e8eed0b94b

execute-once wrapper selftest =
c746251999460a2351b016639588fba2385acff1

posthoc analyzer =
8d0f04af746e6c12f3f22c38e85fced905c3c575

posthoc selftest =
dca4a90089f50c1a6d5aaa395a7894e13679e5d5

canonical KV directory digest =
12cf1d016ab0d9c10c8e7f498f4930a9a2edbbb0

canonical KV directory digest selftest =
dd070fd8ecaf4c72e3226144420b05a33ad4ae30

canonical local-GPU resource guard =
473e135a8af30e5d27a1578db4b32bf4b995cb2b

resource-guard selftest =
ab8494835e7211df0fcd12addbf4aaf95fb403bd
```

The measured runner must never be invoked manually. The only authorized measured entrypoint is:

`diagnostics/llama-cpp/e2d2c0d6-gemma4-layer0-projection-origin-execute-once.py`

## Frozen source/model subject

llama.cpp:

```text
HEAD =
e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d

tree =
6d39fd93dc91fc0a4bc86dffe9782d4f26318004
```

Model SHA256:

`c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`

## Qualified premeasured apparatus identity

The successful preparation classified:

`LAYER0_PROJECTION_ORIGIN_PREMEASURED_READY`

The execution wrapper may accept a premeasured root at any path, but it must revalidate the following exact identity before any measured server starts.

Runtime closure:

```text
llama-server SHA256 =
a5d767da8006aaf0537594ae308fc427cdb92154f48c5a3a325be3908352c5bb

libllama-server-impl.so SHA256 =
2a693007d6c344c6248478d6008c5055b76d2c885012aff133bdfa1b4be6dc71

libllama.so SHA256 =
533a1a35c686c8375b077fb2eec3b8e293a6ef54d1a1f3643989542ab4e3b46e
```

Patch/build identity:

```text
combined applied.patch SHA256 =
5073a690590bf22e6b437425f1f6210b2dd239b549eaeb7509fad22deb43522d

aligned-reuse patch SHA256 =
cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a

logical-prefix patch SHA256 =
d62810fdc645cbb011c52047e9ba9227b1d6c29fafc0bac0e7cf659f6104e4c8

projection-origin patch SHA256 =
61af8dce39b0dceb0ce12b7fef8014dcb8f94ba7564955783c5ff76c9d211674
```

Successful original evidence hashes:

```text
binary-preflight JSON SHA256 =
0e573f7fad469f4483b3a16f73f3ad03aca7078afccba818f0ef4fa000c1b06c

build-stage terminal.json SHA256 =
05a6df11a3063d6f94cfa8d28a59afb549a72bdf58c18dd57186a0ac0f7c7a49

qualification-stage terminal.json SHA256 =
345399965614aa6b44e1c4b79f6fd70163c514f6ec6bacea5c96173890f9faea

top-level terminal.json SHA256 =
17da154f0648a89b2cea4a4740919da7dc87926c77a141efe14add02dafcbfd9
```

Those whole-file evidence hashes document the original successful root. Admission is identity-based, not path-based: if a path changes or an equivalent root is reconstructed, the runner must still independently verify the source/model/runtime/patch/startup identity below.

Startup identity:

```text
canonical argv SHA256 =
031c7df7867ea521e2df37fa3a0a97b60a7eb2303e7c54fee5c92b55aa8b6dea

n_seq_max = 1
n_ctx = 8192
n_batch = 512
n_ubatch = 512
Flash Attention = enabled
base KV = 8192
compact SWA KV = 1536
plain/probe = READY_NON_GENERATIVE
```

Premeasured counters must remain:

```text
generated_requests = 0
measured_l0_submitted = false
measured_attempt_consumed = false
```

## Historical integrity reference

Historical canonical KV root must contain directories equivalent to the previously consumed fixture-v2 evidence:

```text
WR-P512 canonical directory SHA256 =
492663002bf7f1c37d7df2e346d7eff38ff21d6225040c21e07f8fa4984b7ce6

C-P512 canonical directory SHA256 =
c7a5bfc7ea2176fd26b32ee0d45e644ca8737facd11f00647850001d45f373d2
```

Directory digest algorithm:

`sha256(sorted(relative_path\0size\0file_sha256\n))`

Each canonical directory must prove:

- 100 total files;
- 96 K/V payload files;
- base and SWA cells each contain exactly 512 logical rows;
- positions exactly 0..511;
- base KV = 8192;
- SWA KV = 1536;
- `v_trans=0`;
- complete K/V pair set and exact payload sizes.

The historical directories are read-only. They must never be regenerated or mutated by this authority.

## Exact request identity

W request:

```text
fixture path =
diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2/L0.request.json

Git blob =
a4d7d31b268cb173a93ff32c87184dc9a16998e4

SHA256 =
d777877485b3307d8ee76e6b6df783d00b4302bb700c405ac5cbf2f6d7344f5d

prompt length = 883
cache_prompt = true
n_predict = 1
temperature = 0
stream = false
```

C request:

```text
fixture path =
diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2/LC.request.json

Git blob =
5534a9dcb9da289b0448a139b77dcf94287fdfd7

SHA256 =
63afb2a44ea12f14377ba52348616a0bd8ac3ebdd65d81d1a3ede1c4c2c64043

prompt length = 2927
cache_prompt = false
n_predict = 1
temperature = 0
stream = false
```

No request-file override is authorized.

## Physical observation contract

W fresh server must set:

```text
LLAMA_KV_PROBE_LABEL=W
LLAMA_PROJECTION_ORIGIN_PROBE_LABEL=W
```

Required W outputs:

- `kv/W-P512`
- `projection/W-p0-370-w371`
- `projection/W-p371-878-w508`

C fresh server must set:

```text
LLAMA_KV_PROBE_LABEL=C
LLAMA_PROJECTION_ORIGIN_PROBE_LABEL=C
```

Required C outputs:

- `kv/C-P512`
- `projection/C-p0-511-w512`

Both measured servers use exactly:

```text
ctx = 8192
parallel = 1
gpu layers = 999
context shift = disabled
n_batch = 512
n_ubatch = 512
Flash Attention = ON
log verbosity = 4
compact SWA
```

Expected request accounting:

```text
W: cache_n=0, prompt_n=883, predicted_n=1
C: cache_n=0, prompt_n=2927, predicted_n=1
```

## Mandatory static gate

Immediately before invoking the execute-once wrapper:

1. reacquire current diagnostic HEAD/tree;
2. reacquire current v1 HEAD/tree;
3. check open PRs and ruleset 20931403;
4. confirm no newer conflicting measured authority or terminal exists;
5. verify all required Git blob identities above;
6. Python-compile:
   - measured runner;
   - measured runner selftest;
   - execute-once wrapper;
   - execute-once wrapper selftest;
   - posthoc analyzer/selftest;
   - canonical KV digest/selftest;
   - resource guard/selftest;
7. run selftests and require:
   - `LAYER0_PROJECTION_ORIGIN_MEASURED_RUNNER_SELFTEST_PASS`
   - `LAYER0_PROJECTION_ORIGIN_EXECUTE_ONCE_SELFTEST_PASS`
   - `LAYER0_PROJECTION_ORIGIN_POSTHOC_SELFTEST_PASS`
   - `CANONICAL_KV_DIRECTORY_DIGEST_SELFTEST_PASS`
   - `LOGICAL_PREFIX_RESOURCE_GUARD_SELFTEST_PASS`;
8. run the measured runner's `--preflight-only` path and require:
   - `LAYER0_PROJECTION_ORIGIN_MEASURED_PREFLIGHT_PASS`;
9. confirm primary checkout is untouched.

Any failure before wrapper invocation stops this authority. Do not repair and continue in the same transaction.

## Shared local-GPU boundary

The execute-once wrapper must invoke the measured runner only through the canonical resource guard:

`e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py`

Required resource:

```text
resource key = llama-cpp:local-gpu
lock root = /tmp/relaylm/physical/locks
lock = /tmp/relaylm/physical/locks/a820834e5681ba28.lock
```

Before child invocation, exactly two idle observations five seconds apart must prove:

- no `llama-server`;
- no `llama-cli`;
- no `llama-run`;
- no listener on `127.0.0.1:1234`.

The guard must not create or touch campaign queue/receipt/lease/spend state.

## Exactly-once execution sequence

Only after all admission checks pass:

```text
W fresh server:
  start
  W request exactly once
  stop

C fresh server:
  start
  C request exactly once
  stop

zero-GPU posthoc:
  historical-integrity gate
  logical-position reconstruction
  attn_norm-0 / Kcur-0 / Vcur-0 exact comparison
```

Measured request count must be exactly 2.

## Consumption boundary

The measured runner writes:

`server-W/W.request.json`

before the W HTTP POST.

If the execute-once child terminates without a measured terminal:

```text
W.request.json absent
  -> LAYER0_PROJECTION_ORIGIN_PROBE_NOT_EXERCISED
  -> measured_attempt_consumed = false

W.request.json present
  -> LAYER0_PROJECTION_ORIGIN_PROBE_EXERCISED_INCOMPLETE
  -> measured_attempt_consumed = true
```

Once the W request record exists, this authority is permanently consumed regardless of whether the HTTP call completes.

No retry, replay, resume, reseed, alternate port set, repaired runner, fallback, or replacement attempt is authorized after consumption.

A complete W/C classification is also permanently consumed.

## Posthoc integrity gate

Before interpreting layer-0 tensors:

```text
new W-P512 == historical WR-P512
new C-P512 == historical C-P512
```

must hold byte-for-byte under canonical geometry validation.

If not:

`INSTRUMENTATION_PERTURBED_SUBJECT`

This is a terminal consumed result. Do not interpret projection tensors causally and do not rerun.

## Primary complete classifications

### `LAYER0_PROJECTION_NUMERICAL_ORIGIN_OBSERVED`

Required:

- historical KV integrity gate passes;
- `attn_norm-0(W) == attn_norm-0(C)` bit-for-bit across logical positions 0..511;
- Kcur and/or Vcur differs.

Interpretation: the earliest observed numerical difference across this boundary appears at the layer-0 projection output. This does not by itself prove stream-K as the specific internal submechanism.

### `LAYER0_PREPROJECTION_DIFFERENCE_OBSERVED`

Historical integrity gate passes, but `attn_norm-0` already differs.

Interpretation at classification time: the earliest observed difference on the instrumented boundary is already present at `attn_norm-0`, before raw K/V projection output. Post-terminal source audit below narrows the scientific claim: because `ggml_set_output()` changes fusion eligibility, this classification does **not** by itself prove that the uninstrumented causal origin is earlier than K/V projection.

### `LAYER0_PROJECTION_OUTPUT_IDENTICAL_ORIGIN_LATER`

Historical integrity gate passes and attn_norm/Kcur/Vcur are all bit-identical while cache-visible W/C still differs.

Interpretation: origin lies after raw projection output and before/in cache-visible K/V formation.

### `LAYER0_PROJECTION_PARTIAL_OR_AMBIGUOUS`

Integrity-valid complete observations that fit none of the above.

### `INSTRUMENTATION_PERTURBED_SUBJECT`

Historical integrity gate fails.

All complete measured classifications consume this authority.

## Forbidden

Must remain zero:

- L1 request;
- L0R request;
- WR2 server;
- any third measured request;
- historical fixture-v2 measured wrapper/runner replay;
- historical segmentation-control replay;
- FA-OFF;
- `scientific --execute`;
- #2965 campaign invocation;
- #2964 mutation;
- campaign queue/receipt/lease/spend;
- protected `v1` mutation;
- `main`, `v2`, or `relay-theory` mutation;
- production cache-policy mutation;
- primary dirty checkout mutation;
- historical raw evidence mutation;
- upstream submission.

## Authorized invocation shape

Use fresh nonexistent preflight and measured output roots, an identity-qualified premeasured root, a historical KV root matching the pinned directory digests, the frozen model, and two fresh distinct loopback ports:

```bash
python3 \
  diagnostics/llama-cpp/e2d2c0d6-gemma4-layer0-projection-origin-execute-once.py \
  --premeasured-root <IDENTITY_QUALIFIED_PREMEASURED_ROOT> \
  --historical-kv-root <PINNED_HISTORICAL_KV_ROOT> \
  --model <FROZEN_MODEL_PATH> \
  --preflight-root <FRESH_NONEXISTENT_PREFLIGHT_ROOT> \
  --out-root <FRESH_NONEXISTENT_MEASURED_ROOT> \
  --port-w <FRESH_PORT_W> \
  --port-c <FRESH_PORT_C>
```

Invoke this wrapper at most once under this authority.

Do not invoke the inner measured runner directly.

## Stop condition

After the wrapper returns, read back:

- wrapper preflight terminal;
- resource guard;
- external quiescence;
- measured terminal if present;
- W/C request accounting;
- required KV/projection dumps;
- posthoc terminal.

Then stop. No follow-on physical test is authorized by this authority.

## Terminal measured execution

This authority was exercised exactly once and is permanently consumed.

Observed terminal classification: **LAYER0_PREPROJECTION_DIFFERENCE_OBSERVED**.

Execution accounting:

- execute-once wrapper invocations = 1
- direct measured inner-runner invocations = 0
- required non-measured --preflight-only invocations = 1
- measured request count = 2
- request order = W -> C
- retry/replay/resume/reseed/fallback = 0
- L1 = 0; L0R = 0; WR2 = 0; FA-OFF = 0
- scientific campaign interaction = 0
- rerun_authorized = false

Measured request accounting:

- W: HTTP 200, cache_n=0, prompt_n=883, predicted_n=1
- C: HTTP 200, cache_n=0, prompt_n=2927, predicted_n=1

Both request SHA256 identities matched the pinned authority.

Historical integrity gate:

- new W-P512 == historical WR-P512: true
- new C-P512 == historical C-P512: true
- each canonical directory: 100 files, 96 K/V payloads, base/SWA rows 512/512, base/SWA KV 8192/1536, logical positions 0..511, v_trans=0

Therefore the instrumentation preserved the previously measured cache-visible W/C subject at the canonical 512-token boundary.

Projection-surface result over logical positions 0..511:

- attn_norm-0: bit-exact=false; differing rows=512/512; differing elements=1,966,080/1,966,080; max abs=10.2819712162; max ULP-like=2,168,173,358
- Kcur-0: bit-exact=false; differing rows=512/512; differing elements=1,048,575/1,048,576; max abs=10.0582499504; max ULP-like=2,168,577,328
- Vcur-0: bit-exact=false; differing rows=512/512; differing elements=1,048,575/1,048,576; max abs=10.0582499504; max ULP-like=2,168,577,328

The attn_norm-0 difference begins at logical position 0 and occurs in both warm physical-segmentation regions: segment A (0..370) and segment B (371..511).

### Post-terminal frozen-source interpretation

Fresh static read-back of frozen llama.cpp e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d establishes this layer-0 order:

token embedding lookup -> inp_scaled = embedding * sqrt(n_embd) -> layer-0 RMS norm -> attn_norm-0 -> Q/K/V projection -> Kcur-0 / Vcur-0 -> K/V norm / K RoPE -> cache write.

For the committed fixture, W and C share the same token sequence through logical position 864, so logical positions 0..511 have identical token IDs. The immediate mathematical predecessor of layer-0 RMS normalization is therefore the same token-embedding lookup and fixed sqrt(n_embd) scaling for the compared prefix.

However, the observation method marks attn_norm-0, Kcur-0, and Vcur-0 with ggml_set_output(). In the same frozen GGML source, fusion eligibility explicitly rejects any node carrying GGML_TENSOR_FLAG_OUTPUT. Therefore ggml_set_output() is not merely a lifetime-retention annotation; it can alter graph fusion and kernel scheduling around the observed tensors.

Conservative terminal scientific interpretation:

**CACHE-VISIBLE SUBJECT PRESERVED + EARLIEST OBSERVED INSTRUMENTED DIFFERENCE = attn_norm-0 + UNINSTRUMENTED CAUSAL ORIGIN NOT YET PROVEN.**

The measured result rejects the narrower claim that the first observed difference appears only at K/V projection output.

It does not yet distinguish between (1) a genuine width/segmentation-sensitive numerical difference arising at the layer-0 RMS-normalization surface and (2) an observation-induced difference caused by the output/fusion barrier interacting with width-dependent execution.

Accordingly, this terminal must not be upgraded to LAYER0_RMS_NORM_CAUSAL_ORIGIN_PROVEN or STREAM_K_CAUSAL_ORIGIN_PROVEN without a separate non-perturbative discriminator.

No further physical execution is authorized by this terminal authority.

### Frozen-source audit refinement after terminal reconciliation

Additional zero-GPU source audit narrows the instrumentation concern.

1. GGML allocator semantics: tensors carrying GGML_TENSOR_FLAG_OUTPUT are never freed by the graph allocator and are not eligible for in-place parent-buffer reuse. Therefore the post-graph host dumps of attn_norm-0, Kcur-0, and Vcur-0 are not explained by their buffers being recycled and overwritten by later tensors.

2. CUDA fusion semantics: Gemma4 layer-0 build_norm produces an RMS_NORM followed by the learned-weight MUL. The named attn_norm-0 tensor is the final MUL node. The generic sequential fusion predicate rejects GGML_TENSOR_FLAG_OUTPUT only on intermediate nodes, not on the final node. Therefore marking attn_norm-0 as an output does not by itself disable the RMS_NORM->MUL fusion that produces attn_norm-0.

3. Immediate predecessor semantics: the layer-0 input is token embedding lookup followed by elementwise multiplication by the fixed sqrt(n_embd) factor. Frozen CUDA get-rows selects/dequantizes each token row independently, and the scale kernel performs an elementwise fixed multiply. Neither operation reduces across token rows.

4. RMS normalization semantics: the frozen CUDA RMS-norm kernel launches one block per row and reduces only across that row's hidden dimension ncols. Token batch width changes grid extent but not another row's reduction domain. With identical token IDs at logical positions 0..511, the ordinary mathematical path embedding -> fixed scale -> row-local RMS norm is therefore expected to be width-invariant for those rows.

Consequently, the measured all-element attn_norm-0 W/C difference is not naturally explained by the pure layer-0 mathematical operators alone. The remaining static candidate class moves toward runtime graph/input binding, graph reuse/update, allocator/scheduler placement, or another shape-dependent execution-state effect before or at the realized attn_norm buffer.

This still does not prove a specific runtime mechanism. The next permitted work is zero-GPU analysis of the already-consumed projection dumps; no additional physical request is authorized.

### Zero-GPU row-wise scalar relation result

Existing consumed projection dumps were analyzed without GPU/model/server/HTTP/generation activity.

Classification:

`ROW_WISE_SCALAR_PREPROJECTION_RELATION_MIXED`

Key result:

- Segment A (logical 0..370; W width 371 vs C width 512) remains moderately similar but fails strict scalar/collinearity thresholds for every row.
- Segment B (logical 371..511; W rows are local columns 0..140 of width-508 ubatch, C rows are local columns 371..511 of width-512 ubatch) is strongly non-collinear.
- near-pure-scalar rows = 0/512 for attn_norm-0, Kcur-0, and Vcur-0.
- near-collinear rows = 0/512 for attn_norm-0, Kcur-0, and Vcur-0.

Representative summaries:

- attn_norm-0 segment A: mean cosine 0.987321; mean scalar-fit residual 0.154198.
- attn_norm-0 segment B: mean cosine 0.178276; mean scalar-fit residual 0.983603.
- Kcur/Vcur segment A: mean cosine 0.907078; mean scalar-fit residual 0.389956.
- Kcur/Vcur segment B: mean cosine 0.136602; mean scalar-fit residual 0.990234.

Therefore the simple model `W row ~= alpha * C row` is rejected as a global explanation of the consumed preprojection difference.

The abrupt A/B contrast is itself a new zero-GPU clue: Segment B changes local ubatch column origin (W logical 371 starts at local column 0; C logical 371 is local column 371). A dedicated read-only row-alignment posthoc has been added to distinguish same-logical-position correspondence from accidental same-local-column correspondence.

No physical rerun is authorized or required for that analysis.


### Row-alignment interpretation refinement

The zero-GPU row-alignment runner emitted the raw classifier:

`ROW_ALIGNMENT_PREVIOUS_WARM_LOCAL_COLUMN_SUPPORTED`

That raw label is preserved as execution output, but its mechanistic interpretation is narrower than the evidence supports.

For Segment B, local column `i` is compared against:

- cold C local column `i`, which is logical position `i`;
- previous warm W-A local column `i`, which is also logical position `i`.

Because W and C share the same token sequence through logical position 864, those two local-column references carry the same token ID at every `i=0..140`. They are therefore not independent stale-vs-cold hypotheses.

By contrast, W-B local column `i` corresponds to logical position `371+i`. In the committed fixture, only 10/141 pairs satisfy:

`token[i] == token[371+i]`

Thus 131/141 Segment-B rows compare different token IDs between the local-column and same-logical alternatives.

Observed correspondence:

- for all three dumped tensors, local-column references beat same-logical references on all 141 Segment-B rows;
- previous-warm and cold-local mean cosines are close, as expected because both refer to the same token identity at local column `i`;
- the small previous-warm advantage is not sufficient to isolate stale previous-ubatch carry-over.

Therefore the conservative scientific interpretation is:

`ROW_ALIGNMENT_LOCAL_COLUMN_TOKEN_CORRESPONDENCE_SUPPORTED`

This supersedes only the mechanistic reading of the raw `PREVIOUS_WARM` label, not the raw zero-GPU result itself.

The result supports a strong local-column / token-correspondence anomaly in the consumed intermediate dumps and weakens the claim that those dumped rows can be interpreted directly as the intended logical positions in Segment B.

It does **not** yet prove:

- previous-ubatch stale-buffer carry-over;
- scheduler bug;
- CUDA graph bug;
- allocator bug;
- stream-K causal origin.

A follow-on zero-GPU nearest-row analysis is authorized on the existing consumed dump only. No new physical request is authorized.


### Distinct-token nearest-row result

A zero-GPU nearest-row analysis over the existing consumed Segment-B dump completed with:

`LOCAL_COLUMN_PAIRWISE_CORRESPONDENCE_ONLY_UNDER_DISTINCT_TOKEN_CONTROL`

Control:

- Segment-B rows analyzed = 141;
- `token[i] == token[371+i]` = 10;
- distinct local-vs-logical token rows = 131.

For each of `attn_norm-0`, `Kcur-0`, and `Vcur-0`:

- same-local cosine exceeded same-logical cosine on all 131/131 distinct-token rows;
- the globally nearest C row was never the exact same local column and never the exact same logical position for those distinct-token controls;
- nearest-row token identity showed only weak local-token preference and no exact-row mapping.

Observed distinct-token summaries:

- attn_norm-0: best same-local row = 0; best same-logical row = 0; best-row token matches local token = 11; best-row token matches warm-logical token = 4.
- Kcur-0: best same-local row = 0; best same-logical row = 0; best-row token matches local token = 10; best-row token matches warm-logical token = 10.
- Vcur-0: same as Kcur-0.

Therefore the evidence supports a **local-column-dependent correspondence/distortion**, but does not support an exact local-row remapping or exact stale previous-ubatch row copy.

The previous raw row-alignment classification must not be upgraded to a stale-buffer mechanism claim.

### GGUF projection-path correction

A zero-GPU GGUF tensor-name audit of the frozen model SHA256
`c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`
found:

- layer-0 path = `SEPARATE_Q_K_V`;
- q tensors = 48;
- k tensors = 48;
- v tensors = 40;
- fused qkv tensors = 0;
- layer 0 has q=true, k=true, v=true, qkv=false.

Therefore layer-0 `Kcur-0 == Vcur-0` cannot be explained by the Gemma4 optional-`v_proj` fallback `Vcur = Kcur`.

The byte-identical Kcur/Vcur dump payloads are now a separate unresolved anomaly requiring zero-GPU weight-identity and instrumentation/runtime reconciliation before any additional physical discriminator is designed.


### Static K/V alias-path audit

Further zero-GPU audit of frozen llama.cpp `e2d2c0d6...` narrows the byte-identical raw `Kcur-0` / `Vcur-0` anomaly.

Established from frozen source:

1. Gemma4 layer-0 with present `wv` constructs separate projection nodes:
   - `Kcur = build_lora_mm(layer.wk, cur, ...)`
   - `Vcur = build_lora_mm(layer.wv, cur, ...)`
2. `cb(Kcur, "Kcur", 0)` and `cb(Vcur, "Vcur", 0)` assign distinct graph names.
3. `ggml_graph_get_tensor()` resolves exact names by string equality.
4. The model loader only returns an existing tensor for the explicit `TENSOR_DUPLICATED` path. Gemma4 K/V projection weights are not created with that flag, so present `wk` and `wv` are distinct model tensor objects.
5. Scheduler graph copies preserve tensor flags, names, op params, view metadata, and recursively distinct sources.
6. GGML allocator semantics keep graph outputs alive and prevent output-parent reuse; output tensors are not freed/recycled during the graph allocation lifetime.

Therefore the consumed `Kcur-0 == Vcur-0` payload identity is not naturally explained by:

- absent V projection;
- graph-name collision;
- model-loader duplicated-tensor aliasing;
- ordinary gallocr output-buffer reuse.

A zero-GPU layer-0 K/V weight-identity audit has been added. It compares frozen GGUF K/V tensor type, shape, raw payload SHA256, and frozen gguf-py dequantized F32 equality.

If that audit classifies `LAYER0_KV_WEIGHTS_DISTINCT`, the remaining anomaly is localized to projection execution / scheduler-backend realization / observation instrumentation rather than model weight identity.

No physical execution is authorized by this refinement.


### K/V weight audit dependency blocker and apparatus repair

The first canonical zero-GPU K/V weight-identity runner invocation did not produce a scientific result.

Observed local execution:

- output root: `/tmp/relaylm-layer0-kv-weight-identity.Tvva0g/result`;
- canonical runner invoked exactly once;
- runner rc = 1;
- failure occurred while importing frozen `gguf-py`;
- blocker: `ModuleNotFoundError: No module named 'numpy'`;
- `GGUFReader` was not reached;
- no K/V metadata, payload SHA, dequantized SHA, or numerical comparison was produced;
- no `terminal.json` was produced;
- physical/GPU/model/generation/measured counters remained zero.

Classification of that attempt:

`KV_WEIGHT_IDENTITY_ZERO_GPU_DEPENDENCY_BLOCKED_NO_SCIENTIFIC_RESULT`

This was not a scientific spend and does not consume any physical authority.

The diagnostic apparatus has since been repaired without adding dependencies:

- GGUF header, metadata, tensor table, offsets, and tensor payloads are parsed with Python stdlib only;
- Q4_K and Q6_K dequantization required by the frozen layer-0 K/V subject is implemented directly from frozen llama.cpp / gguf-py format definitions;
- float32 rounding is reproduced at the same arithmetic boundaries used by the frozen NumPy implementation before hashing F32 output;
- raw payload SHA256 and dequantized F32 SHA256 remain part of the audit;
- no `numpy` import is used or required;
- synthetic selftests cover GGUF parsing, Q4_K decode, Q6_K decode, tensor offsets, and dependency absence.

The repaired apparatus is a new zero-GPU execution generation. It does not authorize any physical/model/server execution.

Status:

`KV_WEIGHT_IDENTITY_STDLIB_ZERO_GPU_REPAIRED_READY`


### Layer-0 K/V weight distinctness and execution-path narrowing

The repaired stdlib-only zero-GPU K/V weight audit completed successfully under generation:

`kv-weight-identity-stdlib-20260922-a`

Scientific classification:

`LAYER0_KV_WEIGHTS_DISTINCT`

Frozen model:

- SHA256: `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`

Layer-0 K:

- tensor: `blk.0.attn_k.weight`
- type: Q4_K
- shape: [3840, 2048]
- elements: 7,864,320
- bytes: 4,423,680
- data offset: 841,595,040
- raw payload SHA256: distinct from V
- dequantized F32 SHA256: distinct from V

Layer-0 V:

- tensor: `blk.0.attn_v.weight`
- type: Q6_K
- shape: [3840, 2048]
- elements: 7,864,320
- bytes: 6,451,200
- data offset: 863,730,848
- raw payload SHA256: distinct from K
- dequantized F32 SHA256: distinct from K

Numerical comparison:

- same type: false
- same shape: true
- raw payload identical: false
- dequantized bit-exact equal: false
- elements compared: 7,864,320
- max absolute difference: 0.32143402099609375
- mean absolute difference: 0.017000692212983875

Therefore the consumed byte-identical raw `Kcur-0` / `Vcur-0` projection dumps cannot be explained by model-level K/V weight identity.

Further frozen-source audit narrows the path:

1. Gemma4 layer-0 constructs separate K/V projections from present `wk` and `wv`.
2. `build_lora_mm()` creates a fresh `ggml_mul_mat(ctx0, w, cur)` for every call; it does not cache or share results by input.
3. K/V raw projection nodes receive distinct names `Kcur-0` and `Vcur-0`.
4. `ggml_graph_get_tensor()` performs exact-name lookup.
5. K/V weights are distinct loader tensor objects; `TENSOR_DUPLICATED` does not apply.
6. Scheduler graph copy preserves tensor flags, names, sources, shapes, strides, and source data pointers.
7. GGML graph outputs are retained and are not ordinarily freed/reused by gallocr.
8. CUDA backend tensor reads copy from `tensor->data + offset`, so view/data origin is respected by the backend read path.
9. CUDA MMQ dispatch switches on `src0->type`; Q4_K and Q6_K select distinct template specializations.
10. CUDA graph update state records each node and each source data pointer/shape/stride by node index; it is not keyed only by output shape.
11. CUDA graph QKV concurrency reordering is separately opt-in through `GGML_CUDA_GRAPH_OPT=1`.
12. `build_lora_mm()` itself supplies no projection-result cache or aliasing path.

Conservative residual domain:

- realized projection execution;
- scheduler/backend tensor realization;
- CUDA/MMQ runtime state;
- diagnostic observation instrumentation.

Still unproven:

- MMQ bug;
- CUDA graph bug;
- scheduler bug;
- stale-buffer bug;
- instrumentation bug.

The next useful physical discriminator, if separately authorized, should not repeat the prior value-only projection probe. It should record **runtime tensor provenance** for Kcur/Vcur: tensor object identity, data pointer, buffer identity, view source/offset, op, source tensor identities/types/data pointers, geometry, and output flags, while preserving the existing historical-KV integrity gate.

No physical execution is authorized by this authority update.


### Provenance static selftest false-negative and repair

The first provenance patch static qualification did not reach the temporary
frozen-source clone or patch application stage.

Observed classification:

`PROVENANCE_PATCH_STATIC_SELFTEST_FAIL_MISSING_MARKERS`

The failure was caused by the selftest requiring each TSV field name to appear
as its own separately quoted C++ string literal, while the provenance patch
emits the schema across combined string literals.

No physical/GPU/model/generation activity occurred and no scientific evidence
was consumed.

The selftest has been repaired to:

- locate the combined provenance TSV header;
- decode its C++ string literals;
- compare the exact decoded tab-separated schema;
- preserve the existing forbidden-arithmetic/execution checks;
- continue to require clean four-patch application to frozen llama.cpp and
  `git diff --check`.

A follow-up inspection found and repaired over-escaped `\\t` handling in the
first repair before any new selftest execution.

New static selftest generation:

`projection-provenance-static-20260923-b`

Current status:

`PROVENANCE_APPARATUS_STATIC_REQUALIFICATION_READY`

This status authorizes only a new zero-GPU/static selftest invocation. It does
not authorize build, model load, GPU execution, HTTP/generation, or any physical
probe.


### Provenance posthoc classifier apparatus

A zero-GPU posthoc classifier has been added for any future provenance-enabled
projection dump.

Files:

- `e2d2c0d6-gemma4-layer0-projection-provenance-posthoc.py`
- `e2d2c0d6-gemma4-layer0-projection-provenance-posthoc-selftest.py`

The classifier requires the exact provenance TSV schema and evaluates K/V per
dump using:

- tensor object pointers;
- output data pointers;
- output buffer pointers;
- view source / view offset;
- op / flags / geometry;
- immediate source object/name/type/data/buffer/op;
- raw Kcur/Vcur payload SHA256.

Strong classification
`K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_IDENTICAL` requires:

- distinct K/V tensor objects;
- distinct K/V output data pointers;
- distinct K/V src0(weight) objects and data pointers;
- K src0 name/type = `blk.0.attn_k.weight` / Q4_K;
- V src0 name/type = `blk.0.attn_v.weight` / Q6_K;
- both ops = MUL_MAT;
- K/V src1 object and data pointer are the same shared activation;
- raw Kcur/Vcur payload remains byte-identical.

Other explicit classifications cover tensor-object alias, output-data alias,
weight-source alias, unexpected source semantics, value-distinct outputs, and
mixed behavior across W371/W508/C512 dumps.

Aggregate strong result across all three dumps is:

`K_V_DISTINCT_RUNTIME_PROVENANCE_IDENTICAL_VALUES_REPRODUCED`

This would still not by itself identify MMQ, CUDA graph, scheduler, or another
specific mechanism. It would establish only that distinct runtime graph/source
provenance produced identical observed values.

Current zero-GPU gate order:

1. `projection-provenance-static-20260923-b` patch static requalification;
2. provenance posthoc classifier selftest.

No physical execution is authorized by either gate.


### Provenance patch hunk corruption and generation-c repair

The first execution of static generation
`projection-provenance-static-20260923-b` passed schema decoding and the first
three prerequisite patch applications, then failed on the fourth provenance
patch with:

`error: corrupt patch at line 92`

No Stage-B posthoc selftest was run. No physical/GPU/model/generation activity
occurred.

Root cause was deterministic patch syntax:

- provenance patch declared hunk: old/new = 6/63;
- actual hunk body: old/new = 6/67;
- added lines = 61;
- unchanged context lines = 6.

The patch header has been corrected to:

`@@ -1435,6 +1435,67 @@`

Repository-side static recount confirms declared old/new 6/67 equals observed
old/new 6/67.

The static selftest has also been hardened with an independent unified-diff
hunk-count validator so future declared/body count drift fails explicitly before
temporary clone/apply.

New static generation:

`projection-provenance-static-20260923-c`

Allowed next gate order remains:

1. one Stage-A static provenance patch selftest for generation c;
2. only if Stage A passes, one provenance posthoc classifier selftest.

Status:

`PROVENANCE_PATCH_GENERATION_C_STATIC_REQUALIFICATION_READY`

No build or physical/model execution is authorized.


### Provenance patch generation-c context failure and generation-d repair

Static generation `projection-provenance-static-20260923-c` passed:

- Python compile;
- unified-diff hunk-count validation;
- exact 26-field provenance schema decoding;
- frozen source verification;
- temporary clone;
- prerequisite patches 1-3 apply/check.

It then failed at provenance patch 4 with:

`src/llama-context.cpp:1435: patch does not apply`

No Stage-B selftest was run. No physical/GPU/model/generation activity occurred.

The remaining defect was stale/over-specific hunk context, not hunk syntax.

Generation d rewrites the provenance patch hunk to anchor directly on the unique
existing projection-origin declaration:

`std::ofstream manifest(root / "manifest.tsv", ...)`

The new hunk removes preceding context that could drift after patches 1-3.

Generation-d hunk:

- declared old/new = 3/64;
- repository-side observed old/new = 3/64.

New static generation:

`projection-provenance-static-20260923-d`

Status:

`PROVENANCE_PATCH_GENERATION_D_STATIC_REQUALIFICATION_READY`

Allowed next order:

1. one generation-d Stage-A static selftest;
2. only if Stage A passes, one provenance posthoc classifier selftest.

No build or physical/model execution is authorized.


### Provenance apparatus and posthoc classifier statically qualified

Static generation:

`projection-provenance-static-20260923-d`

Stage A completed successfully:

- `py_compile`: PASS;
- canonical static selftest invocation count: 1;
- classification:
  `LAYER0_PROJECTION_PROVENANCE_PATCH_STATIC_PASS`;
- all unified-diff hunk-count checks: PASS;
- provenance patch hunk declared/observed old/new: 3/64 == 3/64;
- exact 26-field provenance schema: PASS;
- all four diagnostic patches `git apply --check`: PASS;
- all four diagnostic patches applied in the temporary frozen-source clone: PASS;
- `git diff --check`: PASS;
- provenance markers and existing projection-origin markers: PASS;
- no arithmetic or graph-execution path added.

Stage B completed successfully:

- `py_compile`: PASS;
- canonical posthoc selftest invocation count: 1;
- classification:
  `LAYER0_PROJECTION_PROVENANCE_POSTHOC_SELFTEST_PASS`.

Synthetic classifier coverage includes:

- `K_V_RUNTIME_TENSOR_OBJECT_ALIAS`;
- `K_V_RUNTIME_OUTPUT_DATA_ALIAS`;
- `K_V_RUNTIME_WEIGHT_SOURCE_ALIAS`;
- `K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_IDENTICAL`;
- `K_V_RUNTIME_PROVENANCE_DISTINCT_VALUE_DISTINCT`.

Aggregate strong synthetic result:

`K_V_DISTINCT_RUNTIME_PROVENANCE_IDENTICAL_VALUES_REPRODUCED`

The strong case requires:

- distinct K/V tensor objects;
- distinct K/V output data pointers;
- distinct K/V source-weight objects and data pointers;
- K/V ops both `MUL_MAT`;
- K source `blk.0.attn_k.weight` / Q4_K;
- V source `blk.0.attn_v.weight` / Q6_K;
- shared K/V src1 activation object and data pointer;
- byte-identical observed Kcur/Vcur payloads.

Safety counters for both static stages:

- physical_calls = 0;
- gpu_calls = 0;
- model_loads = 0;
- generation_requests = 0;
- measured_requests = 0.

Final static qualification:

`PROVENANCE_APPARATUS_AND_POSTHOC_STATICALLY_QUALIFIED`

This does not constitute runtime provenance evidence and does not authorize
replay of the consumed layer-0 projection-origin transaction.

Any future physical discriminator should be a separately authorized
provenance-enabled execution that preserves the existing historical-KV
integrity gate and uses the prequalified posthoc classifier.

Status:

`PROVENANCE_ENABLED_PHYSICAL_AUTHORITY_NOT_YET_GRANTED`


### Provenance-enabled preparation apparatus

A new preparation-only apparatus has been added for the future
provenance-enabled physical discriminator.

Files:

- `e2d2c0d6-gemma4-layer0-projection-provenance-build-run.sh`
- `e2d2c0d6-gemma4-layer0-projection-provenance-binary-preflight.py`
- `e2d2c0d6-gemma4-layer0-projection-provenance-qualification-run.sh`
- `e2d2c0d6-gemma4-layer0-projection-provenance-prepare-run.sh`
- `e2d2c0d6-gemma4-layer0-projection-provenance-preparation-static-selftest.py`

Purpose:

1. build a fresh isolated llama.cpp binary from frozen
   `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`;
2. apply the exact four-patch chain:
   aligned-reuse -> logical-prefix -> projection-origin -> projection-provenance;
3. bind binary provenance to the four patch SHA256 values and the complete
   applied patch;
4. verify runtime binary markers for projection-origin and provenance output;
5. run only non-generative plain/probe startup qualification under the canonical
   local-GPU resource guard;
6. emit a premeasured terminal suitable for a later, separately authorized
   provenance-enabled measured runner.

The qualification stage includes the already qualified provenance posthoc
classifier selftest.

The binary preflight requires runtime markers including:

- `provenance.tsv`;
- `tensor_ptr`;
- `src0_ptr`;
- `src1_ptr`.

It rejects historical consumed server binary hashes, including
`a5d767da8006aaf0537594ae308fc427cdb92154f48c5a3a325be3908352c5bb`.

Preparation classification on success:

`LAYER0_PROJECTION_PROVENANCE_PREMEASURED_READY`

Important boundary:

- preparation may build CUDA code and perform guarded non-generative model/GPU
  startup qualification;
- it sends no completion/chat/generation request;
- it creates no measured W/C request record;
- it does not consume the future scientific measured attempt;
- it does not authorize measured execution by its own result.

Preparation-only status:

`PROVENANCE_PREPARATION_ONLY_AUTHORIZED_UNSPENT`

Measured provenance-enabled physical execution remains:

`PROVENANCE_ENABLED_PHYSICAL_AUTHORITY_NOT_YET_GRANTED`

The next allowed local action is exactly one fresh provenance preparation run.
After its immutable binary/runtime hashes and startup evidence are reported,
the measured provenance authority and execute-once runner can be pinned to that
specific prepared apparatus.


### Provenance preparation static gate false-positive and generation-b repair

The first preparation static selftest stopped before build/startup with:

`qualification unexpectedly contains forbidden measured/generation token: campaign queue`

No build, model startup, generation, measured request, or scientific spend
occurred.

The failure was a static-selftest false positive. The qualification runner
contains fail-closed assertions that explicitly reject:

- `campaign_queue_receipt_created != false`;
- `campaign_queue_or_spend_artifact_touched != false`.

The old selftest treated the descriptive phrase `campaign queue` itself as an
execution marker.

The repaired gate now:

- rejects concrete generation/measured execution paths such as
  `/completion`, `/v1/chat/completions`, `scientific --execute`, and
  measured/execute-once runner names;
- explicitly requires the two negative campaign/spend assertions to remain in
  the qualification runner;
- stamps build, qualification, and top-level preparation terminals with the
  same preparation generation.

New preparation generation:

`provenance-preparation-20260923-b`

Status:

`PROVENANCE_PREPARATION_GENERATION_B_STATIC_REQUALIFICATION_READY`

Existing boundary remains unchanged:

- preparation-only execution may be attempted after the repaired static gate;
- provenance measured physical execution remains unauthorized.


### Provenance preparation transitive non-generation audit and generation-c repair

Before running preparation generation b, the static apparatus audit was extended
to cover the transitive startup path:

- provenance build runner;
- provenance qualification runner;
- provenance prepare orchestrator;
- provenance binary preflight;
- startup recovery runner;
- startup recovery helper;
- canonical resource guard.

The extended gate requires:

- shell syntax for all shell helpers;
- Python compile for binary preflight and resource guard;
- no concrete completion/chat/measured/execute-once path in the transitive
  preparation closure;
- startup helper contains only the expected `/health` readiness probe and
  explicit `READY_NON_GENERATIVE` / unexpected-dump guards;
- qualification invokes startup through the canonical resource guard;
- qualification retains the negative campaign queue/spend assertions.

During this read-only audit, one additional static false-negative was found
before any local preparation execution: the selftest expected the literal
`"--evidence-root" "$guard_root" --`, while the real qualified invocation is
`--evidence-root "$guard_root" --`.

That marker has been corrected. Build, qualification, prepare, and static
selftest generation stamps have all been advanced consistently to:

`provenance-preparation-20260923-c`

Repository-side read-back confirms:

- generation c is consistent across all four apparatus surfaces;
- resource-guard invocation marker matches the actual qualification script;
- guarded child is exactly the startup recovery runner;
- no generation request has been executed.

Status:

`PROVENANCE_PREPARATION_GENERATION_C_STATIC_REQUALIFICATION_READY`

Measured provenance execution remains unauthorized.


### Adversarial review blocks provenance preparation generation c

A full preparation-apparatus review is recorded in:

`e2d2c0d6-gemma4-layer0-projection-provenance-preparation-review.md`

The review found blocking gaps in:

- remote-authority to local-apparatus byte binding;
- hermetic runtime environment control;
- general GPU quiescence detection;
- build/preflight/startup artifact identity closure;
- exact frozen startup/runtime contract enforcement;
- strong posthoc pointer/null/src1 validation;
- internal enforcement of the preparation static gate;
- resource-guard release/failure semantics.

Additional hardening findings cover historical-binary rejection timing,
startup-run exit semantics, duplicate provenance rows, /tmp persistence, and
post-preparation artifact mutation.

Preparation generation c has not been executed. No build/model startup,
generation, measured request, or scientific spend was consumed by this review.

Previous readiness:

`PROVENANCE_PREPARATION_GENERATION_C_STATIC_REQUALIFICATION_READY`

is superseded by:

`PROVENANCE_PREPARATION_REVIEW_BLOCKED`

No preparation run is currently authorized. Measured provenance execution
remains unauthorized.


### Provenance preparation generation-d review repair complete

The adversarial review blockers have been addressed in the current preparation
apparatus. The detailed resolution matrix is recorded in:

`e2d2c0d6-gemma4-layer0-projection-provenance-preparation-review.md`

Generation-d now includes:

- fresh canonical remote authority fetch and exact clean-checkout binding;
- hermetic build/runtime environments;
- active CUDA compute-process quiescence checks;
- exact RTX 3060 / driver 591.44 / 12288 MiB identity;
- full prepared runtime-library hash closure;
- live loaded-library path verification;
- exact frozen startup geometry and SWA=1536;
- hardened null-safe provenance source binding;
- duplicate-row and payload-geometry validation;
- internal preparation static gate;
- fail-closed resource-guard release semantics;
- persistent non-/tmp evidence and read-only sealing;
- non-generative startup coverage for both KV and projection probe environments.

No generation-d preparation build/startup has been consumed.

The previous review-blocked status is superseded by:

`PROVENANCE_PREPARATION_GENERATION_D_STATIC_REQUALIFICATION_READY`

Only the generation-d static qualification is authorized next.

A preparation run becomes authorized only if that exact static gate passes.

Measured provenance execution remains:

`PROVENANCE_ENABLED_PHYSICAL_AUTHORITY_NOT_YET_GRANTED`


### Provenance preparation generation-d static gate failure and generation-e repair

Generation-d canonical static requalification was invoked exactly once from an
isolated clean authority checkout and failed before build/model startup.

Observed failure:

`prepare missing authority/sealing marker: gpu0.get("driver_version") != "591.44"`

Safety at failure:

- build invocations: 0;
- model startups: 0;
- GPU runtime calls: 0;
- generation requests: 0;
- measured requests: 0;
- measured attempt consumed: false;
- scientific spend consumed: false.

The exact GPU identity checks were not missing from the apparatus. They were
already present in
`e2d2c0d6-gemma4-layer0-projection-provenance-qualification-run.sh`:

- driver version must equal `591.44`;
- total GPU memory must equal `12288 MiB`.

The static selftest incorrectly required those qualification-owned markers to
appear in `prepare-run.sh`.

The repair moves the marker assertions to the qualification-run static marker
set while keeping the prepare-run checks limited to orchestration/authority/
sealing responsibilities.

The failed generation-d record is immutable. All preparation generation stamps
have been advanced to:

`provenance-preparation-20260923-e`

Current status:

`PROVENANCE_PREPARATION_GENERATION_E_STATIC_REQUALIFICATION_READY`

Only one generation-e canonical static requalification is authorized next.

A preparation build/startup remains unauthorized until that exact static gate
passes.

Measured provenance execution remains:

`PROVENANCE_ENABLED_PHYSICAL_AUTHORITY_NOT_YET_GRANTED`

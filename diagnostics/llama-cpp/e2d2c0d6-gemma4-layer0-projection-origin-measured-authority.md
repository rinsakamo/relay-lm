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

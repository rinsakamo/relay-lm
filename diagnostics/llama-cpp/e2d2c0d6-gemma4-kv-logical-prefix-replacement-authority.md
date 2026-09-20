# Gemma 4 logical-prefix KV replacement probe authority

Diagnostic only.

## Status of prior measured attempt

The preceding KV provenance attempt is terminal and consumed:

`PROBE_EXERCISED_INCOMPLETE`

It submitted L0 exactly once, received HTTP 200 with cache_n=0 / prompt_n=883 and first token 607 (`" with"`), then stopped because `WR-P512/` was absent.

That attempt MUST NOT be retried, replayed, repaired in-place, or resumed.

The absence of `WR-P512/` is an apparatus failure. It does not establish any of:

- `PREFIX_DUMP_NOT_REPRODUCIBLE`
- `PREFIX_KV_GENERATION_DIFFERS`
- `RETAINED_PREFIX_KV_MUTATED_BY_REUSE`
- `PREFIX_KV_IDENTICAL_THROUGH_REUSE`

## Replacement hypothesis

The old P512 instrumentation triggered only when a successful server decode had a physical `n_tokens == 512` batch whose positions were exactly 0..511.

That binds an observation of logical KV state to a physical server-batch shape.

The replacement instrumentation instead triggers after the successful prompt decode that contains logical position 511, independent of physical batch size. The dump routine itself remains the authority that positions 0..511 are live exactly once.

Therefore these physical decode shapes are observationally equivalent for the P512 trigger if they reach the same logical prefix:

```text
512
256 + 256
128 + 128 + 128 + 128
other successful subdivisions
```

No cache/reuse/attention/model semantics may be changed to obtain the dump.

## Frozen semantic target

Keep:

```text
llama.cpp source = e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d
model sha256 = c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed
ctx = 8192
batch = 512
ubatch = 512
parallel = 1
gpu layers = 999
context shift = disabled
flash attention = ON
compact SWA
temperature = 0
greedy
generated tokens per measured request = 1
```

The aligned-reuse diagnostic behavior used by the prior logical-batch-512 discriminator remains the intended reuse intervention.

## Replacement instrumentation

Use:

`e2d2c0d6-gemma4-kv-logical-prefix-dump-diagnostic.patch`

The P512 hook must:

1. run only after a successful prompt decode;
2. inspect the successful `batch_view`;
3. trigger when exactly one prompt token in that decode has logical position 511 and a single sequence id;
4. call `llama_debug_dump_kv_prefix(..., 0, 512, ...)`;
5. not require `n_tokens == 512`;
6. let the dump routine fail closed unless positions 0..511 are all present exactly once;
7. retain the separate aligned-reuse R512 hook after suffix removal and before continuation decode.

The hook may synchronize/copy already-computed state only. It must not add graph nodes, alter cache state, change attention inputs, change batch geometry, modify sampling, or change reuse policy.

## Build boundary

The old recovered binary SHA:

`0a9160015c31d11b607b1bd7559e69fe90c02d1079ad7517ccb24ea75c71b08e`

belongs to the consumed apparatus and MUST NOT be reused as the identity of the replacement probe.

Before any replacement measured generation:

1. use a clean disposable checkout/worktree of exact llama.cpp source revision;
2. apply the existing aligned-reuse diagnostic patch in its authority-defined order;
3. apply `e2d2c0d6-gemma4-kv-logical-prefix-dump-diagnostic.patch`;
4. verify patch application with `git apply --check`;
5. build `llama-server`;
6. record exact source/tree, patch SHA256 values, compiler/build identity, and new binary SHA256;
7. run `e2d2c0d6-gemma4-kv-logical-prefix-binary-preflight.py` and require `LOGICAL_PREFIX_BINARY_PREFLIGHT_PASS`;
8. prove the built binary contains the replacement instrumentation strings and does not retain the old generated-prefix failure marker;
9. run only non-generative startup qualification first.

Do not rewrite any runner's expected binary SHA until the new binary SHA has been observed and reconciled.

## Static patch contract

Before build, run:

`e2d2c0d6-gemma4-kv-logical-prefix-patch-selftest.py`

Required terminal:

`LOGICAL_PREFIX_PATCH_SELFTEST_PASS`

The self-test must prove at minimum:

- logical position 511 is the P512 trigger;
- the generated-prefix hook does not require `n_tokens == 512`;
- the dump request remains 0..512;
- the retained-prefix R512 hook remains bound to reuse p0==512;
- both P512 and R512 remain diagnostic-only hooks.

## Binary provenance preflight

After build and before startup qualification, run:

```bash
python3 diagnostics/llama-cpp/e2d2c0d6-gemma4-kv-logical-prefix-binary-preflight.py \
  --server-bin <new-llama-server> \
  --model <frozen-gguf> \
  --out <fresh-preflight-root>/logical-prefix-binary-preflight.json
```

Required terminal:

`LOGICAL_PREFIX_BINARY_PREFLIGHT_PASS`

It records:

- new server SHA256;
- frozen model SHA256;
- logical-prefix patch SHA256;
- aligned-reuse patch SHA256;
- presence of required replacement instrumentation markers;
- absence of the old `generated-prefix dump` failure marker.

This is non-generative and does not consume a measured replacement attempt.

## Non-generative recovery gate

A newly built replacement binary is a new physical artifact.

Before replacement measured L0, run a fresh non-generative startup recovery/qualification using the exact intended runtime and probe environment. The preferred orchestration is `e2d2c0d6-gemma4-kv-logical-prefix-qualification-run.sh`, normally invoked by the top-level pre-measured preparation wrapper.

Required evidence:

- server/model SHA256;
- exact canonical argv;
- HTTP health 200;
- same final `llama_context` block proves n_seq_max=1, n_ctx=8192, n_batch=512, n_ubatch=512, flash_attn=enabled;
- startup allocation proves base KV 8192 and compact SWA smaller than base;
- probe environment alone creates no dump;
- strict startup-classifier self-test passes;
- plain/probe allocation geometry agrees;
- no generation request is sent.

After this gate, record the new binary SHA into a fresh replacement measured-runner authority. Do not silently edit the consumed runner identity.

## Preferred pre-measured preparation entrypoint

Use:

`e2d2c0d6-gemma4-kv-logical-prefix-prepare-run.sh`

as the preferred host entrypoint for the replacement preparation stage.

Invocation:

```bash
bash diagnostics/llama-cpp/e2d2c0d6-gemma4-kv-logical-prefix-prepare-run.sh \
  <fresh-output-root> \
  <existing-llama.cpp-source-repository> \
  <frozen-model-path> \
  <fresh-plain-port> \
  <fresh-probe-port> \
  [build-jobs]
```

It performs only:

1. isolated local clone of the supplied llama.cpp repository;
2. checkout of exact source revision `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`;
3. patch self-test;
4. aligned-reuse patch apply-check/application;
5. logical-prefix patch apply-check/application;
6. `git diff --check`;
7. CUDA Release build of target `llama-server`;
8. replacement binary provenance preflight;
9. non-generative plain/probe startup recovery;
10. strict final-context and compact-SWA startup classification.

The build helper uses:

```text
-DGGML_CUDA=ON
-DCMAKE_BUILD_TYPE=Release
target = llama-server
```

and operates only in its fresh output root. It does not mutate the supplied source checkout.

Required terminal:

`LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY`

This terminal explicitly records:

```text
generated_requests = 0
measured_l0_submitted = false
measured_attempt_consumed = false
measured_execution_authorized_by_this_result = false
```

Therefore even a successful prepare result is **not** authority to send replacement L0. The returned new server SHA256 and qualification evidence must first be reconciled into a distinct measured-attempt authority.

## Replacement measured attempt boundary

This authority prepares the replacement apparatus but does **not** itself authorize an immediate measured rerun of the consumed attempt.

A subsequent replacement measured handoff must explicitly bind:

- the new binary SHA256;
- exact applied patch SHA256 values;
- non-generative startup qualification PASS;
- frozen model/request/token identities;
- canonical shared-GPU guard;
- a fresh output root;
- a new attempt identity distinct from the consumed attempt.

Once the replacement L0 is submitted, it is again exactly-once and consumed on any later failure.

## Campaign separation

This remains independent of the RelayLM v1 scientific campaign.

Must remain zero:

- #2965 campaign invocation;
- campaign queue/receipt/lease/spend mutation;
- #2964 reuse/mutation;
- protected v1 mutation;
- RC1 action;
- production/cache-policy mutation;
- FA-OFF arm;
- primary dirty checkout mutation;
- upstream submission.

Current repository authority at execution time always wins over snapshots in this document.

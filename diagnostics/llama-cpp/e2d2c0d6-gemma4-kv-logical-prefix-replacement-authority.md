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
8. prove the built runtime artifact closure contains the replacement instrumentation strings in their owning components and does not retain the old generated-prefix failure marker anywhere in that closure;
9. run only non-generative startup qualification first.

Do not rewrite any runner's expected binary SHA until the new binary SHA has been observed and reconciled.

## Static patch contract

Before build, run:

`e2d2c0d6-gemma4-kv-logical-prefix-patch-selftest.py`

Required terminal:

`LOGICAL_PREFIX_PATCH_SELFTEST_PASS`

The self-test must prove at minimum:

- every unified-diff hunk's declared old/new line counts match its actual body, so malformed patch metadata fails before build;
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
- the runtime artifact closure rooted at the built `llama-server`;
- canonical/resolved paths and SHA256 for the marker-owning sibling libraries;
- the three `server-context.cpp` replacement markers in `libllama-server-impl.so`;
- the two `llama-context.cpp` replacement markers in `libllama.so`;
- absence of the old `generated-prefix dump` failure marker from `llama-server`, `libllama-server-impl.so`, and `libllama.so`.

The executable alone is not the marker owner under the frozen build graph: `llama-server` is a thin entrypoint, `server-context.cpp` is incorporated into `llama-server-impl`, and `llama-context.cpp` is incorporated into `llama`.

This is non-generative and does not consume a measured replacement attempt.

## Non-generative recovery gate

A newly built replacement binary is a new physical artifact.

Before replacement measured L0, run a fresh non-generative startup recovery/qualification using the exact intended runtime and probe environment. The preferred orchestration is `e2d2c0d6-gemma4-kv-logical-prefix-qualification-run.sh`, normally invoked by the top-level pre-measured preparation wrapper.

Before either plain/probe server model load, qualification MUST acquire the canonical diagnostic shared-GPU flock for resource `llama-cpp:local-gpu` under `/tmp/relaylm/physical/locks/<sha256(resource_key)[:16]>.lock`. While holding that flock, it MUST prove two consecutive external-idle observations five seconds apart for `llama-server`, `llama-cli`, `llama-run`, and `127.0.0.1:1234`. Socket result `0` is busy, `ECONNREFUSED` is idle, and permission/timeout/other errno is inconclusive and fails closed. This guard is diagnostic-only and MUST NOT create or touch #2965 campaign queue/receipt/lease/spend artifacts.

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
9. resource-guard self-test plus canonical `llama-cpp:local-gpu` flock acquisition;
10. two consecutive external-idle observations five seconds apart while the flock is held;
11. non-generative plain/probe startup recovery under that same held flock;
12. strict final-context and compact-SWA startup classification.

The build helper uses the host-qualified native Linux CUDA toolkit binding:

```text
CUDA toolkit root = /usr/local/cuda-12.8
nvcc = /usr/local/cuda-12.8/bin/nvcc
required nvcc release = 12.8
configure PATH = /usr/local/cuda-12.8/bin:/usr/bin:/bin
-DGGML_CUDA=ON
-DCMAKE_BUILD_TYPE=Release
-DCUDAToolkit_ROOT=/usr/local/cuda-12.8
-DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.8/bin/nvcc
target = llama-server
```

This explicit binding is required because the WSL host inherits a Windows CUDA 12.1 path whose `nvcc.exe` can otherwise be selected by CMake while Linux `cudart` remains unresolved. The helper must fail closed before clone/build if the qualified native root/nvcc is absent, non-canonical, or not CUDA release 12.8. It records the exact toolkit root, nvcc path/version, native build PATH, and version.json hash when present.

The helper operates only in its fresh output root. It does not mutate the supplied source checkout, CUDA installation, symlinks, shell profile, or inherited host PATH.

Required terminal:

`LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY`

This terminal explicitly records:

```text
generated_requests = 0
measured_l0_submitted = false
measured_attempt_consumed = false
measured_execution_authorized_by_this_result = false
```

A successful qualification must also record the canonical diagnostic flock as acquired and cleanly released, exactly two idle observations with no busy process/default listener, guarded startup child exit 0, and explicit `campaign_queue_receipt_created=false` / `campaign_queue_or_spend_artifact_touched=false`.

Therefore even a successful prepare result is **not** authority to send replacement L0. The returned new server SHA256 and qualification evidence must first be reconciled into a distinct measured-attempt authority.

A pre-measured preparation failure before replacement L0 submission does not consume the replacement measured attempt. A build-stage CUDA discovery/configuration failure is apparatus-only when no model/server/generation boundary has been crossed. After deterministic apparatus repair, any subsequent preparation must use a fresh output root and a fresh preparation transaction; it is not a resume of the failed preparation.

## Observed pre-measured qualification

A fresh pre-measured preparation completed successfully under diagnostic commit:

`a9b69daae1ca6efc641a044db45f93287759dfb8`

with terminal:

`LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY`

Observed qualified artifact identity:

```text
premeasured evidence root = /tmp/relaylm-logical-prefix-premeasured.4BYIKs/output
llama.cpp source = e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d
llama.cpp tree = 6d39fd93dc91fc0a4bc86dffe9782d4f26318004
CUDA root = /usr/local/cuda-12.8
nvcc = /usr/local/cuda-12.8/bin/nvcc
nvcc = CUDA 12.8 / V12.8.93
CUDA version.json sha256 = 7c875ac3db43717d43da5d97d23c2b6b005f1afedf659f5191338b579fd0c764
aligned patch sha256 = cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a
logical-prefix patch sha256 = caad4731d82659468624e73803b6de6c3b8ac081d44350b8f71ae2d0600e1f36
combined applied.patch sha256 = d8d251727e5f3aa9a2d38434c124d0feb8748024f78cce5d4ec185bd8266fc7e
llama-server sha256 = 30d3f94f7335821a74828c243ab1dd315df9dc7a4c6df0cdff2f3ce1629dbaff
libllama-server-impl.so sha256 = e6003c1e1a1c1c16dc5a09da485517eec6b6010d17f198acd34981075c14a64c
libllama.so resolved sha256 = 53228c024c04bd4a1acefa03d9ddc602cdfc78b5214d7fb7da13de458d2a2965
model sha256 = c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed
canonical startup argv sha256 = 9294cc601e6be0511d92caa7e560b1f9a2843147b6b876a9c8896ae7822ab6fd
base KV = 8192
SWA KV = 1536
```

Binary provenance terminal:

`LOGICAL_PREFIX_BINARY_PREFLIGHT_PASS`

Startup terminal:

`LOGICAL_PREFIX_STARTUP_QUALIFIED`

The canonical diagnostic GPU flock was acquired and released cleanly, with exactly two idle observations and zero campaign queue/receipt/spend mutation.

Counters remained:

```text
generated_requests = 0
measured_l0_submitted = false
measured_attempt_consumed = false
measured_execution_authorized_by_this_result = false
```

This observed qualification binds the replacement physical artifact but is still not measured execution authority.

## Request-identity reconciliation gate

Before creating the distinct replacement measured-attempt authority, freeze the exact raw measured request identities.

Already frozen:

```text
warm token file sha256 = c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2
target token file sha256 = 549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e
warm length = 883
target length = 2927
LCP = 865
```

Still required before measured authority:

- exact raw L0 request SHA256;
- exact raw L1 request SHA256;
- exact raw LC request SHA256;
- deterministic proof that L0 is the frozen warm request, L1/LC are the frozen target request, and L1/LC differ only by `cache_prompt`;
- L0R remains defined as the exact L0 request bytes sent once on the fresh WR2 server.

Use only:

`e2d2c0d6-gemma4-kv-logical-prefix-request-identity-reconcile.py`

for this zero-GPU reconciliation.

Required terminal:

`LOGICAL_PREFIX_REQUEST_IDENTITY_RECONCILED`

That terminal explicitly does not authorize measured execution. If request identity is missing or ambiguous, stop with zero model/server/generation calls.

The static replacement measured runner:

`e2d2c0d6-gemma4-kv-logical-prefix-replacement-measured-run.py`

and its contract self-test are preparation artifacts only until this request-identity gate is reconciled into a fresh measured-attempt authority.

## Replacement measured attempt boundary

This authority prepares the replacement apparatus but does **not** itself authorize an immediate measured rerun of the consumed attempt.

A subsequent replacement measured handoff must explicitly bind:

- the new server SHA256 plus the marker-owning runtime-library SHA256 identities;
- exact applied patch SHA256 values;
- non-generative startup qualification PASS;
- frozen model/request/token identities;
- canonical shared-GPU guard;
- a fresh output root;
- a new attempt identity distinct from the consumed attempt.

Once the replacement L0 is submitted, it is again exactly-once and consumed on any later failure.

## Post-consumption dump-format repair

The replacement measured attempt authorized by `logical-prefix-kv-replacement-measured-authority-20260921-l0sha64` is terminal and consumed as `PROBE_EXERCISED_INCOMPLETE`.

It MUST NOT be retried or resumed.

The measured failure exposed a deterministic instrumentation-output defect:

- the logical-prefix hook fired and created `WR-P512/`;
- L0 completed HTTP 200 with the expected cache/prompt/predicted accounting;
- the metadata writer emitted literal `\\t` / `\\n` escape text instead of tab/newline control characters;
- `base.cells.tsv` therefore parsed as zero data rows;
- L1/L0R/LC were not submitted;
- no KV-state causal classification was produced.

Static inspection of the patch confirmed that its added C++ source contained doubled backslashes for tab/newline/NUL escape sequences.

Diagnostic-only repair commits:

```text
6c5230f4674f5006dd1fbd6728f5b88eb2b44ff3
  Fix logical-prefix dump metadata escapes

d2988ac2dd0d7c4268bfaf20144d5116eb426240
  Detect malformed C++ diagnostic escapes
```

Current repaired patch Git blob:

`16b3e79a6137e4f84ec5b47f6aff82d135bb1c53`

Current repaired patch self-test Git blob:

`631aa78914695090b744801a11ad574dcf4da573`

Remote byte-level read-back proves:

```text
doubled \\t occurrences in patch = 0
doubled \\n occurrences in patch = 0
doubled \\0 occurrences in patch = 0

single C++ \\t escapes are present
single C++ \\n escapes are present
single C++ \\0 escapes are present
```

The patch self-test now additionally requires:

- no doubled tab escape in added diagnostic code;
- no doubled newline escape in added diagnostic code;
- no doubled NUL escape in added diagnostic code;
- the cells TSV header uses actual C++ `\\t` / `\\n` escapes;
- the manifest TSV header uses actual C++ `\\t` / `\\n` escapes;
- row writers use C++ `'\\t'` / `'\\n'` character escapes.

This repair changes the physical instrumented artifact identity. Therefore:

- the prior pre-measured evidence root `/tmp/relaylm-logical-prefix-premeasured.4BYIKs/output` is historical only;
- server SHA `30d3f94f7335821a74828c243ab1dd315df9dc7a4c6df0cdff2f3ce1629dbaff` and its sibling-library SHAs belong to the consumed apparatus and MUST NOT be used for another measured attempt;
- the consumed measured authority is terminal;
- no current measured execution authority exists for the repaired patch.

Before any future measured request, the repaired patch requires a completely fresh pre-measured preparation transaction:

1. fresh isolated exact llama.cpp source checkout;
2. fresh patch SHA256 calculation;
3. fresh combined applied.patch SHA256;
4. fresh CUDA build;
5. fresh server/runtime-library SHA identities;
6. fresh binary provenance preflight;
7. fresh non-generative plain/probe startup qualification;
8. fresh canonical GPU guard observations;
9. zero generation / zero L0 during qualification.

Only after a new `LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY` result may management consider creating a distinct new measured-attempt authority.

The frozen request identities may be reused only after fresh read-back/revalidation of their exact raw SHA256 values; they are not regenerated or reconstructed.

## Observed post-repair pre-measured qualification pending exact reconciliation

A fresh post-repair preparation has now reported:

`LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY`

from:

`/tmp/relaylm-logical-prefix-premeasured.d3wSLc/output`

The reported run remained generation-free and L0-free, used the repaired logical-prefix dump instrumentation, produced a new server distinct from the consumed `30d3f94f...` apparatus, passed binary provenance, passed non-generative startup qualification, and cleanly acquired/released the canonical diagnostic GPU flock with exactly two idle observations.

During that run the protected v1 lane independently advanced via merged PR #3008 to:

```text
v1 head = 5461d0c6a134e2491cf4b07a36aa654389f9fe08
v1 tree = d902268113fe455c971e7a2e3e44259dfbb25178
```

PR #3008 concerns Hindsight retain acknowledgement durability and single-slot scheduling in the v1 scientific apparatus. It does not itself authorize, invalidate, or mutate this diagnostic llama.cpp apparatus. Current repository authority at execution time still wins.

The handoff report supplied abbreviated hashes for the newly built server/runtime libraries/patch. Therefore the report is not yet sufficient to mint a new measured-attempt authority.

Before any new measured authority is created, perform one zero-GPU exact reconciliation with:

`e2d2c0d6-gemma4-kv-logical-prefix-post-repair-reconcile.py`

and require its contract self-test:

`e2d2c0d6-gemma4-kv-logical-prefix-post-repair-reconcile-selftest.py`

Required self-test terminal:

`LOGICAL_PREFIX_POST_REPAIR_RECONCILE_SELFTEST_PASS`

Required reconciliation terminal:

`LOGICAL_PREFIX_POST_REPAIR_RECONCILED`

The reconciliation must bind, with complete 64-hex identities:

- repaired logical-prefix patch SHA256;
- aligned-reuse patch SHA256;
- combined applied.patch SHA256;
- new llama-server SHA256;
- new libllama-server-impl.so SHA256;
- new libllama.so SHA256;
- frozen model SHA256;
- exact startup canonical argv SHA256;
- base/SWA geometry;
- exact resource-guard evidence;
- exact two idle observations.

It must also freshly re-read and SHA256-verify the existing raw request artifacts from the prior request-reconciliation root and rerun deterministic request admission, without regenerating or reconstructing any request.

The previously reconciled request identities remain expected:

```text
warm tokens = c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2
target tokens = 549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e
L0 = 9120aed18e9aac20615cab2de00337eb9bf65edeb7249015c97d3c41d881e38d
L1 = d4deaa365324c5ca3c42eba4e6db9defe957a1cf06bbc08e9d3a01ba94ec0d1f
LC = 284630a2f90e364b5dd336d3d9fadc59ddd0fa072fbac7cc825200bef2e7af52
```

The zero-GPU reconciliation result explicitly does not authorize measured execution.

Until that reconciliation is complete:

- no current measured execution authority exists for the repaired apparatus;
- no L0/L1/L0R/LC may be sent;
- the consumed measured authority remains terminal and immutable.

## Post-repair reconciliation static-gate correction

The first invocation attempt of the post-repair exact reconciliation was stopped before the reconciliation helper itself was invoked.

Observed static result:

```text
LOGICAL_PREFIX_POST_REPAIR_RECONCILE_SELFTEST_FAIL
all_frozen_sha256_are_64_lower_hex = false
only_request_admission_subprocess = false
```

No reconciliation output root was created. No request admission, build, model load, server startup, GPU runtime, generation, L0/L1/L0R/LC, guard runtime, or measured execution occurred. The repaired pre-measured apparatus remains unconsumed and the consumed measured authority remains terminal.

The self-test failures were self-test defects:

1. the frozen upstream Git commit/tree object IDs are 40-hex Git object IDs, not SHA256 values;
2. the string-based subprocess check rejected the read-only string `shared-resource-guard` used to inspect already-recorded qualification evidence, even though the helper's only actual subprocess transition is request admission.

Diagnostic-only static repair:

```text
9835b92bf5162d7e29c0549d5288079f67744563
  Fix post-repair reconciliation self-test typing
```

The corrected self-test now requires:

- frozen Git commit/tree object IDs to match `[0-9a-f]{40}`;
- model/server/request SHA256 identities to match `[0-9a-f]{64}`;
- exactly one `subprocess.run` transition;
- that transition's first positional argument is the local `cmd` constructed for `e2d2c0d6-gemma4-kv-request-admission.py`;
- no `subprocess.Popen` transition.

This correction does not alter the reconciliation helper or any physical/runtime artifact.

A new zero-GPU reconciliation transaction may be attempted only from fresh repository authority and a fresh non-existing reconciliation output root. It is not a retry of a consumed measured attempt because the prior reconciliation helper invocation count was zero.

## Post-repair reconciliation input-location correction

A subsequent zero-GPU reconciliation transaction passed static compile and the corrected reconciliation self-test, then stopped inside the reconciliation helper before any request admission because its supplied pre-measured root was misspelled and the historical request-reconciliation root no longer existed.

Observed supplied pre-measured root:

`/tmp/relaylm-logical-prefix-premeasured.d3wSL6/output`

Correct qualified pre-measured root:

`/tmp/relaylm-logical-prefix-premeasured.d3wSLc/output`

The final character is lowercase `c`, not digit `6`.

The historical request-reconciliation root:

`/tmp/relaylm-logical-prefix-request-id.JWuNTY/reconciliation`

was also absent at the time of that transaction.

The transaction terminalized:

`LOGICAL_PREFIX_POST_REPAIR_NOT_RECONCILED`

with zero model loads, zero server startups, zero GPU runtime, zero generation, zero measured L0, and no measured authority creation. It does not consume the repaired apparatus or authorize any measured retry.

The post-repair reconciliation helper now supports three explicit request-provenance modes, in priority order:

1. an existing prior request-reconciliation root;
2. an existing measured preflight `bound-identity.json` containing the original raw request paths and SHA256 identities;
3. explicitly supplied bounded search roots using the repository-owned artifact locator.

The known consumed measured preflight binding is:

`/tmp/relaylm-logical-prefix-preflight.enkGnB/bound-identity.json`

When present, it is preferred over filesystem rediscovery. Its request paths must be treated only as provenance pointers; each pointed raw file must still exist and must fresh-hash to the frozen expected SHA256 before request admission is rerun.

Only if both the prior reconciliation root and measured preflight binding are absent may bounded artifact rediscovery be used. Search roots must be explicitly supplied; the helper does not implicitly scan all of `/tmp`.

All paths converge on the same fixed request SHA identities and require `REQUEST_ADMISSION_PASS`. No request may be regenerated or reconstructed.

Current corrected helper/self-test add only zero-GPU request-provenance recovery. They do not add any model/server/guard/measured runtime transition.

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

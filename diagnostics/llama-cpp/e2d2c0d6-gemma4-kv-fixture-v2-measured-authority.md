# Gemma 4 fixture-v2 retained-prefix KV measured-attempt authority

Diagnostic only. This authority is independent of the protected v1 scientific campaign and independent of the historical consumed request subject.

## Status

`TERMINAL_CONSUMED_PREFIX_KV_GENERATION_DIFFERS`

The single authorized fixture-v2 measured attempt was executed exactly once and is permanently consumed. It MUST NOT be retried, replayed, resumed, reseeded, repaired in place, or replaced under this authority.

Authority generation:

`logical-prefix-kv-fixture-v2-measured-authority-20260922-f6b67141`

Attempt identity:

`logical-prefix-kv-fixture-v2-20260922-f6b67141`

This is a distinct measured subject based on the repository-owned fixture v2. It is not a retry, replay, resume, repair-in-place, or continuation of the historical consumed request subject.

Fresh repository authority at execution time always wins over this snapshot.

## Code authority at authoring

```text
diagnostic code head before this authority commit =
4ce76b0d36ea6b4e882788d7e246da953975eb8d

diagnostic code tree =
e280131c783cd56a02b551ce55877518fdcb3cd2

v1 head =
c694bc185bd1e00d9c410f2b0d64b0310c2323bf

v1 tree =
9284f97707c0b62a38c9ae9d18b703d3f29a2209

open PRs targeting v1 = 0
open diagnostic-related PRs = 0
ruleset 20931403 = active
```

Relevant code blobs:

```text
fixture-v2 measured runner =
63c4281430496647f68a76ab3e2ed1ea3b46e3db

fixture-v2 runner self-test =
b9cfc6a3a45f52aafcabd2a9a149b8f57d62a28a

fixture-v2 execute-once wrapper =
5a44bea6372cc228c757f67bfccc3a531ac2b338

fixture-v2 wrapper self-test =
c0af1ca2a401a6638aacee330e1fcff0697bda79
```

The historical consumed measured authority remains terminal:

`TERMINAL_CONSUMED_PROBE_EXERCISED_INCOMPLETE`

It must not be executed or reused.

## Repository-owned request subject

Fixture authority status:

`FIXTURE_V2_COMMITTED`

Fixture commit:

`58d3c1e9b8cf973648be1aeb8a8b12429a69d088`

Fixture subtree:

`455d94850515c70995addc6c1c446ba738a01474`

Fixture path:

`diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2/`

Exact fixture geometry:

```text
warm length = 883
target length = 2927
LCP = 865
effective aligned reuse = 512
target suffix source offset = 883
target suffix length = 2062
```

Exact committed SHA256 identities:

```text
source-corpus.txt =
8f5e83bc034a7678ecce6ddc25dc5507ed726b849f9ecfaa19865b9ba885459a

tokenizer-request.json =
cd55b727276462f2725e1a13b0f217bb35f0e7a097504f082473200fa2bdb66e

tokenizer-response.json =
e46ec4970db8dfeca4f7f0a7133da4c5eba75c20815dfbdcf446912310ebe4ac

warm.tokens.json =
cc42e325d85ed559835225b53152446bc405b2d166c10a3e16b07c7859bf7f27

target.tokens.json =
8c05cf7a6d11d684be091c49a9f9d76201274e1efad31c9b19234cb4ec985730

L0.request.json =
d777877485b3307d8ee76e6b6df783d00b4302bb700c405ac5cbf2f6d7344f5d

L1.request.json =
b7e482874b1a3c8b80136e2d2e8a76594c318230f5f8bae4171d2f0efff465eb

LC.request.json =
63afb2a44ea12f14377ba52348616a0bd8ac3ebdd65d81d1a3ede1c4c2c64043

manifest.json =
d08e6aa1c4a9c263f5b3e0d1911f3117335f4dfdc267d9a2d5ea187401c92e3d
```

Exact Git blob identities:

```text
source-corpus.txt =
7ad9ae44ee56f7338cdc8594ed5872e9d1773001

tokenizer-request.json =
7bf97501c02a813c3ae8b608c1e8f82c869918dd

tokenizer-response.json =
247a2a285877b217f2f6132f3e7edf5629b1658f

warm.tokens.json =
c83fffa75bf006804131eb9dd9ad84dfa9f46d1b

target.tokens.json =
f127cf2bec7f217f27a5c04cb059ddb9ccd039bd

L0.request.json =
a4d7d31b268cb173a93ff32c87184dc9a16998e4

L1.request.json =
07dfdc83366dd5ba57e0c9af5571493dbe9ed6ca

LC.request.json =
5534a9dcb9da289b0448a139b77dcf94287fdfd7

manifest.json =
ece1a792d3ec60e594131c52d5f0f4900298db04
```

Request semantics:

```text
L0 prompt = exact committed warm token array
L1 prompt = exact committed target token array
LC prompt = exact committed target token array

L0 cache_prompt = true
L1 cache_prompt = true
LC cache_prompt = false

n_predict = 1
temperature = 0
stream = false
n_probs = 20

L1 and LC differ only by cache_prompt
```

L0R is defined as sending the exact committed raw bytes of `L0.request.json` once on the fresh WR2 server.

The runner accepts no request-file CLI arguments. It resolves only the committed fixture directory and validates the exact nine-file set, SHA256 identities, Git blob identities, and fixture geometry before measured inference.

## Fresh qualified physical apparatus

Bound pre-measured evidence root:

`/tmp/relaylm-kv-v2-premeasured.kq8VQ5/output`

Required terminal:

`LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY`

Frozen source identity:

```text
llama.cpp head =
e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d

llama.cpp tree =
6d39fd93dc91fc0a4bc86dffe9782d4f26318004
```

Patch/build identities:

```text
aligned patch SHA256 =
cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a

repaired logical-prefix patch SHA256 =
d62810fdc645cbb011c52047e9ba9227b1d6c29fafc0bac0e7cf659f6104e4c8

combined applied.patch SHA256 =
2f3829164ae8dffce6054681fbcef3f674fb901d37a2ffc383a91f3c867f7737
```

Runtime closure:

```text
llama-server SHA256 =
f6b671417ac9b6c7b4e00da95980caf828b8d63133ca61fdad60153b67a39e22

libllama-server-impl.so SHA256 =
7456ded50dca4f6ad5f53dd9e178d16954e2c9134ee912c5ea8ed3760db3735a

libllama.so SHA256 =
178b81207d10e053490627e2755a61069ae912053cf0abcffa258989bac0528e

model SHA256 =
c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed
```

Startup identity:

```text
canonical argv SHA256 =
5d9d486e67aa19e1b26ff00c33f50c30b57a41788c212bcccc2ab0bf4f992706

n_seq_max = 1
n_ctx = 8192
n_batch = 512
n_ubatch = 512
flash_attn = enabled
base KV = 8192
SWA KV = 1536
plain/probe geometry equal
probe startup dump = none
```

Binary provenance:

`LOGICAL_PREFIX_BINARY_PREFLIGHT_PASS`

Startup qualification:

`LOGICAL_PREFIX_STARTUP_QUALIFIED`

All required runtime markers must remain present and `forbidden_old_marker_present=false`.

The pre-measured qualification performed zero generation requests and zero L0/L1/L0R/LC requests.

## Only authorized measured entrypoint

The only authorized measured entrypoint is:

`diagnostics/llama-cpp/e2d2c0d6-gemma4-kv-fixture-v2-execute-once.py`

The inner runner:

`diagnostics/llama-cpp/e2d2c0d6-gemma4-kv-fixture-v2-measured-run.py`

must not be invoked manually.

The historical replacement runner/wrapper must not be invoked.

## Required static gate

Immediately before invoking the execute-once wrapper, from a fresh isolated diagnostic checkout:

1. reacquire current diagnostic HEAD/tree;
2. reacquire current v1 HEAD/tree;
3. confirm no conflicting/newer measured authority or terminal exists;
4. confirm open PR state and ruleset 20931403;
5. read this authority from the current diagnostic branch;
6. confirm primary checkout remains untouched;
7. Python-compile:
   - fixture-v2 measured runner;
   - fixture-v2 runner self-test;
   - fixture-v2 execute-once wrapper;
   - fixture-v2 wrapper self-test;
   - fixture-v2 admission checker;
   - KV digest comparator;
   - canonical resource guard;
   - resource-guard self-test;
8. run the fixture-v2 runner self-test;
9. run the fixture-v2 wrapper self-test;
10. run the canonical resource-guard self-test.

Required terminals:

```text
LOGICAL_PREFIX_FIXTURE_V2_RUNNER_SELFTEST_PASS
LOGICAL_PREFIX_FIXTURE_V2_WRAPPER_SELFTEST_PASS
LOGICAL_PREFIX_RESOURCE_GUARD_SELFTEST_PASS
```

The runner self-test must fresh-read the committed fixture and validate its exact SHA256/Git-blob identities and geometry.

Any static failure must stop before wrapper invocation.

No repair/retry in that transaction.

## Wrapper pre-L0 reconciliation

The wrapper must, before entering the measured GPU guard:

- validate the bound pre-measured root;
- validate source/tree;
- validate all three patch/build identities;
- validate new server/runtime-library/model SHA256 identities;
- validate binary preflight;
- validate all required runtime markers;
- validate forbidden marker absence;
- validate exact startup canonical argv SHA256;
- validate base KV 8192 / SWA KV 1536;
- validate prior pre-measured guard evidence and exactly two idle observations;
- require fixture commit `58d3c1e9...` to be an ancestor of current HEAD;
- require current HEAD's fixture subtree to equal `455d9485...`;
- rerun fixture-v2 admission against the committed fixture;
- verify the live model SHA256.

Any mismatch before the measured child invocation is:

`PROBE_NOT_EXERCISED`

with:

```text
measured_l0_submitted = false
measured_attempt_consumed = false
measured_execution_authorized_by_this_result = false
```

Stop and return to management. Do not invoke the wrapper again under this authority.

## Shared local-GPU boundary

The execute-once wrapper must run the measured runner only as the child of:

`e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py`

Canonical resource:

```text
resource key = llama-cpp:local-gpu
lock root = /tmp/relaylm/physical/locks
lock = /tmp/relaylm/physical/locks/a820834e5681ba28.lock
```

Before the measured child is invoked, require exactly two external-idle observations five seconds apart for:

- `llama-server`;
- `llama-cli`;
- `llama-run`;
- `127.0.0.1:1234`.

Socket semantics remain fail-closed.

The diagnostic guard must not create or touch scientific campaign queue/receipt/lease/spend state.

## Runtime

Every measured server lifetime uses exactly:

```text
context = 8192
parallel = 1
gpu layers = 999
context shift = disabled
n_batch = 512
n_ubatch = 512
flash attention = ON
log verbosity = 4
temperature = 0
generated tokens per request = 1
compact SWA
```

FA OFF is forbidden.

## Exactly-once measured sequence

After all pre-L0 checks pass:

```text
WR fresh server:
  L0 exactly once
  require WR-P512
  L1 exactly once
  require WR-R512

WR2 fresh server:
  L0R exactly once
  require WR2-P512

C fresh server:
  LC exactly once
  require C-P512
```

Required request accounting:

```text
L0:
cache_n = 0
prompt_n = 883
predicted_n = 1

L1:
cache_n = 512
prompt_n = 2415
predicted_n = 1

L0R:
cache_n = 0
prompt_n = 883
predicted_n = 1

LC:
cache_n = 0
prompt_n = 2927
predicted_n = 1
```

## Required KV dump validation

Required dump roots:

- `WR-P512/`
- `WR-R512/`
- `WR2-P512/`
- `C-P512/`

Every point must pass manifest-driven completeness validation:

- base and SWA cells files contain exactly 512 data rows;
- positions exactly 0..511;
- `v_trans=0`;
- base KV size 8192;
- compact SWA size positive and below base;
- all corresponding observations share equal geometry;
- manifest rows report 512 rows and positive row bytes;
- all participating layers have both K and V;
- every payload size is exact;
- actual payload set exactly equals manifest-derived expected set.

A partial dump must not be interpreted as a KV mismatch.

## Primary classifications

A complete attempt must end in exactly one:

### `PREFIX_DUMP_NOT_REPRODUCIBLE`

WR-P512 differs from WR2-P512.

### `PREFIX_KV_GENERATION_DIFFERS`

WR-P512 equals WR2-P512 but differs from C-P512.

### `RETAINED_PREFIX_KV_MUTATED_BY_REUSE`

WR-P512 == WR2-P512 == C-P512, but WR-R512 differs.

### `PREFIX_KV_IDENTICAL_THROUGH_REUSE`

All four retained-prefix observations are byte-identical.

The runner also retains the fixture-v2 L1-vs-LC API comparison, but fixture-v2 numerical values must not be compared as if they were historical g1/g2 values.

## Consumption boundary

This authority permits at most one invocation of the execute-once wrapper.

Before L0 submission, a failure is unconsumed:

```text
PROBE_NOT_EXERCISED
measured_l0_submitted = false
measured_attempt_consumed = false
```

Nevertheless, stop and return to management. Do not automatically invoke the wrapper again.

At the L0 boundary, consumption is conservative.

The measured runner writes:

`server-WR/L0.request.json`

before performing the HTTP POST.

If the measured runner exits without `terminal.json`, the wrapper must classify from this record:

```text
L0 request record absent
  -> PROBE_NOT_EXERCISED
  -> measured_attempt_consumed = false

L0 request record present
  -> PROBE_EXERCISED_INCOMPLETE
  -> measured_attempt_consumed = true
  -> rerun_authorized = false
```

Once L0 crosses this boundary, any later failure is terminal and consumed.

No retry, replay, resume, reseed, fallback, repair, or replacement attempt is authorized after consumed status.

A complete four-point classification is also consumed.

## Terminal execution result

Observed terminal classification:

`PREFIX_KV_GENERATION_DIFFERS`

Execution repository identity:

```text
diagnostic head/tree =
651a710989b81ceba2dcc055c5104967e7080239
5bf10780adf498183d137454081886d05d6c141a

post-run diagnostic head/tree =
651a710989b81ceba2dcc055c5104967e7080239
5bf10780adf498183d137454081886d05d6c141a

v1 head/tree at terminal read-back =
671893aafcb353395e8f4dcb3849c2a678e2930e
eecc3e5d96480eec8f1ffba60bc1561b89e46076
```

Measured evidence roots:

```text
preflight =
/tmp/relaylm-kv-v2-measured.2DZbPg/preflight

measured output =
/tmp/relaylm-kv-v2-measured.2DZbPg/measured-output
```

Exactly-once accounting:

```text
execute-once wrapper invocations = 1
direct inner-runner invocations = 0
measured runner guard-child invocations = 1
fresh idle observations = 2
retry/replay/resume/reseed/fallback/repair = 0
FA-OFF arms = 0
scientific campaign interaction = 0
campaign queue/receipt/spend mutation = 0
historical runner/wrapper invocation = 0
```

Request order and accounting:

```text
L0  : cache_n=0   prompt_n=883  predicted_n=1
L1  : cache_n=512 prompt_n=2415 predicted_n=1
L0R : cache_n=0   prompt_n=883  predicted_n=1
LC  : cache_n=0   prompt_n=2927 predicted_n=1

order = L0 -> L1 -> L0R -> LC
request count = 4
```

The exact consumed L0 raw request SHA256 was:

`d777877485b3307d8ee76e6b6df783d00b4302bb700c405ac5cbf2f6d7344f5d`

The pre-POST `server-WR/L0.request.json` record exists, therefore this attempt is consumed independent of the complete terminal classification.

All four logical-prefix dumps passed completeness and equal-geometry validation:

```text
WR-P512  = PASS
WR-R512  = PASS
WR2-P512 = PASS
C-P512   = PASS

base rows = 512
SWA rows = 512
logical positions = 0..511
v_trans = 0
base KV = 8192
SWA KV = 1536
base manifest layer rows = 16
SWA manifest layer rows = 80
all K/V pairs present
payload sets exact
payload sizes exact
```

KV relation:

```text
W  = WR-P512
R  = WR-R512
W2 = WR2-P512
C  = C-P512

W == W2
W == R
W != C

W_vs_C different payload files = 96
W_vs_C missing payload files = 0
first mismatch = swa.layer-0.K.bin
```

Therefore the complete discriminator is:

`PREFIX_KV_GENERATION_DIFFERS`

This directly rejects `RETAINED_PREFIX_KV_MUTATED_BY_REUSE` for this fixture/physical-apparatus subject: the retained prefix after reuse is byte-identical to the warm prefix, and the independent warm replay is also byte-identical.

The fixture-v2 API comparison observed equal first generated token ID 6571 (`" memory"`) for L1 and LC, while the top-N probability structures were not byte-identical and had top-N intersection 16. These values belong only to fixture v2 and must not be substituted for historical g1/g2 values.

## Post-terminal decode-segmentation interpretation

Fresh static inspection of exact llama.cpp source and the diagnostic hook establishes an important confounder for interpreting `W != C`.

The server builds prompt batches up to `n_batch=512`, but completion tasks using SWA checkpointing deliberately split near the prompt end. The exact checkpoint rule uses offsets:

```text
4 + n_ubatch = 516 -> min(n_batch, 516) = 512
4                         -> 4
```

and breaks when:

`task.n_tokens == prompt.n_tokens + n_last`

For fixture-v2 warm length 883:

```text
883 - 512 = 371
```

so the first warm prompt decode stops after logical positions 0..370 (371 tokens).

The following warm decode advances from position 371 to the next checkpoint at:

```text
883 - 4 = 879
```

which is 508 tokens (positions 371..878). Logical position 511 is therefore observed after this second physical decode.

Consequently `WR-P512` / `WR2-P512` contain logical positions 0..511 generated across two physical prompt decodes:

```text
371-token decode
then
508-token decode
```

By contrast, for cold target length 2927 the first checkpoint boundary is:

```text
2927 - 512 = 2415
```

so the first cold prompt decode is the ordinary full 512-token batch, positions 0..511. `C-P512` is therefore captured after one 512-token physical decode.

Thus the complete measured result proves that the stored logical-prefix KV bytes differ between these two prompt-processing histories, but it does NOT by itself prove future-token dependence of KV generation. Physical decode segmentation differs between W/W2 and C.

Because `W == W2` and `W == R`, reproducibility and retained-prefix stability are proven for the warm segmentation. The next causal discriminator should equalize physical decode segmentation for warm and cold generation before attributing `W != C` to prompt suffix/context semantics.

No further measured execution is authorized by this terminal authority.

## Campaign separation

Must remain zero:

- protected v1 mutation;
- fixture mutation;
- scientific `--execute`;
- #2965 campaign invocation;
- campaign queue/receipt/lease/spend mutation;
- #2964 mutation;
- historical measured runner/wrapper invocation;
- FA-OFF arm;
- production/cache-policy mutation;
- primary dirty checkout mutation;
- upstream submission.

## Authorized invocation shape

Use fresh nonexistent preflight/output roots and three fresh distinct loopback ports:

```bash
python3 \
  diagnostics/llama-cpp/e2d2c0d6-gemma4-kv-fixture-v2-execute-once.py \
  --model <existing-frozen-model-path> \
  --preflight-root <fresh-nonexistent-preflight-root> \
  --out-root <fresh-nonexistent-measured-output-root> \
  --port-wr <fresh-port-1> \
  --port-wr2 <fresh-port-2> \
  --port-c <fresh-port-3>
```

Invoke this command at most once.

Do not invoke the inner measured runner separately.

## Required terminal report

After the single wrapper invocation, fresh-read repository authority and report:

- authority generation;
- attempt ID;
- execution diagnostic HEAD/tree;
- post-run diagnostic HEAD/tree;
- current v1 HEAD/tree;
- open PR/ruleset state;
- primary checkout unchanged;
- preflight root;
- measured output root;
- wrapper invocation count;
- measured runner invocation count;
- guard acquisition/release;
- exactly two fresh idle observations;
- fixture commit/subtree read-back;
- fixture admission result;
- server/runtime-library/model SHA read-back;
- submitted request order/count;
- exact L0 request SHA read-back;
- L0 consumed status;
- server lifetime attempts/completions;
- four dump existence/validation states;
- KV geometry consistency;
- KV comparison;
- first mismatch localization if applicable;
- fixture-v2 L1-vs-LC API comparison;
- retry/replay/resume/reseed/fallback/repair counts;
- FA-OFF count;
- scientific campaign interaction count;
- campaign queue/receipt/spend mutation count;
- exact terminal classification.

Once the wrapper has been invoked once, stop regardless of result.

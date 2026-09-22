# Gemma 4 fixture-v2 segmentation-control authority

Diagnostic only. This authority prepares a new derived cold-control request. It does not authorize model execution or measured KV generation.

## Status

`SEGMENTATION_CONTROL_COMMITTED`

## Parent terminal result

The prior fixture-v2 measured authority is terminal and consumed:

`TERMINAL_CONSUMED_PREFIX_KV_GENERATION_DIFFERS`

Measured relation:

```text
W  = WR-P512
R  = WR-R512
W2 = WR2-P512
C  = C-P512

W == W2
W == R
W != C
```

That result rules out retained-prefix mutation for the measured subject, but it does not yet isolate why fresh cold generation differs.

## Identified physical-segmentation confounder

Exact llama-server source at:

`e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`

builds prompt batches up to `n_batch=512`, while completion/SWA checkpointing breaks near the prompt end at offsets:

```text
min(n_batch, 4 + n_ubatch) = 512
min(n_batch, 4)            = 4
```

For the committed warm prompt length 883:

```text
883 - 512 = 371
883 -   4 = 879
```

Therefore warm physical prompt processing is:

```text
decode 1: positions 0..370   = 371 tokens
decode 2: positions 371..878 = 508 tokens
decode 3: positions 879..882 = 4 tokens
```

The logical-prefix diagnostic sees position 511 during decode 2.

For the prior cold target length 2927, the first checkpoint boundary is 2415, so positions 0..511 are produced in one ordinary 512-token decode.

Thus W and C had equal logical prefix tokens/positions but different physical decode segmentation.

## Control hypothesis

Create a new cold request with total length 883:

`C883 = committed target.tokens.json[0:883]`

The committed warm/target LCP is 865, therefore:

```text
len(warm) = 883
len(C883) = 883
LCP(warm, C883) = 865
warm != C883
```

Both fresh warm and fresh C883 requests then have identical total prompt length and identical checkpoint-driven segmentation:

```text
371 -> 508 -> 4
```

while still diverging after position 864.

The causal discriminator becomes:

```text
W == C883
  -> prior W != C2927 is explained by physical decode-segmentation dependence
     at the byte-exact KV level for this apparatus.

W != C883
  -> a difference remains even after total length and physical segmentation
     are equalized; suffix/content-path or another uncontrolled factor remains.
```

This authority does not predetermine which result will occur.

## Parent fixture authority

Parent fixture:

`diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2/`

Parent fixture commit:

`58d3c1e9b8cf973648be1aeb8a8b12429a69d088`

Parent fixture subtree:

`455d94850515c70995addc6c1c446ba738a01474`

Parent identities:

```text
warm.tokens.json SHA256 =
cc42e325d85ed559835225b53152446bc405b2d166c10a3e16b07c7859bf7f27

target.tokens.json SHA256 =
8c05cf7a6d11d684be091c49a9f9d76201274e1efad31c9b19234cb4ec985730
```

The parent fixture must not be modified.

## Repository-owned preparation tooling

Use only:

```text
e2d2c0d6-gemma4-kv-fixture-v2-segmentation-control-materialize.py
e2d2c0d6-gemma4-kv-fixture-v2-segmentation-control-selftest.py
```

Required self-test terminal:

`LOGICAL_PREFIX_SEGMENTATION_CONTROL_SELFTEST_PASS`

Required materializer terminal:

`LOGICAL_PREFIX_SEGMENTATION_CONTROL_MATERIALIZED`

## Derived control request

The materializer must create exactly:

```text
C883.tokens.json
C883.request.json
manifest.json
```

C883 request semantics:

```text
prompt = exact C883 token array
cache_prompt = false
n_predict = 1
temperature = 0
stream = false
n_probs = 20
```

The manifest must bind:

- parent fixture identities;
- control SHA256 and byte counts;
- warm/control LCP = 865;
- control length = 883;
- expected physical segmentation 371/508/4;
- position-511 decode ordinal = 2.

## Hard boundary

This preparation transaction is zero-GPU and zero-model.

Must remain zero:

```text
build
model load
llama-server startup
GPU guard acquisition
/tokenize
generation
L0
L1
L0R
LC
measured wrapper
measured runner
scientific campaign interaction
v1 mutation
```

Do not use historical measured evidence as a source for request bytes.

Do not alter the parent fixture.

## Repository durability

After self-test and materialization pass, commit the three derived files under:

`diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2-segmentation-control/`

Commit only that directory.

Before commit/push:

- fresh-read current diagnostic remote HEAD;
- require no conflicting existing control directory;
- do not rebase/merge/force-push on drift;
- if drift occurs, preserve local evidence and stop.

Required successful terminal:

`LOGICAL_PREFIX_SEGMENTATION_CONTROL_COMMITTED`

Success still does not authorize GPU execution.

## Committed control identity

Control commit:

`ccf9e78a89d170ae43e6ccfa6aa0788bd9a6cacc`

Commit tree:

`023e797dc6c7357a8465f919973d6aa10f26772b`

Control subtree:

`ac26ba25c3b88cbd9586ec009eeefe66004e2cb5`

Repository path:

`diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2-segmentation-control/`

Fresh remote read-back confirms exactly three files:

```text
C883.tokens.json
C883.request.json
manifest.json
```

SHA256 identities:

```text
C883.tokens.json =
1b3796b5dbec09d1fe2188d0bce1a9a9e8be316943d0e415582dde0a0ff3a92a

C883.request.json =
1e490f609ac0b844521784cd4603ea79a9c5ab0b199117e4395c4a8cf2efa47c

manifest.json =
aa23a149d9d54137f8a455034c5048c8b7d8e03a4d12d3f33000c66aece8b86b
```

Git blob identities:

```text
C883.tokens.json =
1d313fa510cb75465380646fc26f63811c3cb683

C883.request.json =
b2bfbc61558b7158394693c2df29de31af35d794

manifest.json =
39a230ddaa21e5c13dc80d9707c8f71c1bd8d476
```

Fresh semantic read-back confirms:

```text
len(C883) = 883
LCP(warm, C883) = 865
cache_prompt = false
n_predict = 1
temperature = 0
stream = false
n_probs = 20
expected segmentation = 371 -> 508 -> 4
logical position 511 decode ordinal = 2
```

This committed control is now the sole authority for the segmentation-controlled cold request.

The preparation transaction was zero-build, zero-model, zero-server, zero-GPU, zero-generation, zero-L0, and did not mutate v1 or the scientific campaign.

The prior measured-authority generation without the `-c883sha64` suffix failed its static runner self-test before wrapper invocation because its C883 token SHA binding was 63 hexadecimal characters. It was never exercised and is superseded. The current route below is the corrected generation.

## Current post-hoc route

The segmentation-control measured attempt has been consumed and terminalized:

`TERMINAL_CONSUMED_PROBE_EXERCISED_INCOMPLETE`

No measured rerun is authorized.

The current route is zero-GPU forensic reconciliation of the already-produced W/W2/C883 evidence:

`e2d2c0d6-gemma4-kv-segmentation-control-posthoc-authority.md`

Required status:

`SEGMENTATION_CONTROL_POSTHOC_RECONCILIATION_READY`

Source measured evidence:

```text
/tmp/relaylm-segmentation-control-attempt.7bkdqi/measured-output
```

The forensic reconciler must not start a server, call HTTP, acquire the GPU guard, invoke subprocesses, mutate measured evidence, or authorize a rerun.

The original measured terminal remains authoritative as `PROBE_EXERCISED_INCOMPLETE`; any post-hoc derived KV classification is recorded separately.


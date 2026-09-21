# Gemma 4 fixture-v2 segmentation-control authority

Diagnostic only. This authority prepares a new derived cold-control request. It does not authorize model execution or measured KV generation.

## Status

`SEGMENTATION_CONTROL_PREPARATION_REQUIRED`

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

## After durable control commit

Management must fresh-read and bind:

- control commit/tree/subtree;
- C883 tokens SHA256/Git blob;
- C883 request SHA256/Git blob;
- control manifest SHA256/Git blob.

Only then may a distinct segmentation-controlled measured authority be created.

That future measurement should compare fresh warm P512 against fresh C883 P512 under an equal physical segmentation contract. It must not reuse or replay the consumed fixture-v2 measured attempt.

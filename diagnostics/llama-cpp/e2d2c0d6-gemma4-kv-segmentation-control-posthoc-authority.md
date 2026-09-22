# Gemma 4 KV segmentation-control post-hoc reconciliation authority

Diagnostic only.

## Status

`TERMINAL_SEGMENTATION_CONTROL_POSTHOC_RECONCILED_KV_IDENTICAL`

This authority permits exactly one zero-GPU forensic reconciliation over the already-consumed measured evidence.

It does not authorize any model/server/GPU execution and does not authorize a measured retry.

## Consumed source attempt

Authority generation:

`logical-prefix-kv-segmentation-control-measured-authority-20260922-6802c20c-c883sha64`

Attempt:

`logical-prefix-kv-segmentation-control-20260922-6802c20c`

Consumed measured authority status:

`TERMINAL_CONSUMED_PROBE_EXERCISED_INCOMPLETE`

Measured evidence root:

`/tmp/relaylm-segmentation-control-attempt.7bkdqi/measured-output`

Preflight root:

`/tmp/relaylm-segmentation-control-attempt.7bkdqi/preflight`

The measured attempt MUST NOT be rerun.

## Why post-hoc reconciliation is permitted

The measured transaction successfully completed all three physical requests:

```text
W
W2
C883
```

Each request returned HTTP 200 with:

```text
cache_n = 0
prompt_n = 883
predicted_n = 1
```

and each individual logical-prefix dump validated successfully:

```text
W-P512
W2-P512
C883-P512
```

The transaction failed only after all three dumps existed, when the inherited cross-observation geometry helper required obsolete historical names:

```text
WR-P512
WR-R512
WR2-P512
C-P512
```

The exact failure was:

`missing dump geometry records: ['WR-P512', 'WR-R512', 'WR2-P512', 'C-P512']`

Therefore no additional physical observation is needed to answer the intended comparison, provided the existing evidence is revalidated read-only.

## Forensic tooling

Use only:

```text
e2d2c0d6-gemma4-kv-segmentation-control-posthoc-reconcile.py
e2d2c0d6-gemma4-kv-segmentation-control-posthoc-selftest.py
```

Required self-test terminal:

`SEGMENTATION_CONTROL_POSTHOC_SELFTEST_PASS`

The reconciler may import read-only validation/comparison helpers from the consumed runner.

It MUST NOT:

- start a server;
- call HTTP;
- acquire the GPU guard;
- invoke subprocesses;
- mutate the consumed measured evidence;
- overwrite the consumed `terminal.json`;
- modify fixture/control files;
- authorize a rerun.

## Required source evidence

The consumed measured terminal must prove:

```text
primary_classification = PROBE_EXERCISED_INCOMPLETE
measured_w_submitted = true
measured_attempt_consumed = true
rerun_authorized = false
submitted_requests = ["W", "W2", "C883"]
request_count_submitted = 3
```

Its failure reason must contain all four obsolete geometry names.

## Request evidence

Required exact raw SHA256:

```text
W request =
d777877485b3307d8ee76e6b6df783d00b4302bb700c405ac5cbf2f6d7344f5d

W2 request =
d777877485b3307d8ee76e6b6df783d00b4302bb700c405ac5cbf2f6d7344f5d

C883 request =
1e490f609ac0b844521784cd4603ea79a9c5ab0b199117e4395c4a8cf2efa47c
```

Each response must still prove:

```text
HTTP 200
cache_n = 0
prompt_n = 883
predicted_n = 1
```

## Dump revalidation

All three directories:

```text
kv/W-P512
kv/W2-P512
kv/C883-P512
```

must independently re-pass the existing complete dump validator:

- 512 base rows;
- 512 SWA rows;
- logical positions 0..511;
- v_trans=0;
- base KV=8192;
- 0 < SWA KV < base KV;
- complete layer K/V pairs;
- exact payload sizes;
- exact payload file set.

Then the post-hoc three-point geometry join requires equal:

```text
kv_size
v_trans
logical_rows
layer_count
```

for base and SWA across all three observations.

## Derived comparison

Only after the above validation may the reconciler compute:

```text
W vs W2 payload SHA256 equality
W vs C883 payload SHA256 equality
layout metadata equality
first mismatch
W vs C883 API first-token/top-N comparison
```

Allowed derived classifications:

```text
SEGMENTATION_CONTROL_WARM_NOT_REPRODUCIBLE
SEGMENTATION_CONTROL_KV_IDENTICAL
SEGMENTATION_CONTROL_KV_DIFFERS
```

The post-hoc success terminal is:

`SEGMENTATION_CONTROL_POSTHOC_RECONCILED`

and must separately record the derived measured classification.

The original measured terminal remains `PROBE_EXERCISED_INCOMPLETE`. Do not rewrite history by replacing it.

## Interpretation

If derived:

`SEGMENTATION_CONTROL_WARM_NOT_REPRODUCIBLE`

then no causal conclusion about C883 is permitted.

If derived:

`SEGMENTATION_CONTROL_KV_IDENTICAL`

then the existing consumed evidence supports that W and C883 are byte-identical once total prompt length / expected checkpoint segmentation are equalized. For this subject/apparatus, the prior W-vs-C2927 byte difference is attributable to the unequal physical prompt-processing history that was removed by this control.

If derived:

`SEGMENTATION_CONTROL_KV_DIFFERS`

then a byte-level prefix KV difference remains even after total length and expected segmentation are equalized; suffix/content-path or another uncontrolled factor remains.

## Terminal forensic result

The authorized zero-GPU reconciliation completed successfully.

Post-hoc terminal:

`SEGMENTATION_CONTROL_POSTHOC_RECONCILED`

Derived measured classification:

`SEGMENTATION_CONTROL_KV_IDENTICAL`

The original measured attempt remains unchanged and consumed:

```text
source measured terminal SHA256 =
747a62fe3a16d7d6e524169ec2bc1901799e8ca7baf36de7de722f1ad8d84ad0

source measured terminal =
PROBE_EXERCISED_INCOMPLETE

measured_attempt_consumed = true
rerun_authorized = false
```

No measured evidence was replayed or regenerated.

Request read-back:

```text
W request SHA256 =
d777877485b3307d8ee76e6b6df783d00b4302bb700c405ac5cbf2f6d7344f5d

W2 request SHA256 =
d777877485b3307d8ee76e6b6df783d00b4302bb700c405ac5cbf2f6d7344f5d

C883 request SHA256 =
1e490f609ac0b844521784cd4603ea79a9c5ab0b199117e4395c4a8cf2efa47c
```

All three saved HTTP results independently proved:

```text
HTTP 200
cache_n = 0
prompt_n = 883
predicted_n = 1
```

All three dumps revalidated successfully:

```text
W-P512    = PASS
W2-P512   = PASS
C883-P512 = PASS

base rows = 512
SWA rows = 512
logical positions = 0..511
v_trans = 0
base KV = 8192
SWA KV = 1536
payload files = 96 per dump
complete K/V pairs = true
payload set/sizes exact = true
```

Three-point geometry consistency:

```text
base:
  kv_size = 8192
  v_trans = 0
  logical_rows = 512
  layer_count = 8

SWA:
  kv_size = 1536
  v_trans = 0
  logical_rows = 512
  layer_count = 40
```

Byte-level KV comparison:

```text
W vs W2:
  equal = true
  different payload files = 0
  missing payload files = 0

W vs C883:
  equal = true
  different payload files = 0
  missing payload files = 0

W vs W2 layout metadata:
  equal = true

W vs C883 layout metadata:
  equal = true

first mismatch = null
```

API output comparison remained different, as expected for prompts that diverge after the shared prefix:

```text
first token equal = false

W first token:
  id = 7501
  token = " sequence"

C883 first token:
  id = 236819
  token = "9"

top-N exact equal = false
top-N intersection = 8
maximum absolute logprob delta = 6.460263252258301
max-delta token id = 236770
```

This separates prefix-KV identity from final request output identity: equal prefix KV through logical position 511 does not imply equal final logits after the later suffix tokens are processed.

Zero-runtime forensic accounting:

```text
model_calls = 0
server_startups = 0
gpu_guard_acquisitions = 0
http_requests = 0
subprocess_transitions = 0
```

## Scientific interpretation

For this exact fixture/model/runtime subject:

1. warm generation is byte-reproducible: `W == W2`;
2. equal-length W883 and C883, which share tokens 0..864 and the same expected 371 -> 508 -> 4 checkpoint segmentation, produce byte-identical stored KV for logical positions 0..511;
3. the earlier cold C2927 arm produced different prefix KV when its physical prompt-processing history used a different first-decode segmentation.

Therefore the earlier `W != C2927` observation is not evidence that future suffix token content changes already-computed prefix KV.

The discriminating factor removed by the control is total-prompt-length-dependent physical prompt processing, specifically the checkpoint/decode segmentation identified in exact server source. Within this apparatus, the evidence supports decode-segmentation/history dependence of the byte representation rather than retained-prefix mutation or future-suffix dependence.

The API-output difference between W and C883 is compatible with this conclusion because the requests diverge after token 864 and generation occurs only after all 883 prompt tokens have been processed.

No further physical execution is authorized by this authority.

## Hard zero-runtime boundary

The reconciliation must report exactly:

```text
model_calls = 0
server_startups = 0
gpu_guard_acquisitions = 0
http_requests = 0
subprocess_transitions = 0
```

No scientific campaign interaction or repository/v1 mutation is permitted during reconciliation.

## Terminal rule

Run the post-hoc reconciler at most once from a fresh nonexistent output root.

If it succeeds, stop.

If it fails, terminalize as:

`SEGMENTATION_CONTROL_POSTHOC_NOT_RECONCILED`

and stop.

Do not repair/retry/replay within the same reconciliation authority generation.

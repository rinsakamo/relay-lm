# Gemma 4 KV segmentation-control post-hoc reconciliation authority

Diagnostic only.

## Status

`SEGMENTATION_CONTROL_POSTHOC_RECONCILIATION_READY`

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

# Gemma 4 KV segmentation-control measured authority

Diagnostic only.

## Status

`QUALIFIED_FOR_ONE_SEGMENTATION_CONTROL_MEASURED_ATTEMPT`

This authority permits exactly one measured segmentation-control attempt.

It does not authorize retry, replay, resume, reseed, alternate ports after consumption, FA-OFF, historical-runner invocation, scientific campaign mutation, or v1 mutation.

## Authority generation

`logical-prefix-kv-segmentation-control-measured-authority-20260922-6802c20c-c883sha64`

## Attempt identity

`logical-prefix-kv-segmentation-control-20260922-6802c20c`

## Superseded static-gate generation

The immediately preceding authority generation:

`logical-prefix-kv-segmentation-control-measured-authority-20260922-6802c20c`

is superseded before measured execution.

Its static gate failed because the bound `C883.tokens.json` SHA256 omitted the final hexadecimal character:

```text
invalid 63-hex binding:
1b3796b5dbec09d1fe2188d0bce1a9a9e8be316943d0e415582dde0a0ff3a92

correct committed 64-hex SHA256:
1b3796b5dbec09d1fe2188d0bce1a9a9e8be316943d0e415582dde0a0ff3a92a
```

Observed execution boundary for the superseded generation:

```text
py_compile = PASS
runner self-test invocations = 1
runner self-test = FAIL
wrapper self-test invocations = 0
guard self-test invocations = 0
execute-once wrapper invocations = 0
direct measured runner invocations = 0
guard child invocations = 0
W/W2/C883 requests = 0
measured attempt consumed = false
terminal state = PROBE_NOT_EXERCISED
retry/replay/resume/reseed/repair/fallback = 0
```

The old generation MUST NOT be executed. The attempt identity remains unchanged because no measured request was attempted and no consumption boundary was crossed.

## Scientific question

The prior fixture-v2 measured attempt terminalized:

`TERMINAL_CONSUMED_PREFIX_KV_GENERATION_DIFFERS`

with:

```text
W == W2 == R
W != C2927
```

Static source inspection then identified unequal physical prompt segmentation:

```text
W883:
371 -> 508 -> 4

C2927:
512 -> ...
```

This attempt equalizes prompt length and checkpoint-driven decode segmentation.

It compares:

```text
W    = fresh committed warm request, 883 tokens
W2   = independent fresh replay of the exact W raw request
C883 = committed target prefix of length 883
```

Both W and C883 have:

```text
total prompt length = 883
LCP = 865
expected segmentation = 371 -> 508 -> 4
logical position 511 decode ordinal = 2
```

Allowed complete classifications:

```text
SEGMENTATION_CONTROL_WARM_NOT_REPRODUCIBLE
SEGMENTATION_CONTROL_KV_IDENTICAL
SEGMENTATION_CONTROL_KV_DIFFERS
```

Interpretation:

```text
W != W2
  -> SEGMENTATION_CONTROL_WARM_NOT_REPRODUCIBLE

W == W2 == C883
  -> SEGMENTATION_CONTROL_KV_IDENTICAL
     The prior W != C2927 byte-level KV difference is attributable to the
     unequal physical prompt-decode segmentation for this apparatus/subject.

W == W2 && W != C883
  -> SEGMENTATION_CONTROL_KV_DIFFERS
     A prefix KV difference remains after total prompt length and expected
     physical segmentation are equalized. Suffix/content-path or another
     uncontrolled factor remains.
```

This authority does not predetermine the outcome.

## Repository authority

Diagnostic branch execution-authority snapshot before this file:

```text
HEAD = be81f2fea7ad5dd992554e73e301cac9bd5ee520
```

Current repository authority at execution time always wins.

Protected v1 is independent from this diagnostic attempt.

## Parent fixture

Repository path:

`diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2/`

Fixture commit:

`58d3c1e9b8cf973648be1aeb8a8b12429a69d088`

Fixture subtree:

`455d94850515c70995addc6c1c446ba738a01474`

Warm request:

```text
L0.request.json SHA256 =
d777877485b3307d8ee76e6b6df783d00b4302bb700c405ac5cbf2f6d7344f5d
```

Warm tokens:

```text
warm.tokens.json SHA256 =
cc42e325d85ed559835225b53152446bc405b2d166c10a3e16b07c7859bf7f27
```

## Segmentation-control fixture

Repository path:

`diagnostics/llama-cpp/fixtures/e2d2c0d6-gemma4-kv-v2-segmentation-control/`

Control commit:

`ccf9e78a89d170ae43e6ccfa6aa0788bd9a6cacc`

Control subtree:

`ac26ba25c3b88cbd9586ec009eeefe66004e2cb5`

Committed identities:

```text
C883.tokens.json SHA256 =
1b3796b5dbec09d1fe2188d0bce1a9a9e8be316943d0e415582dde0a0ff3a92a

C883.request.json SHA256 =
1e490f609ac0b844521784cd4603ea79a9c5ab0b199117e4395c4a8cf2efa47c

manifest.json SHA256 =
aa23a149d9d54137f8a455034c5048c8b7d8e03a4d12d3f33000c66aece8b86b
```

Git blobs:

```text
C883.tokens.json =
1d313fa510cb75465380646fc26f63811c3cb683

C883.request.json =
b2bfbc61558b7158394693c2df29de31af35d794

manifest.json =
39a230ddaa21e5c13dc80d9707c8f71c1bd8d476
```

## Fresh pre-measured apparatus

Qualified root:

`/tmp/relaylm-segmentation-control-qual.UsVe3A/output`

Required terminal:

`LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY`

Frozen source:

```text
llama.cpp HEAD =
e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d

source tree =
6d39fd93dc91fc0a4bc86dffe9782d4f26318004
```

Patch identities:

```text
aligned reuse =
cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a

repaired logical-prefix =
d62810fdc645cbb011c52047e9ba9227b1d6c29fafc0bac0e7cf659f6104e4c8

applied.patch =
2f3829164ae8dffce6054681fbcef3f674fb901d37a2ffc383a91f3c867f7737
```

Runtime closure:

```text
llama-server =
6802c20c27073fd0ec4640808aa89586d9261b1775c07c0a01761e3a6169f95a

libllama-server-impl.so =
960a1e8ef9b49ac06898737bef8148d5ab680eb8f2062d35c289d797b631f17b

libllama.so =
3cb5756febc27493f88b29373ed0274885bdb7a411163d6af24d430e0d57c463

model =
c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed
```

Startup canonical argv SHA256:

`9ee42d8effe614d5ab9827c35c2bde820478ffa0626099b3b0f944e7c51519c8`

Runtime geometry:

```text
n_seq_max = 1
n_ctx = 8192
n_batch = 512
n_ubatch = 512
flash_attn = enabled
base KV = 8192
SWA KV = 1536
```

The qualification was non-generative and unconsumed.

## Measured apparatus code

Only these new measured files belong to this authority:

```text
e2d2c0d6-gemma4-kv-segmentation-control-measured-run.py
Git blob = e0c7dc9a775e712b6d9ad1cfa8edb7432679cf5f

e2d2c0d6-gemma4-kv-segmentation-control-measured-runner-selftest.py
Git blob = 192f75a9a0cfa34308ae21610ee287d65b357f4c

e2d2c0d6-gemma4-kv-segmentation-control-execute-once.py
Git blob = 2f1e81411fe95f64aefaab51b68ec0de73560ad1

e2d2c0d6-gemma4-kv-segmentation-control-wrapper-selftest.py
Git blob = d734ac13fa8eb7178bda6b426cbe78f6ea0bb3e2
```

The historical four-point fixture-v2 runner/wrapper is consumed historical apparatus and is not authorized.

## Static gate

Before wrapper invocation, require:

```text
LOGICAL_PREFIX_SEGMENTATION_CONTROL_RUNNER_SELFTEST_PASS
LOGICAL_PREFIX_SEGMENTATION_CONTROL_WRAPPER_SELFTEST_PASS
LOGICAL_PREFIX_RESOURCE_GUARD_SELFTEST_PASS
```

and Python compile success for all measured/control helpers.

If any static gate fails:

- wrapper invocation must remain zero;
- measured W must remain zero;
- stop;
- do not repair/retry in the same transaction.

## Only authorized measured entrypoint

`e2d2c0d6-gemma4-kv-segmentation-control-execute-once.py`

The inner runner must never be invoked directly.

The execute-once wrapper must be invoked at most once.

## Canonical resource guard

Measured runner execution is allowed only as the child of:

`e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py`

Resource key:

`llama-cpp:local-gpu`

Lock:

`/tmp/relaylm/physical/locks/a820834e5681ba28.lock`

Require exactly two external-idle observations five seconds apart before the child begins.

## Measured sequence

Use three distinct fresh loopback ports, none equal to 1234.

Exactly:

```text
fresh W server:
  exact committed L0.request.json raw bytes
  cache_n = 0
  prompt_n = 883
  predicted_n = 1
  require W-P512

fresh W2 server:
  exact same committed L0.request.json raw bytes
  cache_n = 0
  prompt_n = 883
  predicted_n = 1
  require W2-P512

fresh C883 server:
  exact committed C883.request.json raw bytes
  cache_n = 0
  prompt_n = 883
  predicted_n = 1
  require C883-P512
```

All three dumps must independently pass complete logical-prefix validation.

## Consumption boundary

The first measured request is W.

The runner records exact raw W bytes at:

`server-W/W.request.json`

before the HTTP POST.

That record is the conservative consumption boundary.

Before it exists:

```text
PROBE_NOT_EXERCISED
measured_attempt_consumed = false
```

Once it exists:

```text
PROBE_EXERCISED_INCOMPLETE
measured_attempt_consumed = true
rerun_authorized = false
```

if a complete terminal classification is not produced.

A complete classification is also terminal and consumed.

## Hard prohibitions

Must remain zero:

- retry;
- replay;
- resume;
- reseed;
- repair-in-place;
- FA-OFF;
- historical four-point measured wrapper/runner;
- fixture mutation;
- control mutation;
- protected v1 mutation;
- scientific `--execute`;
- #2965 campaign invocation;
- campaign queue/receipt/lease/spend mutation;
- #2964 mutation;
- production/cache-policy mutation;
- primary dirty checkout mutation;
- upstream submission.

## Terminal rule

Once the execute-once wrapper has been invoked, stop regardless of outcome.

No result from this authority authorizes its own rerun or a follow-on physical measurement.

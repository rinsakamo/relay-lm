# Gemma 4 logical-prefix KV replacement measured-attempt authority

Diagnostic only. This authority is independent of the RelayLM v1 scientific campaign.

## Status

`QUALIFIED_FOR_ONE_REPLACEMENT_MEASURED_ATTEMPT`

Authority generation:

`logical-prefix-kv-replacement-measured-authority-20260921-l0sha64`

This generation supersedes the prior authority at diagnostic commit `6f180d2ee4f5f2a11a9b05b082e66791c010d045`, which was invalid before execution because its L0 SHA256 constant was malformed at 63 hexadecimal characters. Under that invalid generation: wrapper invocations = 0, measured runner invocations = 0, server lifetimes = 0, requests submitted = 0, L0 submitted = false, measured attempt consumed = false.

The authoritative L0 raw request SHA256 is the 64-character reconciliation identity:

`9120aed18e9aac20615cab2de00337eb9bf65edeb7249015c97d3c41d881e38d`

The superseded generation MUST NOT be executed or retried.

Attempt identity:

`logical-prefix-kv-replacement-20260921-30d3f94f`

This is a distinct replacement attempt. It is not a retry, replay, resume, repair-in-place, or continuation of the previously consumed `PROBE_EXERCISED_INCOMPLETE` attempt.

Fresh repository authority at execution time always wins over snapshots in this file.

## Fresh repository snapshot at authoring

```text
diagnostic code head before this authority commit = 6dee1e952afe696a26592446110db22e6ff8543a
diagnostic code tree = 30bbc36a7dc830d6f18ae4d822ef74d7f42380fa
v1 head = 959491d0c36dcfc7d6401c3aa8a6fdab39107515
v1 tree = d36b2fcf6da166578dbcfc64056649ccf97b0c2b
open PRs targeting v1 = 0
open diagnostic-related PRs = 0
ruleset 20931403 = active
```

The primary dirty checkout remains out of scope and must not be mutated.

## Qualified pre-measured apparatus

The pre-measured qualification completed with:

`LOGICAL_PREFIX_REPLACEMENT_PREMEASURED_READY`

Bound evidence root:

`/tmp/relaylm-logical-prefix-premeasured.4BYIKs/output`

Frozen build/runtime identity:

```text
llama.cpp source = e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d
llama.cpp tree = 6d39fd93dc91fc0a4bc86dffe9782d4f26318004

aligned patch sha256 =
cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a

logical-prefix patch sha256 =
caad4731d82659468624e73803b6de6c3b8ac081d44350b8f71ae2d0600e1f36

combined applied.patch sha256 =
d8d251727e5f3aa9a2d38434c124d0feb8748024f78cce5d4ec185bd8266fc7e

llama-server sha256 =
30d3f94f7335821a74828c243ab1dd315df9dc7a4c6df0cdff2f3ce1629dbaff

libllama-server-impl.so sha256 =
e6003c1e1a1c1c16dc5a09da485517eec6b6010d17f198acd34981075c14a64c

libllama.so sha256 =
53228c024c04bd4a1acefa03d9ddc602cdfc78b5214d7fb7da13de458d2a2965

model sha256 =
c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed

canonical startup argv sha256 =
9294cc601e6be0511d92caa7e560b1f9a2843147b6b876a9c8896ae7822ab6fd

base KV = 8192
SWA KV = 1536
flash attention = enabled
n_ctx = 8192
n_batch = 512
n_ubatch = 512
n_seq_max = 1
```

Binary provenance:

`LOGICAL_PREFIX_BINARY_PREFLIGHT_PASS`

Startup qualification:

`LOGICAL_PREFIX_STARTUP_QUALIFIED`

The pre-measured qualification performed zero generation requests and did not consume a measured attempt.

## Frozen request identity

Request reconciliation completed with:

`LOGICAL_PREFIX_REQUEST_IDENTITY_RECONCILED`

Bound reconciliation root:

`/tmp/relaylm-logical-prefix-request-id.JWuNTY/reconciliation`

Exact frozen input identities:

```text
warm token raw SHA256 =
c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2

target token raw SHA256 =
549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e

L0 raw request SHA256 =
9120aed18e9aac20615cab2de00337eb9bf65edeb7249015c97d3c41d881e38d

L1 raw request SHA256 =
d4deaa365324c5ca3c42eba4e6db9defe957a1cf06bbc08e9d3a01ba94ec0d1f

LC raw request SHA256 =
284630a2f90e364b5dd336d3d9fadc59ddd0fa072fbac7cc825200bef2e7af52
```

The admitted request contract is:

```text
L0 prompt = exact frozen warm token array
L1 prompt = exact frozen target token array
LC prompt = exact frozen target token array

L0 cache_prompt = true
L1 cache_prompt = true
LC cache_prompt = false

n_predict = 1
temperature = 0
stream = false
L1 n_probs = 20
LC n_probs = 20

L1 and LC differ only by cache_prompt
```

L0R is defined as the exact L0 raw request bytes sent once on the fresh WR2 server.

No request may be regenerated, retokenized, normalized, reconstructed, or substituted.

## Canonical measured entrypoint

The only authorized measured entrypoint is:

`e2d2c0d6-gemma4-kv-logical-prefix-replacement-execute-once.py`

The direct replacement runner:

`e2d2c0d6-gemma4-kv-logical-prefix-replacement-measured-run.py`

must not be invoked manually.

The old consumed runner and old resume wrapper must not be invoked.

The execute-once wrapper is bound to:

```text
attempt id = logical-prefix-kv-replacement-20260921-30d3f94f
premeasured root = /tmp/relaylm-logical-prefix-premeasured.4BYIKs/output
request reconciliation root = /tmp/relaylm-logical-prefix-request-id.JWuNTY/reconciliation
server/runtime closure SHA256 values above
model SHA256 above
warm/target/L0/L1/LC SHA256 values above
```

Before entering the shared GPU guard, the wrapper must re-read and validate both evidence roots, verify live artifact hashes, verify the model hash, and run the replacement runner/wrapper contract self-tests.

Any mismatch before measured execution must terminate as:

`PROBE_NOT_EXERCISED`

with:

```text
measured_l0_submitted = false
measured_attempt_consumed = false
```

No automatic repair or retry is authorized.

## Shared local-GPU boundary

The measured wrapper must execute the measured runner only as the child of:

`e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py`

Canonical resource:

```text
resource key = llama-cpp:local-gpu
lock root = /tmp/relaylm/physical/locks
lock file = /tmp/relaylm/physical/locks/a820834e5681ba28.lock
```

Before the child is invoked, require exactly two external-idle observations five seconds apart for:

- `llama-server`
- `llama-cli`
- `llama-run`
- `127.0.0.1:1234`

Socket semantics:

```text
connect success = busy
ECONNREFUSED = idle
permission / timeout / other errno = inconclusive -> fail closed
```

This diagnostic guard must not create or touch #2965 campaign queue/receipt/lease/spend artifacts.

## Runtime

All three server lifetimes use exactly:

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

After all pre-L0 checks have passed, run exactly:

```text
WR server:
  L0 exactly once
  L1 exactly once

WR2 fresh server:
  L0R exactly once

C fresh server:
  LC exactly once
```

Expected path accounting:

```text
L0  -> cache_n=0,   prompt_n=883
L1  -> cache_n=512, prompt_n=2415
L0R -> cache_n=0,   prompt_n=883
LC  -> cache_n=0,   prompt_n=2927
predicted_n = 1 for each request
```

Required dump points:

- `WR-P512/`
- `WR-R512/`
- `WR2-P512/`
- `C-P512/`

Each dump must pass manifest-driven completeness and cross-observation geometry checks.

## Consumption boundary

This authority permits at most one invocation of the execute-once wrapper.

Before L0 submission:

- a failure is `PROBE_NOT_EXERCISED`;
- the measured attempt is not consumed;
- nevertheless this authority is terminal for that invocation;
- do not automatically invoke the wrapper again;
- return to management for a fresh authority decision.

At the L0 boundary, consumption is conservative.

The measured runner writes:

`server-WR/L0.request.json`

before performing the HTTP POST.

If the runner exits without `terminal.json`, the execute-once wrapper must use that record as the conservative consumption marker:

```text
L0 request record absent
  -> PROBE_NOT_EXERCISED

L0 request record present
  -> PROBE_EXERCISED_INCOMPLETE
  -> measured_attempt_consumed = true
  -> rerun_authorized = false
```

Once L0 has crossed the consumption boundary, any later failure is terminal and consumed.

No retry, replay, resume, reseed, fallback, repair, or replacement attempt is authorized after consumed status.

## Allowed completed classifications

A complete four-point probe must end in exactly one of:

- `PREFIX_DUMP_NOT_REPRODUCIBLE`
- `PREFIX_KV_GENERATION_DIFFERS`
- `RETAINED_PREFIX_KV_MUTATED_BY_REUSE`
- `PREFIX_KV_IDENTICAL_THROUGH_REUSE`

Interpretation must follow the existing retained-prefix KV provenance probe contract.

If the sequence cannot produce a valid four-point classification after L0 is consumed, terminalize:

`PROBE_EXERCISED_INCOMPLETE`

## Fresh execution requirements

Immediately before invoking the execute-once wrapper:

1. reacquire current diagnostic HEAD/tree;
2. reacquire current v1 HEAD/tree;
3. confirm no conflicting diagnostic authority or measured execution has appeared;
4. read this authority from the current diagnostic branch;
5. confirm the primary checkout remains untouched;
6. verify the pre-measured evidence root still exists;
7. verify the request-reconciliation root still exists;
8. verify the existing model artifact matches the frozen SHA256;
9. use a fresh non-existing preflight root;
10. use a fresh non-existing measured output root;
11. use three fresh distinct loopback ports;
12. run static Python compile plus:
    - replacement runner self-test;
    - replacement wrapper self-test;
    - logical-prefix resource-guard self-test.

If any static or authority check fails, stop before wrapper invocation.

## Authorized invocation shape

Use the current diagnostic checkout:

```bash
python3 diagnostics/llama-cpp/e2d2c0d6-gemma4-kv-logical-prefix-replacement-execute-once.py \
  --model <existing-frozen-model-path> \
  --preflight-root <fresh-nonexistent-preflight-root> \
  --out-root <fresh-nonexistent-measured-output-root> \
  --port-wr <fresh-port-1> \
  --port-wr2 <fresh-port-2> \
  --port-c <fresh-port-3>
```

Invoke this command at most once.

Do not invoke any inner measured runner separately.

## Required terminal reconciliation

After the single wrapper invocation, preserve:

- fresh repository HEAD/tree;
- wrapper preflight evidence;
- bound identity;
- shared-resource guard evidence;
- exactly two external-idle observations;
- exact measured runner argv;
- physical identity;
- request admission;
- all three server logs;
- all four raw requests/responses;
- four KV dump roots;
- dump geometry;
- KV digest comparison;
- API L1-vs-LC comparison;
- localization;
- terminal classification.

Report exact counts:

```text
execute-once wrapper invocations
measured runner invocations
server lifetime attempts
requests submitted
L0 submitted
retry/replay/reseed/fallback/repair
FA-OFF arms
scientific campaign interactions
campaign queue/receipt/spend mutations
```

Do not relabel a partial/consumed run as complete.

## Campaign separation

Must remain zero:

- #2965 campaign invocation;
- campaign queue/receipt/lease/spend mutation;
- #2964 reuse/mutation;
- scientific `--execute`;
- protected v1 mutation;
- production/cache-policy mutation;
- FA-OFF arm;
- primary dirty checkout mutation;
- upstream submission.

This authority is solely for the one replacement FA-ON KV provenance diagnostic attempt.

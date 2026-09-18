# Gemma 4 KV provenance resume after startup recovery

Diagnostic-only execution handoff.

## Fresh repository authority at resume authoring

- protected v1: `1e3a6ed3136fbb68342973e63386b4468d96327f`
- protected v1 tree: `a1251b57efc1fb631b8d9513c3422e34dc1d4903`
- open PRs targeting v1: 0
- ruleset 20931403: active on v1
- #2961: CLOSED / completed zero-semantic proof
- #2964: OPEN historical scientific owner, explicitly not to be rebound/reused/executed
- #2965: OPEN qualification-only repair owner
- #1449 / #1447: remain open; no scientific campaign authorization is carried by this diagnostic

Current repository authority at execution time wins over this snapshot.

## #2965 separation boundary

#2965 is currently stopped at a static fail-closed preparation barrier before any public rehearsal or execute invocation.

This KV diagnostic MUST NOT:

- read or mutate #2965 owner-local plan/proof/queue/spend artifacts;
- invoke `v1:external-qualification-campaign`;
- invoke `--rehearsal` or `--execute` for the scientific campaign;
- create or acquire a #2965 campaign queue/lease;
- reconcile/comment/close/route #2965;
- reuse or rewrite #2964.

The scientific campaign spend boundary remains independent and unconsumed by this diagnostic.

This diagnostic does perform llama.cpp model inference for mechanism analysis. Those calls are diagnostic evidence and are not scientific campaign participant/judge/benchmark execution.

## Recovery bridge

The immediately preceding KV provenance attempt ended:

`PROBE_NOT_EXERCISED`

because the warm server did not reach health readiness.

A dedicated non-generative recovery then completed:

`STARTUP_RECOVERED`

Recovered exact runtime identity:

- instrumented llama-server SHA256:
  `0a9160015c31d11b607b1bd7559e69fe90c02d1079ad7517ccb24ea75c71b08e`
- model SHA256:
  `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`
- canonical startup argv SHA256:
  `31f78eb492fc4b91dd438857005f02b91c9aa903975bee48568c104058827c94`
- n_ctx=8192
- n_batch=512
- n_ubatch=512
- parallel=1
- gpu-layers=999
- context shift disabled
- flash_attn=enabled
- both plain/probe non-generative startups reached HTTP 200
- no KV dump was produced during recovery

Do not rebuild or substitute the instrumented binary unless an identity precondition fails before measured generation. A changed binary requires a new recovery/read-back before this probe can be exercised.

## Required authorities

Read fully before execution:

- `e2d2c0d6-gemma4-kv-prefix-provenance-probe.md`
- `e2d2c0d6-gemma4-kv-prefix-provenance-execution-authority.md`
- `e2d2c0d6-gemma4-kv-prefix-digest-compare.py`
- this resume authority

The resume authority narrows startup identity but does not replace the underlying probe classification contract.

## Frozen runtime

Use the recovered binary exactly.

Required:

```text
llama.cpp source = e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d
instrumented binary sha256 = 0a9160015c31d11b607b1bd7559e69fe90c02d1079ad7517ccb24ea75c71b08e
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

FA OFF is not an arm.

## Exactly-once measured sequence

Use a fresh empty KV dump root.

### Server A — warm/reuse

Probe label: `WR`

1. L0 warm exactly once, `cache_prompt=true`
2. L1 target exactly once, `cache_prompt=true`

Required:

- L1 effective reuse exactly 512
- expected L1 prompt eval exactly 2415
- dumps:
  - `WR-P512/`
  - `WR-R512/`

If the reuse path prediction fails, classify `PROBE_NOT_EXERCISED`; do not repair or retry.

### Server B — fresh reproducibility control

Probe label: `WR2`

3. L0R warm exactly once, `cache_prompt=true`

Required dump:

- `WR2-P512/`

L0R is a predeclared independent control, not a retry.

### Server C — fresh cold

Probe label: `C`

4. LC target exactly once, `cache_prompt=false`

Required:

- reuse 0
- prompt eval exactly 2927
- dump:
  - `C-P512/`

## Request identity

Reuse the frozen numeric token arrays and exact request payload identities from the completed logical-batch-512 discriminator.

Do not retokenize, regenerate, or reconstruct the fixture from text if the frozen numeric arrays are available.

Retain for each measured request:

- exact request bytes
- request SHA256
- prompt-array SHA256
- response bytes
- full server log
- cache_n / n_past
- prompt-eval count/timing
- first generated token
- top-N IDs/logprobs/probs

## Terminal comparison

After and only after all four required dump directories exist, run:

```bash
python3 diagnostics/llama-cpp/e2d2c0d6-gemma4-kv-prefix-digest-compare.py \
  <kv-dump-root> > kv-prefix-comparison.json
```

Primary classification must be exactly one:

- `PREFIX_DUMP_NOT_REPRODUCIBLE`
- `PREFIX_KV_GENERATION_DIFFERS`
- `RETAINED_PREFIX_KV_MUTATED_BY_REUSE`
- `PREFIX_KV_IDENTICAL_THROUGH_REUSE`
- `PROBE_NOT_EXERCISED`

If KV payload differs, report:

- W vs W2 gate result
- first differing cache class: base or SWA
- first differing layer
- K or V
- total mismatching per-layer K/V files
- whether layout metadata also differs

Also report instrumented L1 vs LC API first-token/top-N comparison, but do not let API identity override the KV-state primary classification.

## Retry boundary

After the first measured L0 request is submitted:

- retry = 0
- replay = 0
- reseed = 0
- fallback = 0
- repair = 0
- tuning = 0
- alternate binary = 0
- alternate runtime = 0

Any failure after measured L0 is terminal for this probe attempt.

A failure before measured L0 may classify `PROBE_NOT_EXERCISED` without consuming the measured probe.

## Hard boundaries

- protected v1 mutation = 0
- #2965 campaign rehearsal/execute = 0
- #2965 queue/lease/spend interaction = 0
- #2964 mutation/reuse = 0
- production/cache-policy mutation = 0
- RC1 action = 0
- primary dirty checkout mutation = 0
- FA OFF = 0
- completed M/A/F matrix rerun = 0
- #2934 rerun = 0
- #2947 rerun = 0
- upstream submission = 0

This is a llama.cpp physical mechanism diagnostic, not RelayLM scientific campaign execution, production qualification, or release PASS.

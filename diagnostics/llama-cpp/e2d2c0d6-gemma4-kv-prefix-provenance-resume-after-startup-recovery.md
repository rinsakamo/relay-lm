# Gemma 4 KV provenance resume after startup recovery

Diagnostic-only execution handoff.

## Fresh repository authority at resume authoring

- protected v1: `117ff21a8b51c174de4b0cbff9dc2bf1e1b97fc2`
- protected v1 tree: `bfb4a26e1b4e1c18a0faf48093379bd098f34b63`
- open PRs targeting v1: 0
- ruleset 20931403: active on v1
- #2961: CLOSED / completed zero-semantic proof
- #2964: OPEN historical scientific owner, explicitly not to be rebound/reused/executed
- #2965: OPEN qualification-only repair owner; latest host packet at authoring is v9 and scientific `--execute` remains unauthorized
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

## Execution harness

Use the one-shot resume wrapper as the preferred entrypoint:

- `e2d2c0d6-gemma4-kv-prefix-provenance-resume-run.py`

It orchestrates, in order:

1. `e2d2c0d6-gemma4-kv-artifact-locator.py`
2. locator terminal validation
3. `e2d2c0d6-gemma4-kv-prefix-provenance-run.py`
4. request admission inside the measured runner
5. exactly-once measured sequence and terminal comparison

The measured runner accepts only previously retained request JSON artifacts and frozen token-array files. It does not retokenize or reconstruct requests.

Before request admission, use the artifact locator over the prior diagnostic evidence roots. The locator:

- finds frozen token-array files only by their exact raw SHA256;
- identifies measured-request candidates only when their numeric prompt equals the frozen arrays and their request semantics match L0/L1/LC;
- permits duplicate byte-identical copies;
- fails closed if a role has multiple distinct raw request SHA256 identities;
- never creates or rewrites a request.

Required locator terminal: `ARTIFACT_LOCATOR_PASS`.

If the locator reports missing or ambiguous request identity, stop before L0 as `PROBE_NOT_EXERCISED`. Do not choose one candidate manually and do not reconstruct a request.

After locator PASS, request admission must prove:

- raw `warm-token-ids.json` SHA256 equals `c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2`;
- raw `target-token-ids.json` SHA256 equals `549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e`;
- lengths 883 / 2927 and LCP 865;
- saved L0 prompt equals the frozen warm array;
- saved L1/LC prompts equal the frozen target array;
- L0/L1 use `cache_prompt=true`;
- LC uses `cache_prompt=false`;
- L1 and LC differ semantically only by `cache_prompt`;
- L1/LC retain top-N logprobs;
- instrumented binary/model hashes equal the recovered identities;
- all three intended loopback ports are free.

If any saved request or frozen token-array artifact cannot be recovered exactly, stop before L0 as `PROBE_NOT_EXERCISED`. Do not reconstruct the request.

Preferred one-shot invocation:

```bash
python3 diagnostics/llama-cpp/e2d2c0d6-gemma4-kv-prefix-provenance-resume-run.py \
  --search-root <prior-logical-batch-evidence-root> \
  [--search-root <additional-exact-diagnostic-root> ...] \
  --preflight-root <fresh-preflight-root> \
  --server-bin <recovered-instrumented-llama-server> \
  --model <frozen-gguf> \
  --out-root <fresh-measured-output-root> \
  --port-wr <fresh-port> \
  --port-wr2 <fresh-port> \
  --port-c <fresh-port>
```

Use known prior diagnostic evidence roots; do not search the entire filesystem when narrower evidence roots are available.

The wrapper records the locator argv/output, selected exact artifacts, measured-runner argv, and measured-runner exit. It transitions into measured execution only after `ARTIFACT_LOCATOR_PASS`.

The underlying measured invocation is:

```bash
python3 diagnostics/llama-cpp/e2d2c0d6-gemma4-kv-prefix-provenance-run.py \
  --server-bin <recovered-instrumented-llama-server> \
  --model <frozen-gguf> \
  --warm-tokens <exact-warm-token-ids.json> \
  --target-tokens <exact-target-token-ids.json> \
  --l0-request <saved-logical-batch-L0-request.json> \
  --l1-request <saved-logical-batch-L1-request.json> \
  --lc-request <saved-logical-batch-LC-request.json> \
  --out-root <fresh-output-root> \
  --port-wr <fresh-port> \
  --port-wr2 <fresh-port> \
  --port-c <fresh-port>
```

The runner sends the saved request file bytes directly to native `/completion`. L0R sends the exact L0 bytes again on a fresh server. No request JSON is regenerated for measured inference.

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

The runner validates response timings directly:

- L0: cache_n=0 / prompt_n=883
- L1: cache_n=512 / prompt_n=2415
- L0R: cache_n=0 / prompt_n=883
- LC: cache_n=0 / prompt_n=2927

It also requires one predicted token for every measured request.

After and only after all four required dump directories exist, it runs:

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

Required terminal artifacts include:

Preflight root:
- `artifact-locator.json`
- `artifact-locator.argv.json`
- `artifact-locator.stdout.txt`
- `artifact-locator.stderr.txt`
- `selected-artifacts.json`
- `measured-runner.argv.json`
- `measured-runner.exit.json`

Measured output root:
- `request-admission.json`
- complete per-server argv/env/startup/logs
- per-server `startup-evidence.json` proving Flash Attention enabled, `n_batch=512`, and `n_ubatch=512`
- exact measured request bytes and SHA256
- raw and pretty responses
- `api-L1-vs-LC.json`
- `kv-prefix-comparison.json`
- `kv-localization.json`
- `terminal.json`

For a KV mismatch, `kv-localization.json` must identify the governing comparison pair, mismatch-file count, earliest differing layer/cache-class/K-or-V when parseable, and whether layout metadata differs.

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

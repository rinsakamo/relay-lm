# Gemma 4 KV prefix provenance execution authority

This file is the execution handoff for the next diagnostic step.

## Fresh repository state at authoring

- protected v1: `fc5242977f6a56d496a00df769db48f5c7ecf655`
- protected v1 tree: `1c1b4ee9dff6797aaa5a8162b3e45beee556b415`
- open PRs targeting v1: 0
- diagnostic branch before this authority: `a3fd56c2364b14de4d09bde7227653c6a04fca3a`

Fresh repository authority at execution time still wins over these recorded values.

## Prior result

The immediately preceding physical discriminator completed with:

`LOGICAL_BATCH_ALIGNMENT_DOES_NOT_RESTORE_IDENTITY`

under:

```text
n_batch = 512
n_ubatch = 512
flash_attn = enabled
effective reuse = 512
```

L1 and LC had the same first token but different API-visible top-N/logprobs.

Do not rerun that discriminator without the instrumentation defined here.

## Required files

Read fully:

- `e2d2c0d6-gemma4-kv-prefix-provenance-probe.md`
- `e2d2c0d6-gemma4-kv-prefix-dump-diagnostic.patch`
- `e2d2c0d6-gemma4-kv-prefix-digest-compare.py`
- prior logical-batch authority for frozen fixture/runtime identity

## Practical constraint

Flash Attention is part of the intended production configuration.

This probe MUST keep:

`--flash-attn on`

Do not run an FA-OFF arm as part of this work.

The investigation goal is to make cache reuse safe under the FA-ON configuration, not to qualify a slower FA-OFF workaround.

## Build gate

Use a clean disposable checkout/worktree of exact llama.cpp:

`e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`

First verify all frozen source/model/fixture identities.

Apply the existing aligned-reuse diagnostic patch, then the KV-prefix dump diagnostic patch.

Before any measured request:

1. `git apply --check` for each diagnostic patch against its intended base/order.
2. Build `llama-server`.
3. retain source revision, patch hashes and resulting binary SHA256.
4. run a non-generative startup/preflight with the exact intended runtime.
5. verify:
   - n_ctx=8192
   - n_batch=512
   - n_ubatch=512
   - flash_attn=enabled
   - compact SWA
   - RTX 3060 intended backend/device
   - HTTP health 200

If the patch does not apply or the build fails, do not improvise a semantic repair during the same physical attempt. Preserve the failure and stop before measured generation. A purely mechanical compile fix may be prepared separately in the diagnostic branch and must be reviewed before spending the probe.

## Instrumentation behavior

The patch is allowed only to observe already-computed state.

It must not:

- add compute-graph nodes;
- change attention inputs;
- change sampling;
- change cache allocation/reuse policy;
- change batch geometry;
- change Flash Attention state.

It synchronizes only at dump points and copies existing KV rows to host files.

The dump is ordered by logical position and fails closed unless positions 0..511 are present exactly once.

## Server lifetimes

### Warm/reuse server

Set:

```text
LLAMA_KV_PROBE_DIR=<fresh empty output root>
LLAMA_KV_PROBE_LABEL=WR
```

Run exactly:

- L0 warm
- L1 target with aligned reuse=512

Expected dump directories:

- `WR-P512/` after L0 first 512-token decode
- `WR-R512/` after L1 suffix removal and before continuation decode

### Cold server

Fresh server, same binary/config.

Set:

```text
LLAMA_KV_PROBE_DIR=<same output root>
LLAMA_KV_PROBE_LABEL=C
```

Run exactly:

- LC target cache_prompt=false

Expected:

- `C-P512/`

The dumper refuses to overwrite an existing dump directory. Use a fresh empty output root before the measured run.

## Requests

Exactly one each:

- L0
- L1
- LC

No retry/replay/reseed/fallback/repair/parameter tuning after L0.

Retain responses and complete logs because the instrumented binary is a new physical artifact.

## Comparison

After all three dumps exist:

```bash
python3 diagnostics/llama-cpp/e2d2c0d6-gemma4-kv-prefix-digest-compare.py <output-root> > kv-prefix-comparison.json
```

Compare KV payload and layout metadata separately.

Primary KV-state classification comes from the probe authority:

- `PREFIX_KV_GENERATION_DIFFERS`
- `RETAINED_PREFIX_KV_MUTATED_BY_REUSE`
- `PREFIX_KV_IDENTICAL_THROUGH_REUSE`
- `PROBE_NOT_EXERCISED`

If KV differs, localize the earliest mismatching cache class/layer/K-or-V file.

If all KV payload is identical but instrumented L1 vs LC still differs, the next investigation must move downstream of retained KV storage while remaining FA ON.

## Hard boundaries

- FA OFF = 0
- completed 9-request matrix rerun = 0
- #2934 rerun = 0
- #2947 rerun = 0
- protected v1 mutation = 0
- production/cache-policy mutation = 0
- RC1 action = 0
- primary dirty checkout mutation = 0
- upstream submission = 0

This is diagnostic instrumentation and a physical mechanism probe only.

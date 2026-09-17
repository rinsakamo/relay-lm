# Gemma 4 cache-boundary × SWA matrix — startup recovery

Diagnostic only. This document repairs only the pre-inference server-startup observation gap from the prior `PHYSICAL_PROBE_UNSPENT` attempt. It does not change the matrix, fixture, model, patches, or semantic protocol.

Primary matrix authority remains:

`diagnostics/llama-cpp/e2d2c0d6-gemma4-cache-boundary-swa-matrix-validation.md`

## Prior terminal state

The prior attempt stopped before the first measured one-token generation:

- classification: `PHYSICAL_PROBE_UNSPENT`
- measured generation count: `0`
- semantic inference started: `false`
- M warm server failed before health readiness
- health HTTP code: `000`
- curl exit: `7`
- stdout SHA256: empty-file SHA256
- stderr SHA256: empty-file SHA256
- no server log
- server process absent after failure
- no residual port
- no residual GPU process

This means the matrix hypotheses were not exercised. Do not interpret the startup failure as cache, SWA, ubatch, Flash-Attention, model-quality, or semantic evidence.

## Frozen identities retained from the prior attempt

Do not rebuild or replace these artifacts merely because startup failed.

Fixture:

- corpus SHA256: `4ffd2967dc487d6c4fd4de94e66a017fdf452399105c08093ebbcf0ecfc13936`
- corpus bytes: `113853`
- tokenized corpus length: `28800`
- warm length: `883`
- target length: `2927`
- LCP: `865`
- target suffix source index `j`: `1024`
- warm token IDs SHA256: `c3fe4b297c5213be586b2e95824aa4fcb7a7305683ae38336a33e7bbf58baca2`
- target token IDs SHA256: `549c108554c7a6613886addcf5a64ed74cc1ee7deeb901d580165b23011ec59e`

The corpus byte count was corrected from `113854` to `113853` after read-back of the retained file. The corpus SHA256 and both frozen token-array SHA256 values were unchanged; this is a metadata correction only, not fixture replacement.

Physical target:

- llama.cpp revision: `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`
- llama.cpp tree: `6d39fd93dc91fc0a4bc86dffe9782d4f26318004`
- model SHA256: `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`
- GPU: NVIDIA GeForce RTX 3060
- CUDA toolkit observed: `12.8.93`
- build: `0.4.0-dev build 10874 commit e2d2c0d6a`

Patches / binaries:

- maximum-reuse patch SHA256: `cfb1a054ec5b89e7a271c2042ee6135a876d0f18d7f357d819224df06ac833f4`
- aligned-reuse patch SHA256: `cef233d776686ea36f03174b0c1d729545e2356f7009d613df726bcaf16a856a`
- maximum-reuse binary SHA256: `f63b51bf248374bdee3785c47ff836869d87821b42b2c6cd620ea803cb5fcfa5`
- aligned-reuse binary SHA256: `4d02da9c2178f6b0ac67a6a3a0e663b64a08010f7b1a4983e3c0b8cc190ee157`

If a supposedly retained artifact no longer matches these identities, stop before inference and report `PHYSICAL_PROBE_UNSPENT`. Do not silently regenerate a replacement fixture.

## Non-generative startup helper

Use:

`diagnostics/llama-cpp/e2d2c0d6-gemma4-cache-boundary-swa-startup-preflight.sh`

Invoke it with `bash`; executable mode is not required.

For Arm M startup diagnosis, use the retained maximum-reuse binary, the exact GGUF, and a free loopback port. Do not pass `--swa-full`.

Conceptual invocation:

```bash
bash diagnostics/llama-cpp/e2d2c0d6-gemma4-cache-boundary-swa-startup-preflight.sh \
  "$OUT_DIR" \
  "$MAX_REUSE_LLAMA_SERVER" \
  "$MODEL_GGUF" \
  18101
```

The helper sends no completion or generation request. It records:

- exact binary/model SHA256
- `file` / `ldd` evidence when available
- `llama-server --version` stdout/stderr/exit code
- NVIDIA/CUDA-visible process information when available
- port state before launch
- exact server argv
- PID and `/proc/<pid>/cmdline` / status when observable
- complete startup stdout/stderr
- bounded `/health` readiness polling only
- exit code and derived signal if the server dies before readiness
- port/GPU state after early exit
- kernel tail when readable
- explicit startup evidence for Flash Attention / CUDA / context / batch / slot / SWA-related settings

Fixed startup arguments inside the helper are:

- host `127.0.0.1`
- context `8192`
- parallel/slots `1`
- GPU layers `999`
- context shift disabled
- logical batch `2048`
- physical ubatch `512`
- `--flash-attn on`

The F-arm preflight may append `--swa-full`; M/A must not.

## Mechanical classifications

The helper classification is startup-only and does not replace the matrix classification.

Possible examples:

- `SERVER_BINARY_NOT_EXECUTABLE`
- `MODEL_PATH_INVALID`
- `SERVER_VERSION_FAILED`
- `PORT_ALREADY_OCCUPIED`
- `SERVER_EXITED_BEFORE_READINESS`
- `STARTUP_READINESS_TIMEOUT`
- `FLASH_ATTN_EVIDENCE_MISSING`
- `READY_NON_GENERATIVE`

Any failure before measured generation remains compatible with matrix-level `PHYSICAL_PROBE_UNSPENT`.

## Resume rule

If M preflight reaches `READY_NON_GENERATIVE`:

1. retain the complete preflight output directory;
2. verify binary/model hashes still match the frozen identities above;
3. launch a fresh M warm-target server with the same physical argv/configuration;
4. perform health readiness only;
5. only then send M0.

M0 is the first measured one-token generation and consumes the probe. From M0 onward, the no-retry/no-replay/no-reseed/no-fallback/no-repair/no-tuning rules in the matrix validation apply.

Do not count the successful non-generative preflight server lifetime as M0 or as a cache warm source; it must be terminated before the measured server starts.

If startup still fails, preserve all preflight files and stop. Do not alter the fixture, model, patch, binary, FA mode, batch sizes, SWA mode, or matrix design to make startup succeed.

## Boundaries

- protected `v1` mutation = 0
- production mutation = 0
- RC1 action = 0
- #2934 rerun = 0
- #2947 rerun = 0
- historical prompt reconstruction = 0
- semantic generation during preflight = 0
- upstream submission = 0
- primary dirty checkout mutation = 0

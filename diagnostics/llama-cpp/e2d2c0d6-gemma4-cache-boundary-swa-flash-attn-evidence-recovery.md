# Gemma 4 cache-boundary × SWA matrix — Flash Attention evidence recovery

Diagnostic only. This document repairs only the non-generative observability gap that produced `FLASH_ATTN_EVIDENCE_MISSING`. It does not change the fixture, model, patches, cache policy, SWA mode, batch geometry, matrix arms, or semantic protocol.

Primary matrix authority remains:

`diagnostics/llama-cpp/e2d2c0d6-gemma4-cache-boundary-swa-matrix-validation.md`

Startup recovery authority remains:

`diagnostics/llama-cpp/e2d2c0d6-gemma4-cache-boundary-swa-startup-recovery.md`

## Prior preflight result

The Arm M non-generative startup preflight reached health readiness successfully:

- `llama-server --version`: exit 0
- `/health`: HTTP 200
- server reached listen / model-loaded state
- server was visible as an RTX 3060 GPU process during readiness
- clean exit after health
- measured generation count: 0
- semantic inference started: false
- matrix state remains `PHYSICAL_PROBE_UNSPENT`

The helper nevertheless returned `FLASH_ATTN_EVIDENCE_MISSING` because startup logs did not contain the INFO-level context configuration lines needed by its evidence gate.

Do not interpret that classification as evidence that Flash Attention was disabled.

## Exact-source observations at llama.cpp e2d2c0d6

The exact target source maps the requested Flash Attention mode into context state before graph construction:

```cpp
cparams.flash_attn = params.flash_attn_type != LLAMA_FLASH_ATTN_TYPE_DISABLED;
cparams.auto_fa    = params.flash_attn_type == LLAMA_FLASH_ATTN_TYPE_AUTO;
```

Therefore `--flash-attn on` maps to an enabled, non-auto context state.

The same exact context constructor emits the following values at INFO level:

```cpp
LLAMA_LOG_INFO("%s: n_batch               = %u\n",   __func__, cparams.n_batch);
LLAMA_LOG_INFO("%s: n_ubatch              = %u\n",   __func__, cparams.n_ubatch);
LLAMA_LOG_INFO("%s: causal_attn           = %d\n",   __func__, cparams.causal_attn);
LLAMA_LOG_INFO("%s: flash_attn            = %s\n",   __func__, llama_flash_attn_type_name(params.flash_attn_type));
```

For `LLAMA_FLASH_ATTN_TYPE_ENABLED`, `llama_flash_attn_type_name()` returns `enabled`.

The exact CLI supports:

```text
-lv, --verbosity, --log-verbosity N
```

with:

- `3 = info`
- `4 = trace`
- `5 = debug`

The missing lines in the prior preflight are therefore an observability/log-threshold issue unless contrary evidence appears.

## Gemma 4 Flash Attention graph path

The exact generic attention graph computes:

```cpp
const bool use_flash_attn = cparams.flash_attn && kq_b == nullptr;
```

and when true builds:

```cpp
ggml_flash_attn_ext(...)
```

Gemma 4 calls its attention builder with `kq_b == nullptr` in the target graph path.

Therefore, for this exact source/model path, startup evidence showing:

```text
flash_attn = enabled
```

together with the frozen Gemma 4 target is sufficient pre-inference evidence that the graph is configured to take the Flash Attention branch when attention is evaluated.

This is distinct from direct observation of a CUDA kernel launch. Actual backend kernel dispatch occurs only when the measured graph executes and cannot be required by a strictly non-generative startup gate.

## Revised non-generative preflight

Do not alter the existing helper. Pass INFO verbosity through its existing extra-arguments mechanism.

Arm M invocation:

```bash
bash diagnostics/llama-cpp/e2d2c0d6-gemma4-cache-boundary-swa-startup-preflight.sh \
  "$OUT_DIR" \
  "$MAX_REUSE_LLAMA_SERVER" \
  "$MODEL_GGUF" \
  18101 \
  --log-verbosity 3
```

If port 18101 is occupied before launch, selecting another free loopback port is still mechanical.

Do not pass `--swa-full` for M.

`--log-verbosity 3` is an observability-only change. It does not change model bytes, fixture bytes, cache reuse geometry, attention mode, sampling, batch size, ubatch size, SWA mode, or semantic request content. Record it explicitly in argv and use the same log verbosity for all measured server lifetimes if the matrix later proceeds.

## Required evidence for `READY_NON_GENERATIVE`

Require health readiness plus captured startup evidence containing all of:

```text
n_ctx                 = 8192
n_batch               = 2048
n_ubatch              = 512
flash_attn            = enabled
```

Also retain evidence that the intended GPU backend/device loaded and that the process owned the expected loopback port while ready.

Do not require a CUDA Flash Attention kernel-launch trace before M0. That would require computation and would collapse the distinction between non-generative readiness and measured inference.

If the exact INFO-level lines above are present, classify the startup preflight:

`READY_NON_GENERATIVE`

and stop. Do not send M0 in the same task unless separately authorized.

If health is ready but `flash_attn = enabled` is still absent at `--log-verbosity 3`, retain complete logs and remain `PHYSICAL_PROBE_UNSPENT`; do not increase verbosity or change parameters in the same attempt.

## Accounting

This recovery remains pre-inference mechanical work:

- measured generation count = 0
- semantic inference started = false
- retry/replay/reseed/fallback/repair = 0
- fixture replacement = 0
- parameter tuning = 0 (`--log-verbosity 3` is observability, not an inference parameter)
- protected v1 mutation = 0
- production mutation = 0
- RC1 action = 0
- #2934/#2947 rerun = 0
- primary dirty checkout mutation = 0
- upstream submission = 0

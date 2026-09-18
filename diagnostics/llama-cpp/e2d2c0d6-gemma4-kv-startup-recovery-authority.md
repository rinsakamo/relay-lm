# Gemma 4 KV probe startup recovery authority

Diagnostic only. The KV provenance probe classified `PROBE_NOT_EXERCISED` because the instrumented warm server exited before HTTP health readiness. No measured generation or KV dump occurred.

## Goal

Recover and explain startup readiness without consuming the KV provenance probe.

## Frozen target

- llama.cpp: `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`
- same aligned-reuse + KV-dump instrumented binary/artifact that passed build/apply checks, unless the binary identity is proven invalid
- model/fixture identities unchanged
- n_ctx=8192
- n_batch=512
- n_ubatch=512
- parallel=1
- gpu-layers=999
- no context shift
- `--flash-attn on`
- compact SWA

## Important inference

The KV dump code is only invoked after a successful decode or after reuse suffix removal. Therefore an exit before health readiness occurs before any intended KV dump hook is exercised. Do not attribute the startup failure to a measured KV-state effect.

## Recovery harness

Use:

`diagnostics/llama-cpp/e2d2c0d6-gemma4-kv-startup-recovery.sh`

It is strictly non-generative and polls `/health` for up to 180s while retaining exact argv, binary/model hashes, stdout/stderr, process status, exit code/signal, ports, nvidia-smi, and dmesg tail.

## Two startup arms

Run each once on a fresh loopback port:

1. `plain`: same instrumented binary, no `LLAMA_KV_PROBE_*` environment
2. `probe`: same binary and runtime, sets the probe environment, but sends no generation request

Do not send completion/chat requests in either arm.

Prefer the one-shot runner:

```bash
bash diagnostics/llama-cpp/e2d2c0d6-gemma4-kv-startup-recovery-run.sh \
  <fresh-output-root> <server-bin> <model-path> <plain-port> <probe-port>
```

The runner requires distinct loopback ports and a fresh output root, executes exactly `plain -> probe -> classifier`, records each arm's harness exit code, and emits `startup-recovery-terminal.json`.

The classifier requires identical server/model SHA256 and identical canonical server arguments across arms, while intentionally allowing different loopback ports and different probe-environment state. It also rejects any unexpected probe dump/output.

## Classification

Exactly one:

### `INSTRUMENTED_BINARY_STARTUP_FAILED`

`plain` exits before readiness or times out. Inspect server stderr/exit code/signal/dmesg. Do not run the KV physical probe.

### `PROBE_ENV_STARTUP_FAILED`

`plain` reaches `READY_NON_GENERATIVE` but `probe` does not. Investigate launch/environment handling only. Do not run measured generation.

### `STARTUP_RECOVERED`

Both `plain` and `probe` reach `READY_NON_GENERATIVE`, with FA enabled and 512/512 startup evidence. Interpretation: the previous failure was launch/harness/environmental rather than a stable startup failure of the instrumented binary. Stop after the non-generative recovery record; the KV provenance probe remains unexercised and can then be resumed exactly once under a fresh execution handoff.

### `STARTUP_RECOVERY_INCONCLUSIVE`

Required evidence is missing or an identity/runtime precondition fails.

## Hard boundaries

- measured generation = 0
- KV dump = 0
- FA OFF = 0
- retry/replay/repair/tuning = 0
- #2934/#2947/9-request matrix rerun = 0
- protected v1 / production / RC1 / primary dirty checkout mutation = 0

This recovery step is not production qualification or release PASS.

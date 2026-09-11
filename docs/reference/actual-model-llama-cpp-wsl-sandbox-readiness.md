# llama.cpp WSL sandbox readiness

Status: evaluation-only execution boundary owned by #2603 after spent physical owner #2599 exposed a pre-server sandbox filesystem failure.

## Problem

The repository-owned WSL wrapper creates a fresh child `HOME` before invoking the inner llama.cpp transaction. The inner transaction later derives its one-process-lifetime server log from:

```text
Path.home() / "logs" / llama-server-<timestamp>-<pid>.log
```

#2599 established that proving only the child `HOME` itself writable is insufficient. Its wrapper and inner transaction were consumed once; `llama-server --version` and `nvidia-smi` succeeded, but the transaction terminated with `PermissionError: [Errno 1] Operation not permitted` before `_start_server()`, server lifecycle, host calls, provider calls, or semantic generations.

The first remaining filesystem operation in that order was creation of the nested `HOME/logs` directory.

## Current contract

Before crossing the wrapper-to-inner process boundary, the WSL wrapper must:

1. create its fresh runtime `HOME`;
2. prove the runtime `HOME` is a directory and writable with an actual create/write/unlink probe;
3. create `runtime_home/logs`;
4. prove that exact log directory is a directory and writable with the same create/write/unlink probe;
5. keep the workspace and artifact roots nonexistent/fresh for the inner transaction;
6. only then invoke the inner transaction once.

Failure of either write probe is pre-inner mechanical setup failure. The inner transaction must not be invoked, so no one-shot scientific owner is consumed by that failed controller/wrapper preparation.

Once the inner transaction is invoked, the ordinary exactly-once consumption rules remain unchanged.

## Non-change boundary

This readiness correction does not change:

- production cognition semantics;
- State or Continuity semantics;
- Stage R prompts, scenarios, oracle, scorer, parser or validator;
- model, quantization, context, slots, GPU offload or reasoning treatment;
- the transaction's server-log naming/location contract;
- host `--server-log-path` evidence;
- retry/replay/reseed/fallback policy;
- Core semantic fingerprint.

The correction only moves a filesystem prerequisite to the restartable side of the process/sandbox boundary.

## Regression requirement

Unit coverage must prove both:

- the nested `runtime_home/logs` directory exists and is writable before the mocked inner subprocess is invoked; and
- a failed nested-log readiness probe prevents the inner subprocess from being invoked.

> Prove every child filesystem prerequisite before spending the one-shot.
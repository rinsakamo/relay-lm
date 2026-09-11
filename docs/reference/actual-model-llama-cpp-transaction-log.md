# llama.cpp transaction-owned server log

Status: evaluation-only execution boundary owned by #2603 after spent physical owner #2599 exposed a pre-server child-HOME filesystem failure.

## Triggering evidence

#2599 crossed its one-shot wrapper/inner boundary exactly once and then terminated:

```text
disposition = HARNESS_INVALID
phase       = unexpected_exception
error       = PermissionError: [Errno 1] Operation not permitted
server lifecycle = 0
host/provider calls = 0
semantic generations = 0
```

Before the exception, `llama-server --version`, GGUF validation and `nvidia-smi` had completed. `_start_server()` was not reached. The first remaining uncaught filesystem operation was `_new_server_log_path()`, which attempted to create `Path.home() / "logs"` inside the child process.

The same inner transaction had already created its explicit workspace/artifact roots, and the final transaction summary was written successfully under the artifact root. The artifact root is therefore the already-proven transaction-owned writable evidence boundary.

## Current contract

The transaction allocates its per-launch llama-server log directly under the already-created `artifact_root`:

```text
artifact_root/
  stage-r-llama-cpp-transaction-summary.json
  llama-server-<UTC timestamp>-<pid>.log
  ... host evidence ...
```

`_new_server_log_path()` must:

- accept the current transaction `artifact_root` explicitly;
- require that root to exist as a directory;
- return one direct-child log path with the existing timestamp/PID uniqueness convention;
- perform no `Path.home()` lookup and create no `~/logs` directory.

The server launch still receives the exact selected path through `--log-file`. The citable host still receives the same exact path through `--server-log-path`. Final SHA-256 capture, owned-process teardown and evidence semantics are unchanged.

## Why wrapper precreation is not the final fix

Precreating `$HOME/logs` before the inner process can avoid the immediate directory-creation exception, but it does not prove that a sandboxed inner/server process may later create the actual logfile inside child HOME. Moving the transaction-owned log into the already-writable artifact root removes that undeclared HOME dependency rather than shifting the failure one operation later.

## Regression requirement

Deterministic coverage must prove:

- log allocation remains a direct child of `artifact_root`;
- log allocation succeeds without consulting `Path.home()`;
- ordinary owned-server lifecycle tests exercise the real log allocator rather than monkeypatching it away;
- log existence/hash and host handoff behavior remain unchanged.

## Non-change boundary

This correction does not change:

- production cognition semantics;
- State or Continuity semantics;
- Stage R prompts, scenarios, oracle, scorer, parser or validator;
- model, quantization, context, slots, GPU offload or reasoning treatment;
- request/generation accounting;
- retry/replay/reseed/fallback policy;
- Core semantic fingerprint.

> Transaction-owned evidence belongs in transaction-owned artifact space.
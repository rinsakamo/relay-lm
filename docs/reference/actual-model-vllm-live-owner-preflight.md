# Actual-model vLLM live-owner preflight

Status: current #1386 execution-infrastructure boundary for distinguishing pre-launch host cleanliness from post-launch ownership checks.

This surface does not choose cognition semantics, model quality, context defaults, GPU/KV admission, or benchmark outcomes. It consumes the process/listener ownership proof produced by `relaylm.actual_model_vllm_launch_preflight` after an owned vLLM runtime exists.

## Phase distinction

Before provider spawn, there is no transaction-owned runtime to exempt. Use the strict canonical-process guard:

```text
snapshot_vllm_processes()
  -> find_stale_vllm_processes(...)
  -> any canonical vLLM / VLLM::EngineCore process is a pre-launch conflict
```

`find_stale_vllm_processes(...)` intentionally remains command-identity based and strict. Do not weaken it to make a later live runtime pass.

After provider spawn and positive `RuntimeOwnershipAttestation`, the expected runtime is supposed to remain alive through readiness, capacity attestation, execution freeze, and semantic execution. At that point a canonical process is not stale merely because its argv identifies vLLM. Use the ownership-aware live guard:

```text
current RuntimeOwnershipAttestation
  + fresh HostProcess snapshot
  -> find_unowned_vllm_processes(...)
  -> positively owned PIDs are the expected live runtime
  -> any additional canonical vLLM PID remains an unowned conflict
```

Only PIDs contained in the current positive ownership attestation are exempted. The helper does not infer ownership from command names, parent relationships, listener similarity, historical PIDs, or a remembered run. Passing anything other than a current `RuntimeOwnershipAttestation` fails rather than manufacturing ownership.

## Execution ordering

The bounded qualification ordering is:

```text
PRE-LAUNCH
  strict stale-process cleanliness
  -> launch nonce-owned runtime
  -> positive process/listener ownership attestation
  -> STARTUP_READY
  -> fresh serving capacity
  -> ownership-aware live-process check
  -> EXECUTION_FROZEN
  -> semantic execution
```

A post-launch semantic/pre-freeze check must not re-run the pre-launch generic detector as though the current nonce-owned EngineCore were unrelated host residue. Conversely, the existence of one owned runtime never authorizes an unrelated canonical vLLM process; an extra unowned `vllm serve`, Python API server, or `VLLM::EngineCore` remains a fail-closed conflict.

## Evidence and freshness

The ownership attestation is volatile execution evidence. Its PIDs, nonce, listener ownership and process identities are valid only for the current bounded runtime. They must not be copied into later transaction authority.

A later transaction reacquires host cleanliness before launch, creates a new ownership boundary after spawn, and obtains a new attestation before using the live-owner guard.

> **Command-name staleness proves pre-launch cleanliness; nonce ownership proves which canonical processes are expected after launch. Never let the current proven-owned EngineCore become its own stale competitor.**

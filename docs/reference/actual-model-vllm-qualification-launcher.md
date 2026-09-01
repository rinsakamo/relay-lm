# Actual-model vLLM qualification launcher

Status: current #1386 execution binding for repository-owned vLLM process launch before actual-model or external-qualification semantic execution.

This surface composes the already-owned #2045/#2051 preflight primitives. It does not choose cognition semantics, benchmark answers, model quality, release context defaults, or final capacity authority.

## Required launch path

When RelayLM tooling starts a vLLM process for a citable actual-model or external-qualification transaction, it must use the repository-owned qualification launcher rather than issue a remembered `vllm serve` command directly.

```text
fresh host facts
  -> prepare_vllm_qualification_launch(...)
       -> negotiate_gpu_memory_utilization(...)
       -> selected reservation written into final argv
       -> negotiate_vllm_launch(...)
       -> fresh native RPC/temp path
  -> launch_vllm_qualification_runtime(...)
       -> launch_owned_vllm_runtime(...)
       -> wait_for_vllm_runtime_readiness(...)
  -> fresh serving-runtime capacity / launch attestation
  -> EXECUTION_FROZEN
  -> semantic execution
```

`actual_model_host` remains a provider-facing facade. It does not retroactively own process launch or make an already-running provider fresh.

## Bounded GPU reservation correction

`requested_utilization` is part of the declared preflight request. The launcher accepts at most one explicitly supplied `fallback_utilization`.

The fallback:

- must be strictly lower than the requested reservation;
- is considered only before execution freeze;
- must preserve the exact declared fixed context through the existing fresh `capacity_recheck` callback;
- never creates a reservation sweep or retry-until-pass loop;
- cannot change model, artifact, quantization, tokenizer, chat template, backend, decoding, reasoning, structured-output, or benchmark identity.

If the requested reservation is admissible, it remains selected. If neither the requested reservation nor the one lower fallback preserves the declared condition, launch preparation fails closed.

A successful lower selection retains the existing #2045 evidence semantics:

```text
reason = mechanical_gpu_reservation_reduced_before_freeze
reattest_required = true
```

The selected value, not the remembered requested value, is written into the exact final `--gpu-memory-utilization` argv.

## Command identity

The incoming direct vLLM command must contain exactly one `--gpu-memory-utilization` setting, in either split or `--flag=value` form. Its numeric value must agree with `requested_utilization`.

Duplicate, conflicting, missing, malformed, or mismatched reservation settings fail closed. All other semantic launch tokens remain unchanged except for the already-authorized omission of explicitly classified non-semantic legacy flags through `negotiate_vllm_launch(...)`.

The launcher does not lower `--max-model-len`, truncate input, or infer a new context to make a process fit.

## Runtime paths and ownership

The selected plan creates a fresh native-Linux runtime path through `prepare_vllm_runtime_paths(...)`. Caller environment may add unrelated variables but may not override the plan's RPC/temp path values.

Launch then uses the #2051 owned-process contract:

- direct child launch;
- fresh owner nonce and run identity;
- distinct process/session boundary;
- expected listener ownership;
- `wait_for_vllm_runtime_readiness(...)` before readiness can be claimed;
- owned cleanup on readiness failure.

An unrelated or stale listener cannot satisfy readiness.

## Capacity and freeze boundary

`VLLMQualificationLaunchPlan` is preflight evidence, not final capacity evidence. `VLLMQualificationRuntime` proves that the exact selected command reached owned readiness; it still does not authorize semantic execution by itself.

After readiness, the transaction must independently obtain fresh serving-runtime capacity and the current `LiveLaunchAdmissionAttestation` / equivalent execution identity required by its owner. Only then may the experiment freeze.

No value from an earlier launch, #2078/#2079 stop receipt, historical profiler, or previous capacity artifact becomes current merely because the launcher selected the same number.

## External benchmark use

External benchmark controllers may consume this launcher, but they may not add benchmark-specific admission rules. A matched A/B transaction must use the same final launch mechanics and frozen physical condition for both arms except for the explicitly declared independent variable.

Preflight correction is infrastructure convergence, not semantic retry. Once `EXECUTION_FROZEN` is emitted, reservation, context, model/runtime identity and other qualification-significant launch controls are immutable.

> **A negotiated reservation becomes citable only when the exact selected value is the one that actually launches the owned runtime and is freshly re-attested before freeze.**

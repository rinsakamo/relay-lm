# Actual-model vLLM qualification launcher

Status: current #1386 execution binding for repository-owned vLLM process launch before actual-model or external-qualification semantic execution.

This surface composes the already-owned #2045/#2051 preflight primitives. It does not choose cognition semantics, benchmark answers, model quality, release context defaults, or final capacity authority.

## Required launch path

When RelayLM tooling starts a vLLM process for a citable actual-model or external-qualification transaction, it must use the repository-owned qualification launcher rather than issue a remembered `vllm serve` command directly.

```text
fresh host facts
  -> prepare_vllm_qualification_launch(...)
       -> validate direct `vllm serve <model>` topology
       -> negotiate_gpu_memory_utilization(...)
       -> selected reservation written into final argv
       -> negotiate_vllm_launch(...)
       -> fresh native RPC/temp path
  -> launch_vllm_qualification_runtime(...)
       -> validate Unix IPC path budget
       -> launch_owned_vllm_runtime(...)
       -> wait_for_vllm_runtime_readiness(...)
  -> fresh serving-runtime capacity / launch attestation
  -> EXECUTION_FROZEN
  -> semantic execution
```

`actual_model_host` remains a provider-facing facade. It does not retroactively own process launch or make an already-running provider fresh.

## Operational convergence before citable qualification

A strict qualification transaction proves a predeclared physical condition; it should not also be the loop that discovers how to make the host/runtime start.

When unresolved non-semantic launch mechanics materially threaten a citable actual-model or external-qualification run, use a separate **operational convergence / rehearsal transaction** first.

```text
fixed scientific condition
  -> bounded non-semantic mechanical attempts
  -> one complete owned readiness + capacity recipe
  -> owned cleanup
  -> concise execution handoff / reusable-learning reconciliation
  -> fresh qualification transaction
       -> reacquire current authority and live host facts
       -> revalidate the selected recipe
       -> launch the one declared qualification condition
       -> freeze
       -> semantic execution
```

The convergence transaction may use the same repository-owned preparation, negotiation, launch, readiness, capacity, ownership, and cleanup primitives repeatedly. Multiple mechanical attempts are allowed **inside that convergence transaction** when each attempt is a deliberate correction grounded in an observable previous failure. Blind Cartesian sweeps, retry-until-semantic-PASS, and unbounded parameter search remain prohibited.

The convergence transaction must keep the qualification-significant scientific condition fixed. It must not vary or tune:

- RelayLM product commit/fingerprint or cognition semantics;
- model artifact/revision, quantization, backend/runtime version, or model runner;
- tokenizer or chat template;
- the declared fixed context window or benchmark workload;
- decoding, reasoning, or structured-output semantics;
- prompt, State, Continuity, MEMORY, retrieval, parser, Validator, or oracle behavior;
- benchmark answers, reference answers, or scoring inputs.

Subject to the owning execution contract, convergence may vary only non-semantic/mechanical launch facts needed to obtain owned readiness and capacity while preserving that fixed condition, including:

- native runtime root/path placement;
- caller environment delta, while runtime-owned keys remain protected;
- capability-negotiated non-semantic observability flags;
- process/session/listener placement where it does not alter the scientific condition;
- mechanical GPU reservation across distinct attempts when the same fixed context and capacity requirement remain unchanged.

The existing per-call launcher contract remains unchanged: one preparation request still accepts at most one explicitly supplied lower `fallback_utilization`. A convergence transaction may make a later, distinct preparation attempt with a newly declared requested reservation when the previous observable failure justifies it. A citable qualification transaction may not continue that search.

Operational convergence emits **zero qualification-semantic requests**. It must not run Stage R semantic turns, benchmark questions, crystallization quality generations, or any other model-facing request whose answer could influence the qualification result. Provider startup, owned readiness, and capacity acquisition are allowed because they establish the launch recipe rather than product quality.

A successful convergence recipe is historical planning evidence, not current host authority and not a qualification verdict. At minimum it should identify the stable launch class plus the selected mechanical recipe needed to reproduce it: command/capability shape, runtime-root/path policy, caller-env delta policy, selected reservation/KV/context relationship, process/listener expectations, and the readiness/capacity evidence references that demonstrated the recipe once. Volatile GPU free bytes, PIDs, listeners, nonces, and process state remain historical only.

The subsequent qualification must start from complete owned cleanup, reacquire fresh repository/owner/model/runtime/host/GPU/process/listener authority, freshly derive or revalidate every launch-significant value, and create a new provider process. It may use the converged recipe as the declared starting plan, but it may not reuse the rehearsal process, readiness, live capacity, PID/listener state, or volatile GPU facts as current evidence.

If the fresh qualification cannot reproduce the declared recipe, it stops before semantic execution. Do not search a second root, reservation, port, environment mapping, or command variant inside the qualification. Route the newly observed mechanical boundary back to a separate convergence/rehearsal owner if more host/runtime work is justified.

> **Converge mechanics first; qualify once.**

## Bounded GPU reservation correction

`requested_utilization` is part of the declared preflight request. The launcher accepts at most one explicitly supplied `fallback_utilization`.

The fallback:

- must be strictly lower than the requested reservation;
- is considered only before execution freeze;
- must preserve the exact declared fixed context through the existing fresh `capacity_recheck` callback;
- never creates a reservation sweep or retry-until-pass loop inside one launch preparation;
- cannot change model, artifact, quantization, tokenizer, chat template, backend, decoding, reasoning, structured-output, or benchmark identity.

If the requested reservation is admissible, it remains selected. If neither the requested reservation nor the one lower fallback preserves the declared condition, launch preparation fails closed.

A successful lower selection retains the existing #2045 evidence semantics:

```text
reason = mechanical_gpu_reservation_reduced_before_freeze
reattest_required = true
```

The selected value, not the remembered requested value, is written into the exact final `--gpu-memory-utilization` argv.

For an operational convergence transaction, a failed preparation/launch may inform a later distinct mechanical attempt under the convergence rules above. For a citable qualification transaction, the selected declared recipe is final for that attempt: no additional reservation search follows a material failure.

## Command identity

The incoming direct command must begin exactly with the current serving topology:

```text
vllm serve <model>
```

`vllm` is the required executable token, `serve` is the required subcommand, and the third token must be a non-option model positional. Missing or different executable/subcommand tokens, a missing model positional, or an option in the model position fail closed with `VLLMHostPreflightError` during `prepare_vllm_qualification_launch(...)`, before GPU admission can produce a launchable plan and before any provider process is spawned.

The launcher does not infer or insert `serve`, repair positional ordering, substitute a model, or reinterpret another vLLM subcommand as serving intent. A malformed caller command is an execution-preflight failure, not a reason to spend a provider-start attempt.

The direct command must also contain exactly one `--gpu-memory-utilization` setting, in either split or `--flag=value` form. Its numeric value must agree with `requested_utilization`.

Duplicate, conflicting, missing, malformed, or mismatched reservation settings fail closed. All other semantic launch tokens remain unchanged except for the already-authorized omission of explicitly classified non-semantic legacy flags through `negotiate_vllm_launch(...)`.

The launcher does not lower `--max-model-len`, truncate input, or infer a new context to make a process fit.

## Runtime paths and ownership

The selected plan creates a fresh native-Linux runtime path through `prepare_vllm_runtime_paths(...)`. Caller environment may add unrelated variables but may not override the plan's RPC/temp path values.

Immediately before spawning the provider, the qualification launcher also checks that the filesystem-encoded `VLLM_RPC_BASE_PATH` can fit the current pinned vLLM V2 Unix IPC endpoint shape. The guard reserves 37 bytes for the `/` separator plus the 36-character vLLM-generated UUID suffix and requires the complete pathname to remain within the conservative 107-byte Unix-domain-socket pathname budget.

If that budget cannot be satisfied, launch fails closed with `VLLMHostPreflightError` **before** `launch_owned_vllm_runtime(...)` is called. The launcher never silently reroots or shortens a scientific condition.

In a citable qualification transaction, an overlong path is terminal for that qualification attempt: do not choose another root or rescue the run after the failure. In a separate operational convergence transaction, the failed path may be recorded, owned resources cleaned up, and a later mechanical attempt may select another freshly attested native-Linux root while the scientific condition remains fixed. The existing `/tmp` default remains only a default or a recipe candidate, not remembered host authority.

This pathname gate is execution infrastructure only. It does not change model, artifact, context, GPU/KV capacity, decoding, reasoning, prompt, scenario, or semantic qualification identity.

Launch then uses the #2051 owned-process contract:

- direct child launch;
- fresh owner nonce and run identity;
- distinct process/session boundary;
- expected listener ownership;
- `wait_for_vllm_runtime_readiness(...)` before readiness can be claimed;
- owned cleanup on readiness failure.

An unrelated or stale listener cannot satisfy readiness.

Every convergence attempt and every qualification attempt receives fresh ownership identity and performs owned cleanup before a later attempt or transaction may start. A successful rehearsal process is never reused as the citable qualification process.

## Capacity and freeze boundary

`VLLMQualificationLaunchPlan` is preflight evidence, not final capacity evidence. `VLLMQualificationRuntime` proves that the exact selected command reached owned readiness; it still does not authorize semantic execution by itself.

During operational convergence, owned readiness plus capacity may establish that one mechanical recipe is viable, but it never emits `EXECUTION_FROZEN` for a semantic qualification and never converts the rehearsal capacity observation into current qualification authority.

For the subsequent citable transaction, after fresh owned readiness the transaction must independently obtain fresh serving-runtime capacity and the current `LiveLaunchAdmissionAttestation` / equivalent execution identity required by its owner. Only then may the experiment freeze.

No value from an earlier convergence launch, #2078/#2079 stop receipt, historical profiler, or previous capacity artifact becomes current merely because the launcher selected the same number. Stable recipe identity may guide the fresh plan only where current owner authority permits that planning role.

## External benchmark use

External benchmark controllers may consume this launcher, but they may not add benchmark-specific admission rules. A matched A/B transaction must use the same final launch mechanics and frozen physical condition for both arms except for the explicitly declared independent variable.

When launch mechanics are unresolved, converge them without benchmark-semantic requests before spending a citable matched A/B qualification. Do not use benchmark answers or arm outcomes to choose the mechanical recipe.

Preflight correction and operational convergence are infrastructure work, not semantic retry. Once a citable qualification begins from its declared recipe, and especially once `EXECUTION_FROZEN` is emitted, reservation, context, model/runtime identity and other qualification-significant launch controls are immutable for that qualification.

> **A negotiated reservation becomes citable only when the exact selected value is freshly revalidated, actually launches the owned qualification runtime, and is re-attested before freeze.**

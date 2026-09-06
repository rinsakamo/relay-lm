# Actual-model vLLM reference producer launcher

Status: current #1386 repository-owned launch surface for zero-semantic `VLLMTokenCapacityReference` production. This surface is intentionally separate from the fixed-window semantic qualification launcher.

## Purpose

A citable token-capacity reference is produced **before** a semantic Stage R owner selects a legal execution token window.

Therefore reference production must not require, infer, or borrow a semantic `required_context_window` merely to launch the profiler/final capacity-measurement pair.

Use:

```text
prepare_vllm_reference_launch(...)
launch_vllm_reference_runtime(...)
```

from `relaylm.actual_model_vllm_reference_launcher` for that producer phase.

The fixed-window semantic surface remains:

```text
prepare_vllm_qualification_launch(...)
launch_vllm_qualification_runtime(...)
```

and continues to require one positive integer `required_context_window` plus exactly one matching integer `--max-model-len`.

## Producer model-length identity

The current pinned-vLLM reference producer uses the repository-authorized auto-fit representation:

```text
--max-model-len auto
```

Split and `--flag=value` CLI spellings are equivalent command encodings; the semantic value must be exactly `auto` and must occur exactly once.

This `auto` value is **not** a Stage R target window, not a release Cognitive Budget, and not a persisted selected context. It is launch-capability measurement machinery. The successful final runtime must expose its live serving `max_model_len` / KV capacity through the existing capacity/reference producer path, and the resulting citable reference records the attested capacity/geometry rather than treating the literal word `auto` as capacity evidence.

Do not replace `auto` with:

- a historical Stage R template value;
- 1616;
- 4096;
- a model-config maximum chosen by the controller;
- a value derived from transient free VRAM; or
- a #1388 release recommendation.

A later semantic owner chooses its legal fixed token window **after** a compatible citable reference exists.

## Mechanical GPU reservation

Reference production is measuring the launch class, so it cannot perform a semantic-context capacity recheck before the capacity reference exists.

`prepare_vllm_reference_launch(...)` therefore owns only bounded **mechanical reservation feasibility**:

1. require fresh positive `free_bytes` and `total_bytes` with `free_bytes <= total_bytes`;
2. require exactly one declared requested `--gpu-memory-utilization` value in `(0, 1]` matching `requested_utilization`;
3. optionally accept one explicitly supplied lower fallback reservation;
4. select the highest declared candidate that does not exceed the fresh `free_bytes / total_bytes` fraction;
5. write that selected reservation into the exact launch argv;
6. perform no semantic token-window capacity callback.

This is not permission to sweep reservations. A strict Qualification consumes only the candidate count its owning transaction permits. If its one declared reservation is not currently available, stop rather than selecting a new value.

The selected reservation remains physical launch identity and fresh re-attestation is required before later physical phases where current authority requires it.

## Required command shape

The producer accepts only direct serving topology:

```text
<vllm executable> serve <model>
```

The executable basename must be `vllm`; an exact prepared absolute executable path is allowed. The third token must be a non-option model positional.

The command must contain exactly one:

```text
--max-model-len auto
--gpu-memory-utilization <declared numeric value>
```

Duplicate, missing, malformed, non-auto model-length, or mismatched GPU-reservation settings fail closed before launch.

All other required launch flags remain subject to current `negotiate_vllm_launch(...)` support. Only flags already classified as non-semantic by that current contract may be omitted when unsupported.

## Runtime path and ownership

The producer reuses the current repository primitives for:

- `prepare_vllm_runtime_paths(...)`;
- native-Linux RPC/temp placement;
- conservative Unix-domain-socket pathname budget;
- protected runtime-owned environment values;
- `launch_owned_vllm_runtime(...)`;
- expected endpoint ownership; and
- `wait_for_vllm_runtime_readiness(...)` with owned cleanup on failure.

GPU/NVML/CUDA observations and device-discovery-dependent producer launches follow `actual-model-vllm-qualification-launcher.md`: when the workflow provides the established authorized elevated/non-sandbox GPU-visible execution path, use that physical context rather than treating ordinary sandbox GPU invisibility as host failure.

## Profiler/final reference sequence

The producer launch surface is valid for both phases of the current reference acquisition:

```text
fresh physical authority
  -> repository capability surface
  -> profiler command
       --max-model-len auto
       no explicit KV bytes
  -> prepare_vllm_reference_launch(...)
  -> owned profiler readiness
  -> canonical profiler recommendation
  -> owned cleanup
  -> fresh owner-required volatile authority
  -> final command
       --max-model-len auto
       exact explicit KV bytes from profiler recommendation
  -> prepare_vllm_reference_launch(...)
  -> owned final readiness
  -> live max_model_len / KV capacity / geometry observation
  -> VLLMTokenCapacityReferenceEvidence
  -> atomic persist + strict reload + compatibility checks
  -> REFERENCE_READY
```

The same launch class, runtime/model/runner identity, and producer model-length representation remain fixed. The explicit KV bytes are measurement output from the single profiler condition, not a semantic target-window conversion.

## Boundary with Stage R

After `REFERENCE_READY`:

```text
bounded semantic owner selects legal integer target_model_len
  -> require_compatible_reference(...)
  -> reference converts target_model_len to conservative KV bytes
  -> fresh physical admission
  -> fixed-window semantic qualification launcher
       --max-model-len <selected integer>
  -> Stage R
```

The two launch surfaces must not be conflated:

```text
reference producer
  auto-fit measurement
  no semantic context selection

semantic qualification
  explicit integer target
  fixed-window capacity preservation
```

> **Measure the ruler in auto-fit mode. Use the ruler later to admit a separately selected semantic window.**

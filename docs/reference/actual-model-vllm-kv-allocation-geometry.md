# Actual-model vLLM KV allocation geometry

Status: current #1386 execution-infrastructure authority for converting a fixed token window into explicit pinned-vLLM KV bytes. #1388 remains the owner of Cognitive Budget/default selection.

This surface refines the continuous byte/token bound described by `actual-model-vllm-functional-acceptance.md`. The continuous bound remains required, but it is not by itself sufficient when the pinned runtime allocates KV in discrete pages/blocks.

## Stable launch-class reference

A reusable `VLLMTokenCapacityReference` must bind one citable same-launch-class observation containing:

- conservative non-KV envelope bytes;
- explicit KV-cache bytes from the successful reference launch;
- resulting attested KV token capacity;
- KV allocation-unit bytes;
- KV allocation-unit token capacity;
- the same target/runtime/runner launch-class identity that makes those values applicable.

Allocation-unit geometry is launch-class evidence. It is not inferred from current free VRAM, a remembered PID, a transaction-local utilization fraction, or a historical absolute KV value.

The reference fails closed if its declared whole-allocation-unit capacity cannot carry its own attested KV token capacity.

## Fixed-window conversion

For a positive selected `target_model_len` that does not exceed the attested reference capacity:

```text
continuous_kv_bytes =
    ceil(reference_kv_cache_bytes / reference_kv_cache_capacity_tokens)
    * target_model_len

allocation_kv_bytes =
    ceil(target_model_len / kv_allocation_unit_tokens)
    * kv_allocation_unit_bytes

required_kv_cache_bytes =
    max(continuous_kv_bytes, allocation_kv_bytes)

required_total_bytes =
    reference_non_kv_bytes + required_kv_cache_bytes
```

The maximum preserves both conservative properties: the historical byte/token upper bound cannot be weakened by page geometry, and page/block rounding cannot be lost to continuous arithmetic.

There is no universal `+1 page` rule and no special case for 4096. If a target happens to cross an allocation boundary, the ordinary ceiling operation requests the additional unit. A different target or launch class follows the same rule.

`target_model_len` above the attested token capacity still requires fresh launch-capability evidence. Allocation geometry does not authorize extrapolation.

## Fresh host admission

`VLLMLaunchMemoryAdmission.for_token_window(...)` consumes the page-conservative `required_kv_cache_bytes`. Fresh `free_bytes` remains only a feasibility observation:

```text
fresh_free_bytes >= required_total_bytes
```

`gpu_memory_utilization` is mechanically derived from the resulting required envelope and total GPU bytes. More free VRAM does not increase the selected context window or KV allocation, and less free VRAM does not silently shrink them.

Final launch memory identity remains:

```text
--gpu-memory-utilization <required-envelope-derived value>
--kv-cache-memory-bytes <page-conservative required KV bytes>
--max-model-len <fixed selected target>
```

## Evidence discipline

Historical execution can demonstrate that continuous arithmetic was insufficient and motivate this invariant. Its absolute KV bytes, utilization, free-memory state, PIDs, paths and live capacity remain historical unless a later owner explicitly requalifies them.

A later physical transaction reacquires the applicable launch-class geometry and fresh host admission before provider spawn. It does not copy one rehearsal's absolute memory recipe into product defaults.

> **Select the semantic window elsewhere, preserve the continuous upper bound, round the physical carrier in the runtime's attested allocation units, and use fresh free VRAM only to decide whether the host can carry that fixed requirement.**

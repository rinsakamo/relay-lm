# Actual-model vLLM KV allocation geometry

Status: current #1386 execution-infrastructure authority for converting a fixed token window into explicit pinned-vLLM KV bytes. The citable reference contract supports heterogeneous shared-pool KV block demand; #1388 remains the owner of Cognitive Budget/default selection.

This surface refines the continuous byte/token bound described by `actual-model-vllm-functional-acceptance.md`. The continuous bound remains required, but it is not by itself sufficient when the pinned runtime allocates one request through multiple KV groups with discrete shared-pool blocks.

## Stable launch-class reference

A reusable `VLLMTokenCapacityReference` binds one citable same-launch-class successful observation containing:

- conservative non-KV envelope bytes;
- explicit KV-cache bytes from the successful reference launch;
- resulting attested KV token capacity;
- `kv_pool_block_bytes`, the exact bytes consumed by one block id in the runtime's shared KV pool;
- a canonical non-empty set of conservative KV allocation-demand terms.

Each `VLLMKVAllocationDemand` term records:

- `multiplicity`: how many equivalent KV groups have this request-allocation shape;
- `tokens_per_block`: the effective request-token span represented by one block for those groups;
- `fixed_blocks_per_request`: any non-negative source-attested constant block overhead required by that group class.

Equivalent terms are merged and sorted canonically. Evidence identity therefore depends on geometry, not input order or duplicated spelling of the same geometry.

The reference is consumable only through a compatible stable launch-class identity. Current `VLLMTokenCapacityLaunchClass` binds mechanically attestable fields:

- exact target id;
- immutable target artifact revision;
- exact target digest;
- exact backend version;
- exact pinned backend source revision;
- model-runner trajectory (`v1` or `v2`);
- GPU compute capability major/minor;
- GPU total memory bytes.

Compute capability and total memory describe the reusable hardware capability class without persisting a GPU UUID or inventing an opaque host-class label. Current free VRAM is deliberately excluded from compatibility and is reacquired for every admission.

Pool-block and per-group demand geometry are launch-class evidence. They are not inferred from current free VRAM, a remembered PID, a transaction-local utilization fraction, or a historical absolute KV value.

A producer may omit a finite-window plateau from a demand term only when doing so makes the recorded demand more conservative. It must never omit or simplify runtime behavior in a way that understates required shared-pool blocks. If the exact runtime geometry cannot be reduced to the recorded terms without guessing or understatement, reference acquisition fails closed.

The schema also fails closed on malformed/empty demands, non-positive pool-block geometry, or a demand shape that cannot carry even one token inside the attested successful-launch KV pool.

## Citable reference evidence

`VLLMTokenCapacityReferenceEvidence` is the producer-owned immutable artifact that makes the reference reusable instead of reconstructing it from a rehearsal log.

One format-v2 artifact is created from one successful owned launch observation by `VLLMTokenCapacityReferenceEvidence.from_successful_launch(...)`. It records:

- the stable `VLLMTokenCapacityLaunchClass` compatibility identity;
- the startup free-memory observation used to derive the conservative launch envelope;
- the derived non-KV envelope;
- explicit reference KV bytes;
- attested reference token capacity;
- exact shared-pool block bytes;
- canonical heterogeneous allocation-demand terms;
- a versioned deterministic `amkvref-<sha256>` evidence id.

The superseded scalar allocation-unit format has no successful physical citable artifact and is not a parallel authority. The current loader accepts only the current format.

`write_vllm_token_capacity_reference_evidence(...)` persists the artifact atomically. `load_vllm_token_capacity_reference_evidence(...)` strictly validates its schema, content-derived evidence id, filename, successful-launch envelope, and allocation geometry before returning it.

A later consumer does not receive a `VLLMTokenCapacityReference` merely because an artifact parses. It supplies the fresh expected `VLLMTokenCapacityLaunchClass` to `require_compatible_reference(...)`; an exact mismatch in target identity/revision/digest, backend version/source, model runner, compute capability, or total GPU memory fails closed.

The successful launch's `startup_free_bytes` is immutable observation provenance used to derive the conservative non-KV envelope; it is not a later host-admission value or a compatibility selector by itself. PID, PGID, session, nonce, listener ownership, GPU UUID, RPC/temp paths and later live GPU free memory are not stored as reusable process authority.

A reference-acquisition transaction may emit this artifact only after a successful owned runtime and capacity attestation establish all required geometry. Source-level geometry without a successful same-launch-class observation is insufficient. Conversely, a later qualification consumes the persisted stable geometry but still reacquires fresh host free/total memory and current process/listener authority.

## Fixed-window conversion

For a positive selected `target_model_len` that does not exceed the attested reference capacity:

```text
kv_bytes_per_token_upper =
    ceil(reference_kv_cache_bytes / reference_kv_cache_capacity_tokens)

continuous_kv_bytes =
    min(
        reference_kv_cache_bytes,
        kv_bytes_per_token_upper * target_model_len
    )

allocation_blocks =
    sum(
        multiplicity
        * (
            ceil(target_model_len / tokens_per_block)
            + fixed_blocks_per_request
        )
        for each canonical allocation-demand term
    )

allocation_kv_bytes =
    min(
        reference_kv_cache_bytes,
        allocation_blocks * kv_pool_block_bytes
    )

required_kv_cache_bytes =
    max(continuous_kv_bytes, allocation_kv_bytes)

required_total_bytes =
    reference_non_kv_bytes + required_kv_cache_bytes
```

The maximum preserves two independent conservative bounds: byte/token arithmetic cannot be weakened by block geometry, and whole-block/group demand cannot be lost to continuous arithmetic.

Both component bounds are capped at the successful launch's attested explicit KV bytes. That cap is itself a proven sufficient upper carrier for every target at or below the attested token capacity; it prevents an intentionally uncapped conservative term from demanding more than the known successful full reference pool.

There is no universal `+1 page` rule, no universal tokens-per-block value, and no special case for 4096. A source-attested group class may carry a fixed block offset when its runtime allocator requires one; another group need not. Heterogeneous group widths remain distinct demand terms while all groups draw from the same attested shared-pool block byte cost.

`target_model_len` above the attested token capacity still requires fresh launch-capability evidence. Allocation geometry does not authorize extrapolation.

## Fresh host admission

`VLLMLaunchMemoryAdmission.for_token_window(...)` consumes the heterogeneous block-conservative `required_kv_cache_bytes`. Fresh `free_bytes` remains only a feasibility observation:

```text
fresh_free_bytes >= required_total_bytes
```

`gpu_memory_utilization` is mechanically derived from the resulting required envelope and total GPU bytes. More free VRAM does not increase the selected context window or KV allocation, and less free VRAM does not silently shrink them.

Final launch memory identity remains:

```text
--gpu-memory-utilization <required-envelope-derived value>
--kv-cache-memory-bytes <block-conservative required KV bytes>
--max-model-len <fixed selected target>
```

## Evidence discipline

Historical execution can reveal that a scalar allocation-unit model was insufficient and motivate this invariant. Its absolute KV bytes, utilization, free-memory state, PIDs, paths and live capacity remain historical unless a later owner explicitly produces citable evidence under the current artifact contract.

A later physical qualification loads one compatible reference artifact and separately reacquires fresh host admission before provider spawn. It does not copy one rehearsal's absolute memory recipe into product defaults.

> **Select the semantic window elsewhere, persist one successful launch's shared-pool bytes plus conservative per-group block demand as identity-bound evidence, preserve the independent byte/token upper bound, and use fresh free VRAM only to decide whether the host can carry that fixed requirement.**

---
relaylm_doc_type: evidence
relaylm_authority: mvp2_runtime_memory_light_apply_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current runtime request-compilation application behavior
  - current memory_light forwarding, streaming, or diagnostics-header behavior
  - current config defaults
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: 71385a5f2ccebbe89e81b9369f5c5abce6a98114
relaylm_source_origin_commit: e5b6a247134be4e52cc47c223e44af3a35c8896e
relaylm_source_pr: 22
relaylm_recorded_on: 2026-05-21
relaylm_source_blob: 63a3edfaaa7e6177f61c69611cdc82c505dbbf35
relaylm_source_content_sha256: f3a3eec0fadd4c729254378b8c76ccdf00d3887f249fa8ded7960afc4eaed818
relaylm_pre_cutover_blob: 63a3edfaaa7e6177f61c69611cdc82c505dbbf35
relaylm_pre_cutover_content_sha256: f3a3eec0fadd4c729254378b8c76ccdf00d3887f249fa8ded7960afc4eaed818
relaylm_exact_source_snapshot: mvp2_runtime_memory_light_apply-source.txt
---
# MVP-2 Runtime Memory-Light Apply Evidence

This frozen record preserves the first connection of the memory-light profile-compilation helper to `/v1/chat/completions` as historical implementation evidence. Note this is a distinct source from the earlier [MVP-2 memory-light apply](mvp2_memory_light_apply.md) evidence record (PR #21); this record covers PR #22, which wired that helper into the runtime request path.

## Exact source

The submitted source is retained byte-for-byte as [mvp2_runtime_memory_light_apply-source.txt](mvp2_runtime_memory_light_apply-source.txt).

```text
old path: docs/mvp/mvp2_runtime_memory_light_apply.md
source PR: #22, merge e5b6a247134be4e52cc47c223e44af3a35c8896e
source commit: 71385a5f2ccebbe89e81b9369f5c5abce6a98114
source blob: 63a3edfaaa7e6177f61c69611cdc82c505dbbf35
source content SHA-256: f3a3eec0fadd4c729254378b8c76ccdf00d3887f249fa8ded7960afc4eaed818
disposition: evidence_retained
```

No post-source modification exists; the source blob equals the pre-cutover blob. The only intervening commit (`bde89c10732832c2e41d9b3a128620c3e66ec17d`) moved the file under `docs/mvp/` without changing its content.

## Current authority

Current request-compilation application behavior, the full `CompiledRequest` field set, and current compile-decision diagnostics belong to [Runtime Compile Current/Target](../../contracts/runtime_compile_current_target.md) and [Context Compiler Contract](../../contracts/context_compiler_contract.md), and to [Runtime Architecture](../../architecture/runtime_architecture.md) for mode-contract and managed-apply behavior. Repository-wide current implementation status remains owned by [Project Status](../../PROJECT_STATUS.md).

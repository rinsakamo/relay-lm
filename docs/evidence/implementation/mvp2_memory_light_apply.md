---
relaylm_doc_type: evidence
relaylm_authority: mvp2_memory_light_apply_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current memory, RelayCTX, or persistence behavior
  - current operator instructions
  - exact compile-apply contracts
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: ed5119b5fe3a07cd395ebd0a4cadaca7945e9599
relaylm_recorded_on: 2026-05-21
relaylm_source_blob: 774819182af6268dc95c9ca5a61571890085c414
relaylm_source_content_sha256: b420a9c6c7b2f221996d6b30c1739fe4de62d0b070f791b998bd48728e434c6c
---
# MVP-2 Memory-Light Apply Helper Evidence

This frozen record preserves the early MVP-2 `memory_light`-mode payload-compilation helper as historical implementation evidence. The `CompiledRequest` helper and its "out of scope" statement belong to that source boundary and are not current memory, RelayCTX, or persistence authority.

## Exact source

The submitted source is retained byte-for-byte as [mvp2_memory_light_apply-source.txt](mvp2_memory_light_apply-source.txt).

```text
old path: docs/mvp/mvp2_memory_light_apply.md
source PR: #21, merge 793dbfa49798a4531039bdd6193c51db191d529d
source commit: ed5119b5fe3a07cd395ebd0a4cadaca7945e9599
source blob: 774819182af6268dc95c9ca5a61571890085c414
source content SHA-256: b420a9c6c7b2f221996d6b30c1739fe4de62d0b070f791b998bd48728e434c6c
disposition: evidence_retained
```

No post-source modification exists; the source blob equals the pre-cutover blob.

## Current authority

Current request compilation behavior belongs to [Runtime Compile Current/Target](../../contracts/runtime_compile_current_target.md) and [Context Compiler Contract](../../contracts/context_compiler_contract.md), which now document `compile_chat_payload_if_enabled` and `CompiledRequest` as live contracts. Repository-wide current implementation status remains owned by [Project Status](../../PROJECT_STATUS.md).

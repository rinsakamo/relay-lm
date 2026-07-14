---
relaylm_doc_type: evidence
relaylm_authority: mvp2_context_compiler_contract_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current context-block primitives, ordering, or stable-prefix block set
  - the retired `room_anchor` placeholder identity or position
  - current compiler wiring into the request path
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: cb2ebc287e6dbe6c85d1285af3584b6484575b63
relaylm_source_origin_commit: 9e22a95ce1cb7977e9da2829b3a38045789093d8
relaylm_source_pr: 13
relaylm_recorded_on: 2026-05-20
relaylm_source_blob: 82054c9ab18c2205ef0b2e82fec48a92083b4257
relaylm_source_content_sha256: 0e38b8a5515b26f4ee0f211487d4a859f7b7a5a3fb2ebcbd9a87fdfc4eac9128
relaylm_pre_cutover_blob: 82054c9ab18c2205ef0b2e82fec48a92083b4257
relaylm_pre_cutover_content_sha256: 0e38b8a5515b26f4ee0f211487d4a859f7b7a5a3fb2ebcbd9a87fdfc4eac9128
relaylm_exact_source_snapshot: mvp2_context_compiler_contract-source.txt
---
# MVP-2 Context Compiler Contract Evidence

This frozen record preserves the first code-level MVP-2 context-compiler contract as historical implementation evidence. The primitive names (`StabilityClass`, `BlockType`, `ContextBlock`, `render_context_blocks()`, `validate_block_order()`, `build_placeholder_persona_blocks()`) and the `stable_prefix -> slow_prefix -> dynamic_suffix` ordering rule remain current, but the concrete stable-prefix block list in this source is stale: `room_anchor` is a retired MVP-2-era placeholder, replaced by `relationship_anchor` in the current implementation. It must not be reintroduced as current merely because this source once called it a contract.

## Exact source

The submitted source is retained byte-for-byte as [mvp2_context_compiler_contract-source.txt](mvp2_context_compiler_contract-source.txt).

```text
old path: docs/mvp/mvp2_context_compiler_contract.md
source PR: #13, merge 9e22a95ce1cb7977e9da2829b3a38045789093d8
source commit: cb2ebc287e6dbe6c85d1285af3584b6484575b63
source blob: 82054c9ab18c2205ef0b2e82fec48a92083b4257
source content SHA-256: 0e38b8a5515b26f4ee0f211487d4a859f7b7a5a3fb2ebcbd9a87fdfc4eac9128
disposition: evidence_retained
```

No post-source modification exists; the source blob equals the pre-cutover blob. The only intervening commit (`73e82797f749280db2c5f1e68c62ae03f08864e3`) moved the file under `docs/mvp/` without changing its content.

## Current authority

Current context-block primitives, the stability-order rule, and the corrected stable-prefix block set (`common_runtime_policy`, `character_soul_anchor`, `character_output_policy`, `relationship_anchor` — not `room_anchor`) belong to [Context Compiler Contract](../../contracts/context_compiler_contract.md) and are implemented in `relaylm/compiler.py`. Repository-wide current implementation status remains owned by [Project Status](../../PROJECT_STATUS.md).

---
relaylm_doc_type: evidence
relaylm_authority: mvp2_gated_compile_decision_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current payload-rewriting or apply behavior
  - current FastAPI request-compiler integration
  - current memory/RAG authority
  - the complete target CompileDecision state taxonomy
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: b9ccba293a780c4da3c89b61b53c6f7e739290c8
relaylm_source_origin_commit: 4a720954d1fed12dbbe0f6b2ba69b25082511ddd
relaylm_source_pr: 20
relaylm_recorded_on: 2026-05-21
relaylm_source_blob: 6da4b16095413191368ea2a75333a094d550977b
relaylm_source_content_sha256: 0b7437684b4e64c265ef3227cea5f075acc0440eaa1f20be4bbe979e63f76809
relaylm_pre_cutover_blob: 6da4b16095413191368ea2a75333a094d550977b
relaylm_pre_cutover_content_sha256: 0b7437684b4e64c265ef3227cea5f075acc0440eaa1f20be4bbe979e63f76809
relaylm_exact_source_snapshot: mvp2_gated_compile_decision-source.txt
---
# MVP-2 Gated Compile Decision Evidence

This frozen record preserves the first explicit MVP-2 compile-apply gate as historical implementation evidence. The `pass_through`/`memory_light`/`memory_full` gate rule and the `CompileApplyDecision`/`decide_compile_apply()` pairing remain current, but the source's "Out of scope" list (no payload rewriting, no FastAPI integration, no memory/RAG) is factually superseded: all three have since been implemented.

## Exact source

The submitted source is retained byte-for-byte as [mvp2_gated_compile_decision-source.txt](mvp2_gated_compile_decision-source.txt).

```text
old path: docs/mvp/mvp2_gated_compile_decision.md
source PR: #20, merge 4a720954d1fed12dbbe0f6b2ba69b25082511ddd
source commit: b9ccba293a780c4da3c89b61b53c6f7e739290c8
source blob: 6da4b16095413191368ea2a75333a094d550977b
source content SHA-256: 0b7437684b4e64c265ef3227cea5f075acc0440eaa1f20be4bbe979e63f76809
disposition: evidence_retained
```

No post-source modification exists; the source blob equals the pre-cutover blob. The only intervening commit (`225e674c11489e94416af59c7d379b2e48a92152`) moved the file under `docs/mvp/` without changing its content.

## Current authority

Current `CompileApplyDecision` fields, `decide_compile_apply()` semantics, and the full current/target compile-decision taxonomy belong to [Runtime Compile Current/Target](../../contracts/runtime_compile_current_target.md), [Runtime Compile Artifact Contract](../../contracts/runtime_compile_artifact_contract.md), and [Runtime Compile and Checkpoint Architecture](../../architecture/runtime/compile-and-checkpoint.md), and are implemented in `relaylm/compile_gate.py`. Repository-wide current implementation status remains owned by [Project Status](../../PROJECT_STATUS.md).

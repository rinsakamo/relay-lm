---
relaylm_doc_type: evidence
relaylm_authority: audit_trace_projection_boundary_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current audit-trace persistence and typed-projection authority
  - current TOP_LEVEL_PROJECTORS and PIPELINE_NODE_PROJECTORS registries
  - current PipelineNodeResult contract and node-name registry
  - current trace serialization and legacy JSONL-read behavior
  - current privacy/content-free boundary validation coverage
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: 28f3500c9208e6a686b27478b0ea4948f64aa15b
relaylm_source_origin_commit: 44da3d98ae43c05dfb64ab8e1a7c555aa9c25190
relaylm_source_pr: 264
relaylm_recorded_on: 2026-06-14
relaylm_source_blob: bc042c8370d88d995df8a454c920f80503ae558d
relaylm_source_content_sha256: 11278cb325dea1ba97b7fd006d0267d038a006df601f6b3edd24b204e0d0683c
relaylm_pre_cutover_blob: bc042c8370d88d995df8a454c920f80503ae558d
relaylm_pre_cutover_content_sha256: 11278cb325dea1ba97b7fd006d0267d038a006df601f6b3edd24b204e0d0683c
relaylm_exact_source_snapshot: audit_trace_projection_boundary-source.txt
---
# MVP Audit Trace Projection Boundary Evidence

This frozen record preserves the short MVP note that first described RelayLM's typed audit-trace projection boundary, as historical implementation evidence. The source commit is `28f3500c9208e6a686b27478b0ea4948f64aa15b` ("docs: describe typed audit projection boundary", author/commit date 2026-06-14T07:31:27+00:00), brought into `main` by a genuine, non-squash merge: `44da3d98ae43c05dfb64ab8e1a7c555aa9c25190` ("Merge pull request #264 from rinsakamo/p0-a1-content-free-trace-contract", 2026-06-17T20:36:27+09:00). Unlike the squash-merge precedent (MVP-47, PR #241, source and origin commit identical) and the direct-push precedent (MVP-48, no PR at all), this record's source commit and origin/merge commit are two distinct, independently reachable commits: the source commit sits on the merged-in feature branch and was preserved intact rather than squashed, confirmed by walking the merge commit's two parents (`34a1e8936082ba817508e1b90cbc689d79c966b9` pre-merge mainline, `85030ac0ef4ad6b06ac39112fcf6bd639d229c50` branch tip) and by `git merge-base --is-ancestor`. Source PR #264 was read directly from the merge commit's subject and body, not guessed.

This file was never renamed and has exactly one commit in its entire repository history (`git log --all --follow`, verified after confirming the working clone is not shallow). No post-source modification commits exist: the source blob and today's pre-cutover blob are byte-identical (`bc042c8370d88d995df8a454c920f80503ae558d`, content SHA-256 `11278cb325dea1ba97b7fd006d0267d038a006df601f6b3edd24b204e0d0683c`), independently recomputed with `git rev-parse`, `git cat-file`, `git hash-object`, and `sha256sum` (all four agree). The advisory pre-cutover blob hash supplied with this cutover's task brief was confirmed correct by this independent recomputation, not copied. This file has zero live referrers anywhere in the repository: an exact-path and bare-filename `git grep` across the full tree returns no hits outside the file's own single historical commit, and it is absent from `docs/mvp/README.md`, `docs/evidence/implementation/README.md`, and every other index — a stronger case than any prior cutover record in this ledger, none of which had zero referrers.

All five substantive statements in the source are independently verified against current code. Every one is already covered by an existing current authority; none is a unique rule that would otherwise disappear with this file's retirement:

1. "The P0-A1 trace boundary is typed projection, not heuristic recursive sanitization." — Confirmed true: `relaylm/audit_projection.py::project_audit_metadata()` dispatches through a literal, statically-defined registry, not recursive key-name inference. Already stated by [Audit Trace Content-Free Contract](../../architecture/audit_trace_content_free_contract.md).
2. "Supported top-level projectors live in `relaylm/audit_projection.py`... A new runtime artifact is not persisted until a projector is registered." — Confirmed true. The current `TOP_LEVEL_PROJECTORS` registry has exactly 24 keys (`bytes_avoided`, `bytes_in`, `bytes_out`, `compile_decision_dry_run`, `content_type`, `error_class`, `error_type`, `event`, `latency_ms`, `memory_block_assembly`, `memory_selection_summary`, `memory_source`, `pipeline_node_results`, `projection_dropped_field_count`, `projection_unsupported_artifact_count`, `relaymem_primary_recall_projection`, `relayrun_artifact`, `runtime_ctx_injection_result`, `runtime_snippet_injection_result`, `stable_prefix_block_ids`, `stable_prefix_hash`, `status_code`, `stream_timing`, `token_memory_dry_run`), independently recomputed from source and confirmed identical to the literal expected set already asserted by `scripts/relaylm_audit_projection_contract_smoke.py::assert_registry_hygiene()`. The fail-closed rule is already stated by the same architecture contract.
3. "Pipeline node diagnostics are similarly documented by the node projector registry; unknown nodes must not become durable by accident." — Confirmed true. The current `PIPELINE_NODE_PROJECTORS` registry has exactly 16 keys, machine-verified equal to [PipelineNodeResult Contract](../../contracts/pipeline_node_result_contract.md)'s documented current node-name authority by `scripts/relaylm_pipeline_node_result_contract_smoke.py`.
4. "The historical suffix/forbidden-token/cross-field-taint logic is no longer the primary persistence boundary." — Historical evidence only. That logic (`_is_forbidden_key`, `_SAFE_KEY_SUFFIXES`, and cross-field taint tracking, introduced by commit `bca93d8f945fcef43585f70621f67a6a1aaa34ca`) was fully removed the same day by commit `809ea32371281779488dc2f5aa4d33b334ad25fd`, which introduced the typed-projector system that is current code today; a later commit (`8efd6dc`) removed the remaining taint-context scaffolding entirely. The source phrase is a gloss over that removed code, not a literal quotation — the strings "forbidden_token", "forbidden_suffix", and "cross_field_taint" never existed verbatim in history. No trace of this logic remains in `relaylm/audit_projection.py` or `relaylm/trace.py` today.
5. "Any remaining validation is defense in depth for already-projected fields: scalar types, finite non-negative numbers, bounded opaque identifiers, exact media type grammar, and URL/path rejection." — Confirmed true at the categorical level this source describes. The current validator set (`_bool`, `_non_negative_int`, `_non_negative_number`, `_http_status`, `_bounded_token`, `_lower_token`, `_class_token`, `_opaque_id`, `_sha256`, `_content_type`, `_scoped_uuid_id`, `_enum`, `_list_of`, `_mapping`, `_looks_like_url_or_path`, all in `relaylm/audit_projection.py`) is already covered by the same architecture contract's "Fail-closed behavior" section.

No block required absorption into a current authority. One accuracy correction, independent of this file's retirement, was made to [Audit Trace Content-Free Contract](../../architecture/audit_trace_content_free_contract.md): its "P0-A1 compatibility boundary" section used present/future-tense "During P0-A1..." and "P0-A2 removes ... entirely" phrasing for a phase pair that has no separate tracked existence anywhere else in the repository (`docs/PROJECT_STATUS.md` records no P0-A1/P0-A2 entries) and for behavior that current code has already fully achieved. The section was reworded to present tense to state the current, already-complete, permanent compatibility-shim behavior, and the contract's validation command list was extended to name the two previously code-only, CI-unwired contract smokes (`scripts/relaylm_audit_projection_contract_smoke.py`, `scripts/relaylm_audit_projection_exact_contract_smoke.py`) that this cutover wires into CI.

## Exact source

The submitted source is retained byte-for-byte as [audit_trace_projection_boundary-source.txt](audit_trace_projection_boundary-source.txt).

```text
old path: docs/mvp/audit_trace_projection_boundary.md (no prior path; never renamed)
source PR: 264 (rinsakamo/p0-a1-content-free-trace-contract)
source commit: 28f3500c9208e6a686b27478b0ea4948f64aa15b (2026-06-14T07:31:27+00:00)
source origin/merge commit: 44da3d98ae43c05dfb64ab8e1a7c555aa9c25190 (2026-06-17T20:36:27+09:00)
source merge strategy: real_merge_source_commit_preserved_distinct_from_origin_merge_commit
source blob: bc042c8370d88d995df8a454c920f80503ae558d
source content SHA-256: 11278cb325dea1ba97b7fd006d0267d038a006df601f6b3edd24b204e0d0683c
disposition: evidence_retained_no_absorption_required_plus_unrelated_current_authority_accuracy_correction
```

No post-source content modification exists; the source blob equals the pre-cutover blob and today's blob.

## Current authority

The exact current audit-trace persistence boundary, content-free schema, typed metadata projection contract, and fail-closed defense-in-depth validation are owned by [Audit Trace Content-Free Contract](../../architecture/audit_trace_content_free_contract.md) and implemented in `relaylm/audit_projection.py` and `relaylm/trace.py`. The exact current `PipelineNodeResult` shape and pipeline-node projector name registry are owned by [PipelineNodeResult Contract](../../contracts/pipeline_node_result_contract.md). The PM-D6 RelayINT-native-artifact / RelayREF-supersession boundary underlying the `relayint_reference_repair` compatibility node name is owned by [PM-D6 RelayINT Native Artifact / RelayREF Wrapper Removal](../../architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md). Repository-wide current implementation status remains owned by [Project Status](../../PROJECT_STATUS.md).

This record is not authoritative for any of the above; it is retained solely as frozen historical evidence of the note that first announced this boundary.

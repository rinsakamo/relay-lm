---
relaylm_doc_type: evidence
relaylm_authority: mvp48_pipeline_node_result_scaffold_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current PipelineNodeResult field shape, status enum, and detachment semantics
  - current list of pipeline nodes that emit results
  - current RelayINT / RelayREF compatibility-key boundary
  - current RelayCTX Unpack phase status
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: 69cecf1841e54e95d18868559e03686c5e60484f
relaylm_source_origin_commit: 69cecf1841e54e95d18868559e03686c5e60484f
relaylm_source_pr: none
relaylm_recorded_on: 2026-06-12
relaylm_source_blob: 4fe7ee9ce200ab84055d0476fc06b0e13893d988
relaylm_source_content_sha256: 2233a265198a33bfb2dfd917b78ecb1861c5641b6e597a50403fc1bb67150f3d
relaylm_pre_cutover_blob: 4fe7ee9ce200ab84055d0476fc06b0e13893d988
relaylm_pre_cutover_content_sha256: 2233a265198a33bfb2dfd917b78ecb1861c5641b6e597a50403fc1bb67150f3d
relaylm_exact_source_snapshot: mvp48_pipeline_node_result_scaffold-source.txt
---
# MVP-48 Pipeline Node Result Scaffold Evidence

This frozen record preserves the Phase 4.5 `PipelineNodeResult` scaffold summary as historical implementation evidence. Unlike MVP-45/46/47, this file was never renamed and has no source pull request: it was added directly at its current path by a standalone documentation commit, `69cecf1841e54e95d18868559e03686c5e60484f` ("docs: summarize Phase 4.5 pipeline node result scaffold", 2026-06-12), sixteen minutes after the related code landed in PR #245 ("feat: record Phase 4.5 pipeline node diagnostics", merged as squash commit `559fa8afc7ffd72743a51d8832d627be059fdc8d`). PR #245's diff does not include this doc file, so it is not treated as the source PR here; source commit and origin/merge commit are recorded as the same direct-push commit. This was independently verified via the GitHub API (`list_commits` on the exact current path returns exactly this one commit, with no PR association found by title/commit search) against the advisory table in the Cutover 1C-33 task brief, and the advisory blob/SHA-256 values were confirmed correct.

Most of this source remains independently verified true against current code: the exact `PipelineNodeResult` dataclass fields, the frozen/immutable dataclass, `to_log_dict()` detachment, `build_pipeline_node_result(...)` builder behavior, request-local `PipelineContext.node_results`, ordered recording, best-effort semantics (wrapped in `try/except` one layer up in `relaylm/trace_runtime.py`), the `pipeline_node_results` trace-metadata key, and the non-authority over routing/fallback/retry/short-circuit/recovery/checkpoints and RelayRUN consumption — all confirmed unchanged in `relaylm/pipeline_node_result.py`, `relaylm/pipeline_context.py`, and `relaylm/trace_runtime.py`.

Two parts of this source are now **superseded and must not be treated as current**:

1. **The "historical RelayINT / RelayREF compatibility boundary" section** (`runtime compatibility key: relayref_artifact`; `historical source node: relayref`; `RelayINT-facing alias: relayint_reference_repair`) is superseded by PM-D6 (`docs/architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md`, `relaylm_status: current`, confirmed `complete` in `docs/PROJECT_STATUS.md`). RelayINT's live artifact key is now `relayint_intent_artifact` (schema `relayint.intent.v1`), produced natively by `build_relayint_reference_intent_artifact()` in `relaylm/relayint.py` with no RelayREF import or call. `relaylm/pipeline_node_adapter.py` now synthesizes a native `relayint_reference_intent` node alongside the legacy-shaped `relayint_reference_repair` node (kept only as a trace-shape compatibility identifier, not a real RelayREF data dependency).
2. **The three-node emitter list** (`relayint_reference_repair`, `relayint_quick_clarification`, `relayctx_repack`) is stale and incomplete. Current code has at least 16 distinct pipeline node names registered in `relaylm/audit_projection.py::PIPELINE_NODE_PROJECTORS`, including client-instruction-pipeline nodes, `relayint_reference_intent`, `relayctx_unpack`, and RelayMEM-SLP nodes that did not exist at source time. This doc's "Deferred work" entry for "minimal non-streaming RelayCTX Unpack: Phase 5" is also superseded: `relayctx_unpack` is implemented and already recording node results (`relaylm/adapter.py`), so the "Next phase" section's forward-looking Phase 5 framing no longer describes the current roadmap position.

## Exact source

The submitted source is retained byte-for-byte as [mvp48_pipeline_node_result_scaffold-source.txt](mvp48_pipeline_node_result_scaffold-source.txt).

```text
old path: docs/mvp/mvp48_pipeline_node_result_scaffold.md (no prior path; never renamed)
source PR: none (direct push; related code PR #245 did not add this doc)
source commit: 69cecf1841e54e95d18868559e03686c5e60484f (== origin/merge commit)
source blob: 4fe7ee9ce200ab84055d0476fc06b0e13893d988
source content SHA-256: 2233a265198a33bfb2dfd917b78ecb1861c5641b6e597a50403fc1bb67150f3d
disposition: evidence_retained_plus_narrow_absorption_plus_superseded_relayref_section
```

No post-source content modification exists; the source blob equals the pre-cutover blob and today's blob.

## Current authority

The exact current `PipelineNodeResult` field shape, `PipelineNodeStatus` enum, immutability/detachment semantics, request-local ordered collection, best-effort recording, content-free trace projection, current node-name authority, and non-authority over routing/persistence/RelayRUN are owned by [PipelineNodeResult Contract](../../contracts/pipeline_node_result_contract.md) and implemented in `relaylm/pipeline_node_result.py`, `relaylm/pipeline_context.py`, `relaylm/pipeline_node_adapter.py`, `relaylm/trace_runtime.py`, and `relaylm/audit_projection.py`. The PM-D6 RelayINT-native-artifact / RelayREF-supersession boundary is owned by [PM-D6 RelayINT Native Artifact / RelayREF Wrapper Removal](../../architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md). The general content-free trace/audit principle this scaffold implements is owned, at a repository-wide level, by [Audit Trace Content-Free Contract](../../architecture/audit_trace_content_free_contract.md) and [Pipeline Responsibilities](../../architecture/pipeline-responsibilities.md). Repository-wide current implementation status remains owned by [Project Status](../../PROJECT_STATUS.md).

This record is not authoritative for the current RelayINT quick-clarification chain (MVP-45/46/47 evidence and the RelayINT runtime contract own that), the current RelayCTX Unpack implementation, or any RelayRUN checkpoint/routing behavior (none exists yet).

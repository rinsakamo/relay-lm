---
relaylm_doc_type: evidence
relaylm_authority: mvp43_relayctx_short_term_runtime_injection_apply_gate_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current RelayCTX short-term extraction/assembly/preflight schema authority
  - the current full apply-gate blocked-reason taxonomy (13 distinct reasons in current code; this source names only 4 gate conditions in prose)
  - current stage ordering inside RelayCTX Repack
  - current config-flag list beyond the two flags named here
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: d76e8e623dddd8b437ee76597014c354bbce17d6
relaylm_source_origin_commit: 8eabaf1c46fbc46b1628e957fe949a40f8f80f9f
relaylm_source_pr: 237
relaylm_recorded_on: 2026-06-06
relaylm_source_blob: dfce2f4a7cde838749791e8ac91cc213a2a0eb55
relaylm_source_content_sha256: 7227d7438c8fa49b13fa0c3854676800636fd95169248c747752a27bfed30850
relaylm_pre_cutover_blob: 628e58946a34e277fa3a07bed7219dd2ce57b70f
relaylm_pre_cutover_content_sha256: acc1f209e667acd3e6526c8ce1464b2d4101371e75e73e1a571f2f470da00c39
relaylm_exact_source_snapshot: mvp43_relayctx_short_term_runtime_injection_apply_gate-source.txt
relaylm_exact_source_snapshot_matches: pre_cutover_blob_not_source_commit_blob
---
# MVP-43 RelayCTX Short-Term Runtime Injection Apply Gate Evidence

This frozen record preserves the RelayCTX short-term runtime injection apply-gate summary as historical implementation evidence. **The source commit and the pre-cutover blob are different versions and must not be treated as the same version.** PR #237 (origin/merge commit `8eabaf1c46fbc46b1628e957fe949a40f8f80f9f`, merged 2026-06-06) introduced the doc's original wording at the old path `docs/mvp43_summary.md`. Five days later, commit `e39f846fa8e015b4f2810f96b4b59283153a2aa2` (2026-06-11) added the file at the current path with one reworded clause — "delete/compress/reconstruct OpenWebUI messages" became "alter OpenWebUI message history" — and commit `90025c9645c06ee5aa87955cab9a899064b8b2af` (2026-06-11, two minutes later) removed the old path. The frozen snapshot below retains the **pre-cutover** wording (post-`e39f846`), per this cutover's requirement to freeze the exact bytes being deleted from `docs/mvp/`, not the PR #237 introduction wording. The rewording is a non-substantive broadening of the same non-goal claim; either wording remains accurate against current code.

The task brief's warning about this record proved accurate: the gate-condition list in this source names only 4 conditions in prose, while current code (`relaylm/relayctx_repack.py`, `relaylm/diagnostics.py`) enforces at least 13 distinct blocked-reason strings across the preflight and apply tiers. This source's problem is incompleteness, not incorrectness — every claim it does make is still true today — but its 4-condition list must not be copied into current authority unchanged. The full, current, code-derived gate/blocked-reason taxonomy lives in [RelayCTX Short-Term Runtime Contract](../../contracts/relayctx_short_term_runtime_contract.md).

## Exact source

The submitted source is retained byte-for-byte as [mvp43_relayctx_short_term_runtime_injection_apply_gate-source.txt](mvp43_relayctx_short_term_runtime_injection_apply_gate-source.txt), matching the **pre-cutover** blob, not the PR #237 introduction blob.

```text
old path: docs/mvp/mvp43_relayctx_short_term_runtime_injection_apply_gate.md
source PR: #237, origin/merge commit 8eabaf1c46fbc46b1628e957fe949a40f8f80f9f (original wording)
source commit: d76e8e623dddd8b437ee76597014c354bbce17d6
source blob (PR #237 introduction): dfce2f4a7cde838749791e8ac91cc213a2a0eb55
source content SHA-256 (PR #237 introduction): 7227d7438c8fa49b13fa0c3854676800636fd95169248c747752a27bfed30850
post-source modification commit: e39f846fa8e015b4f2810f96b4b59283153a2aa2 (2026-06-11; reworded one clause and moved to the current path)
post-source modification commit: 90025c9645c06ee5aa87955cab9a899064b8b2af (2026-06-11; removed the old path)
pre-cutover blob (retained below): 628e58946a34e277fa3a07bed7219dd2ce57b70f
pre-cutover content SHA-256 (retained below): acc1f209e667acd3e6526c8ce1464b2d4101371e75e73e1a571f2f470da00c39
disposition: evidence_retained_plus_absorption
```

## Current authority

The four-stage RelayCTX short-term diagnostics/injection chain's current schemas, config owners, full gate/blocked-reason taxonomy, insertion mechanics, apply-result schema, and stage ordering belong to [RelayCTX Short-Term Runtime Contract](../../contracts/relayctx_short_term_runtime_contract.md) and are implemented in `relaylm/relayctx_repack.py`, `relaylm/diagnostics.py`, and `relaylm/managed_chat_runtime.py`. The current CTX-Repack stage-ordering rule (this gate must run before token-budget truncation) is owned by [Pipeline Responsibility Design](../../architecture/pipeline_responsibility_design.md#9-relayctx-repack); [Project Status](../../PROJECT_STATUS.md) records that this ordering was once wrong and has since been fixed, a historical fact this frozen source has no way to reflect.

This record is not authoritative for the current stage ordering inside RelayCTX Repack, the current full config-flag list, or any behavior of the MVP-40/41/42 stages.

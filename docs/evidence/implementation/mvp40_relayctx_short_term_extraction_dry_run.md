---
relaylm_doc_type: evidence
relaylm_authority: mvp40_relayctx_short_term_extraction_dry_run_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current RelayCTX short-term extraction/assembly/preflight/apply schema and gate authority
  - current stage ordering inside RelayCTX Repack
  - current config-flag list beyond the single flag named here
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: d794ad3859b5c48447f5073bc21913a33aaa6dac
relaylm_source_origin_commit: a3335b6681ef8b14f108469942882f1cbb50f734
relaylm_source_pr: 234
relaylm_recorded_on: 2026-06-06
relaylm_source_blob: 1ffcaa98d5c527c8f12f0ec8d56a4224c12c9564
relaylm_source_content_sha256: 19084122d521604d0092ead59f79ac4b1a95a174e0e4efe18e8132545a8de804
relaylm_pre_cutover_blob: 1ffcaa98d5c527c8f12f0ec8d56a4224c12c9564
relaylm_pre_cutover_content_sha256: 19084122d521604d0092ead59f79ac4b1a95a174e0e4efe18e8132545a8de804
relaylm_exact_source_snapshot: mvp40_relayctx_short_term_extraction_dry_run-source.txt
---
# MVP-40 RelayCTX Short-Term Extraction Dry-Run Evidence

This frozen record preserves the first RelayCTX short-term extraction dry-run summary as historical implementation evidence. The content has been byte-identical since PR #234 merged on 2026-06-06 through the pre-cutover boundary (`37140d4beda98562659686faa1b3464296e2d3fa`, 2026-07-14) — the only intervening event was a pure path rename (`docs/mvp40_summary.md` -> `docs/mvp/mvp40_relayctx_short_term_extraction_dry_run.md`, commits `ab0e7d8011617fb52fc1366704fa6e9238b5b5c4` / `807cb8dea629942569cae06d3d3ad602660a80e4`, 2026-06-11) with no content change.

Every claim in this source remains independently verified true against current code at the pre-cutover boundary: default-off (`relaylm/config.py`), artifact/schema-version name, text-only/non-text-suppressed content handling, aggregate-count-only field shape, all five hardcoded safety gates, and deterministic heuristic-only (non-LLM) classification. The producer function (`build_relayctx_short_term_extraction_dry_run`) still lives in `relaylm/diagnostics.py`; only its call site has moved, from `relaylm/app.py` at source time to `relaylm/managed_chat_runtime.py::handle_managed_chat_completion` today.

## Exact source

The submitted source is retained byte-for-byte as [mvp40_relayctx_short_term_extraction_dry_run-source.txt](mvp40_relayctx_short_term_extraction_dry_run-source.txt).

```text
old path: docs/mvp/mvp40_relayctx_short_term_extraction_dry_run.md
source PR: #234, origin/merge commit a3335b6681ef8b14f108469942882f1cbb50f734
source commit: d794ad3859b5c48447f5073bc21913a33aaa6dac
source blob: 1ffcaa98d5c527c8f12f0ec8d56a4224c12c9564
source content SHA-256: 19084122d521604d0092ead59f79ac4b1a95a174e0e4efe18e8132545a8de804
disposition: evidence_retained_plus_narrow_absorption
```

No post-source content modification exists; the source blob equals the pre-cutover blob. The only intervening commits (`ab0e7d8011617fb52fc1366704fa6e9238b5b5c4`, `807cb8dea629942569cae06d3d3ad602660a80e4`) moved the file under `docs/mvp/` without changing its content.

## Current authority

The four-stage RelayCTX short-term diagnostics/injection chain's current schemas, config owners, gate prerequisites, blocked-reason taxonomy, and stage ordering belong to [RelayCTX Short-Term Runtime Contract](../../contracts/relayctx_short_term_runtime_contract.md) and are implemented in `relaylm/diagnostics.py`, `relaylm/relayctx_repack.py`, `relaylm/managed_chat_runtime.py`, and `relaylm/config.py`. The general content-free-surfaces principle this extraction stage embodies is also stated, at a repository-wide level, in [Context Packing Design](../../architecture/context_packing_design.md). Repository-wide current implementation status remains owned by [Project Status](../../PROJECT_STATUS.md).

This record is not authoritative for the current stage ordering inside RelayCTX Repack, the current full config-flag list, or any behavior of the downstream MVP-41/42/43 stages.

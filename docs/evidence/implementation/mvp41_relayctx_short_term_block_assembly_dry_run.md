---
relaylm_doc_type: evidence
relaylm_authority: mvp41_relayctx_short_term_block_assembly_dry_run_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current RelayCTX short-term extraction/preflight/apply schema and gate authority
  - current stage ordering inside RelayCTX Repack
  - current config-flag list beyond the single flag named here
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: 2debea2f3fd50af6015807efa8e490898d9b558f
relaylm_source_origin_commit: 40f98c532a535962068fdd28cc9d01fd065d5ff6
relaylm_source_pr: 235
relaylm_recorded_on: 2026-06-06
relaylm_source_blob: 8d83bc2bfd424dda09a7b85ec381b597343e0c4d
relaylm_source_content_sha256: 7c1ece92f8e5e39b569fb6b3147e6f1600e3ef294adf395cefc2d67947ebc03d
relaylm_pre_cutover_blob: 8d83bc2bfd424dda09a7b85ec381b597343e0c4d
relaylm_pre_cutover_content_sha256: 7c1ece92f8e5e39b569fb6b3147e6f1600e3ef294adf395cefc2d67947ebc03d
relaylm_exact_source_snapshot: mvp41_relayctx_short_term_block_assembly_dry_run-source.txt
---
# MVP-41 RelayCTX Short-Term Block Assembly Dry-Run Evidence

This frozen record preserves the first RelayCTX short-term block assembly dry-run summary as historical implementation evidence. The content has been byte-identical since PR #235 merged on 2026-06-06 through the pre-cutover boundary (`37140d4beda98562659686faa1b3464296e2d3fa`, 2026-07-14) — the only intervening event was a pure path rename (`docs/mvp41_summary.md` -> `docs/mvp/mvp41_relayctx_short_term_block_assembly_dry_run.md`, commits `92dd008d82a8cd89eb9dcb40153c1b01c51a1e6e` / `e2687212479d0ba3ad9fd470976cafae10ab331b`, 2026-06-11) with no content change.

Every claim in this source remains independently verified true against current code at the pre-cutover boundary: default-off, schema version `relayctx_short_term_block_assembly_dry_run.v0`, direct consumption of the MVP-40 extraction artifact, the `relayctx_short_term` / `openwebui_messages` / `current_thread_over_memory_seed` block-concept/source/priority fields, the 4-item priority order (still read back unmodified by the MVP-42 preflight builder, not superseded), and all six hardcoded safety gates. One nuance this source does not state: the artifact's token-budget hint is currently a hardcoded `400` constant at the assembly stage, not config-driven (unlike the sibling injection-stage budget, which is a real `RelayLMConfig` field).

## Exact source

The submitted source is retained byte-for-byte as [mvp41_relayctx_short_term_block_assembly_dry_run-source.txt](mvp41_relayctx_short_term_block_assembly_dry_run-source.txt).

```text
old path: docs/mvp/mvp41_relayctx_short_term_block_assembly_dry_run.md
source PR: #235, origin/merge commit 40f98c532a535962068fdd28cc9d01fd065d5ff6
source commit: 2debea2f3fd50af6015807efa8e490898d9b558f
source blob: 8d83bc2bfd424dda09a7b85ec381b597343e0c4d
source content SHA-256: 7c1ece92f8e5e39b569fb6b3147e6f1600e3ef294adf395cefc2d67947ebc03d
disposition: evidence_retained_plus_absorption
```

No post-source content modification exists; the source blob equals the pre-cutover blob. The only intervening commits (`92dd008d82a8cd89eb9dcb40153c1b01c51a1e6e`, `e2687212479d0ba3ad9fd470976cafae10ab331b`) moved the file under `docs/mvp/` without changing its content.

## Current authority

The four-stage RelayCTX short-term diagnostics/injection chain's current schemas, config owners, gate prerequisites, blocked-reason taxonomy, and stage ordering belong to [RelayCTX Short-Term Runtime Contract](../../contracts/relayctx_short_term_runtime_contract.md) and are implemented in `relaylm/diagnostics.py`. Repository-wide current implementation status remains owned by [Project Status](../../PROJECT_STATUS.md).

This record is not authoritative for the current stage ordering inside RelayCTX Repack, the current full config-flag list, or any behavior of the MVP-40/42/43 stages.

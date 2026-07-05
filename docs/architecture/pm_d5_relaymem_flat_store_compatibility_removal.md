---
relaylm_doc_type: implementation_handoff
relaylm_authority: pm_d5_relaymem_flat_store_compatibility_removal_boundary
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - RelayMEM store layout discovery changes
  - Primary or Secondary MEM runtime readable layout changes
  - E1-R5 or PM-D8 Primary recall adapter/root handling changes
relaylm_not_authoritative_for:
  - repository-wide current status
  - roadmap sequencing
  - automatic migration or repair behavior
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - project_execution_plan.md
  - current_target_migration_guide.md
  - relaymem_slp_current_target.md
  - e1r5_primary_mem_recall_candidate_bridge.md
---
# PM-D5 RelayMEM flat-store compatibility removal

## Purpose

PM-D5 removes RelayMEM flat-store compatibility from ordinary runtime discovery and public diagnostics. RelayMEM page discovery now treats the character-scoped target layout as the only readable runtime MEM layout.

## Implemented boundary in this slice

- RelayMEM store diagnostics expose `flat_store_compatibility_removed: true`.
- Runtime page candidate discovery scans only target Primary/Secondary directories.
- Bounded snippet extraction accepts only target Primary/Secondary page paths.
- Legacy flat-only stores fail closed with `target_primary_secondary_layout_missing` or `unsupported_scope` rather than being selected.
- Source evidence directories under `memory/sources/**` remain supported.
- Target control files `memory/mem/index.md` and `memory/mem/log.md` remain supported.

## Removed compatibility behavior

The runtime store implementation no longer scans or reports flat candidate pages from:

- `memory/mem/projects`
- `memory/mem/concepts`
- `memory/mem/summaries`
- `memory/mem/relations`

The PM-D5 diagnostics shape also removes the former flat compatibility fields:

- `current_flat_present`
- `migration_required`
- `read_only_compatibility_mode`

## Character-scoped target-only root behavior

The safe target remains:

```text
<configured_root>/characters/<opaque_character_partition>/memory/sources/**
<configured_root>/characters/<opaque_character_partition>/memory/mem/primary/**
<configured_root>/characters/<opaque_character_partition>/memory/mem/secondary/**
<configured_root>/characters/<opaque_character_partition>/memory/mem/index.md
<configured_root>/characters/<opaque_character_partition>/memory/mem/log.md
```

Missing or incomplete target Primary/Secondary layout must fail closed and must not create symlinks, repair directories, or copy legacy flat files.

## E1-R5 / PM-D8 interaction

This slice preserves the E1-R5 bounded scoped Primary recall bridge as the intended Primary recall path. PM-D8 remains open unless a later PR explicitly folds the E1-R5 bridge into the canonical adapter with equivalent security and no-symlink smoke coverage.

## Public diagnostics and leakage boundary

Public diagnostics are content-free. They must not expose raw physical paths, character ids, namespace values, page bodies, queue payloads, protected source bodies, digests, lineage identifiers, or idempotency keys.

## Non-goals

This document does not implement PM-D6, PM-D7, PM-D8, automatic migration, copy/repair, symlink creation, runtime memory mutation, post-hoc visible response rewriting, TTS/audio/avatar execution, or browser-owned trust.

## Validation

A dedicated local smoke was added:

```bash
PYTHONPATH=. python scripts/relaylm_pm_d5_flat_store_compat_removal_smoke.py
```

The full PM-D5 validation set should also include the current RelayMEM, I1, E1, E1-R5, docs-link, and documentation-boundary smokes before merge.

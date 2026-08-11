---
relaylm_doc_type: evidence
relaylm_authority: reviewed_scripts_inventory_snapshot
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: validation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - live repository counts after the recorded source commit
  - runtime implementation status
  - whether an unreferenced script is safe to delete
  - repeatable inventory generation methodology
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../operations/consolidated-smoke-workflow-maintenance.md
relaylm_source_commit: 167bc884223b5c6c4b1bb0e9c0086efcac80e814
relaylm_source_pr: 544
relaylm_source_path: docs/smoke/scripts_inventory.md
relaylm_recorded_on: 2026-07-11
relaylm_source_blob: da042c2dfe2699af679b5cb15572b0a6a11e5704
relaylm_source_content_sha256: a653ea0f2506ce4c756a366174c0bdcf5710964a5921fe655d2c35b084bc1334
---
# Scripts Inventory

This frozen evidence record preserves the maintainer-facing summary of a reviewed mechanically generated script inventory from PR #544. The row-level inventory is generated in CI and uploaded as the `scripts-inventory` artifact by `.github/workflows/scripts-inventory.yml`; it is intentionally not kept as a large hand-maintained table in Git.

## Recorded snapshot

Source evidence:

```text
review source: PR #544 scripts-inventory validation artifact
merged main commit: 167bc884223b5c6c4b1bb0e9c0086efcac80e814
inventory interpretation: historical snapshot, not a live counter
```

The reviewed artifact reported:

- 459 Python scripts under `scripts/`;
- 227 referenced by a current CI workflow or by the consolidated smoke command registry;
- 284 referenced by documentation other than this inventory file;
- 99 referenced by neither CI nor documentation and therefore candidates for maintainer triage.

The inventory file itself is excluded from documentation-reference detection. This prevents its own generated rows from marking every listed script as documented.

An unreferenced result is a triage signal only. It does not prove that a script is dead, obsolete, or safe to delete; callers outside CI/docs and intentional manual tools must be reviewed separately.

## Regeneration

Run from the repository root and write the row-level artifact outside this summary:

```bash
python scripts/relaylm_generate_scripts_inventory.py \
  --output generated/scripts_inventory.md
```

For pull requests, use the uploaded `scripts-inventory` artifact as review evidence. The generated document records the exact checked-out commit SHA and contains one row per Python script with:

- CI-reference status;
- documentation-reference status;
- a neutral filename signal: `helper-shaped`, `smoke-named`, or `other`;
- the reviewed responsibility, lifecycle, and owner copied together from an exact script path in `records/repository/asset_classification_v1.yaml`, or `unclassified` for all three fields when the script is not listed there.

Reference status and filename shape are mechanical review inputs only. The reviewed-classification columns mirror one complete current Lane R registry claim; they do not create authority or authorize lifecycle, retention, deletion, consolidation, or rename decisions. Conflicting responsibility, lifecycle, or owner claims fail generation rather than selecting one.

Do not rewrite this frozen evidence record with later counts and do not overwrite it with the generator. Future current reviews use the generated CI artifact. If a later reviewed snapshot is intentionally retained, preserve it as a separate evidence record with its own provenance instead of updating this record.

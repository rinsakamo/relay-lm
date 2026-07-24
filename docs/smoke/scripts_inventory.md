---
relaylm_doc_type: evaluation_record
relaylm_authority: reviewed_scripts_inventory_snapshot
relaylm_status: historical
relaylm_volatility: high
relaylm_owner: validation
relaylm_update_trigger:
  - a new generated inventory artifact is reviewed
  - script, workflow, registry, or documentation reference counts change
relaylm_not_authoritative_for:
  - live repository counts after the recorded source commit
  - runtime implementation status
  - whether an unreferenced script is safe to delete
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# Scripts Inventory

This is the maintainer-facing summary for a reviewed mechanically generated script inventory. The row-level inventory is generated in CI and uploaded as the `scripts-inventory` artifact by `.github/workflows/scripts-inventory.yml`; it is intentionally not kept as a large hand-maintained table in Git.

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
- the reviewed responsibility copied from an exact script path in `records/repository/asset_classification_v1.yaml`, or `unclassified` when the script is not listed there.

Reference status and filename shape are mechanical review inputs only. The reviewed-responsibility column mirrors the current Lane R classification registry; it does not create a responsibility or authorize lifecycle, retention, deletion, consolidation, or rename decisions. Conflicting reviewed responsibility claims fail generation rather than selecting one.

After reviewing a new artifact, update this summary only with its source commit/run and aggregate counts. Do not copy the generated row table into this file and do not overwrite this file with the generator.

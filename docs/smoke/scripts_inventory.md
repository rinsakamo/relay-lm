# Scripts Inventory

This is the maintainer-facing summary for the mechanically generated script inventory. The row-level inventory is generated in CI and uploaded as the `scripts-inventory` artifact by `.github/workflows/scripts-inventory.yml`; it is intentionally not kept as a large hand-maintained table in Git.

## Current audited snapshot

The corrected PR-14 inventory artifact reports:

- 459 Python scripts under `scripts/`
- 227 referenced by a current CI workflow or by the consolidated smoke command registry
- 284 referenced by documentation other than this inventory file
- 99 referenced by neither CI nor documentation and therefore candidates for maintainer triage

The inventory file itself is excluded from documentation-reference detection. This prevents its own table from marking every listed script as documented.

## Regeneration

Run from the repository root:

```bash
python scripts/relaylm_generate_scripts_inventory.py \
  --output generated/scripts_inventory.md
```

For pull requests, use the uploaded `scripts-inventory` artifact as the review authority. The generated document records the exact checked-out commit SHA and contains one row per Python script with:

- CI-reference status
- documentation-reference status
- a mechanical category guess: active smoke, phase-completion evidence, helper, or tool

Regenerate after rebasing PR-14 or after changing `scripts/`, `.github/workflows/`, the consolidated smoke command registry, or documentation. Do not manually copy individual rows back into this summary.

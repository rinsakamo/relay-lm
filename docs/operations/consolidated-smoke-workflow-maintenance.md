---
relaylm_doc_type: operations
relaylm_authority: consolidated_smoke_workflow_maintenance
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: validation
relaylm_update_trigger:
  - consolidated workflow files change
  - smoke group registry changes
  - changed-path classification changes
  - script inventory generation changes
relaylm_not_authoritative_for:
  - runtime implementation status
  - individual smoke behavior contracts
  - historical PR stacking instructions
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# Consolidated smoke workflow maintenance

The consolidated smoke fleet is split into three workflow surfaces:

- `.github/workflows/smoke-relaymem.yml`
- `.github/workflows/smoke-runtime.yml`
- `.github/workflows/smoke-ui.yml`

Changed paths are classified by `scripts/relaylm_ci_consolidated_smoke.py`. Runtime and UI workflows convert the selected groups into bounded matrices with `scripts/relaylm_ci_changed_matrix.py`. Manual dispatch intentionally selects all groups.

## Validation

Run the static contract locally after changing group patterns, command lists, or workflow job structure:

```bash
python -m pip install pyyaml
PYTHONPATH=scripts python scripts/relaylm_ci_consolidated_smoke_contract.py
```

The contract verifies that registered command paths exist, every executable group has a command list, representative path changes select only the expected groups, consolidated workflow job sets remain stable, and every execution job has an explicit timeout.

## Script inventory

Generate the row-level maintainer inventory outside the hand-maintained summary file:

```bash
python scripts/relaylm_generate_scripts_inventory.py \
  --output generated/scripts_inventory.md
```

The generator records the exact checked-out commit SHA and treats commands registered in the consolidated runner as CI references. The `Scripts inventory artifact` workflow uploads a freshly generated copy for pull-request review.

Do not generate directly into `docs/smoke/scripts_inventory.md`; that file is a concise reviewed snapshot and pointer, not the generated row-level table.

Regenerate after:

- rebasing a workflow-consolidation change;
- adding, removing, or renaming files under `scripts/`;
- changing `.github/workflows/`;
- changing the consolidated smoke command registry;
- changing documentation references used by the inventory classifier.

## Branch and PR maintenance

The original PR-13/PR-14 stack has merged. Future changes do not inherit those historical restacking instructions.

For a new stacked workflow change:

1. state the exact base branch in the PR body;
2. keep each child branch based on the final parent head;
3. after parent review fixes, rebase or merge the updated parent into the child;
4. regenerate the inventory from the child head;
5. rerun the static contract and affected smoke matrices;
6. remove branch-specific instructions from this current runbook after the stack merges.

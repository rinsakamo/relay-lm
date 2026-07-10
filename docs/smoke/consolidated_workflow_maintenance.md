# Consolidated smoke workflow maintenance

The consolidated smoke fleet is split into three workflow surfaces:

- `.github/workflows/smoke-relaymem.yml`
- `.github/workflows/smoke-runtime.yml`
- `.github/workflows/smoke-ui.yml`

Changed paths are classified by `scripts/relaylm_ci_consolidated_smoke.py`.
Runtime and UI workflows convert the selected groups into bounded matrices with
`scripts/relaylm_ci_changed_matrix.py`. Manual dispatch intentionally selects
all groups.

## Validation

Run the static contract locally after changing group patterns, command lists, or
workflow job structure:

```bash
python -m pip install pyyaml
PYTHONPATH=scripts python scripts/relaylm_ci_consolidated_smoke_contract.py
```

The contract verifies that registered command paths exist, every executable
group has a command list, representative path changes select only the expected
groups, consolidated workflow job sets remain stable, and every execution job
has an explicit timeout.

## Script inventory

Regenerate the maintainer inventory after a rebase or after changing scripts,
workflows, or documentation:

```bash
python scripts/relaylm_generate_scripts_inventory.py \
  --output docs/smoke/scripts_inventory.md
```

The generator records the exact commit SHA and treats commands registered in
the consolidated runner as CI references. The `Scripts inventory artifact`
workflow also uploads a freshly generated copy for pull-request review.

## Stack maintenance

PR-14 must be restacked onto the final PR-13 head before merge. If PR-13 is
rebased or receives review fixes, rebase PR-14 or merge the updated PR-13 head
into PR-14, then regenerate the inventory and rerun the contract workflow.

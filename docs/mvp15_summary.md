# MVP-15 Summary

## Completed scope

- RelaySOUL artifact persistence dry-run contract
- supported artifact kinds:
  - `patch_dry_run`
  - `rollback_summary`
  - `approval_summary`
- artifact id / parent artifact id extraction
- lineage warnings:
  - missing/empty rollback `parent_revision_id`
  - missing/empty approval `patch_candidate_id`
- blocked/warning source artifacts remain persistable for audit when persistence-contract blockers are absent
- RelaySOUL patch compile dry-run contract
- target file -> compile block id mapping
- stable-prefix target / dynamic target classification
- empty observed `context_block_summary.block_ids=[]` treated as missing targets
- persona source budget warning propagation
- stable prefix hash presence signal

## Design intent

MVP-15 adds a contract layer that validates RelaySOUL artifacts and compile observability before any apply/persistence implementation.

- Validate RelaySOUL artifacts in a content-free way before actual persistence.
- Connect patch candidates to RelayLM compile diagnostics so target observability can be checked before patch apply.
- Keep blocked/warning source artifacts persistable for audit when persistence-contract blockers are absent.
- Keep persistence and compile dry-run contracts separate from runtime mutation/apply behavior.

## Runtime safety

- contract-only / dry-run-only
- no actual persistence
- no file write
- no DB write
- no patch generation
- no patch apply
- no revision apply
- no rollback execution
- no persona source mutation
- no runtime compile path connection
- no model call
- no runtime behavior change
- no backend forwarding payload change
- no persona/memory/patch body content in artifacts

## Main validation

- `python -m compileall relaylm`
- `python scripts/relaylm_relaysoul_persistence_smoke.py`
- `python scripts/relaylm_relaysoul_compile_dry_run_smoke.py`
- `python scripts/relaylm_relaysoul_patch_candidate_smoke.py`
- `python scripts/relaylm_relaysoul_revision_smoke.py`
- `python scripts/relaylm_relaysoul_approval_smoke.py`
- `python scripts/relaylm_context_block_summary_smoke.py`
- `python scripts/relaylm_persona_source_budget_smoke.py`

## Next phase

- optional docs for RelaySOUL artifact fields
- patch candidate compile dry-run artifact persistence linkage
- approval/revision artifact persistence storage design
- future patch apply / rollback execution remains separate MVP

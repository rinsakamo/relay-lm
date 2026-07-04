---
relaylm_doc_type: implementation_handoff
relaylm_authority: pm_d7_runtime_install_hook_fold_in
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: operations
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - project_execution_plan.md
  - current_target_migration_guide.md
  - relaymem_slp_current_target.md
  - e1r2_character_store_bootstrap.md
  - o1f_operational_validation.md
---
# PM-D7 Runtime Install Hook Fold-in

Last reviewed: 2026-07-04 JST

## Purpose

PM-D7 folds local runtime install and setup debt into a first-class explicit RelayLM command:

```bash
relaylm-runtime-install --config config.yaml --dry-run
relaylm-runtime-install --config config.yaml --write
relaylm-runtime-install --config config.yaml --write --character-id default
```

The default behavior is dry-run. Filesystem writes happen only when the operator passes `--write`.

## Command boundary

`relaylm-runtime-install` loads `config.yaml`, validates configured local runtime paths, and emits a bounded content-free report with schema `relaylm.runtime_install_projection.v0`.

The command may preflight configured RelayMEM memory root, optional character-scoped Primary MEM bootstrap readiness, queue/protected-source/durable-finalization/checkpoint/cache/trace directories, and generated `.relaylm/build` layout.

The public report does not include raw paths, secrets, API keys, source Markdown, memory text, queue payloads, trace bodies, protected source bodies, digests, or raw config bodies.

## Allowed writes

When and only when `--write` is supplied, PM-D7 may create missing safe empty directories from an allowlist derived from configuration and `.relaylm/build`.

When `--write --character-id <id>` is supplied, PM-D7 may invoke the existing E1-R2 character-store bootstrap authority to prepare the character-scoped Primary MEM directory layout and empty control files.

Repeated `--write` is idempotent and must not overwrite existing files.

## Forbidden writes and side effects

PM-D7 does not run during `pip install`, module import, or app startup. It does not create queue jobs, worker claims, scheduler rounds, trace bodies, semantic MEM/SOUL/source content, credentials, services, systemd units, Windows Task Scheduler tasks, downloads, or legacy flat RelayMEM compatibility layout.

## Path and character safety

Runtime install fails closed for missing config, invalid config, symlink roots, path traversal, unsafe roots, existing files where directories are expected, and malformed character-store bootstrap preconditions.

When `--character-id` is supplied, PM-D7 validates character-store preconditions before reporting a fresh dry-run as actionable. Invalid or unconfigured character ids must fail closed in dry-run before any later write attempt.

## Relation to E1-R2

E1-R2 remains the dedicated character-store bootstrap authority. PM-D7 does not remove `relaylm-character-store-bootstrap`; it explicitly delegates to the same authority when the operator supplies `--character-id`.

## Relation to O1 / O2 / O3

PM-D7 is an explicit one-shot operator preflight/apply command. It does not implement O2 supervised worker service or O3 always-on local operation.

## Validation

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_pm_d7_runtime_install_hook_fold_in_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r2_character_store_bootstrap_smoke.py
PYTHONPATH=. python scripts/relaylm_openwebui_lmstudio_config_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
```

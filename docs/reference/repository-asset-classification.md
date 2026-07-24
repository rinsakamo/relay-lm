---
relaylm_doc_type: reference
relaylm_authority: repository_asset_responsibility_and_lifecycle_classification
relaylm_status: current
relaylm_volatility: high
relaylm_owner: repository_maintenance
relaylm_update_trigger:
  - a listed asset gains or loses a supported caller or protected responsibility
  - a transitional removal gate closes or changes
  - the responsibility or lifecycle vocabulary changes
  - a bounded R2, R3, or R4 wave changes a listed path or canonical invocation
  - a generated classification registry or drift check becomes authoritative
relaylm_not_authoritative_for:
  - current runtime implementation status
  - runtime, storage, schema, API, or UI behavior
  - deletion, movement, rename, consolidation, or compatibility removal
  - user-data migration or irreversible state change
  - classification of assets not explicitly listed here
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/project_execution_plan.md
  - ../adr/0006-repository-structure-and-maintenance-sequencing.md
  - ../planning/repository-structure-migration.md
  - ../planning/workstream-orchestration.md
  - ../evidence/implementation/repository_inventory_baseline_1ca928cd.md
---
# Repository Asset Responsibility and Lifecycle Classification

Last reviewed: 2026-07-24 JST

## Purpose and authority boundary

This page defines the canonical Lane R responsibility and lifecycle classification format and records the bounded R1 surface plus accepted R2, R3, and R4 decisions.

```text
repository: rinsakamo/relay-lm
source main: 17ce820b91299e72dc532e7ed67046a377c0fd7e
source main meaning: exact R4-E2 reviewed base after the disjoint governance failure-budget dispatch-input correction
lane: R
stage: R4 low-risk independent package moves
scope: reviewed classification, canonical repository-inventory ownership, generated classification evidence, and the bounded runtime-install, worker, character-store bootstrap, shared character-creation, and installed RelayLM launcher package moves
```

Classification is evidence for later review. It does not authorize deletion, movement, rename, consolidation, behavior change, compatibility removal, storage migration, or status changes. Every destructive or authority-affecting action requires its own atomic PR and fresh caller evidence.

Assets not explicitly listed in the bounded registry below remain `unclassified` for Lane R purposes even when the mechanical inventory reports an invocation root or low reachability.

## Canonical classification format

A classification record uses these fields:

| Field | Requirement | Meaning |
|---|---|---|
| `asset_id` | required | Stable identifier independent of row order. |
| `paths` | required | Exact repository paths. Unexpanded globs are not classification evidence. |
| `entrypoint` | optional | Exact command-to-symbol mapping when the record is an installed entry point. |
| `responsibility` | required | One accepted responsibility class. |
| `lifecycle` | required | `active`, `transitional`, or `retired`. |
| `owner` | required | Maintainer or subsystem that owns the continuing responsibility. |
| `protected_boundary` | required for `active` and `transitional` | Runtime, operator, process, migration, recovery, or governance boundary protected by the asset. |
| `current_callers` | required for `active` and `transitional` | Current direct, indirect, dynamic, subprocess, workflow, operator, test, or documentation callers. |
| `invocation_roots` | required | Mechanical root kinds supporting the decision. An empty list for an active or transitional internal asset requires `invocation_root_reason`. |
| `invocation_root_reason` | required for an active or transitional asset with no roots | Why the asset is internal rather than independently invoked. |
| `evidence` | required | Exact current repository anchors used for the decision. |
| `removal_gate` | required for `transitional` | Explicit event that must close before retirement review. Active and retired records use `null`. |
| `replacement_validation` | required for `transitional` | Validation that must replace the protected responsibility before retirement. Active and retired records use `null`. |
| `confidence` | required | `confirmed`, `provisional`, or `unclassified`. |
| `notes` | optional | Scope limits, naming debt, or candidate-wave observations. |

Accepted responsibility values are:

```text
ordinary_test
process_smoke
operator_cli
offline_tooling
generator
migration_or_maintenance
benchmark
repository_validation
planned_inactive
unclassified
```

Accepted lifecycle values are:

```text
active
  current supported runtime, operator, contract, regression, process,
  recovery, or repository-governance responsibility

transitional
  characterization, compatibility, rollback, or migration responsibility
  required until an explicit removal gate closes

retired
  no remaining supported caller, protected boundary, migration role,
  rollback role, characterization role, or repository-governance responsibility
```

An unreferenced asset, low fan-in, absence from the FastAPI import graph, or milestone-oriented name is only a triage signal. None is sufficient retirement evidence.

## Invocation-root inventory

The current non-destructive inventory tool recognizes:

```text
console_script
dynamic_import
fastapi_route
frontend_route
github_actions_step
npm_script
operator_cli
pytest_root
python_dash_m
registry
smoke_only_root
static_or_package_data
subprocess_child
```

These are discovery categories, not responsibility decisions. Lane R review must inspect FastAPI/request paths, installed commands, supported `python -m` entry points, workflows, subprocesses, dynamic registries, tests, process smoke, migrations, recovery and rollback tools, generators, benchmarks, repository validators, and current runbooks where applicable.

The fixed `1ca928cd` baseline counted 731 roots. It is historical mechanical evidence, not a current complete classification. Current caller inspection at the source revision above controls each listed decision.

## Bounded classification registry

The following YAML records are the canonical human-reviewed representation for this Lane R slice. `records/repository/asset_classification_v1.yaml` is a machine-readable mirror. Drift validation is fail-closed, but neither the mirror nor generated navigation can authorize retirement.

```yaml
classification_version: 1
source_commit: 17ce820b91299e72dc532e7ed67046a377c0fd7e
records:
  - asset_id: console.relaylm
    paths: [pyproject.toml]
    entrypoint: "relaylm = relaylm.cli.soul_lab:main"
    responsibility: operator_cli
    lifecycle: active
    owner: soul_lab_runtime
    protected_boundary: supported local RelayLM ASGI and SOUL Lab launch
    current_callers: [installed relaylm command, local operator invocation]
    invocation_roots: [console_script]
    evidence:
      - "pyproject.toml [project.scripts]"
      - relaylm/cli/soul_lab.py
      - relaylm/soul_lab_app.py
      - tests/test_relaylm_soul_lab_entrypoint_boundary.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed
    notes: R4-E2 moved the installed launcher implementation into the CLI package while retaining the ASGI factory in soul_lab_app without an alias or second invocation root

  - asset_id: console.worker
    paths: [pyproject.toml]
    entrypoint: "relaylm-worker = relaylm.cli.worker:main"
    responsibility: operator_cli
    lifecycle: active
    owner: relaymem_worker
    protected_boundary: explicit local one-job worker operation
    current_callers:
      - installed relaylm-worker command
      - local operator invocation
      - scripts/relaylm_o0_local_one_job_runner_security_smoke.py direct main import
    invocation_roots: [console_script]
    evidence:
      - "pyproject.toml [project.scripts]"
      - relaylm/cli/worker.py
      - scripts/relaylm_o0_local_one_job_runner_security_smoke.py
      - tests/test_relaylm_worker_entrypoint_boundary.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed
    notes: R4-B2 moved the implementation without retaining the unsupported old module path or adding a compatibility alias

  - asset_id: console.character_store_bootstrap
    paths: [pyproject.toml]
    entrypoint: "relaylm-character-store-bootstrap = relaylm.cli.character_store_bootstrap:main"
    responsibility: operator_cli
    lifecycle: active
    owner: character_workspace
    protected_boundary: explicit character-store bootstrap
    current_callers:
      - installed relaylm-character-store-bootstrap command
      - local operator invocation
      - scripts/relaylm_e1r2_character_store_bootstrap_smoke.py direct main import
    invocation_roots: [console_script]
    evidence:
      - "pyproject.toml [project.scripts]"
      - relaylm/cli/character_store_bootstrap.py
      - scripts/relaylm_e1r2_character_store_bootstrap_smoke.py
      - tests/test_relaylm_character_store_bootstrap_entrypoint_boundary.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed
    notes: R4-C2 moved the implementation without retaining the unsupported old module path or adding a compatibility alias

  - asset_id: console.character_create
    paths: [pyproject.toml]
    entrypoint: "relaylm-character-create = relaylm.cli.character_creation:main_create"
    responsibility: operator_cli
    lifecycle: active
    owner: character_workspace
    protected_boundary: explicit character creation
    current_callers: [installed relaylm-character-create command, local operator invocation]
    invocation_roots: [console_script]
    evidence:
      - "pyproject.toml [project.scripts]"
      - relaylm/cli/character_creation.py
      - tests/test_relaylm_character_creation_entrypoint_boundary.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed
    notes: R4-D2 moved the shared two-command implementation without retaining the unsupported old module path or adding a compatibility alias

  - asset_id: console.character_template_validate
    paths: [pyproject.toml]
    entrypoint: "relaylm-character-template-validate = relaylm.cli.character_creation:main_validate"
    responsibility: operator_cli
    lifecycle: active
    owner: character_workspace
    protected_boundary: explicit character-template validation
    current_callers: [installed relaylm-character-template-validate command, local operator invocation]
    invocation_roots: [console_script]
    evidence:
      - "pyproject.toml [project.scripts]"
      - relaylm/cli/character_creation.py
      - tests/test_relaylm_character_creation_entrypoint_boundary.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed
    notes: R4-D2 moved the shared two-command implementation without retaining the unsupported old module path or adding a compatibility alias

  - asset_id: console.runtime_install
    paths: [pyproject.toml]
    entrypoint: "relaylm-runtime-install = relaylm.cli.runtime_install:main"
    responsibility: operator_cli
    lifecycle: active
    owner: runtime_install
    protected_boundary: explicit dry-run-first runtime install and preflight operation
    current_callers:
      - installed relaylm-runtime-install command
      - local operator invocation
      - scripts/relaylm_pm_d7_runtime_install_hook_fold_in_smoke.py direct main import
    invocation_roots: [console_script]
    evidence:
      - "pyproject.toml [project.scripts]"
      - relaylm/cli/runtime_install.py
      - scripts/relaylm_pm_d7_runtime_install_hook_fold_in_smoke.py
      - tests/test_relaylm_repo_inventory.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed
    notes: R4-A3 moved the implementation without retaining the unsupported old module path or adding a compatibility alias

  - asset_id: repo_inventory.entrypoint
    paths: [scripts/relaylm_repo_inventory_cli.py]
    responsibility: repository_validation
    lifecycle: active
    owner: repository_maintenance
    protected_boundary: sole supported direct repository-inventory operator and workflow entry point
    current_callers:
      - .github/workflows/repository-storage-inventory.yml
      - docs/evidence/implementation/repository_inventory_baseline_1ca928cd.md reproduction command
      - tests/test_relaylm_repo_inventory.py operator-root assertion
    invocation_roots: [operator_cli, github_actions_step]
    evidence:
      - scripts/relaylm_repo_inventory_cli.py
      - .github/workflows/repository-storage-inventory.yml
      - tests/test_relaylm_repo_inventory.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed
    notes: R2-A retained this function-oriented wrapper because scripts is a flat non-installed tooling directory and all supported callers already use it

  - asset_id: repo_inventory.implementation
    paths:
      - scripts/relaylm_repo_inventory/__init__.py
      - scripts/relaylm_repo_inventory/cli.py
      - scripts/relaylm_repo_inventory/config_deps.py
      - scripts/relaylm_repo_inventory/invocations.py
      - scripts/relaylm_repo_inventory/repo.py
      - scripts/relaylm_repo_inventory/records.py
      - scripts/relaylm_repo_inventory/report.py
      - scripts/relaylm_repo_inventory/storage.py
      - scripts/relaylm_repo_inventory/storage_root_links.py
      - scripts/relaylm_repo_inventory/subprocess_aliases.py
      - scripts/relaylm_repo_inventory/toml_dependencies.py
    responsibility: repository_validation
    lifecycle: active
    owner: repository_maintenance
    protected_boundary: import-only discovery and rendering implementation for current inventory evidence
    current_callers: [scripts/relaylm_repo_inventory_cli.py, repository inventory tests]
    invocation_roots: []
    invocation_root_reason: internal package reached from the supported wrapper and maintained tests; R2-A removed the unsupported cli.py main guard
    evidence:
      - scripts/relaylm_repo_inventory/cli.py
      - scripts/relaylm_repo_inventory/invocations.py
      - scripts/relaylm_repo_inventory/records.py
      - tests/test_relaylm_repo_inventory.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: repo_inventory.workflow
    paths: [.github/workflows/repository-storage-inventory.yml]
    responsibility: repository_validation
    lifecycle: active
    owner: repository_maintenance
    protected_boundary: reproducible inventory and classification validation, deterministic rendering, and artifact upload
    current_callers: [pull_request path-filter trigger, workflow_dispatch]
    invocation_roots: [github_actions_step]
    evidence:
      - .github/workflows/repository-storage-inventory.yml
      - scripts/relaylm_repository_asset_classification_registry.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: repo_inventory.tests
    paths: [tests/test_relaylm_repo_inventory.py]
    responsibility: ordinary_test
    lifecycle: active
    owner: repository_maintenance
    protected_boundary: regression coverage for discovery, determinism, cross-mode behavior, subprocess and dynamic-import expansion, storage linkage, config evidence, and one canonical repository-inventory entry point
    current_callers: [.github/workflows/repository-storage-inventory.yml, maintained pytest suite]
    invocation_roots: [pytest_root]
    evidence:
      - tests/test_relaylm_repo_inventory.py
      - .github/workflows/repository-storage-inventory.yml
    removal_gate: null
    replacement_validation: null
    confidence: confirmed
    notes: R2-B consolidated the cross-mode and final-hardening partitions without removing their assertions

  - asset_id: asset_classification.registry
    paths: [records/repository/asset_classification_v1.yaml]
    responsibility: repository_validation
    lifecycle: active
    owner: repository_maintenance
    protected_boundary: machine-readable mirror of reviewed classification records and explicit canonical-entrypoint claims
    current_callers:
      - scripts/relaylm_repository_asset_classification_registry.py
      - .github/workflows/repository-storage-inventory.yml
      - tests/test_relaylm_repository_asset_classification_registry.py
    invocation_roots: [static_or_package_data]
    evidence:
      - records/repository/asset_classification_v1.yaml
      - docs/reference/repository-asset-classification.md
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: asset_classification.validator
    paths: [scripts/relaylm_repository_asset_classification_registry.py]
    responsibility: repository_validation
    lifecycle: active
    owner: repository_maintenance
    protected_boundary: fail-closed registry drift, schema, path, lifecycle-gate, canonical-entrypoint, and deterministic-render validation
    current_callers:
      - .github/workflows/repository-storage-inventory.yml
      - tests/test_relaylm_repository_asset_classification_registry.py
      - operator validation command
    invocation_roots: [operator_cli, github_actions_step]
    evidence:
      - scripts/relaylm_repository_asset_classification_registry.py
      - records/repository/asset_classification_v1.yaml
      - tests/test_relaylm_repository_asset_classification_registry.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: asset_classification.tests
    paths: [tests/test_relaylm_repository_asset_classification_registry.py]
    responsibility: ordinary_test
    lifecycle: active
    owner: repository_maintenance
    protected_boundary: regression coverage for mirror drift, enum and path rejection, lifecycle gates, retired-state safety, and canonical-entrypoint uniqueness
    current_callers: [.github/workflows/repository-storage-inventory.yml, maintained pytest suite]
    invocation_roots: [pytest_root]
    evidence:
      - tests/test_relaylm_repository_asset_classification_registry.py
      - scripts/relaylm_repository_asset_classification_registry.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: scheduler.o3_cli
    paths: [scripts/relaylm_o3_always_on_local_scheduler.py]
    responsibility: operator_cli
    lifecycle: active
    owner: relaymem_scheduler
    protected_boundary: opt-in local O2 process wrapper, signal cancellation, JSON projection, and bounded exit codes
    current_callers:
      - docs/architecture/o3_always_on_local_scheduler.md
      - scripts/relaylm_o3_always_on_local_scheduler_smoke.py
    invocation_roots: [operator_cli, subprocess_child]
    evidence:
      - scripts/relaylm_o3_always_on_local_scheduler.py
      - docs/architecture/o3_always_on_local_scheduler.md
      - scripts/relaylm_o3_always_on_local_scheduler_smoke.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: scheduler.o3_process_smoke
    paths: [scripts/relaylm_o3_always_on_local_scheduler_smoke.py]
    responsibility: process_smoke
    lifecycle: active
    owner: relaymem_scheduler
    protected_boundary: real subprocess invocation, stdout and stderr contract, exit status, config failure, and disclosure boundary
    current_callers: [docs/architecture/o3_always_on_local_scheduler.md validation commands]
    invocation_roots: [smoke_only_root]
    evidence:
      - scripts/relaylm_o3_always_on_local_scheduler_smoke.py
      - docs/architecture/o3_always_on_local_scheduler.md
    removal_gate: null
    replacement_validation: null
    confidence: confirmed
    notes: must not be converted to an in-process test solely to reduce file count

  - asset_id: retrieval.primary_recall_characterization
    paths: [scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py]
    responsibility: migration_or_maintenance
    lifecycle: transitional
    owner: retrieval_migration
    protected_boundary: current Primary MEM scoped recall, grounding, disabled-store behavior, and content-free public projection characterization while LC-1 and RT-1 remain open
    current_callers:
      - scripts/relaylm_mvp_eval_runner_registry.py E1_SCRIPTS
      - docs/architecture/e1_evaluation_consolidation.md
    invocation_roots: [registry, smoke_only_root]
    evidence:
      - scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py
      - scripts/relaylm_mvp_eval_runner_registry.py
      - docs/architecture/e1_evaluation_consolidation.md
      - docs/architecture/project_execution_plan.md
    removal_gate: RT-1 establishes one ordinary Subjective MEM Retrieval authority and the MVP evaluation registry no longer requires Primary MEM characterization
    replacement_validation: exact old/new characterization comparison, exact-current Subjective MEM selection, lifecycle and mutation fail-closed checks, rebuild-equivalent projection validation, disclosure regression, and negative-reference validation on the accepted RT-1 head
    confidence: confirmed
```

## Decision summary

```text
active: 15
transitional: 1
retired: 0
```

No classified responsibility in this bounded surface is retired. R2-B retires two redundant pytest file partitions through Git history while preserving every assertion in the active repository-inventory test owner.

## Explicit unknowns and unclassified surfaces

The following remain unresolved and must not be guessed:

- current complete inventory row counts at `17ce820b...`; the committed baseline is fixed to `1ca928cd...`;
- runtime expansion of dynamically assembled imports, registries, plugin-style lookup, and subprocess commands;
- responsibility and lifecycle outside the bounded registry above;
- whether each discovered `python -m` root is supported or only an implementation convenience;
- whether milestone-named smoke outside this surface is active regression, process validation, transitional characterization, or retired;
- any retirement disposition for Primary MEM, ordinary Retrieval, Subjective MEM publication, lifecycle, recovery, rollback, or characterization before the owning LC-1 or RT-1 gate closes.

## Wave register and accepted decisions

### R2-A: repository inventory entry-point consolidation

```text
canonical supported invocation:
  python scripts/relaylm_repo_inventory_cli.py <arguments>

import-only implementation:
  scripts/relaylm_repo_inventory/cli.py
```

The top-level wrapper remains the supported entry point. The internal `cli.py` main guard was removed without changing scan modes, self-test, formats, output paths, exit behavior, or implementation imports.

### R2-B: repository inventory test consolidation

R2-B consolidates all repository-inventory pytest responsibility into `tests/test_relaylm_repo_inventory.py`. The cross-mode and final-hardening partitions are deleted from the current tree after their six tests are moved unchanged. The dedicated workflow continues to execute the canonical-entrypoint regression by its new path, and the classification authority and mirror identify one maintained pytest owner. Process, operator, migration, and characterization assets are unaffected.

### R2-C: process-smoke retention and naming review

Use O3 as a control example. Subprocess, output, exit-code, platform, filesystem, security, concurrency, restart, and operator boundaries remain explicit process smoke. Function-oriented renames occur only through an owning atomic migration with complete caller updates.

### R3-A: generated classification registry and drift check

R3-A adds a machine-readable mirror and fail-closed validator. The validator rejects document/registry drift, unknown enums, missing paths, unexpanded globs, duplicate IDs, incomplete transitional gates, retired records with live responsibilities, and competing canonical-entrypoint claims. It renders deterministic JSON and Markdown navigation evidence.

The reviewed document remains upstream authority. Registry and generated outputs remain navigation and review evidence only.

### R4: installed CLI package moves

R4-A1 added generic console-target integrity validation. R4-A2 proved that `relaylm-runtime-install` is the sole supported runtime-install invocation, removed the unsupported `python -m relaylm.runtime_install_cli` root, and locked the direct PM-D7 smoke caller. R4-A3 moved that implementation to `relaylm/cli/runtime_install.py`, updated every accepted caller and mirror, and deleted the old module without a compatibility alias.

R4-B1 proved that `relaylm-worker` is the sole supported worker invocation, removed the unsupported `python -m relaylm.local_worker_cli` root, and locked the O0 security-smoke caller. R4-B2 moved that implementation to `relaylm/cli/worker.py`, updated the installed target, direct caller, focused regression, authority, and mirror, and deleted the old module without a compatibility alias.

R4-C1 proved that `relaylm-character-store-bootstrap` is the sole supported character-store bootstrap invocation, removed the unsupported `python -m relaylm.character_store_bootstrap_cli` root, and locked the direct E1-R2 smoke caller. R4-C2 moved that implementation to `relaylm/cli/character_store_bootstrap.py`, updated the installed target, direct caller, focused regression, authority, and mirror, and deleted the old module without a compatibility alias.

R4-D1 proved that `relaylm-character-create` and `relaylm-character-template-validate` are the two supported installed roots for one shared implementation, removed the asymmetric unsupported `python -m relaylm.character_creation_cli` root, and locked both console targets as one ownership boundary. R4-D2 moved that shared implementation to `relaylm/cli/character_creation.py`, updated both installed targets, the focused regression, authority, and mirror, and deleted the old module without a compatibility alias.

R4-E1 proved that `relaylm` is the sole supported installed product launch, removed the unsupported `python -m relaylm.soul_lab_app` root, retained the distinct documented `python -m relaylm.app` Core fallback, and locked the installed target without changing the ASGI factory or management routes. R4-E2 moves only the installed launcher implementation to `relaylm/cli/soul_lab.py`, updates the console target, focused regression, authority, and mirror, removes `main` from the ASGI module, and retains `relaylm.soul_lab_app:create_app` as the sole SOUL Lab ASGI ownership boundary without an alias.

All six installed console implementation owners now live under `relaylm/cli/`. The `relaylm.soul_lab_app:create_app` ASGI factory remains outside that package because it owns runtime routes rather than operator parsing. Any later pre-RT-1 move requires complete direct, dynamic, subprocess, workflow, test, documentation, and operator evidence and must not touch active LC-1, Subjective MEM publication, ordinary Retrieval, or Primary MEM authority.

## Parallel-safety and non-goals

R4-E2 changes only the installed RelayLM launcher owner, its console target, its focused entrypoint regression, and the Lane R classification authority/mirror. It leaves `relaylm.soul_lab_app:create_app` and every management route in place and does not change command arguments, environment propagation, config loading, uvicorn target, host, port, HTTP APIs, UI behavior, feature gates, user state, Primary MEM, `docs/PROJECT_STATUS.md`, Lane C, Lane D, LC-1, or RT-1 paths.

Every later R2, R3, or R4 PR must refresh `main`, open PRs, exact callers, workflows, review threads, and authority overlap before treating a candidate above as executable.

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

This page defines the canonical Lane R responsibility and lifecycle classification format and records the first bounded R1 classification surface.

```text
repository: rinsakamo/relay-lm
source main: 555ce47c8b558fde77230973d148f78420702b93
source main meaning: squash merge of PR #668
lane: R
stage: R1 responsibility classification
P0 scope: classification and candidate planning only
```

Classification is evidence for later review. It does not authorize deletion, movement, rename, consolidation, behavior change, compatibility removal, storage migration, or status changes. Every destructive or authority-affecting action requires its own atomic PR and fresh caller evidence.

Assets not explicitly listed in the bounded registry below remain `unclassified` for R1 purposes even when the mechanical inventory reports an invocation root or low reachability.

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
| `protected_boundary` | required | Runtime, operator, process, migration, recovery, or governance boundary protected by the asset. |
| `current_callers` | required for `active` and `transitional` | Current direct, indirect, dynamic, subprocess, workflow, operator, test, or documentation callers. |
| `invocation_roots` | required | Mechanical root kinds supporting the decision. An empty list requires `invocation_root_reason`. |
| `invocation_root_reason` | required when `invocation_roots` is empty | Why the asset is internal rather than independently invoked. |
| `evidence` | required | Exact current repository anchors used for the decision. |
| `removal_gate` | required for `transitional` | Explicit event that must close before retirement review. Active records use `null`. |
| `replacement_validation` | required for `transitional` | Validation that must replace the protected responsibility before retirement. Active records use `null`. |
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

These are discovery categories, not responsibility decisions. R1 review must inspect FastAPI/request paths, installed commands, supported `python -m` entry points, workflows, subprocesses, dynamic registries, tests, process smoke, migrations, recovery and rollback tools, generators, benchmarks, repository validators, and current runbooks where applicable.

The fixed `1ca928cd` baseline counted 731 roots. It is historical mechanical evidence, not a current complete classification. Current caller inspection at the source revision above controls each listed decision.

## Initial bounded classification registry

The following YAML-shaped records are the canonical human-reviewed representation for this R1 slice. They are not yet a generated registry.

```yaml
classification_version: 1
source_commit: 555ce47c8b558fde77230973d148f78420702b93
records:
  - asset_id: console.relaylm
    paths: [pyproject.toml]
    entrypoint: "relaylm = relaylm.soul_lab_app:main"
    responsibility: operator_cli
    lifecycle: active
    owner: soul_lab_runtime
    protected_boundary: supported local RelayLM ASGI and SOUL Lab launch
    current_callers: [installed relaylm command, local operator invocation]
    invocation_roots: [console_script]
    evidence: ["pyproject.toml [project.scripts]", relaylm/soul_lab_app.py]
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: console.worker
    paths: [pyproject.toml]
    entrypoint: "relaylm-worker = relaylm.local_worker_cli:main"
    responsibility: operator_cli
    lifecycle: active
    owner: relaymem_worker
    protected_boundary: explicit local one-job worker operation
    current_callers: [installed relaylm-worker command, local operator invocation]
    invocation_roots: [console_script]
    evidence: ["pyproject.toml [project.scripts]", relaylm/local_worker_cli.py]
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: console.character_store_bootstrap
    paths: [pyproject.toml]
    entrypoint: "relaylm-character-store-bootstrap = relaylm.character_store_bootstrap_cli:main"
    responsibility: operator_cli
    lifecycle: active
    owner: character_workspace
    protected_boundary: explicit character-store bootstrap
    current_callers: [installed relaylm-character-store-bootstrap command, local operator invocation]
    invocation_roots: [console_script]
    evidence: ["pyproject.toml [project.scripts]", relaylm/character_store_bootstrap_cli.py]
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: console.character_create
    paths: [pyproject.toml]
    entrypoint: "relaylm-character-create = relaylm.character_creation_cli:main_create"
    responsibility: operator_cli
    lifecycle: active
    owner: character_workspace
    protected_boundary: explicit character creation
    current_callers: [installed relaylm-character-create command, local operator invocation]
    invocation_roots: [console_script]
    evidence: ["pyproject.toml [project.scripts]", relaylm/character_creation_cli.py]
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: console.character_template_validate
    paths: [pyproject.toml]
    entrypoint: "relaylm-character-template-validate = relaylm.character_creation_cli:main_validate"
    responsibility: operator_cli
    lifecycle: active
    owner: character_workspace
    protected_boundary: explicit character-template validation
    current_callers: [installed relaylm-character-template-validate command, local operator invocation]
    invocation_roots: [console_script]
    evidence: ["pyproject.toml [project.scripts]", relaylm/character_creation_cli.py]
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: console.runtime_install
    paths: [pyproject.toml]
    entrypoint: "relaylm-runtime-install = relaylm.runtime_install_cli:main"
    responsibility: operator_cli
    lifecycle: active
    owner: runtime_install
    protected_boundary: explicit dry-run-first runtime install and preflight operation
    current_callers: [installed relaylm-runtime-install command, local operator invocation]
    invocation_roots: [console_script]
    evidence: ["pyproject.toml [project.scripts]", relaylm/runtime_install_cli.py]
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: repo_inventory.entrypoint
    paths: [scripts/relaylm_repo_inventory_cli.py]
    responsibility: repository_validation
    lifecycle: active
    owner: repository_maintenance
    protected_boundary: deterministic non-destructive repository, invocation, config, and storage inventory entry point
    current_callers:
      - .github/workflows/repository-storage-inventory.yml
      - docs/evidence/implementation/repository_inventory_baseline_1ca928cd.md
      - repository inventory subprocess tests
    invocation_roots: [github_actions_step, subprocess_child]
    evidence:
      - scripts/relaylm_repo_inventory_cli.py
      - .github/workflows/repository-storage-inventory.yml
      - tests/test_relaylm_repo_inventory.py
      - tests/test_relaylm_repo_inventory_cross_mode_hardening.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed
    notes: wrapper/core pair is an R2 investigation candidate, not a retirement decision

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
    protected_boundary: discovery and rendering implementation for current inventory evidence
    current_callers: [scripts/relaylm_repo_inventory_cli.py, repository inventory tests]
    invocation_roots: []
    invocation_root_reason: internal package reached from the supported wrapper and maintained tests
    evidence:
      - scripts/relaylm_repo_inventory/cli.py
      - scripts/relaylm_repo_inventory/invocations.py
      - scripts/relaylm_repo_inventory/records.py
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: repo_inventory.workflow
    paths: [.github/workflows/repository-storage-inventory.yml]
    responsibility: repository_validation
    lifecycle: active
    owner: repository_maintenance
    protected_boundary: reproducible inventory self-test, report generation, and artifact upload
    current_callers: [pull_request path-filter trigger, workflow_dispatch]
    invocation_roots: [github_actions_step]
    evidence: [.github/workflows/repository-storage-inventory.yml]
    removal_gate: null
    replacement_validation: null
    confidence: confirmed

  - asset_id: repo_inventory.tests
    paths:
      - tests/test_relaylm_repo_inventory.py
      - tests/test_relaylm_repo_inventory_cross_mode_hardening.py
      - tests/test_relaylm_repo_inventory_final_hardening.py
    responsibility: ordinary_test
    lifecycle: active
    owner: repository_maintenance
    protected_boundary: regression coverage for discovery, determinism, cross-mode behavior, and hardening
    current_callers: [maintained pytest suite]
    invocation_roots: [pytest_root]
    evidence:
      - tests/test_relaylm_repo_inventory.py
      - tests/test_relaylm_repo_inventory_cross_mode_hardening.py
      - tests/test_relaylm_repo_inventory_final_hardening.py
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
active: 12
transitional: 1
retired: 0
```

No asset in this bounded surface is retired. Every record has a current supported caller or an open protected migration responsibility. R1 performs no deletion.

## Explicit unknowns and unclassified surfaces

The following remain unresolved and must not be guessed:

- current complete row counts at `555ce47c...`; the committed baseline is fixed to `1ca928cd...`;
- runtime expansion of dynamically assembled imports, registries, plugin-style lookup, and subprocess commands;
- responsibility and lifecycle outside the bounded registry above;
- whether each discovered `python -m` root is supported or only an implementation convenience;
- whether the three inventory pytest files should remain partitioned after complete overlap review;
- whether milestone-named smoke outside this surface is active regression, process validation, transitional characterization, or retired;
- any retirement disposition for Primary MEM, ordinary Retrieval, Subjective MEM publication, lifecycle, recovery, rollback, or characterization before the owning LC-1 or RT-1 gate closes.

## Registered candidate waves

### R2-A: repository inventory entry-point consolidation

Highest-confidence bounded R2 candidate after R1 acceptance:

```text
scripts/relaylm_repo_inventory_cli.py
scripts/relaylm_repo_inventory/cli.py
.github/workflows/repository-storage-inventory.yml
tests/test_relaylm_repo_inventory.py
tests/test_relaylm_repo_inventory_cross_mode_hardening.py
tests/test_relaylm_repo_inventory_final_hardening.py
docs/evidence/implementation/repository_inventory_baseline_1ca928cd.md
```

Before implementation, select one canonical invocation; preserve all scan modes, self-test, output formats, exit behavior, determinism, and artifact paths; update every workflow, test, and current document caller atomically; prove no supported wrapper caller remains; and run negative-reference checks. Removal uses Git history, not an executable archive.

### R2-B: repository inventory test partition review

Review the three pytest files for duplicated setup and assertions. Consolidate only when cross-mode, subprocess, deterministic-output, and negative coverage remain clear. File-count reduction alone is insufficient.

### R2-C: process-smoke retention and naming review

Use O3 as a control example. Subprocess, output, exit-code, platform, filesystem, security, concurrency, restart, and operator boundaries remain explicit process smoke. Function-oriented renames occur only through an owning atomic migration with complete caller updates.

### R3-A: generated classification registry and drift check

After this schema is accepted, generate a machine-readable registry from explicit records rather than reachability inference. Reject unknown enum values, missing paths, unexpanded globs, duplicate IDs, transitional records missing required gates, retired records with live callers, and competing canonical entry points. Generated output remains navigation and evidence, not retirement authority.

### R4-A: installed CLI package-move discovery

The six console-script records are eligible for caller discovery only. A pre-RT-1 move requires complete direct, dynamic, subprocess, workflow, test, documentation, and operator evidence and must not touch active LC-1, Subjective MEM publication, ordinary Retrieval, or Primary MEM authority.

## Parallel-safety and non-goals

This initial R1 boundary changes only this classification reference. It does not change `docs/PROJECT_STATUS.md`, runtime or storage behavior, APIs, UI, feature gates, schemas, packages, imports, console scripts, workflows, tests, smoke, Lane D retirement decisions, LC-1 or RT-1 authority paths, current callers, or generated registries.

Every later R2, R3, or R4 PR must refresh `main`, open PRs, exact callers, workflows, review threads, and authority overlap before treating a candidate above as executable.
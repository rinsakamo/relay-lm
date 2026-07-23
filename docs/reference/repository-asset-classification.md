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

The classification source revision is:

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

A classification record has the following fields:

| Field | Requirement | Meaning |
|---|---|---|
| `asset_id` | required | Stable identifier for the record, independent of row order. |
| `paths` | required | Exact repository path or an explicitly enumerated path family. Unexpanded globs are not classification evidence. |
| `responsibility` | required | One accepted responsibility class. |
| `lifecycle` | required | `active`, `transitional`, or `retired`. |
| `owner` | required | Maintainer or subsystem that owns the continuing responsibility. |
| `protected_boundary` | required | Runtime, operator, process, migration, recovery, or governance boundary the asset protects. |
| `current_callers` | required for `active` and `transitional` | Current direct, indirect, dynamic, subprocess, workflow, operator, test, or documentation callers. |
| `invocation_roots` | required | Mechanical invocation-root kinds that support the classification. Empty is permitted only with an explicit reason. |
| `evidence` | required | Exact current repository anchors used for the decision. |
| `removal_gate` | required for `transitional`; prohibited as an implied promise for `active` | Explicit event that must close before retirement review. |
| `replacement_validation` | required for `transitional` | Validation that must replace the protected responsibility before retirement. |
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

The current non-destructive inventory tool recognizes the following mechanical root kinds:

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

These are discovery categories, not responsibility decisions. R1 review must inspect, where applicable:

- FastAPI and request-path imports;
- installed console scripts and supported operator commands;
- supported `python -m` entry points;
- GitHub Actions steps;
- subprocess children and command aliases;
- dynamic imports, registries, and plugin-style dispatch;
- tests and process-level smoke;
- migration, recovery, rollback, maintenance, generator, and benchmark tooling;
- repository and evidence validators;
- current documentation and runbooks.

The fixed `1ca928cd` baseline counted 731 invocation roots, but it is historical mechanical evidence rather than a current complete classification. Current caller inspection at the source revision above remains authoritative for each listed decision.

## Initial bounded classification registry

### Installed console commands

All six installed console commands are classified as active operator entry points. This classification covers the entry-point records in `pyproject.toml`; it does not classify every imported implementation module behind them.

| `asset_id` | Paths / target | Responsibility | Lifecycle | Owner | Protected boundary | Current callers and roots | Confidence |
|---|---|---|---|---|---|---|---|
| `console.relaylm` | `pyproject.toml`: `relaylm = relaylm.soul_lab_app:main` | `operator_cli` | `active` | `soul_lab_runtime` | supported local RelayLM application launch | packaging `console_script`; operator invocation | `confirmed` |
| `console.worker` | `pyproject.toml`: `relaylm-worker = relaylm.local_worker_cli:main` | `operator_cli` | `active` | `relaymem_worker` | supported local worker operation | packaging `console_script`; operator invocation | `confirmed` |
| `console.character_store_bootstrap` | `pyproject.toml`: `relaylm-character-store-bootstrap = relaylm.character_store_bootstrap_cli:main` | `operator_cli` | `active` | `character_workspace` | explicit character-store bootstrap | packaging `console_script`; operator invocation | `confirmed` |
| `console.character_create` | `pyproject.toml`: `relaylm-character-create = relaylm.character_creation_cli:main_create` | `operator_cli` | `active` | `character_workspace` | explicit character creation | packaging `console_script`; operator invocation | `confirmed` |
| `console.character_template_validate` | `pyproject.toml`: `relaylm-character-template-validate = relaylm.character_creation_cli:main_validate` | `operator_cli` | `active` | `character_workspace` | explicit template validation | packaging `console_script`; operator invocation | `confirmed` |
| `console.runtime_install` | `pyproject.toml`: `relaylm-runtime-install = relaylm.runtime_install_cli:main` | `operator_cli` | `active` | `runtime_install` | dry-run-first runtime install and preflight operation | packaging `console_script`; operator invocation | `confirmed` |

Removal gates do not apply to these active records. A future package move must preserve the installed command names and behavior or explicitly migrate them through the owning atomic PR.

### Repository inventory and validation family

The following exact family is one active repository-validation surface:

```text
scripts/relaylm_repo_inventory_cli.py
scripts/relaylm_repo_inventory/__init__.py
scripts/relaylm_repo_inventory/cli.py
scripts/relaylm_repo_inventory/config_deps.py
scripts/relaylm_repo_inventory/invocations.py
scripts/relaylm_repo_inventory/repo.py
scripts/relaylm_repo_inventory/records.py
scripts/relaylm_repo_inventory/report.py
scripts/relaylm_repo_inventory/storage.py
scripts/relaylm_repo_inventory/storage_root_links.py
scripts/relaylm_repo_inventory/subprocess_aliases.py
scripts/relaylm_repo_inventory/toml_dependencies.py
.github/workflows/repository-storage-inventory.yml
tests/test_relaylm_repo_inventory.py
tests/test_relaylm_repo_inventory_cross_mode_hardening.py
tests/test_relaylm_repo_inventory_final_hardening.py
```

| `asset_id` | Paths | Responsibility | Lifecycle | Owner | Protected boundary | Current callers and roots | Evidence | Confidence |
|---|---|---|---|---|---|---|---|---|
| `repo_inventory.entrypoint` | `scripts/relaylm_repo_inventory_cli.py` | `repository_validation` | `active` | `repository_maintenance` | deterministic non-destructive repository, invocation, config, and storage inventory entry point | GitHub workflow steps; documented reproduction commands; subprocess-based tests | wrapper imports `relaylm_repo_inventory.cli:main`; workflow executes `--self-test` and report generation | `confirmed` |
| `repo_inventory.implementation` | enumerated `scripts/relaylm_repo_inventory/*.py` files above | `repository_validation` | `active` | `repository_maintenance` | discovery and rendering implementation for current inventory evidence | wrapper import; internal package imports; direct test imports | `cli.py` collects invocation, storage, config, subprocess-alias, and report surfaces without making removal decisions | `confirmed` |
| `repo_inventory.workflow` | `.github/workflows/repository-storage-inventory.yml` | `repository_validation` | `active` | `repository_maintenance` | reproducible CI artifact generation and self-test | `github_actions_step`; pull-request path filters; manual dispatch | invokes the wrapper for self-test, JSON, Markdown, and artifact upload | `confirmed` |
| `repo_inventory.tests` | three enumerated `tests/test_relaylm_repo_inventory*.py` files above | `ordinary_test` | `active` | `repository_maintenance` | regression coverage for inventory discovery, determinism, and cross-mode behavior | `pytest_root`; direct wrapper/package imports and subprocess execution | current maintained pytest suite | `confirmed` |

The wrapper/core shape is a high-confidence R2 investigation candidate, not a retirement decision. The wrapper is currently a supported workflow and documentation entry point, so it remains active until an atomic consolidation proves one canonical invocation and updates every caller.

### O3 local scheduler operator boundary

| `asset_id` | Paths | Responsibility | Lifecycle | Owner | Protected boundary | Current callers and roots | Evidence | Confidence |
|---|---|---|---|---|---|---|---|---|
| `scheduler.o3_cli` | `scripts/relaylm_o3_always_on_local_scheduler.py` | `operator_cli` | `active` | `relaymem_scheduler` | opt-in local O2 process wrapper, signal cancellation, JSON projection, and bounded exit codes | documented operator commands; direct subprocess smoke; `operator_cli` root | current O3 architecture page and CLI implementation | `confirmed` |
| `scheduler.o3_process_smoke` | `scripts/relaylm_o3_always_on_local_scheduler_smoke.py` | `process_smoke` | `active` | `relaymem_scheduler` | real subprocess invocation, stdout/stderr contract, exit status, config failure, and disclosure boundary | architecture validation command; subprocess child invoking the O3 CLI | smoke uses `subprocess.run` and validates process output rather than only in-process functions | `confirmed` |

The O3 process smoke must not be converted to an in-process pytest solely to reduce file count because its protected boundary includes subprocess execution and process output.

### Primary MEM retrieval characterization

| `asset_id` | Paths | Responsibility | Lifecycle | Owner | Protected boundary | Current callers and roots | Removal gate | Replacement validation | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| `retrieval.primary_recall_characterization` | `scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py` | `process_smoke` | `transitional` | `retrieval_migration` | current Primary MEM scoped recall, grounding, disabled-store behavior, and content-free public projection characterization while LC-1 and RT-1 remain open | `scripts/relaylm_mvp_eval_runner_registry.py` `E1_SCRIPTS`; current E1 evaluation documentation; explicit smoke root | RT-1 establishes one ordinary Subjective MEM Retrieval authority and the MVP evaluation registry no longer requires this Primary MEM characterization | exact old/new characterization comparison, exact-current Subjective MEM selection, lifecycle/mutation fail-closed checks, rebuild-equivalent projection validation, disclosure regression, and negative-reference validation on the accepted RT-1 head | `confirmed` |

This transitional smoke is not retired merely because its name refers to E1-R5 or because it is outside the default application import graph.

### Retired decisions in this bounded surface

None.

Every classified asset in this initial surface has a current supported caller or an open protected migration responsibility. R1 therefore makes no retirement claim and performs no deletion.

## Explicit unknowns and unclassified surfaces

The following remain unresolved and must not be guessed:

- current complete row counts at `555ce47c...`; the committed baseline is fixed to `1ca928cd...` and must not be silently treated as current;
- runtime expansion of dynamically assembled imports, registries, plugin-style lookup, and subprocess commands;
- responsibility and lifecycle of scripts, workflows, tests, smoke, migrations, generators, benchmarks, and operator commands outside the bounded registry above;
- whether each discovered `python -m` root is a supported public/operator entry point or only an implementation convenience;
- whether the three repository-inventory pytest modules should remain partitioned after a complete overlap review;
- whether any milestone-named smoke outside this bounded surface is active regression, process validation, transitional characterization, or genuinely retired;
- any retirement disposition for Primary MEM, ordinary Retrieval, Subjective MEM publication, lifecycle, recovery, rollback, or characterization assets before their owning LC-1 or RT-1 gate closes.

## Registered candidate waves

### R2-A: repository inventory entry-point consolidation

Priority: highest-confidence bounded R2 candidate after this R1 classification is accepted.

Candidate scope:

```text
scripts/relaylm_repo_inventory_cli.py
scripts/relaylm_repo_inventory/cli.py
.github/workflows/repository-storage-inventory.yml
tests/test_relaylm_repo_inventory*.py
docs/evidence/implementation/repository_inventory_baseline_1ca928cd.md
```

Required proof before implementation:

- select one canonical supported invocation;
- preserve `--self-test`, all scan modes, output formats, exit behavior, deterministic output, and artifact paths;
- update workflow, tests, and current documentation atomically;
- prove no supported direct wrapper caller remains before wrapper retirement;
- run negative-reference checks for the retired path;
- recover any removed wrapper through Git history rather than an executable archive.

### R2-B: repository inventory test partition review

Review the three maintained pytest modules for duplicated setup and assertions. Consolidate only when the resulting test ownership remains clear and missing cross-mode, subprocess, deterministic-output, and negative cases are preserved. File-count reduction alone is not a reason to merge them.

### R2-C: process-smoke retention and naming review

Use the O3 records as a control example: subprocess, output, exit-code, platform, filesystem, security, concurrency, restart, and operator-path boundaries remain explicit process smoke. Function-oriented renames occur only through the owning atomic migration with complete workflow and documentation caller updates.

### R3-A: generated classification registry and drift check

After the schema and bounded decisions are reviewed, generate a machine-readable registry from explicit records rather than inferring lifecycle from reachability. The drift check must reject:

- unknown responsibility or lifecycle values;
- unexpanded path globs;
- missing paths;
- transitional records without owner, protected boundary, current caller, removal gate, or replacement validation;
- retired records with live current callers or protected gates;
- duplicate asset IDs or competing canonical entry points.

Generated output remains navigation and review evidence only; it cannot authorize retirement.

### R4-A: installed CLI package-move discovery

The six console-script records are eligible for caller discovery only. A pre-RT-1 package move requires complete direct, dynamic, subprocess, workflow, test, documentation, and operator evidence and must not touch active LC-1, Subjective MEM publication, ordinary Retrieval, or Primary MEM authority.

## Parallel-safety and non-goals

This initial R1 boundary changes only this classification reference. It does not change:

- `docs/PROJECT_STATUS.md`;
- runtime or storage behavior;
- API, UI, feature gates, schemas, or state;
- Python packages, imports, console scripts, workflows, tests, or smoke;
- documentation retirement or the Lane D active-graph decision;
- LC-1 or RT-1 authority paths;
- any current caller or generated registry.

A later R2, R3, or R4 PR must refresh `main`, open PRs, exact callers, workflows, review threads, and authority overlap before treating any candidate above as executable.
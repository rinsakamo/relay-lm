---
relaylm_doc_type: evidence
relaylm_authority: repository_inventory_baseline_receipt
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: repository_maintenance
relaylm_update_trigger:
  - this fixed baseline is superseded by a later accepted baseline receipt
  - the inventory tool or its inclusion rules materially change
relaylm_not_authoritative_for:
  - current repository state after the recorded source commit
  - asset responsibility classification
  - dead-code or removal decisions
  - deletion, movement, rename, consolidation, or compatibility removal
  - storage migration or storage authority
  - implementation-debt closure or roadmap sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/repository-maintenance-system.md
  - ../../planning/repository-structure-migration.md
  - ../../architecture/project_execution_plan.md
---
# Repository Inventory Baseline Receipt — `1ca928cd`

## Purpose and authority boundary

This frozen evidence receipt records a commit-fixed repository inventory baseline produced as non-authoritative evidence for the evidence-gated repository simplification proposal revised in PR #624.

It records reproducible mechanical observations from the existing PR #577 inventory tool. It does not classify any asset as removable, obsolete, dead, migratable, or safe to consolidate. Generated row-level inventory is maintainer evidence only and is not documentation, implementation, storage, or roadmap authority.

## Baseline identity

- repository: `rinsakamo/relay-lm`
- source commit: `1ca928cd28541f5a05fece30e9437a7fcf267921`
- source commit meaning: squash merge of PR #624, `docs: revise repository simplification proposal`
- inventory tool: `relaylm_repo_inventory`
- tool version: `1.3.0`
- modes: `config`, `invocations`, `storage`
- Python: `3.12`
- additional installed dependency: `pyyaml`
- generation date: `2026-07-21`

The inventory payload reported the exact source commit above. The generator checked out that commit directly rather than scanning the receipt PR head.

## Exact reproduction commands

Run from a clean checkout of the source commit:

```bash
git checkout 1ca928cd28541f5a05fece30e9437a7fcf267921
python -m pip install --quiet pyyaml
python scripts/relaylm_repo_inventory_cli.py --self-test
python scripts/relaylm_repo_inventory_cli.py --all --format json \
  --output generated/repository_storage_inventory.json
python scripts/relaylm_repo_inventory_cli.py --all --format markdown \
  --output generated/repository_storage_inventory.md
```

The tool self-test runs two consecutive scans and requires byte-identical JSON output.

## Aggregate results

| Inventory surface | Count | Interpretation |
|---|---:|---|
| Storage records | 366 | Mechanical storage/I/O evidence; all remain unclassified |
| Invocation roots | 731 | Static invocation-root observations, not a resolved call graph |
| Config/dependency records | 217 | Config keys, flags, environment variables, dependencies, and workflow tools |
| Unresolved storage classification | 366 | Every storage record remains `classification_state: unclassified` |

### Invocation-root kinds

| Root kind | Count |
|---|---:|
| `console_script` | 6 |
| `dynamic_import` | 6 |
| `fastapi_route` | 32 |
| `frontend_route` | 9 |
| `github_actions_step` | 124 |
| `npm_script` | 12 |
| `operator_cli` | 62 |
| `pytest_root` | 21 |
| `python_dash_m` | 6 |
| `registry` | 5 |
| `smoke_only_root` | 391 |
| `static_or_package_data` | 3 |
| `subprocess_child` | 54 |
| **Total** | **731** |

These root kinds are mechanical invocation categories. They are not the final repository-responsibility classes defined by current repository-maintenance authority. Responsibility classification remains later reviewed work.

### Config/dependency kinds

| Key kind | Count |
|---|---:|
| `config_key` | 101 |
| `env_var` | 3 |
| `extra_or_mode` | 4 |
| `feature_flag` | 94 |
| `node_dependency` | 6 |
| `python_dependency` | 5 |
| `workflow_tool` | 4 |
| **Total** | **217** |

## O3 operator-path protection

The fixed inventory contains exactly one record for `scripts/relaylm_o3_always_on_local_scheduler.py`:

- root ID: `operator_cli:scripts/relaylm_o3_always_on_local_scheduler.py`
- root kind: `operator_cli`
- normalized command: `python scripts/relaylm_o3_always_on_local_scheduler.py`
- source line: 129
- FastAPI import-graph reachability: not applicable

The self-test passed the explicit assertion that O3 is an operator CLI and must not be treated as smoke-only or dead merely because it is outside the default FastAPI import graph.

## Inclusion and exclusion rules

The recorded tool version applies these boundaries:

- storage scan covers Python and JavaScript/TypeScript sources under `relaylm/`, `scripts/`, and `apps/`;
- a storage record requires a code-bound artifact path or observed storage, I/O, locking, or durability API;
- invocation scan covers runtime modules, scripts, tests, application package/route surfaces, `pyproject.toml`, and GitHub Actions workflows;
- config scan covers Python and Node dependency surfaces, `config.example.yaml`, runtime/script/test sources, and workflows;
- `.git`, caches, virtual environments, package/build outputs, `generated`, `dist`, `build`, and `node_modules` are excluded;
- detection is static and non-executing.

## Known limitations

- Dynamic control flow is not executed.
- Storage hidden behind project-specific wrappers can be missed.
- `reachable_from_fastapi_import_graph` describes only the core `relaylm.app` import graph; absence is not dead-code evidence.
- Storage-to-invocation linking is a best-effort textual cross-reference, not a resolved call graph, and can over-match or under-match.
- Literal subprocess and dynamic-import targets are bounded; dynamically assembled targets can remain unresolved.
- Registry records identify dynamic resolution surfaces but do not expand the registry at runtime.
- Pattern-derived values remain heuristic evidence and require human review.

## Self-test receipt

The self-test completed successfully and confirmed, among other checks:

- consecutive scans produced byte-identical JSON;
- JSON parsed successfully;
- all 366 storage records remained `unclassified`;
- each storage record had a concrete path, I/O, locking, or durability anchor;
- inventory implementation files were excluded from storage self-noise;
- O3 was discovered as `operator_cli`;
- required invocation-root families were present;
- multi-line FastAPI, frontend-route, subprocess-child, dependency-extra, JSON I/O, locking, and environment-variable cases were detected.

## Artifact and digest receipt

The bootstrap execution used GitHub Actions run `29824129286` and artifact `8492599489` (`repository-baseline-1ca928cd`). The workflow checked out the fixed baseline source commit before running the tool.

| Artifact | SHA-256 |
|---|---|
| GitHub artifact archive | `763aea60f56d57a6637f3c86728fcee2d872ca54aeec1b622b2bd3362adbfbea` |
| JSON inventory | `5d29cc898fde13a04c591a61ecf4ada520358a2b056bdb7f19ac871780b89fcf` |
| Markdown inventory | `d178aa78bb4e94df9011e226abe1469327a6692d5d37517f980ed45ae3081d37` |
| Self-test output | `bee7e75168d3f4979b4db86734cb3edc2575147382386d8a29f79b45d8441e71` |

The row-level JSON and Markdown reports remain generated artifacts rather than committed authority. Artifact retention is temporary; the fixed source SHA, exact commands, tool version, aggregate results, and file digests preserve reproducibility after artifact expiry.

## Disposition and next boundary

This receipt authorizes no cleanup execution. It is non-authoritative evidence that may inform later repository-maintenance review and any separately approved work.

If separately authorized, later repository-maintenance work could:

1. classify scripts and workflow entry points by reviewed responsibility;
2. audit modules across default, opt-in, operator, offline, dynamic, subprocess, test, evidence, and roadmap roots;
3. identify bounded candidate waves.

Any deletion, move, rename, consolidation, compatibility removal, storage migration, runtime change, implementation-debt closure, or roadmap change still requires its own owning authority, atomic PR, and explicit approval.

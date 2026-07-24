---
relaylm_doc_type: system_architecture
relaylm_authority: repository_maintenance_discovery_classification_projection_and_cleanup_flow
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: repository_maintenance
relaylm_update_trigger:
  - repository asset responsibility or lifecycle classification changes
  - generated inventory or navigation ownership changes
  - validation consolidation or package-migration sequencing changes
  - cleanup evidence, compatibility, rollback, or removal-gate policy changes
relaylm_not_authoritative_for:
  - current repository implementation completion
  - exact per-asset classification rows
  - runtime, storage, schema, or API behavior
  - authorization to delete, move, rename, or consolidate an unreviewed asset
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0006-repository-structure-and-maintenance-sequencing.md
relaylm_related_authority:
  - ../planning/repository-structure-migration.md
  - ../reference/repository-asset-classification.md
  - documentation-governance.md
  - ../operations/documentation-synthesis-and-retirement.md
relaylm_lifecycle: accepted_target
relaylm_primary_consumers:
  - repository maintainers
  - migration reviewers
  - AI coding agents
relaylm_authority_level: system
---
# Repository Maintenance System

## Purpose

This page defines the durable repository-maintenance architecture that turns mechanical discovery into reviewed classification, generated projections, bounded consolidation, and evidence-gated cleanup. It does not contain the exact asset registry or authorize a specific move or deletion. Exact reviewed rows remain in the [Repository Asset Classification Reference](../reference/repository-asset-classification.md), while execution order remains in the [Repository Structure and Documentation Canonicalization Plan](../planning/repository-structure-migration.md).

## System context

RelayLM contains runtime modules, optional components, operator CLIs, offline tools, generators, migration helpers, benchmarks, tests, process smoke, workflows, validators, and historical implementation-oriented names. Static import reachability or file count cannot distinguish those responsibilities.

Repository maintenance therefore uses this dependency direction:

```text
mechanical discovery
  -> reviewed responsibility and lifecycle classification
  -> deterministic current projections
  -> bounded equivalence or migration evidence
  -> one atomic cleanup or move
  -> negative-reference and entry-point verification
  -> Git-recoverable retirement
```

Discovery is evidence. Classification is reviewed authority. Generated projections are navigation. Cleanup requires a separate atomic decision.

## Responsibility map

| Responsibility | Owner | Boundary |
|---|---|---|
| discover files, imports, invocations, config, storage, and workflow roots | repository tooling | mechanical evidence only |
| assign supported responsibility and lifecycle | repository maintenance | reviewed classification authority |
| expose deterministic inventories and navigation | generators | projection only; no deletion authority |
| preserve runtime and operator entry points during moves | owning subsystem plus repository maintenance | atomic migration boundary |
| consolidate tests, smoke, workflows, and validators | responsibility owner | equivalence and removal-gate review |
| retire unsupported assets | repository maintenance | exact caller, rollback, replacement, and Git-recovery proof |
| synthesize and retire documentation | documentation | separate Lane D authority |
| change runtime, storage, lifecycle, or Retrieval semantics | Lane C owners | outside repository-maintenance authority |

## Asset state model

Every governed asset has one operational state:

```text
active
  supported current runtime, operator, test, process, recovery, generator,
  migration, or repository-governance responsibility

transitional
  current characterization, compatibility, rollback, or migration responsibility
  with an owner, consumer, removal gate, and replacement validation

retired
  no supported caller, protected boundary, migration, rollback,
  characterization, or repository-governance responsibility remains
```

`retired` is a reviewed conclusion, not a discovery result. An unreferenced asset, low fan-in, milestone-oriented name, or absence from the default FastAPI graph is only a triage signal.

## Canonical flow

### 1. Discovery

Enumerate direct and indirect roots, including:

- public imports and package data;
- FastAPI and frontend routes;
- console scripts and `python -m` entry points;
- operator commands and subprocess children;
- dynamic imports and registries;
- tests and process smoke;
- GitHub Actions and build scripts;
- migration, recovery, benchmark, and offline-tooling entry points;
- current documentation and roadmap consumers.

The output must be deterministic and content-bounded. Discovery does not infer semantic ownership.

### 2. Reviewed classification

Assign one supported responsibility, lifecycle, owner, and protected boundary. Transitional assets additionally identify current consumers, removal gate, and replacement validation. Contradictory duplicate claims fail closed rather than being merged by precedence.

### 3. Projection

Generate human-readable inventories and indexes from reviewed authority. Generated files are navigation only and must be reproducible from their source registry. Direct edits to generated output are rejected.

### 4. Consolidation or migration

Choose one responsibility-oriented canonical entry point before changing callers. Preserve console scripts, module execution, dynamic dispatch, subprocess roots, workflows, tests, and operator invocations in the same atomic PR. A wrapper is retained only when it owns a real public or operator compatibility boundary with an explicit removal gate.

### 5. Retirement

Delete an asset only after all supported responsibilities have a replacement or explicit reviewed disposition. Repair references and registries atomically. Keep no general executable archive, fallback import, duplicate wrapper, or second live namespace. Git history is the recovery surface.

## Validation architecture

Validation is separated by responsibility:

```text
maintained test suites
  pure unit, parser, schema, renderer, component, and ordinary integration regression

process smoke
  crash, restart, subprocess, filesystem, platform, security, concurrency,
  CLI, and operator-path behavior

repository validators
  classification integrity, generated drift, documentation governance,
  retirement, current records, path references, and entry-point ownership
```

A migration may use characterization while its removal gate remains open. Characterization does not become a permanent second implementation authority.

## Failure and recovery boundary

The system fails closed on:

- unknown or conflicting responsibility claims;
- missing owner, consumer, removal gate, or replacement validation for a transitional asset;
- generated-output drift or hand-edited projection;
- a caller, workflow, registry, or operator entry point left on an old path;
- a wrapper or fallback that hides disagreement between two implementations;
- a proposed deletion supported only by static reachability;
- a package move that crosses an unresolved LC-1 or RT-1 authority gate;
- a change that mixes semantic migration with broad physical reorganization.

Before merge, recovery is branch abandonment or revert. After retirement, the old blob remains recoverable through Git. Reintroducing it as current behavior requires a new reviewed authority decision.

## Parallel-safety boundary

Repository maintenance may proceed beside Lane C and Lane D only when paths, semantic authority, callers, generated registries, status ownership, and canonical entry points are disjoint. Another lane's stalled CI or free capacity does not transfer ownership.

Lane R must not:

- change Subjective MEM lifecycle or ordinary Retrieval authority before the owning Lane C gates close;
- edit documentation semantic authority owned by Lane D merely to simplify a generator;
- treat inventory evidence as authorization to close implementation debt;
- move Primary MEM merely because its present layout is inconvenient.

## Stable invariants

- one reviewed responsibility owner per governed asset;
- one lifecycle state per asset;
- one canonical entry point per supported responsibility;
- generated projections are deterministic and non-authoritative;
- compatibility is bounded by owner, consumer, removal gate, and replacement validation;
- no permanent fallback, duplicate wrapper, dual import authority, or general archive;
- every move and retirement is atomic, caller-complete, and Git-recoverable;
- semantic authority changes remain with the owning implementation or documentation lane.

## Non-goals

This architecture does not:

- prescribe a target file-count or workflow-count reduction;
- require every process validation or operator command to become pytest;
- authorize a whole-repository package rewrite;
- define exact current classification rows;
- declare milestone-oriented assets obsolete without caller and responsibility evidence;
- move Subjective MEM, Retrieval, or Primary MEM ahead of accepted authority gates.

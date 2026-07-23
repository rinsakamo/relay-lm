---
relaylm_doc_type: proposal
relaylm_authority: historical_repository_simplification_proposal
relaylm_status: historical
relaylm_proposal_status: accepted
relaylm_decision_source: ../adr/0006-repository-structure-and-maintenance-sequencing.md
relaylm_decided_on: 2026-07-24
relaylm_volatility: low
relaylm_owner: repository_maintenance
relaylm_update_trigger:
  - the accepted decision source is superseded
  - this historical proposal is removed from the current tree by an accepted retirement batch
relaylm_not_authoritative_for:
  - current runtime behavior
  - current implementation status
  - roadmap or execution sequencing
  - deletion, movement, rename, consolidation, or compatibility removal
  - storage migration or persistent-write enablement
  - default-on feature graduation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - ../architecture/project_execution_plan.md
  - ../planning/repository-structure-migration.md
  - ../planning/workstream-orchestration.md
  - ../adr/0006-repository-structure-and-maintenance-sequencing.md
  - ../evidence/implementation/repository_inventory_baseline_1ca928cd.md
---
# Historical proposal: Evidence-gated repository simplification

## Disposition

This proposal was accepted on 2026-07-24 through [ADR 0006](../adr/0006-repository-structure-and-maintenance-sequencing.md).

The accepted decision is narrower and more operationally specific than this proposal alone:

- new permanent milestone-oriented asset names stop immediately;
- active code, tests, smoke, tools, and documents use intent- and responsibility-oriented names through their owning atomic migrations;
- the already-open Cutover 1C-57 is the last source-by-source documentation cutover slice;
- active documentation is rebuilt by canonical target domain at stable responsibility-level granularity;
- consumed source, completion, evaluation, migration, release, proposal, and wave documents are removed from the current tree and retained through Git history;
- only narrowly typed current records remain under a separately governed record boundary;
- retired executable assets are deleted rather than moved into a general archive tree;
- transitional characterization, compatibility, rollback, and migration assets remain active only with explicit owners and removal gates;
- LC-1B through LC-1E and RT-1 remain the memory-authority critical path;
- script and code classification, bounded smoke consolidation, generated-index preparation, stable-domain documentation synthesis, and low-risk path-disjoint package moves may proceed in parallel;
- Subjective MEM, ordinary Retrieval, and Primary MEM namespace movement waits until RT-1;
- Primary MEM is evaluated for retirement before any final package move;
- `次に進めて` and equivalent shorthand execute the documented critical and parallel workstream portfolio rather than returning only a recommendation.

Current sequencing is owned by the [Project Execution Plan](../architecture/project_execution_plan.md), the subordinate [Repository Structure and Documentation Canonicalization Plan](../planning/repository-structure-migration.md), and [Workstream Orchestration and Continuation Command](../planning/workstream-orchestration.md). This file is retained temporarily as historical proposal context and does not authorize execution. It is expected to be removed from the current tree by a later reviewed historical-retirement batch after the accepted authorities are established on `main`.

The pre-decision full proposal remains recoverable from Git history and the fixed [Repository Inventory Baseline Receipt](../evidence/implementation/repository_inventory_baseline_1ca928cd.md) preserves the evidence boundary used during review.

## Accepted problem statement

RelayLM contains default runtime modules, opt-in components, operator CLIs, offline tools, generators, migration helpers, benchmarks, regression scripts, workflow entry points, evidence validators, and historical phase-oriented names. File counts and static import reachability do not distinguish those responsibilities.

The accepted program addresses:

- flat top-level modules whose prefixes act as informal packages;
- permanent module and architecture names that encode temporary implementation slices;
- mixed-purpose scripts and duplicated smoke entry points;
- hand-maintained documentation indexes that become stale;
- active documentation with inconsistent granularity and mixed authority;
- an open-ended documentation hard-cutover process whose bespoke guard and bookkeeping cost grows with every moved file;
- the risk that a permanent frozen tree would recreate a second ambiguous repository surface;
- repeated user orchestration burden when the next critical and parallel work is already determined by repository authorities.

## Accepted principles

### Classification before cleanup

Assets are classified by supported responsibility and lifecycle state before they become cleanup candidates. An unreferenced or low-fan-in inventory result is a triage signal only, not deletion authority.

Relevant responsibility classes include:

```text
default_runtime
opt_in_runtime
operator_cli
offline_tooling
generator
migration_or_maintenance
benchmark
subprocess_helper
regression_validation
acceptance_or_repository_validation
planned_inactive
unclassified
```

Lifecycle states are:

```text
active
transitional
retired
```

`retired` is a reviewed conclusion, not an initial class.

### Invocation roots before reachability conclusions

Review includes FastAPI paths, console scripts, supported operator commands, `python -m` entry points, workflows, subprocess children, dynamic dispatch, migration and maintenance tools, benchmarks, tests, repository validators, and current documentation.

Absence from the default application import graph is not dead-code evidence. The O3 scheduler path remains the concrete protected example.

### Roadmap authority before cleanup conclusions

Registered implementation debt and accepted near-term work remain dependencies until their owning authority replaces or removes them. Repository inventory cannot silently close PM-D1, PM-D2, PM-D4, PM-D9, LC-1, RT-1, or another registered boundary.

### Responsibility before count reduction

The goal is clearer ownership, fewer duplicated mechanisms, reliable entry points, understandable subsystem boundaries, stable authority, and a current tree containing only active assets and necessary records—not an arbitrary target file, workflow, or line count.

### Current contracts before internal neatness

A move, retirement, or consolidation cannot weaken runtime, evidence, lifecycle, storage, recovery, disclosure, operator, or validation contracts. Existing awkward or milestone-oriented names are migration debt, not proof that the underlying asset is obsolete.

### Canonical target before source retirement

Documentation work starts by defining the final active authority and granularity. Legacy files are source material, not automatic active survivors. Stable architecture and exact contracts are reconstructed first; consumed source and historical documents are then deleted from the current tree and recovered through Git history.

Code, tests, smoke, and tooling follow the same rule: active assets move to function-oriented names, transitional assets retain explicit removal gates, and retired assets are deleted rather than placed in a general executable archive.

### Git history before duplicate archives

Git already preserves prior paths, blobs, commits, tags, and pull-request history. The current tree does not duplicate every retired document or code asset into a second archive.

A small generated retirement manifest records the old path, last-live commit, blob identity, removing PR, replacement paths, and disposition. The manifest is recovery navigation only.

### Current records remain narrowly typed

Only records with a continuing release, stateful migration, audit, recovery, rollback, or repository-governance role remain in the current tree. Completed handoffs, superseded design sources, old planning documents, ordinary completion narratives, and obsolete cutover receipts do not become permanent records by default.

### Evidence before destructive authorization

Every deletion, move, rename, namespace cutover, compatibility removal, documentation retirement batch, or workflow consolidation requires its own bounded scope, caller or source evidence, validation matrix, rollback boundary, Git-recoverability check, and explicit review.

## Accepted validation taxonomy

The proposal rejected converting every script to pytest. The adopted taxonomy is:

| Responsibility | Default treatment |
|---|---|
| pure unit, component, schema, parser, renderer regression | prefer pytest or a maintained test suite |
| ordinary API or integration regression | prefer a maintained integration suite |
| crash, restart, subprocess, filesystem, platform validation | retain explicit process-level smoke |
| security or concurrency validation | retain explicit environment and isolation |
| migration or old/new characterization | retain while the removal gate remains open |
| operator CLI | keep outside test inventory |
| migration, maintenance, generator | keep as tooling with direct tests while current |
| benchmark | keep outside pass/fail regression gates |
| repository or current-record validator | retain while its governed boundary exists |
| proven duplicate or retired asset | delete after replacement equivalence and recovery evidence are reviewed |

Workflow consolidation follows responsibility, not an arbitrary workflow-count target.

## Execution boundary

Acceptance authorizes:

- responsibility and lifecycle classification;
- invocation-root analysis;
- canonical active-graph and retained-record planning;
- domain synthesis, historical-retirement, and generated-index planning;
- preparation of bounded candidate waves;
- proposal of separate atomic implementation and documentation PRs;
- the sequencing, naming, retention, and orchestration constraints recorded in ADR 0006.

Acceptance does not authorize:

- an immediate whole-repository reorganization;
- deletion or migration of user-owned durable state;
- storage authority changes;
- default-on behavior;
- permanent aliases, redirects, fallback imports, dual-read, or dual-write;
- closure of unrelated implementation debt;
- moving Subjective MEM, Retrieval, or Primary MEM ahead of RT-1;
- deleting a source document whose still-live normative content lacks an active replacement or reviewed disposition;
- moving retired assets into an ungoverned archive tree;
- merging a candidate wave without separate exact-scope review;
- hidden background or asynchronous execution.

## Historical alternatives rejected

- deleting everything outside the default application graph;
- converting every script to pytest;
- preserving compatibility during every refactor;
- rewriting the repository from scratch;
- leaving the repository unchanged;
- retaining the current inconsistent active-document set and removing only obvious evidence;
- continuing one-source-document cutover until every historical file is normalized;
- preserving every retired document or executable asset in a permanent frozen tree;
- requiring the user to select the next workstream after every PR when repository authorities already resolve priority.

## Current authority

Read these documents instead of treating this historical proposal as current authority:

1. [Project Status](../PROJECT_STATUS.md) for current implementation state;
2. [Project Execution Plan](../architecture/project_execution_plan.md) for repository-wide sequencing;
3. [ADR 0006](../adr/0006-repository-structure-and-maintenance-sequencing.md) for the accepted decision;
4. [Repository Structure and Documentation Canonicalization Plan](../planning/repository-structure-migration.md) for detailed execution order;
5. [Workstream Orchestration and Continuation Command](../planning/workstream-orchestration.md) for shorthand-command and parallel-lane behavior;
6. [Repository Inventory Baseline Receipt](../evidence/implementation/repository_inventory_baseline_1ca928cd.md) for fixed non-authoritative inventory evidence.

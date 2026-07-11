---
relaylm_doc_type: proposal
relaylm_authority: proposal_for_staged_repository_simplification
relaylm_status: target
relaylm_proposal_status: under_review
relaylm_volatility: medium
relaylm_owner: repository_maintenance
relaylm_update_trigger:
  - proposal is accepted, rejected, withdrawn, or materially revised
  - documentation hard cutover completes
  - reproducible repository baseline is published
  - dogfood evidence changes default-path priorities
relaylm_not_authoritative_for:
  - current runtime behavior
  - permission to delete modules, scripts, workflows, or documentation
  - approval of a SQLite migration
  - approval of repository-wide Pydantic conversion
  - implementation completion
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# Proposal: Staged repository simplification

This is an undecided proposal for reducing RelayLM's maintenance surface without deleting current default, opt-in, operator, tooling, or evidence paths by mistake.

## Status

Under review.

Acceptance of this proposal would authorize bounded audits and follow-up planning. It would not authorize destructive changes, a storage migration, or default-on behavior by itself.

## Problem

RelayLM accumulated many runtime modules, operator and offline scripts, regression and acceptance checks, workflows, and historical documents during phase- and wave-driven MVP development. Some are durable product capabilities; others may be duplicated validation, completed-phase scaffolding, inactive implementation inventory, or historical evidence.

The initial zero-base review identified a real maintenance problem, but several classifications were too broad for deletion decisions:

- Python files under `scripts/` are not all smoke tests;
- static imports from the FastAPI application do not represent every supported invocation path;
- operator CLIs, console entry points, workflows, subprocess helpers, migration tools, generators, and benchmarks need separate treatment;
- file and line counts do not independently prove that a design is simpler or safer.

A concrete false positive was `relaymem_slp_supervised_scheduler_service.py`. It participates in the documented O3 operator path through `scripts/relaylm_o3_always_on_local_scheduler.py`; it is not smoke-only or dead inventory.

## Goals

- publish a commit-fixed, reproducible repository complexity baseline;
- classify scripts and modules by responsibility and invocation path;
- consolidate ordinary regression coverage where pytest improves reuse and coverage visibility;
- retain specialized crash, restart, subprocess, security, concurrency, migration, benchmark, and operator surfaces when their responsibilities differ;
- remove genuinely dead or duplicated assets only after callers, documentation, tests, and accepted plans are checked;
- organize runtime code by durable subsystem rather than phase identifiers;
- evaluate SQLite and serialization changes through bounded evidence;
- choose default-path graduation from dogfood and compatibility evidence.

## Non-goals

- setting a target number of files, scripts, workflows, modules, or lines of code;
- treating every file under `scripts/` as a test;
- deleting modules based only on static imports from `app.py`;
- replacing JSON and JSONL state with SQLite in one migration;
- converting every dataclass or dictionary to Pydantic;
- creating `docs/archive/` or superseding the accepted documentation hard-cutover design;
- enabling history exclusion or another feature by default without request-shape and negative-path evidence;
- changing runtime behavior in this PR.

## Governing principles

### Classification before deletion

Default runtime, opt-in runtime, operator CLI, offline tooling, test or evidence, planned inactive, and dead-code candidates are distinct categories.

### Responsibility before count reduction

Success means clearer ownership, fewer duplicated mechanisms, reliable entry points, and understandable subsystem boundaries. A lower file count is not a standalone objective.

### Evidence before architecture decisions

A reproducible audit belongs in `docs/evidence/`. SQLite adoption, broad persistence migration, and default-on deployment each require a separate decision.

### Preserve file-first product sources

Editable character sources and approved Markdown workspace files remain part of RelayLM's product model. A later runtime-state experiment must not silently absorb them.

## Proposed staged program

| Stage | Proposed disposition | Boundary |
|---|---|---|
| 0. Finish documentation hard cutover | continue existing decision | ADR 0002 remains governing authority |
| 1. Reproducible repository baseline | accept candidate | measurement only |
| 2. Script and test classification | accept candidate | bounded consolidation only |
| 3. Invocation-root module audit | accept candidate | deletion requires explicit evidence |
| 4. Subpackage and naming cleanup | accept in principle | plan per subsystem after Stage 3 |
| 5. SQLite runtime-state spike | defer to experiment | no migration approval here |
| 6. Serialization boundary cleanup | defer to classification | no repository-wide Pydantic mandate |
| 7. Default-path graduation | defer to dogfood evidence | separate deployment decision per feature |

## Stage 0: complete the documentation hard cutover

Continue the accepted authority-first hard cutover before starting another repository-wide documentation structure change.

The governing model remains:

- current authority in canonical collections;
- meaningful historical results in `docs/evidence/`;
- low-value historical material recoverable from Git history only;
- no redirect stubs or dual live paths;
- no parallel `docs/archive/` authority tree.

Recount documentation and workflows after the cutover rather than preserving pre-cutover totals as a baseline.

## Stage 1: publish a reproducible baseline

Create a commit-fixed audit such as:

```text
docs/evidence/audits/repository-complexity-baseline.md
```

The audit must record:

- source commit SHA;
- exact commands or checked-in analyzer versions;
- inclusion and exclusion rules;
- invocation-root definitions;
- category definitions;
- known false-positive and false-negative limits;
- generated artifact digests;
- counts separated by responsibility.

At minimum, classify scripts as:

```text
regression smoke
pytest test
operator CLI
migration or maintenance tooling
generator
benchmark
subprocess helper
historical or evidence validation
unclassified
```

An unreferenced result remains a triage signal, not proof that a script is safe to delete.

### Stage 1 completion criteria

- the inventory can be regenerated from the recorded commit;
- every total has a documented inclusion rule;
- operator and offline tools are separated from regression checks;
- limitations are explicit;
- the audit itself authorizes no deletion.

## Stage 2: classify and consolidate scripts and tests

Choose the validation surface by responsibility rather than mechanically converting every script to pytest.

| Script class | Proposed treatment |
|---|---|
| pure unit or component regression | migrate to pytest |
| ordinary API or integration regression | migrate to a pytest integration suite |
| crash, restart, or subprocess validation | retain a dedicated runner or invoke it from pytest |
| security or concurrency validation | retain an isolated suite with explicit environment needs |
| operator CLI | keep outside the test inventory |
| migration, maintenance, or generator tooling | keep as tooling with direct tests |
| benchmark | separate from pass/fail regression suites |
| completed-phase duplicate | delete only after equivalent current coverage is demonstrated |

The generated inventory should include fields equivalent to:

```text
category
owner
entrypoint
covered boundary
current caller
replacement test, if any
retention or removal decision
```

Workflow consolidation should follow stable validation responsibility. This proposal sets no arbitrary workflow-count target.

### Stage 2 completion criteria

- no retained script is unclassified;
- every retained script has an owner and invocation mode;
- ordinary regressions have a documented primary command;
- duplicated fixtures and assertion helpers are reduced;
- removed scripts have a replacement test or an explicit obsolete-boundary justification.

## Stage 3: audit module invocation paths

A deletion audit must include more roots than the default application import graph.

Required roots include:

- FastAPI startup and request paths;
- console scripts declared in `pyproject.toml`;
- supported operator CLIs under `scripts/`;
- `python -m` entry points;
- workflow and consolidated-registry commands;
- subprocess child modules;
- registry-mediated calls;
- offline migration and maintenance tools;
- test- and evidence-only imports.

Classify each module as:

```text
A. default runtime
B. opt-in runtime
C. operator CLI
D. offline tooling
E. test or evidence only
F. planned but inactive
G. dead-code candidate
```

Each record should include:

```text
module
category
direct or indirect caller
documented use
test coverage
owner
planned integration, retention, or removal
```

### Deletion gate

A module may be removed only when all of the following are established:

- it has no default, opt-in, operator, tooling, or supported subprocess caller;
- current documentation does not describe it as an available path;
- no retained test needs it to verify a current invariant;
- it is absent from accepted near-term plans;
- historical value is retained in evidence or Git history;
- relevant regression, compile, documentation, and operator-path checks pass after removal.

### Stage 3 completion criteria

- the O3 scheduler false positive cannot recur;
- every runtime module has a category and owner;
- dead-code deletion can proceed in bounded reviewable waves;
- planned inactive code is distinct from dead code.

## Stage 4: reorganize by durable subsystem

After Stage 3, prepare subsystem-specific plans. The first objective is understandable ownership, not immediate file merging.

A possible target shape is:

```text
relaylm/
  api/
  pipeline/
  character_workspace/
  memory/
    retrieval/
    primary/
    lifecycle/
  scheduler/
  context/
  persona/
  diagnostics/
  operations/
```

Rules:

- new module names describe durable functions rather than phase or wave IDs;
- move one subsystem at a time;
- separate broad path moves from behavior changes and large file mergers;
- freeze public entry points and serialized artifacts with tests first;
- avoid permanent compatibility-import layers unless separately justified;
- check import cycles and startup behavior after each move.

Suggested initial order is diagnostics, scheduler, memory lifecycle, context, persona stages, and request pipeline. Stage 3 evidence may change that order.

## Stage 5: run a bounded SQLite spike

This proposal does not approve replacing all JSON or JSONL state with SQLite.

Test one bounded internal runtime-state area, preferably scheduler queue and claim state. Compare:

- crash consistency;
- multi-process safety;
- idempotency;
- replay and retention semantics;
- migration and rollback complexity;
- observability and inspectability;
- backup and restore behavior;
- Windows and WSL behavior;
- implementation and test complexity;
- measured latency and contention.

SQLite may replace some locking and atomic-update mechanisms, but it does not automatically remove domain semantics such as replay eligibility, publication boundaries, fence meaning, or protected-source separation.

Adoption requires a separate proposal or ADR supported by a recorded evaluation. Character workspace Markdown remains out of scope.

## Stage 6: clean up serialization at boundaries

A Pydantic dependency does not imply that every internal value should be a Pydantic model.

| Boundary | Default approach |
|---|---|
| configuration | Pydantic |
| API request and response | Pydantic where appropriate |
| persisted versioned artifacts | Pydantic or another explicit versioned schema |
| external or untrusted input | validated schema |
| internal immutable values | dataclass remains acceptable |
| transient hot-path projection | evaluate case by case |

First classify hand-written serialization methods as validation and serialization, serialization only, logging projection, internal value, or compatibility schema. Consolidate only proven duplication or drift.

The current `asyncio.to_thread` compiler handoff already returns captured worker-context blocks and restores them in the awaiting request context. It is not an unresolved propagation bug. A later refactor must preserve the current offload and request-isolation behavior.

## Stage 7: graduate default-path behavior from dogfood evidence

Do not preselect history exclusion as the next default-on feature solely because it is gated.

Prioritize evidence from:

- regular single-user mobile dogfood;
- real conversation memory usefulness;
- persona stability;
- perceived and measured latency;
- practical file-first workspace editing;
- false recall, incorrect mutation, and history-handling failures.

Each default-on proposal must define supported request shapes, negative-path and compatibility tests, rollback behavior, dogfood value, documentation and config updates, and a separate deployment decision.

History exclusion remains governed by its existing decision debt until reconstruction and relevant tool-chain boundaries are safe for the intended request shapes.

## Proposed implementation sequence

```text
A. complete the current documentation hard cutover
B. add reproducible baseline tooling and evidence
C. extend scripts inventory with responsibility classification
D. consolidate one bounded ordinary-regression family into pytest
E. run the invocation-root module audit
F. remove one bounded dead-code or duplicate-validation wave
G. plan and move one low-risk subsystem namespace
H. run the bounded SQLite spike
I. classify serialization boundaries and remove proven duplication
J. propose default-path graduation from dogfood evidence
```

Stages B through F must produce evidence used to revise Stages G through J.

## Alternatives

### Rewrite the default path from scratch

Potentially smaller, but likely to discard validated crash, isolation, lifecycle, and operator semantics. Reject as the initial approach.

### Delete everything absent from the FastAPI import graph

Incorrectly treats opt-in services, operator CLIs, offline tooling, and subprocess paths as dead. Reject.

### Convert every script to pytest

A poor fit for operator commands, migration tools, benchmarks, and some process-level validation. Reject as a blanket rule.

### Move all internal state to SQLite immediately

Commits to migration before measuring invariant coverage, platform behavior, and rollback cost. Defer to Stage 5.

### Keep the repository unchanged

Leaves duplicated validation, phase-oriented naming, and unclear ownership in place. Reject.

## Risks and mitigations

- **Inventory becomes permanent bureaucracy.** Keep row-level outputs generated and commit-fixed; retain only reviewed summaries and decisions.
- **Deletion removes an operational path.** Require invocation roots, documented-use checks, and operator validation.
- **pytest migration weakens process-level coverage.** Preserve dedicated subprocess and crash suites.
- **Namespace moves produce noisy diffs.** Move one subsystem at a time and separate relocation from behavior changes.
- **SQLite is assumed to remove domain logic.** Compare invariant by invariant and require a separate decision.
- **Pydantic increases coupling or hot-path cost.** Apply it at trust and persistence boundaries only where justified.
- **Cleanup delays dogfooding.** Keep mobile dogfood and value evaluation as parallel product priorities.

## Adoption boundary

Acceptance would authorize:

- a reproducible baseline audit;
- responsibility-based script classification;
- an invocation-root module audit;
- bounded test consolidation and evidence-backed deletion waves;
- subsystem-specific namespace plans.

Acceptance would not authorize:

- deletion based on the initial zero-base counts;
- a full SQLite migration;
- repository-wide Pydantic conversion;
- a parallel documentation archive;
- default-on graduation of a specific feature;
- a whole-repository rewrite.

## Validation

Before acceptance:

- documentation metadata, placement, links, and semantic checks pass;
- the O3 scheduler module is not described as smoke-only or dead;
- aggregate script language distinguishes Python scripts from smoke tests;
- exact baseline counts are deferred to reproducible evidence;
- documentation treatment remains consistent with ADR 0002;
- the ContextVar handoff is described as current implemented behavior;
- no runtime file or behavior changes in this PR.

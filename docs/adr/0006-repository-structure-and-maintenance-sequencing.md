---
relaylm_doc_type: adr
relaylm_authority: repository_structure_documentation_canonicalization_and_workstream_orchestration
relaylm_status: target
relaylm_decision_status: accepted
relaylm_decided_on: 2026-07-24
relaylm_volatility: low
relaylm_owner: repository_maintenance
relaylm_update_trigger:
  - this decision is superseded
  - the LC-1 or RT-1 dependency boundary materially changes
  - the active-document, retained-record, or historical-retirement boundary changes
  - the continuation-command, PR-lifecycle, or concurrency policy changes
  - a public import, CLI, compatibility, or repository-retention policy is accepted
relaylm_not_authoritative_for:
  - current implementation status
  - exact runtime, storage, schema, or API behavior
  - authorization to execute an unreviewed cleanup, retirement batch, or namespace migration
  - deletion of user-owned durable state
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - ../architecture/project_execution_plan.md
  - ../architecture/documentation-governance.md
  - ../architecture/repository-maintenance-system.md
  - ../operations/documentation-synthesis-and-retirement.md
  - ../planning/repository-structure-migration.md
  - ../planning/workstream-orchestration.md
  - ../evidence/implementation/repository_inventory_baseline_1ca928cd.md
relaylm_supersedes: []
relaylm_superseded_by: null
---
# ADR 0006: Repository structure, documentation canonicalization, and workstream orchestration

## Decision summary

RelayLM adopts an evidence-gated repository-simplification program and a staged migration from prefix-oriented flat modules toward intent-oriented domain packages.

The migration remains ordered around the in-progress memory authority program:

```text
LC-1B Forget
  -> LC-1C Pin / Unpin
  -> LC-1D Restore
  -> LC-1E Consolidate
  -> RT-1 Retrieval projection and one-authority hard cutover
```

LC-1A Correct and Documentation Hard Cutover 1C-57 are complete. Core Subjective MEM, ordinary Retrieval, and Primary MEM namespace migration remains blocked until RT-1 establishes one authority.

RelayLM also replaces the one-source-document Documentation Hard Cutover with canonical target-domain reconstruction and Git-history retirement. Active documents are rebuilt at stable responsibility-level granularity. After still-live architecture and normative content has an accepted replacement or reviewed disposition, superseded documents are deleted from the current tree and remain recoverable through Git.

The current tree retains only:

```text
docs/       current authority, current guidance, and current navigation
records/    narrowly typed records with a continuing current function
```

`records/` is not a historical-document archive. One small generated retirement manifest records how deleted paths can be recovered from Git and which current authorities replaced them.

Repository code, tests, smoke, workflows, and tooling use the same active/transitional/retired model. Active assets move toward function-oriented names, transitional assets retain explicit removal gates, and retired assets are deleted rather than moved into a general executable archive.

The user shorthand `次に進めて`, `進めて`, `続けて`, or `次へ` is accepted as a portfolio execution command. ChatGPT must converge existing PRs through a universal P0-P8 lifecycle, advance the earliest executable critical item, and advance eligible path- and authority-disjoint parallel work.

This ADR authorizes planning and bounded atomic PRs only. It does not authorize a whole-repository rename, unreviewed deletion wave, default-on behavior, storage migration, user-data migration, or hidden background execution.

## Context

RelayLM has accumulated:

- flat top-level Python modules whose prefixes act as informal packages;
- milestone and slice identifiers in permanent module and architecture names;
- a mixed-purpose `scripts/` surface;
- duplicated smoke and wrapper entry points;
- hand-maintained documentation indexes;
- active documents with inconsistent granularity;
- implementation handoffs, evidence, architecture, contracts, and planning mixed under the same directories;
- a per-document cutover process whose bespoke guard and bookkeeping cost grows with every moved file.

The correct target is responsibility-based synthesis: stable architecture is reconstructed by domain, exact normative material is rebuilt as contracts, current status remains separate, and retired sources leave the current tree.

A permanent frozen copy of every retired document or executable asset would create a second searchable repository surface. Git already preserves prior blobs, paths, commits, tags, and pull-request history. The current tree should not duplicate that archive without a continuing operational reason.

At the same time, the memory and Retrieval implementation remains authority-sensitive. Broad namespace cleanup before RT-1 would mix semantic migration with physical movement and make review and rollback harder.

## Decisions

### 1. Permanent active assets use intent-oriented names

New permanent runtime modules, active architecture, exact contracts, maintained tests, process smoke, public or operator CLI entry points, and workflow-owned commands must not use implementation milestone IDs such as `phase*`, `wave*`, `mvp*`, `i4c2`, or equivalent slice names as their primary identity.

Milestone and slice IDs remain valid in:

- pull requests and branch names;
- temporary construction artifacts removed before merge;
- necessary provenance in current records and retirement manifests;
- Git history.

Active names describe function and responsibility:

```text
runtime code             domain + supported function
ordinary test            function + regression boundary
process smoke            function + process or failure boundary
operator tool            supported operator action
repository validator     invariant being checked
```

Existing milestone-oriented paths are renamed, synthesized, or removed only through their owning atomic migration. There is no global cosmetic rename.

### 2. Domain packaging waits for authority stability

The target Python layout is domain-oriented. Representative domains include:

```text
relaylm/
  evidence/
  context/overlay/
  assessment/
  memory/subjective/
  memory/primary/
  retrieval/
  character/workspace/
  scheduler/
  clients/
  tokens/
  diagnostics/
  interfaces/openai/
  interfaces/soul_lab/
  cli/
```

The exact tree is determined by caller and dependency evidence. This example does not authorize a whole-repository move.

Subjective MEM, Retrieval, and Primary MEM move only after RT-1. Primary MEM is handled last so obsolete assets can be retired instead of reorganized unnecessarily.

### 3. Code and validation assets use active, transitional, and retired states

```text
active
  current runtime, operator, contract, regression, process, recovery,
  or repository-governance responsibility

transitional
  characterization, compatibility, rollback, or migration responsibility
  required until an explicit removal gate closes

retired
  no supported caller, protected boundary, migration, rollback,
  characterization, or repository-governance responsibility
```

Transitional assets remain executable only when they identify:

```text
owner
protected boundary
current caller
removal gate
replacement validation
```

Retired code, smoke, wrappers, migrations, and tooling are deleted from the current tree and recovered through Git history. A general executable `frozen/`, `archive/`, or `legacy/` tree is prohibited.

An exceptional reproduction snapshot may remain only as a non-executable typed record outside packages and test discovery, with source commit and digest.

### 4. Active documentation is rebuilt by canonical domain

The existing active document set is not preserved merely because individual files contain useful material.

Documents share one permanent active page only when they have the same:

```text
owner
update trigger
lifecycle
primary consumers
authority level
```

A difference in any dimension is a reason to split. Shared milestone history or similar length is not a reason to combine.

Canonicalization proceeds by target domain:

```text
identify final authority and granularity
  -> enumerate source documents and code or contract anchors
  -> synthesize durable architecture
  -> rebuild exact normative content as contracts
  -> separate current implementation from accepted target
  -> repair current references and navigation
  -> delete consumed historical sources
  -> record recovery and replacement in one retirement manifest
```

Implementation slices such as LC-1A through LC-1E, Phase 6, M3, Wave, ACG, and CW do not remain separate permanent architecture pages merely because they were implemented separately.

### 5. Historical material is retired to Git by default

Retired documentation is deleted after replacement and omission checks pass. Git history is the historical store.

The generated retirement manifest records fields equivalent to:

```text
old_path
last_live_commit
old_blob_sha
removed_by_pr
replacement_paths
disposition
retention_reason
```

The manifest is navigation and provenance only. It does not reproduce retired prose or become architecture, status, or contract authority.

A source containing still-live architecture or normative content is not deleted until an active replacement or explicit reviewed absorption, supersession, or retirement decision exists.

No redirect stub, duplicate archived Markdown copy, or dual live path is created merely to preserve an old link. Current links are repaired atomically; historical retrieval uses Git.

### 6. Current records are narrowly allowlisted

Only records with a continuing current function remain. Representative classes are:

```text
release or tag validation receipt
irreversible or stateful migration receipt
security, privacy, or external audit record
current recovery or rollback checkpoint
retirement manifest
machine-readable current registry required by CI or operation
```

Completed handoffs, superseded designs, old roadmaps, historical proposals, ordinary completion narratives, and obsolete one-document cutover receipts do not qualify merely because they once provided evidence.

The record boundary must reject untyped free-form historical Markdown and remain much smaller than the active documentation tree.

### 7. Documentation work uses domain batches

Documentation Hard Cutover 1C-57 is the final source-by-source legacy slice. No Cutover 1C-N successor is opened.

Later work uses:

- one active-graph and retained-record lock;
- domain synthesis waves;
- bounded historical-retirement batches;
- one retirement-manifest update per batch;
- generic active-document, retained-record, normative-extraction, Git-recoverability, link, metadata, authority, and generated-index checks.

Bespoke per-document guards, self-tests, Markdown receipts, and active ledger bookkeeping are retired after their source family enters the generic boundary.

Memory lifecycle canonicalization waits for LC-1 completion. Retrieval and Primary MEM canonicalization waits for RT-1. Stable domains may proceed earlier in parallel.

### 8. Validation is separated by responsibility

```text
pytest or maintained test suites
  pure unit, component, schema, parser, renderer, and ordinary integration regression

process-level smoke
  crash, restart, subprocess, security, concurrency, filesystem,
  platform, CLI, and operator-path validation

repository validation tools
  documentation audits, inventory, generated-index drift checks,
  retirement boundaries, current-record registries, and governance checks
```

Migration tools, generators, benchmarks, operator commands, and process-isolation validation are not converted to pytest solely to reduce file count.

### 9. Mechanical navigation is generated

`docs/README.md` remains a short curated entry point. Long active architecture, ADR, contract, planning, reference, and operations lists are generated from canonical metadata and drift-checked.

Retained-record navigation is generated separately. Retired material is found through the retirement manifest and Git history, not a second documentation tree.

Generated indexes are navigation only and cannot become status, contract, architecture, or audit authority.

### 10. Work advances through three coordinated lanes

```text
Lane C: critical implementation
  LC-1B -> LC-1C -> LC-1D -> LC-1E -> RT-1

Lane D: documentation canonicalization and historical retirement
  active graph -> domain synthesis -> retirement -> authority-gated finalization

Lane R: repository maintenance
  classification -> consolidation -> generated navigation -> package migration
```

Default capacity is one Lane C PR, up to one Lane D PR, and up to one Lane R PR. Three PRs are a ceiling, not a target.

Path-disjointness alone is insufficient. Parallel work must also avoid shared semantic authority, callers, workflows, generated registries, status ownership, and canonical entry points.

Detailed sequencing is owned by [Repository Structure and Documentation Canonicalization Plan](../planning/repository-structure-migration.md).

### 11. Every PR follows one convergence lifecycle

```text
P0 scope and authority lock
  -> P1 normal implementation
  -> P2 baseline validation and reviewable PR
  -> P3 thorough review
  -> P4 correction and exact-head validation
  -> P5 fresh final-review loop until clean
  -> P6 merge gate
  -> P7 expected-head-protected merge
  -> P8 post-merge convergence
```

CI success does not replace thorough or final review. Known in-scope defects cannot be deferred to a later PR merely to declare the current PR complete.

Exact behavior is owned by [Workstream Orchestration, Continuation Command, and PR Convergence](../planning/workstream-orchestration.md).

### 12. Continuation shorthand executes the portfolio

A bare `次に進めて`, `進めて`, `続けて`, or `次へ` means:

1. refresh repository and PR state;
2. determine each active PR's P0-P8 stage;
3. converge existing work before opening overlapping replacements;
4. advance the earliest executable Lane C action;
5. use blockers to trigger safe Lane D or Lane R work;
6. advance at least one parallel lane when meaningful safe work exists;
7. avoid asking the user to choose when documented priority resolves the choice;
8. merge when P6 passes unless the user limited the turn to review-only;
9. report critical, parallel, and portfolio state.

This command does not authorize hidden background execution. All work is performed and reported in the current interaction.

### 13. Every move and retirement is atomic and evidence-gated

Each namespace, script family, documentation domain, retirement batch, or index-generation wave requires its own accepted scope and exact caller or source evidence.

A wave updates current imports, invocations, workflows, entry points, tests, links, manifests, and documentation in the same PR or an explicitly coordinated atomic set.

Permanent aliases, redirects, fallback imports, dual-read, and dual-write are prohibited by default. Any temporary compatibility surface requires an owner, current consumer, removal gate, and bounded exit condition.

## Consequences

- New milestone-oriented naming debt stops when this ADR merges.
- LC-1 and RT-1 remain reviewable and are not obscured by broad package movement.
- Active documentation converges toward consistent responsibility-level granularity.
- Retired documents and code disappear from ordinary current-tree search while remaining recoverable through Git.
- The repository avoids maintaining a second frozen source tree.
- One-file cutover bookkeeping stops growing after 1C-57.
- Stable documentation and low-risk maintenance can proceed in parallel with product work when authority ownership is disjoint.
- A bare continuation instruction becomes reproducible across threads.
- Primary MEM may be retired rather than reorganized.

## Rejected alternatives

### Reorganize all of `relaylm/` immediately

Rejected because LC-1 and RT-1 still change memory and Retrieval authority. Mixing semantic and physical migration would reduce reviewability and rollback clarity.

### Keep the current active documents and only remove obvious evidence

Rejected because the active set has inconsistent granularity and mixed authority.

### Continue one-source-document cutover until every file is normalized

Rejected because bespoke guard, self-test, receipt, ledger, and link-repair cost grows faster than the value of polishing historical sources.

### Copy every retired asset into a frozen tree

Rejected because a second searchable tree recreates ambiguity and maintenance cost already solved by Git history.

### Delete source documents before active replacement review

Rejected because some sources still contain live architecture or normative content.

### Convert every script to pytest

Rejected because process isolation, operator paths, migrations, generators, benchmarks, and repository audits have distinct responsibilities.

### Preserve every old import through compatibility wrappers

Rejected because indefinite wrappers create duplicate entry points and permanent removal debt.

### Ask the user to choose a lane after every PR

Rejected because the accepted plan already defines dependency and parallel priority when repository evidence resolves the choice.

## Implementation status

This ADR records an accepted target and execution constraint. It does not claim that D1, Lane R classification, historical retirement, generated navigation, or domain-package migration is complete.

Current completion remains owned by `docs/PROJECT_STATUS.md` and exact implementation evidence.

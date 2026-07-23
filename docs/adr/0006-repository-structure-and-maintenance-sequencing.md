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
  - the canonical active-document or retained-record boundary changes
  - the continuation-command or PR concurrency policy changes
  - a public import, CLI, compatibility, or repository-retention policy is accepted
relaylm_not_authoritative_for:
  - current implementation status
  - exact runtime, storage, schema, or API behavior
  - authorization to execute an unreviewed cleanup, documentation retirement batch, or namespace migration
  - deletion of user-owned durable state
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - ../architecture/project_execution_plan.md
  - ../planning/repository-structure-migration.md
  - ../planning/workstream-orchestration.md
  - ../proposals/repository-simplification.md
  - ../evidence/implementation/repository_inventory_baseline_1ca928cd.md
relaylm_supersedes: []
relaylm_superseded_by: null
---
# ADR 0006: Repository structure, documentation canonicalization, and workstream orchestration

## Decision summary

RelayLM adopts an evidence-gated repository-simplification program and a staged migration from prefix-oriented flat modules toward intent-oriented domain packages. The migration is ordered around the existing LC-1 lifecycle and RT-1 Retrieval authority cutover, not ahead of them.

RelayLM replaces the open-ended one-source-document Documentation Hard Cutover with canonical target-domain reconstruction. Active documents are rebuilt at stable responsibility-level granularity. After their still-live architecture and normative content has an accepted replacement or reviewed disposition, superseded source, implementation, evaluation, migration, proposal, release, and wave documents are removed from the current tree and remain recoverable through Git history.

The current tree retains only:

```text
docs/       current authority, current guidance, and current navigation
records/    narrowly typed records that still perform a current audit, release,
            migration, recovery, or repository-governance function
```

`records/` is not a historical-document archive. Free-form retired documents do not move there. A small generated retirement manifest records how deleted paths can be recovered from Git and which active authorities replaced them.

The user shorthand `次に進めて`, `進めて`, or `続けて` is accepted as a portfolio execution command. ChatGPT must converge existing work, advance the earliest executable critical-path item, and also advance eligible path- and authority-disjoint documentation or repository-maintenance work according to the accepted orchestration plan.

This decision also freezes new milestone-oriented names in permanent assets, separates ordinary tests from process-level smoke and repository validation tooling, keeps `docs/README.md` curated while generating mechanical indexes, and applies the same active-versus-retired principle to code and validation assets.

Acceptance of this ADR authorizes planning and bounded atomic PRs only. It does not authorize a whole-repository rename, unreviewed deletion wave, default-on behavior, storage migration, user-data migration, or background execution.

## Context

RelayLM has accumulated:

- flat top-level Python modules whose prefixes act as informal packages;
- milestone and slice identifiers in permanent module and architecture names;
- a large mixed-purpose `scripts/` surface;
- hand-maintained documentation indexes;
- active documents with inconsistent granularity;
- implementation handoffs, evidence, current architecture, contracts, and planning material mixed under the same directories;
- an active documentation cutover whose per-document guard and bookkeeping cost is becoming a permanent maintenance surface.

The existing documentation preparation identified the correct target idea: stable architecture is synthesized by responsibility, exact normative blocks are rebuilt as contracts, and slice records cease to be active architecture. The execution model drifted toward moving one legacy source at a time, leaving the mixed active tree difficult to understand throughout the migration.

A permanent frozen copy of every retired document or source file would create a second searchable tree. That would preserve the same ambiguity for humans, repository tooling, and AI readers. Git already preserves prior blobs, paths, commits, tags, and pull-request history; the current tree should not duplicate that archive without a continuing operational reason.

At the same time, the current critical implementation path is not structurally stable yet:

```text
LC-1A Correct
  -> LC-1B Forget
  -> LC-1C Pin / Unpin
  -> LC-1D Restore
  -> LC-1E Consolidate
  -> RT-1 Retrieval projection and hard cutover
```

Primary MEM remains the current ordinary memory and Retrieval authority until RT-1. Moving or renaming the core memory and Retrieval modules, or finalizing their permanent active documentation, before that boundary would mix semantic authority migration with physical and editorial migration and reduce reviewability.

## Decisions

### Permanent active assets use intent-oriented names

New permanent code modules, public or operator CLI entry points, workflow-owned permanent commands, active architecture documents, exact contracts, maintained tests, and process-level smoke must not use implementation milestone identifiers such as `phase*`, `wave*`, `mvp*`, `i4c2`, `o1d1`, or equivalent slice IDs as their primary names.

Milestone and slice IDs remain valid in:

- pull requests and branch names;
- temporary construction artifacts removed before merge;
- retirement manifests and current records where the identifier is necessary provenance;
- Git history.

Existing milestone-oriented permanent assets are not renamed in a repository-wide sweep. They are renamed, synthesized, or removed only when their owning domain is migrated or a separately approved hard cutover establishes one accepted replacement.

Active names describe function and responsibility:

```text
runtime code             domain + supported function
ordinary test            function + regression boundary
process smoke            function + process or failure boundary
operator tool            supported operator action
repository validator     repository invariant being checked
```

### Domain packaging is staged around authority stability

The target Python layout is domain-oriented rather than prefix-oriented. Representative target domains include:

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

The exact final tree is determined by per-domain caller and dependency evidence. The example above is not authorization to create every directory or move every matching file in one PR.

Core governed domains move only after their authority boundary is stable. In particular, Subjective MEM, Retrieval, and Primary MEM namespace migration is blocked until RT-1 completes the one-authority cutover. Primary MEM is handled last so the implementation can choose retirement instead of spending effort moving code that no longer needs to remain current.

### Code and validation assets use active, transitional, and retired dispositions

Repository code, tests, smoke, workflows, and tools are classified into three operational states.

```text
active
  currently supported runtime, operator, contract, regression, process,
  recovery, or repository-governance responsibility

transitional
  characterization, compatibility, rollback, or migration responsibility
  that remains required until an explicit removal gate closes

retired
  no remaining supported caller, protected boundary, migration role,
  rollback role, or repository-governance responsibility
```

Active assets move to intent-oriented names when their owning atomic migration is executed. Transitional assets remain executable and visible in maintained locations such as `tests/characterization/`; each must identify its owner, protected boundary, current caller, removal gate, and replacement validation.

Retired code, smoke, wrappers, migrations, and tooling are deleted from the current tree and remain available through Git history. They are not moved to a general executable archive. An exceptional historical reproduction snapshot may remain only as a non-executable typed record, outside packages and test discovery, with source commit and digest; this is exceptional rather than the default.

### Active documentation is rebuilt by canonical domain

RelayLM does not preserve the current active document set merely because individual files are still useful. The permanent active set is rebuilt at stable responsibility-level granularity.

Documents share one active page only when they have the same owner, update trigger, lifecycle, primary consumers, and authority level. A difference in any of these is a reason to split. Shared milestone history, similar length, or current directory placement is not a reason to combine.

Canonicalization is executed by target domain:

```text
identify final authority and granularity
  -> enumerate all source documents and code or contract anchors
  -> synthesize current durable architecture
  -> rebuild exact normative content as contracts
  -> separate current implementation from accepted target
  -> fix current references and navigation
  -> delete consumed source and historical documents from the current tree
  -> record recovery and replacement data in one generated retirement manifest
```

Permanent active architecture describes stable responsibility. LC-1A through LC-1E, Phase 6, M3, Wave, ACG, CW, and similar implementation slices do not remain separate permanent architecture pages merely because they were implemented separately.

### Historical documents are retired to Git history by default

Retired documentation is deleted from the current tree after replacement and omission checks pass. Git history is the authoritative historical store.

The repository retains one small generated retirement manifest with fields equivalent to:

```text
old_path
last_live_commit
old_blob_sha
removed_by_pr
replacement_paths
disposition
retention_reason
```

The manifest is navigation and provenance only. It does not reproduce retired prose and does not become architecture, status, or contract authority.

A source document containing still-live architecture or normative content is not deleted until that content has an accepted active replacement or an explicit reviewed absorption, supersession, or retirement disposition. Desired wording changes are separated from verbatim contract migration when exact wording matters.

No redirect stubs, duplicate archived Markdown copies, or dual live paths are introduced merely to preserve old links. Current links and routers are repaired atomically; historical retrieval uses Git.

### Current records are narrowly allowlisted

The current tree may retain records only when they still perform a current function. Representative allowed classes are:

```text
release or tag validation receipt
irreversible or stateful migration receipt
security, privacy, or external audit record
current recovery or rollback checkpoint
retirement manifest
machine-readable current registry required by CI or operation
```

Completed implementation handoffs, superseded design sources, old roadmaps, historical proposals, ordinary completion reports, past convergence narratives, and obsolete one-document cutover receipts do not qualify merely because they once provided evidence.

The canonical location and schemas for retained records are fixed by the active-graph lock. `records/` must reject untyped free-form historical Markdown and must remain much smaller than `docs/`.

### Documentation migration uses domain batches, not source-file sequences

The already-open Cutover 1C-57 may finish under the reviewed legacy process. No new one-document Cutover 1C-N slice is opened afterward.

Later documentation work uses:

- one canonical active graph and retained-record allowlist lock;
- domain synthesis waves;
- bounded historical-retirement batches;
- one retirement-manifest update per batch;
- generic active-document, retained-record, normative-extraction, Git-recoverability, link, metadata, authority, and generated-index checks.

Bespoke per-document guards, self-tests, Markdown receipts, and active ledger bookkeeping are retired after their protected source family is included in the generic boundary.

Memory lifecycle canonicalization waits for LC-1. Retrieval and Primary MEM canonicalization waits for RT-1. Stable domains may proceed earlier in parallel.

### Repository maintenance follows coordinated workstreams

The accepted portfolio contains:

```text
Lane C: critical implementation
  LC-1 -> RT-1

Lane D: documentation canonicalization and historical retirement
  active graph -> stable-domain synthesis -> historical retirement

Lane R: repository maintenance
  classification -> smoke consolidation -> generated indexes -> package migration
```

The default capacity is one critical PR, up to one documentation PR, and up to one repository-maintenance PR. Three open PRs are a ceiling, not a target.

Path-disjointness alone is insufficient. Work is parallel-safe only when it also does not share runtime, storage, schema, contract, documentation authority, callers, generated registries, status ownership, or canonical entry points.

The detailed current sequencing authority is [Repository Structure and Documentation Canonicalization Plan](../planning/repository-structure-migration.md).

### Continuation shorthand executes the portfolio

The user instructions `次に進めて`, `進めて`, `続けて`, and `次へ` mean:

1. refresh repository and open-PR state;
2. converge existing work before creating overlapping replacements;
3. advance the earliest executable critical-path action;
4. use CI, sequencing, or owner-only blockers as a trigger to advance eligible parallel work;
5. advance at least one parallel lane when meaningful safe work exists;
6. avoid asking the user to choose among candidates when documented priority resolves the choice;
7. report the resulting critical, parallel, and portfolio state.

This command does not authorize hidden background execution. All work is performed and reported in the current interaction. Exact behavior is governed by [Workstream Orchestration and Continuation Command](../planning/workstream-orchestration.md).

### Validation is separated by responsibility

The repository uses three validation classes:

```text
pytest or maintained test suites
  pure unit, component, schema, parser, renderer, and ordinary integration regression

process-level smoke
  crash, restart, subprocess, security, concurrency, filesystem publication,
  platform, CLI, and operator-path validation

repository validation tools
  documentation audits, inventory, generated-index drift checks, retirement boundaries,
  current-record registries, and other repository-governance checks
```

Not every script becomes pytest. Migration, generator, benchmark, operator, and current-record validation commands remain outside ordinary test inventory when their responsibility differs.

### Documentation entry points stay curated; mechanical lists are generated

`docs/README.md` remains a short human- and AI-curated entry point for current authority and product-critical boundaries. Long active architecture, ADR, contract, planning, reference, and operations lists are generated from canonical metadata and validated for drift.

Retained-record navigation is generated separately and must not be mixed with current authority navigation. Retired documents are found through the retirement manifest and Git history, not a second document tree.

Generated indexes are navigation only and must not become a second status, contract, architecture, or audit authority.

### Every move or retirement is atomic and evidence-gated

Each namespace, script-family, canonical documentation domain, historical-retirement batch, or index-generation wave requires its own accepted scope and exact caller or source evidence. A wave must update current imports, invocations, workflows, entry points, tests, active links, manifests, and documentation in the same PR or an explicitly coordinated atomic set.

Permanent aliases, redirects, fallback imports, dual-read, and dual-write are prohibited by default. A temporary compatibility surface requires a named owner, current consumer, removal gate, and bounded exit condition.

## Consequences

- New naming debt stops immediately when this ADR merges.
- The critical LC-1 and RT-1 authority migration remains reviewable and is not obscured by a broad package move.
- The active documentation tree converges toward consistent responsibility-level granularity instead of preserving mixed historical shapes.
- Retired documents and code disappear from ordinary current-tree search while remaining recoverable through Git.
- The repository avoids maintaining a second frozen source tree.
- One-file cutover bookkeeping stops growing after the already-open legacy slice.
- Low-risk repository cleanup and stable-domain documentation can proceed without blocking product work when paths and authorities are disjoint.
- A bare continuation instruction becomes reproducible across threads because the selection algorithm and lane registry are repository authorities.
- Core package migration remains substantial, but it occurs once against stable domain boundaries.
- Some phase-oriented names remain temporarily; this is accepted migration debt rather than permission to create more.
- Primary MEM may be retired instead of reorganized, avoiding unnecessary churn.

## Rejected alternatives

### Reorganize all of `relaylm/` immediately

Rejected because LC-1 and RT-1 still change memory and Retrieval authority. Combining those changes with a repository-wide move would make failures and regressions harder to attribute.

### Keep the current active documents and only remove obvious evidence

Rejected because the active documents have inconsistent granularity and mixed authority. Merely selecting survivors would preserve the central readability problem.

### Continue one-source-document cutover until every file is normalized

Rejected because the per-document guard, self-test, receipt, ledger, and link-repair cost grows faster than the value of polishing historical sources.

### Move every legacy document into a frozen repository tree

Rejected because Git already preserves the source blobs and history. A second tree would remain searchable, would confuse current authority discovery, and would create another index, link, validation, and maintenance surface.

### Delete legacy documents before synthesizing active replacements

Rejected because some source documents contain still-live architecture and normative content. Historical retirement requires accepted active replacement or explicit reviewed disposition.

### Move every retired code asset into an executable archive

Rejected because archived Python and smoke remain discoverable by imports, tests, dependency scanners, security tooling, and AI readers. Retired executable assets are deleted by default; exceptional reproduction snapshots are non-executable typed records.

### Convert every script to pytest

Rejected because operator commands, subprocess isolation, crash/restart tests, platform checks, migration tools, generators, benchmarks, and repository audits have distinct execution responsibilities.

### Preserve every old import through compatibility wrappers

Rejected because indefinite wrappers create duplicate entry points and permanent removal debt. Compatibility is exceptional and time-bounded.

### Ask the user to choose the next lane after every PR

Rejected because the accepted project plan already establishes dependency and parallel-work priority. Repeated choice prompts add orchestration burden without improving correctness when repository evidence resolves the decision.

## Implementation status

This ADR records an accepted target and execution constraint. It does not claim that the canonical active graph or retained-record allowlist exists, historical documents or code have been retired, indexes are generated, smoke families are reorganized, continuation orchestration has been exercised, or domain packages are migrated. Current completion remains owned by `docs/PROJECT_STATUS.md` and exact implementation evidence.

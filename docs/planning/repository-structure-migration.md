---
relaylm_doc_type: planning
relaylm_authority: repository_structure_documentation_canonicalization_and_maintenance_execution_order
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: repository_maintenance
relaylm_update_trigger:
  - an active prerequisite PR merges or is superseded
  - LC-1 or RT-1 ordering changes
  - the documentation canonicalization or retirement boundary changes
  - a repository-maintenance stage opens, completes, or is reordered
  - a public import, compatibility, retained-record, or PR-lifecycle rule changes
relaylm_not_authoritative_for:
  - current implementation completion
  - exact runtime, storage, schema, or API behavior
  - deletion or migration authorization for an unlisted asset
  - repository-wide user-data migration
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0006-repository-structure-and-maintenance-sequencing.md
relaylm_related_authority:
  - ../architecture/project_execution_plan.md
  - workstream-orchestration.md
  - ../DOCUMENTATION_MODEL.md
  - ../architecture/documentation-governance.md
  - ../architecture/repository-maintenance-system.md
  - ../operations/documentation-synthesis-and-retirement.md
  - ../evidence/implementation/repository_inventory_baseline_1ca928cd.md
---
# Repository Structure and Documentation Canonicalization Plan

Last reviewed: 2026-08-09 JST

## Purpose

This document owns the execution order for repository simplification, documentation canonicalization, historical retirement, validation-surface consolidation, generated navigation, and domain-package migration.

Current implementation completion remains owned by [Project Status](../PROJECT_STATUS.md). The universal PR lifecycle and shorthand continuation behavior are owned by [Workstream Orchestration, Continuation Command, and PR Convergence](workstream-orchestration.md).

## Current post-RT-1 convergence state

The original planning-adoption prerequisites and the legacy Lane C critical implementation program are complete. Current implementation authority records RT-1D-R5 immediate retirement, its mandatory P8, and the P8 result/current-authority correction as completed. The ordinary Primary reader and its ranking/fallback path are retired; only explicitly classified read-only Primary history/observation/lifecycle/admin projections survive.

This completion releases the prerequisite that kept core memory and Retrieval modules protected from repository package migration. The next repository-maintenance stage is therefore Lane R R5, governed core package migration. Lane D has since advanced into D6; D6 final retirement and legacy cutover-tool retirement is the remaining Lane D work before PD-1, and it continues independently where path and authority safety permit.

The post-RT-1 handoff is:

```text
Lane R  R5 governed core package migration                 now eligible
Lane D  D6 final retirement / cutover-tool retirement      continue to completion

R5 complete + D6 complete
  -> Lane D PD-1 personality responsibility convergence
  -> Lane D PD-2 exact personality contracts
  -> Lane C PC-1..PC-4 Personality Core implementation
  -> 9B end-to-end evaluation
  -> Character Presence implementation
```

Lane R R6 Primary MEM disposition remains required repository cleanup after R5, but it is not a blanket prerequisite for PD/PC. It may proceed in parallel with later personality design or implementation only when exact path, caller, import, retained-authority, and semantic ownership are disjoint. A concrete R6 dependency still blocks the affected PD/PC slice.

For historical context, the plan was originally adopted after:

```text
PR #665  LC-1A Subjective MEM Correct                 merged
PR #667  Documentation Hard Cutover 1C-57             merged
PR #668  ADR / planning adoption                      merged
```

No new one-source-document Documentation Hard Cutover slice is opened after 1C-57.

## Program model

RelayLM uses three coordinated lanes. The first Lane C authority-changing program is complete; the lane is intentionally idle until the post-migration Personality Core gates are satisfied.

```text
Lane C: critical implementation
  legacy program complete:
    LC-1B -> LC-1C -> LC-1D -> LC-1E -> RT-1

  future gated program:
    PC-1 Personality State
      -> PC-2 Working Self
      -> PC-3 SLP automatic personality updates
      -> PC-4 Reflective Distillation

Lane D: documentation canonicalization and historical retirement
  D1 active graph lock
    -> D2 stable-domain synthesis
    -> D3 historical-retirement batches
    -> D4 lifecycle canonicalization after LC-1
    -> D5 Retrieval / Primary MEM canonicalization after RT-1
    -> D6 final retirement and legacy cutover-tool retirement
    -> PD-1 personality responsibility convergence after D6 + Lane R R5
    -> PD-2 exact personality contracts

Lane R: repository maintenance
  R1 classification
    -> R2 test / smoke / validation consolidation
    -> R3 generated navigation and drift checks
    -> R4 low-risk independent package moves
    -> R5 governed core package migration after RT-1
    -> R6 Primary MEM retirement-or-move cleanup
```

Lane C controls authority-changing implementation order. Lanes D and R may proceed in parallel only when path, caller, generated-registry, and semantic-authority ownership are disjoint. PD-1 may not begin until both D6 and Lane R R5 are complete; PC-1 may not begin until PD-2 is complete.

## Universal PR lifecycle

Every PR in every lane follows the same convergence lifecycle:

```text
P0 scope and authority lock
  -> P1 normal implementation
  -> P2 baseline validation and reviewable PR
  -> P3 thorough review
  -> P4 correction and exact-head validation
  -> P5 fresh final review
       -> finding exists? return to P4
       -> clean? proceed to P6
  -> P6 merge gate
  -> P7 expected-head-protected merge
  -> P8 post-merge convergence
```

A passing CI run does not replace P3 or P5. Known in-scope defects cannot be deferred merely to declare the current PR complete.

## Immediate rules

The following rules begin when ADR 0006 merges:

- no new permanent milestone- or slice-ID names in runtime modules, active architecture, contracts, maintained tests, process smoke, permanent CLI entry points, or workflow-owned commands;
- active assets use function- and responsibility-oriented names through their owning atomic migration;
- broad `relaylm/` namespace movement is allowed only through an explicitly governed migration stage such as the now-unblocked Lane R R5; ad-hoc namespace cleanup remains prohibited;
- no permanent import alias, redirect, fallback, dual-read, or dual-write is created merely to ease cleanup;
- every code, document, test, smoke, workflow, and tool is classified before deletion or consolidation;
- planning-only work does not change `docs/PROJECT_STATUS.md`;
- no general `frozen/`, `archive/`, or `legacy/` tree is created for retired Markdown or executable code;
- retired material is deleted from the current tree and recovered through Git history;
- only narrowly typed records with a continuing current function remain in the tree.

## Lane C: critical implementation

### C1: LC-1B Forget

Implement canonical Forget with:

- current-revision and authorization binding;
- retrieval invisibility;
- anti-reformation tombstones;
- deterministic idempotency and recovery;
- exact lineage to the forgotten revision;
- Primary MEM characterization comparison;
- no Purge or heuristic resurrection.

### C2: LC-1C Pin / Unpin

Port pinning without creating ranking authority outside the accepted current revision and lifecycle state.

### C3: LC-1D Restore

Restore only through exact Forget lineage and current authorization. Restore does not imply Purge reversal or heuristic resurrection.

### C4: LC-1E Consolidate

Implement exact source identity, supersession, false-merge controls, audit lineage, and deterministic rollback or recovery boundaries.

### C5: RT-1 Retrieval cutover

RT-1 must establish:

- exact-current Subjective MEM selection;
- lifecycle and mutation fail-closed behavior;
- rebuild-equivalent projections;
- old/new characterization comparison;
- durable content-free usage records;
- writer fencing;
- one ordinary Retrieval authority;
- removal of temporary adapters and replaced readers or writers.

RT-1 is complete. The core memory and Retrieval namespace is no longer protected merely because LC-1/RT-1 authority is still changing; later moves are nevertheless authorized only through Lane R R5/R6 with exact caller, compatibility, retained-authority, and rollback evidence.

### Future Lane C: Personality Core

The next Lane C authority-changing program is not a continuation of RT-1. It opens only after Lane R R5 establishes the governed core package boundary and Lane D completes D6 plus PD-1/PD-2 responsibility and contract convergence.

The ordered implementation program is:

```text
PC-1 Personality State
  -> PC-2 Working Self
  -> PC-3 SLP automatic personality updates
  -> PC-4 Reflective Distillation
```

Personality semantics for this later program remain owned by the accepted [Character Personality and Experience Architecture](../architecture/character/personality-and-experience.md); only repository execution ordering is governed by `docs/architecture/project_execution_plan.md`. This repository-maintenance plan does not define personality semantics or authorize those runtime changes by itself.

## Lane D: documentation canonicalization and historical retirement

### D1: canonical active graph and retained-record lock

D1 defines the intended active documentation graph before large-scale retirement.

The active tree contains current authority and current guidance only:

```text
docs/
  README.md
  PROJECT_STATUS.md
  DOCUMENTATION_MODEL.md
  adr/
  architecture/
  contracts/
  planning/
  reference/
  operations/
  guides/
  release/
  templates/
```

D1 also defines a narrow retained-record allowlist. Representative current record classes are:

```text
release or tag validation receipt
irreversible or stateful migration receipt
security, privacy, or external audit record
current recovery or rollback checkpoint
retirement manifest
machine-readable current registry required by CI or operation
```

`records/` is not a free-form historical archive.

D1 must fix:

- canonical active document list or deterministic generation rules;
- document granularity by owner, update trigger, lifecycle, primary consumer, and authority level;
- retained-record classes and schemas;
- retirement-manifest schema;
- domain synthesis order;
- generic active-document, retained-record, normative-extraction, Git-recoverability, link, authority, and generated-index checks;
- retirement path for bespoke per-document guards, receipts, and ledger entries.

### Canonical granularity

Documents share one permanent active page only when they have the same:

```text
owner
update trigger
lifecycle
primary consumers
authority level
```

Shared milestone history or similar length is not a reason to combine. Implementation slices do not survive as permanent architecture pages merely because they landed separately.

### D2: stable-domain synthesis

Each domain PR:

1. identifies final active authority and target granularity;
2. enumerates source documents and code, contract, status, and test anchors;
3. extracts durable architecture and exact normative content;
4. creates or revises canonical active documents;
5. distinguishes current implementation from accepted target;
6. classifies any continuing record against the allowlist;
7. repairs current links, routers, and generated navigation;
8. records retiring paths and replacement authorities;
9. deletes consumed historical sources from the current tree;
10. verifies Git recoverability and updates one retirement manifest.

Recommended stable-domain order before LC-1 and RT-1 completion:

```text
D2-A documentation governance and repository system
D2-B runtime pipeline and compile/checkpoint
D2-C Governed Evidence, CTX-OVL, and Shared Assessment
D2-D Character Workspace
D2-E Relationship, Scene, Emotion, and Analyzer governance
D2-F scheduler and local operation
D2-G voice, streaming, TTS, and latency
D2-H stable memory formation and storage boundaries unaffected by LC-1 or RT-1
```

Multiple D2 PRs may coexist only when they share no target document, source ownership, router, generated registry, or semantic authority.

### D3: historical-retirement batches

Retired documentation is deleted from the current tree after replacement and omission checks pass. One generated manifest records fields equivalent to:

```text
old_path
last_live_commit
old_blob_sha
removed_by_pr
replacement_paths
disposition
retention_reason
```

A source containing still-live architecture or normative content is not retired until an active replacement or explicit reviewed disposition exists.

No redirect stub, duplicate archived Markdown copy, or second live path is created solely to preserve an old link.

### D4, D5, D6, and Personality Design gates

D4 lifecycle and mutation canonicalization begins only after LC-1B through LC-1E stabilize lifecycle semantics. That prerequisite is complete.

D5 Retrieval and Primary MEM canonicalization begins only after RT-1 establishes one ordinary Retrieval authority. That prerequisite is complete, and Lane D has since advanced into D6; D6 final retirement and legacy cutover-tool retirement continues according to its own current Lane D authority and status.

After D6 and Lane R R5 are both complete, Lane D opens a new bounded Personality Design convergence program:

```text
PD-1 responsibility convergence
  SOUL / SELF boundary
  REL / OTHER MODEL
  GOAL / commitments / prospection
  Character Workspace ownership
  SLP update ownership
  Working Self vs RelayCTX responsibility

PD-2 exact contracts
  personality-state write authority
  provenance / confidence / evidence binding
  Working Self input/output and projection boundary
  SOUL automatic-write prohibition
  Reflective Distillation candidate/adoption boundary
```

PD-1/PD-2 revise only the responsibility nodes actually changed by the accepted personality target. They do not reopen stable Evidence, storage, retrieval, or lifecycle authorities unless an exact dependency requires it.

### D6: final retirement and tooling cleanup

D6 completes the documentation program by:

- retiring remaining non-active documents;
- completing the generated retirement manifest;
- removing retired path routers and hand-maintained long lists;
- retiring bespoke one-document guards, receipts, and active ledger bookkeeping;
- retaining only generic metadata, link, authority, normative-extraction, Git-recoverability, retained-record, and generated-index checks.

## Lane R: repository maintenance

### R1: responsibility classification

Classify each repository asset into its supported responsibility and operational state.

Responsibility classes include:

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

Operational states are:

```text
active
transitional
retired
```

An unreferenced asset is only a triage signal. `retired` requires proof that no supported runtime, operator, migration, rollback, characterization, or repository-governance responsibility remains.

### Transitional assets

Characterization, compatibility, rollback, and migration assets remain executable only when they identify:

```text
owner
protected boundary
current caller
removal gate
replacement validation
```

### R2: test, smoke, and validator consolidation

Preferred order:

1. remove proven wrapper/core or duplicate-entry-point pairs;
2. move pure regression into maintained pytest or integration suites;
3. retain process-level validation for crash, restart, subprocess, security, concurrency, filesystem, platform, CLI, and operator boundaries;
4. place migration characterization in a maintained location with an explicit removal gate;
5. consolidate repository validators and generated registries;
6. update workflow invocations only after one canonical entry point is selected;
7. rename retained assets by supported function through their owning atomic migration.

Do not convert operator commands, process-isolation smoke, migrations, generators, or benchmarks into pytest solely to reduce file count.

Retired code, smoke, wrappers, migrations, and tools are deleted from the current tree and remain recoverable through Git history. A general executable archive is prohibited.

### R3: generated navigation

After D1 fixes active placement and record classes:

- keep `docs/README.md` curated and short;
- generate active architecture, ADR, contract, planning, reference, and operations indexes;
- generate retained-record navigation separately;
- make generated files navigation-only;
- add reproducibility and drift checks;
- remove hand-maintained long lists only after equivalence is reviewed.

### R4: low-risk package moves

A package move may occur before RT-1 only when it does not touch active LC-1, Subjective MEM publication, ordinary Retrieval, or Primary MEM authority.

Candidate domains may include:

```text
clients/
tokens/
diagnostics/
scheduler/
interfaces/openai/
interfaces/soul_lab/
cli/
character/workspace/
```

Each move must preserve console scripts, `python -m` entry points, dynamic callers, subprocess roots, and operator invocations, and must not create a second public import authority.

### R5: governed core package migration

RT-1 is complete, so the R5 prerequisite is satisfied. R5 is the next governed core repository migration and proceeds in dependency order:

```text
evidence
  -> context overlay
  -> shared assessment
  -> subjective memory
  -> retrieval
  -> request and product interfaces
```

Each R5 wave must preserve one semantic authority, migrate callers atomically, reject old-path forwarding aliases unless a concrete governed compatibility consumer exists, and prove negative old-path/import references before its merge. R5 establishes the stable package/dependency substrate required before PD-1/PD-2 can freeze the new personality responsibility graph.

The Evidence wave completed in PR #947 with exact resulting main `ab7b07cfdd7a4886d71c335a55011da87c6572f7`; `relaylm.evidence` is its sole canonical package. The context-overlay wave completed in PR #951 with exact resulting main `1529bf38220e489300fdff322865a11a4d66406f`; `relaylm.context_overlay` is its sole canonical import package. The persisted `relaylm.ctx_ovl_*` schema identities remain byte-stable data-contract identities, not Python import compatibility surfaces. No old-path alias remains. The Shared Assessment wave completed in PR #956 with exact resulting main `5f85995678d01c8a0e4853fd38ae23eaa15bd303`; `relaylm.shared_assessment` is its sole canonical Python package, while persisted `relaylm.shared_assessment_*` schema identities remain unchanged. The Subjective Memory models slice completed in PR #966 with exact resulting main `1153af8b001b36ec625304234178f27bd7229b4f`; `relaylm.subjective_mem.models` is the sole model owner and persisted schema identities remain unchanged. The Subjective Memory commit-owner slice completed in PR #968 with exact resulting main `7399f7b0fa82e138a32406ef25a8930741916dd9`; `relaylm.subjective_mem.commit`, `commit_io`, and `commit_runtime` are canonical while persisted platform/schema identities remain unchanged. The Subjective Memory Markdown-owner slice completed in PR #971 with exact resulting main `6f7e51c21cae4aca0c26a4b1e1bbde7e11e1a8d1`; `relaylm.subjective_mem.markdown` is canonical while persisted Markdown schema identities remain unchanged. The Subjective Memory lifecycle-record slice completed in PR #973 with exact resulting main `6d3394fbe2d107c0f355161423d808432d581705`; `relaylm.subjective_mem.lifecycle` is canonical while persisted lifecycle schema identities remain unchanged. Remaining Subjective Memory responsibilities require fresh bounded P1 transactions before Retrieval, and later waves remain blocked on the dependency order above.

### R6: Primary MEM disposition

Do not automatically move every Primary MEM module. Classify each remaining asset as:

```text
retired_after_cutover
migration_or_characterization_dependency
rollback_dependency
operator_or_recovery_dependency
retained_current_component
```

Delete only through reviewed atomic waves. Move only the subset that remains a supported current component.

R6 follows R5 as repository cleanup. It is not a blanket gate on Personality Design or Personality Core, because the ordinary Primary reader has already retired; however any PD/PC slice that touches a still-undisposed Primary path, caller, recovery surface, or retained authority must wait for that exact R6 disposition.

## Post-R5 handoff to Personality Design and Personality Core

Repository maintenance does not own the new character semantics. Its handoff is structural:

```text
Lane R R5 complete
       +
Lane D D6 complete
       ↓
Lane D PD-1 responsibility convergence
       ↓
Lane D PD-2 exact contracts
       ↓
Lane C PC-1 Personality State
       ↓
Lane C PC-2 Working Self
       ↓
Lane C PC-3 SLP automatic personality updates
       ↓
Lane C PC-4 Reflective Distillation
       ↓
9B end-to-end evaluation
       ↓
Character Presence
```

This handoff preserves the accepted distinction between repository structure, documentation/contract authority, and authority-changing runtime implementation. Package movement must not silently implement SELF, GOAL, OTHER MODEL, Working Self, SLP personality writes, or Reflective Distillation.

## Parallel portfolio

Default capacity:

```text
1 Lane C PR
+ up to 1 Lane D PR
+ up to 1 Lane R PR
```

Three PRs are a ceiling, not a target. A new PR requires a bounded scope, owner, exact path and authority non-overlap, and a validation plan.

Until PD-2 completes, the Lane C slot has no Personality Core work merely because capacity is free. R6, remaining Lane D canonicalization, and later PD work may overlap only under the ordinary path/authority disjointness rules.

Two items are not parallel-safe when either changes:

- the same file or generated registry;
- the same runtime, storage, schema, contract, documentation, or record authority;
- a caller or entry point the other moves or removes;
- shared status or sequencing without one convergence owner;
- an unmerged semantic dependency;
- competing canonical paths, imports, or precedence rules.

## Atomic PR requirements

Every execution PR states:

```text
lane and stage
scope and exact paths
current responsibility and callers
accepted replacement mapping
behavioral and authority non-goals
public and operator entry-point effect
state migration or no-state rationale
compatibility and removal gate
validation matrix
rollback boundary
negative-reference checks
parallel-safety analysis
current P0-P8 stage
```

A documentation synthesis or retirement PR additionally states:

```text
canonical target documents
source-document set
normative extraction result
retained-record decisions
retiring-path manifest effect
Git-recoverability proof
retired bespoke guards or receipts
```

## Completion criteria

The program is complete only when:

- permanent milestone-oriented naming is rejected;
- active documentation is complete at stable responsibility-level granularity;
- retired documentation and code are absent from the current tree and recoverable through Git;
- retained records are narrowly typed and current-function-owned;
- one-document cutover guards, receipts, and ledger growth are retired;
- generated navigation is reproducible and drift-checked;
- retained scripts have one clear responsibility and canonical invocation;
- ordinary tests, process smoke, transitional characterization, operator tools, and repository validators are distinguishable;
- accepted domain packages enforce dependency direction;
- Subjective MEM and Retrieval have one canonical package and authority path;
- remaining Primary MEM assets have an explicit retained, transitional, rollback, or retired disposition;
- no permanent migration aliases or duplicate semantic authorities remain.

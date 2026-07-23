---
relaylm_doc_type: planning
relaylm_authority: repository_structure_documentation_canonicalization_and_maintenance_execution_order
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: repository_maintenance
relaylm_update_trigger:
  - an active prerequisite PR merges or is superseded
  - LC-1 or RT-1 ordering changes
  - the documentation canonicalization or historical-retirement boundary changes
  - a repository-maintenance wave opens, completes, or is reordered
  - a public import, compatibility, or repository-retention requirement changes
  - the parallel-work orchestration contract changes
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
  - ../proposals/repository-simplification.md
  - ../evidence/implementation/repository_inventory_baseline_1ca928cd.md
---
# Repository Structure and Documentation Canonicalization Plan

## Purpose and authority

This document owns the accepted execution order for repository simplification, canonical active-document reconstruction, historical retirement, retained-record governance, validation-surface consolidation, documentation-index generation, and domain-package migration. It is subordinate to the repository-wide [Project Execution Plan](../architecture/project_execution_plan.md) and does not claim current implementation completion.

The plan deliberately separates product-critical memory authority migration from physical repository movement and documentation reconstruction. The shorthand continuation command and parallel-lane selection rules are defined by [Workstream Orchestration and Continuation Command](workstream-orchestration.md).

## Program model

The program has three coordinated workstreams:

```text
Lane C: critical implementation
  LC-1 lifecycle migration -> RT-1 Retrieval hard cutover

Lane D: documentation canonicalization and historical retirement
  canonical active graph -> domain synthesis -> Git-history retirement

Lane R: repository maintenance
  classification -> smoke consolidation -> generated indexes -> package migration
```

Lane C controls authority-changing implementation order. Lanes D and R may proceed in parallel only when path and authority ownership are disjoint.

## Current critical path and merge order

The current ordered work is:

```text
A. Converge active work
   1. Cutover 1C-57: complete final review and merge PR #667
   2. LC-1A Correct: synchronize PR #665 with resulting main, rerun exact-head validation,
      complete final review, and merge
   3. Retarget, validate, and merge the ADR / planning PR that adopts this program

B. Establish the new documentation boundary
   4. D1 canonical active graph, retained-record allowlist, and retirement-manifest lock
   5. D2 first stable-domain synthesis wave
   6. D3 first completed-evidence and source-document historical-retirement batch

C. Complete the memory authority migration
   7. LC-1B Forget and anti-reformation tombstones
   8. LC-1C Pin / Unpin
   9. LC-1D Restore with exact Forget lineage
  10. LC-1E Consolidate with source, supersession, and false-merge controls
  11. RT-1 Retrieval projection and one-authority hard cutover

D. Complete authority-dependent documentation
  12. D4 lifecycle and mutation canonicalization after LC-1
  13. D5 Retrieval and Primary MEM canonicalization after RT-1
  14. D6 final historical retirement and legacy cutover-tool retirement

E. Perform governed core namespace migration
  15. Evidence
  16. CTX overlay
  17. Shared Assessment
  18. Subjective MEM
  19. Retrieval
  20. Primary MEM retirement-or-move decision and final cleanup
```

PR #667 remains first because it is the already-open last legacy cutover slice and is path-disjoint from LC-1A. PR #665 follows after synchronization so its current-status and execution-plan claims are validated against the post-cutover main tree. The program then stops opening one-source-document cutover PRs and switches to canonical target-domain waves.

No later item is marked complete by this registration.

## Immediate rules that start with the decision PR

The following rules apply as soon as ADR 0006 merges:

- do not create new permanent `phase*`, `wave*`, `mvp*`, or slice-ID module names;
- do not create new permanent active architecture, contract, maintained-test, or process-smoke filenames with milestone IDs;
- put slice IDs in PRs, temporary construction artifacts, necessary record provenance, and Git history instead;
- do not start a broad `relaylm/` move while LC-1 or RT-1 authority is changing;
- do not add permanent import aliases merely to ease future migration;
- classify a script, module, smoke, workflow, or document before proposing deletion or consolidation;
- keep `docs/PROJECT_STATUS.md` unchanged for planning-only work;
- stop registering new one-document Documentation Hard Cutover slices after the already-open Cutover 1C-57;
- select documentation work by canonical target domain, not by the next legacy filename;
- treat documents outside the canonical active set as source or historical material pending replacement review and retirement;
- do not create a general frozen or archive tree for retired Markdown, Python, smoke, or tooling assets;
- retain only narrowly typed current records with a continuing operational or governance function.

Existing milestone-oriented assets remain valid current paths until their owning atomic migration, synthesis, or removal PR lands.

## Parallel work portfolio

The default portfolio is one critical implementation PR, up to one documentation-canonicalization PR, and up to one repository-maintenance PR. Three open PRs are a ceiling rather than a target.

A bare `次に進めて` advances this portfolio according to [Workstream Orchestration and Continuation Command](workstream-orchestration.md): converge existing PRs first, advance the earliest executable critical-path item, and then advance eligible path- and authority-disjoint documentation or maintenance work without asking the user to choose among already ordered candidates.

## Lane D: documentation canonicalization and historical retirement

### D0: finish the last legacy cutover slice

Cutover 1C-57 may finish under the existing reviewed process. No new Cutover 1C-N source-by-source slice is opened afterward.

D0 completion does not claim that the active documentation tree is already coherent.

### D1: canonical active graph, retained-record allowlist, and retirement-manifest lock

D1 defines the final intended active documentation graph, stable granularity rules, the narrow current-record boundary, and Git-history retirement mechanics before large-scale deletion.

The active document tree contains current authority and current guidance only:

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

D1 must decide whether repeatable evaluation methods remain under `docs/evaluation/` or are folded into another current collection. Completed results do not remain active merely because the method remains current.

The separately indexed record tree is narrow:

```text
records/
  releases/
  migrations/
  audits/
  checkpoints/
  manifests/
```

Exact directory names may be refined by D1. The governing restriction is mandatory: `records/` contains only typed records with a continuing release, stateful migration, audit, recovery, rollback, or repository-governance function. It is not a free-form historical-document archive.

D1 must define:

- the canonical active document list or deterministic generation rules;
- stable document granularity by owner, update trigger, lifecycle, consumer, and authority level;
- retained-record types, required fields, retention triggers, and retirement rules;
- the domain synthesis order;
- the generated retirement-manifest schema;
- generic active-document, retained-record, normative-extraction, Git-recoverability, and link checks;
- the retirement plan for bespoke per-document guards, receipts, evidence collections, and ledger entries.

### Canonical granularity rule

Documents share one active page only when they have the same:

```text
owner
update trigger
lifecycle
primary consumers
authority level
```

A difference in any of these dimensions is a reason to split. Similar length or a shared historical milestone is not a reason to combine.

Permanent active documents describe stable responsibility, not implementation slices. For example, LC-1A Correct, LC-1B Forget, LC-1C Pin / Unpin, LC-1D Restore, and LC-1E Consolidate do not remain as five permanent architecture pages. Their durable design belongs under lifecycle-and-mutation architecture and exact lifecycle contracts; their completed slice documents are retired after synthesis.

### Retained-record allowlist

Representative allowed record classes are:

```text
release_or_tag_validation_receipt
stateful_or_irreversible_migration_receipt
security_privacy_or_external_audit
current_recovery_or_rollback_checkpoint
retirement_manifest
machine_readable_current_registry_required_by_ci_or_operation
```

A retained record must state:

```text
record type
current consumer or governing requirement
creation or execution identity
immutable or update semantics
retention trigger
retirement trigger
```

The following do not qualify merely because they were once useful:

- completed implementation handoffs;
- superseded architecture or contract sources;
- old roadmaps and planning registrations;
- historical proposals;
- ordinary completion reports and convergence narratives;
- past evaluation descriptions that no current release, audit, or decision consumes;
- one-document cutover receipts whose only function was proving a path move.

### Retirement manifest

The generated retirement manifest contains fields equivalent to:

```text
old_path
last_live_commit
old_blob_sha
removed_by_pr
replacement_paths
disposition
retention_reason
```

The manifest is provenance and recovery navigation only. It does not reproduce retired prose and does not become a second architecture, status, contract, or evidence authority.

CI should verify that recorded commits and blobs remain addressable through full Git history and that current links do not depend on retired paths.

### D2: stable-domain synthesis waves

D2 reconstructs active documentation by canonical target domain rather than moving one source file at a time.

Each domain wave:

1. defines the final active authority and target granularity;
2. enumerates all source documents and current code, contract, status, test, and record anchors;
3. extracts durable current architecture and exact normative content;
4. creates or revises the canonical active document set;
5. separates current implementation from accepted target behavior;
6. classifies any still-current record against the retained-record allowlist;
7. repairs current links, routers, and navigation;
8. records retiring paths and replacements in one generated manifest update;
9. deletes consumed source and historical documents from the current tree;
10. verifies Git recoverability and negative current-path references.

Recommended stable-domain order before LC-1 and RT-1 completion:

```text
D2-A documentation governance and repository system
D2-B runtime pipeline and compile/checkpoint
D2-C Governed Evidence, CTX-OVL, and Shared Assessment
D2-D Character Workspace
D2-E Relationship, Scene, Emotion, and Analyzer governance
D2-F Scheduler and local operation
D2-G Voice, streaming, TTS, and latency
D2-H stable memory formation and storage boundaries not changed by LC-1 or RT-1
```

Multiple D2 waves may be open only when they do not share target documents, source ownership, routers, generated registries, or authority references.

### D3: bulk historical retirement

D3 removes documents whose durable value is historical, evidentiary, or source-only after replacement and omission checks pass.

Default treatment:

```text
source body           delete from current tree; retain through Git history
source filename       record in retirement manifest
old metadata          no rewrite required before deletion
old relative links    do not preserve through redirect stubs
active references     remove or replace atomically
current record        retain only when allowlisted and still consumed
manifest              required
Git recoverability    required
```

A source document containing still-live normative content is not retired until that content has an accepted active replacement or an explicit reviewed absorption, supersession, or retirement rationale.

D3 should favor bounded domain or collection batches over one enormous deletion PR. It must not create a duplicate `frozen/documentation/` tree.

### D4: lifecycle and mutation canonicalization

D4 begins after LC-1A through LC-1E establish the stable lifecycle boundary. It creates the final lifecycle-and-mutation architecture and contracts, then retires the LC-1 slice documents and replaced Primary MEM lifecycle source material.

D4 must not run ahead of unresolved LC-1 semantics merely to make the tree look clean.

### D5: Retrieval and Primary MEM canonicalization

D5 begins after RT-1 establishes one ordinary Retrieval authority. It builds the final Retrieval and grounding architecture, records the current Subjective MEM projection and usage-record boundary, and classifies every remaining Primary MEM document as active, current record, migration/rollback dependency, or retireable history.

### D6: final historical retirement and tooling retirement

D6 completes the documentation program by:

- retiring remaining non-active documents;
- generating the final retirement-manifest state;
- retaining only allowlisted current records;
- removing retired path routers and hand-maintained long lists;
- retiring bespoke per-document guards, self-tests, receipts, and evidence indexes;
- replacing the active migration ledger with the generic retirement manifest and any still-current program record;
- retaining generic metadata, link, authority, normative extraction, Git-recoverability, record-schema, and generated-index drift checks.

## Documentation validation model

The new model keeps four generic validation families.

### Active-document validation

The active document tree rejects:

- historical or superseded document profiles outside explicitly permitted current policy cases;
- implementation handoff, completion report, validation receipt, or wave evidence presented as current architecture;
- new permanent milestone-oriented architecture or contract filenames;
- duplicate authority keys and competing canonical documents;
- active links that depend on retired documents as current authority.

### Retained-record validation

The record tree requires:

- every record type is allowlisted;
- required provenance, current consumer, retention trigger, and retirement trigger fields exist;
- free-form historical Markdown cannot enter as an untyped record;
- records are excluded from current architecture and status indexes unless explicitly referenced by their owning authority;
- obsolete records are retired rather than accumulated indefinitely.

### Historical-retirement and Git-recoverability validation

Each retirement batch requires:

- every removed path appears in the generated retirement manifest;
- last-live commit and source blob are addressable in full Git history;
- replacement paths or explicit no-replacement disposition are recorded;
- current routers, workflows, scripts, and documents no longer depend on removed paths;
- no redirect stub or duplicate archive copy was added by default.

### Normative-extraction validation

When source material contains exact schema, state, gate, must/must-not, or other normative candidates, the batch must record:

- active replacement path;
- exact digest preservation where wording is moved verbatim; or
- explicit reviewed absorption, supersession, or retirement rationale.

The existing inventory, path-dependency, normative-digest, and provenance tools are retained where useful, but their purpose changes from controlling one-file-at-a-time movement to preventing omissions during domain synthesis and historical retirement.

## Lane R: repository maintenance before RT-1

The following work may proceed in parallel with Lane C and Lane D when it is path- and authority-disjoint.

### R1: script, workflow, code, and validation responsibility classification

Use the fixed repository inventory as evidence and classify assets into both responsibility and lifecycle state.

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
runtime_component
planned_inactive
unclassified
```

Lifecycle states are:

```text
active
transitional
retired
```

`transitional` includes characterization, compatibility, rollback, and migration assets still required until an explicit gate closes. `retired` is a reviewed conclusion, not an initial reachability label.

R1 produces reviewed classification and candidate plans. It does not authorize deletion by itself.

### R2: smoke, test, tooling, and validation consolidation

Execute bounded families in this order:

1. remove proven wrapper/core or duplicate-entrypoint pairs;
2. move pure unit, schema, parser, renderer, and ordinary integration regression into maintained pytest or integration suites;
3. retain explicit process-level runners for crash, restart, subprocess, security, concurrency, filesystem, platform, CLI, and operator boundaries;
4. place migration and old/new equivalence characterization in maintained locations with explicit removal gates;
5. group repository audits and inventory under a validation-tool namespace;
6. update workflow registries only after the canonical invocation is selected;
7. remove milestone IDs when the canonical active file is moved or renamed, not through an unrelated global rename;
8. delete retired executable assets rather than moving them to a general archive tree.

Every transitional asset must name:

```text
owner
protected boundary
current caller
removal gate
replacement validation
```

An exceptional code-reproduction snapshot may remain only as a non-executable typed record, outside packages and test discovery, with source commit and digest.

### R3: documentation and record entry-point generation

Begin after D1 establishes stable active placement, record schemas, and metadata boundaries.

1. keep `docs/README.md` curated and short;
2. generate active architecture, ADR, contract, planning, reference, and operations indexes from metadata;
3. generate a separate small retained-record index;
4. expose retired paths through the retirement manifest and Git recovery instructions, not a duplicate content tree;
5. make generated files navigation-only;
6. add reproducibility and drift checks;
7. remove corresponding hand-maintained long lists only after generated equivalence is reviewed.

### R4: low-risk independent package moves

A low-risk package move may occur before RT-1 only when it does not touch active LC-1, Subjective MEM publication, ordinary Retrieval, or Primary MEM authority. Candidate domains include:

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

Candidate order is determined by complete caller evidence, not by the list order above. Each move must preserve console scripts and operator invocations, and must not create a second public import authority.

## LC-1 and RT-1 critical-path gate

The package migration and authority-dependent documentation must not destabilize lifecycle and Retrieval semantics.

### LC-1B Forget

Complete canonical Forget, retrieval invisibility, anti-reformation tombstones, exact authorization lineage, deterministic recovery, and Primary characterization comparison.

### LC-1C Pin / Unpin

Port pinning behavior without creating ranking authority outside the accepted current revision and lifecycle state.

### LC-1D Restore

Restore only through exact Forget lineage and current authorization. Do not add purge or heuristic resurrection.

### LC-1E Consolidate

Implement source identity, supersession, false-merge controls, audit lineage, and deterministic rollback or recovery boundaries.

### RT-1 Retrieval cutover

RT-1 must establish:

- exact-current Subjective MEM selection;
- lifecycle and mutation fail-closed behavior;
- rebuild-equivalent projections;
- old/new characterization comparison;
- durable content-free usage records;
- writer fencing;
- one ordinary Retrieval authority;
- removal of temporary adapters and replaced readers or writers.

Until this gate closes, core memory and Retrieval modules remain protected migration dependencies and are not namespace-cleanup candidates.

## Core domain-package migration after RT-1

Core governed packages move in dependency order so later domains import final lower-level paths once.

### Stage R5-C1: `evidence/`

Move canonical Evidence records, stores, authorization state, projections, and supporting public boundaries. Update every current producer and consumer atomically.

### Stage R5-C2: `context/overlay/`

Move CTX-OVL state, selection, invalidation, TTL, checkpoint, and rebuild logic after Evidence paths are stable.

### Stage R5-C3: `assessment/`

Move Shared Assessment schemas, selectors, formation-time validation, and receipts after Evidence and overlay boundaries are stable.

### Stage R5-C4: `memory/subjective/`

Move Subjective MEM semantic records, lifecycle operations, Markdown publication, commit protocol, and recovery after LC-1 and RT-1 are complete.

### Stage R5-C5: `retrieval/`

Move ordinary Retrieval projection, query handling, ranking or selection boundaries, usage records, and request-path integration after the one-authority cutover is already proven.

### Stage R6: Primary MEM retirement or final move

Do not automatically move every `relaymem_primary_*` module. First classify each remaining asset as:

```text
retired_after_cutover
migration_or_characterization_dependency
rollback_dependency
operator_or_recovery_dependency
retained_current_component
```

Delete only through separately approved atomic waves. Move only the subset that remains a supported current component. Historical code and names remain recoverable through Git history; exceptional non-executable reproduction records remain separately allowlisted.

## Import and compatibility rules

Each package wave must define:

- the package public surface;
- allowed dependency direction;
- forbidden reverse imports;
- all console-script and `python -m` entry points;
- dynamic and subprocess roots;
- direct and indirect callers;
- temporary compatibility, if any, with owner and removal gate;
- negative checks for retired imports and paths.

Preferred dependency direction for governed core domains is:

```text
evidence
  -> context overlay
  -> shared assessment
  -> subjective memory
  -> retrieval
  -> request and product interfaces
```

Cross-cutting utilities must remain narrow. A `common` or `utils` package is not a substitute for assigning domain ownership.

## Atomic PR template

Every execution PR must state:

```text
workstream and program stage
scope and exact paths
current responsibility and callers
accepted replacement mapping
behavioral non-goals
public and operator entry-point effect
state migration or no-state rationale
compatibility and removal gate
validation matrix
rollback boundary
negative-reference checks
parallel-safety and authority-overlap analysis
```

A package move should not also redesign schemas, change default behavior, or close unrelated decision debt unless an explicitly coordinated atomic set is necessary and documented.

A documentation synthesis or retirement wave must additionally state:

```text
canonical target documents
source-document set
normative extraction result
retained-record decisions
retiring paths and last-live identities
retirement-manifest effect
Git-recoverability validation
retired bespoke guards or receipts
```

## Completion criteria

The repository-structure and documentation-canonicalization program is complete only when:

- new permanent milestone-oriented names are rejected;
- the canonical active document graph is complete at stable responsibility-level granularity;
- only allowlisted current records remain outside the active document authority tree;
- retired source and historical documents are absent from the current tree and recoverable through the generated manifest and Git history;
- no general frozen Markdown or executable-code archive tree exists;
- bespoke one-document cutover sequences, guards, receipts, evidence indexes, and active ledger bookkeeping are retired;
- long mechanical active-document and retained-record indexes are generated and drift-checked;
- retained scripts have clear responsibility and one canonical invocation;
- ordinary tests, process smoke, transitional characterization, operator tools, and repository validators are distinguishable;
- retired executable assets are removed rather than silently archived;
- accepted domain packages have enforced dependency direction;
- Subjective MEM and Retrieval have one canonical package and authority path;
- remaining Primary MEM assets have an explicit retained, transitional, record, or retired disposition;
- no permanent migration aliases or duplicate semantic authorities remain.

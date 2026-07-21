---
relaylm_doc_type: proposal
relaylm_authority: proposal_for_evidence_gated_repository_simplification
relaylm_status: target
relaylm_proposal_status: under_review
relaylm_volatility: medium
relaylm_owner: repository_maintenance
relaylm_update_trigger:
  - proposal is accepted, rejected, withdrawn, or materially revised
  - repository inventory or invocation-root evidence changes
  - a cleanup wave is accepted or completed
  - storage, serialization, or deployment authority changes
relaylm_not_authoritative_for:
  - current runtime behavior
  - deletion, movement, rename, consolidation, or compatibility removal
  - storage migration or persistent-write enablement
  - repository-wide serialization conversion
  - default-on feature graduation
  - implementation completion
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - ../adr/0005-subjective-mem-storage-authority.md
  - ../contracts/subjective-mem-storage-authority-and-commit-protocol.md
---
# Proposal: Evidence-gated repository simplification

This is an undecided proposal for reducing RelayLM's maintenance surface without confusing inventory evidence with deletion authority.

Acceptance would authorize measurement, classification, invocation-root analysis, and preparation of bounded cleanup candidates. It would not authorize deleting, moving, renaming, consolidating, or migrating any repository asset. Every destructive or compatibility-removing wave requires its own atomic pull request and separate explicit approval.

## Current context

RelayLM contains default runtime modules, opt-in components, operator CLIs, offline tools, generators, migration helpers, benchmarks, regression scripts, workflow entry points, evidence validators, and historical phase-oriented names. File counts and static import reachability do not distinguish those responsibilities.

The earlier repository-simplification proposal in PR #567 established several useful principles but is no longer current:

- it treated completion of the documentation hard cutover as a prerequisite, while repository simplification should proceed as an independent track that can run in parallel with the ongoing documentation hard cutover;
- it treated storage authority and a bounded SQLite spike as future work, while the Subjective MEM authority direction is now accepted and the experiment has been dispositioned;
- it allowed wording that could be read as proposal acceptance authorizing deletion waves;
- it predates the merged non-destructive repository and storage inventory tooling.

A concrete false positive remains instructive: `relaymem_slp_supervised_scheduler_service.py` participates in the supported O3 operator path through `scripts/relaylm_o3_always_on_local_scheduler.py`. It must not be classified as smoke-only or dead merely because it is absent from the default FastAPI import graph.

## Settled inputs

### Documentation boundary

Documentation cleanup continues as a parallel, separately governed track. This proposal neither governs nor blocks that work and does not require its completion before code or test inventory begins.

The current documentation model remains authoritative. Any proposal, evidence record, ADR, contract, or implementation document changed by a later cleanup wave follows its existing placement and lifecycle rules. Coordination is required when the parallel tracks touch the same path or authority reference.

### Existing inventory tooling

The merged repository and storage inventory tooling from PR #577 is non-destructive evidence collection. Its generated artifact is a starting point, not classification authority.

An `unclassified`, unreferenced, or low-fan-in result is a triage signal only. It never proves that an asset is unused or safe to remove.

### Subjective MEM storage authority

ADR 0005 and the Subjective MEM Storage Authority and Commit Protocol Contract settle the target authority split for Subjective MEM:

- canonical Markdown owns committed memory semantics, revision lineage, exact current/successor authority, and lifecycle-visible state;
- persistent cache/search state is rebuildable projection;
- the operations ledger owns non-rebuildable operational facts without becoming a second semantic authority;
- permanent dual-read or dual-write authority is prohibited.

This decision does not authorize a production migration and does not automatically govern unrelated scheduler, request-runtime, relationship, scene, evidence, or other storage domains. Cleanup of those domains still requires their own current authority analysis.

## Goals

- produce a commit-fixed and reproducible responsibility baseline from existing inventory tooling;
- classify every retained script by actual responsibility and invocation mode;
- audit Python modules from all supported invocation roots rather than only the default application graph;
- distinguish current, opt-in, operator, tooling, validation, planned-inactive, and dead-code-candidate paths;
- identify duplicated validation families without weakening crash, restart, subprocess, concurrency, security, migration, or operator coverage;
- prepare bounded cleanup waves with exact replacement and caller evidence;
- use hard cutover only after a specific replacement has been separately accepted;
- preserve user-owned durable state and every accepted authority boundary.

## Non-goals

- setting a target number of files, modules, scripts, workflows, or lines of code;
- treating all Python files under `scripts/` as tests or smoke checks;
- deleting modules based on static imports from `relaylm/app.py` or another single root;
- approving any deletion, path move, rename, workflow consolidation, or namespace reorganization in this proposal;
- approving a broad SQLite migration;
- applying the Subjective MEM storage decision to unrelated storage domains without review;
- converting every internal value to Pydantic;
- enabling a feature by default;
- creating compatibility aliases merely to make refactors easier;
- governing, pausing, replacing, or changing the scope of the parallel documentation hard-cutover program.

## Governing principles

### Classification before candidate status

Assets are classified by supported responsibility before they can become cleanup candidates.

Required responsibility classes include:

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
acceptance_or_evidence_validation
planned_inactive
unclassified
```

`dead_code_candidate` is not an initial responsibility class. It is a later conclusion that requires complete invocation-root and authority evidence.

### Invocation roots before reachability conclusions

The audit includes at least:

- FastAPI startup and request paths;
- console scripts declared in `pyproject.toml`;
- supported scripts and operator CLIs;
- `python -m` entry points;
- GitHub Actions commands and consolidated registries;
- subprocess child modules;
- plugin, registry, or dynamic-dispatch roots;
- migration, maintenance, generator, and benchmark commands;
- tests and evidence validators that protect current invariants;
- current documentation that advertises an operator or offline path.

Dynamic dispatch, subprocess construction, optional imports, and shell invocation are explicit audit limitations rather than silently ignored edges.

### Responsibility before count reduction

Success is clearer ownership, fewer duplicated mechanisms, reliable entry points, and understandable subsystem boundaries. Lower counts are useful only when those properties are preserved or improved.

### Current contracts before internal neatness

A cleanup may not weaken accepted runtime, evidence, lifecycle, storage, recovery, disclosure, operator, or validation contracts merely to improve package shape.

Phase-oriented or awkward names are not sufficient removal evidence. A move or rename must preserve all current consumers or be executed through a separately accepted hard cutover.

### Evidence before destructive authorization

No generated report, classifier, proposal, or local agent judgment authorizes deletion.

A destructive wave requires a separate atomic PR that names its exact files, modules, commands, workflows, or schemas and receives explicit approval after review.

## Proposed program

### Step 1: publish a commit-fixed baseline receipt

Use the existing inventory tools at one exact main commit and record:

- source commit SHA;
- analyzer versions and exact commands;
- inclusion and exclusion rules;
- responsibility taxonomy;
- invocation-root definitions;
- known false-positive and false-negative limits;
- generated artifact digests;
- aggregate counts separated by responsibility;
- unresolved classification count.

The reviewed summary belongs in evidence. Large row-level outputs may remain reproducible workflow artifacts when committing them would add noise without authority value.

Completion criteria:

- the result can be regenerated from the recorded commit;
- operator, offline, benchmark, generator, migration, and validation surfaces are distinguishable;
- no row is treated as a deletion decision;
- the O3 operator path is represented correctly.

### Step 2: classify scripts and workflow entry points

For each retained script, record at least:

```text
path
responsibility_class
owner
entrypoint_or_caller
covered_boundary
primary_validation_command
replacement_or_successor_if_any
retention_or_candidate_reason
confidence_and_unresolved_notes
```

Default treatment by class:

| Class | Default treatment |
|---|---|
| pure unit/component regression | prefer pytest when equivalent and clearer |
| ordinary API/integration regression | prefer a maintained integration suite |
| crash/restart/subprocess validation | retain a dedicated runner or isolated invocation |
| security/concurrency validation | retain explicit environment and isolation |
| operator CLI | keep outside test inventory |
| migration/maintenance/generator | keep as tooling with direct tests |
| benchmark | keep outside pass/fail regression gates |
| evidence validator | retain while its current evidence boundary exists |
| proven duplicate | candidate only after replacement equivalence is reviewed |

Workflow consolidation follows responsibility, not an arbitrary workflow-count target.

### Step 3: audit module invocation roots

For each module, record:

```text
module
responsibility_class
direct_and_indirect_callers
dynamic_or_subprocess_roots
documented_use
feature_gate_or_enablement
validation_coverage
owner
current_plan_dependency
candidate_status
```

A module can become a dead-code candidate only when all supported default, opt-in, operator, tooling, dynamic, subprocess, test, evidence, and near-term-plan roots have been checked.

Planned inactive code remains distinct from dead code. Test-only code remains distinct from obsolete code when it protects a current invariant.

### Step 4: prepare bounded candidate waves

Candidate waves are grouped by one responsibility and one reviewable boundary, for example:

- one proven duplicate ordinary-regression family;
- one retired phase-specific wrapper with an existing canonical replacement;
- one generated or temporary artifact family;
- one low-risk subsystem namespace whose callers are completely enumerated.

A candidate-wave plan includes:

- exact asset list;
- current caller and documentation evidence;
- replacement mapping or obsolete-boundary rationale;
- retained invariant list;
- affected workflows and operator commands;
- negative-reference checks;
- expected validation matrix;
- state migration, drain, rebuild, or no-state rationale;
- rollback boundary;
- explicit statement that the plan itself does not authorize execution.

### Step 5: execute only separately approved atomic waves

Each implementation PR requires separate explicit approval. Proposal acceptance is insufficient.

An execution PR must:

- be based on current main;
- change only the accepted wave;
- update all current callers and documentation in the same PR or an explicitly coordinated atomic set;
- preserve current behavior unless behavior change is separately authorized;
- remove the superseded internal path at the accepted cutover boundary;
- add negative checks preventing retired references from returning;
- avoid indefinite aliases, redirects, fallbacks, dual-read, or dual-write paths;
- use one-time migration or rebuild tooling only where required;
- verify user-owned durable state by backup plus count or digest checks when affected;
- pass exact-head CI and independent final review before merge.

### Step 6: keep broader architecture changes separate

The following remain separate decisions even after this proposal is accepted:

- production storage migration;
- scheduler or other non-Subjective-MEM storage authority;
- subsystem-wide namespace redesign;
- broad serialization conversion;
- public CLI or external API compatibility changes;
- default-on feature graduation;
- whole-repository rewrite.

## Deletion authorization gate

No module, script, workflow, schema, document, or command may be deleted under this proposal alone.

A deletion wave is eligible for separate approval only when:

- the exact asset is classified;
- no supported invocation root remains, or every current caller has an accepted replacement;
- current documentation no longer advertises the old path after the same atomic change;
- no retained validation requires the asset for a current invariant;
- no accepted near-term plan depends on it;
- historical value remains in current evidence or Git history;
- user-owned durable state is absent or has an accepted migration/backup plan;
- relevant compile, runtime, operator, documentation, and regression checks pass;
- the PR body requests explicit authorization for that exact deletion wave.

A reviewer may approve audit evidence without approving the resulting deletion candidate.

## Hard-cutover boundary

Hard cutover is the preferred execution model only after a specific replacement has been accepted.

For an approved internal replacement:

- update every current caller;
- switch one authority or entry point;
- remove the superseded path in the bounded cutover;
- reject legacy references with deterministic checks;
- do not retain permanent compatibility solely for convenience.

Compatibility may be retained only when a current consumer is identified and a separate time-bounded decision defines its owner, scope, removal trigger, and exit date or condition.

## Alternatives

### Merge PR #567 as written

Rejected. Its treatment of documentation completion as a prerequisite and its storage sequencing are stale, and its adoption boundary can be read as authorizing deletion waves without a separate decision.

### Delete everything absent from the default application graph

Rejected because it misses opt-in, operator, offline, workflow, dynamic, subprocess, and evidence paths.

### Convert every script to pytest

Rejected because operator commands, benchmarks, generators, migration tools, and some process-level validation have different responsibilities.

### Preserve compatibility during every refactor

Rejected as a default because it creates aliases, bridges, duplicate paths, and removal debt. Current consumers still require an explicit compatibility decision.

### Rewrite the repository from scratch

Rejected as the initial strategy because it would discard validated lifecycle, recovery, isolation, storage, operator, and evidence semantics.

### Keep the repository unchanged

Rejected because unclear ownership and duplicated mechanisms continue to increase review and maintenance cost.

## Risks and mitigations

- **Inventory is mistaken for authority.** Keep generated rows non-authoritative and require a separate deletion PR.
- **An operator path is missed.** Include CLIs, workflows, subprocesses, dynamic roots, and documentation in the invocation audit.
- **Classification becomes permanent bureaucracy.** Keep one generated source and record only reviewed decisions and summaries.
- **Test consolidation weakens process-level coverage.** Preserve dedicated crash, restart, security, concurrency, and subprocess suites where responsibility differs.
- **Hard cutover removes a hidden consumer.** Require complete caller evidence, negative-reference checks, and separate approval.
- **User data is mistaken for disposable state.** Require authority classification and backup/count/digest verification.
- **Subjective MEM authority is over-generalized.** Apply ADR 0005 only to its owned domain; review other stores separately.
- **Parallel tracks conflict on the same path.** Reconcile shared paths and authority references before either PR is finalized; neither track silently overwrites the other.
- **Cleanup delays product validation.** Keep dogfood and feature-value work independent from maintenance sequencing.

## Adoption boundary

Acceptance would authorize only:

- generation and review of a commit-fixed repository baseline;
- responsibility classification of scripts, workflows, and modules;
- invocation-root analysis;
- preparation of non-executing candidate-wave plans;
- proposal of separate atomic implementation PRs.

Acceptance would not authorize:

- deletion, movement, rename, consolidation, or compatibility removal;
- merging any candidate wave;
- changing runtime behavior;
- storage migration or persistent-write enablement;
- deleting or migrating user-owned durable state;
- applying Subjective MEM storage authority to unrelated domains;
- repository-wide Pydantic conversion;
- default-on graduation;
- governing, pausing, replacing, or changing the scope of the separately authorized documentation hard-cutover program;
- whole-repository rewrite.

## Validation before disposition

Before this proposal is accepted or rejected:

- metadata, placement, links, and documentation semantic checks pass;
- current main is the proposal base;
- only this proposal document changes;
- PR #567's O3 false-positive correction is preserved;
- proposal acceptance is explicitly insufficient to authorize deletion;
- documentation cleanup is represented as a parallel, separately governed track rather than a prerequisite;
- PR #577 inventory is described as evidence, not authority;
- ADR 0005 is limited to Subjective MEM storage authority;
- broad SQLite migration remains unauthorized;
- no runtime, workflow, storage, schema, or implementation file changes.

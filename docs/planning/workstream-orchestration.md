---
relaylm_doc_type: planning
relaylm_authority: chatgpt_continuation_command_parallel_workstream_and_pr_convergence
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - the shorthand continuation command changes
  - the project critical path or parallel lane registry changes
  - the universal PR convergence lifecycle changes
  - PR concurrency or conflict rules change
  - the authoritative status or sequencing source moves
  - the historical-retirement or retained-record policy changes
relaylm_not_authoritative_for:
  - current implementation completion
  - exact runtime, storage, schema, contract, or API behavior
  - authorization to merge a PR that has not passed required review and validation
  - background or asynchronous execution
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/project_execution_plan.md
  - repository-structure-migration.md
  - ../DOCUMENTATION_MODEL.md
  - ../adr/0006-repository-structure-and-maintenance-sequencing.md
---
# Workstream Orchestration, Continuation Command, and PR Convergence

Last reviewed: 2026-07-24 JST

## Purpose

This document defines:

1. what ChatGPT does when the user says `次に進めて`, `進めて`, `続けて`, or `次へ`;
2. how critical and parallel workstreams are selected;
3. the universal P0-P8 lifecycle required for every pull request.

The shorthand instruction is an execution command, not a request for a menu of recommendations.

Parallel work means advancing multiple independent workstreams in the current project portfolio. It does not mean hidden background execution, delayed delivery, or asynchronous work after the current response.

## Current lane entry points

As of this review:

```text
completed prerequisites
  PR #665 LC-1A Correct                         merged
  PR #667 Documentation Hard Cutover 1C-57     merged

Lane C next
  LC-1B Forget

Lane D next
  D1 canonical active graph / retained-record allowlist / retirement-manifest lock

Lane R next
  R1 code, script, smoke, workflow, and validator classification
```

Detailed stage definitions remain owned by [Repository Structure and Documentation Canonicalization Plan](repository-structure-migration.md).

## Meaning of continuation commands

The following instructions invoke the same default behavior unless the user narrows the scope:

```text
次に進めて
進めて
続けて
次へ
```

On receipt, ChatGPT must:

1. refresh `main`, open PRs, checks, reviews, mergeability, and relevant authorities;
2. identify each active PR's current P0-P8 state;
3. converge existing PRs before opening overlapping replacements;
4. advance the earliest executable Lane C action;
5. use CI, sequencing, permission, or shared-path blockers as a trigger to advance eligible Lane D or Lane R work;
6. advance at least one parallel lane when meaningful path- and authority-disjoint work exists;
7. avoid asking the user to choose when the documented order resolves the choice;
8. merge a clean PR when P6 passes unless the user limited the turn to review-only;
9. report the resulting critical, parallel, and portfolio state and the next automatically selected action.

A scope-specific instruction such as `LC-1だけ進めて`, `ドキュメント整理だけ進めて`, `コード整理を進めて`, or `#668を進めて` limits lane selection for that turn. It does not weaken the universal PR lifecycle.

## Authoritative reading order

At the beginning of every continuation turn, read or verify:

1. current `main` and open PR state;
2. `docs/PROJECT_STATUS.md` for implemented state and caveats;
3. `docs/architecture/project_execution_plan.md` for repository-wide sequencing;
4. the owning plan for each active lane;
5. exact ADRs, contracts, changed files, review threads, callers, workflows, generated registries, and entry points required by the selected action.

Conversation memory, handoff prompts, PR bodies, retired Git blobs, and historical records are orientation only. They do not override current repository authorities.

## Workstream registry

### Lane C: critical implementation

```text
LC-1B Forget
  -> LC-1C Pin / Unpin
  -> LC-1D Restore
  -> LC-1E Consolidate
  -> RT-1 Retrieval projection and one-authority hard cutover
```

Only one authority-changing LC-1 or RT-1 PR may be active at a time unless an accepted plan explicitly authorizes a coordinated atomic set.

### Lane D: documentation canonicalization and historical retirement

```text
D1 active graph / retained-record / retirement-manifest lock
  -> D2 stable-domain synthesis
  -> D3 historical-retirement batches
  -> D4 lifecycle canonicalization after LC-1
  -> D5 Retrieval / Primary MEM canonicalization after RT-1
  -> D6 final retirement and legacy cutover-tool retirement
```

Retired documentation is deleted from the current tree and recovered through Git history. `records/` retains only narrowly typed records with a continuing current function.

### Lane R: repository maintenance

```text
R1 responsibility classification
  -> R2 test / smoke / validation consolidation
  -> R3 generated navigation and drift checks
  -> R4 low-risk independent package moves
  -> R5 governed core package migration after RT-1
  -> R6 Primary MEM retirement-or-move cleanup
```

Classification may overlap other lanes. Destructive cleanup, path moves, namespace changes, and historical retirement still require their own reviewed atomic PRs.

## Default portfolio capacity

```text
1 Lane C PR
+ up to 1 Lane D PR
+ up to 1 Lane R PR
```

Three open PRs are a ceiling, not a target. Open fewer when work overlaps, review capacity would be diluted, or an unmerged dependency is likely to invalidate the next PR.

A PR is not opened merely to fill a lane. It requires a bounded scope, identified owner, path and authority non-overlap, and a validation plan.

## Universal PR convergence lifecycle

Every PR in every lane passes through the following states. Reliable repository evidence may prove an earlier state complete, but no required state may be skipped merely for speed.

### P0: scope and authority lock

Before substantive implementation:

- identify lane and program stage;
- identify exact paths and authorities;
- identify current callers, consumers, entry points, workflows, and generated registries;
- state behavioral and authority non-goals;
- state compatibility, migration, rollback, retirement, and removal boundaries;
- define the validation matrix;
- establish path and authority parallel-safety.

An unclear or expanding scope returns to P0.

### P1: normal implementation

Implement the smallest complete atomic boundary.

Implementation includes the tests, process validation, documentation, records, migrations, link repairs, caller updates, deletions, and negative-reference checks required to make the boundary reviewable.

Known in-scope correctness work is not deferred merely to open a PR sooner.

### P2: baseline validation and reviewable PR

Before thorough review:

- branch and PR match the declared atomic scope;
- obvious syntax, format, compile, schema, link, and focused-test failures are fixed;
- PR body records scope, non-goals, validation, rollback, retirement, and parallel-safety;
- current head SHA is recorded;
- no uncommitted or hidden work is required to understand the PR.

A draft PR may exist before P2, but it is not implementation-complete until P2 passes.

### P3: thorough review

Perform a fresh adversarial review of the complete PR, not only the latest patch.

Review includes, where relevant:

- accepted contracts, ADRs, plans, and current status;
- the complete diff and every changed file;
- direct, indirect, dynamic, subprocess, workflow, operator, and documentation callers;
- correctness, failure modes, race and crash behavior, security and privacy, migration, rollback, and recovery;
- tests for missing negative cases, false positives, false negatives, and accidental tautologies;
- compatibility surfaces and removal gates;
- duplicate authority, fallback precedence, stale paths, dead wrappers, and scope drift;
- documentation claims against actual behavior;
- deletion or retirement recoverability and replacement coverage.

Lane emphasis:

```text
Lane C
  runtime semantics, state transitions, schemas, authorization, concurrency,
  crash recovery, idempotency, migration, rollback, and regression

Lane D
  authority, granularity, current-versus-target separation, normative extraction,
  links and routers, retained records, Git recoverability, and omission risk

Lane R
  caller and invocation coverage, behavioral equivalence, process boundaries,
  imports and workflows, characterization removal gates, and negative references
```

P3 ends with explicit findings or an explicit no-finding result. CI success alone is not P3.

### P4: correction and exact-head validation

For every actionable finding:

1. correct the underlying issue rather than only the symptom;
2. add or strengthen regression coverage when practical;
3. update contracts, docs, PR body, manifests, or records when the boundary changed;
4. commit the correction;
5. rerun focused validation and required exact-head CI;
6. verify the correction did not expand scope or create a new authority conflict.

A finding remains open until the corrected exact head is inspected.

### P5: fresh final-review loop

Review the latest exact head after every correction.

The final review verifies:

- every prior finding is factually resolved;
- the complete resulting diff remains in scope;
- corrections introduced no new defect;
- required focused and broad validation passed on the exact head;
- review threads are resolved or factually dispositioned;
- PR body and evidence describe the actual final state;
- the PR is mergeable against the intended base;
- shared status and sequencing changes belong to the correct convergence PR.

Loop rule:

```text
P4 correction and exact-head validation
  -> P5 final review
  -> finding exists? yes -> P4
  -> finding exists? no  -> P6
```

There is no fixed iteration limit. The loop ends only when the exact head has no unresolved correctness, scope, validation, authority, review-thread, conflict, or mergeability issue.

### P6: merge gate

A PR is merge-ready only when:

- P0 through P5 are complete;
- P3 and P5 covered the complete PR;
- final review found no unresolved issue;
- required exact-head checks succeeded and skips are understood;
- no unresolved review thread or requested change remains;
- base and head are the intended commits;
- no unreviewed conflict resolution exists;
- no later repository change invalidated the review;
- destructive and authority-changing effects remain within authorization.

Do not merge a failing, stale, conflicting, unresolved, or semantically unreviewed PR merely because it is next.

### P7: merge

When P6 passes and continuation authorization applies, merge without asking the user to repeat a choice already resolved by this plan.

Use the repository's accepted merge method and expected-head protection where available. Do not silently merge a moved head.

`レビューだけ`, `マージしないで`, or an equivalent user restriction disables automatic merge for that turn.

### P8: post-merge convergence

After merge:

- verify merge result and resulting `main` identity;
- verify required post-merge or main-head validation;
- update shared status, sequencing, generated registries, or bookkeeping only through the owning convergence action;
- close or supersede replaced PRs and branches with a factual disposition where appropriate;
- release the lane slot;
- select the next executable portfolio action.

A merged PR is not reported as complete when required post-merge convergence failed or remains unknown.

## Continuation behavior inside a PR

A bare continuation command advances an existing PR toward P8 before opening another PR in the same lane.

```text
no PR exists
  -> P0 -> P1 -> P2 reviewable PR

PR awaits thorough review
  -> P3

review findings exist
  -> P4 -> P5 loop

PR is clean but CI is pending
  -> verify CI and advance a parallel-safe lane

PR passes P6
  -> P7 merge -> P8 convergence
```

Do not call a PR complete while deferring a known correction to a later PR. Do not start the next item in the same lane while the current PR can still be converged.

## Portfolio action-selection algorithm

### Step 1: converge existing work

Determine the P0-P8 state of every active PR and perform the next executable convergence action. Existing clean or correctable PRs take priority over replacements.

### Step 2: advance Lane C

Choose the earliest incomplete executable Lane C item. Advance its current PR through the lifecycle or create a bounded P0-P2 PR when no owner exists.

Do not skip an earlier lifecycle dependency to begin a later lifecycle or Retrieval slice.

### Step 3: use blockers to trigger parallel work

When Lane C is temporarily blocked by pending CI, permission, merge sequencing, or a shared-path dependency, select the highest-priority executable Lane D or Lane R action that is path- and authority-disjoint.

Pending CI alone is not a stop condition while another safe bounded action exists.

### Step 4: fill remaining safe capacity

After Lane C, advance one additional eligible parallel lane when:

- it shares no path, authority, caller, or generated registry;
- it will not be invalidated by a pending merge;
- its PR remains atomic and reviewable;
- it does not create a second runtime, storage, documentation, record, or import authority;
- the current interaction can complete a meaningful bounded action.

Do not create speculative work only to appear parallel.

### Step 5: update shared authorities at convergence points

Implementation PRs update code, tests, contracts that must ship atomically, and slice-owned validation. Shared status and sequencing documents are updated only by their owning convergence or planning PR.

`docs/PROJECT_STATUS.md` changes only after exact-head evidence proves implemented state.

## Parallel-safety rules

Two work items are not parallel-safe when either changes:

- the same file or generated registry;
- the same runtime, storage, schema, contract, documentation, or record authority;
- a caller or entry point the other moves or removes;
- shared status or sequencing without one convergence owner;
- an unmerged semantic dependency;
- competing canonical paths, import surfaces, record classes, or precedence rules.

Textual path-disjointness is necessary but not sufficient. Authority overlap also blocks parallel execution.

When two lanes require one shared file, assign one owner PR and make the other depend on it.

## Documentation execution rule

Documentation work is selected by canonical target domain, not by the next legacy filename.

Each synthesis and retirement PR must identify target authority and granularity, enumerate sources, extract live normative content, build canonical documents, classify retained records, repair current links, record retiring blobs and replacements, delete retired sources, and verify Git recoverability.

Memory lifecycle canonicalization waits for LC-1. Retrieval and Primary MEM canonicalization waits for RT-1.

## Code, smoke, and tooling execution rule

Each asset is classified as:

```text
active
transitional
retired
```

Active assets have a current supported caller or protected boundary and move toward function-oriented names through their owning migration.

Transitional assets must identify owner, protected boundary, current caller, removal gate, and replacement validation.

Retired assets are deleted from the current tree and recovered through Git history. Do not create a general executable archive tree.

## Progress report contract

Every continuation response reports:

```text
Critical lane
  PR and P0-P8 stage
  action completed
  exact head
  validation, review, and merge state

Parallel lanes
  PR and P0-P8 stage where applicable
  action completed or exact reason no safe action existed

Portfolio state
  active PR count
  conflicts or blockers
  next automatically selected action
```

Do not present a menu unless a genuine unresolved policy decision requires the user rather than repository evidence.

## Stop conditions

A continuation turn may stop without opening or changing work only when:

- all registered lanes are complete;
- every remaining item requires a genuine user decision or unavailable external authority;
- no path- and authority-disjoint bounded action exists;
- repository state cannot be read reliably enough to act safely.

The response must name the exact condition. Pending CI alone is not a stop condition while another eligible lane exists.
